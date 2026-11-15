#!/usr/bin/env python3
"""r27_a1w_v71_contract.py — SYS_A1_INT_V71 = the V7 contract + the
STANDARD-BILL BIND (the AM26 D1 feasibility tuning: close the last
0.125 of the 0.375 pilot gap so every implementation line is a
standard catalog part or standard operation).

AM26 direction verbatim (the acceptance owner): "Run the full 30-pair
V7 battery and tune feasibility to parity. The pilot is at 0.375;
close the last 0.125 (e.g., ensure every bill line is a catalog part /
standard operation, no custom machining like the p04 vane reprofile).
Accept: feasibility |gap| <=0.25 AND novelty delta >=0.5 on >=30
pairs, auditor-judged."

Byte-typed basis (the pilot's gap-1 rows + the same-shape rows found
by the committed r27 standard-bill scan on the r26 generation):
- bench-p01: a "passive capillary wick (b)" custom-calibrated "to
  match the water recovery rate of 0.05 ml/min per A/cm2" — a bespoke
  component specified by a custom calibration, not a catalog part.
- bench-p04: a "vane-geometry reprofile ... (b) Standard CNC machining
  (replaces constant-thickness profile with tapered-thickness
  profile)" — custom machining of a precision component (the auditor's
  named example).
- bench-p08: a custom deposition recipe ("Power: 100 W, time: 60 s"
  vs the standard practice's "150 W, time: 30 s") PLUS an extra
  "post-deposition anneal 300C N2 30 min" step — process development,
  not a standard operation.
- bench-p09: a "co-extruded interlayer of PE containing 5 wt%
  montmorillonite nano-clay (b)" — a custom-compounded material.
- bench-p11: an "Aluminum mounting bracket (machined from standard
  stock ...)" — custom machining.
- eval-new01: "Module end plates (existing) — modified with a 0.5 mm
  deep recess" — custom machining of existing parts.
- eval-sofc-thermal-cycling: a "Graded glass-ceramic seal with 0.25
  intergranular glass phase at electrolyte interface, 0.05 at
  interconnect" — a custom-graded material.

The common failure shape: V7's generic-class palette stopped FICTIONAL
catalog items (named custom variants), but the novelty still leaked
onto the PROCESS-ENGINEERING axis — custom machining, custom recipes,
custom formulations, bespoke calibration — where implementation
burden is real development work, so feasibility cannot reach parity
with a standard-practice bill that buys stock parts and runs stock
procedures. V7.1 closes that axis: the bill may contain ONLY
procurable catalog parts and standard operations; whatever novelty
was doing on the process axis must be relocated onto the ARRANGEMENT
axis (the V7 clause-B surface: combination, duty, schedule,
interconnection, operating point) — e.g., a bilayer of two standard
commercial materials (each used exactly as its supplier specifies), a
duty-cycle schedule, a standard-part interconnection.

The machine path is otherwise BYTE-UNCHANGED (critic + question-type
gate + typed scans [base + constraint-fit + catalog-v2 + the r27
standard-bill scan] + the machine's own NEUTRAL repair directives,
REPAIR_BUDGET=2). No selection (K_GEN=1), judge-blind (no outcome
feedback, no judged numbers in any prompt). Predictor side:
UNCHANGED (SYS_A1F_V5, holdout-v3-proven; no predictor row is
scan-flagged — their bills are existing-sensor/derived-threshold
designs with no new hardware).
"""
from r26_a1w_v7_contract import (  # noqa: F401
    SYS_A1_INT_V7, MACHINE_REPAIR_DIRECTIVE)
from r26_a1w_v7_contract import SYS_A1F_V5  # noqa: F401

STANDARD_BILL_BIND = """

STANDARD-BILL BIND (V7.1 — refines the CATALOG-COMPOSITION BIND's
palette rule onto the BILL ROWS; OUTRANKS mechanism preference):

F. EVERY BILL LINE IS A CATALOG PART OR A STANDARD OPERATION. Each
   implementation-bill row is EXACTLY ONE of:
   (a) the problem's STATED existing equipment, used as-is;
   (b) a PROCURABLE CATALOG PART — a commercial standard product
       named by its generic class and its STOCK grade/size/rating
       (e.g., "commercial EPDM sheet, 60 Shore A, 3 mm", "standard
       3-way ball valve, DN80 PN16", "commercial NTC 10k probe,
       +/-0.5C") — procurable from the class name alone, off the
       shelf, in stock grades only;
   (c) a STANDARD OPERATION or PARAMETER CHANGE on existing or
       standard equipment AT ITS RATED/MANUFACTURER-STANDARD
       settings (e.g., "set the timer to 15 min on / 2 h off",
       "operate the existing charger at 2.27 V float", "bond with the
       supplier's own contact cement per its data sheet") — the kind
       of operation the standard practice's own bill already performs.
G. THE FOUR FORBIDDEN CLASSES (the measured feasibility defects; a
   bill row containing any of them is a typed defect — recompose the
   mechanism):
   1. CUSTOM MACHINING or material-removal work: CNC reprofiles,
      machined/milled/turned-down brackets, recesses cut into plates,
      regrinds, 3D-printed fixtures. If a part must be cut, ground,
      reprofiled, or resized to make the mechanism work, the
      mechanism is OUT OF SCOPE — compose it from parts that fit
      as-sold.
   2. CUSTOM PROCESS RECIPES: running a process (deposition, coating,
      cure, anneal, sintering, plating) at OTHER THAN the standard
      practice's own or the supplier's published parameters, or
      ADDING process steps the standard practice's bill does not
      perform. A catalog part is USED AS-SOLD: applied, installed, or
      cured exactly as its supplier specifies.
   3. CUSTOM-COMPOUNDED OR GRADED MATERIALS: wt%-doped, filled,
      blended, gradient, or graded-composition materials specified by
      mixture fractions ("5 wt% nano-clay", "0.25 intergranular phase
      at one interface, 0.05 at the other"). Standard stock grades
      ONLY — if two materials are needed, that is an ARRANGEMENT
      (a bilayer/stack of two catalog materials, each standard), not
      a formulation.
   4. BESPOKE CUSTOM-CALIBRATED COMPONENTS: a component specified by
      a custom calibration or custom sizing target ("a wick
      calibrated to match 0.05 ml/min per A/cm2"). If a flow, a
      dimension, or a rating must be CUSTOM-MADE to hit a target, use
      a standard part at its stock rating and put the precision in
      the ARRANGEMENT (the schedule, the duty split, the count, the
      placement) instead.
H. RELOCATION RULE (where the novelty goes instead): any mechanism
   content that would need a forbidden class is RECOMPOSED onto the
   arrangement axis — a BILAYER or STACK of two standard catalog
   materials (each used exactly as-sold, per its own supplier
   procedure), a DUTY-CYCLE or SCHEDULE on standard equipment, a
   SERIES/PARALLEL or REDUNDANT interconnection of standard parts, an
   OPERATING-POINT selection within standard ratings. The NOVELTY
   STATEMENT still names its one-line departure, and the departure is
   an arrangement element (V7 clause B), now provably free of
   process-development burden.
I. PARITY IS PROVEN FROM THE BILL ROWS (extends clause E): the BURDEN
   LEDGER's row-by-row comparison shows every one of your bill rows
   is the same CLASS of procurement/operation as the standard
   practice's own rows — buy a stock part, run a stock procedure,
   set a parameter — with the count and the schedule as the only
   differences. If any row's honest class is "develop", "qualify",
   "calibrate-to-target", or "machine-to-drawing", the parity claim
   is a defect.
"""

SYS_A1_INT_V71 = SYS_A1_INT_V7 + STANDARD_BILL_BIND

# The V7.1 repair directive EXTENDS the V61 neutral directive with the
# standard-bill relocation instruction (still NEUTRAL: typed findings
# only, no outcome feedback, no judged numbers).
V71_REPAIR_DIRECTIVE = """MACHINE REPAIR PASS (typed findings on your draft below):
{findings}
Resolve ONLY these typed findings in a complete revised answer; keep
the mechanism, structure, and all satisfied parts as-is. For
STANDARD_BILL findings: recompose the flagged row onto the arrangement
axis (a standard catalog part at stock grade, a standard operation at
rated parameters, a bilayer/stack of two standard materials, a
duty-cycle schedule) per the STANDARD-BILL BIND — never by asserting
procurability for a custom item.
"""


def contract_for_v71(question_type):
    """V7.1 arm map: interventions carry the standard-bill bind;
    predictors stay on SYS_A1F_V5 (unchanged, holdout-v3-proven)."""
    qt = (question_type or "").lower()
    return SYS_A1_INT_V71 if qt.startswith("intervention") else SYS_A1F_V5
