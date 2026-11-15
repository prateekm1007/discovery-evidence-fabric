#!/usr/bin/env python3
"""r26_a1w_v7_contract.py — SYS_A1_INT_V7 = the V6.1 contract + the
CATALOG-COMPOSITION BIND (the AM25 D1 NEW feasibility lever).

AM25 direction verbatim (the acceptance owner): "Produce novel
COMBINATIONS of procurable catalog components (novel arrangement, no
new development, and no audit apparatus that itself reads as burden),
so implementation burden is provably <= standard practice."

Lever kind (pre-registered, distinct from the retired kinds): the
three retired generation-side levers (BOK selection r21, V5 repair
r22, V6/V6.1 contract-bind r23/r24) kept the SAME novelty target (a
novel mechanism/material) and tried to bind feasibility onto it; the
measured result — novelty moves (1.967-2.333), feasibility does not
(1.4-2.3 vs incumbent 1.5) — is byte-typed to a specific failure:
the generator invents a FICTIONAL CATALOG ITEM and tags it (b)
"procurable" (r24 bench-p05: "procured standard catalog
gradient-crosslink-density neoprene sheets", fgap 4; bench-p10:
"low-sodium borosilicate cover glass (b) — procurable standard
catalog item", fgap 4), or installs NEW MODULES (r24 bench-p03
titanium/steel electrode modules, bench-p06 PLC + motorized valves +
actuator upgrade — both fgap 3). No amount of bind LANGUAGE stops a
generator that can assert procurability it cannot ground.

V7 therefore RELOCATES THE NOVELTY TARGET: the mechanism must be a
novel ARRANGEMENT of generic-class procurable components and stated
infrastructure. There is nothing to invent on the component axis —
every part is a generic class ("a standard solenoid valve") whose
procurability is undeniable from the class name — so the feasibility
surface (procurable-by-construction) and the novelty surface (the
arrangement: combination, duty, schedule, interconnection, operating
point) are separated by construction. This is the auditor's
"novel COMBINATIONS of procurable catalog components" lever, in the
contract.

The machine path is otherwise BYTE-UNCHANGED (critic + question-type
gate + typed scans [base + catalog-v2] + the machine's own NEUTRAL
repair directives, REPAIR_BUDGET=2 — the same code path as r20/r21/
holdout-v2/v3, with the catalog-v2 scan added as the lever's
deterministic leg, disclosed as the machine under test). No selection
(K_GEN=1). The canonical metric, problems, baselines, judge and
acceptance are unchanged (Art. 16/19).

Predictor side: UNCHANGED (SYS_A1F_V5 — the r24 primary-indicator
constraint, holdout-v3-proven at 3.0/4). Its fresh rows enter the
r26 all-fresh byte map because the rides floor made the <=0.25 gate
clause structurally unreachable (pre-registered disclosure).
"""
from r24_a1w_v61_contract import (  # noqa: F401
    SYS_A1_INT_V61, MACHINE_REPAIR_DIRECTIVE)
from r24_a1w_v61_contract import SYS_A1F_V5  # noqa: F401

CATALOG_COMPOSITION_BIND = """

CATALOG-COMPOSITION BIND (V7 — refines the PROCUREMENT RULE and the
FEASIBILITY BIND; OUTRANKS mechanism preference):

A. GENERIC-CLASS PALETTE (procurability by construction): every
   hardware element of the mechanism is named by its GENERIC material
   or component class — "a standard solenoid valve", "a mechanical
   timer", "a check valve", "a commercially available hydrophilic
   silica coating" — NEVER by brand, model number, or a NAMED CUSTOM
   VARIANT of a material. A variant no generic class covers
   ("gradient-crosslink-density neoprene sheet", "low-sodium
   borosilicate cover glass") is a FORBIDDEN fictional catalog item:
   procurability must be undeniable from the class name alone. If the
   mechanism needs a component whose generic class is not procurable,
   the mechanism is OUT OF SCOPE — compose a different one.
B. NOVELTY LIVES IN THE ARRANGEMENT (this is where the NEW MECHANISM
   lives now): the mechanism is a novel COMBINATION of palette
   components and the problem's stated infrastructure. The departure
   is HOW the components are combined, sequenced, driven, connected,
   oriented, or parameterized — the duty cycle, the schedule, the
   interconnection, the geometry, the operating point — NEVER a new
   or custom component. In the NOVELTY STATEMENT, name in one line
   exactly WHICH arrangement element is the departure (the schedule?
   the interconnection? the duty split? the operating point?).
C. NO-APPARATUS RULE (no audit apparatus that itself reads as
   burden): the DEPLOYED mechanism adds no monitoring, instrumentation,
   data-collection, or logging apparatus — no new sensors, no new
   instruments, no new analysis programs in the bill. The arrangement
   works through the stated existing controls or runs open-loop on
   stated physics. (Instruments named in the EXECUTABLE TEST are
   unchanged — the falsifier is not the deployed mechanism.)
D. FULL SPECIFICATION (anti-vagueness — "vague means" is the measured
   feasibility defect): EVERY bill row states (i) the generic class
   or the stated item it rides, (ii) WHERE it attaches in the STATED
   infrastructure, and (iii) the operating parameter(s) it sets, with
   values. A row that cannot be written at that specificity is a
   typed defect: the mechanism is not yet an arrangement — recompose
   it.
E. PROVE PARITY FROM THE ROWS: the BURDEN LEDGER compares the
   arrangement against the standard practice's own bill ROW-BY-ROW
   (installation, commissioning, operation, maintenance, cost class)
   and concludes same-or-lower burden FROM THOSE ROWS. Asserting
   "same burden" without the row-by-row basis is a defect. Where the
   problem's stated constraints enumerate allowed measures, every
   bill row draws from those classes and each row NAMES the allowed
   class it implements (a catalog equivalent of a listed class says
   so explicitly).
"""

SYS_A1_INT_V7 = SYS_A1_INT_V61 + CATALOG_COMPOSITION_BIND


def contract_for_v7(question_type):
    """V7 arm map: interventions carry the catalog-composition bind;
    predictors stay on SYS_A1F_V5 (unchanged, holdout-v3-proven)."""
    qt = (question_type or "").lower()
    return SYS_A1_INT_V7 if qt.startswith("intervention") else SYS_A1F_V5
