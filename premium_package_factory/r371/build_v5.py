"""
build_v5.py — R371 portfolio V5 build orchestrator (R372 release-grade
extension).

Build order (each step fails closed):
  1. Load canonical packages + V2-mutation-aware headlines
  2. Derive per-package artifacts (commercial, equations + R372 validation,
     unknown roadmap, economics, loop state, R372 traceability semantics)
  3. Generate the two technical visuals per package (mechanism + experiment,
     the experiment diagram rendered from the machine-checkable spec)
  4. Render the six buyer PDFs per package + machine-readable JSON layer
     (the buyer card carries the FIVE DECISION CRITICALS block)
  5. Build the 15 package ZIPs from the folders
  6. Render portfolio-level documents (index/ranking, master, release report
     incl. the R372 traceability semantics table)
  7. Build PORTFOLIO_IDENTITY_REGISTRY.json from the actual artifacts
  8. Build RELEASE_CONTENT_MANIFEST.json from the actual filesystem,
     generate README.md from it, build the master ZIP from it
  9. Preserve history: move R370 release-process certificates to
     RELEASE/history_r370/ (never deleted — Constitution Art. XI)

Usage: python -m premium_package_factory.r371.build_v5 [--portfolio-root PATH]
"""

import argparse
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

# R374-5 deterministic ZIP entries: zipfile's default embeds each
# file's mtime into the archive, making the package ZIPs non-reproducible
# across builds (found live by the R374 fresh-clone protocol — the R372
# byte-identical claim covered PDFs/JSONs but never the ZIP containers).
# Fixed epoch timestamps make the ZIP container byte-reproducible while
# the archived CONTENT is unchanged.
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


def _zip_add(zf, path, arcname):
    zi = zipfile.ZipInfo(arcname, date_time=_ZIP_EPOCH)
    zi.compress_type = zipfile.ZIP_DEFLATED
    zi.external_attr = 0o644 << 16
    with open(path, "rb") as f:
        zf.writestr(zi, f.read())

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from premium_package_factory.r371.builder import get_styles, sha256_file, _now
from premium_package_factory.r371.builder_documents import init_styles
from premium_package_factory.r371.builder_dossier import init_styles as _init_dossier_styles
from premium_package_factory.r371 import builder_documents as bd
from premium_package_factory.r371 import builder_dossier as bdd
from premium_package_factory.r371 import builder_portfolio as bp
from premium_package_factory.r371.canonical_source import load_all_packages
from premium_package_factory.r371.commercial import build_commercial_evidence
from premium_package_factory.r371.economics import build_validation_economics
from premium_package_factory.r371.equations import build_equation_registry
from premium_package_factory.r371.experiment_diagram import build_experiment_diagram
from premium_package_factory.gates.render_verification import (
    content_completeness, geometric_qa, rendered_page_qa, verify_package,
    verify_pdf_rendering, write_report)
from premium_package_factory.gates.content_expectations import (
    build_content_expectations)
from premium_package_factory.r371.identity import build_registry, write_registry
from premium_package_factory.r371.loopstate import build_loop_state, portfolio_loop_summary
from premium_package_factory.r371.mechanism_diagram import build_all_mechanism_diagrams
from premium_package_factory.r371.ranking import build_ranking
from premium_package_factory.r371.unknowns import build_unknown_roadmap
from premium_package_factory.r372.diagram_adequacy import (
    experiment_diagram_spec, validate_experiment_spec)
from premium_package_factory.r372.equation_validation import validate_registry
from premium_package_factory.r372.traceability_semantics import (
    build_traceability_json, portfolio_traceability_table)
from premium_package_factory.r381.portfolio_cad import build_model_layer

FACTORY_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENGINE_ROOT = os.path.dirname(FACTORY_ROOT)
INPUT_DIR = os.path.join(FACTORY_ROOT, "input")

R370_LEGACY_ROOT_FILES = [
    "AI_LEARNING_TO_PACKAGE_CERTIFICATE.json",
    "BUYER_DISTRIBUTION_RELEASE_CERTIFICATE.json",
    "DISTRIBUTION_CANONICAL_MANIFEST.json",
    "FINAL_BUYER_RELEASE_ID.json",
    "FINAL_DISTRIBUTION_VERIFICATION_CERTIFICATE.json",
    "FINAL_RELEASE_ANCHOR_REPORT.json",
    "FINAL_RELEASE_OBJECT.json",
    "SOURCE_RELEASE_MANIFEST.json",
    "RELEASE_INTEGRITY_REPORT.md",
]

PACKAGE_JSON_ROLES = {
    "PACKAGE_MANIFEST.json": "identity + file hashes",
    "ENGINEERING_TRACEABILITY.json": "design-input/output traceability chains",
    "MATURITY_BASIS.json": "maturity basis evidence IDs",
    "COMMERCIAL_EVIDENCE.json": "market/competitor/precedent/IP (provenance-disciplined)",
    "EQUATION_REGISTRY.json": "canonical equations + typeset registry",
    "UNKNOWN_ROADMAP.json": "classified unknowns with resolution actions",
    "VALIDATION_ECONOMICS.json": "cost NOT_ESTABLISHED + time ranges with basis",
    "LOOP_STATE.json": "loop verification state + event queues",
    "V2_MUTATION_ADDENDUM.json": "V1->V2 mutation trail (external-evidence driven)",
    "V3_MUTATION_ADDENDUM.json": "R394 canonical correction trail (exact-match, auditable)",
    "MECHANISM_EVIDENCE.json": "R394 5-way classified mechanism evidence + the four-question record",
    "R394_RELEASE_GATES.json": "R394 hard release gates (mechanism-geometry, decisive experiment, self-containment, equation structure)",
    "EXTERNAL_CONSULTANT_EVIDENCE/CONSULTANT_RECONCILIATION_REPORT.json": "referenced V2 mutation evidence basis, shipped in-package (self-containment)",
    "MODEL/VALIDATION_STATES.json": "R394 CAD/engineering validation state split (never one blob)",
    "MODEL/3D_DESIGN_STATUS.json": "R381 honest 3D classification (REQUIRED / NOT_APPLICABLE)",
    "MODEL/PARAMETRIC_MODEL_SOURCE.py": "R381 parametric build program — source of truth",
    "MODEL/MODEL_MANIFEST.json": "R381 model identity, kernel, artifacts + sha256, views",
    "MODEL/PARAMETERS.json": "R381 parameter map + envelopes + record bindings",
    "MODEL/CONSTRAINTS.json": "R381 geometric constraints, interference pairs, material compatibility",
    "MODEL/GEOMETRY_VALIDATION_REPORT.json": "R381 deterministic G1-G8 validation on the built solid",
    "MODEL/KEY_DIMENSIONS.json": "R381 measured geometry + computation logs",
    "MODEL/ENGINEERING_PROVENANCE.json": "R381 per-parameter provenance chains",
    "MODEL/DESIGN_LINEAGE.json": "R381 base -> mutation -> child lineage",
    "MODEL/IMPROVEMENT_LOOP_EVIDENCE.json": "R381 mutation -> rebuild -> evaluate -> KEEP/KILL",
    "MODEL/README.json": "R381 model directory readme",
}


def _external_references(portfolio_root: str) -> dict:
    """R394: immutable external references for artifacts a package
    references but does not carry (CEO option 2). The portfolio-root
    identity registry is pinned by sha256 here AND by the canonical
    release manifest (Art. XXXIX chain)."""
    out = {}
    reg = os.path.join(portfolio_root, "PORTFOLIO_IDENTITY_REGISTRY.json")
    if os.path.isfile(reg):
        out["PORTFOLIO_IDENTITY_REGISTRY.json"] = {
            "location": "portfolio root (ships with the distribution)",
            "sha256": sha256_file(reg),
            "pinned_by": "CANONICAL_RELEASE_MANIFEST.json (Art. XXXIX "
                         "release chain)",
            "note": "immutable external reference with recorded "
                    "integrity hash — the buyer can verify the bytes "
                    "independently",
        }
    return out


def _package_files_recursive(pdir):
    """Relative paths of every FILE under the package dir (MODEL/
    included). Sorted; directories themselves are not entries."""
    out = []
    for root, _dirs, files in os.walk(pdir):
        for f in files:
            out.append(os.path.relpath(os.path.join(root, f), pdir))
    return sorted(out)


def _write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def build(portfolio_root, work_dir=None):
    work = work_dir or os.path.join(ENGINE_ROOT, "premium_package_factory",
                                    "output", "r371_v5_build")
    os.makedirs(work, exist_ok=True)
    os.makedirs(os.path.join(portfolio_root, "DOWNLOAD"), exist_ok=True)

    styles = get_styles()
    init_styles(styles)
    _init_dossier_styles(styles)

    # 1-2. canonical + derived artifacts ------------------------------------
    print("[R371] loading canonical packages ...")
    packages = load_all_packages()
    headlines = {r["package_id"]: r for r in json.load(
        open(os.path.join(INPUT_DIR, "headlines_r371.json"), encoding="utf-8"))["packages"]}

    comm = {p.pkg_id: build_commercial_evidence(p) for p in packages}
    eqs = {p.pkg_id: build_equation_registry(p) for p in packages}
    eq_validations = {p.pkg_id: validate_registry(eqs[p.pkg_id], p)
                      for p in packages}
    for p in packages:
        # R372-3: validation ships inside the buyer-visible registry
        eqs[p.pkg_id]["r372_validation"] = eq_validations[p.pkg_id]
    # R374-2 + R374-3: three-level validation status + per-symbol unit
    # status (SOURCE_BACKED / UNKNOWN with resolution paths)
    from premium_package_factory.r374.equation_status import \
        attach_r374_status
    for p in packages:
        attach_r374_status(eqs[p.pkg_id], p)
    roads = {p.pkg_id: build_unknown_roadmap(p) for p in packages}
    # R394: the decisive work package derives from the recorded kill
    # condition (never build_plan[0]); the derivation ships in the JSON.
    ecos = {p.pkg_id: build_validation_economics(
        p, headlines[p.pkg_id].get("kill_if", "")) for p in packages}
    loops = {p.pkg_id: build_loop_state(p) for p in packages}
    loop_summary = portfolio_loop_summary(packages)
    ranking = build_ranking(packages, headlines, roads)
    # R372-1: explicit traceability semantics per package
    # R394: + genuine identifier/phrase bindings and the extended
    # chain slots (mechanism feature, parameter, experiment, decision)
    traces = {}
    for p in packages:
        legacy = os.path.join(INPUT_DIR, "legacy_json", p.num,
                              "ENGINEERING_TRACEABILITY.json")
        trace = build_traceability_json(p, legacy)
        from premium_package_factory.r394.traceability import attach \
            as _r394_attach_trace
        traces[p.pkg_id] = _r394_attach_trace(p, trace)
    # R374-1: truth model — chain-level four states + the UNKNOWN-is-
    # not-verified declaration inside the shipped artifact
    from premium_package_factory.r374.traceability_truth import \
        attach_truth_model
    for p in packages:
        attach_truth_model(traces[p.pkg_id], p)
    # R372-2: experiment-diagram specs validated at build time (fail closed)
    exp_specs = {p.pkg_id: experiment_diagram_spec(p, headlines[p.pkg_id])
                 for p in packages}
    for p in packages:
        spec_check = validate_experiment_spec(exp_specs[p.pkg_id], p,
                                              headlines[p.pkg_id])
        if not spec_check["ok"]:
            raise RuntimeError(
                f"experiment diagram spec invalid for {p.pkg_id}: "
                f"{spec_check['failures']}")

    # 3. visuals --------------------------------------------------------------
    print("[R372] generating technical visuals ...")
    mech_dir = os.path.join(work, "mechanism")
    mech_pngs = build_all_mechanism_diagrams(mech_dir)
    exp_dir = os.path.join(work, "experiment")
    os.makedirs(exp_dir, exist_ok=True)
    exp_pngs = {}
    for p in packages:
        exp_pngs[p.pkg_id] = build_experiment_diagram(
            p, headlines[p.pkg_id],
            os.path.join(exp_dir, f"{p.num}_experiment_setup.png"),
            spec=exp_specs[p.pkg_id])

    # 4. per-package render -----------------------------------------------------
    print("[R371] rendering 15 packages ...")
    # R375-5/6: every rendered page is rasterized to PNG under
    # INTERNAL_QA/rendered_pages/ — the actual rendered page is the audit
    # object. GEOMETRIC_QA + RENDERED_PAGE_QA + content completeness are
    # ALL blocking before the package ZIP is created.
    qa_root = os.path.join(portfolio_root, "INTERNAL_QA", "rendered_pages")
    qa_report = {}
    for p in packages:
        h = headlines[p.pkg_id]
        folder = p.folder
        pdir = os.path.join(portfolio_root, "DOWNLOAD", folder)
        if os.path.isdir(pdir):
            shutil.rmtree(pdir)
        os.makedirs(pdir)

        bd.render_package_readme(p, h, [], os.path.join(pdir, "00_PACKAGE_README.pdf"))
        bd.render_exec_brief(p, h, comm[p.pkg_id], ecos[p.pkg_id], loops[p.pkg_id],
                             os.path.join(pdir, "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf"))
        bdd.render_engineering_dossier(
            p, h, eqs[p.pkg_id], roads[p.pkg_id], comm[p.pkg_id],
            ecos[p.pkg_id], loops[p.pkg_id], mech_pngs[p.pkg_id],
            exp_pngs[p.pkg_id],
            os.path.join(pdir, "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf"))
        bd.render_buyer_card(p, h, comm[p.pkg_id], ecos[p.pkg_id], loops[p.pkg_id],
                             os.path.join(pdir, "03_BUYER_DECISION_CARD.pdf"))
        bd.render_evidence_summary(p, h, loops[p.pkg_id],
                                   os.path.join(pdir, "04_EVIDENCE_SUMMARY.pdf"))
        bd.render_transfer_manifest(p, h, comm[p.pkg_id],
                                    os.path.join(pdir, "05_TRANSFER_MANIFEST.pdf"))

        # V3 BUILD GATE + R375-5/6 RENDERED-PAGE GATE: the package ZIP is
        # not created unless every rendered PDF passes GEOMETRIC_QA and
        # RENDERED_PAGE_QA (blocking by exception). PNG page artifacts
        # persist for audit under INTERNAL_QA/rendered_pages/.
        pkg_qa = verify_package(
            pdir, png_dir=os.path.join(qa_root, folder))

        # R375-1/10 content completeness: every authoritative canonical
        # string must appear IN FULL in the package's PDF text (cell-aware
        # extraction — see pdf_haystacks).
        from premium_package_factory.gates.render_verification import (
            pdf_haystacks)
        streams = []
        for f in sorted(os.listdir(pdir)):
            if f.endswith(".pdf"):
                streams.extend(pdf_haystacks(os.path.join(pdir, f)))
        exp = build_content_expectations(p, h, roads[p.pkg_id])
        ok, failures = content_completeness(exp, streams)
        if not ok:
            raise RuntimeError(
                f"R375 content completeness FAILED for {p.pkg_id}: "
                f"{len(failures)} authoritative strings missing/truncated "
                f"from the PDF set: "
                + "; ".join(f"{f['field']} "
                             f"(head: {f['expected_head'][:60]!r})"
                             for f in failures[:8]))
        qa_report[folder] = {"geometric_and_rendered": "PASS",
                             "content_completeness": {
                                 "expected": len(exp), "missing": 0}}
        print(f"   {p.num} QA: geometric+rendered+completeness PASS "
              f"({len(exp)} authoritative strings verified in full)")

        # machine-readable layer
        # R381: the 3D engineering design layer runs FIRST here so its
        # verdict can enter the traceability + manifest records below.
        # Honest outcomes only (CAD_VALIDATED / NOT_APPLICABLE /
        # BLOCKED_*); a BLOCKED/NOT_APPLICABLE status never kills the
        # package build (the buyer package is the deliverable, the 3D
        # layer is evidence). Fail-closed on CRASH (a silent skip would
        # fabricate a package without its design layer). CAD crashes are
        # recorded honestly as BLOCKED with the exception, never hidden.
        try:
            model_summary = build_model_layer(p.pkg_id, pdir,
                                              work_dir=work)
        except Exception as exc:  # noqa: BLE001
            from premium_package_factory.r381.portfolio_cad import (
                R381_VERSION, _write_json as _r381_write_json, MODEL_DIR)
            import traceback as _tb
            mdir = os.path.join(pdir, MODEL_DIR)
            os.makedirs(mdir, exist_ok=True)
            _r381_write_json(os.path.join(
                mdir, "3D_DESIGN_STATUS.json"), {
                "artifact": "3D_DESIGN_STATUS",
                "r381_version": R381_VERSION,
                "package_id": p.pkg_id,
                "classification": "3D_PHYSICAL_DESIGN_REQUIRED",
                "3d_design_status": "BLOCKED_PIPELINE_EXCEPTION",
                "reason": (f"the R381 CAD layer raised {type(exc).__name__}: "
                           f"{exc} — recorded, not hidden (Art. XV)"),
                "traceback_tail": _tb.format_exc().strip().splitlines()[-6:],
            })
            model_summary = {"status": "BLOCKED_PIPELINE_EXCEPTION",
                             "files": [], "model_id": None}
        print(f"   {p.num} R381 3D: {model_summary.get('status')}")

        # R372-1: ENGINEERING_TRACEABILITY.json now carries explicit
        # per-chain semantics (legacy R370 record preserved inside it)
        # R381: the traceability record gains the 3D-design chain summary
        # (the full per-parameter chain ships in MODEL/ENGINEERING_PROVENANCE)
        _trace = traces[p.pkg_id]
        _trace["three_d_design"] = {
            "r381_version": model_summary.get("r381_version", "1.0.0"),
            "classification": (model_summary.get("classification") or
                               {}).get("classification"),
            "status": model_summary.get("status"),
            "model_id": model_summary.get("model_id"),
            "improvement_loop_outcome": model_summary.get("loop_outcome"),
            # R394 self-containment: the provenance pointer is recorded
            # only when the file actually exists (software-only packages
            # are 3D_NOT_APPLICABLE and carry no ENGINEERING_PROVENANCE)
            "provenance": ("MODEL/ENGINEERING_PROVENANCE.json"
                           if os.path.exists(os.path.join(
                               pdir, "MODEL",
                               "ENGINEERING_PROVENANCE.json"))
                           else None),
            "chain_shape": ("TECHNICAL_STATE -> parameter -> CAD feature -> "
                            "derived geometry -> measured geometry -> "
                            "validation result"),
            "evidence_class": "COMPUTATIONAL_RESULT",
            "render_is_not_validation": True,
        }
        _write_json(os.path.join(pdir, "ENGINEERING_TRACEABILITY.json"),
                    _trace)
        legacy_num = os.path.join(INPUT_DIR, "legacy_json", p.num)
        for fn in ("MATURITY_BASIS.json",):
            src = os.path.join(legacy_num, fn)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(pdir, fn))
        _write_json(os.path.join(pdir, "COMMERCIAL_EVIDENCE.json"), comm[p.pkg_id])
        _write_json(os.path.join(pdir, "EQUATION_REGISTRY.json"), eqs[p.pkg_id])
        _write_json(os.path.join(pdir, "UNKNOWN_ROADMAP.json"), roads[p.pkg_id])
        _write_json(os.path.join(pdir, "VALIDATION_ECONOMICS.json"), ecos[p.pkg_id])
        _write_json(os.path.join(pdir, "LOOP_STATE.json"), loops[p.pkg_id])
        # V2 mutation trail (preserved verbatim from the engine input
        # snapshot — never read from the live portfolio tree, which this
        # build wipes and rebuilds)
        v2src = os.path.join(INPUT_DIR, "v2_mutations",
                             f"V2_MUTATION_ADDENDUM_{p.pkg_id}.json")
        if os.path.exists(v2src):
            shutil.copy2(v2src, os.path.join(pdir, "V2_MUTATION_ADDENDUM.json"))
            cert_src = os.path.join(INPUT_DIR, "v2_mutations")
            for fcert in os.listdir(cert_src):
                if (fcert.startswith("PACKAGE_MUTATION_CERTIFICATE")
                        and f"_V2.json" in fcert
                        and p.pkg_id in fcert):
                    shutil.copy2(os.path.join(cert_src, fcert),
                                 os.path.join(pdir, fcert))

        # ------------------ R394 truth-and-semantics layer ------------------
        # (a) MECHANISM_EVIDENCE.json — the 5-way classified evidence +
        #     the four-question record (statements recorded per package;
        #     absent -> honest None, never synthesized)
        from premium_package_factory.r394.evidence_classes import (
            build_mechanism_evidence)
        _stmt_path = os.path.join(
            INPUT_DIR, "v3_corrections",
            f"{p.pkg_id}_MECHANISM_EVIDENCE_STATEMENTS.json")
        _stmt = None
        if os.path.exists(_stmt_path):
            with open(_stmt_path, encoding="utf-8") as _sf:
                _stmt = json.load(_sf)
        _write_json(os.path.join(pdir, "MECHANISM_EVIDENCE.json"),
                    build_mechanism_evidence(p, _stmt))
        # (b) MODEL/VALIDATION_STATES.json — the CAD/engineering split
        from premium_package_factory.r394.validation_states import (
            derive_validation_states, compact_epistemic_line)
        _vstates = derive_validation_states(
            p, os.path.join(pdir, "MODEL"), eqs[p.pkg_id],
            loops[p.pkg_id])
        _write_json(os.path.join(pdir, "MODEL", "VALIDATION_STATES.json"),
                    _vstates)
        # (c) V3 correction trail ships as the audit record
        if p.v3_trail:
            _write_json(os.path.join(pdir, "V3_MUTATION_ADDENDUM.json"),
                        p.v3_trail)
        # (d) self-containment: the V2 mutation certificate references
        # EXTERNAL_CONSULTANT_EVIDENCE/CONSULTANT_RECONCILIATION_REPORT.json
        # — ship the referenced artifact INSIDE the package at the same
        # relative path so the reference resolves (CEO directive 12)
        _consultant_src = os.path.join(
            ENGINE_ROOT, "EXTERNAL_CONSULTANT_EVIDENCE",
            "CONSULTANT_RECONCILIATION_REPORT.json")
        _certs = [f for f in os.listdir(pdir)
                  if f.startswith("PACKAGE_MUTATION_CERTIFICATE")]
        if _certs and os.path.exists(_consultant_src):
            with open(os.path.join(pdir, _certs[0]), encoding="utf-8") \
                    as _cf:
                _cert = json.load(_cf)
            if "EXTERNAL_CONSULTANT_EVIDENCE" in json.dumps(_cert):
                _dest = os.path.join(pdir, "EXTERNAL_CONSULTANT_EVIDENCE")
                os.makedirs(_dest, exist_ok=True)
                shutil.copy2(_consultant_src, os.path.join(
                    _dest, "CONSULTANT_RECONCILIATION_REPORT.json"))
        # (e) the four HARD release gates — FAIL blocks the ZIP (raise)
        from premium_package_factory.r394.release_gates import run_all_gates
        _manifest_pre = {
            "external_references": _external_references(portfolio_root),
        }
        _gates = run_all_gates(
            p, pdir, os.path.join(pdir, "MODEL"), ecos[p.pkg_id],
            eqs[p.pkg_id], headlines[p.pkg_id].get("kill_if", ""),
            manifest_dict=_manifest_pre)
        _write_json(os.path.join(pdir, "R394_RELEASE_GATES.json"), _gates)
        if _gates["overall"] != "PASS":
            raise RuntimeError(
                f"R394 release gates FAILED for {p.pkg_id}: "
                + "; ".join(
                    f"{g['gate']}={g['state']} "
                    f"({len(g.get('violations', []))} violation(s))"
                    for g in _gates["gates"] if g["state"] == "FAIL"))
        print(f"   {p.num} R394 gates: PASS "
              f"(epistemic line: "
              f"{' / '.join(compact_epistemic_line(_vstates))})")

        # package manifest (identity-linked) — files hashed from disk
        # R381: MODEL/ files are first-class manifest entries (recursive
        # walk; subdirectory files listed as MODEL/<name>)
        files = []
        for f in _package_files_recursive(pdir):
            if f == "PACKAGE_MANIFEST.json":
                continue
            files.append({
                "file": f,
                "role": PACKAGE_JSON_ROLES.get(f, _model_artifact_role(f)),
                "sha256": sha256_file(os.path.join(pdir, f)),
            })
        pm = {
            "portfolio_number": p.num,
            "package_id": p.pkg_id,
            "technology_name": h["technology_name"],
            "package_version": p.version,
            "technology_maturity": "ENGINEERING_DEFINITION",
            "dossier_maturity": "COMPLETE_FOR_CURRENT_STAGE",
            "transfer_posture": "SPONSORED_VALIDATION",
            "loop_verification_state": p.loop_state,
            "has_v2_addendum": bool(p.addendum),
            "has_v3_addendum": bool(p.v3_trail),
            "epistemic_maturity_line": compact_epistemic_line(_vstates),
            "validation_states": {
                k: (v.get("state") if isinstance(v, dict) else v)
                for k, v in _vstates.items()
                if isinstance(v, dict) and "state" in v
            },
            "external_references": _external_references(portfolio_root),
            "three_d_design": {
                "classification": (model_summary.get("classification") or
                                   {}).get("classification"),
                "status": model_summary.get("status"),
                "model_id": model_summary.get("model_id"),
                "improvement_loop_outcome": model_summary.get("loop_outcome"),
                "directory": "MODEL/",
                "policy": (
                    "CEO R381: honest classification from the canonical "
                    "record; geometry verdicts are MEASURED on the built "
                    "solid; all 3D content is COMPUTATIONAL_RESULT with "
                    "computation logs; a render is presentation, never "
                    "validation (Art. XXVIII/XXXVIII)."),
            },
            "identity_policy": (
                "Portfolio number and historical package ID are bound in "
                "PORTFOLIO_IDENTITY_REGISTRY.json (portfolio root; sha256 "
                "pinned in this manifest's external_references and in "
                "CANONICAL_RELEASE_MANIFEST.json) and never renumbered."),
            "files": files,
            "external_evidence_count": len(p.external_precedent),
            "engineering_artifact_count": len(p.build_plan),
        }
        _write_json(os.path.join(pdir, "PACKAGE_MANIFEST.json"), pm)

        # 5. package zip built from the folder (byte-verified by acceptance)
        zpath = os.path.join(portfolio_root, "DOWNLOAD", f"{folder}.zip")
        if os.path.exists(zpath):
            os.remove(zpath)
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in _package_files_recursive(pdir):
                _zip_add(zf, os.path.join(pdir, f), f)
        print(f"   {p.num} {p.pkg_id} ({p.version}) done")

    # README of each package needs the final file list; rebuild readmes now
    for p in packages:
        h = headlines[p.pkg_id]
        pdir = os.path.join(portfolio_root, "DOWNLOAD", p.folder)
        pm = json.load(open(os.path.join(pdir, "PACKAGE_MANIFEST.json"),
                            encoding="utf-8"))
        bd.render_package_readme(p, h, pm["files"],
                                 os.path.join(pdir, "00_PACKAGE_README.pdf"))
        verify_pdf_rendering(os.path.join(pdir, "00_PACKAGE_README.pdf"))
        # update manifest hash for the re-rendered readme
        for f in pm["files"]:
            if f["file"] == "00_PACKAGE_README.pdf":
                f["sha256"] = sha256_file(os.path.join(pdir, "00_PACKAGE_README.pdf"))
        _write_json(os.path.join(pdir, "PACKAGE_MANIFEST.json"), pm)
        # rebuild zip with final readme
        zpath = os.path.join(portfolio_root, "DOWNLOAD", f"{p.folder}.zip")
        os.remove(zpath)
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in _package_files_recursive(pdir):
                _zip_add(zf, os.path.join(pdir, f), f)

    # 5.5 R382: CEO PORTFOLIO DISPOSITION ---------------------------------
    # The buyer release becomes the 4 BUYER_PRIMARY packages (CEO
    # presentation order); the other 11 packages MOVE (byte-identical)
    # to HOLDING/ SPECIALIST_TRACK/ RETIRED/ with the disposition
    # record + frozen identity hashes at the portfolio root. The
    # pre-disposition release is snapshotted to RELEASE/history_r381/
    # (history is evidence, Art. XI).
    print("[R382] applying CEO portfolio disposition ...")
    from premium_package_factory.r382.disposition import (
        apply_portfolio_disposition)
    disposition_summary = apply_portfolio_disposition(
        portfolio_root,
        statuses={p.pkg_id: "V2" for p in packages if p.addendum})
    print(f"   buyer release (CEO order): "
          f"{disposition_summary['buyer_primary']}")

    # 6-8. buyer-scoped release documents ------------------------------------
    # ONE code path with the live-tree retrofit (r382.release_docs):
    # index/report/manifests/README/master ZIP regenerated over the
    # BUYER_PRIMARY subset; the full 15-technology overview moves to
    # the INTERNAL layer.
    print("[R382] regenerating buyer release documents ...")
    from premium_package_factory.r382.release_docs import (
        regenerate_buyer_release_documents)
    release_summary = regenerate_buyer_release_documents(
        portfolio_root, packages, headlines, ranking, loop_summary,
        traces, eq_validations, qa_root=qa_root)
    # R375-5/6 per-package QA verdict persists exactly as before
    write_report(qa_report, os.path.join(
        portfolio_root, "INTERNAL_QA", "R375_RENDER_QA.json"))
    print(f"   master ZIP: {release_summary['master_zip_sha256'][:16]}...")

    # 9. history preservation ---------------------------------------------------------
    hist = os.path.join(portfolio_root, "RELEASE", "history_r370")
    os.makedirs(hist, exist_ok=True)
    for fn in R370_LEGACY_ROOT_FILES:
        src = os.path.join(portfolio_root, fn)
        if os.path.exists(src):
            shutil.move(src, os.path.join(hist, fn))
    for legacy_dir in ("FULL_DOSSIERS", "BUYER_OUTREACH"):
        d = os.path.join(portfolio_root, legacy_dir)
        if os.path.isdir(d):
            shutil.rmtree(d)
            print(f"[R371] removed duplicate tree {legacy_dir}/ "
                  f"(DOWNLOAD/ is the single authoritative release layer; "
                  f"history preserved in git)")

    print("[R371] V5 build complete:", portfolio_root)
    return {"portfolio_root": portfolio_root, "ranking": ranking,
            "loop_summary": loop_summary}


def _model_artifact_role(rel_path):
    """R381: role for MODEL/ artifacts not in the static role table
    (STEP/STL/GLB/SVG derivatives of the parametric model)."""
    if rel_path.startswith("MODEL/"):
        ext = rel_path.rsplit(".", 1)[-1].lower() if "." in rel_path else ""
        return {
            "step": "3D engineering exchange derivative (B-rep, hashed)",
            "stl": "mesh derivative (trimesh watertight-checked)",
            "glb": "presentation/render derivative (render != validation)",
            "svg": "rendered engineering view (presentation only)",
        }.get(ext, "3D design artifact (MODEL/)")
    return "buyer document"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--portfolio-root", default=bp.PORTFOLIO_ROOT_DEFAULT)
    ap.add_argument("--work-dir", default=None)
    args = ap.parse_args()
    build(args.portfolio_root, args.work_dir)


if __name__ == "__main__":
    main()
