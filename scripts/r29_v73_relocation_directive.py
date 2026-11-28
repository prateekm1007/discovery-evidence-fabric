#!/usr/bin/env python3
"""r29_v73_relocation_directive.py — the V7.3 RELOCATION directive
(the AM27 D2 continuation round, claim c-0027).

MEASURED BASIS (the V7.2 round's typed outcome, committed at the
r29_v72_tuned bytes): 5 of 10 rows exhausted repair budget 2 with
the defect CLASS INTACT — the machine satisficed the scan letter by
RELABELLING the same physical approach as "commercial" or "standard"
instead of recomposing the mechanism:

  bench-p04  "Commercial micro-dimple coating, 20-um depth, 100-um
              pitch, applied via spray" (still a surface treatment
              on the deployed part)
  bench-p08  "Commercial polyimide spin-coat solution ... O2 plasma
              etch ... anneal to cure" (still added process steps)
  bench-p11  "Standard copper-graphite composite sheet ... cut into
              asymmetric w[ashers] ... adhesive" (still a bonded
              interface as the compensating element)
  eval-new01 "sacrificial electrolyte reservoir ... reabsorb or
              replenish electrolyte" (still an off-spec material-
              function claim)
  eval-new03 "dual-lumen catheter design with ... integrated
              microchannel pressure sensor array" (still an added
              sensing channel on a regulated device)

The V7.3 directive is therefore BLUNTER about what a CONVERSION
finding means: the flagged MECHANISM CLASS itself is out of scope.
It remains NEUTRAL in the Art. 19 sense — it carries typed findings
and class relocations only, never outcome feedback, never judged
numbers (the judge-blind property is pinned by
tests/test_r29_v73_round.py over the directive text).

The contract is SYS_A1_INT_V72 BYTE-UNCHANGED (the arm is stable);
only the repair directive and the budget (2 -> 3, pre-registered on
the claim with the measured basis) differ from the V7.2 machine.
"""

V73_FLAGGED = [
    "bench-p04-pump-cavitation",
    "bench-p08-mems-stiction",
    "bench-p11-spindle-thermal-drift",
    "eval-new01-supercap-dryout",
    "eval-new03-insulin-pump-occlusion",
]

V73_REPAIR_DIRECTIVE = """MACHINE REPAIR PASS (typed findings on your draft below):
{findings}
Resolve ONLY these typed findings in a complete revised answer. Two
classes of finding, two different obligations:

For a CONVERSION finding (SURFACE_TREATMENT_DEV, ADDED_PROCESS_STEP,
BONDED_INTERFACE_DEV, ADDED_SENSING_CHANNEL_ON_REGULATED_DEVICE,
MATERIAL_FUNCTION_CLAIM, PREMISE_TOPOLOGY_INVALID): the flagged
MECHANISM CLASS itself is OUT OF SCOPE. Do NOT relabel the same
physical approach as "commercial" or "standard" — a purchasable
version of a forbidden class is still forbidden. The physical
approach may not appear in your revision in any form: no textured,
dimpled, blasted, or laser-patterned surfaces and no surface films
on the deployed part; no added coating, cure, adhesive, lamination,
etch, anneal, sinter, plating, or deposition steps on any line; no
bonded or adhered interface acting as the load-bearing or
compensating element; no material claimed to reabsorb, replenish,
or selectively transport anything beyond its supplier-stated
function; no new sensing channel, lumen, or electrode set on a
regulated device; no flow reversal on a topology without a second
path. Compose a DIFFERENT mechanism from the allowed novelty
surface: a duty cycle or schedule on existing or standard
equipment, an operating-point change within standard ratings, an
interconnection or arrangement of stock parts (series, parallel,
bypass, staging, placement, count), detection that rides EXISTING
signals (existing sensors, motor or drive current signatures,
derived observables of already-measured channels), or a procedure
change at standard parameters. Keep the failure physics and the
test protocol; change the mechanism's physical approach.

For any other finding (BILL_UNTAGGED, CONSTRAINT_EXCLUSION,
APPARATUS_ROW, NAMED_VARIANT, STANDARD_BILL, DEV_NEED,
UNPRICED_OPERATIONAL_LOSS, critic or type-gate anchors): resolve it
in place. BILL_UNTAGGED means every implementation-bill row carries
its (a)/(b)/(c) procurement tag. NAMED_VARIANT means generic
classes only — no brands, no model numbers, no (e.g., Vendor X)
rows. APPARATUS_ROW means no monitoring or instrumentation rows in
the deployed bill. UNPRICED_OPERATIONAL_LOSS means the burden
ledger states the operational loss (a number or an explicit zero
with the schedule) and counts it against parity.
"""
