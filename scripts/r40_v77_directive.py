#!/usr/bin/env python3
"""r40_v77_directive.py — the V7 PHYSICS-AND-DIVERSITY directive (the
AM37 D1-D3 round, claim c-0046, pre-registered BEFORE any LLM call).

MEASURED BASIS (the auditor's AM37 verdict, committed at 8fb6a9f93):
the first attested acceptance run (v6, VALID, 12/12 served ==
registered) scored 64.6% (mean 2.583/4) — ACCEPTANCE NOT GRANTED:
  F54 duty-cycle monoculture: 6/6 interventions are the same template
  (duty-cycle a permitted setpoint); HO6-02 INVERTED (periodic thermal
  shock to "inhibit cracking" on a coated copper mould — cyclic shock
  CAUSES heat-checking, the remedy is the failure's own driver);
  HO6-03 fiction mechanism + unpriced throughput cost; HO6-04/HO6-12
  require signals (online surface-charge sensing; ion activities /
  water chemistry) that are not among the constraint's permitted
  signals.

The V7 directive adds FOUR clauses on top of the V7.6 stack (imported
verbatim — the permitted-set class clause, the direction-of-effect
presence clause, the V7.5 conversion clauses and the V7.4
DEPLOYED-PART clause stay in force):

  THE DIRECTION-CORRECTNESS CLAUSE: the PHYSICS CHECK must carry the
  signed statement of the governing relation: which quantity drives
  the failure, what sign the remedy's action imposes on it, and why
  that sign lowers the damage integral over the duty cycle. A remedy
  whose active ingredient imposes the SAME sign as the failure's own
  driver (thermal shock to heal thermal-shock cracking; cycling to
  heal fatigue; more of the driver to undo the driver) is NOT an
  intervention — replace the mechanism, not the wording.

  THE INPUT-AVAILABILITY CLAUSE: every signal the remedy REQUIRES to
  actuate or trigger (sensed, monitored, analyzed, inferred online)
  must be derivable from the permitted measures and signals the
  constraint names. If the constraint permits only setpoint/
  procedure measures, the bill may not presuppose an online
  measurement the plant does not already have. Name every required
  input and its permitted source; if an input is unavailable, the
  mechanism must be re-chosen, not the instrumentation invented.

  THE COST-PRICING CLAUSE: any measure that modulates a production
  setpoint or duty cycle must state its operational cost explicitly
  in the OPERATIONAL COST line: what is given up (throughput, energy,
  availability, quality), an order-of-magnitude bound, and why the
  trade still nets positive. An unpriced duty cycle is an incomplete
  bill.

  THE MECHANISM-DIVERSITY CLAUSE: the bill opens with a
  MECHANISM CLASS: line naming the mechanism class in one phrase
  (e.g. "duty-cycle modulation of a transport flow", "surface
  state conversion", "inventory replacement procedure"). Within a
  6-intervention set at most 2 rows may share one mechanism class;
  when the set already carries 2 of the candidate's class, the
  mechanism must come from a different class.
"""
from __future__ import annotations

from r30_v76_directive import V76_REPAIR_DIRECTIVE

_V77_CLAUSES = """

THE DIRECTION-CORRECTNESS CLAUSE (AM37 D1): the PHYSICS CHECK must
carry the signed statement of the governing relation: the driving
quantity, the sign your mechanism's active ingredient imposes on it,
and why that sign LOWERS the damage/failure integral over the duty
cycle. If the ingredient imposes the SAME sign as the failure's own
driver, the mechanism is inverted — replace the mechanism (different
physics), never reword the claim.

THE INPUT-AVAILABILITY CLAUSE (AM37 D2): list every signal the remedy
REQUIRES online (sensed, monitored, analyzed) and its permitted
source; each must be derivable from the measures/signals the
constraint permits. A required input the plant cannot legally or
physically obtain under the constraint invalidates the mechanism —
re-choose the mechanism, do not invent the instrumentation.

THE COST-PRICING CLAUSE (AM37 D3): any setpoint or duty-cycle
modulation carries an OPERATIONAL COST line stating what is given up
(throughput, energy, availability, quality), an order-of-magnitude
bound, and why the trade nets positive.

THE MECHANISM-DIVERSITY CLAUSE (AM37 D1): open the bill with
"MECHANISM CLASS: <one phrase>". At most 2 rows of a 6-intervention
set may share one mechanism class; if the set already carries 2,
deliver a DIFFERENT mechanism class."""

V77_REPAIR_DIRECTIVE = (V76_REPAIR_DIRECTIVE.rstrip() + _V77_CLAUSES)
