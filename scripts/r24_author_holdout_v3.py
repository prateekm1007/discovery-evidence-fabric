#!/usr/bin/env python3
"""r24_author_holdout_v3.py — AM24 D3: author the fresh sealed holdout
v3 (loop-owned per the Art. 28 addendum + AM24 D3).

DIVISION OF LABOR (typed, seal-preserving):
  AUTHOR:    builder-r20s1 (this script) — problems ONLY.
  EXECUTOR:  the peer session (builder-r20s2) — one-shot generation
             under claim-before-work, receiving problems only.
  SCORER:    the auditor — with their PRIVATE rubric (0-4), which the
             author NEVER writes, sees, or speculates about.
  BURN:      after scoring (v3 becomes DEV; v4 fresh next).

STRESS DESIGN (from AM24 findings):
  - interventions carry EXPLICIT allowed-measures enumerations inside
    the constraint text (the F36 read: the machine must draw mechanism
    and bill rows ONLY from the listed classes);
  - exclusion cues ("no ...", "without ...", "retrofit only") stress
    hard-exclusion compliance;
  - predictors name the failure-DEFINING indicator so a correct answer
    monitors the PRIMARY stated indicator (the HO2-11/HO2-13 lesson);
  - feasibility parity is stressed: every intervention mechanism is
    expressible with procurable, standard-practice classes.

The machine under test is FROZEN BEFORE these problems exist (the
V6.1 contract commit precedes this authoring commit in git history —
provable order, cited in the pre-registration).
"""
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

IV_Q = ("What engineering change, intervention, or design would "
        "prevent or mitigate the stated failure under the stated "
        "constraint, and what concrete test would falsify the "
        "proposed approach?")
PD_Q = ("Propose the most cost-effective measurable leading indicator "
        "(predictor) for the stated failure, its operating threshold, "
        "and the concrete test that would validate or kill the "
        "predictor.")

problems = [
    # ---------------- intervention (6): allowed-measures stress ------
    {"problem_id": "HO3-01-cooling-tower-legionella",
     "device": "induced-draft cooling tower serving a hospital chilled-water plant, with film-fill packing and a basin",
     "failure": "Legionella pneumophila colonizes the warm basin and film fill; quarterly sampling returns >1000 CFU/L, forcing shutdown-and-shock protocols that interrupt hospital cooling",
     "failure_mode": "basin-biofilm-legionella-colonization",
     "constraint": "retrofit only: no change to the tower structure or fill packing; allowed measures: side-stream filtration with automatic backwash or in-duct UV irradiation on the recirculation loop only; continuous chemical biocide dosing is excluded; disinfection residual must stay below 0.2 mg/L free oxidant at the basin outlet",
     "domain": "water-systems",
     "source": "builder_holdout_v3", "contamination_tag": None,
     "question_type": "intervention-proposal", "question": IV_Q,
     "user_variables": ["use only the two allowed measure classes",
                        "keep plant availability above 99 percent",
                        "sampling cadence stays monthly"],
     "clarification_answer": None, "followup_finding": None,
     "split": "HOLDOUT"},
    {"problem_id": "HO3-02-offshore-riser-internal-corrosion",
     "device": "10-inch carbon-steel subsea gas-production riser with water condensation at the dewpoint band, 1200 m water depth",
     "failure": "top-of-line condensation corrosion thins the riser wall at the 8 o'clock section; ILI runs show 0.9 mm/year loss against a 3.2 mm wall, with a predicted through-wall date in 6 years",
     "failure_mode": "top-of-line-condensation-corrosion",
     "constraint": "allowed measures: batch corrosion-inhibitor injection at the riser inlet or in-line inspection pigging frequency increase only; no internal coating or lined spool re-placement is permitted because the line cannot be shut down; inhibitor concentration is capped at 25 ppm for environmental discharge limits",
     "domain": "subsea-pipelines",
     "source": "builder_holdout_v3", "contamination_tag": None,
     "question_type": "intervention-proposal", "question": IV_Q,
     "user_variables": ["no shutdown or line break is permitted",
                        "injection points are limited to the existing umbilical",
                        "ILI tool access is every 18 months at most"],
     "clarification_answer": None, "followup_finding": None,
     "split": "HOLDOUT"},
    {"problem_id": "HO3-03-vaccine-coldchain-overtemp",
     "device": "pharmacy-grade vaccine refrigerator bank (six 400 L cabinets) in a regional distribution hub, with 300 vials of mRNA product",
     "failure": "defrost cycles and door-open recoveries let cabinet air exceed +8 C for 12-20 minutes about three times per week; two excursions per quarter ruin a shelf of product worth 40k",
     "failure_mode": "defrost-and-recovery-overtemperature",
     "constraint": "procedure-and-controls only: allowed measures are controller setpoint and defrost-interval retuning, plus a door-discipline procedure with an audible alarm; no compressor, evaporator, or cabinet replacement is permitted; alarm delay after door closure must stay under 60 seconds so staff can restock",
     "domain": "cold-chain",
     "source": "builder_holdout_v3", "contamination_tag": None,
     "question_type": "intervention-proposal", "question": IV_Q,
     "user_variables": ["no hardware replacement is permitted",
                        "staff cannot add door-opening logging paperwork",
                        "the cabinets hold validated setpoint certificates"],
     "clarification_answer": None, "followup_finding": None,
     "split": "HOLDOUT"},
    {"problem_id": "HO3-04-paper-dryer-lint-fire",
     "device": "paper-machine dryer section, 40 cylinders, with hood exhaust ducts and a lint accumulation history at the rope-return area",
     "failure": "lint layers 3-8 mm thick build on duct bends and rope pulleys; a hot-bearing spark ignited duct lint last year, causing a 14-hour outage, and near-miss temperature excursions now occur monthly",
     "failure_mode": "duct-lint-accumulation-ignition",
     "constraint": "allowed measures: hood ventilation rebalancing and duct access-door cleaning procedure with IR surface-temperature monitoring only; replacement of dryer cans, ropes, or duct geometry is excluded; cleaning may only occur during the weekly 4-hour planned stop",
     "domain": "paper-machinery",
     "source": "builder_holdout_v3", "contamination_tag": None,
     "question_type": "intervention-proposal", "question": IV_Q,
     "user_variables": ["no duct rerouting or can replacement",
                        "cleaning windows are the weekly 4-hour stop only",
                        "IR cameras already exist at six fixed points"],
     "clarification_answer": None, "followup_finding": None,
     "split": "HOLDOUT"},
    {"problem_id": "HO3-05-immersion-fluid-degradation",
     "device": "single-phase immersion-cooling tank (synthetic ester dielectric) hosting 38 GPU servers, 55 C bulk fluid, 1.2 m deep",
     "failure": "fluid acid number rises 0.09 mgKOH/g per year and dissolved copper from server heatsinks darkens the fluid; dielectric breakdown margin has fallen from 55 kV to 41 kV against a 35 kV trip line",
     "failure_mode": "ester-fluid-oxidation-and-copper-dissolution",
     "constraint": "allowed measures: side-loop fluid fine filtration with activated-alumina cartridges or scheduled partial top-up with fresh inhibitor-blended fluid only; full fluid replacement or a fluid-chemistry redesign is excluded this budget cycle; tank downtime may not exceed one 6-hour window per quarter",
     "domain": "datacenter-cooling",
     "source": "builder_holdout_v3", "contamination_tag": None,
     "question_type": "intervention-proposal", "question": IV_Q,
     "user_variables": ["no full fluid replacement is permitted",
                        "downtime budget is one 6-hour window per quarter",
                        "cartridge housings already exist on the side loop"],
     "clarification_answer": None, "followup_finding": None,
     "split": "HOLDOUT"},
    {"problem_id": "HO3-06-greenhouse-emitter-clogging",
     "device": "drip-irrigation fertigation system over 2.4 hectares of greenhouse tomatoes, with 16 mm laterals and pressure-compensating emitters",
     "failure": "calcium-phosphate precipitate and root fragments clog about 8 percent of emitters per season; outlet uniformity drops below 85 percent by week 14, stressing fruit quality; flushing crews recover only half the loss",
     "failure_mode": "emitter-precipitate-and-root-clogging",
     "constraint": "allowed measures: acid-dosing interval retuning (nitric acid, pH floor 5.6) and screen-filter flush automation only; emitter or lateral redesign is excluded; root-growth intrusion must be addressed by flushing procedure, not by chemicals above the stated pH floor",
     "domain": "greenhouse-irrigation",
     "source": "builder_holdout_v3", "contamination_tag": None,
     "question_type": "intervention-proposal", "question": IV_Q,
     "user_variables": ["no emitter or lateral redesign",
                        "acid floor is pH 5.6 for root safety",
                        "the fertilizer recipe is fixed by contract"],
     "clarification_answer": None, "followup_finding": None,
     "split": "HOLDOUT"},
    # ---------------- predictor (6): primary-indicator stress ---------
    {"problem_id": "HO3-07-elevator-door-opener-trips",
     "device": "traction elevator with a DC door operator and belt-driven door hanger rollers serving 60 openings/day per door",
     "failure": "door hanger rollers flatten and the operator belt slips; the door stalls and the controller trips on door-timeout about once per month, trapping passengers between floors",
     "failure_mode": "hanger-roller-flattening-belt-slip",
     "constraint": "the controller already logs door-motor current per operation and door close-duration; the failure-DEFINING event is the door-timeout trip, so the predictor must trigger on the operator's measured current signature (the primary indicator); floor-vibration or cabin-acceleration sensors are not installed and must not be assumed",
     "domain": "vertical-transport",
     "source": "builder_holdout_v3", "contamination_tag": None,
     "question_type": "predictor-design", "question": PD_Q,
     "user_variables": ["use only existing door-motor current and "
                        "close-duration logs; warn >=14 days before a "
                        "timeout trip; <=1 false alarm per 10 "
                        "elevators/month"],
     "clarification_answer": None, "followup_finding": None,
     "split": "HOLDOUT"},
    {"problem_id": "HO3-08-irrigation-pump-waterhammer",
     "device": "centrifugal irrigation pump with a 2.4 km PVC main, check valve at the pump, and air valves at two high points",
     "failure": "sudden power-off events send a return surge that fatigues the PVC main at glued joints; two joint bursts in three years each flooded a field for a day",
     "failure_mode": "return-surge-joint-fatigue",
     "constraint": "pressure transducers already log at 10 Hz at the pump header and at high point 2; the failure-DEFINING quantity is the peak pressure transient amplitude at the pump header (the primary indicator); soil or joint-strain instrumentation does not exist and must not be assumed",
     "domain": "irrigation-networks",
     "source": "builder_holdout_v3", "contamination_tag": None,
     "question_type": "predictor-design", "question": PD_Q,
     "user_variables": ["use only existing 10 Hz pressure traces; warn "
                        "when cumulative surge dose approaches the "
                        "joint fatigue budget; <=2 false alerts per "
                        "season"],
     "clarification_answer": None, "followup_finding": None,
     "split": "HOLDOUT"},
    {"problem_id": "HO3-09-bakery-oven-gasket-degradation",
     "device": "rotating-rack bakery oven with a rope door gasket and steam injection, 14 bakes/day",
     "failure": "the door gasket hardens and shrinks; steam leaks at the door frame and the oven can no longer recover to setpoint between racks, so crust quality fails specification about twice a month",
     "failure_mode": "door-gasket-hardening-steam-leak",
     "constraint": "the oven controller already records steam-valve duty and cavity-temperature recovery time per bake; the failure-DEFINING symptom is the cavity temperature-recovery time after rack loading (the primary indicator); door-frame IR imaging is not installed and must not be assumed",
     "domain": "food-processing",
     "source": "builder_holdout_v3", "contamination_tag": None,
     "question_type": "predictor-design", "question": PD_Q,
     "user_variables": ["use only existing recovery-time and steam-duty "
                        "logs; warn >=10 bakes before a quality "
                        "failure; <=1 false alarm per 60 bakes"],
     "clarification_answer": None, "followup_finding": None,
     "split": "HOLDOUT"},
    {"problem_id": "HO3-10-forklift-watering-events",
     "device": "warehouse fleet of 18 lead-acid forklift batteries on opportunity charging with a shared watering cart",
     "failure": "opportunity charging drives electrolyte loss; cells watered late run low and sulfate on plate tops, and two batteries per year lose over 20 percent capacity and are retired early",
     "failure_mode": "electrolyte-loss-plate-top-sulfation",
     "constraint": "chargers already log charge amp-hours and end-of-charge voltage per battery, and the watering cart logs fills per battery; the failure-DEFINING quantity is the electrolyte level deficit the fills compensate (the primary indicator); single-cell impedance probes are not installed and must not be assumed",
     "domain": "material-handling",
     "source": "builder_holdout_v3", "contamination_tag": None,
     "question_type": "predictor-design", "question": PD_Q,
     "user_variables": ["use only charger and watering-cart logs; warn "
                        ">=7 days before a capacity-loss threshold "
                        "crossing; <=1 false alarm per fleet per month"],
     "clarification_answer": None, "followup_finding": None,
     "split": "HOLDOUT"},
    {"problem_id": "HO3-11-mri-chiller-surge",
     "device": "air-cooled screw chiller rejecting heat for an MRI suite, with a variable-speed condenser fan bank and a fixed evaporator flow",
     "failure": "at high ambient the chiller surges intermittently; a surge trip aborts the magnet's cooling interlock and cancels scans; four scan-session cancellations last quarter each cost 9k",
     "failure_mode": "high-ambient-compressor-surge",
     "constraint": "the chiller controller already logs suction pressure, discharge pressure, and condenser fan staging every 10 seconds; the failure-DEFINING precursor is the condenser approach temperature (the primary indicator); compressor vibration sensors are not installed and must not be assumed",
     "domain": "hvac-medical",
     "source": "builder_holdout_v3", "contamination_tag": None,
     "question_type": "predictor-design", "question": PD_Q,
     "user_variables": ["use only existing 10 s pressure and fan-stage "
                        "logs; warn >=20 minutes before a surge trip; "
                        "<=1 false alarm per 30 cooling days"],
     "clarification_answer": None, "followup_finding": None,
     "split": "HOLDOUT"},
    {"problem_id": "HO3-12-paver-screed-wear",
     "device": "asphalt paver with a vibratory screed plate set paving 1.5 km of arterial road per week",
     "failure": "screed plate bottoms wear thin at the leading edge; mat thickness drifts 4 mm below target before crews notice, forcing a 200 m mill-and-repave correction twice a season",
     "failure_mode": "screed-plate-edge-thinning",
     "constraint": "the paver logs screed vibration frequency, amplitude, and extension-plate position per shift, and grade control logs mat thickness sensor readings per meter; the failure-DEFINING quantity is the mat thickness sensor deviation at constant screed settings (the primary indicator); plate-thickness ultrasonic probes are not installed and must not be assumed",
     "domain": "road-paving",
     "source": "builder_holdout_v3", "contamination_tag": None,
     "question_type": "predictor-design", "question": PD_Q,
     "user_variables": ["use only existing paver and grade-control "
                        "logs; warn >=150 m before a 4 mm drift "
                        "correction; <=1 false alarm per 10 km"],
     "clarification_answer": None, "followup_finding": None,
     "split": "HOLDOUT"},
]

problems.sort(key=lambda p: p["problem_id"])
domains = sorted({p["domain"] for p in problems})
v2_domains = sorted({p["domain"] for p in json.loads(
    __import__("subprocess").run(
        ["git", "show",
         "origin/audit/r11-auditor-verdict-20261114:audit/holdout_v2/"
         "holdout_v2_problems.json"],
        capture_output=True, check=True).stdout.decode())["problems"]})
overlap_v2 = set(domains) & set(v2_domains)
assert not overlap_v2, f"v3 domains collide with v2: {overlap_v2}"
dev_domains = set()
for f in ("eval/problems.json", "eval/problems_dev12.json"):
    pl = json.loads((REPO / f).read_text())
    pl = (pl if isinstance(pl, list) else pl.get("problems", []))
    dev_domains |= {str(p.get("domain") or "") for p in pl}
overlap_dev = set(domains) & dev_domains
assert not overlap_dev, f"v3 domains collide with dev/bench pools: " \
                        f"{overlap_dev}"

payload = {"record": "HOLDOUT_V3_PROBLEMS/1.0.0 (author: builder-r20s1, "
                      "owner-delegated per AM24 D3; problems ONLY — the "
                      "PRIVATE rubric is the auditor's instrument and "
                      "is NEVER authored, seen, or assumed by the "
                      "author)",
           "n_problems": len(problems),
           "intervention": sum(1 for p in problems
                               if p["question_type"].startswith(
                                   "intervention")),
           "predictor": sum(1 for p in problems
                            if p["question_type"].startswith(
                                "predictor")),
           "problems": problems}
canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"))
sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
prereg = {
    "record": "HOLDOUT_V3_PREREGISTRATION/1.0.0",
    "registered_at": "2026-11-15",
    "registered_by": ("builder-r20s1 (owner-delegated authoring per "
                      "AM24 D3 and the Art. 28 addendum; problems "
                      "ONLY)"),
    "article": ("Art.7 sealed instruments — AM24 D3 reassigns v3 "
                "authoring to the loop; the PRIVATE rubric remains "
                "the auditor's instrument, never authored or seen by "
                "the author; the executor is the PEER session "
                "(cross-actor seal: author != executor)"),
    "selection_sha256": sha,
    "selection_recipe": ("sha256 over json.dumps(payload, sort_keys="
                         "True, ensure_ascii=False, separators=(',',"
                         "':')) of the payload in "
                         "audit/holdout_v3/holdout_v3_problems.json"),
    "n_problems": len(problems),
    "tiers": {"K": 10, "D": 2},
    "intervention": 6, "predictor": 6,
    "domains": domains,
    "domain_freshness": ("all 12 domains are DISJOINT from holdout v2's "
                         "twelve (proven by assertion against the "
                         "committed v2 problems file) and from every "
                         "dev/bench pool domain (proven by assertion "
                         "against eval/problems.json + "
                         "eval/problems_dev12.json); holdout v1's "
                         "exact domain labels are NOT readable by the "
                         "author (v1 was the auditor's sealed set, "
                         "burned before this round) — typed "
                         "assumption: the 12 labels also do not "
                         "overlap v1's subject areas as described in "
                         "the auditor's v1 verdict"),
    "stress_design": ("interventions carry EXPLICIT allowed-measures "
                      "enumerations and exclusion cues in the "
                      "constraint text (the F36 read); predictors name "
                      "the failure-DEFINING primary indicator (the "
                      "HO2-11/HO2-13 lesson); feasibility parity "
                      "stressed — every mechanism is expressible with "
                      "procurable standard-practice classes"),
    "machine_freeze_order": ("the machine under test (V6.1: "
                             "SYS_A1_INT_V61 + SYS_A1F_V5, claim "
                             "c-0014 pre-registration 5acb63012) was "
                             "COMMITTED BEFORE this authoring commit — "
                             "provable in git history; the author "
                             "tunes nothing to these problems "
                             "afterwards (the executor runs the "
                             "frozen machine byte-unchanged)"),
    "one_shot_protocol": [
        "1. Auditor (or the loop per Art. 28) reviews and authorizes "
        "the sealed set.",
        "2. The PEER session claims work_id holdout-v3-generation "
        "(EXECUTOR), receives holdout_v3_problems.json one-shot, "
        "generates answers ONCE with the frozen type-aware machine "
        "(intervention -> SYS_A1_INT_V61, predictor -> SYS_A1F_V5, "
        "byte-unchanged); no rubric, no iteration, no judge calls.",
        "3. The author session (builder-r20s1) is the VERIFIER: "
        "recomputes generation integrity from committed bytes "
        "(Art. 13, never re-runs).",
        "4. Auditor scores with the PRIVATE rubric (0-4, K coverage/D "
        "quality, red-flag penalties; constraint-fit >=3/4 is the "
        "AM24 D2 acceptance).",
        "5. BURN: holdout v3 becomes DEV; fresh v4 for the next "
        "sealed test."],
    "custody": ("audit/holdout_v3/ on the audit branch; the PRIVATE "
                "rubric NEVER reaches builder/pipeline/judge; the "
                "author never writes a scoring instrument"),
    "burn_after_use": True,
    "status": ("SEALED_REGISTERED — awaiting auditor authorization "
               "and the peer's one-shot claim (holdout-v3-generation)"),
}

outdir = REPO / "audit" / "holdout_v3"
outdir.mkdir(parents=True, exist_ok=True)
(outdir / "holdout_v3_problems.json").write_text(
    json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
    encoding="utf-8")
(outdir / "PREREGISTRATION.json").write_text(
    json.dumps(prereg, indent=1, ensure_ascii=False) + "\n",
    encoding="utf-8")
print(f"problems authored: {len(problems)} "
      f"(iv {prereg['intervention']} / pd {prereg['predictor']})")
print(f"domains: {domains}")
print(f"distinct from v2 ({len(v2_domains)} domains) and dev/bench "
      f"pools: PROVEN by assertion")
print(f"selection_sha256: {sha[:16]}…")
