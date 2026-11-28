#!/usr/bin/env python3
"""r30_v76_directive.py — the V7.6 CLASS-AND-DIRECTION directive (the
AM29 D1+D2 round, claim c-0031, pre-registered BEFORE any LLM call).

MEASURED BASIS (the auditor's AM29 verdict, committed at d9a6b2c06):
the holdout v4 acceptance FAILED (62.5%, 2 allowed-measures
violations, F43 inverted physics):
  HO4-04/HO4-05 — the constraint-bind learned the DEV allowed-measures
  LISTS, not the CLASS "the measure must be drawn from the permitted
  set" (hardware installed under param-only permitted sets);
  HO4-02/HO4-03 — the established-effect bind checks PROVENANCE, not
  DIRECTION (coarser bedding under a geomembrane; cycling to heal a
  cycling-driven seal).

The V7.6 directive adds TWO clauses on top of the V7.5 stack
(imported — the V7.4 DEPLOYED-PART clause and the V7.5
EXEMPLAR-REALITY / PREMISE-VALIDITY / CERTIFIED-SYSTEM-AS-SOLD
clauses stay in force verbatim):

  THE PERMITTED-SET CLAUSE (class, not list): the answer's measures
  must be drawn from the permitted set THIS problem states. When the
  stated permitted set is exhaustive over parameter/procedure
  measures ("... retuning/adjustment/procedure ONLY"), NO physical
  measure is permitted: the bill may not install, fit, or provision
  any device or bulk material. When the set names a physical measure
  class, its actuation equipment is permitted, nothing beyond it.

  THE DIRECTION-OF-EFFECT CLAUSE (Art. 25): the PHYSICS CHECK must
  carry an explicit structured statement:
    DIRECTION-OF-EFFECT: driving variable = <the quantity that drives
    the failure>; the mechanism moves it <up/down> by <magnitude and
    mechanism>; this <reduces/raises> the failure driver.
  A mechanism that moves a driving variable TOWARD the failure is OUT
  OF CLASS even if the measure itself is permitted (a remedy may not
  be the driver, and a permitted variable may only move the way the
  permitted measure's own wording implies: a LIMIT permits decrease
  only). The auditor judges whether the stated direction is CORRECT.

Deterministic enforcement: scripts/r30_allowed_class_scan.py
(ALLOWED_MEASURE_TYPE_OUTSIDE, LIMIT_DIRECTION_VIOLATION) and
scripts/r30_physics_direction_scan.py (PHYSICS_DIRECTION_UNSTATED,
DRIVER_AS_REMEDY) run IN the machine path; findings feed this
directive's repair pass.
"""
from r30_v75_directive import V75_REPAIR_DIRECTIVE  # noqa: E402

V76_CLAUSES = """
TWO FURTHER OBLIGATIONS THIS ROUND (the AM29 D1+D2 conversion, on top
of the clauses above):

THE PERMITTED-SET CLAUSE (the class, not a memorized list): the
answer's measures must be drawn from the permitted set THIS problem
states in its constraint. Read the constraint at answer time. When
the permitted set is exhaustive over parameter/procedure measures
("... retuning / adjustment / procedure / interval ONLY"), NO
physical measure is in class: the bill may not install, fit, or
provision any device or bulk material — recompose as pure
parameter/procedure changes on the stated permitted axes. When the
permitted set names a physical measure class (a dosing system, a
gradation change, catalog parts), the equipment that implements THAT
class is permitted and nothing beyond it. If the constraint text
names no permitted set, use the smallest standard-practice-adjacent
measure class that attacks the failure physics.

THE DIRECTION-OF-EFFECT CLAUSE (Art. 25): the PHYSICS CHECK must
carry this explicit structured statement:
DIRECTION-OF-EFFECT: driving variable = <the quantity that drives the
failure>; the mechanism moves it <up/down> by <magnitude and
mechanism>; this <reduces/raises> <the failure driver>.
Get the direction RIGHT, not merely stated: a mechanism that moves a
driving variable TOWARD the failure is OUT OF CLASS even when the
measure class itself is permitted (a remedy may not be the failure's
own driver; a permitted LIMIT on a variable permits moving it DOWN
only). If the correct direction cannot be achieved with the
permitted measures, the mechanism is out of class — recompose.
"""

V76_REPAIR_DIRECTIVE = V75_REPAIR_DIRECTIVE.replace(
    "Keep the failure physics and the test protocol; change the\n"
    "mechanism's physical approach.",
    "Keep the failure physics and the test protocol; change the\n"
    "mechanism's physical approach." + V76_CLAUSES)

assert "PERMITTED-SET CLAUSE" in V76_REPAIR_DIRECTIVE
assert "DIRECTION-OF-EFFECT CLAUSE" in V76_REPAIR_DIRECTIVE
assert "EXEMPLAR-REALITY" in V76_REPAIR_DIRECTIVE
assert "DEPLOYED-PART CLAUSE" in V76_REPAIR_DIRECTIVE
