#!/usr/bin/env python3
"""r19_a1w_v4_contract.py — SYS_A1_INT_V4 (F30 iteration 3, AM19 D2).

Evolution basis, typed from the COMMITTED per-pair bytes of
eval/battery_a1w_r11.json (Art. VI: no contract change without a byte
type):

SYS_A1_INT_WB (r16) achieved: intervention feasibility mean 2.389 ->
1.5 (AM16 D1 sharply-reduced arm MET) with novelty UP (2.556). But the
STRICT <=0.25 clause is NOT met (overall 1.367), and the residual gap
concentrates on the novelty-carrying pairs (fgap 3-4 where nd 4).

BYTE TYPE of the residual failure (the highest-gap answers):
  bench-p06-water-biofilm (fgap=4, nd=4) ALREADY itemizes a
  standard-vs-intervention bill — and its own ledger note concedes the
  departure rides a component that does not exist yet:
  "The encapsulated nitrification inhibitor would need to be
  developed". The judge scores the development program, not the
  mechanism's elegance. V3's bill section ASKED the generator to
  disclose development needs and engineer them out; the generator
  disclosed and KEPT them. Disclosure was not enough — the rule must
  bind the MECHANISM CHOICE, not the bookkeeping.

V4 (this file) therefore adds, on top of SYS_A1_INT_WB (Steps 0/1/1b/2
and the section structure are UNCHANGED):
  STEP 3+ — PROCUREMENT RULE: every Intervention-Bill line must be
  (a) already present in the problem's stated infrastructure, (b) a
  procurable standard catalog item of the same class as the standard
  practice's own components, or (c) a parameter/duty/procedure/
  configuration change to stated equipment (no hardware cost).
  NO-DEVELOPMENT RULE: a mechanism whose physics requires a component
  that is not procurable today is OUT OF SCOPE — choose a mechanism
  whose novelty lives in the CHANGE (how existing components are
  driven, arranged, combined, scheduled, or parameterized), not in a
  NEW THING. "Would need to be developed", "custom formulation",
  "novel material", "prototype", "new sensor type" in ANY bill line
  or note = typed defect (LEDGER_DEV_NEED), engineered out BEFORE the
  answer ships.
  BOTH failure modes are named forbidden (the V3 pair, now completed):
  conventionalizing the mechanism to win the burden ledger, and
  hiding a development program inside the ledger rows. Novelty lives
  in the CHANGE; feasibility lives in the COMPONENTS.

The battery problems are fixed and untouched (Art. LXXIX); the judge,
rubric, k=3, and axis definitions are the CANONICAL battery metric
(eval/battery_metrics.py, Art. 16 — one canonical metric). The pilot
is typed MECHANICS_PILOT: a direction probe on the pre-declared
hard-7 subset, NOT the gate battery (which requires >=30 pairs).
"""
import re

# Marker scan for the NO-DEVELOPMENT RULE (machine-enforced in the
# pilot driver's repair loop; findings are disclosed, never hidden).
DEV_NEED_MARKERS = re.compile(
    r"need[s]? to be developed|would (?:need|require)[^.]{0,40}develop"
    r"|custom[- ](?:formulation|compound|blend|material)|novel "
    r"(?:material|additive|coating|polymer|sensor)|prototype"
    r"|new sensor type|must be developed|requires development"
    r"|special(?:ly)? formulated", re.I)

SYS_A1_INT_V4 = """NOVEL INTERVENTION IDEATION — WEIGHT-BOUND V4
(required — the two properties are ORTHOGONAL and BOTH mandatory; do
not trade one for the other):

STEP 0 — ANSWER THE QUESTION ASKED: this question asks for an
INTERVENTION — how to prevent, mitigate, reduce, or fix the failure.
The answer is a DESIGN OR OPERATIONAL CHANGE to the equipment, its
materials, its configuration, its duty, or its maintenance. A
monitoring observable, a leading indicator, or a detection scheme is
NOT an answer to an intervention question: it watches the failure
instead of preventing it. Do not propose a predictor.

STEP 1 — INVENT THE MITIGATION (this is where novelty lives): ask
"what change to design, material, configuration, duty, or procedure
directly reduces the DRIVING MECHANISM of the failure that standard
practice does not make?" The mitigation must be a NEW MECHANISM: not
a restatement of the standard mitigation, not "monitor it more
closely", not "do the standard practice more often". Name in one
line what standard practice does, and in one line why your
mitigation is a genuine departure.

STEP 1b — ADJACENT-TECHNIQUE CLEARANCE (mandatory): name the CLOSEST
existing mitigation practice from ANY industry and state in one line
what makes yours different. A mitigation that merely relabels a
textbook fix is a defect: if the closest practice in ANY industry IS
your mitigation, invent a further departure.

STEP 2 — THE WEIGHT RULE (this is where feasibility lives, and it
BINDS): the mitigation must be deliverable WITHIN the standard
practice's existing infrastructure and cost class. Prefer mechanism
classes that ride existing practice: a material or coating
substitution, an additive-package change, a duty or schedule or
configuration change, a fit/tolerance/geometry change within
existing machining, a procedural change, or a swap to procurable
standard parts. A mechanism that requires NEW HARDWARE CLASSES —
major redesign, new tooling, exotic instruments, plant-level
changes — is OUT OF SCOPE for this problem: choose a DIFFERENT
mechanism that carries the same physics through a lighter
implementation. The pattern to emulate: novelty lives in the
MECHANISM, weight lives in the IMPLEMENTATION — a genuinely new
mechanism delivered through a boring, procurable implementation. If
the honest version of your mechanism cannot satisfy the weight rule,
go back to STEP 1 and invent a different mechanism; do not keep the
heavy mechanism and hope the ledger hides it.

STEP 3 — THE PROCUREMENT RULE (V4, BINDS HARDER THAN V2/V3): every
line of the Intervention Bill must be exactly one of:
  (a) an item ALREADY PRESENT in the problem's stated infrastructure
      (equipment, instruments, materials, data streams the problem
      itself states exist);
  (b) a PROCURABLE STANDARD CATALOG ITEM of the same class as the
      standard practice's own components (a vendor ships it today);
  (c) a PARAMETER / DUTY / PROCEDURE / CONFIGURATION change to
      equipment already in (a) — the physics or the operating point
      changes, no new hardware.
NO-DEVELOPMENT RULE: a mechanism whose physics requires a component
that is NOT procurable today is OUT OF SCOPE — no exceptions, no
"it would be simple to develop". Go back to STEP 1 and choose a
mechanism whose novelty lives in the CHANGE (how existing components
are driven, arranged, combined, scheduled, or parameterized), not in
a NEW THING. In particular: an additive or coating that ships only as
a standard product is fine; an additive or coating that must be
FORMULATED or DEVELOPED for this use is forbidden — express the same
physics through a shipped product, an existing material used outside
its common application, a duty change, or a procedure change.
TWO failure modes are forbidden, and EITHER alone fails the answer:
  - hiding a development program inside the ledger rows ("would need
    to be developed", "custom formulation", "novel material",
    "prototype") — the judge scores the development program;
  - conventionalizing the mechanism to win the burden ledger — the
    judge scores the lost novelty.
The resolution is not a compromise between them: keep the NEW
MECHANISM, deliver it ENTIRELY through items of classes (a)/(b)/(c).

STEP 4 — PROVE THE WEIGHT: the IMPLEMENTATION BILL must be itemized
against the standard practice's own bill (what the standard fix
already uses vs what yours adds or replaces, with each of your rows
tagged (a), (b), or (c)), and the BURDEN LEDGER must CONCLUDE
same-or-lower burden class FROM THOSE ITEMIZED ROWS. A ledger that
concludes "same burden" while the bill shows new equipment is a
defect. Feasibility is proven by the itemized comparison, not
asserted.

REQUIRED SECTIONS (each labeled, IN THIS ORDER):
NOVELTY STATEMENT (INTERVENTION) — the question-answered sentence
first (what is being proposed), then what standard practice does vs
your mitigation, the adjacent-technique clearance, and the mechanism
by which the intervention attacks the failure's driving physics.
PHYSICS CHECK — the governing physical relation showing the
intervention reduces the failure mechanism, with a one-to-two-line
magnitude verification; a number that fails its own physics is a
defect.
IMPLEMENTATION BILL — components, materials, instruments, procedure
for INSTALLING and RUNNING the intervention, itemized against the
standard practice's own bill, every one of YOUR rows tagged (a),
(b), or (c) per the PROCUREMENT RULE.
BURDEN LEDGER (STANDARD-PRACTICE PARITY) — the itemized comparison
from the bill, concluding same-or-lower burden class; if heavier
anywhere, say where and why the physics forces it (this is a typed
defect for the machine, not an acceptable conclusion).
EXECUTABLE TEST — the falsification test as a competent engineer
could run it: protocol, instruments, pass/fail thresholds, duration,
kill criterion. For an intervention the falsifier validates
EFFECTIVENESS (the failure rate or magnitude DROPS with the
intervention), not a correlation."""


# ---------------------------------------------------------------------------
# V4-predictor marker scans (byte-typed from the r11 predictor rows):
# the 4 retargeted pairs (eval-new06/07/10/12) carry fgap 2-3 WITHOUT any
# development-need marker — their bills are already "existing /
# off-the-shelf" everywhere. The residual burden the judge scores is the
# SCHEME-TRUST BUILDING: baseline-data collection programs (eval-new12:
# "Baseline resonance database (implementation: record healthy bearing
# signatures during manufacturing)") and calibration/validation campaigns
# ("calibrate during commissioning", "validate over a trial period").
# The predictor analog of a development program is a data or validation
# program: V4 forbids it the same way — the scheme's trust must come
# from data that ALREADY EXISTS, not from a program that must run first.
# ---------------------------------------------------------------------------
BASELINE_PROGRAM_MARKERS = re.compile(
    r"record (?:healthy|baseline|reference)[^.]{0,30}?(?:signatures?|"
    r"data|readings?|profiles?)|collect(?:ing|ion of)? (?:a )?baseline"
    r"|baseline (?:database|dataset|data[- ]collection|library)"
    r"|gather (?:historical|failure|baseline) (?:data|records?)"
    r"|historical failure (?:data|records?)\s+(?:to|for|over|spanning)"
    r"|(?:build|establish|compile) (?:a |an )?(?:reference|signature|"
    r"healthy|failure) (?:library|database|baseline|history)"
    r"|training (?:period|phase|data)\s+(?:of|over|collection|spanning)",
    re.I)

COMMISSIONING_PROGRAM_MARKERS = re.compile(
    r"calibrat\w+ (?:during|over|in|at) (?:commissioning|operation|a "
    r"trial|service|installation)|commissioning (?:period|phase|study|"
    r"campaign|program)|trial (?:period|run|campaign)\s+(?:to|before|"
    r"over|spanning)|tun(?:e|ing) (?:the )?thresholds? (?:in|during|"
    r"over|after|once) (?:operation|service|deployment|the field)"
    r"|field (?:trial|validation) (?:period|campaign|study)"
    r"|validat\w+ (?:the )?(?:predictor|model|algorithm|thresholds?|"
    r"scheme) (?:over|during|across) (?:a |an |the )?(?:trial|week|"
    r"month|season|campaign|period)", re.I)


def predictor_violations(ans):
    """V4-predictor typed violations (matched text snippets only, never
    hidden; the repair directive quotes them back to the generator)."""
    hits = {}
    b = sorted({m.group(0).lower() for m in
                BASELINE_PROGRAM_MARKERS.finditer(ans)})
    c = sorted({m.group(0).lower() for m in
                COMMISSIONING_PROGRAM_MARKERS.finditer(ans)})
    d = sorted({m.group(0).lower() for m in
                DEV_NEED_MARKERS.finditer(ans)})
    if b:
        hits["BASELINE_PROGRAM"] = b
    if c:
        hits["COMMISSIONING_PROGRAM"] = c
    if d:
        hits["DEV_NEED"] = d
    return hits


# Verbatim from r11_a1f_v3_generate.SYS_A1_V2 (the shared base contract;
# duplicated literally so this module stays import-side-effect-free).
SYS_A1_V2 = (
    "You are a careful engineer. Answer the user's problem directly "
    "with concrete engineering: the design or leading indicator, its "
    "threshold, and the falsification test. Respect every stated "
    "constraint verbatim. English only. Label every number as USER "
    "CONSTRAINT, CALCULATED, or ASSUMPTION with a one-line engineering "
    "rationale.")

SYS_A1F_V4 = SYS_A1_V2 + """

SAME-CLASS NOVELTY IDEATION V4 (required — novelty and feasibility are
BOTH mandatory and are achieved in the SAME delivery class; do not
trade one for the other):

STEP 1 — DELIVER THE STANDARD PRACTICE'S OUTCOME CLASS (this is where
novelty lives): FIRST name what the field-standard practice for this
problem class DELIVERS — a DESIGN CHANGE (hardware, material, or
procedure modification that prevents or mitigates the failure) or a
MONITORING/INDICATION scheme (a measured or inferred leading
indicator). Your proposal MUST deliver that SAME class of outcome.
The novelty lives in the MECHANISM inside that class: a genuinely
different physical mechanism, architecture, or inference achieving
the same class of outcome. Name in one line what the standard
practice delivers, and in one line your mechanism's genuine
departure from it.

FORBIDDEN FAILURE MODES (all measured on prior contracts, named here
so you do not repeat them):
- SUBSTITUTING A SENSOR WHERE THE STANDARD PRACTICE INTERVENES.
- CONVENTIONALIZING TO WIN THE BURDEN COMPARISON: restating the
  standard mechanism with new words is not a departure.
- HIDING A DATA OR VALIDATION PROGRAM IN THE BILL ROWS: a predictor
  whose trust must be BUILT by a program (record healthy baselines,
  collect a reference dataset, calibrate during commissioning,
  validate over a trial period) carries that program as burden — the
  judge scores it. The scheme's trust must come from data that
  ALREADY EXISTS per the problem's own statements.

STEP 2 — MATCH THE STANDARD PRACTICE'S BURDEN CLASS (this is where
feasibility lives): your implementation bill must use the SAME
instrument, material, and service classes as the standard-practice
solution itself.

STEP 2B — THE DATA-SOURCE RULE (V4, BINDS HARD):
  (i) EVERY input stream must be data the problem states ALREADY
      EXISTS and is ALREADY RECORDED or exported (a stated sensor,
      stated log, stated telemetry feed, stated inspection record).
      A predictor that requires NEW instrumentation to be deployed,
      commissioned, or connected is OUT OF SCOPE.
  (ii) EVERY reference, baseline, or threshold must be DERIVABLE NOW
      from data the problem states exists, from stated
      specs/nameplate/geometry, or from a stated physical relation —
      show the derivation and label it CALCULATED. "Record healthy
      signatures", "collect a baseline dataset", "gather historical
      failures" are typed defects (BASELINE_PROGRAM): go back to
      STEP 1 and choose a mechanism whose reference comes from
      already-recorded data, stated specs, or physics.
  (iii) NO COMMISSIONING OR VALIDATION PROGRAM (COMMISSIONING_PROGRAM
      defect): no calibrate-during-commissioning, no validate-over-a-
      trial-period, no tune-in-operation. If the mechanism needs a
      tuning campaign to become trustworthy, choose a mechanism whose
      decision rule is a stated-physics relation or an
      already-exported data comparison.
  TWO failure modes remain forbidden together: conventionalizing the
  mechanism to satisfy (i)-(iii), and hiding the program inside a
  bill row or an ASSUMPTION. The resolution is the same as V4's:
  keep the NEW MECHANISM (novelty in the computed observable and its
  inference), deliver its trust ENTIRELY from stated-existing data,
  stated specs, and stated physics.

REQUIRED SECTIONS (each labeled):
NOVELTY STATEMENT — one line: what the standard practice delivers
(its class and mechanism); one line: your same-class mechanism
departure; then the failure-physics connection that makes your
mechanism work.
PHYSICS CHECK — the governing physical relation for your mechanism and
a one-to-two-line magnitude verification; a number that fails its own
physics is a defect.
IMPLEMENTATION BILL — components, materials, instruments, procedure;
every input stream tagged ALREADY-RECORDED (with the problem's own
wording for it), every reference/threshold tagged DERIVED (with its
derivation source: stated data / stated spec / stated physics). This
section is where feasibility is EARNED.
BURDEN LEDGER (STANDARD-PRACTICE PARITY) — installability,
operability, maintenance, rough cost class against the
standard-practice solution. The ledger's expected conclusion is SAME
burden class, DIFFERENT mechanism. If your approach is heavier
somewhere, say where and why it is worth it.
EXECUTABLE TEST — the falsification test as a competent engineer
could run it: protocol, instruments, pass/fail thresholds, duration,
kill criterion; validated against ALREADY-RECORDED data or a stated
physical relation, never against a to-be-collected campaign."""


def contract_for(question_type):
    """V4 arm selection: interventions keep SYS_A1_INT_V4; predictors
    move to SYS_A1F_V4 (this module). The change is isolated to the
    retargeted predictor pairs; the other 8 predictor pairs ride r11
    byte-identical rows per the pre-registered byte map."""
    qt = (question_type or "").lower()
    return SYS_A1_INT_V4 if qt.startswith("intervention") else SYS_A1F_V4

