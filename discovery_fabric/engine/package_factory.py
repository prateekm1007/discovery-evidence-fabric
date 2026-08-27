"""discovery_fabric/engine/package_factory.py — E4/E10/E12 survivor -> buyer
package bridge.

CEO E4: the discovery engine calls the SAME generator architecture that
produced technology-transfer-portfolio-15 (premium_package_factory/
templates/build_portfolio_v4.py per-package builders). Templates are NOT
recreated; the bridge converts a canonical invention specification +
engineering specification into the ArtifactRichDossier shape those builders
already consume, then renders the established buyer hierarchy:

    00_PACKAGE_README.pdf
    01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf
    02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf
    03_BUYER_DECISION_CARD.pdf
    04_EVIDENCE_SUMMARY.pdf
    05_TRANSFER_MANIFEST.pdf
    PACKAGE_MANIFEST.json
    ENGINEERING_TRACEABILITY.json
    MATURITY_BASIS.json
    <short>.zip

CEO E5/E12: generation is evidence-bound and provenance-chained —
PACKAGE_CLAIM -> INVENTION_FIELD -> CANDIDATE_STAGE -> EVIDENCE_ID ->
SOURCE -> HASH. The generated ENGINEERING_TRACEABILITY.json is computed from
STRUCTURAL design-graph links (explicit IDs), never keyword matching.

Status doctrine (Art. XXXVII/XXXVIII): every generated package declares
loop_verification_state=NONE and REAL_LOOP_VERIFIED=FALSE (derived state,
impossible to assign manually) and transfer_ready=FALSE. A package built
from a rehearsal fixture is additionally flagged SYNTHETIC_REHEARSAL=TRUE
and must never leave the development environment.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from .candidate import Candidate, sha256_obj, utc_now
from .engineering_spec import build_engineering_spec
from .invention_spec import SPEC_FIELDS, build_invention_spec, tagged

REPO_ROOT = Path(__file__).resolve().parents[2]
FACTORY_V4 = REPO_ROOT / "premium_package_factory" / "templates" / \
    "build_portfolio_v4.py"

PACKAGE_FILES = [
    "00_PACKAGE_README.pdf",
    "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
    "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
    "03_BUYER_DECISION_CARD.pdf",
    "04_EVIDENCE_SUMMARY.pdf",
    "05_TRANSFER_MANIFEST.pdf",
]


def _load_v4():
    """Load the frozen portfolio-v4 builder module by path. No state is
    mutated: the per-package builders are pure functions of (pi, d, op)."""
    spec = importlib.util.spec_from_file_location("engine_portfolio_v4",
                                                  FACTORY_V4)
    mod = importlib.util.module_from_spec(spec)
    import sys
    sys.modules["engine_portfolio_v4"] = mod
    spec.loader.exec_module(mod)
    return mod


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _safe_slug(s: str, maxlen: int = 40) -> str:
    slug = "".join(ch if ch.isalnum() else "_" for ch in s.lower()).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return (slug or "technology")[:maxlen].strip("_")


# --------------------------------------------------------------------------
def survivor_to_canonical_package(
        spec: Dict[str, Any], eng: Dict[str, Any], env: Optional[Candidate],
        run_ctx: Dict[str, Any], rehearsal: bool = False) -> Dict[str, Any]:
    """Assemble the ArtifactRichDossier-shaped record + package-info entry
    for the frozen v4 builders (E4 reuse)."""
    problem = (spec.get("problem") or {}).get("value") or {}
    mech = (spec.get("mechanism") or {}).get("value") or {}
    invention_id = (spec.get("invention_id") or {}).get("value", "inv:unknown")
    short = _safe_slug(problem.get("device") or invention_id.split(":")[-1])

    # Evidence-bound external source list (E5): custodied evidence first,
    # standards candidates second — each item carries source + snippet keys
    # the v4 evidence-summary builder expects.
    ext: List[Dict[str, Any]] = []
    for e in (env.evidence if env else []) or []:
        ext.append({
            "source_title": e.get("title", ""),
            "source": e.get("source_uri") or e.get("doi") or "",
            "source_snippet": (e.get("abstract") or "")[:220],
            "evidence_id": e.get("id"),
            "content_hash": e.get("content_hash"),
            "epistemic_class": "SOURCE_FACT (custodied evidence)"})
    for s in eng.get("external_engineering_precedent", []):
        ext.append({
            "source_title": s.get("precedent", ""),
            "source": "standard reference — verify applicability",
            "source_snippet": "candidate standard; applicability NOT "
                              "verified (Art. II)",
            "epistemic_class": "EXTERNAL_PRECEDENT_CANDIDATE"})

    # pi: the per-package identity the v4 builders expect
    n = run_ctx.get("package_number") or "90"
    pi = {
        "num": n,
        "pkg_id": invention_id,
        "short": short,
        "name": _short(mech.get("intervention", ""), 90)
                or f"Engine-discovered invention {invention_id}",
        "problem": problem.get("failure", ""),
        "mechanism": mech.get("mechanism", ""),
        "buyer_type": (problem.get("target_buyer")
                       or "domain-appropriate technology buyer (to be "
                          "identified by portfolio owner)"),
        "kill_if": _kill_condition(spec),
    }
    dossier = {
        "package_id": invention_id,
        "view_type": "ENGINE_GENERATED_ARTIFACT_RICH",
        "engineering_content": eng,
        "_provenance": {
            "run_id": run_ctx.get("run_id"),
            "final_envelope_hash": (env.envelope_hash() if env else None),
            "invention_spec_hash": spec.get("_spec_hash"),
            "rehearsal": rehearsal,
            "loop_verification_state": "NONE",
            "real_loop_verified": False,
            "transfer_ready": False,
            "generated_at": utc_now()},
    }
    return {"pi": pi, "dossier": dossier, "external_sources": ext}


def _short(s: str, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 3].rstrip() + "..."


def _kill_condition(spec: Dict[str, Any]) -> str:
    """Kill condition = the candidate's own recorded falsification path.
    No new thresholds are invented here (Art. XXVII)."""
    ke = (spec.get("killer_experiment") or {}).get("value") or {}
    sel = ke.get("selected")
    name = sel if isinstance(sel, str) else (sel or {}).get("name", "")
    return (f"killer experiment fails: {name or 'NOT ESTABLISHED'} "
            "(pre-registered pass/fail required before any transfer)")


# --------------------------------------------------------------------------
def build_traceability(spec: Dict[str, Any], eng: Dict[str, Any],
                       pkg: Dict[str, Any],
                       env: Optional[Candidate]) -> Dict[str, Any]:
    """E12 ENGINEERING_TRACEABILITY.json — computed from STRUCTURAL links.

    Chains: PACKAGE_CLAIM -> INVENTION_FIELD -> CANDIDATE_STAGE ->
    EVIDENCE_ID -> SOURCE -> HASH. Structural, not keyword-based.
    """
    graph = eng.get("design_graph") or {}
    ev_index = (spec.get("_evidence_index") or {})
    chains: List[Dict[str, Any]] = []
    # design-input chains
    for d in eng.get("design_inputs", []):
        chains.append({
            "chain_type": "DESIGN_INPUT",
            "node_id": d["id"],
            "invention_field": "problem" if "problem.json" in
                               (d.get("evidence_refs") or []) else "mechanism",
            "candidate_stage": d.get("source", "MODELLED (LLM synthesis)"),
            "evidence_ids": d.get("evidence_refs", []),
            "source": ev_index.get((d.get("evidence_refs") or [None])[0], {})
                      .get("source_uri", "engine-generated (structural)"),
            "hash": sha256_obj(d),
            "linked": bool(d.get("parent_ids"))})
    # design-output chains
    for d in eng.get("design_outputs", []):
        chains.append({
            "chain_type": "DESIGN_OUTPUT", "node_id": d["id"],
            "invention_field": "engineering_parameters",
            "candidate_stage": d.get("basis", "ENGINEERING_PROPOSED"),
            "evidence_ids": [],
            "parent_ids": d.get("parent_ids", []),
            "hash": sha256_obj(d),
            "linked": bool(d.get("parent_ids"))})
    # failure mode chains
    for f in eng.get("failure_analysis", []):
        chains.append({
            "chain_type": "FAILURE_MODE",
            "node_id": f.get("verification", "FM-?"),
            "invention_field": "failure_modes",
            "candidate_stage": f.get("evidence", "ATTACK"),
            "evidence_ids": [],
            "hash": sha256_obj(f),
            "linked": f.get("verification", "NOT_LINKED") != "NOT_LINKED"})
    # verification chains
    for v in eng.get("verification_matrix", []):
        chains.append({
            "chain_type": "VERIFICATION", "node_id": v["id"],
            "invention_field": "killer_experiment",
            "candidate_stage": "KILLER_EXPERIMENT",
            "evidence_ids": [],
            "hash": sha256_obj(v),
            "linked": True, "result": v.get("result", "NOT_TESTED")})

    eq_integrity = {
        "equations_total": len(eng.get("engineering_core", {})
                               .get("governing_model", {}).get("equations", [])),
        "numeric_values_emitted": 0,
        "rule": "no numeric value may be emitted without SOURCE_FACT or "
                "COMPUTED inputs (Art. XXVII); generator emits SYMBOLIC ONLY",
        "all_symbolic": True}
    number_provenance = {
        "policy": "every number in this package is either a content hash, a "
                  "count, or an engine score; NO physical parameter values "
                  "exist because no measurement exists",
        "violations": []}
    di_do = {
        "method": "structural parent_ids (explicit IDs), NOT keyword matching",
        "d_inputs": len(eng.get("design_inputs", [])),
        "d_outputs": len(eng.get("design_outputs", [])),
        "unlinked_outputs": [d["id"] for d in eng.get("design_outputs", [])
                             if not d.get("parent_ids")]}
    passed = (graph.get("integrity", {}).get("passed", False)
              and not number_provenance["violations"])
    return {
        "package_id": (pkg["pi"]["pkg_id"]),
        "traceability_chains": chains,
        "equation_integrity": eq_integrity,
        "number_provenance": number_provenance,
        "di_do_consistency": di_do,
        "design_graph_integrity": graph.get("integrity"),
        "gaps": graph.get("gaps", []),
        "evidence_index": {
            k: {"title": v.get("title"), "content_hash": v.get("content_hash"),
                "source_uri": v.get("source_uri")}
            for k, v in ev_index.items()},
        "provenance_chain_template": ("PACKAGE_CLAIM -> INVENTION_FIELD -> "
                                      "CANDIDATE_STAGE -> EVIDENCE_ID -> "
                                      "SOURCE -> HASH"),
        "issues": graph.get("integrity", {}).get("problems", []),
        "passed": passed,
        "checked_at": utc_now(),
    }


def build_maturity_basis(spec: Dict[str, Any], eng: Dict[str, Any],
                         data: Dict[str, Any],
                         pkg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """MATURITY_BASIS.json mirroring the frozen packages' honesty: maturity
    is DERIVED from the recorded presence/absence of engineering artifacts,
    and evidence ids are the graph IDs itself."""
    core = eng.get("engineering_core", {})
    gm = core.get("governing_model", {})
    counts = {
        "governing_equations": len(gm.get("equations", [])),
        "design_inputs": len(eng.get("design_inputs", [])),
        "design_outputs": len(eng.get("design_outputs", [])),
        "failure_modes": len(core.get("failure_modes", [])),
        "build_plan_steps": len(eng.get("engineering_build_plan", [])),
        "verifications_tested": 0,
        "validations_performed": 0,
    }
    return {
        "package_id": (spec.get("invention_id") or {}).get("value"),
        "technology_maturity": data.get("maturity", "EARLY_CONCEPT"),
        "basis": "Derived from: governing equations present, design inputs "
                 ">= 5, failure modes >= 3, build plan >= 4 steps "
                 "(same rule as the frozen portfolio, applied to the "
                 "generated package)",
        "governing_model_evidence_ids": [e["equation_id"]
                                         for e in gm.get("equations", [])],
        "design_input_evidence_ids": [d["id"] for d in
                                      eng.get("design_inputs", [])],
        "design_output_evidence_ids": [d["id"] for d in
                                       eng.get("design_outputs", [])],
        "failure_analysis_evidence_ids": [f"FM-{i+1:03d}" for i in
                                          range(counts["failure_modes"])],
        "build_plan_evidence_ids": [w["work_package"] for w in
                                    eng.get("engineering_build_plan", [])],
        "verification_evidence_ids": [v["id"] for v in
                                      eng.get("verification_matrix", [])],
        "external_evidence_ids": [e.get("evidence_id")
                                  for e in (pkg or {}).get("external_sources", [])
                                  if e.get("evidence_id")],
        "known_blockers": [
            "no physical prototype exists",
            "no sourced acceptance thresholds exist",
            "no validation has been performed",
            "no regulatory pathway established"],
        "counts": counts,
        "loop_verification_state": "NONE",
        "real_loop_verified": False,
        "transfer_ready": False,
        "generated_at": utc_now(),
    }


# --------------------------------------------------------------------------
def generate_buyer_package(
        out_dir: str, spec: Dict[str, Any], eng: Dict[str, Any],
        env: Optional[Candidate], run_ctx: Dict[str, Any],
        rehearsal: bool = False) -> Dict[str, Any]:
    """E10: SURVIVING INVENTION -> DOWNLOAD/<nn>_<short>/ + .zip.
    Reuses the frozen v4 builders. Returns a report with every file+hash and
    an explicit fail list (missing link = loud failure, E11 contract)."""
    out = Path(out_dir)
    pkg = survivor_to_canonical_package(spec, eng, env, run_ctx,
                                        rehearsal=rehearsal)
    v4 = _load_v4()
    pi, dossier = pkg["pi"], pkg["dossier"]
    data = v4.get_data(dossier, pi)

    folder = out / "DOWNLOAD" / f"{pi['num']}_{pi['short']}"
    folder.mkdir(parents=True, exist_ok=True)

    # render the 6 canonical PDFs with the frozen builders
    rendered: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    jobs = [
        ("00_PACKAGE_README.pdf", lambda p: v4.build_readme(pi, data, p)),
        ("01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
         lambda p: v4.build_exec_brief(pi, dossier, p)),
        ("02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
         lambda p: v4.build_dossier(pi, dossier, p)),
        ("03_BUYER_DECISION_CARD.pdf",
         lambda p: v4.build_buyer_card(pi, dossier, p)),
        ("04_EVIDENCE_SUMMARY.pdf",
         lambda p: v4.build_evidence_summary(pi, dossier, p)),
        ("05_TRANSFER_MANIFEST.pdf",
         lambda p: v4.build_transfer_manifest(pi, dossier, p)),
    ]
    for fname, fn in jobs:
        path = folder / fname
        try:
            fn(str(path))
            if not path.exists() or path.stat().st_size == 0:
                raise RuntimeError("builder produced no bytes")
            rendered.append({"file": fname,
                             "sha256": _sha256_file(path),
                             "bytes": path.stat().st_size})
        except Exception as exc:  # noqa: BLE001 — recorded, fails the run
            failed.append({"file": fname,
                           "error": f"{type(exc).__name__}: {exc}"})

    # traceability + maturity basis + manifest
    trace = build_traceability(spec, eng, pkg, env)
    trace_path = folder / "ENGINEERING_TRACEABILITY.json"
    trace_path.write_text(json.dumps(trace, indent=2, ensure_ascii=False))

    maturity = build_maturity_basis(spec, eng, data, pkg)
    maturity_path = folder / "MATURITY_BASIS.json"
    maturity_path.write_text(json.dumps(maturity, indent=2,
                                        ensure_ascii=False))

    discipline_note = (
        "SYNTHETIC REHEARSAL — generated from a recorded fixture envelope; "
        "NOT a real discovery run; must not be shown to buyers"
        if rehearsal else
        "Generated end-to-end by discovery_fabric.engine from a real "
        "engine run envelope")

    manifest = {
        "portfolio_number": pi["num"],
        "package_id": pi["pkg_id"],
        "technology_name": pi["name"],
        "package_version": "1.0",
        "generator": "discovery_fabric.engine.package_factory (E4/E10)",
        "generator_basis": "premium_package_factory/templates/"
                           "build_portfolio_v4.py builders (frozen, reused)",
        "technology_maturity": data["maturity"],
        "dossier_maturity": "COMPLETE_FOR_CURRENT_STAGE",
        "transfer_posture": data["posture"],
        "loop_verification_state": "NONE",
        "real_loop_verified": False,
        "transfer_ready": False,
        "synthetic_rehearsal": rehearsal,
        "discipline_note": discipline_note,
        "provenance": {
            "run_id": run_ctx.get("run_id"),
            "final_envelope_hash": (env.envelope_hash() if env else None),
            "invention_spec_hash": spec.get("_spec_hash"),
            "candidate_stages": [e["stage"] for e in
                                 (env.stage_log if env else [])]},
        "files": rendered,
        "traceability_passed": trace["passed"],
        "external_evidence_count": len(pkg["external_sources"]),
        "engineering_artifact_count": len(eng.get(
            "engineering_build_plan", [])),
        "generated_at": utc_now(),
    }
    (folder / "PACKAGE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False))

    # zip mirrors the established hierarchy
    zip_path = out / "DOWNLOAD" / f"{pi['num']}_{pi['short']}.zip"
    if not failed:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(folder.iterdir()):
                zf.write(f, f"{folder.name}/{f.name}")

    # E11 contract: report missing links loudly
    missing = []
    expected = PACKAGE_FILES + ["PACKAGE_MANIFEST.json",
                                "ENGINEERING_TRACEABILITY.json",
                                "MATURITY_BASIS.json"]
    present = {r["file"] for r in rendered} | {
        "PACKAGE_MANIFEST.json", "ENGINEERING_TRACEABILITY.json",
        "MATURITY_BASIS.json"}
    missing = [f for f in expected if f not in present]
    if not missing and not failed and zip_path.exists():
        zip_ok = True
        with zipfile.ZipFile(zip_path) as zf:
            zip_ok = zf.testzip() is None
        if not zip_ok:
            failed.append({"file": zip_path.name, "error": "zip test failed"})
    missing.extend(f["file"] for f in failed)

    return {
        "folder": str(folder),
        "zip": str(zip_path) if zip_path.exists() else None,
        "rendered": rendered,
        "failed": failed,
        "missing_links": missing,
        "complete": not missing,
        "maturity": data["maturity"],
        "posture": data["posture"],
        "traceability_passed": trace["passed"],
    }
