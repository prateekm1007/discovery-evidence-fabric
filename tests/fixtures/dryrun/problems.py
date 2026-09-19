"""tests/fixtures/dryrun/problems.py — CONTROLLED dry-run problems.

Three problems across three declared families (thermal-management,
fluid-power, structural-dynamics) with frozen fixture evidence and
deterministic fixture response texts.

EPISTEMIC STATUS (read first):
- These problems are MACHINE-AUTHORED test material for measuring the
  dry-run candidate funnel (can the real EngineRun execute without
  live credentials and produce a reproducible portfolio + funnel?).
- They are NOT blind fresh problems (Art. LXXIX) and NOT discovery
  evidence (Art. LXXVII): no discovery capability may be claimed from
  them, and every artifact they produce carries DRY_RUN_FIXTURE
  provenance with r506_eligible=False.
- The naive synthesis text deliberately carries NO falsification
  test: the machine's own deterministic classify gate
  (a2/classify.py: "no concrete falsification test") rejects it,
  which unlocks the production exploration-grid path (E16-F). This
  exercises the weak-naive -> grid -> gauntlet -> portfolio path with
  deterministic inputs; no gate, threshold, prompt, or instrument is
  touched to achieve it.
- Fixture texts were validated against the REAL validators before
  use: span_derivation_check MEASURED on all 18 texts,
  _testable_prediction_check testable on all grid/operator texts,
  deduplicate_candidates DISTINCT=6 per problem, adversarial kill
  texts overall=KILLED on all three problems (see
  scripts/r510_dryrun_proof.py and tests/test_r510_dryrun.py).
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

BUNDLE_ID = "r510-dryrun/1"

# ---------------------------------------------------------------- P1
P1: Dict[str, Any] = {
    "problem_id": "dry-p1",
    "device": "engine cooling system",
    "failure": "coolant vapor leak under driving conditions",
    "failure_mode": "vapor leak",
    "constraint": "no engine removal",
    "family": "thermal-management",
}
P1E1: Dict[str, Any] = {
    "id": "dry-p1-e1",
    "title": "Engine cooling system vapor leak acoustic monitoring",
    "abstract": ("Acoustic emission sensors mounted on engine cooling "
                 "system manifolds detect vapor bubble formation in "
                 "coolant channels before visible leakage occurs. Field "
                 "trials recorded bubble collapse frequencies between 40 "
                 "and 90 kilohertz during driving conditions. Detection "
                 "threshold was set at three standard deviations above "
                 "baseline manifold noise."),
    "content_hash": "ev1",
    "retrieval_timestamp": "2026-01-01T00:00:00Z",
    "source": "dry-run-fixture",
}
P1E2: Dict[str, Any] = {
    "id": "dry-p1-e2",
    "title": "Coolant channel corrosion under thermal cycling in engine "
             "cooling systems",
    "abstract": ("Repeated thermal cycling degrades coolant channel "
                 "walls in engine cooling. Wall thinning above 0.2 "
                 "millimeters per year preceded vapor leak events in "
                 "fleet observations. Corrosion changes channel geometry "
                 "and raises local vapor nucleation rates under driving "
                 "conditions."),
    "content_hash": "ev2",
    "retrieval_timestamp": "2026-01-01T00:00:00Z",
    "source": "dry-run-fixture",
}
_P1_S1 = ("detect vapor bubble formation in coolant channels before "
          "visible leakage occurs")
_P1_S2 = ("Repeated thermal cycling degrades coolant channel walls in "
          "engine cooling")

P1_BODIES: List[Tuple[str, Tuple[str, ...]]] = [
    ("xfer", (
        "Centrifugal vapor separation transfers aerospace bleed-air "
        "moisture separator physics into engine coolant circuits; "
        "rotation flings dense liquid outward while vapor migrates "
        "to the core vent",
        "Install a clamp-on centrifugal vapor separator in the upper "
        "coolant hose without engine removal",
        "Vapor diverts to the vent before reaching the radiator; leak "
        "alarms trigger 10 times earlier",
        "separator bowl diameter",
        "Separator cuts undetected vapor leak duration from 40 hours "
        "to under 4 hours at 90 Celsius coolant temperature",
        "separator bearing seizure under vibration load", _P1_S1)),
    ("invert", (
        "Passive gravity vapor trap inverts active acoustic sensing; "
        "a high-point chamber collects rising vapor while liquid "
        "coolant continues past the trap outlet",
        "Weld a high-point vapor trap chamber into the heater return "
        "line without engine removal",
        "Trapped vapor volume indicates leak rate; dashboard warning "
        "fires after 50 milliliters accumulate",
        "trap chamber volume",
        "Trap fills to the 50 milliliter warning level within 6 hours "
        "of leak onset at idle coolant flow",
        "trap outlet clogging from corrosion debris", _P1_S2)),
    ("simple", (
        "Sacrificial sight-glass plug gives the simplest vapor "
        "indication; a glass insert clouds when vapor fraction rises "
        "in the adjacent coolant channel",
        "Replace the drain plug with a sight-glass vapor indicator "
        "without engine removal",
        "Drivers see clouding within 2 days of leak onset; inspection "
        "cost drops below 5 dollars per check",
        "sight-glass diameter",
        "Glass clouding appears within 48 hours when vapor fraction "
        "exceeds 3 percent at 85 Celsius",
        "glass fouling from coolant additives", _P1_S1)),
    ("hybrid", (
        "Thermoelectric cold finger hybridizes thermal condensation "
        "with acoustic confirmation; a Peltier element chills a probe "
        "so vapor condenses while the acoustic sensor counts collapse "
        "events in coolant channels",
        "Clamp a Peltier cold finger probe with acoustic pickup onto "
        "the thermostat housing without engine removal",
        "Condensation rate plus acoustic counts localize leaks within "
        "10 centimeters; false alarms fall below 1 per year",
        "Peltier drive current",
        "Cold finger condenses 2 milliliters per hour at 12 volts "
        "drive while acoustic counts exceed 100 per minute",
        "Peltier element burnout from overvoltage", _P1_S1)),
    ("constraint", (
        "External ultrasonic collar derives leak location strictly "
        "from outside the pipe; phased transducers map bubble "
        "formation along coolant channels with no disassembly",
        "Strap an ultrasonic phased-array collar around the lower "
        "radiator hose without engine removal",
        "Collar maps bubble formation sites within 5 centimeters; "
        "installation takes under 30 minutes",
        "transducer ring spacing",
        "Collar locates test bubble injection within 5 centimeters "
        "at 60 kilohertz drive frequency",
        "collar slip from hose vibration", _P1_S1)),
    ("operator", (
        "Acoustic emission sensing transfers directly into coolant "
        "manifolds; manifold-mounted sensors detect vapor bubble "
        "formation in coolant channels before visible leakage occurs",
        "Bond acoustic emission sensors onto both coolant manifolds "
        "without engine removal",
        "Manifold sensing detects leaks 20 hours earlier than "
        "pressure-drop alarms at highway load",
        "sensor bond thickness",
        "Bonded sensors alarm within 1 hour when injected vapor "
        "reaches 1 percent fraction at 2000 rpm",
        "sensor bond delamination from heat soak", _P1_S1)),
]

# ---------------------------------------------------------------- P2
P2: Dict[str, Any] = {
    "problem_id": "dry-p2",
    "device": "hydraulic lift actuator",
    "failure": "pressure decay during sustained hold",
    "failure_mode": "seal leak",
    "constraint": "no system drain-down",
    "family": "fluid-power",
}
P2E1: Dict[str, Any] = {
    "id": "dry-p2-e1",
    "title": "Hydraulic lift actuator pressure decay during sustained hold",
    "abstract": ("Pressure decay exceeds 5 bar per hour during sustained "
                 "hold in hydraulic lift actuators with worn rod seals. "
                 "Test rigs logged decay curves across 200 hold cycles at "
                 "210 bar working pressure. Seal extrusion opens leak "
                 "paths after 1000 hold cycles."),
    "content_hash": "ev3",
    "retrieval_timestamp": "2026-01-01T00:00:00Z",
    "source": "dry-run-fixture",
}
P2E2: Dict[str, Any] = {
    "id": "dry-p2-e2",
    "title": "Actuator seal extrusion under sustained hydraulic pressure",
    "abstract": ("Seal extrusion opens leak paths after 1000 hold cycles "
                 "under sustained hydraulic pressure above 180 bar. "
                 "Extruded nitrile shows nibbling at the gland edge in "
                 "lift actuators held overnight. Replacement with "
                 "fabric-reinforced seals cut decay by half."),
    "content_hash": "ev4",
    "retrieval_timestamp": "2026-01-01T00:00:00Z",
    "source": "dry-run-fixture",
}
_P2_S3 = ("pressure decay exceeds 5 bar per hour during sustained hold")
_P2_S4 = ("seal extrusion opens leak paths after 1000 hold cycles")

P2_BODIES: List[Tuple[str, Tuple[str, ...]]] = [
    ("xfer", (
        "Self-energizing pressure seal transfers aerospace hydraulic "
        "coupling physics into lift actuators; rising pressure wedges "
        "the seal tighter instead of extruding it",
        "Fit self-energizing wedge seals into the actuator rod gland "
        "without system drain-down",
        "Decay drops below 1 bar per hour; hold extends past 72 hours "
        "at 210 bar",
        "wedge angle",
        "Wedge seals hold 210 bar for 72 hours with decay under 1 bar "
        "per hour at 40 Celsius oil temperature",
        "wedge cracking under pressure spikes", _P2_S3)),
    ("invert", (
        "Gravity-seated ball check inverts the piloted hold valve; a "
        "free ball seals the lift port when flow stops, removing the "
        "pilot stage that leaks",
        "Insert a gravity ball-check cartridge in the lift port "
        "without system drain-down",
        "Pilot-stage leak path eliminated; overnight decay falls to "
        "zero measurable bar loss",
        "ball diameter",
        "Ball check shows zero measurable decay over 12 hours at 200 "
        "bar with ISO 46 oil",
        "ball seat brinelling from impact load", _P2_S4)),
    ("simple", (
        "Color-change wear ring gives the simplest seal state "
        "indication; a dyed backup ring exposes bright color when "
        "extrusion starts in the actuator gland",
        "Swap the backup ring for a color-change wear ring without "
        "system drain-down",
        "Extrusion visible at inspection; unplanned failures drop "
        "below 1 per 5 years",
        "dye layer thickness",
        "Color exposure appears after 800 hold cycles at 190 bar "
        "before measurable decay starts",
        "dye washout from hot oil", _P2_S4)),
    ("hybrid", (
        "Magneto-hydraulic seal hybridizes magnetic stiffening with "
        "hydraulic sealing; iron particles in the gland fluid align "
        "under a coil and choke leak paths during sustained hold",
        "Wrap an excitation coil around the actuator gland and dose "
        "magneto fluid without system drain-down",
        "Aligned particles cut decay by 80 percent on demand; coil "
        "off restores normal motion",
        "coil turn count",
        "Energized seal cuts decay from 5 bar per hour to under 1 bar "
        "per hour at 24 volts drive",
        "particle settling during long idle", _P2_S3)),
    ("constraint", (
        "External pressure capsule derives hold integrity strictly "
        "from outside the circuit; a clamped capsule around the "
        "cylinder traps a reference volume whose decay mirrors "
        "internal pressure decay",
        "Clamp a reference capsule around the actuator barrel without "
        "system drain-down",
        "External reading tracks internal decay within 0.5 bar; no "
        "ports opened",
        "capsule volume",
        "Capsule tracks a 5 bar per hour internal decay within 0.5 "
        "bar over 24 hours",
        "capsule seal creep under sun load", _P2_S3)),
    ("operator", (
        "Seal extrusion monitoring transfers directly into lift "
        "actuators; gland sensors watch seal extrusion opens leak "
        "paths after 1000 hold cycles",
        "Mount extrusion feeler gauges on the actuator gland without "
        "system drain-down",
        "Gauges warn 200 cycles before measurable decay at rated 210 "
        "bar hold",
        "feeler stiffness",
        "Gauges deflect 0.1 millimeters by cycle 800 at 200 bar "
        "sustained hold pressure",
        "feeler fatigue fracture", _P2_S4)),
]

# ---------------------------------------------------------------- P3
P3: Dict[str, Any] = {
    "problem_id": "dry-p3",
    "device": "bridge cable damper",
    "failure": "resonance amplification under crosswind load",
    "failure_mode": "vortex-induced vibration",
    "constraint": "no cable replacement",
    "family": "structural-dynamics",
}
P3E1: Dict[str, Any] = {
    "id": "dry-p3-e1",
    "title": "Bridge cable damper resonance under crosswind load",
    "abstract": ("Resonance amplification exceeds damping capacity "
                 "above 15 meters per second crosswind on bridge cable "
                 "dampers. Field records show second mode lock-in "
                 "persists for hours under steady crosswind. Tuned "
                 "dampers detuned by ice accretion lost half their "
                 "stroke."),
    "content_hash": "ev5",
    "retrieval_timestamp": "2026-01-01T00:00:00Z",
    "source": "dry-run-fixture",
}
P3E2: Dict[str, Any] = {
    "id": "dry-p3-e2",
    "title": "Stay cable vibration modes in crosswind conditions",
    "abstract": ("Second mode lock-in persists for hours under steady "
                 "crosswind on stay cables near bridge towers. Helical "
                 "fillets disrupting spanwise correlation cut amplitudes "
                 "by two thirds in wind tunnel runs at 12 meters per "
                 "second."),
    "content_hash": "ev6",
    "retrieval_timestamp": "2026-01-01T00:00:00Z",
    "source": "dry-run-fixture",
}
_P3_S5 = ("resonance amplification exceeds damping capacity above 15 "
          "meters per second")
_P3_S6 = ("second mode lock-in persists for hours under steady crosswind")

P3_BODIES: List[Tuple[str, Tuple[str, ...]]] = [
    ("xfer", (
        "Helical strake transfer adapts chimney-stack vortex spoiling "
        "to bridge cables under steady crosswind; a helical fillet "
        "breaks spanwise correlation so second mode lock-in cannot "
        "organize during hours of crosswind",
        "Wrap helical fillet strakes around the cable near the damper "
        "without cable replacement",
        "Amplitudes fall below one cable diameter at 20 meters per "
        "second crosswind",
        "fillet pitch",
        "Strakes hold amplitude under 0.5 diameters at 20 meters per "
        "second in tunnel runs",
        "fillet ice bridging in freezing rain", _P3_S6)),
    ("invert", (
        "De-tuned dead mass inverts active damping under steady "
        "crosswind; a loose collar sliding on the cable dissipates "
        "lock-in energy through friction over hours instead of tuned "
        "resonance absorption",
        "Slip a friction collar onto the cable beside the damper "
        "without cable replacement",
        "Friction dissipates 60 percent of modal energy per cycle "
        "across wind speeds",
        "collar clearance",
        "Collar cuts second mode amplitude by 60 percent at 10 meters "
        "per second crosswind",
        "collar seizure from corrosion", _P3_S6)),
    ("simple", (
        "Paint-band telltale gives the simplest resonance indication; "
        "contrasting bands blur visibly when amplitude exceeds the "
        "service limit",
        "Paint contrast bands on the cable at the damper station "
        "without cable replacement",
        "Crews spot exceedance from the deck; inspection needs no "
        "instruments",
        "band width",
        "Bands blur at amplitudes above 1 diameter under 12 meters "
        "per second crosswind",
        "paint fading from ultraviolet exposure", _P3_S5)),
    ("hybrid", (
        "Magnetorheological damper hybridizes fluid damping with "
        "field control; iron-fluid viscosity rises under coil current "
        "exactly when resonance amplification exceeds damping capacity",
        "Swap damper oil for magnetorheological fluid with a sensor "
        "coil without cable replacement",
        "Field-on damping triples during events; field-off restores "
        "normal compliance",
        "coil current limit",
        "Fluid raises damping force from 2 to 6 kilonewtons at 3 "
        "amperes during lock-in",
        "fluid sedimentation during calm months", _P3_S5)),
    ("constraint", (
        "Deck-mounted laser vibrometer derives cable motion strictly "
        "without touching the cable; the beam tracks second mode "
        "lock-in persists for hours under steady crosswind",
        "Bolt a laser vibrometer to the deck rail aimed at the cable "
        "without cable replacement",
        "Remote readings match contact sensors within 5 percent; zero "
        "cable access needed",
        "beam spot size",
        "Vibrometer tracks 2 hertz cable motion within 5 percent at "
        "50 meters range",
        "beam loss in heavy rain", _P3_S6)),
    ("operator", (
        "Crosswind lock-in monitoring transfers directly into cable "
        "dampers; deck accelerometers watch second mode lock-in "
        "persists for hours under steady crosswind",
        "Bolt accelerometers to the damper housing without cable "
        "replacement",
        "Housing data warns 30 minutes before amplitude limits at "
        "design wind",
        "mount resonant frequency",
        "Housing accelerometers flag lock-in within 5 minutes at 14 "
        "meters per second crosswind",
        "mount bolt loosening from vibration", _P3_S6)),
]

# ------------------------------------------------------------- builders
# Angle prompt keys: substrings of the frozen EXPLORATION_ANGLES
# instructions (candidate_diversity.py) — the fixture matches the
# angle-specific call by prompt_contains.
ANGLE_KEYS = {
    "xfer": "DIFFERENT industry",
    "invert": "Invert or rearrange",
    "simple": "SIMPLEST physical",
    "hybrid": "two DIFFERENT physical domains",
    "constraint": "strictly from the stated constraint",
}


def full_text(body: Tuple[str, ...], boundary: str) -> str:
    """Full candidate text (synthesis/grid/operator format): the
    ensemble line-anchored fields incl. falsification test + span."""
    mech, interv, effect, var, test, fail, span = body
    return (
        "MECHANISM: %s\nINTERVENTION: %s\nEXPECTED_EFFECT: %s\n"
        "PREDICTED_EFFECT: %s\nNOVEL_DESIGN_VARIABLE: %s\n"
        "TESTABLE_PREDICTION: %s\nFALSIFICATION_TEST: %s\n"
        "KNOWN_FAILURE_MODES: %s\nBOUNDARY_CONDITIONS: %s\n"
        "MECHANISM_SOURCE_SPAN: %s" % (
            mech, interv, effect, effect, var, test, test, fail,
            boundary, span))


def naive_text(body: Tuple[str, ...], boundary: str) -> str:
    """Naive synthesis text: identical fields EXCEPT no falsification
    test (no TESTABLE_PREDICTION / FALSIFICATION_TEST lines). The
    span stays (VERIFY must pass on evidence); the machine's own
    classify gate rejects the candidate for the missing test, which
    unlocks the exploration grid (E16-F production path)."""
    mech, interv, effect, var, _test, fail, span = body
    return (
        "MECHANISM: %s\nINTERVENTION: %s\nEXPECTED_EFFECT: %s\n"
        "PREDICTED_EFFECT: %s\nNOVEL_DESIGN_VARIABLE: %s\n"
        "KNOWN_FAILURE_MODES: %s\nBOUNDARY_CONDITIONS: %s\n"
        "MECHANISM_SOURCE_SPAN: %s" % (
            mech, interv, effect, effect, var, fail, boundary,
            span))


def attack_text(kill_basis: str) -> str:
    """Deterministic adversarial response: all dimensions PASS except
    a CONTRADICTION KILLED with a two-sided record-bound basis (the
    a2 burden-of-proof instrument requires the claim value AND the
    divergent evidence value from the record). The machine parses,
    corrects, and adjudicates for real; the burden ledger decides."""
    lines = [
        "UNSUPPORTED_MECHANISM: PASS - mechanism stated with evidence span",
        "WEAK_TRANSFER: PASS - transfer within same system class",
        "OBVIOUS_COMBINATION: PASS - not a combination of known techniques",
        "PRIOR_ART: PASS - no named disclosure in held evidence",
        "CONTRADICTION: KILLED \u2014 %s" % kill_basis,
        "BOUNDARY_FAILURE: PASS - within declared boundary",
        "ENGINEERING_INFEASIBILITY: PASS - feasible as specified",
        "REGULATORY_INCOMPATIBILITY: PASS - no regime cited",
        "OVERALL: KILLED",
        "REASON: contradiction defeats the naive claim",
    ]
    return "\n".join(lines) + "\n"


P1_KILL = ("bonded manifold sensors cannot separate vapor-bubble "
           "collapse signatures in the 40 to 90 kilohertz band from "
           "cavitation erosion noise occupying the same band per "
           "EVIDENCE dry-p1-e1 / 40-90kHz signal versus same-band noise")
P2_KILL = ("candidate claims gauges warn 200 cycles before decay with "
           "0.1 millimeter deflection by cycle 800, but EVIDENCE "
           "dry-p2-e2 records extrusion opens leak paths after 1000 "
           "hold cycles while decay is already measurable \u2014 the gauge "
           "signals after leak paths open, contradicting the "
           "early-warning claim / 800-cycle claim versus 1000-cycle "
           "evidence")
P3_KILL = ("candidate claims housing data warns 30 minutes before "
           "amplitude limits at 14 meters per second, but EVIDENCE "
           "dry-p3-e2 records second mode lock-in persisting for "
           "hours with destructive amplitudes \u2014 the warning arrives "
           "after damage accumulates, contradicting the 30-minute "
           "claim / 30-minute claim versus hours-long persistence")

P1_BOUNDARY = "no engine removal; ambient minus 20 to 60 Celsius"
P2_BOUNDARY = "no system drain-down; oil ISO 46 at 40 Celsius"
P3_BOUNDARY = "no cable replacement; crosswind to 20 meters per second"


def problem_pack(problem: Dict[str, Any],
                 evidence: List[Dict[str, Any]],
                 bodies: List[Tuple[str, Tuple[str, ...]]],
                 boundary: str, kill_basis: str) -> Dict[str, Any]:
    """Assemble one controlled problem's full fixture bundle spec
    list + metadata. Spec ORDER is declaration order only — matching
    is by specificity precedence, never first-match-wins."""
    by_label = dict(bodies)
    specs = [
        {"purpose_prefix": "synthesis",
         "content": naive_text(by_label["operator"], boundary)},
        {"purpose_prefix": "operator_",
         "content": full_text(by_label["operator"], boundary)},
        {"purpose_exact": "attack",
         "content": attack_text(kill_basis)},
    ]
    for angle, key in ANGLE_KEYS.items():
        specs.append({"purpose_prefix": "diversity_exploration",
                      "prompt_contains": key,
                      "content": full_text(by_label[angle], boundary)})
    texts = {label: full_text(body, boundary)
             for label, body in bodies}
    return {"problem": problem, "evidence": evidence,
            "boundary": boundary, "specs": specs, "texts": texts,
            "naive": naive_text(by_label["operator"], boundary),
            "kill_basis": kill_basis}


PACKS = {
    "dry-p1": problem_pack(P1, [P1E1, P1E2], P1_BODIES, P1_BOUNDARY,
                           P1_KILL),
    "dry-p2": problem_pack(P2, [P2E1, P2E2], P2_BODIES, P2_BOUNDARY,
                           P2_KILL),
    "dry-p3": problem_pack(P3, [P3E1, P3E2], P3_BODIES, P3_BOUNDARY,
                           P3_KILL),
}
