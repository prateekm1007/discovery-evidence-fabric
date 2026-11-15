#!/usr/bin/env python3
"""r24_a1w_v61_contract.py — V6 ROUND 2 (same lever, Art. 20 clock 2/2):
the feasibility bind gains CONSTRAINT-AWARENESS (the F36 fix).

F36 evidence (auditor, holdout v2 @ 62.5%): HO2-03 proposed a
zinc-anode collar OUTSIDE the stated allowed measures
(orthophosphate/pH only); HO2-04 proposed intake-humidity control
OUTSIDE the allowed list (filtration/coalescer/water-wash only);
predictors used secondary instead of primary indicators. The machine
respects question TYPE but not the problem's own measure constraints.

V6.1 therefore binds the mechanism choice to the problem's stated
constraints CONDITIONALLY (they differ per problem):
  - allowed-measures enumeration present -> mechanism + every bill row
    draw ONLY from that list (catalog equivalents of listed classes
    allowed; anything else is out of scope even if procurable);
  - exclusion/limitation cues ("without X", "must not X", "retrofit
    only", "no change to X") -> hard exclusions, off-limits even when
    feasible;
  - performance bounds stay first-class bill-test targets;
  - the bind outranks mechanism preference (choose a different
    mechanism that fits).

Predictor side (for holdout v3's one-shot): SYS_A1F_V5 = SYS_A1F_V4 +
PRIMARY-INDICATOR CONSTRAINT (the monitored indicator must be the
problem's primary stated indicator; secondary indicators only as
supplements, never replacements). Byte-unchanged otherwise; the
battery rides predictors (no fresh predictor drafts) so this clause
affects only sealed tests.

Machine path: byte-unchanged (critic + gate + NEUTRAL typed repairs,
budget 2). No selection (K_GEN=1). Canonical metric unchanged
(Art. 16/19).
"""
from r23_a1w_v6_contract import SYS_A1_INT_V6  # noqa: F401
from r19_a1w_v4_contract import SYS_A1F_V4  # noqa: F401

CONSTRAINT_BIND = """

CONSTRAINT BIND (reads the problem's own stated constraints — these
OUTRANK mechanism preference and outrank procurability convenience):
0. BEFORE choosing the mechanism, extract the problem's constraint
   classes: (i) allowed-measures enumerations ("X only", "X or Y",
   "allowed measures: ..."), (ii) exclusions ("without X", "must not
   X", "retrofit only", "no change to X"), (iii) performance bounds
   (numeric operating envelopes).
1. If an allowed-measures list exists: the mechanism and EVERY bill
   row draw ONLY from that list (or a procurable catalog item of the
   same class as a listed item). A measure outside the list is out of
   scope EVEN IF procurable and even if it would score well.
2. Every exclusion is a hard exclusion: the mechanism must not rely
   on, add, or increase anything the constraints exclude.
3. Performance bounds are the bill's verification targets: the MINIMAL
   bill must carry the test that falsifies the mechanism against each
   stated bound.
4. If a candidate mechanism violates any of the above, choose a
   DIFFERENT mechanism that fits. Constraint fit is a hard requirement
   of this contract, not a preference.
"""

SYS_A1_INT_V61 = SYS_A1_INT_V6 + CONSTRAINT_BIND

PREDICTOR_CONSTRAINT = """

CONSTRAINT BIND (predictor): the monitored indicator must be the
problem's PRIMARY stated indicator (the one whose threshold defines
the failure). A secondary indicator may only SUPPLEMENT the primary
one — never replace it — and the answer must say explicitly which
stated indicator is primary and why.
"""

SYS_A1F_V5 = SYS_A1F_V4 + PREDICTOR_CONSTRAINT

MACHINE_REPAIR_DIRECTIVE = """MACHINE REPAIR PASS (typed findings on your draft below):
{findings}
Resolve ONLY these typed findings in a complete revised answer; keep
the mechanism, structure, and all satisfied parts as-is.
"""
