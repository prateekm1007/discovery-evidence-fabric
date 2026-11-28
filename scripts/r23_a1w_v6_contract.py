#!/usr/bin/env python3
"""r23_a1w_v6_contract.py — SYS_A1_INT_V6 = the V4 contract + a
FEASIBILITY BIND AT MECHANISM CHOICE (the AM23 D2 round-2 lever).

Evolution basis, typed from COMMITTED bytes (Art. VI):
  - V4 pilot (r19): contract binds WORK when they act on the mechanism
    choice — hard-7 fgap 3.0 -> 1.857.
  - V5 repair leg (c-0006, r22): POST-generation rework measured
    NEGATIVE (2.222 vs incumbent 1.5; 11/18 residuals) — the typed
    lesson: the repair directive does not BIND the bill format and
    cannot reroute an already-chosen mechanism.
  - V6 therefore moves the bind UP into the DRAFT: the mechanism choice
    itself is constrained to procurable classes, the bill format is
    mandated at draft time, and the bind OUTRANKS mechanism preference
    (choose a different mechanism if the first cannot meet it).

The machine path is BYTE-UNCHANGED otherwise (critic + question-type
gate + typed machine repair directives, REPAIR_BUDGET=2 — the same
code path as r20/r21 and the holdout-v2 machine, disclosed as the
machine under test). No selection (K_GEN=1). The canonical metric,
problems, baselines, judge and acceptance are unchanged (Art. 16/19).
"""
from r19_a1w_v4_contract import (  # noqa: F401
    DEV_NEED_MARKERS, SYS_A1_INT_V4)

FEASIBILITY_BIND = """

FEASIBILITY BIND (applies at mechanism CHOICE, before the bill is
written — this bind OUTRANKS mechanism preference):
1. Choose ONLY a change achievable with: (a) the problem's stated
   infrastructure, (b) procurable standard catalog items of the same
   class standard practice already procures, or (c) a parameter/duty/
   procedure/configuration change to stated equipment (no hardware
   cost).
2. The IMPLEMENTATION BILL: EVERY row carries its (a)/(b)/(c) tag, and
   the bill is MINIMAL — delete optional and auxiliary rows; total
   install/commissioning burden must not exceed standard practice's
   own profile.
3. The novelty must live in the CHANGE (arrangement, parameters,
   procedure), never in new or custom things.
4. If a candidate mechanism cannot meet this bind, choose a DIFFERENT
   mechanism that can. Feasibility parity with standard practice is a
   hard requirement of this contract.
"""

SYS_A1_INT_V6 = SYS_A1_INT_V4 + FEASIBILITY_BIND

# Machine-internal repair directive (the standard typed-violations
# feedback — NO feasibility-rework text, NO rubric/judge feedback; the
# lever under test is the DRAFT-TIME bind, so the repair pass stays
# neutral: resolve the typed findings, keep everything else).
MACHINE_REPAIR_DIRECTIVE = """MACHINE REPAIR PASS (typed findings on your draft below):
{findings}
Resolve ONLY these typed findings in a complete revised answer; keep
the mechanism, structure, and all satisfied parts as-is.
"""
