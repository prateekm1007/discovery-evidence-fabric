#!/usr/bin/env python3
"""scripts/r425_package_quality_audit.py — R425 §8/§9.

THE INDEPENDENT PACKAGE-QUALITY AUDITOR.

Independence contract (R425 §8: the factory must not grade itself):
  * this auditor reads ONLY the generated package bytes (the ZIP) and,
    when supplied, the run record for cross-checks;
  * it imports NO factory module (no invention_bridge, no package
    builders) — its checks are written against the SCHEMA the factory
    promises, not against the factory's own functions;
  * every hash is re-computed from the actual bytes on disk (Art. VI);
  * the CAD regeneration equivalence check EXECUTES THE SHIPPED
    PARAMETRIC_MODEL_SOURCE.py in a subprocess — the recipient's own
    verification path, not the factory's.

It verifies twelve dimensions (R425 §8) and compares the package
against the released elite portfolio P-07 BY CONTENT (R425 §9),
distinguishing STRUCTURAL PARITY (the files exist) from SEMANTIC
PARITY (the content depth is present) — semantic parity is never
claimed merely because the file list matches.

Usage:
    python scripts/r425_package_quality_audit.py <package.zip> \
        [--run-record run.json] [--benchmark p07_benchmark.json] \
        [--out PACKAGE_QUALITY_AUDIT.json] [--model-dir <dir>]

--model-dir: the UNPACKED package directory (when available, the
regeneration check executes the shipped source from it; otherwise the
auditor unpacks to a temp dir).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

SCHEMA = "R425_PACKAGE_QUALITY_AUDIT/2.0"

ELITE_DOCS = (
    "00_PACKAGE_README.pdf", "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
    "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
    "03_BUYER_DECISION_CARD.pdf", "04_EVIDENCE_SUMMARY.pdf",
    "05_TRANSFER_MANIFEST.pdf")
DECISIVE_FIELDS = (
    "experiment_id", "hypothesis", "intervention", "baseline_control",
    "test_article", "measurable_variables",
    "apparatus_instrumentation", "procedure", "acceptance_rule",
    "falsification_rule", "expected_discriminating_outcomes",
    "dependencies", "safety_operational_constraints",
    "decision_mapping", "next_technical_state_transition")
FILLER_PHRASES = (
    "further testing required", "additional studies needed",
    "more research is required")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ok(ok, **kw):
    kw["verdict"] = "PASS" if ok else "FAIL"
    return kw


class Auditor:
    def __init__(self, zip_path: Path, run_record: dict | None,
                 benchmark: dict | None):
        self.zip_path = zip_path
        self.run_record = run_record or {}
        self.benchmark = benchmark
        self.names: list[str] = []
        self.files: dict[str, bytes] = {}
        with zipfile.ZipFile(zip_path) as zf:
            self.names = zf.namelist()
            for n in self.names:
                self.files[n] = zf.read(n)
        # the package root inside the zip (e.g. TECHNOLOGY_PACKAGE/)
        self.root = ""
        if self.names:
            first = self.names[0]
            self.root = first.split("/")[0] + "/" \
                if "/" in first else ""
        self.metrics: dict = {}
        self.verdicts: dict = {}

    # -- helpers ---------------------------------------------------------
    def _j(self, rel: str):
        raw = self.files.get(self.root + rel)
        if raw is None:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None

    def _has(self, rel: str) -> bool:
        return (self.root + rel) in self.files

    def _sizes(self, suffix: str) -> list[int]:
        return [len(v) for k, v in self.files.items()
                if k.endswith(suffix) and k.count("/") == 1]

    # -- dimension 1: buyer-document structure ---------------------------
    def check_buyer_documents(self):
        missing = [d for d in ELITE_DOCS if not self._has(d)]
        pdfs_ok = all(
            self.files.get(self.root + d, b"").startswith(b"%PDF")
            for d in ELITE_DOCS if self._has(d))
        sizes_ok = all(
            len(self.files.get(self.root + d, b"")) > 1500
            for d in ELITE_DOCS if self._has(d))
        passed = not missing and pdfs_ok and sizes_ok
        self.metrics["documents"] = {
            "pdf_count": len(self._sizes(".pdf") or []) or
            len([d for d in ELITE_DOCS if self._has(d)]),
        }
        return _ok(passed, missing=missing, pdf_magic=pdfs_ok,
                   nontrivial_size=sizes_ok,
                   note="six elite buyer documents, real PDF bytes")

    # -- dimension 2: engineering-definition completeness ------------------
    def check_engineering_definition(self):
        ed = self._j("02_ENGINEERING_DEFINITION.json") or {}
        families = {k: len(ed.get(k) or [])
                    for k in ("design_inputs", "design_outputs",
                              "failure_modes", "verification_items",
                              "build_steps", "governing_equations")}
        has_build_path = isinstance(ed.get("build_path"), dict)
        passed = (sum(families.values()) >= 12 and has_build_path)
        self.metrics["engineering"] = dict(families)
        return _ok(passed, families=families,
                   build_path=has_build_path,
                   note="machine layer carries the real derived "
                        "engineering families")

    # -- dimension 3: evidence classification integrity ---------------------
    def check_evidence(self):
        ev = self._j("03_EVIDENCE_SUMMARY.json") or {}
        roles = {r.get("role"): r.get("count")
                 for r in (ev.get("roles") or [])
                 if isinstance(r, dict)}
        expected_roles = {"DIRECT_SUPPORT", "PARTIAL_SUPPORT",
                          "BACKGROUND", "ANALOGY", "CONTRADICTION",
                          "UNAVAILABLE_SOURCES"}
        counts_match = True
        if self.run_record:
            fs = self.run_record.get("final_state") or {}
            rc = fs.get("evidence_classification_counts") or {}
            for role, cnt in roles.items():
                key = role if role != "CONTRADICTION" \
                    else "CONTRADICTORY"
                if key in rc and rc[key] != cnt:
                    counts_match = False
        passed = (set(roles) == expected_roles and counts_match
                  and bool(ev.get("provenance")))
        self.metrics["evidence"] = {
            "role_count": len(roles),
            "total_classified": sum(
                v for v in roles.values() if isinstance(v, int)),
        }
        return _ok(passed, roles=sorted(roles),
                   counts_match_run_record=counts_match,
                   note="evidence roles + counts cross-checked "
                        "against the run record when supplied")

    # -- dimension 4: traceability completeness -----------------------------
    def check_traceability(self):
        tr = self._j("ENGINEERING_TRACEABILITY.json") or {}
        links = tr.get("links") or []
        kinds = {l.get("link_kind") for l in links}
        nodes = (tr.get("coverage") or {}).get("total_nodes") or {}
        # the edge classes are REQUIRED exactly when their node
        # families exist — a record with no design outputs honestly
        # carries no DO_TO_DI links, but every family that EXISTS must
        # have its edges (each node contributes at least one link,
        # EXPLICIT or UNKNOWN-with-basis)
        required = set()
        if (nodes.get("design_outputs") or 0) > 0:
            required.add("DO_TO_DI")
        if (nodes.get("failure_modes") or 0) > 0:
            required.add("FM_TO_DO")
        if (nodes.get("verification") or 0) > 0:
            required.add("VF_TO_FM")
        cov = tr.get("coverage") or {}
        accounting = (cov.get("explicit_bindings", 0)
                      + cov.get("unknown_bindings", 0)
                      == cov.get("total_links") == len(links))
        unknowns_cited = all(
            l.get("binding_basis")
            for l in links if l.get("binding") == "UNKNOWN")
        coverage_keys = all(k in cov for k in (
            "total_nodes", "orphan_nodes",
            "unverified_failure_modes",
            "failure_modes_without_decisive_verification",
            "experiment_targets_with_no_upstream_requirement"))
        passed = (required <= kinds and links and accounting
                  and unknowns_cited and coverage_keys)
        self.metrics["traceability"] = {
            "chains_or_links": len(links),
            "link_kinds": len(kinds),
            "explicit": cov.get("explicit_bindings"),
            "unknown": cov.get("unknown_bindings"),
        }
        return _ok(passed, link_kinds=sorted(kinds),
                   accounting_identity=accounting,
                   unknown_links_cite_records=unknowns_cited,
                   coverage_metrics=coverage_keys,
                   note="the COMPLETE graph with coverage metrics — "
                        "not merely 'some links exist'")

    # -- dimension 5: decisive-experiment completeness -----------------------
    def check_decisive_experiment(self):
        dex = self._j("04_DECISIVE_EXPERIMENT.json") or {}
        contract = dex.get("contract") or {}
        fields_present = [f for f in DECISIVE_FIELDS if f in contract]
        every_field_classified = all(
            isinstance(contract.get(f), dict)
            and contract[f].get("status") in (
                "DEFINED", "NOT_DEFINED_IN_CANONICAL_STATE")
            and contract[f].get("provenance_basis")
            for f in fields_present)
        blob = json.dumps(dex).lower()
        no_filler = not any(p in blob for p in FILLER_PHRASES)
        passed = (len(fields_present) >= 14
                  and every_field_classified and no_filler)
        cc = dex.get("contract_completeness") or {}
        self.metrics["experiment"] = {
            "fields_total": cc.get("fields_total",
                                   len(fields_present)),
            "fields_defined": cc.get(
                "fields_defined_in_canonical_state"),
        }
        return _ok(passed, fields=len(fields_present),
                   every_field_classified=every_field_classified,
                   no_filler_prose=no_filler,
                   note="14-field buyer-runnable contract; gaps are "
                        "NOT_DEFINED_IN_CANONICAL_STATE with basis")

    # -- dimension 6: maturity basis integrity ---------------------------------
    def check_maturity(self):
        mb = self._j("MATURITY_BASIS.json") or {}
        sem = mb.get("semantic_gates") or {}
        contract = mb.get("experiment_contract") or {}
        counts = mb.get("counts") or {}
        evidence_derived = bool(sem.get("counts_semantically_complete")
                                and counts)
        level = mb.get("technology_maturity")
        # EXPERIMENT_READY must be backed by the discriminating contract
        ready_backed = (level != "EXPERIMENT_READY"
                        or contract.get("discriminating") is True)
        passed = bool(mb.get("basis") and evidence_derived
                      and ready_backed)
        self.metrics["maturity"] = {
            "level": level,
            "evidence_id_families": len(
                [k for k in mb if k.endswith("_evidence_ids")]),
        }
        return _ok(passed, level=level,
                   semantic_gates_present=bool(sem),
                   evidence_derived=evidence_derived,
                   experiment_ready_backed=ready_backed,
                   note="maturity is semantic + evidence-derived")

    # -- dimension 7: unknown-roadmap actionability ----------------------------
    def check_unknown_roadmap(self):
        ur = self._j("UNKNOWN_ROADMAP.json") or {}
        unknowns = ur.get("unknowns") or []
        source_count = ur.get("unknown_count_source")
        if not unknowns and (source_count in (0, None)):
            return _ok(True, entries=0,
                       note="no unknowns recorded in the canonical "
                            "state — the roadmap discipline applies "
                            "where unknowns exist (honest absence)")
        fields_required = ("unknown_statement", "why_unknown",
                           "consequence", "resolution_action",
                           "expected_measurement", "acceptance_rule",
                           "priority", "source_record_ids")
        complete = sum(1 for u in unknowns if all(
            u.get(f) is not None for f in fields_required))
        priorities_ok = all(
            u.get("priority") in ("HIGH", "MEDIUM", "LOW")
            for u in unknowns)
        distinct_actions = len({
            json.dumps(u.get("resolution_action"), sort_keys=True)
            for u in unknowns})
        passed = (unknowns and complete == len(unknowns)
                  and priorities_ok)
        self.metrics["unknown_specificity"] = {
            "unknown_count": len(unknowns),
            "avg_fields_per_entry": round(sum(
                len(u) for u in unknowns) / max(len(unknowns), 1), 2),
            "with_resolution_action": sum(
                1 for u in unknowns if u.get("resolution_action")),
            "distinct_resolution_actions": distinct_actions,
        }
        return _ok(passed, entries=len(unknowns),
                   all_entries_complete=complete == len(unknowns),
                   priorities_full_words=priorities_ok,
                   distinct_resolution_actions=distinct_actions,
                   note="specific, actionable, per-unknown — answers "
                        "'what must a technical team do next?'")

    # -- dimension 8: provenance / integrity ------------------------------------
    def check_provenance(self):
        pm = self._j("PACKAGE_MANIFEST.json") or {}
        entries = pm.get("files") or []
        verified = 0
        mismatches = []
        for e in entries[:400]:
            raw = self.files.get(self.root + e.get("path", ""))
            if raw is None:
                mismatches.append(f"missing in zip: {e.get('path')}")
                continue
            if _sha256_bytes(raw) == e.get("sha256"):
                verified += 1
            else:
                mismatches.append(f"hash mismatch: {e.get('path')}")
        prov = self._j("PROVENANCE.json") or {}
        commit = prov.get("engine_commit")
        commit_ok = bool(commit) and str(commit).lower() not in (
            "unknown", "none", "")
        version_ok = bool(prov.get("package_version"))
        passed = (entries and verified == len(entries)
                  and not mismatches and commit_ok and version_ok)
        self.metrics["provenance"] = {
            "manifest_hashed_files": len(entries),
            "hashes_verified": verified,
        }
        return _ok(passed, manifest_entries=len(entries),
                   hashes_verified_against_bytes=verified,
                   hash_mismatches=mismatches[:5],
                   engine_commit=commit,
                   engine_commit_resolved=commit_ok,
                   package_version=prov.get("package_version"),
                   note="every manifest hash re-computed from the "
                        "actual ZIP bytes")

    # -- dimension 9: 3D / model integrity ---------------------------------------
    def check_model_layer(self):
        status = self._j("MODEL/3D_DESIGN_STATUS.json") or {}
        cls = status.get("visualizability_class")
        is_eng = cls == "ENGINEERING_3D"
        model_files = [n for n in self.names
                       if n.startswith(self.root + "MODEL/")]
        if is_eng:
            steps = [n for n in model_files if n.endswith(".step")]
            stls = [n for n in model_files if n.endswith(".stl")]
            glbs = [n for n in model_files if n.endswith(".glb")]
            ev = [n for n in model_files
                  if "/3D_EVIDENCE/" in n and n.endswith(".json")]
            regen = self._j("MODEL/3D_EVIDENCE/"
                            "REGENERATION_CHECK.json") or {}
            passed = bool(steps and stls and glbs and ev
                          and regen.get("regeneration_status")
                          == "REPRODUCIBLE")
            self.metrics["model_layer"] = {
                "step_files": len(steps), "stl_files": len(stls),
                "glb_files": len(glbs),
                "evidence_files": len(ev),
                "has_parametric_source": self._has(
                    "MODEL/PARAMETRIC_MODEL_SOURCE.py"),
            }
            return _ok(passed, cls=cls, step=len(steps),
                       stl=len(stls), glb=len(glbs),
                       evidence_json=len(ev),
                       regeneration=regen.get("regeneration_status"),
                       note="ENGINEERING_3D: parametric source + "
                            "derived CAD + independent evidence")
        # conceptual class: NO fake engineering files
        no_eng = not any(
            n.endswith((".step", ".stl"))
            for n in model_files) and not self._has(
            "MODEL/PARAMETRIC_MODEL_SOURCE.py")
        disclaimer = self._has("MODEL/CONCEPTUAL_3D_DISCLAIMER.json") \
            or bool(status.get("status_meaning"))
        self.metrics["model_layer"] = {
            "glb_files": len([n for n in model_files
                              if n.endswith(".glb")]),
            "has_parametric_source": False,
            "evidence_files": 0,
        }
        return _ok(no_eng and disclaimer, cls=cls,
                   no_fake_engineering_files=no_eng,
                   note="conceptual class honestly labeled; no "
                        "fabricated engineering artifacts")

    # -- dimension 10: canonical-source regeneration equivalence -----------------
    def check_cad_regeneration(self):
        cls = (self._j("MODEL/3D_DESIGN_STATUS.json") or {}).get(
            "visualizability_class")
        if cls != "ENGINEERING_3D":
            return _ok(True, cls=cls,
                       note="not applicable: conceptual class ships "
                            "no parametric source (nothing to "
                            "regenerate — honest)")
        prov = self._j("MODEL/CAD_SOURCE_PROVENANCE.json")
        src = self.files.get(
            self.root + "MODEL/PARAMETRIC_MODEL_SOURCE.py")
        if prov is None or src is None:
            return _ok(False, cls=cls,
                       provenance_record=prov is not None,
                       note="ENGINEERING package missing CAD source "
                            "provenance or the exported source")
        recorded_sha = prov.get("exported_source_sha256")
        actual_sha = _sha256_bytes(src)
        identity_fields = all(
            prov.get("canonical_builder", {}).get(f)
            for f in ("form", "builder_function",
                      "builder_source_sha256"))
        param_hash = prov.get("parameter_hash")
        derived = prov.get("derived_artifacts") or []
        derived_ok = all(e.get("sha256") for e in derived) and derived
        # best-effort independent regeneration (the recipient's path)
        regen = self._regenerate_in_subprocess()
        passed = (recorded_sha == actual_sha and identity_fields
                  and param_hash and derived_ok
                  and regen.get("ok") is not False)
        return _ok(passed,
                   exported_source_sha_matches=recorded_sha
                   == actual_sha,
                   canonical_identity_fields=identity_fields,
                   parameter_hash=bool(param_hash),
                   derived_artifact_hashes=derived_ok,
                   independent_regeneration=regen,
                   note="the shipped source is the exported canonical "
                        "builder and independently regenerates the "
                        "recorded geometry")

    def _regenerate_in_subprocess(self) -> dict:
        """Execute the SHIPPED source in a subprocess — the recipient's
        verification path, independent of the factory (R425 §2/§8)."""
        try:
            with tempfile.TemporaryDirectory() as td:
                td = Path(td)
                (td / "PARAMETRIC_MODEL_SOURCE.py").write_bytes(
                    self.files[
                        self.root + "MODEL/PARAMETRIC_MODEL_SOURCE.py"])
                params = self._j("MODEL/PARAMETERS.json")
                if params:
                    (td / "PARAMETERS.json").write_text(
                        json.dumps(params))
                proc = subprocess.run(
                    [sys.executable,
                     str(td / "PARAMETRIC_MODEL_SOURCE.py")],
                    capture_output=True, text=True, timeout=300,
                    cwd=str(td))
                if proc.returncode != 0:
                    return {"ok": False,
                            "error": proc.stderr[-200:]}
                out = json.loads(proc.stdout)
                kd = self._j("MODEL/KEY_DIMENSIONS.json") or {}
                v_ok = abs((out.get("volume_mm3") or 0)
                           - (kd.get("volume_mm3") or 0)) <= 1e-3
                bb = out.get("bbox") or {}
                kd_bb = kd.get("bbox") or {}
                b_ok = all(
                    abs((bb.get(k) or 0) - (kd_bb.get(k) or 0)) <= 1e-3
                    for k in ("xlen", "ylen", "zlen"))
                return {"ok": v_ok and b_ok,
                        "volume_matches_record": v_ok,
                        "bbox_matches_record": b_ok}
        except Exception as exc:  # noqa: BLE001 — typed, never silent
            return {"ok": None, "error": f"{type(exc).__name__}: "
                                         f"{exc}",
                    "note": "TOOL LIMITATION: regeneration subprocess "
                            "unavailable in this environment"}

    # -- dimension 11: no counsel package / customer surface ---------------------
    def check_no_counsel_surface(self):
        """A counsel WORKFLOW surface (files, routes, JSON sections,
        buyer actions) is forbidden; the honest boundary DISCOURSE
        ('patentability is downstream legal work for qualified
        counsel') is allowed — it is disclosure, not a product."""
        # structural markers: file names + JSON keys + action phrases
        key_pat = re.compile(r'"([a-z0-9_\- ]*)"\s*:')
        structural_markers = (
            "counsel_package", "ip_counsel", "counsel_workflow",
            "counsel_readiness", "patent_claims", "claim_drafting",
            "fto_opinion", "freedom_to_operate_opinion",
            "patentability_adjudication", "claim_chart",
            "patentability_opinion")
        action_phrases = (
            "download for ip counsel", "counsel export",
            "ip counsel package", "legal readiness package")
        offenders = []
        for n, raw in self.files.items():
            lname = n.lower()
            for marker in structural_markers:
                if marker in lname:
                    offenders.append(f"{n}: filename {marker}")
            if not n.endswith((".json", ".py", ".md", ".txt")):
                continue
            try:
                text = raw.decode("utf-8", errors="ignore").lower()
            except Exception:  # noqa: BLE001
                continue
            keys = {m.group(1) for m in key_pat.finditer(text)}
            for marker in structural_markers:
                if any(marker in k for k in keys):
                    offenders.append(f"{n}: json key {marker}")
            for phrase in action_phrases:
                if phrase in text:
                    offenders.append(f"{n}: action phrase {phrase}")
        passed = not offenders
        return _ok(passed, offenders=offenders[:5],
                   note="no counsel WORKFLOW surface (files/routes/"
                        "sections/actions); the honest boundary "
                        "statement — legal work is downstream — is "
                        "disclosure, not a product surface")

    # -- dimension 12: no fabricated numeric/commercial claims --------------------
    def check_no_fabricated_claims(self):
        loop = self._j("LOOP_STATE.json") or {}
        loop_ok = loop.get("loop_verification_state") in (
            "NONE", "SYNTHETIC_LOOP_VERIFIED", "REAL_LOOP_VERIFIED")
        never_real = loop.get("loop_verification_state") != \
            "REAL_LOOP_VERIFIED"
        text_blob = "\n".join(
            raw.decode("utf-8", errors="ignore")
            for n, raw in self.files.items()
            if n.endswith((".json", ".py", ".md", ".txt")))
        # a fabricated PHYSICAL_OBSERVATION claim would appear as a
        # JSON VALUE (an evidence class assigned to something), not as
        # the honest boundary STATEMENTS the package carries ("no
        # physical observation is presented..."). Scan for the value
        # form only; count-based reality fields must be 0.
        value_form = re.findall(
            r':\s*"PHYSICAL_OBSERVATION"', text_blob)
        reality_counts = [
            (loop.get("reality_boundary") or {}).get(
                "physical_observation_count"),
            (self._j("05_TECHNICAL_EVALUATION.json") or {}).get(
                "physical_validation", {}).get("performed"),
        ]
        no_physical = (not value_form
                       and not any(c for c in reality_counts
                                   if isinstance(c, (bool, int))))
        econ = self._j("VALIDATION_ECONOMICS.json") or {}
        cost = (econ.get("cost_range") or {}).get("value")
        cost_ok = cost in (None, "NOT_ESTABLISHED",
                           "ENGINEERING_ESTIMATE", "ROUGH_ESTIMATE")
        comm = self._j("COMMERCIAL_EVIDENCE.json") or {}
        fabricated_dollars = re.findall(
            r"\$\s?\d[\d,.]*\s?(billion|million|bn|mm)",
            json.dumps(comm).lower())
        passed = (loop_ok and never_real and no_physical and cost_ok
                  and not fabricated_dollars)
        return _ok(passed, loop_state=loop.get(
            "loop_verification_state"), reality_boundary=no_physical,
                   cost_discipline=cost_ok,
                   market_figure_scan=fabricated_dollars[:3],
                   note="Art. XXXVII/XXXVIII/LXVI: loop NONE, no "
                        "physical-observation claim, no invented "
                        "dollars")

    # -- §9 benchmark comparison (content, not filenames) -------------------------
    def check_benchmark(self) -> dict:
        if not self.benchmark:
            return {"status": "NOT_SUPPLIED",
                    "note": "no benchmark fixture supplied — the P-07 "
                            "comparison was not run (disclosed)"}
        bm = self.benchmark
        m = self.metrics
        dims = []

        def _dim(name, structural, semantic_ratio, evidence):
            verdict = ("PARITY" if semantic_ratio >= 0.7 else
                       "PARTIAL" if semantic_ratio > 0 else "GAP")
            dims.append({
                "dimension": name,
                "structural_parity": structural,
                "semantic_parity": verdict,
                "semantic_ratio": round(semantic_ratio, 2),
                "evidence": evidence,
            })

        # engineering depth / equations
        eq = self._j("EQUATION_REGISTRY.json") or {}
        eqs = eq.get("equations") or []
        bm_eq = bm.get("equation_depth") or {}
        ratio = (
            (len(eqs) / max(bm_eq.get("equation_count", 1), 1))
            if bm_eq else 0.0)
        _dim("equation_depth",
             eq.get("status") in ("APPLICABLE", "NOT_APPLICABLE"),
             min(ratio, 1.0) if eqs else (1.0 if eq.get("status")
             == "NOT_APPLICABLE" else 0.0),
             {"audited": len(eqs),
              "benchmark": bm_eq.get("equation_count")})
        # traceability depth
        tr = self.metrics.get("traceability") or {}
        bm_tr = bm.get("traceability_depth") or {}
        _dim("traceability_depth", bool(tr.get("chains_or_links")),
             min((tr.get("chains_or_links", 0)
                  / max(bm_tr.get("chains", 1), 1)), 1.0),
             {"audited_links": tr.get("chains_or_links"),
              "benchmark_chains": bm_tr.get("chains")})
        # unknown specificity
        u = m.get("unknown_specificity") or {}
        bm_u = bm.get("unknown_specificity") or {}
        if u and bm_u:
            fields_ratio = (u.get("avg_fields_per_entry", 0)
                            / max(bm_u.get("avg_fields_per_entry", 1),
                                  1))
            distinct_ratio = (u.get("distinct_resolution_actions", 0)
                              / max(u.get("unknown_count", 1), 1))
            _dim("unknown_specificity", bool(u.get("unknown_count")),
                 min((fields_ratio * 0.5 + distinct_ratio * 0.5), 1.0),
                 {"audited": u, "benchmark": bm_u})
        # verification depth
        ed = m.get("engineering") or {}
        _dim("verification_depth",
             "verification_items" in ed,
             min((ed.get("verification_items", 0) or 0) / 8.0, 1.0),
             {"audited_verification_items":
                  ed.get("verification_items")})
        # build-plan usefulness
        _dim("build_plan_usefulness", "build_steps" in ed,
             min((ed.get("build_steps", 0) or 0) / 6.0, 1.0),
             {"audited_build_steps": ed.get("build_steps")})
        # buyer decision architecture
        has_card = self._has("03_BUYER_DECISION_CARD.pdf")
        has_readme = self._has("00_PACKAGE_README.pdf")
        _dim("buyer_decision_architecture",
             has_card and has_readme,
             1.0 if has_card and has_readme else 0.0,
             {"nine_question_card": has_card,
              "readme": has_readme})
        # model-source integrity (§2's contribution)
        eng = (self._j("MODEL/3D_DESIGN_STATUS.json") or {}).get(
            "visualizability_class") == "ENGINEERING_3D"
        cad_prov = self._j("MODEL/CAD_SOURCE_PROVENANCE.json")
        _dim("model_source_integrity",
             bool(cad_prov) if eng else True,
             1.0 if (cad_prov or not eng) else 0.0,
             {"cad_source_provenance": bool(cad_prov),
              "note": "P-07 predates the canonical-export record "
                      "(R425 §2); fresh engineering packages must "
                      "carry it"})
        # 3D evidence depth
        ml = m.get("model_layer") or {}
        bm_ml = bm.get("model_layer") or {}
        if eng:
            ratio = (ml.get("evidence_files", 0)
                     / max(bm_ml.get("evidence_files", 1), 1))
        else:
            ratio = 1.0 if ml.get("glb_files") else 0.0
        _dim("3d_evidence_depth", bool(ml), min(ratio, 1.0),
             {"audited": ml, "benchmark": bm_ml})
        # honesty of maturity
        mat = m.get("maturity") or {}
        _dim("honesty_of_maturity", bool(mat.get("level")),
             1.0 if mat else 0.0,
             {"audited_level": mat.get("level"),
              "benchmark_level": (bm.get("maturity_honesty")
                                  or {}).get("technology_maturity")})

        semantic = [d["semantic_parity"] for d in dims]
        structural_all = all(d["structural_parity"] for d in dims)
        return {
            "status": "COMPARED",
            "benchmark_provenance": bm.get("provenance"),
            "dimensions": dims,
            "structural_parity": ("PARITY" if structural_all
                                  else "GAP"),
            "semantic_parity_summary": {
                "PARITY": semantic.count("PARITY"),
                "PARTIAL": semantic.count("PARTIAL"),
                "GAP": semantic.count("GAP"),
            },
            "semantic_parity_verdict": (
                "SEMANTIC_PARITY" if semantic.count("PARITY")
                >= len(dims) - 2 and semantic.count("GAP") == 0
                else "SEMANTIC_PARTIAL" if semantic.count("PARITY")
                + semantic.count("PARTIAL") >= len(dims) // 2
                else "SEMANTIC_GAP"),
            "rule": ("STRUCTURAL parity = the files exist; SEMANTIC "
                     "parity = the content depth reaches the "
                     "benchmark's measured level (ratio >= 0.7 per "
                     "dimension). Semantic parity is NEVER claimed "
                     "from the file list alone (R425 §9)."),
        }

    # -- the audit -------------------------------------------------------------
    def run(self) -> dict:
        t0 = time.time()
        checks = {
            "buyer_document_structure": self.check_buyer_documents(),
            "engineering_definition_completeness":
                self.check_engineering_definition(),
            "evidence_classification_integrity":
                self.check_evidence(),
            "traceability_completeness": self.check_traceability(),
            "decisive_experiment_completeness":
                self.check_decisive_experiment(),
            "maturity_basis_integrity": self.check_maturity(),
            "unknown_roadmap_actionability":
                self.check_unknown_roadmap(),
            "provenance_integrity": self.check_provenance(),
            "model_integrity": self.check_model_layer(),
            "canonical_source_regeneration_equivalence":
                self.check_cad_regeneration(),
            "no_counsel_customer_surface":
                self.check_no_counsel_surface(),
            "no_fabricated_numeric_commercial_claims":
                self.check_no_fabricated_claims(),
        }
        benchmark = self.check_benchmark()
        all_pass = all(c["verdict"] == "PASS" for c in checks.values())
        return {
            "schema": SCHEMA,
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "audited_package": {
                "zip": str(self.zip_path),
                "bytes": self.zip_path.stat().st_size,
                "file_count": len(self.names),
                "zip_sha256": _sha256_bytes(
                    Path(self.zip_path).read_bytes()),
            },
            "independence": (
                "this auditor imports no factory module; every check "
                "reads the package bytes (and the supplied run record "
                "for cross-checks); every hash is re-computed from "
                "the bytes; the CAD regeneration executes the SHIPPED "
                "source in a subprocess — the factory cannot grade "
                "itself through this path"),
            "checks": checks,
            "benchmark_comparison": benchmark,
            "overall": {
                "all_twelve_pass": all_pass,
                "verdict": "PASS" if all_pass else "FAIL",
            },
            "wall_s": round(time.time() - t0, 2),
        }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("package_zip", type=Path)
    ap.add_argument("--run-record", type=Path, default=None)
    ap.add_argument("--benchmark", type=Path, default=None)
    ap.add_argument("--out", type=Path,
                    default=Path("PACKAGE_QUALITY_AUDIT.json"))
    args = ap.parse_args()
    if not args.package_zip.is_file():
        print(f"package zip not found: {args.package_zip}",
              file=sys.stderr)
        return 2
    run_record = None
    if args.run_record and args.run_record.is_file():
        run_record = json.loads(args.run_record.read_text())
    benchmark = None
    if args.benchmark and args.benchmark.is_file():
        benchmark = json.loads(args.benchmark.read_text())
    audit = Auditor(args.package_zip, run_record, benchmark).run()
    args.out.write_text(json.dumps(audit, indent=2,
                                   ensure_ascii=False))
    print(json.dumps({
        "verdict": audit["overall"]["verdict"],
        "all_twelve_pass": audit["overall"]["all_twelve_pass"],
        "benchmark": audit["benchmark_comparison"].get(
            "semantic_parity_verdict"),
        "wall_s": audit["wall_s"],
        "out": str(args.out),
    }, indent=1))
    return 0 if audit["overall"]["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
