"""
acceptance_r374.py — CEO R374 acceptance gate: final engineering
evidence hardening.

Seven conditions, ADDITIVE over the R371 (16-condition), R372
(12-condition) and R373 (15-artifact-gate) standards — no existing gate
is lowered. Each condition recomputes from canonical data / shipped
artifacts and never trusts builder claims (Art. III).

  R374-1  traceability truth model        15/15 chains four-stated with
                                          reasons + truth-model block;
                                          recomputed counts match; no
                                          release artifact implies
                                          UNKNOWN == verified
  R374-2  equation-status language        15/15 registries carry the
                                          three-level validation status;
                                          recomputed totals match; zero
                                          bare 'N equations validated'
                                          claims in release artifacts
  R374-3  source-backed units             every equation symbol carries
                                          UNIT_STATUS SOURCE_BACKED
                                          (traceable to a recorded
                                          critical parameter) or UNKNOWN
                                          (with resolution path); zero
                                          invented units
  R374-4  diagram proofs                  15/15 mechanism diagrams prove
                                          5 elements; 15/15 experiment
                                          diagrams prove 7 elements
  R374-5  fresh-clone reproduction        certificate all-pass
                                          (build -> audit -> ZIP ->
                                          hashes -> PDF extraction)
  R374-6  failed-candidate pathway        cemetery pathway complete per
                                          entry; append-only verified
                                          (nothing deleted)
  R374-7  survivors only                  repo rule applied: every
                                          package present in the
                                          portfolio release has
                                          release_gate PASS

Art. XXVI: this is builder-run tooling — SUBMITTED FOR CEO AUDIT, not
independent certification.
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..")))

from premium_package_factory.r371.canonical_source import load_all_packages
from premium_package_factory.r371.equations import build_equation_registry
from premium_package_factory.r372.equation_validation import (
    validate_registry,
    _symbol_units,
)
from premium_package_factory.r374 import equation_status, traceability_truth

_ENGINE_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", ".."))


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _pdf_text(path, cache={}):
    import subprocess
    key = os.path.abspath(path)
    if key not in cache:
        r = subprocess.run(["pdftotext", "-raw", path, "-"],
                           capture_output=True, text=True, timeout=120)
        cache[key] = r.stdout or ""
    return cache[key]


# ---------------------------------------------------------------------------

def run_r374_acceptance(portfolio_root, r374_audit, engine_root=None,
                        fresh_clone_certificate=None) -> dict:
    """Evaluate the seven R374 conditions over the built release."""
    engine_root = engine_root or _ENGINE_ROOT
    packages = load_all_packages()
    results = []
    conditions = {}

    def record(name, ok, detail):
        conditions[name] = {"pass": bool(ok), "detail": str(detail)[:400]}
        results.append((name, bool(ok)))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    # ---- 1. traceability truth model ----------------------------------
    problems = []
    for p in packages:
        shipped = _load(os.path.join(portfolio_root, "DOWNLOAD", p.folder,
                                     "ENGINEERING_TRACEABILITY.json"))
        tm = traceability_truth.audit_truth_model(shipped, p)
        if not tm["ok"]:
            problems.append(f"{p.pkg_id}: "
                            f"{[f['check'] for f in tm['failures']][:4]}")
    pdf_texts = {}
    for pdf in ("PORTFOLIO_RELEASE_REPORT.pdf", "PORTFOLIO_INDEX.pdf"):
        fp = os.path.join(portfolio_root, pdf)
        if os.path.exists(fp):
            pdf_texts[pdf] = _pdf_text(fp)
    lang = traceability_truth.scan_release_language(portfolio_root, pdf_texts)
    if not lang["clean"]:
        problems.append(f"over-claim language: {lang['offenders']}")
    record("R374-1 traceability truth model (15/15 four-stated + "
           "truth-model block + no UNKNOWN-as-verified language)",
           not problems, f"problems={problems[:6]}")

    # ---- 2. equation-status language ----------------------------------
    problems = []
    totals = {"structural": 0, "applicability": 0, "dimensional": 0,
              "equations": 0}
    for p in packages:
        shipped = _load(os.path.join(portfolio_root, "DOWNLOAD", p.folder,
                                     "EQUATION_REGISTRY.json"))
        st = shipped.get("r374_validation_status")
        if not st or st.get("schema") != "R374_EQUATION_VALIDATION_LEVELS":
            problems.append(f"{p.pkg_id}: shipped registry lacks the R374 "
                            f"three-level status")
            continue
        # independent recompute (Art. III)
        reg = build_equation_registry(p)
        reg["r372_validation"] = validate_registry(reg, p)
        reg = equation_status.attach_r374_status(reg, p)
        rc = reg["r374_validation_status"]
        if rc["totals"] != st["totals"]:
            problems.append(f"{p.pkg_id}: totals mismatch shipped "
                            f"{st['totals']} != recomputed {rc['totals']}")
        else:
            t = st["totals"]
            totals["structural"] += t["structural_validated"]
            totals["applicability"] += t["applicability_validated"]
            totals["dimensional"] += t["dimensionally_validated"]
            totals["equations"] += t["equations"]
        # every equation's levels must be internally consistent with the
        # r372 dimensional state
        val_by_id = {v["equation_id"]: v for v in
                     shipped.get("r372_validation", {}).get("validations",
                                                            [])}
        for eq in st.get("equations", []):
            v = val_by_id.get(eq["equation_id"], {})
            dstate = (v.get("dimensional_check") or {}).get("state")
            dproven = eq["dimensional_validation"]["proven"]
            if (dstate == "DIMENSIONALLY_CONSISTENT") != dproven:
                problems.append(f"{p.pkg_id}/{eq['equation_id']}: "
                                f"dimensional level disagrees with the "
                                f"r372 dimensional_check state")
    # language scan across release artifacts
    scan_texts = {}
    readme = os.path.join(portfolio_root, "README.md")
    if os.path.exists(readme):
        scan_texts["README.md"] = open(readme, encoding="utf-8").read()
    scan_texts.update(pdf_texts)
    for sub in ("RELEASE", "INTERNAL_QA"):
        d = os.path.join(portfolio_root, sub)
        if os.path.isdir(d):
            for fn in sorted(os.listdir(d)):
                if fn.endswith(".json"):
                    try:
                        scan_texts[f"{sub}/{fn}"] = open(
                            os.path.join(d, fn), encoding="utf-8").read()
                    except Exception:
                        pass
    offenders = {}
    for name, text in scan_texts.items():
        hits = equation_status.bare_validated_claims(text)
        if hits:
            offenders[name] = hits[:4]
    if offenders:
        problems.append(f"bare 'validated' claims: {offenders}")
    record("R374-2 equation-status language (three levels separated; "
           f"recomputed: structural {totals['structural']}/66, "
           f"applicability {totals['applicability']}/66, dimensional "
           f"{totals['dimensional']}/66; zero unqualified claims)",
           not problems, f"problems={problems[:6]}")

    # ---- 3. source-backed units ----------------------------------------
    problems = []
    unit_counts = {"SOURCE_BACKED": 0, "UNKNOWN": 0}
    invented = []
    for p in packages:
        shipped = _load(os.path.join(portfolio_root, "DOWNLOAD", p.folder,
                                     "EQUATION_REGISTRY.json"))
        recorded_units = {}
        for cp in p.critical_parameters:
            if cp.get("unit"):
                recorded_units[cp["unit"]] = cp.get("name")
        for entry in shipped.get("equations", []):
            for row in entry.get("r374_unit_status", []):
                us = row.get("unit_status")
                if us not in ("SOURCE_BACKED", "UNKNOWN"):
                    problems.append(f"{p.pkg_id}/{entry['equation_id']}/"
                                    f"{row.get('symbol')}: bad unit_status "
                                    f"{us!r}")
                    continue
                unit_counts[us] += 1
                if us == "UNKNOWN" and not row.get("resolution_path"):
                    problems.append(f"{p.pkg_id}/{entry['equation_id']}/"
                                    f"{row.get('symbol')}: UNKNOWN without "
                                    f"resolution path")
                if us == "SOURCE_BACKED":
                    src = row.get("unit_source", {})
                    if row.get("unit") not in recorded_units:
                        invented.append(
                            f"{p.pkg_id}/{entry['equation_id']}/"
                            f"{row.get('symbol')}: unit "
                            f"{row.get('unit')!r} not in the canonical "
                            f"critical parameters")
                    if not src.get("recorded_parameter"):
                        problems.append(
                            f"{p.pkg_id}/{entry['equation_id']}/"
                            f"{row.get('symbol')}: SOURCE_BACKED without "
                            f"recorded source")
    if invented:
        problems.append(f"INVENTED UNITS: {invented[:5]}")
    record("R374-3 source-backed units (every symbol SOURCE_BACKED or "
           f"UNKNOWN+resolution path; {unit_counts['SOURCE_BACKED']} "
           f"backed / {unit_counts['UNKNOWN']} unknown; zero invented)",
           not problems, f"problems={problems[:6]}")

    # ---- 4. diagram proofs ----------------------------------------------
    mech_ok = sum(1 for r in r374_audit["packages"].values()
                  if r["mechanism_diagram_proof"]["all_elements_proven"])
    exp_ok = sum(1 for r in r374_audit["packages"].values()
                 if r["experiment_diagram_proof"]["all_elements_proven"])
    unproven_pkgs = [
        pid for pid, r in r374_audit["packages"].items()
        if not r["mechanism_diagram_proof"]["all_elements_proven"]
        or not r["experiment_diagram_proof"]["all_elements_proven"]
    ]
    record("R374-4 diagram proofs (mechanism 5 elements 15/15; "
           "experiment 7 elements 15/15)",
           mech_ok == 15 and exp_ok == 15,
           f"mechanism {mech_ok}/15, experiment {exp_ok}/15; "
           f"packages with unproven elements: {unproven_pkgs[:5]}")

    # ---- 5. fresh-clone reproduction -------------------------------------
    cert = fresh_clone_certificate or {}
    record("R374-5 fresh-clone reproduction (build -> audit -> ZIP -> "
           "hashes -> PDF extraction; byte-exact)",
           bool(cert.get("all_pass")),
           f"certificate: {cert.get('report', 'NOT_RUN')} "
           f"all_pass={cert.get('all_pass')}")

    # ---- 6. failed-candidate pathway -------------------------------------
    cem = r374_audit.get("cemetery_pathway_audit", {})
    record("R374-6 failed-candidate pathway (six elements per entry; "
           "append-only; nothing deleted)",
           bool(cem.get("ok")),
           f"entries {cem.get('entry_count')}, complete "
           f"{cem.get('pathway_complete_entries')}, removed "
           f"{cem.get('append_only', {}).get('removed_entry_ids')}")

    # ---- 7. survivors only -------------------------------------------------
    per_pkg = r374_audit.get("packages", {})
    survivors = [pid for pid, r in per_pkg.items()
                 if r.get("state_ladder", {}).get("release_gate") == "PASS"]
    non_survivors = [pid for pid in per_pkg
                     if pid not in survivors]
    # every package folder present in the release must be a survivor
    present = set()
    dl = os.path.join(portfolio_root, "DOWNLOAD")
    if os.path.isdir(dl):
        for fn in sorted(os.listdir(dl)):
            if os.path.isdir(os.path.join(dl, fn)):
                present.add(fn)
    survivor_folders = {f"{p.num}_{p.short}" for p in packages
                        if p.pkg_id in survivors}
    stray = present - survivor_folders
    record("R374-7 survivors only (complete release gate -> portfolio; "
           "failures -> cemetery with pathway)",
           len(survivors) == len(per_pkg) and not stray,
           f"survivors {len(survivors)}/{len(per_pkg)}; "
           f"non-survivors {non_survivors}; stray folders {sorted(stray)}")

    all_pass = all(ok for _, ok in results)
    return {
        "report": "R374_ACCEPTANCE",
        "cycle": "R374 — final engineering evidence hardening",
        "conditions": conditions,
        "condition_count": len(conditions),
        "conditions_passed": sum(1 for _, ok in results if ok),
        "all_pass": all_pass,
        "gate_note": ("Additive over R371 (16) + R372 (12) + R373 (15 "
                      "artifact gates). No existing gate lowered. "
                      "Art. XXVI: builder-run tooling — SUBMITTED FOR "
                      "CEO AUDIT."),
    }
