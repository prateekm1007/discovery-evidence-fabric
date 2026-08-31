"""R377 Task 1 — Six-survivor COMPLETE CHAIN AUDIT (CEO directive 1).

> "Take the six fresh-domain survivors and audit the complete chain:
>  EVIDENCE -> MECHANISM -> DIFFERENTIATING ELEMENTS -> PRIOR ART ->
>  SURVIVING FEATURES -> DECISIVE EXPERIMENT."

Deterministic audit of the six fresh t6 runs' SURVIVOR specification,
measuring each link with recorded evidence. This is a MEASUREMENT
instrument (Art. XXVI diagnostic; never wired into kill/promote).

Measured per link:
  1 EVIDENCE            records present, resolvable, hash-custodied
  2 MECHANISM           presence + SPAN-DERIVATION: term overlap between
                        the mechanism_source_span and the mechanism +
                        intervention text (the CEO's "is the mechanism
                        genuinely derived from evidence?" — measured, not
                        asserted)
  3 DIFFERENTIATING     element set size + generic-filler fraction
  4 PRIOR ART           recorded status, families, tiers, coverage classes
  5 SURVIVING FEATURES  surviving differentiators count + generic fraction
  6 DECISIVE EXPERIMENT selected experiment, EIG, hypotheses, and whether
                        it DISCRIMINATES against an existing approach
                        (baseline/control named) vs measuring in isolation

Output: TOSCANINI/R377_SIX_SURVIVOR_CHAIN_AUDIT.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.source_registry.query_relevance import terms  # noqa: E402

RUNS = [
    "t6_medical_infusion_occlusion",
    "t6_aerospace_battery_thermal_event",
    "t6_energy_ev_thermal_runaway",
    "t6_industrial_rolling_stock_equipment_failure",
    "t6_materials_rail_steel_fatigue",
    "t6_electronics_li_battery_product_fire",
]

# Generic engineering filler that any recombination can assemble from.
GENERIC_TERMS = {
    "sensor", "sensors", "monitoring", "monitor", "data", "processing",
    "unit", "system", "systems", "control", "controller", "detect",
    "detection", "early", "real", "time", "analysis", "pattern",
    "patterns", "algorithm", "algorithms", "temperature", "vibration",
    "protection", "protection circuit", "management", "integrated",
    "connected", "install", "deploy", "implement", "retrofit", "standard",
    "redundant", "dual", "multiple", "independent", "signal", "signals",
}

BASE = Path(__file__).resolve().parents[1]


def _t(text: str) -> set:
    return set(terms(text or ""))


def _generic_fraction(word_list) -> dict:
    if not word_list:
        return {"n": 0, "n_generic": 0, "generic_fraction": None}
    n = len(word_list)
    n_generic = sum(1 for w in word_list
                    if str(w).lower() in GENERIC_TERMS)
    return {"n": n, "n_generic": n_generic,
            "generic_fraction": round(n_generic / n, 3),
            "generic_members": [w for w in word_list
                                if str(w).lower() in GENERIC_TERMS]}


def audit_run(run_dir: Path) -> dict:
    sel = json.loads((run_dir / "SURVIVOR_SELECTION.json").read_text())
    cid = sel["selected"]
    grid_key = cid.split(":")[2] if cid.count(":") >= 2 else None
    spec_path = (run_dir /
                 f"INVENTION_SPECIFICATION_grid-{grid_key}.json")
    if not spec_path.exists():
        spec_path = run_dir / "INVENTION_SPECIFICATION.json"
    spec = json.loads(spec_path.read_text())
    dec = json.loads((run_dir / "DECISIVE_EXPERIMENT.json").read_text())

    # ---- link 1: EVIDENCE --------------------------------------------
    ev_value = (spec.get("evidence") or {}).get("value") or []
    ev_ids = {e.get("id") for e in ev_value if isinstance(e, dict)}
    mech_ev = (spec.get("mechanism") or {}).get("evidence_ids") or []
    ev_unresolved = [i for i in mech_ev if i not in ev_ids]

    # ---- link 2: MECHANISM + SPAN DERIVATION -------------------------
    mv = (spec.get("mechanism") or {}).get("value") or {}
    mech_text = " ".join(str(mv.get(k) or "") for k in
                         ("mechanism", "intervention", "expected_effect"))
    span = str(mv.get("mechanism_source_span") or "")
    span_terms = _t(span)
    mech_terms = _t(mech_text)
    shared = sorted(span_terms & mech_terms)

    # ---- link 3: DIFFERENTIATING ELEMENTS -----------------------------
    dv = (spec.get("distinguishing_features") or {}).get("value") or {}
    intervention = str(dv.get("intervention") or "")
    npa = dv.get("vs_nearest_prior_art") or []
    # full element set: same rule as collision core (natural tokens minus
    # filler) — reuse the module so ONE authority defines elements
    from discovery_fabric.prior_art_v2.collision_resolution import (
        _natural_tokens, _INTERVENTION_FILLER)
    elements = [t for t in _natural_tokens(intervention)
                if t not in _INTERVENTION_FILLER]
    elements = list(dict.fromkeys(elements))
    elem_generic = _generic_fraction(elements)

    # ---- link 4: PRIOR ART ---------------------------------------------
    nhv = (spec.get("novelty_hypothesis") or {}).get("value") or {}
    pav = (spec.get("prior_art") or {}).get("value") or {}
    res = pav.get("differentiation_resolution") or {}
    per_family = res.get("per_family") or []
    tiers = [f.get("evidence_tier") for f in per_family]
    cov_classes = [f.get("coverage", {}).get("coverage_class")
                   for f in per_family]

    # ---- link 5: SURVIVING FEATURES ------------------------------------
    surviving = dv.get("surviving_differentiators") or []
    if not surviving:
        s = set()
        for pa in npa:
            if isinstance(pa, dict):
                s.update(pa.get("distinguishing_terms_surviving") or [])
        surviving = sorted(s)
    surv_generic = _generic_fraction(surviving)

    # ---- link 6: DECISIVE EXPERIMENT ------------------------------------
    sel_exp = dec.get("selected") or {}
    exp_text = json.dumps(sel_exp) + json.dumps(
        (spec.get("killer_experiment") or {}).get("value") or {})
    # discrimination: does the experiment COMPARE against an existing
    # approach/baseline/control (vs measuring the candidate in isolation)?
    baseline_markers = ("baseline", "control", "without", "versus", " vs ",
                        "compared", "comparison", "existing", "conventional",
                        "reference")
    has_baseline = any(m in exp_text.lower() for m in baseline_markers)
    eig = sel_exp.get("expected_information_gain") \
        if isinstance(sel_exp, dict) else None
    hyps = sel_exp.get("hypotheses") if isinstance(sel_exp, dict) else None
    if not isinstance(hyps, list):
        kv = (spec.get("killer_experiment") or {}).get("value") or {}
        hyps = kv.get("hypotheses") or []
        eig = eig or kv.get("eig")

    audit = {
        "run": run_dir.name,
        "survivor_candidate_id": cid,
        "spec_file": spec_path.name,
        "problem": (spec.get("problem") or {}),
        "chain": {
            "EVIDENCE": {
                "records": len(ev_value),
                "mechanism_evidence_ids": mech_ev,
                "unresolved_ids": ev_unresolved,
                "hashed_fraction": round(
                    sum(1 for e in ev_value if isinstance(e, dict)
                        and e.get("content_hash")) / len(ev_value), 3)
                if ev_value else None,
            },
            "MECHANISM": {
                "mechanism": mv.get("mechanism"),
                "intervention": mv.get("intervention"),
                "expected_effect": mv.get("expected_effect"),
                "span": span[:400],
                "span_derivation": {
                    "method": ("shared content terms between "
                               "mechanism_source_span and mechanism+"
                               "intervention+effect text (same term rule "
                               "family as the engine adjudicator)"),
                    "shared_terms": shared,
                    "n_shared": len(shared),
                    "span_terms_n": len(span_terms),
                    "derivation_overlap_ratio": round(
                        len(shared) / len(span_terms), 3)
                    if span_terms else None,
                },
            },
            "DIFFERENTIATING_ELEMENTS": {
                "n_elements": elem_generic["n"],
                "elements": elements,
                "generic_fraction": elem_generic["generic_fraction"],
                "generic_members": elem_generic["generic_members"],
            },
            "PRIOR_ART": {
                "status": nhv.get("prior_art_status")
                          or pav.get("status"),
                "n_families": len(per_family),
                "evidence_tiers": tiers,
                "coverage_classes": cov_classes,
                "nearest_patents": [
                    {"patent_id": (f.get("representative") or {})
                     .get("patent_id"),
                     "title": (f.get("representative") or {})
                     .get("title", "")[:100]}
                    for f in per_family],
            },
            "SURVIVING_FEATURES": {
                "n": surv_generic["n"],
                "features": surviving,
                "generic_fraction": surv_generic["generic_fraction"],
                "generic_members": surv_generic["generic_members"],
            },
            "DECISIVE_EXPERIMENT": {
                "selected": (sel_exp or {}).get("experiment")
                            or (sel_exp or {}).get("selected"),
                "eig": eig,
                "n_hypotheses": len(hyps) if isinstance(hyps, list) else 0,
                "discriminates_against_existing_approach": has_baseline,
            },
        },
    }
    return audit


def main() -> None:
    out = []
    for r in RUNS:
        rd = BASE / "ENGINE_RUNS" / r
        if not rd.exists():
            out.append({"run": r, "state": "MISSING"})
            continue
        out.append(audit_run(rd))
    dest = BASE / "TOSCANINI" / "R377_SIX_SURVIVOR_CHAIN_AUDIT.json"
    dest.write_text(json.dumps(out, indent=1))
    print(f"audited {len(out)} runs -> {dest}")

    # console summary: the measured weak links
    for a in out:
        if a.get("state") == "MISSING":
            continue
        c = a["chain"]
        sd = c["MECHANISM"]["span_derivation"]
        print(f"\n=== {a['run']} ({a['survivor_candidate_id']})")
        print(f"  EVIDENCE: {c['EVIDENCE']['records']} records, "
              f"unresolved mech ids: {c['EVIDENCE']['unresolved_ids']}")
        print(f"  MECHANISM span-derivation: {sd['n_shared']}/"
              f"{sd['span_terms_n']} span terms shared "
              f"(ratio {sd['derivation_overlap_ratio']})")
        print(f"  ELEMENTS: {c['DIFFERENTIATING_ELEMENTS']['n_elements']} "
              f"({c['DIFFERENTIATING_ELEMENTS']['generic_fraction']} generic)")
        print(f"  PRIOR ART: {c['PRIOR_ART']['status']}, "
              f"{c['PRIOR_ART']['n_families']} families, "
              f"tiers {c['PRIOR_ART']['evidence_tiers']}")
        print(f"  SURVIVING: {c['SURVIVING_FEATURES']['n']} "
              f"({c['SURVIVING_FEATURES']['generic_fraction']} generic)")
        print(f"  EXPERIMENT: eig={c['DECISIVE_EXPERIMENT']['eig']}, "
              f"baseline-discrimination="
              f"{c['DECISIVE_EXPERIMENT']['discriminates_against_existing_approach']}")


if __name__ == "__main__":
    main()
