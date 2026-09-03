#!/usr/bin/env python3
"""scripts/r401_dedup_safety.py — R401-WC PHASE 5: prove dedup safety
with adversarial fixtures and MEASURE false merges / false splits.

Fixture classes (authored INDEPENDENTLY of the comparator's
implementation — Art. VIII: the certification corpus is not generated
from the verifier's own behavior):

  1  same mechanism / different wording        -> expected MERGE
  2  same phenomenon / different mechanism     -> expected SPLIT
  3a cross-domain same mechanism, same envelope-> expected MERGE
  3b cross-domain same mechanism, different
     boundary regime                           -> expected SPLIT
  4  near-duplicate (synonym variation)        -> expected MERGE
  5  genuinely distinct mechanism              -> expected SPLIT

False merge  = expected SPLIT pair the machine collapsed.
False split  = expected MERGE pair the machine kept apart.

Every fixture pair is fed through the REAL deduplicate_candidates()
(the engine's spine) exactly as candidates reach it in production.
Output: R401/DEDUP_RESULTS.json (measurement record, not a narrative).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.engine import mechanism_space as ms  # noqa: E402

OUT = REPO_ROOT / "R401" / "DEDUP_RESULTS.json"


def _chash(c: Dict[str, Any]) -> str:
    basis = json.dumps(
        {k: c.get(k) for k in ("mechanism", "intervention",
                               "predicted_effect",
                               "novel_design_variable")},
        sort_keys=True, default=str)
    return hashlib.sha256(basis.encode()).hexdigest()


def _cand(cid: str, *, mechanism: str, intervention: str,
          predicted_effect: str, design_variable: str,
          boundary: str, failure_modes: List[str],
          graph_nodes: Dict[str, List[str]],
          graph_edges: List[Dict[str, str]]) -> Dict[str, Any]:
    return {
        "candidate_id": cid,
        "candidate_state": "CANDIDATE",
        "mechanism": mechanism,
        "intervention": intervention,
        "predicted_effect": predicted_effect,
        "novel_design_variable": design_variable,
        "constraint_set": {"boundary_conditions": boundary},
        "known_failure_modes": list(failure_modes),
        "mechanism_graph": {
            "nodes": {k: {"terms": list(v)} for k, v in graph_nodes.items()},
            "edges": [
                {"from": e["from"], "relation": e["relation"],
                 "to": e["to"]} for e in graph_edges]},
        "testable_prediction": (
            "in vitro drainage > 0.5 mL/min at 37C for 30 days"),
        "transformation_operator": "FIXTURE",
    }


# ---------------------------------------------------------------------------
# The fixtures. Each pair: (candidate A, candidate B, expected outcome)
# ---------------------------------------------------------------------------

HEPARIN_GRAPH = {
    "nodes": {
        "heparin": ["heparin", "anticoagulant", "bonded"],
        "surface": ["luminal", "surface", "coating"],
        "clot": ["clot", "thrombus", "fibrin"],
        "inhibit": ["inhibit", "suppress", "block"],
    },
    "edges": [
        {"from": "heparin", "relation": "inhibits", "to": "clot"},
        {"from": "surface", "relation": "carries", "to": "heparin"},
    ],
}

FIXTURES: List[Dict[str, Any]] = []

# --- Class 1: same mechanism / different wording -> MERGE ---------------
FIXTURES.append({
    "fixture_id": "F1a-wording-heparin",
    "class": "1_same_mechanism_different_wording",
    "expected": "MERGE",
    "adversarial_point": (
        "morphological rewording (lumen vs luminal, coating vs bonding) "
        "must NOT buy distinctness"),
    "A": _cand(
        "fix:1a:A",
        mechanism="Heparin bonding on the catheter luminal surface "
                  "inhibits clotting cascade activation",
        intervention="apply a heparin-bonded coating to the inner lumen",
        predicted_effect="fibrin deposition reduced; drainage sustained "
                         "above 0.5 mL/min",
        design_variable="heparin surface density (IU/cm2)",
        boundary="steady flow 0.5 mL/min at 37C, physiological pH",
        failure_modes=["coating wear", "systemic anticoagulant leaching"],
        graph_nodes=dict(HEPARIN_GRAPH["nodes"]),
        graph_edges=HEPARIN_GRAPH["edges"]),
    "B": _cand(
        "fix:1a:B",
        mechanism="A bonded anticoagulant layer on the inner tube wall "
                  "blocks activation of the coagulation cascade",
        intervention="coat the tube's interior surface with bonded "
                     "heparin",
        predicted_effect="clot formation is diminished; drain flow stays "
                         "above the required minimum",
        design_variable="heparin surface density (IU/cm2)",
        boundary="steady flow 0.5 mL/min at 37C, physiological pH",
        failure_modes=["coating wear", "systemic anticoagulant leaching"],
        graph_nodes=dict(HEPARIN_GRAPH["nodes"]),
        graph_edges=HEPARIN_GRAPH["edges"]),
})

# --- Class 2: same phenomenon / different mechanism -> SPLIT ------------
FIXTURES.append({
    "fixture_id": "F2a-phenomenon-patency",
    "class": "2_same_phenomenon_different_mechanism",
    "expected": "SPLIT",
    "adversarial_point": (
        "both keep the catheter patent (the phenomenon) — the causal "
        "cores are unrelated (electrostatic repulsion vs mechanical "
        "flush); phenomenon overlap must never merge mechanisms"),
    "A": _cand(
        "fix:2a:A",
        mechanism="Negative electrostatic surface charge electrostatically "
                  "repels negatively-charged plasma proteins, preventing "
                  "adhesion",
        intervention="graft zwitterionic charged groups onto the "
                     "catheter polymer",
        predicted_effect="protein adhesion reduced by electrostatic "
                         "repulsion; patency maintained",
        design_variable="surface charge density (mC/m2)",
        boundary="static immersion in plasma at 37C",
        failure_modes=["charge screening by ions", "delamination"],
        graph_nodes={
            "charge": ["charge", "electrostatic", "repel", "zwitterionic"],
            "protein": ["protein", "fibrinogen", "adhesion"],
        },
        graph_edges=[
            {"from": "charge", "relation": "repels", "to": "protein"}]),
    "B": _cand(
        "fix:2a:B",
        mechanism="Intermittent high-pressure saline pulses mechanically "
                  "shear off incipient fibrin deposits before they "
                  "occlude the lumen",
        intervention="automated intermittent flush pump delivering "
                     "pressure pulses",
        predicted_effect="fibrin sheared before occlusion; patency "
                         "maintained",
        design_variable="flush pulse amplitude and interval",
        boundary="pulsatile pressure cycles at 300 mmHg",
        failure_modes=["pump failure", "pressure trauma to tissue"],
        graph_nodes={
            "pulse": ["pressure", "pulse", "shear", "flush"],
            "deposit": ["fibrin", "deposit", "occlusion"],
        },
        graph_edges=[
            {"from": "pulse", "relation": "shears", "to": "deposit"}]),
})

# --- Class 3a: cross-domain same mechanism, same envelope -> MERGE ------
FIXTURES.append({
    "fixture_id": "F3a-crossdomain-wick-same-envelope",
    "class": "3a_cross_domain_same_mechanism_same_envelope",
    "expected": "MERGE",
    "adversarial_point": (
        "the SAME capillary-wick causal core proposed twice with "
        "botanical vs engineering vocabulary; envelope identical — "
        "a true duplicate must merge despite domain wording"),
    "A": _cand(
        "fix:3a:A",
        mechanism="Capillary rise through porous micro-channels passively "
                  "transports fluid along a wick structure driven by "
                  "surface tension",
        intervention="embed a porous wick layer along the catheter wall",
        predicted_effect="passive drainage sustained without external "
                         "pressure",
        design_variable="micro-channel radius and porosity",
        boundary="ambient pressure 1 atm at 20C, water-like fluid",
        failure_modes=["channel clogging", "wick delamination"],
        graph_nodes={
            "capillary": ["capillary", "surface", "tension", "rise"],
            "channel": ["porous", "micro", "channel", "wick"],
        },
        graph_edges=[
            {"from": "capillary", "relation": "drives", "to": "channel"}]),
    "B": _cand(
        "fix:3a:B",
        mechanism="Xylem-like wicking: fluid climbs a porous medium "
                  "passively by capillary action of surface tension in "
                  "micro-pores",
        intervention="line the drain lumen with a xylem-inspired porous "
                     "material",
        predicted_effect="fluid removed passively with no applied "
                         "pressure gradient",
        design_variable="micro-channel radius and porosity",
        boundary="ambient pressure 1 atm at 20C, water-like fluid",
        failure_modes=["channel clogging", "wick delamination"],
        graph_nodes={
            "capillary": ["capillary", "surface", "tension", "rise"],
            "channel": ["porous", "micro", "channel", "wick"],
        },
        graph_edges=[
            {"from": "capillary", "relation": "drives", "to": "channel"}]),
})

# --- Class 3b: cross-domain same mechanism, different boundary -> SPLIT -
FIXTURES.append({
    "fixture_id": "F3b-crossdomain-wick-different-boundary",
    "class": "3b_cross_domain_same_mechanism_different_boundary",
    "expected": "SPLIT",
    "adversarial_point": (
        "same capillary core, but plant xylem operates under negative "
        "transpiration tension at 25C in soil while the catheter must "
        "operate under positive intra-abdominal pressure at 37C in "
        "protein-rich dialysate — the boundary regime difference is "
        "MATERIAL for this problem and must be recorded, not collapsed"),
    "A": _cand(
        "fix:3b:A",
        mechanism="Capillary rise through porous micro-channels passively "
                  "transports fluid along a wick structure driven by "
                  "surface tension",
        intervention="embed a porous wick layer along the catheter wall",
        predicted_effect="passive drainage sustained at intra-abdominal "
                         "pressure in proteinaceous dialysate",
        design_variable="micro-channel radius and porosity",
        boundary="positive pressure 5 mmHg, 37C, protein-rich dialysate, "
                 "viscous fluid",
        failure_modes=["protein fouling of pores", "wick delamination"],
        graph_nodes={
            "capillary": ["capillary", "surface", "tension", "rise"],
            "channel": ["porous", "micro", "channel", "wick"],
        },
        graph_edges=[
            {"from": "capillary", "relation": "drives", "to": "channel"}]),
    "B": _cand(
        "fix:3b:B",
        mechanism="Xylem sap ascent: negative tension generated by "
                  "transpiration pulls water through capillary "
                  "micro-channels of porous plant tissue",
        intervention="mimic xylem architecture with aligned "
                     "hydrophilic micro-tubes",
        predicted_effect="water transported upward under negative "
                         "tension in soil-water conditions",
        design_variable="micro-tube alignment density",
        boundary="negative tension 0.08 MPa, 25C, clean water, sterile "
                 "soil environment",
        failure_modes=["cavitation embolism", "salt accumulation"],
        graph_nodes={
            "capillary": ["capillary", "surface", "tension", "rise"],
            "channel": ["porous", "micro", "channel", "wick"],
        },
        graph_edges=[
            {"from": "capillary", "relation": "drives", "to": "channel"}]),
})

# --- Class 4: near-duplicate (synonym variation) -> MERGE ---------------
FIXTURES.append({
    "fixture_id": "F4a-synonym-hydrophilic",
    "class": "4_near_duplicate_synonym_variation",
    "expected": "MERGE",
    "adversarial_point": (
        "reduces/diminishes, fouling/adhesion, coating/treatment — "
        "synonym-level variation over an identical causal core and "
        "envelope must not split"),
    "A": _cand(
        "fix:4a:A",
        mechanism="A permanently hydrophilic coating absorbs a bound "
                  "water layer which reduces protein fouling on the "
                  "catheter surface",
        intervention="apply a hydrophilic polymeric coating that "
                     "retains bound water",
        predicted_effect="protein fouling reduced 60 percent; lumen "
                         "patency extended",
        design_variable="coating hydrophilicity (contact angle)",
        boundary="steady flow 0.5 mL/min at 37C, physiological pH",
        failure_modes=["coating degradation", "layer abrasion"],
        graph_nodes={
            "layer": ["hydrophilic", "water", "layer", "coating"],
            "foul": ["protein", "fouling", "adhesion"],
            "block": ["reduce", "diminish", "inhibit"],
        },
        graph_edges=[
            {"from": "layer", "relation": "reduces", "to": "foul"}]),
    "B": _cand(
        "fix:4a:B",
        mechanism="A bound water film on a hydrophilic treated surface "
                  "diminishes protein adhesion to the drainage tube",
        intervention="treat the tube surface with a hydrophilic "
                     "polymer layer",
        predicted_effect="protein adhesion diminished 60 percent; "
                         "drainage patency extended",
        design_variable="coating hydrophilicity (contact angle)",
        boundary="steady flow 0.5 mL/min at 37C, physiological pH",
        failure_modes=["coating degradation", "layer abrasion"],
        graph_nodes={
            "layer": ["hydrophilic", "water", "layer", "coating"],
            "foul": ["protein", "fouling", "adhesion"],
            "block": ["reduce", "diminish", "inhibit"],
        },
        graph_edges=[
            {"from": "layer", "relation": "reduces", "to": "foul"}]),
})

# --- Class 5: genuinely distinct mechanism -> SPLIT ----------------------
FIXTURES.append({
    "fixture_id": "F5a-distinct-valve-vs-osmotic",
    "class": "5_genuinely_distinct_mechanism",
    "expected": "SPLIT",
    "adversarial_point": (
        "a mechanically actuated anti-reflux valve and an osmotic "
        "gradient pump are unrelated causal structures — both must "
        "survive as distinct mechanisms"),
    "A": _cand(
        "fix:5a:A",
        mechanism="A spring-loaded check valve mechanically occludes "
                  "backflow when upstream pressure drops below the "
                  "cracking pressure",
        intervention="integrate a miniaturized check valve at the "
                     "proximal port",
        predicted_effect="reflux eliminated; forward drainage "
                         "unimpeded",
        design_variable="valve cracking pressure setpoint",
        boundary="pulsatile pressure 0 to 10 mmHg at 37C",
        failure_modes=["valve jam", "spring fatigue"],
        graph_nodes={
            "valve": ["valve", "check", "spring", "occlude"],
            "backflow": ["reflux", "backflow", "pressure", "reverse"],
        },
        graph_edges=[
            {"from": "valve", "relation": "occludes", "to": "backflow"}]),
    "B": _cand(
        "fix:5a:B",
        mechanism="An osmotic agent across a semipermeable membrane "
                  "generates chemical potential gradient that drives "
                  "net fluid transport",
        intervention="mount an osmotic pump module distal to the "
                     "drainage lumen",
        predicted_effect="continuous slow net drainage independent of "
                         "positional pressure",
        design_variable="osmotic agent concentration and membrane area",
        boundary="constant 37C, osmotic gradient 300 mOsm",
        failure_modes=["agent depletion", "membrane rupture"],
        graph_nodes={
            "osmotic": ["osmotic", "gradient", "chemical", "potential"],
            "membrane": ["membrane", "semipermeable", "transport"],
        },
        graph_edges=[
            {"from": "osmotic", "relation": "drives", "to": "membrane"}]),
})


def main() -> int:
    results: List[Dict[str, Any]] = []
    n_false_merge = 0
    n_false_split = 0
    for fx in FIXTURES:
        a, b = dict(fx["A"]), dict(fx["B"])
        for c in (a, b):
            c["candidate_hash"] = _chash(c)
        res = ms.deduplicate_candidates([a, b])
        machine = "MERGE" if res["n_kept"] == 1 else "SPLIT"
        correct = machine == fx["expected"]
        if not correct:
            if fx["expected"] == "SPLIT":
                n_false_merge += 1
            else:
                n_false_split += 1
        cmp_detail = None
        if res["dedup_events"]:
            cmp_detail = (res["dedup_events"][0].get("comparison")
                          or {}).get("dimensions")
        if res["retain_events"]:
            cmp_detail = ((res["retain_events"][-1].get(
                "difference_basis") or {}).get("comparison") or
                {}).get("dimensions")
        results.append({
            "fixture_id": fx["fixture_id"],
            "class": fx["class"],
            "expected": fx["expected"],
            "machine": machine,
            "correct": correct,
            "n_kept": res["n_kept"],
            "adversarial_point": fx["adversarial_point"],
            "dimension_jaccards": (
                {d: (v or {}).get("jaccard")
                 for d, v in (cmp_detail or {}).items()}
                if cmp_detail else None),
            "recorded_reason": (
                (res["dedup_events"] or [{}])[0].get("reason") or
                (res["retain_events"] or [{}])[-1].get("reason"))[:200],
        })

    n_total = len(results)
    n_correct = sum(1 for r in results if r["correct"])
    record = {
        "suite": "R401-WC PHASE 5 — dedup safety (adversarial fixtures)",
        "instrument": "discovery_fabric.engine.mechanism_space."
                      "deduplicate_candidates (the production spine)",
        "fixture_authorship": (
            "fixtures authored independently of the comparator "
            "implementation (Art. VIII); expected outcomes declared "
            "BEFORE running the machine"),
        "n_fixture_pairs": n_total,
        "n_correct": n_correct,
        "false_merge": {
            "definition": "expected SPLIT, machine collapsed the pair",
            "count": n_false_merge},
        "false_split": {
            "definition": "expected MERGE, machine kept the pair apart",
            "count": n_false_split},
        "accuracy": round(n_correct / n_total, 3) if n_total else None,
        "verdict": ("DEDUP_SAFE" if n_false_merge == 0 and
                    n_false_split == 0 else "DEDUP_DEFECT_FOUND"),
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=1, default=str))
    print(json.dumps({k: v for k, v in record.items()
                      if k != "results"}, indent=1))
    for r in results:
        print(f"  {r['fixture_id']}: expected {r['expected']:5s} | "
              f"machine {r['machine']:5s} | "
              f"{'OK' if r['correct'] else 'DEFECT'}")
    print(f"\nfull record -> {OUT}")
    return 0 if record["verdict"] == "DEDUP_SAFE" else 1


if __name__ == "__main__":
    sys.exit(main())
