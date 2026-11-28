#!/usr/bin/env python3
"""r29_a1w_v72_contract.py — SYS_A1_INT_V72 = the V7.1 contract + the
AM27 D2 CONVERSION BIND (the premise-validity kill + the gap-1 row
conversions + the F38 operational-loss pricing).

AM27 direction verbatim (the acceptance owner): "Kill the premise-
flawed row and convert the seven gap-1 rows. bench-p06 needs a
topology-valid mechanism (no reversal without a second path). The
seven gap-1 rows (micro-roughened vane, MEMS dimples, silica
interlayer, Al-on-steel sleeve, silica packet, added sensor channel,
graded co-firing) must become pure catalog-part or procedure
changes. Accept: feasibility |gap| <= 0.25 AND novelty delta >= 0.5
on >= 30 pairs, auditor-judged."

Byte-typed basis (the auditor's 18-row re-judgment at audit tip
d7540c6fe, eval/auditor_r28_adjudication.json — 8 rows at gap 1 +
bench-p06 at gap 2, PLUS bench-p10's F38 finding):
- bench-p06: "PREMISE FLAW: dead-end main has no second supply path,
  cannot reverse flow" (the auditor self-correction the machine
  caught) -> the PREMISE-VALIDITY clause.
- bench-p04: "micro-roughened leading edge: procurable surface
  treatment, cavitation-suppression effect unproven" -> the r27
  tuning relocated CNC machining into micro-blasting at a target Ra;
  still a surface-treatment DEVELOPMENT -> forbidden class 5.
- bench-p08: "micro-dimple texture ... MEMS comb process development"
  -> the dimple etch -> forbidden classes 5+6.
- bench-p09: "hydrophilic silica interlayer: catalog silica but
  food-contact lamination/migration compliance dev" -> the added
  gravure coating/cure steps -> forbidden class 6.
- bench-p11: "aluminium sleeve bonded to steel shaft: catalog
  materials, CTE bond risk is design detail" -> the new dissimilar-
  metal bonded interface -> forbidden class 7.
- eval-new01: "hydrophilic silica packet: catalog desiccant but
  solvent-selective reabsorption unproven" -> the off-spec material
  function dependence -> forbidden class 9.
- eval-new03: "dual-channel differential pressure: adds sensor
  channel, medical device hardware+regulatory dev" -> forbidden
  class 8.
- eval-sofc-thermal-cycling: "graded/bilayer glass-phase seal ...
  graded co-firing is process dev" -> already the r27 CUSTOM_MATERIAL
  class (the intergranular-phase composition rows; the disclosed
  V7.1 residual) — the V7.2 machine path keeps that scan leg and the
  repair directive names the relocation (a single standard commercial
  sealant applied per its supplier spec; the arrangement novelty
  elsewhere).
- bench-p01: "catalog-class membrane humidifier but anode-side
  integration/water balance unproven" + the Nafion(TM) brand rows +
  "selectively permeates water vapor" -> forbidden class 9 + the
  generic-class palette (the r26 NAMED_VARIANT scan leg stays).
- bench-p10: "8h-on/4h-off duty cycle is ~33% daily energy
  curtailment, unpriced in a burden ledger that counts only PLC
  wiring hours" (F38) -> the OPERATIONAL-LOSS PRICING clause.

The machine path is otherwise BYTE-UNCHANGED in logic (zai-gateway
generation + critic + question-type gate + typed scans [base +
constraint-fit + catalog-v2 + standard-bill r27 + operational-loss
r29 + conversion r29] + the machine's own NEUTRAL repair directives,
REPAIR_BUDGET=2, K_GEN=1, judge-blind — no outcome feedback, no
judged numbers in any prompt; the AM27 direction is a structural
bind). Predictor side: UNCHANGED (SYS_A1F_V5, holdout-v3-proven).
"""
from r70_v75_deliverable_bind import V75_DELIVERABLE_BIND  # noqa: E402
from r27_a1w_v71_contract import (  # noqa: F401
    SYS_A1_INT_V71, V71_REPAIR_DIRECTIVE)
from r27_a1w_v71_contract import SYS_A1F_V5  # noqa: F401
from r26_a1w_v7_contract import MACHINE_REPAIR_DIRECTIVE  # noqa: F401

V72_CONVERSION_BIND = """

CONVERSION BIND (V7.2 — extends the STANDARD-BILL BIND's forbidden
classes and adds the premise-validity + operational-loss clauses;
OUTRANKS mechanism preference):

J. PREMISE VALIDITY (a mechanism that contradicts the problem's
   stated topology is a typed defect, not a feasibility risk): any
   mechanism that REVERSES or bidirectionally redirects a flow must
   NAME the physical second supply path, return loop, or cross-tie
   that enables the reversal. If the system is dead-end,
   single-supply, or otherwise has no second path (as stated in the
   problem or in your own text), flow-reversal mechanisms are OUT OF
   SCOPE — compose a mechanism that works WITH the stated topology:
   unidirectional flushing or scouring pulses, injection or dosing
   schedules, setpoint or duty changes, venting arrangements.
K. FOUR MORE FORBIDDEN CLASSES (the auditor-adjudicated gap-1
   shapes — each is real development burden hiding behind catalog
   parts; recompose onto the arrangement axis):
   5. SURFACE-TREATMENT DEVELOPMENT on the deployed part: blasted,
      grit-treated, laser-textured, etched, dimpled, or otherwise
      re-finished surfaces specified to a target (an Ra value, a
      dimple geometry, a texture). Developing or qualifying a
      surface treatment for THIS part is process development even
      at "stock parameters" — the surface effect is unproven. The
      deployed parts are used AS-SOLD.
   6. PROCESS STEPS ADDED BEYOND THE STANDARD PRACTICE'S OWN BILL:
      a coating, cure, adhesive bond, lamination, anneal, sinter,
      plating, or deposition step the standard practice's own bill
      does not already perform. A process class the standard
      practice's own bill DOES perform, run on the equipment the
      problem states exists at that practice's own parameters, is a
      standard operation and is allowed.
   7. DISSIMILAR-METAL BONDED INTERFACES: bonding a catalog metal
      part onto another metal part where the BOND ITSELF is the
      load-bearing or compensating element (a sleeve bonded to a
      shaft, a pad bonded across a CTE mismatch). Qualifying a new
      metal-to-metal bonded interface is development. Elastomer and
      polymer-sheet laminates bonded on the standard practice's OWN
      existing bonding infrastructure (the class the problem's own
      practice already performs) are arrangement-class and allowed.
   8. ADDED SENSING CHANNELS ON REGULATED DEVICES: where the device
      class is regulated (medical, implantable, clinical, sterile),
      adding any NEW physical sensing channel (a second pressure
      transducer, an added electrode set, a new flow sensor) is
      hardware AND regulatory development regardless of how
      catalog-standard the part is. Detection must ride EXISTING
      signals: the existing sensors, the motor/drive current
      signature, derived observables of already-measured channels,
      or standard process observations.
   9. OFF-SPEC MATERIAL FUNCTION CLAIMS: a catalog material is used
      ONLY as its supplier specifies it. Claiming a selective
      function the spec does not state ("selectively permeates",
      "selectively recirculates", a desiccant that "reabsorbs
      solvent", a membrane that excludes exactly your contaminant)
      makes the mechanism DEPEND on an unproven functional property.
      Use every catalog part at its stated, stock function and put
      the mechanism in the ARRANGEMENT (placement, count, schedule,
      duty split, interconnection, operating point).
L. OPERATIONAL-LOSS PRICING (the burden ledger prices LOSSES, not
   just hardware): any duty cycle, curtailment, or derate applied to
   the system's PRIMARY OUTPUT (energy delivery, production
   throughput, service delivery) must STATE the operational loss in
   the BURDEN LEDGER — a number (energy/output/throughput lost per
   day or per cycle) or an explicit zero — and count it against
   parity. A schedule that moves the gated windows off production
   hours (night reset windows, non-producing intervals) must SAY the
   avoided loss is zero. "Operation unchanged" does not price a duty
   cycle; an unpriced curtailment is a typed defect.
"""

SYS_A1_INT_V72 = (SYS_A1_INT_V71 + V72_CONVERSION_BIND
                   + V75_DELIVERABLE_BIND)  # F75 (AM63 d1)

# The V7.2 repair directive EXTENDS the V71 neutral directive with the
# conversion + premise-validity + pricing relocations (still NEUTRAL:
# typed findings only, no outcome feedback, no judged numbers).
V72_REPAIR_DIRECTIVE = """MACHINE REPAIR PASS (typed findings on your draft below):
{findings}
Resolve ONLY these typed findings in a complete revised answer; keep
the mechanism, structure, and all satisfied parts as-is. For
STANDARD_BILL findings: recompose the flagged row onto the
arrangement axis (a standard catalog part at stock grade, a standard
operation at rated parameters, a bilayer/stack of two standard
materials, a duty-cycle schedule) per the STANDARD-BILL BIND — never
by asserting procurability for a custom item. For CONVERSION
findings: recompose per the CONVERSION BIND — PREMISE_TOPOLOGY_
INVALID means the mechanism contradicts the stated topology (compose
one that works WITH it); SURFACE_TREATMENT_DEV / ADDED_PROCESS_STEP /
BONDED_INTERFACE_DEV / ADDED_SENSING_CHANNEL_ON_REGULATED_DEVICE /
MATERIAL_FUNCTION_CLAIM mean the mechanism depends on a forbidden
development or off-spec class (use parts AS-SOLD at their stated
function, ride existing signals and existing process classes, put
the novelty in the arrangement). For UNPRICED_OPERATIONAL_LOSS:
state the operational loss (a number or an explicit zero with the
non-producing-hours schedule) in the burden ledger and count it
against parity.
"""


def contract_for_v72(question_type):
    """V7.2 arm map: interventions carry the conversion bind;
    predictors stay on SYS_A1F_V5 (unchanged, holdout-v3-proven)."""
    qt = (question_type or "").lower()
    return SYS_A1_INT_V72 if qt.startswith("intervention") else SYS_A1F_V5
