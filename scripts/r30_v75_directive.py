#!/usr/bin/env python3
"""r30_v75_directive.py — the V7.5 CONVERSION directive (the AM28 D2
continuation round, claim c-0030, FOUR rows).

MEASURED BASIS (the auditor's AM28 row-by-row read, committed at
af3ef4d01): three residual gap-1 rows + one F40 content defect:

  bench-p09  "commercial hydrophilic silica nanoparticle sheet" — a
             product CLASS whose catalog reality is unproven (no
             such sheet is a standard stocked SKU; the auditor's
             residual);
  bench-p11  "existing hydraulic ports" on a machine-tool spindle
             housing — a PREMISE assumption (the problem does not
             state ports; the auditor's residual);
  eval-new03 a 0.1 mm bypass-lumen catheter + bellows — a NEW
             infusion-set DESIGN into a certified medical device
             with a regulatory path (the auditor's residual);
  bench-p10  DuPont SentryGlas named as a "sodium-barrier film" —
             an ionoplast STRUCTURAL interlayer, not an ion-barrier
             product (F40, property misattribution).

The V7.5 directive adds THREE clauses on top of the V7.4
DEPLOYED-PART-NO-MODIFICATION clause (imported — the V7.4 clause
stays in force verbatim):

  EXEMPLAR-REALITY CLAUSE: every named commercial exemplar must be a
  product CLASS that exists as stocked SKUs from multiple suppliers
  (e.g., SiOx-coated PET barrier film, a standard food/medical
  packaging class) with the property claimed sourced from the
  supplier's own published data sheet; if no such class exists, the
  mechanism must not rest on it — recompose from classes that do.

  PREMISE-VALIDITY CLAUSE: the mechanism may reference ONLY
  instrumentation, ports, spaces, and states the problem STATES
  exist. If the stated topology lacks the referenced feature (a
  port, a second path, a channel), the mechanism that needs it is
  OUT OF CLASS (the bench-p06 lesson: no reversal on a dead-end
  main).

  CERTIFIED-SYSTEM-AS-SOLD CLAUSE (restates V7.2 clause L for the
  new03 class): into a certified/regulated system the mechanism
  adds NO new hardware and NO new consumable design — it derives
  its action from firmware/sampling/analysis on instrumentation
  ALREADY INSTALLED, and/or uses consumable/accessory parts already
  certified for that application, as-sold.
"""
from r29_v74_directive import V74_REPAIR_DIRECTIVE  # noqa: E402

V75_FLAGGED = [
    "bench-p09-packaging-barrier",
    "bench-p11-spindle-thermal-drift",
    "eval-new03-insulin-pump-occlusion",
    "bench-p10-pv-pid",
]

V75_CLAUSES = """
TWO FURTHER OBLIGATIONS THIS ROUND (the AM28 D2 conversion, on top of
the deployed-part clause above):

THE EXEMPLAR-REALITY CLAUSE: every named commercial exemplar in a
bill row must be a product CLASS that exists as stocked SKUs from
multiple suppliers, with the claimed property sourced from the
supplier's own published data sheet (e.g., "SiOx-coated PET barrier
film" — a standard food/medical packaging class — with the oxygen/
ion transmission rate quoted from its data sheet). If no such
stocked class exists for the needed property, the mechanism must
not rest on that exemplar — recompose from classes that do. Never
name a product for a property class it is not sold under.

THE PREMISE-VALIDITY CLAUSE: the mechanism may reference ONLY
instrumentation, ports, spaces, fluids, and states the problem
STATES exist. If the stated topology lacks the referenced feature
(a port, a second supply path, a channel, a space), the mechanism
that needs it is OUT OF CLASS — recompose on the stated topology.

THE CERTIFIED-SYSTEM-AS-SOLD CLAUSE: into a certified/regulated
system (medical, food-contact), the mechanism adds NO new hardware
and NO new consumable design (no custom catheters, lumens,
bellows, or set components). It derives its action from
firmware/sampling/analysis on instrumentation ALREADY INSTALLED
(the problem states what exists) and/or uses consumable/accessory
parts already certified for that application, as-sold, per their
supplier procedures.
"""

V75_REPAIR_DIRECTIVE = V74_REPAIR_DIRECTIVE.replace(
    "Keep the failure physics and the test protocol; change the\n"
    "mechanism's physical approach.",
    "Keep the failure physics and the test protocol; change the\n"
    "mechanism's physical approach." + V75_CLAUSES)
assert "EXEMPLAR-REALITY" in V75_REPAIR_DIRECTIVE
assert "PREMISE-VALIDITY" in V75_REPAIR_DIRECTIVE
assert "CERTIFIED-SYSTEM-AS-SOLD" in V75_REPAIR_DIRECTIVE
assert "DEPLOYED-PART CLAUSE" in V75_REPAIR_DIRECTIVE
