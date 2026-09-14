#!/usr/bin/env python3
"""scripts/r458_benchmark.py — R458-C1 §1: the FROZEN discovery
benchmark (model capability + adaptive pipeline rounds).

Directive (verbatim intent): "Freeze a discovery benchmark. Use a small
but serious corpus spanning several domains. At minimum: mechanical,
thermal, fluid, materials, biomedical, electrical/control, software/AI.
Do not let the benchmark itself become the optimization target. Use a
blind holdout. The Constitution's anti-circularity principle and the
blind-spot register's BS-016 directly require this discipline."

DESIGN (Art. XLIX + Art. LIX + BS-016):

  - 14 AUTHORED problems, 7 domain families x 2 each
    (mechanical, thermal, fluid, materials, biomedical,
    electrical_control, software_ai) — exceeding Art. XLIX's minimum
    (>=10 problems, >=6 domains, >=2 per domain family).
  - Authoring discipline (the R452 assay standard, applied to every
    problem): SYMPTOMS AND CONSTRAINTS ONLY — quantitative symptoms,
    hard constraints kept hard, no solution class seeded, no hint of
    the expected mechanism family. Each problem is a genuine
    engineering/discovery situation with numbers a solver must respect.
  - SPLIT, fixed at authoring time (BEFORE any model run — BS-016):
      DEV set      7 problems (one per domain family) — the ONLY set
                   any model arm, tuning pass, or adaptive comparison
                   may touch;
      BLIND HOLDOUT 7 problems (one per domain family) — sealed at
                   freeze; mechanically refused to every driver except
                   the blind-test phase, which itself refuses to run
                   until the dev-phase record exists (ordering is
                   enforced, not promised).
  - FREEZE discipline (Art. LIX — no benchmark gaming): `freeze`
    records per-problem content sha256, the split, the corpus hash,
    and the script's own sha256; it FAILS CLOSED if any R458 result
    artifact already exists (the corpus is frozen before results are
    looked at). `verify` recomputes everything and refuses drift.
  - ANTI-CIRCULARITY (Art. VIII + BS-016): the corpus is authored
    BEFORE any R458 model runs; the instrument's metric definitions
    are frozen in a SEPARATE module (r458_quality_instrument.py) under
    the same fail-closed discipline; no prompt/threshold/operator/
    retrieval/model tuning against the holdout is possible from the
    drivers (the holdout ids are refused outside the blind phase).

Usage:
  python scripts/r458_benchmark.py author     # write the corpus JSON
  python scripts/r458_benchmark.py freeze     # seal split + hashes
  python scripts/r458_benchmark.py verify     # recompute + refuse drift
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

OUT_ROOT = REPO_ROOT / "R458"
CORPUS_PATH = OUT_ROOT / "BENCHMARK_CORPUS.json"
FREEZE_PATH = OUT_ROOT / "BENCHMARK_FREEZE.json"

#: the frozen domain families (the directive's own minimum list, exact)
DOMAIN_FAMILIES = (
    "mechanical", "thermal", "fluid", "materials",
    "biomedical", "electrical_control", "software_ai",
)

#: artifact files whose existence BEFORE freeze proves the corpus was
#: not frozen before results were looked at (fail-closed, Art. LIX)
_RESULT_ARTIFACTS = (
    "R458_C1_MODEL_CAPABILITY_BENCHMARK.json",
    "R458_C1_ADAPTIVE_PIPELINE_BENCHMARK.json",
    "R458_C1_NEXT_ACTION_DECISION_TRACE.json",
    "R458_C1_REALITY_MUTATION_PROOF.json",
    "R458/BLIND_TEST_RESULTS.json",
    "R458/MODEL_ARMS/r458mc_",
)

# ---------------------------------------------------------------------------
# THE 14 AUTHORED PROBLEMS — symptoms and constraints only
# (authored 2026-09-15, before any R458 model run; the R452 discipline)
# ---------------------------------------------------------------------------
# Split is fixed AT AUTHORING TIME. Within each family the DEV problem
# is the one whose numbers are furthest from the family's holdout
# problem in operating regime (recorded to make the split non-arbitrary
# in hindsight: each pair differs in scale, industry, and failure
# physics, so the holdout genuinely probes transfer, not memorized
# numbers).
# ---------------------------------------------------------------------------

AUTHORED_PROBLEMS: Dict[str, Dict[str, Any]] = {

    # ------------------------- MECHANICAL ------------------------------
    "M1": {
        "case_id": "r458-m1-cam-follower-surface-fatigue",
        "domain_family": "mechanical",
        "split": "DEV",
        "text": (
            "A packaging line runs a rotary cam-driven folding station at "
            "420 cycles per minute, 20 hours a day. The flat-faced cam "
            "followers, 16 millimetres in diameter on fixed studs, develop "
            "surface fatigue spalls within 6 to 9 weeks of service, and "
            "metal debris from the spalling contaminates the food-contact "
            "belt, forcing line stops for cleaning roughly every 9 days. "
            "Lubrication is a once-per-shift manual grease gun routine "
            "that the crew already skips about one shift in five. The "
            "measured cam contact stress at the peak dwell is 1.4 "
            "gigapascals against a follower material rolling-contact "
            "limit near 1.7 gigapascals, but the measured oil film "
            "thickness ratio sits near 0.8, meaning asperity contact "
            "during every dwell. The line must keep 420 cycles per minute "
            "on the same cam mechanism, cannot change the cam profile "
            "(the camshaft is certified with the machine and re-cutting "
            "needs a six-week recertification), cannot switch to a "
            "different follower diameter class (the stud pattern is "
            "fixed), and cannot add any maintenance step the crew "
            "performs more than once per week."
        ),
    },
    "M2": {
        "case_id": "r458-m2-soft-fruit-gripper-bruising",
        "domain_family": "mechanical",
        "split": "HOLDOUT",
        "text": (
            "An automated apple packing house uses two-finger pneumatic "
            "grippers on six delta robots to transfer fruit from the "
            "float tank to the tray at 30 picks per second across the "
            "array. Bruising audits show 4.2 percent of fruit carries "
            "pressure bruises over 8 millimetres across at the grip "
            "contact patches, concentrated on the fruit graded in the "
            "top two size classes, and the cooperative deducts the bruised "
            "fraction from the payment every week. Grip force is commanded "
            "to a fixed 14 newtons per finger because the same gripper "
            "must hold fruit from 65 to 95 millimetres diameter without "
            "dropping any; a dropped fruit on the tray line costs a full "
            "line stop of 40 seconds. The soft silicone finger pads "
            "currently measure 40 Shore 00 and wear to a polished finish "
            "in three weeks, after which the bruise rate roughly doubles. "
            "The plant must keep 30 picks per second with the same robot "
            "array, cannot add per-fruit sensing that costs more than 40 "
            "cents per gripper, cannot drop fewer than the current "
            "0.05 percent, and cannot slow the pick rate because the "
            "grader downstream feeds at a fixed clock."
        ),
    },

    # --------------------------- THERMAL -------------------------------
    "T1": {
        "case_id": "r458-t1-cold-aisle-hotspot-legacy-retrofit",
        "domain_family": "thermal",
        "split": "DEV",
        "text": (
            "A legacy data hall built in 2011 has twelve 20-kilowatt racks "
            "added to a room originally laid out for 6-kilowatt racks, "
            "with perforated floor tiles at the original 30 percent open "
            "area pattern and two 75-ton computer-room air handlers "
            "against a design day of 35 degrees Celsius outside. After "
            "the retrofit, rows 4 through 7 measure inlet temperatures "
            "between 29 and 34 degrees Celsius against the 27-degree "
            "maximum, two spots in row 5 reach 36 degrees during the "
            "afternoon, and the air handlers already run at 92 percent "
            "capacity with supply air at 15 degrees Celsius, near the "
            "condensation limit for the underfloor plenum. The building "
            "cannot add another air handler (roof structural reserve is "
            "exhausted and the capital is not approved), cannot raise "
            "supply air below 14 degrees (condensation on the legacy "
            "plenum), cannot rearrange the perforated tile layout more "
            "than once per quarter because every change requires a "
            "shutdown window the tenants refuse, and must hold every "
            "rack inlet at or below 27 degrees Celsius at 35 degrees "
            "ambient with the existing two handlers."
        ),
    },
    "T2": {
        "case_id": "r458-t2-battery-fast-charge-propagation-onset",
        "domain_family": "thermal",
        "split": "HOLDOUT",
        "text": (
            "A 400-volt traction battery pack for delivery vans uses "
            "prismatic lithium iron phosphate cells in 8-module strings, "
            "and the fleet operator wants 2C fast charging at depots "
            "during the 40-minute driver break. Cell testing shows the "
            "peak cell temperature during 2C charge reaches 52 degrees "
            "Celsius against a 45-degree limit at 25-degree ambient, and "
            "the hottest cell sits at the pack's geometric center where "
            "the measured temperature spread across the pack reaches 11 "
            "degrees Celsius by end of charge. The existing cooling is a "
            "cold-plate on the module underside with a 40-percent "
            "water-glycol mix at 1.2 litres per minute; aging data from "
            "the first 60 vans shows cells at the pack center lose 8 "
            "percent capacity by 1200 cycles versus 3 percent at the "
            "edges. The pack cannot change cell format or chemistry "
            "(supplier contract, two years remaining), cannot grow in "
            "height more than 3 millimetres (vehicle floor pan fixed), "
            "cannot exceed 150 watts of added parasitic pump or fan "
            "power (range penalty budget), and must hold the peak cell "
            "at or below 45 degrees Celsius during 2C charge at "
            "30-degree ambient depot temperature."
        ),
    },

    # ---------------------------- FLUID --------------------------------
    "F1": {
        "case_id": "r458-f1-microirrigation-emitter-clogging",
        "domain_family": "fluid",
        "split": "DEV",
        "text": (
            "A 300-hectare drip-irrigation vineyard on treated "
            "wastewater runs pressure-compensating emitters rated at 2 "
            "litres per hour through 16-millimetre laterals at a 0.8-bar "
            "design head. Within one season, emitter discharge on the "
            "laterals furthest from the pump station falls 25 to 40 "
            "percent below rated flow, and physical teardown of 50 "
            "emitters shows biological film mixed with calcium carbonate "
            "scaling inside the emitter labyrinth channels; the vine "
            "rows at the far end show measurable water stress by "
            "mid-season. The existing filtration is a 120-mesh screen "
            "filter with automatic backflush at a 70-kilopascal "
            "differential trigger, and the water carries 3 to 4 "
            "milligrams per litre of residual organic carbon after the "
            "treatment plant. The operation cannot switch water source, "
            "cannot add acid or chlorine dosing (organic certification "
            "forbids it and the treatment plant will not permit "
            "chemical injection upstream), cannot replace the whole "
            "emitter stock more often than every 5 seasons (capital), "
            "and must deliver at least 90 percent of the design "
            "emission uniformity on the same 0.8-bar head with the "
            "existing pump."
        ),
    },
    "F2": {
        "case_id": "r458-f2-inkjet-nozzle-starvation-burst",
        "domain_family": "fluid",
        "split": "HOLDOUT",
        "text": (
            "A production single-pass inkjet press prints corrugated "
            "board at 150 metres per minute with 4-inch-wide printhead "
            "modules firing 30-kilohertz bursts during solid-area "
            "coverage. Mid-web, the nozzles in the center 40 percent of "
            "each module show drop velocity falling from 7 to under 5 "
            "metres per second within 20 seconds of a solid-area "
            "section, and the print shows visible banding that the "
            "customer rejects; the head recovers fully after 60 seconds "
            "of idle. The ink is a water-based pigment formulation with "
            "3.5 millipascal-second viscosity at print temperature, and "
            "the measured channel refill time constant after firing is "
            "14 microseconds against the 33-microsecond firing period "
            "in bursts. The press must keep 150 metres per minute, "
            "cannot change ink formulation (the substrate supplier "
            "qualification locks the ink to the coating), cannot reduce "
            "the firing frequency below 26 kilohertz without dropping "
            "below the coverage spec, cannot add a recirculation pump "
            "drawing more than 2 watts per printhead module (the "
            "machine's power and vibration envelope is fixed), and must "
            "hold drop velocity above 6 metres per second through "
            "60-second continuous solid-area printing."
        ),
    },

    # --------------------------- MATERIALS -----------------------------
    "MA1": {
        "case_id": "r458-ma1-diecast-porosity-leak-paths",
        "domain_family": "materials",
        "split": "DEV",
        "text": (
            "A die-cast ADC12 aluminum compressor housing for a "
            "commercial refrigeration condensing unit leaks refrigerant "
            "at a 1.8 percent rate at the helium leak test station, "
            "traced to interconnected gas porosity chains in the "
            "thick-walled boss section where two 8-millimetre walls "
            "meet; the casting is made on a 6-cavity die at a 55-second "
            "cycle, and X-ray sectioning of rejected castings shows "
            "porosity clusters of 0.4 to 1.2 millimetres concentrated "
            "within 15 millimetres of the boss. Each rejected housing "
            "costs 31 euros in scrap and remelt, and the leak-test "
            "station is becoming the bottleneck at 24000 units per "
            "month. The plant must keep the same alloy (the refrigerant "
            "compatibility and the customer's material qualification "
            "lock ADC12), cannot add a vacuum-assist retrofit to the "
            "existing machine this fiscal year (capital not approved, "
            "and the machine frame has no provision), cannot extend the "
            "cycle beyond 57 seconds (the line's takt time), and must "
            "reduce the leak rate below 0.5 percent at the existing "
            "leak-test threshold."
        ),
    },
    "MA2": {
        "case_id": "r458-ma2-rail-rolling-contact-fatigue",
        "domain_family": "materials",
        "split": "HOLDOUT",
        "text": (
            "A heavy-haul railway moves 32-tonne axle-load ore trains "
            "over a 9-degree curve section of track, and rail life "
            "there has fallen from an expected 500 million gross tonnes "
            "to 210 million before grinding is forced by rolling "
            "contact fatigue: head checks at the gauge-corner spacing "
            "of 4 to 9 millimetres, with measured crack depths reaching "
            "4 millimetres at removal and two cases in five years where "
            "a crack turned transverse and the rail had to be replaced "
            "inside an emergency possession. The rail is 136-rebound "
            "grade in the curve with standard carbon composition, "
            "lubrication is a trackside grease stick applied when the "
            "maintenance gang passes, roughly every 3 weeks, and often "
            "found dry at inspection. The railway must keep the 32-tonne "
            "axle load and traffic (the mine contract fixes tonnage), "
            "cannot change rail grade on the curve this cycle (the "
            "premium rail budget covers only 8 kilometres per year and "
            "other curves are queued ahead), cannot grind more than "
            "twice per year on this section (possessions are granted at "
            "that frequency only), and must keep the section's rail "
            "life at or above 350 million gross tonnes."
        ),
    },

    # -------------------------- BIOMEDICAL -----------------------------
    "B1": {
        "case_id": "r458-b1-dialysis-tmp-drift-mid-session",
        "domain_family": "biomedical",
        "split": "DEV",
        "text": (
            "An in-center hemodialysis unit runs 4-hour sessions on "
            "high-flux dialyzers and sees transmembrane pressure creep "
            "in the last 90 minutes of roughly one session in six: "
            "pressure climbs from the set 50 millimetres of mercury "
            "toward the 100-millimetre machine alarm limit, staff "
            "respond by lowering the ultrafiltration goal mid-session, "
            "and the session ends with 0.4 to 0.9 litres below the "
            "prescribed fluid removal, which the nephrologists flag as "
            "a chronic fluid-overload contribution for those patients. "
            "Teardown of fouled dialyzers shows the hollow-fiber "
            "bundle's middle third heavily protein-fouled with a "
            "measured fiber patency of 82 percent versus 96 percent on "
            "clean runs, and the unit's water system measures 90 to "
            "140 colony-forming units per millilitre of heterotrophic "
            "bacteria in the loop, within the 200 limit but high. The "
            "unit must keep the same dialyzer class and membrane "
            "material (tender contract, two years), cannot add any "
            "blood-side sensor to the disposable circuit (regulatory "
            "filing for the circuit is closed), cannot extend session "
            "time beyond 4 hours 15 minutes (chair capacity is the "
            "constraint), and must complete the prescribed fluid "
            "removal in at least 95 percent of sessions without "
            "transmembrane-pressure alarms."
        ),
    },
    "B2": {
        "case_id": "r458-b2-knee-implant-micromotion-loosening",
        "domain_family": "biomedical",
        "split": "HOLDOUT",
        "text": (
            "A registry review at an orthopedic group shows their "
            "cementless total-knee femoral components revisions for "
            "aseptic loosening running at 3.1 percent at 10 years "
            "versus the 1.5-percent benchmark, with retrieval analysis "
            "of nine revised components showing a fibrous tissue "
            "interface instead of bone ingrowth across the anterior "
            "flange, where intra-operative measurements suggest "
            "micromotion of 80 to 150 microns under stair-climbing "
            "load against the widely cited 50-to-75-micron threshold "
            "for reliable ingrowth. The implant is a cobalt-chrome "
            "femoral component with a 1-millimetre porous coating on "
            "the pegs only, and the group's patient mix skews 20 "
            "percent heavier than the design cohort. The group must "
            "keep the same implant system (surgeon training and "
            "hospital contracts lock the platform for 3 more years), "
            "cannot change the stem or peg geometry (regulatory "
            "changes to the component would re-open the 510(k)), "
            "cannot add operative time beyond 5 minutes per case (the "
            "block schedule is fixed), and must bring 10-year aseptic "
            "loosening at or below 2 percent within the existing "
            "surgical workflow."
        ),
    },

    # --------------------- ELECTRICAL / CONTROL ------------------------
    "E1": {
        "case_id": "r458-e1-inverter-weak-grid-sag-trips",
        "domain_family": "electrical_control",
        "split": "DEV",
        "text": (
            "A 3-megawatt rooftop solar farm on a weak distribution "
            "feeder (short-circuit ratio measured 2.6) trips on "
            "voltage sags: utility switching events on the adjacent "
            "line produce 0.6-per-unit, 200-millisecond sags, and the "
            "inverters trip on instantaneous undervoltage about once "
            "every 11 days, each trip costing roughly 4 minutes of "
            "lost production at peak and triggering the utility's "
            "ride-through compliance report, now at 14 exceptions this "
            "year against a 6-exception allowance. The inverters are "
            "grid-tie string inverters with an LCL grid filter, and "
            "the protection settings are locked to the certified "
            "grid-code envelope (the 0.6-per-unit 200-millisecond "
            "point is inside the mandated no-trip zone, but the "
            "inverters still trip because the sag recovery overshoots "
            "and the controller's synchronous reference frame "
            "oscillates). The farm cannot change the feeder (utility "
            "asset), cannot alter the certified protection curve "
            "(grid-code filing), cannot add energy storage (capital), "
            "and must achieve at most 2 ride-through exceptions per "
            "year with the existing inverters and filters."
        ),
    },
    "E2": {
        "case_id": "r458-e2-agv-regen-dcbus-overshoot",
        "domain_family": "electrical_control",
        "split": "HOLDOUT",
        "text": (
            "A warehouse runs 45 automated guided vehicles with "
            "permanent-magnet motor drives, and during simultaneous "
            "deceleration events at shift change, the 48-volt DC bus "
            "on each vehicle overshoots to 61 volts against a "
            "58.5-volt capacitor rating, the drives protectively "
            "disable regenerative braking, and the vehicles brake on "
            "the mechanical service brakes, wearing them 4 times "
            "faster than design and occasionally rolling through pick "
            "positions when the service brakes are due for adjustment. "
            "The measured regenerative current pulse is 95 amperes for "
            "0.8 seconds per vehicle, with up to 12 vehicles "
            "decelerating within the same 5-second window at the "
            "battery-charging depot where the shared bus coupling is "
            "weakest. Each vehicle must keep the same battery pack and "
            "motor (spares inventory), cannot add a dedicated braking "
            "chopper module above 15 euros per vehicle (fleet budget), "
            "cannot change the braking profile commanded by the fleet "
            "manager (throughput model fixed), and must hold the DC "
            "bus at or below 58 volts through simultaneous "
            "deceleration events."
        ),
    },

    # --------------------------- SOFTWARE / AI -------------------------
    "S1": {
        "case_id": "r458-s1-ranking-model-distribution-shift",
        "domain_family": "software_ai",
        "split": "DEV",
        "text": (
            "A marketplace's search ranking model, trained on 18 months "
            "of interaction logs, decays measurably after a redesign "
            "moves the buy button above the fold on mobile: offline "
            "replay shows a 6-percent drop in normalized discounted "
            "cumulative gain against held-out post-launch traffic, "
            "click-through on ranked position 3 falls 11 percent, and "
            "revenue-per-search is down 4 percent over five weeks while "
            "the site's overall traffic is flat. The model is a "
            "gradient-boosted ranking model over 240 features with a "
            "45-millisecond serving deadline including feature "
            "fetches, and the label pipeline (delayed conversion "
            "labels arriving 1 to 9 days after click) cannot be "
            "rebuilt this quarter. The team cannot launch a full "
            "retraining pipeline redesign (one release per quarter, "
            "already committed), cannot increase serving latency "
            "beyond 45 milliseconds (the page-speed budget is "
            "contractual), cannot buy new labeling beyond the current "
            "budget, and must recover at least 3.5 points of the "
            "4-percent revenue-per-search gap within one quarter "
            "on the existing serving stack."
        ),
    },
    "S2": {
        "case_id": "r458-s2-db-tail-latency-flash-sale",
        "domain_family": "software_ai",
        "split": "HOLDOUT",
        "text": (
            "An e-commerce platform's order database, a sharded "
            "PostgreSQL cluster with 3 replicas per shard, shows "
            "p99.9 read latency collapsing from 40 to 900 milliseconds "
            "for 3 to 7 minutes during flash sales: checkout error "
            "rates hit 2 percent at peak as the 250-millisecond client "
            "timeout fires, and the postmortems show lock waits on the "
            "inventory row for the featured item cascading through "
            "connection pools until the pool exhausts and unrelated "
            "queries queue behind it. The featured-item pages drive "
            "40 percent of sale-window traffic to one shard. The "
            "platform cannot change the schema or add cache invalidation "
            "complexity this quarter (the migration freeze before the "
            "holiday code freeze), cannot increase the replication "
            "factor (storage budget), cannot raise the client timeout "
            "above 250 milliseconds (the mobile team's page budget), "
            "and must hold p99.9 at or below 120 milliseconds during "
            "flash-sale peaks with the existing cluster."
        ),
    },
}

#: the frozen split (authoring-time decision; recorded per problem and
#: re-verified at freeze)
DEV_IDS = tuple(sorted(k for k, p in AUTHORED_PROBLEMS.items()
                       if p["split"] == "DEV"))
HOLDOUT_IDS = tuple(sorted(k for k, p in AUTHORED_PROBLEMS.items()
                           if p["split"] == "HOLDOUT"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _script_sha() -> str:
    return _sha(Path(__file__).read_text())


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_author() -> int:
    if FREEZE_PATH.exists():
        print("REFUSED: benchmark already frozen — authoring after "
              "freeze would be benchmark tampering (Art. LIX)",
              file=sys.stderr)
        return 2
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    families = sorted({p["domain_family"]
                       for p in AUTHORED_PROBLEMS.values()})
    per_family: Dict[str, List[str]] = {}
    for pid, p in AUTHORED_PROBLEMS.items():
        per_family.setdefault(p["domain_family"], []).append(pid)
    for fam in families:
        assert len(per_family[fam]) == 2, \
            f"family {fam} must have exactly 2 problems (Art. XLIX)"
    assert families == sorted(DOMAIN_FAMILIES), \
        f"domain families must be the directive's list, got {families}"
    corpus = {
        "artifact_type": "R458_BENCHMARK_CORPUS/1.0.0",
        "authored_at_utc": _now(),
        "authoring_discipline": (
            "SYMPTOMS_AND_CONSTRAINTS_ONLY — the R452 assay standard: "
            "quantitative symptoms, hard constraints kept hard, no "
            "solution class seeded; authored BEFORE any R458 model run "
            "(anti-circularity, Art. VIII / LIX / BS-016)"),
        "n_problems": len(AUTHORED_PROBLEMS),
        "n_domain_families": len(families),
        "domain_families": families,
        "problems_per_family": {k: sorted(v)
                                for k, v in per_family.items()},
        "split": {
            "dev_ids": list(DEV_IDS),
            "holdout_ids": list(HOLDOUT_IDS),
            "split_rule": (
                "one DEV + one HOLDOUT problem per family, fixed at "
                "authoring time; each pair differs in industry, scale, "
                "and failure physics so the holdout probes transfer, "
                "not memorized numbers"),
            "holdout_policy": (
                "the BLIND HOLDOUT is mechanically refused to every "
                "driver except the blind-test phase; the blind test "
                "refuses to run until the dev-phase record exists "
                "(ordering enforced in r458_model_capability_benchmark."
                "py); NO tuning of prompts, thresholds, operators, "
                "retrieval, or model selection against the holdout "
                "(Art. LIX)"),
        },
        "problems": {k: dict(v) for k, v in AUTHORED_PROBLEMS.items()},
    }
    CORPUS_PATH.write_text(json.dumps(corpus, indent=1, sort_keys=True))
    print(f"authored {len(AUTHORED_PROBLEMS)} problems "
          f"({len(families)} families) -> {CORPUS_PATH}")
    print(f"  DEV      : {', '.join(DEV_IDS)}")
    print(f"  HOLDOUT  : {', '.join(HOLDOUT_IDS)}")
    return 0


def cmd_freeze() -> int:
    # fail-closed: no result artifact may exist before freeze (Art. LIX)
    existing = [a for a in _RESULT_ARTIFACTS
                if (REPO_ROOT / a).exists()
                or list(OUT_ROOT.glob(a.replace("r458mc_", "*"))) ]
    if existing:
        print(f"REFUSED: result artifacts exist before freeze: "
              f"{existing} — the corpus must be frozen before results "
              f"are looked at (Art. LIX / BS-016)", file=sys.stderr)
        return 2
    if not CORPUS_PATH.exists():
        print("corpus missing — run `author` first", file=sys.stderr)
        return 2
    corpus = json.loads(CORPUS_PATH.read_text())
    per_problem = {}
    for pid, p in corpus["problems"].items():
        per_problem[pid] = {
            "content_sha256": _sha(p["text"]),
            "domain_family": p["domain_family"],
            "split": p["split"],
        }
    corpus_hash = _sha(json.dumps(corpus["problems"],
                                  sort_keys=True))
    freeze = {
        "artifact_type": "R458_BENCHMARK_FREEZE/1.0.0",
        "frozen_at_utc": _now(),
        "corpus_path": str(CORPUS_PATH.relative_to(REPO_ROOT)),
        "corpus_hash": corpus_hash,
        "benchmark_script_sha256": _script_sha(),
        "n_problems": corpus["n_problems"],
        "split": corpus["split"],
        "per_problem": per_problem,
        "freeze_discipline": (
            "Art. LIX + BS-016: the corpus, the split, and every "
            "problem's content sha256 are committed here BEFORE any "
            "R458 model arm runs; the quality instrument "
            "(r458_quality_instrument.py) freezes its metric "
            "definitions under the same fail-closed discipline; drift "
            "against this record fails every downstream driver"),
        "anti_circularity": (
            "the corpus was authored before any R458 run; the holdout "
            "is sealed by this freeze and mechanically refused to all "
            "non-blind-test drivers; no dev-phase result, prompt, "
            "threshold, or model-selection decision may reference "
            "holdout content (Art. VIII: the benchmark instrument is "
            "not part of the intervention)"),
    }
    FREEZE_PATH.write_text(json.dumps(freeze, indent=1, sort_keys=True))
    print(f"frozen: {FREEZE_PATH}")
    print(f"  corpus_hash={corpus_hash[:16]}…")
    print(f"  script_sha256={freeze['benchmark_script_sha256'][:16]}…")
    return 0


def cmd_verify() -> int:
    if not FREEZE_PATH.exists() or not CORPUS_PATH.exists():
        print("freeze/corpus missing", file=sys.stderr)
        return 2
    freeze = json.loads(FREEZE_PATH.read_text())
    corpus = json.loads(CORPUS_PATH.read_text())
    failures: List[str] = []
    for pid, rec in freeze["per_problem"].items():
        p = corpus["problems"].get(pid)
        if not p:
            failures.append(f"{pid}: missing from corpus")
            continue
        if _sha(p["text"]) != rec["content_sha256"]:
            failures.append(f"{pid}: content drift vs freeze")
        if p["split"] != rec["split"] or \
                p["domain_family"] != rec["domain_family"]:
            failures.append(f"{pid}: metadata drift vs freeze")
    cur_hash = _sha(json.dumps(corpus["problems"], sort_keys=True))
    if cur_hash != freeze["corpus_hash"]:
        failures.append("corpus hash drift")
    if freeze["benchmark_script_sha256"] != _script_sha():
        failures.append("benchmark script drift vs freeze "
                        "(authoring script modified after freeze)")
    if failures:
        print("VERIFY FAIL:", *failures, sep="\n  ", file=sys.stderr)
        return 1
    print("verify OK: corpus byte-identical to the freeze; "
          "14 problems / 7 families; split intact")
    return 0


def load_corpus() -> Dict[str, Dict[str, Any]]:
    """The corpus for drivers (the frozen artifact only, never the
    module constant — the freeze is the authority, Art. X)."""
    if not FREEZE_PATH.exists():
        raise SystemExit("benchmark not frozen — run author+freeze first")
    return json.loads(CORPUS_PATH.read_text())


def assert_dev_only(case_id: str) -> None:
    """Mechanical BS-016 guard: refuse holdout problems outside the
    blind-test phase."""
    freeze = json.loads(FREEZE_PATH.read_text())
    holdout = set(freeze["split"]["holdout_ids"])
    if case_id in holdout:
        raise SystemExit(
            f"REFUSED (BS-016): {case_id} is a BLIND HOLDOUT problem — "
            f"only the blind-test phase may run it, and only after the "
            f"dev-phase record exists")


def assert_blind_test_allowed() -> None:
    """The blind test may run ONLY after the dev-phase record exists
    (ordering enforced — the holdout is never the tuning surface)."""
    dev_record = REPO_ROOT / "R458" / "MODEL_CAPABILITY_BENCHMARK.json"
    if not dev_record.exists():
        raise SystemExit(
            "REFUSED (BS-016): the blind test may not run before the "
            "dev-phase model-capability record exists (ordering "
            "discipline: DEVELOPMENT SET -> FREEZE -> BLIND TEST)")


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in (
            "author", "freeze", "verify"):
        print(__doc__)
        return 2
    return {"author": cmd_author, "freeze": cmd_freeze,
            "verify": cmd_verify}[sys.argv[1]]()


if __name__ == "__main__":
    raise SystemExit(main())
