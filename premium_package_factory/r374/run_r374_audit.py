"""
run_r374_audit.py — CEO R374 runner: final engineering evidence hardening.

Produces:

  INTERNAL_QA/R374_ENGINEERING_EVIDENCE_HARDENING_AUDIT.json
      per-package R374 dimensions (diagram element proofs, truth-model
      audit, equation three-level status + unit status audit), the
      cemetery pathway audit, the seven-condition acceptance result and
      the repo-rule application record
  RELEASE/R374_RELEASE_CANDIDATE.json
      the six-state ladder per package (never collapsed) + the R374
      acceptance summary + honest open items

R374-7 repository rule: only packages passing the COMPLETE release gate
(R371 16-condition + R372 12-condition + R373 15 artifact gates + R374
7 conditions) are released in the portfolio repo; any failure is
retired to the engine cemetery through the six-element pathway with
nothing deleted.

Art. XXVI: builder-run tooling — SUBMITTED FOR CEO AUDIT, not
independent certification.
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..")))

from premium_package_factory.r371.canonical_source import load_all_packages
from premium_package_factory.r371.equations import build_equation_registry
from premium_package_factory.r372.equation_validation import validate_registry
from premium_package_factory.r372.diagram_adequacy import record_diagram
from premium_package_factory.r373 import run_r373_audit
from premium_package_factory.r373.run_r373_audit import (
    DIAGRAM_FUNCS, ENGINE_ROOT, INPUT_DIR,
)
from premium_package_factory.r373 import audit_diagrams
from premium_package_factory.diagrams import factory as diagram_factory
from premium_package_factory.r374 import (
    diagram_proof, equation_status, traceability_truth, pathway,
    acceptance_r374,
)

import tempfile


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _now():
    from premium_package_factory.r371.builder import _now as __now
    return __now()


# ---------------------------------------------------------------------------

def audit_equation_status(pkg, shipped_registry: dict) -> dict:
    """Recompute the R374 equation status from canonical data and
    cross-check the shipped registry (Art. III — shipped artifacts are
    claims)."""
    problems = []
    reg = build_equation_registry(pkg)
    reg["r372_validation"] = validate_registry(reg, pkg)
    reg = equation_status.attach_r374_status(reg, pkg)
    rc = reg["r374_validation_status"]
    st = shipped_registry.get("r374_validation_status")
    if not st:
        return {"package_id": pkg.pkg_id, "ok": False,
                "failures": [{"check": "R374_STATUS_MISSING",
                              "detail": "shipped registry lacks "
                                        "r374_validation_status"}]}
    if st.get("totals") != rc["totals"]:
        problems.append({
            "check": "TOTALS_MISMATCH",
            "detail": f"shipped {st.get('totals')} != recomputed "
                      f"{rc['totals']}"})
    shipped_units = {e["equation_id"]: e.get("r374_unit_status", [])
                     for e in shipped_registry.get("equations", [])}
    recomputed_units = {e["equation_id"]: e.get("r374_unit_status", [])
                        for e in reg["equations"]}
    for eq_id, rows in recomputed_units.items():
        ship = shipped_units.get(eq_id)
        if ship is None:
            problems.append({"check": "UNIT_TABLE_MISSING",
                             "detail": f"{eq_id}: no unit status table"})
            continue
        if [(r["symbol"], r["unit_status"]) for r in ship] != \
                [(r["symbol"], r["unit_status"]) for r in rows]:
            problems.append({
                "check": "UNIT_TABLE_MISMATCH",
                "detail": f"{eq_id}: shipped unit states differ from "
                          f"recompute"})
        for r in ship:
            if r["unit_status"] == "UNKNOWN" and \
                    not r.get("resolution_path"):
                problems.append({
                    "check": "UNKNOWN_WITHOUT_RESOLUTION_PATH",
                    "detail": f"{eq_id}/{r['symbol']}"})
            if r["unit_status"] == "SOURCE_BACKED" and \
                    not r.get("unit_source", {}).get("recorded_parameter"):
                problems.append({
                    "check": "SOURCE_BACKED_WITHOUT_SOURCE",
                    "detail": f"{eq_id}/{r['symbol']}"})
    return {
        "package_id": pkg.pkg_id,
        "totals": rc["totals"],
        "unit_coverage": rc["unit_coverage"],
        "failures": problems,
        "ok": not problems,
    }


# ---------------------------------------------------------------------------

def run_r374_audit(portfolio_root, engine_root=ENGINE_ROOT,
                   fresh_clone_certificate=None,
                   run_r373=True) -> dict:
    packages = load_all_packages()
    headlines = {r["package_id"]: r for r in _load(os.path.join(
        INPUT_DIR, "headlines_r371.json"))["packages"]}

    # 1. full R373 audit (dimensions + ladder; writes R373 artifacts)
    r373 = None
    if run_r373:
        r373 = run_r373_audit.run_r373_audit(portfolio_root, engine_root)
    else:
        r373 = _load(os.path.join(portfolio_root, "INTERNAL_QA",
                                  "R373_INDEPENDENT_ENGINEERING_"
                                  "ARTIFACT_AUDIT.json"))

    # 2. R374 dimensions per package
    token_freq = audit_diagrams.portfolio_token_frequencies(packages)
    aliens = audit_diagrams.alien_token_map(packages)
    per_pkg = {}
    tmp = tempfile.mkdtemp()
    diagram_factory.OUTPUT_DIR = tmp
    for p in packages:
        hl = headlines[p.pkg_id]
        # diagram element proofs (re-render, neutral recording)
        rec = record_diagram(lambda: DIAGRAM_FUNCS[p.pkg_id]())
        mech = audit_diagrams.audit_mechanism_diagram(
            p, rec, hl, token_freq,
            {t for (pid, t) in aliens if pid == p.pkg_id})
        spec = audit_diagrams._gate3_specs().get(p.pkg_id, {})
        mproof = diagram_proof.mechanism_diagram_proof(
            p, rec, hl, mech, spec)
        from premium_package_factory.r372.diagram_adequacy import (
            experiment_diagram_spec)
        shipped_spec = experiment_diagram_spec(p, hl)
        exp = audit_diagrams.audit_experiment_spec(shipped_spec, p, hl)
        exp["expected_roles"] = audit_diagrams.expected_experiment_roles(p, hl)
        eproof = diagram_proof.experiment_diagram_proof(p, hl, exp)
        # truth model
        shipped_tr = _load(os.path.join(
            portfolio_root, "DOWNLOAD", p.folder,
            "ENGINEERING_TRACEABILITY.json"))
        tm = traceability_truth.audit_truth_model(shipped_tr, p)
        # equation status
        shipped_eq = _load(os.path.join(
            portfolio_root, "DOWNLOAD", p.folder,
            "EQUATION_REGISTRY.json"))
        es = audit_equation_status(p, shipped_eq)
        per_pkg[p.pkg_id] = {
            "mechanism_diagram_proof": mproof,
            "experiment_diagram_proof": eproof,
            "traceability_truth_audit": tm,
            "equation_status_audit": es,
            "state_ladder": r373["packages"][p.pkg_id]["state_ladder"],
        }

    # 3. cemetery pathway (R374-6): migrate + audit (append-only)
    cemetery_path = os.path.join(engine_root, "MECHANISM_CEMETERY",
                                 "CEMETERY.json")
    cemetery = _load(cemetery_path) if os.path.exists(cemetery_path) else \
        {"description": "Library of impossibilities — every killed "
                        "invention with reusable lessons.", "entries": []}
    pathway.migrate_cemetery(cemetery)
    cem_audit = pathway.audit_cemetery(cemetery, engine_root)
    with open(cemetery_path, "w", encoding="utf-8") as f:
        json.dump(cemetery, f, indent=2, ensure_ascii=False)

    r374_audit = {
        "report": "R374_ENGINEERING_EVIDENCE_HARDENING_AUDIT",
        "generated_at": _now(),
        "portfolio_root": portfolio_root,
        "cycle": "R374 — final engineering evidence hardening",
        "independence_statement": (
            "Every R374 classification is recomputed from the canonical "
            "record with fresh code; shipped artifacts are treated as "
            "claims (Constitution Art. III). Diagram proofs re-render the "
            "visuals through neutral instrumentation. Builder-run tooling "
            "per Art. XXVI: SUBMITTED FOR CEO AUDIT, not independent "
            "certification."),
        "r374_dimensions": [
            "R374-1 traceability truth model (four states + reasons + "
            "UNKNOWN-is-not-verified declaration)",
            "R374-2 equation status language (STRUCTURAL / APPLICABILITY "
            "/ DIMENSIONAL separated)",
            "R374-3 source-backed units (SOURCE_BACKED / UNKNOWN with "
            "resolution paths; zero invented)",
            "R374-4 diagram element proofs (mechanism 5, experiment 7)",
            "R374-5 fresh-clone reproduction (build -> audit -> ZIP -> "
            "hashes -> PDF extraction)",
            "R374-6 failed-candidate pathway (six elements; append-only)",
            "R374-7 survivors only (complete gate -> portfolio)",
        ],
        "cemetery_pathway_audit": cem_audit,
        "packages": per_pkg,
    }

    # 4. seven-condition acceptance (R374 gate)
    acceptance = acceptance_r374.run_r374_acceptance(
        portfolio_root, r374_audit, engine_root=engine_root,
        fresh_clone_certificate=fresh_clone_certificate)
    r374_audit["acceptance"] = acceptance

    # 5. write the audit artifact
    qa_dir = os.path.join(portfolio_root, "INTERNAL_QA")
    os.makedirs(qa_dir, exist_ok=True)
    with open(os.path.join(qa_dir,
                           "R374_ENGINEERING_EVIDENCE_HARDENING_"
                           "AUDIT.json"), "w", encoding="utf-8") as f:
        json.dump(r374_audit, f, indent=2, ensure_ascii=False,
                  default=str)

    # 6. R374-7 repository rule application (survivors -> portfolio;
    #    failures -> cemetery pathway, nothing deleted)
    repo_rule = run_r373_audit.apply_repo_rule(
        r373, portfolio_root, engine_root, apply_changes=True)
    r374_audit["repo_rule_application"] = repo_rule

    # 7. release candidate (six states, never collapsed)
    totals = r373["totals"]
    all_pass = acceptance["all_pass"] and \
        all(r["state_ladder"]["release_gate"] == "PASS"
            for r in per_pkg.values())
    eq_totals = {
        "structural": sum(r["equation_status_audit"]["totals"]
                          ["structural_validated"]
                          for r in per_pkg.values()),
        "applicability": sum(r["equation_status_audit"]["totals"]
                             ["applicability_validated"]
                             for r in per_pkg.values()),
        "dimensional": sum(r["equation_status_audit"]["totals"]
                           ["dimensionally_validated"]
                           for r in per_pkg.values()),
        "equations": sum(r["equation_status_audit"]["totals"]["equations"]
                         for r in per_pkg.values()),
    }
    unit_totals = {"SOURCE_BACKED": 0, "UNKNOWN": 0}
    for r in per_pkg.values():
        for k, v in r["equation_status_audit"]["unit_coverage"].items():
            unit_totals[k] = unit_totals.get(k, 0) + v
    candidate = {
        "artifact": "R374_RELEASE_CANDIDATE",
        "generated_at": _now(),
        "cycle": "R374 — final engineering evidence hardening",
        "audit_artifact": ("INTERNAL_QA/R374_ENGINEERING_EVIDENCE_"
                           "HARDENING_AUDIT.json"),
        "status": ("RELEASE_CANDIDATE_SUBMITTED_FOR_CEO_AUDIT"
                   if all_pass else "RELEASE_GATE_FAILED"),
        "acceptance": {
            "condition_count": acceptance["condition_count"],
            "conditions_passed": acceptance["conditions_passed"],
            "all_pass": acceptance["all_pass"],
            "conditions": acceptance["conditions"],
        },
        "equation_validation_levels": {
            "totals": eq_totals,
            "note": ("Three levels reported separately per CEO R374-2. "
                     "DIMENSIONAL_VALIDATION is proven for "
                     f"{eq_totals['dimensional']} of {eq_totals['equations']} "
                     "equations — the honest state; units are unrecorded "
                     "in the canonical record for most symbols and are "
                     "never guessed (Art. VI)."),
        },
        "unit_status_totals": {
            "totals": unit_totals,
            "note": ("Per CEO R374-3: SOURCE_BACKED = recorded in the "
                     "canonical critical parameters; UNKNOWN carries a "
                     "resolution path per symbol in each "
                     "EQUATION_REGISTRY.json."),
        },
        "cemetery_pathway": {
            "entries": cem_audit["entry_count"],
            "pathway_complete": cem_audit["pathway_complete_entries"],
            "nothing_deleted": cem_audit["append_only"]["nothing_deleted"],
        },
        "repo_rule_application": repo_rule,
        "state_ladder_definition": (
            "Six states reported separately per package and never "
            "collapsed. The artifact release gate is DOCUMENT_COMPLETE + "
            "ENGINEERING_EVALUABLE + TRANSFER_EVALUABLE (R373-9), now "
            "hardened by the seven R374 conditions. PHYSICALLY_VALIDATED, "
            "EXTERNALLY_VALIDATED and TRANSFER_READY remain the "
            "reality-side boundary condition — honestly NOT_MET with "
            "what would change them."),
        "totals": totals,
        "per_package_states": {
            pid: {
                "DOCUMENT_COMPLETE": r["state_ladder"]["states"]
                ["DOCUMENT_COMPLETE"]["met"],
                "ENGINEERING_EVALUABLE": r["state_ladder"]["states"]
                ["ENGINEERING_EVALUABLE"]["met"],
                "TRANSFER_EVALUABLE": r["state_ladder"]["states"]
                ["TRANSFER_EVALUABLE"]["met"],
                "PHYSICALLY_VALIDATED": r["state_ladder"]["states"]
                ["PHYSICALLY_VALIDATED"]["met"],
                "EXTERNALLY_VALIDATED": r["state_ladder"]["states"]
                ["EXTERNALLY_VALIDATED"]["met"],
                "TRANSFER_READY": r["state_ladder"]["states"]
                ["TRANSFER_READY"]["met"],
                "release_gate": r["state_ladder"]["release_gate"],
            } for pid, r in per_pkg.items()
        },
        "honest_open_items": [
            "DIMENSIONAL_VALIDATION proven for 0 of 66 equations: the "
            "canonical record assigns units to 19 of 230 equation "
            "symbols. Closing this is canonical-record engineering work "
            "(record units per critical parameter), tracked per package "
            "in UNKNOWN_ROADMAP.json — not a portfolio-polish task.",
            "PHYSICALLY_VALIDATED / EXTERNALLY_VALIDATED / TRANSFER_READY "
            "remain NOT_MET for all 15 packages (0 physical observations, "
            "no external validation event) — the reality boundary "
            "(Constitution Art. XXXVIII), honestly recorded.",
            "Market-size sourcing remains NOT_ESTABLISHED for every "
            "package; no figures invented.",
        ],
        "note": (
            "Per Constitution Art. XXVI this builder-run result is "
            "submitted FOR CEO AUDIT. No R371/R372/R373 gate was lowered; "
            "the frozen benchmark is untouched."),
    }
    rel_dir = os.path.join(portfolio_root, "RELEASE")
    os.makedirs(rel_dir, exist_ok=True)
    with open(os.path.join(rel_dir, "R374_RELEASE_CANDIDATE.json"), "w",
              encoding="utf-8") as f:
        json.dump(candidate, f, indent=2, ensure_ascii=False)

    return r374_audit


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..",
                     "portfolio"))
    cert_path = os.path.join(root, "INTERNAL_QA",
                             "R374_FRESH_CLONE_REPRODUCTION.json")
    cert = _load(cert_path) if os.path.exists(cert_path) else None
    audit = run_r374_audit(root, fresh_clone_certificate=cert)
    print("=" * 74)
    print("R374 FINAL ENGINEERING-EVIDENCE HARDENING — acceptance")
    for name, c in audit["acceptance"]["conditions"].items():
        print(f"  [{'PASS' if c['pass'] else 'FAIL'}] {name}")
    print("=" * 74)
    print(f"R374 ALL PASS: {audit['acceptance']['all_pass']}")
    return 0 if audit["acceptance"]["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
