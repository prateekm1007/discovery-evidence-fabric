#!/usr/bin/env python3
"""r29_v74_directive.py — the V7.4 DEPLOYED-PART-NO-MODIFICATION
directive (the AM27 D2 continuation round 2, claim c-0028, ONE row).

MEASURED BASIS (the V7.3 round's typed outcome, committed at the
r29_v73_tuned bytes): bench-p04's three draws all kept the same
defect attractor — MODIFYING THE DEPLOYED IMPELLER:

  V7.1 (r27)  "Standard CNC machining (replaces constant-thickness
               profile with tapered-thickness profile)" — the AM26
               named example;
  V7.2 (c-0025) "Commercial micro-dimple coating, 20-um depth,
               100-um pitch, applied via spray" — a surface
               treatment relabelled commercial;
  V7.3 (c-0027) "(c) Machining procedure: Create a circumferential
               groove at 10% chord from leading edge, 0.3 mm depth,
               1 mm width, using existing CNC milling equipment" —
               machining relabelled a standard operation on existing
               equipment; the r27 CUSTOM_MACHINING scan correctly
               still flags it (disclosed residual).

The V7.4 directive therefore adds the DEPLOYED-PART clause on top of
the V73 RELOCATION directive: the stated device's parts are used
AS-IS. It remains NEUTRAL in the Art. 19 sense — a structural class
relocation, never outcome feedback, never judged numbers (pinned by
tests/test_r29_v74_round.py over the directive text).
"""

V74_FLAGGED = [
    "bench-p04-pump-cavitation",
]

V74_REPAIR_DIRECTIVE = """MACHINE REPAIR PASS (typed findings on your draft below):
{findings}
Resolve ONLY these typed findings in a complete revised answer. Two
obligations:

THE DEPLOYED-PART CLAUSE (this round's structural relocation): the
problem's DEPLOYED PART — the stated device of record and every
part of it — may not be MODIFIED in any form: no machining,
grooving, cutting, grinding, drilling, texturing, coating, plating,
reprofiling, or re-finishing of the stated device's parts, whether
performed by you or procured from a supplier as a "standard" or
"commercial" service. The stated device's parts are used AS-IS.
The mechanism must be composed of NEW catalog parts installed
AS-SOLD on the SURROUNDING system (the suction or discharge side,
bypass or recirculation lines, mounting, controls, instrumentation
the standard practice's own bill already carries) and/or schedules,
duty cycles, or operating-point changes on existing equipment.
Keep the failure physics and the test protocol; change the
mechanism's physical approach.

For every other finding (BILL_UNTAGGED, CONSTRAINT_EXCLUSION,
APPARATUS_ROW, NAMED_VARIANT, STANDARD_BILL, DEV_NEED,
UNPRICED_OPERATIONAL_LOSS, critic or type-gate anchors): resolve it
in place. BILL_UNTAGGED means every implementation-bill row carries
its (a)/(b)/(c) procurement tag. NAMED_VARIANT means generic
classes only — no brands, no model numbers, no (e.g., Vendor X)
rows. APPARATUS_ROW means no monitoring or instrumentation rows in
the deployed bill beyond what the standard practice's own bill
already carries. UNPRICED_OPERATIONAL_LOSS means the burden ledger
states the operational loss (a number or an explicit zero with the
schedule) and counts it against parity.
"""
