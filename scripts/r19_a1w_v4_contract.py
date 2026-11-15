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
