#!/usr/bin/env python3
"""Two additional STANDARD_REFERENCE baselines (dev-fu-004-fouling,
eval-sofc-thermal-cycling) — the dev12 pairs whose committed records
carry an EMPTY baseline_answer (they were never part of the 10
auditor-judged dev12 pairs). Same discipline as the 18: standard
practice, labeled provenance, falsification test, builder-attributed.
"""
import json
import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

B = {}

B["dev-fu-004-fouling"] = """### Standard-Practice Baseline: Condenser Cleanliness Factor Trend on Existing Temperatures and Flows

The conventional condenser-fouling monitor on an instrumented 300 MW unit is the cleanliness factor (CF): the ratio of the actual overall heat transfer coefficient to the design (clean) U, computed continuously from the existing terminal temperatures and cooling-water flow, trended against a threshold that fires a cleaning work order.

1. **Indicator.** Cleanliness factor CF = U_actual / U_design, where U_actual is back-calculated from the heat balance (steam load from turbine exhaust conditions, cooling-water inlet/outlet temperatures and flow — all existing measurements), corrected to reference conditions for circulating-water inlet temperature and load.
2. **Threshold.** Alarm and schedule cleaning when CF falls below 85% (STANDARD PRACTICE: HEI-based condenser surveillance commonly acts in the 80-90% band; 85% is the common mid-band action level), with the derating limit projected by the CF slope. The 3-week lead requirement (USER CONSTRAINT) is met by trending the CF decline rate and projecting when back-pressure reaches the derating limit.
3. **Expected effect.** Fouling deposits lower U_actual progressively; the CF trend detects the decline weeks before the back-pressure limit, and the projection sets the cleaning date.
4. **Constraint respect.** Uses only existing temperature and flow measurements (USER CONSTRAINT respected; no new instrumentation). The known weaknesses: CF cannot distinguish tube-side fouling from shell-side air in-leakage or circulating-water flow metering error (both masquerade as fouling in the heat balance), and load swings add scatter — the projection's 3-week lead holds only when fouling progresses steadily.
5. **Falsification test.** Back-test one year of operating data against the cleaning log: compute CF and its projected derating date for every historical fouling episode. If the median warning lead time is below 3 weeks, or the false-alarm rate exceeds the operations team's actionable threshold (more than 2 non-fouling work orders per year triggered by CF decline that cleaning did not fix), the standard CF-trend predictor fails the stated duty.
"""

B["eval-sofc-thermal-cycling"] = """### Standard-Practice Baseline: Compliant Glass-Ceramic Seal with Thermal-Match Optimization and Controlled Heating Profile

The conventional mitigation for SOFC thermal-cycling seal and interface cracking is seal-material and stack-design practice: a glass-ceramic seal composition thermally matched to the YSZ electrolyte and LSM cathode expansion curves (CTE matched within roughly 1x10-6/K, STANDARD PRACTICE target), a controlled ramp profile that holds heating at the specified 5 C/min through the glass transition and softening ranges, and compressive stack loading to keep interfaces in compression.

1. **Intervention.** Qualify a CTE-matched compliant glass-ceramic seal (with the stated 0.15 intergranular glass phase fraction, USER CONSTRAINT clarification) whose transition range sits below the 750-800 C operating window, and enforce the 5 C/min ramp (USER CONSTRAINT) with dwell plateaus at the seal's glass-transition and softening temperatures to relax gradients slowly; maintain spring-loaded compressive stack pressure on the seal planes.
2. **Parameters.** 500 thermal cycles 25 C to 800 C at 5 C/min (USER CONSTRAINT). Open-circuit voltage above 1.0 V (USER CONSTRAINT). Seal leakage below 1% of fuel flow (USER CONSTRAINT). Stack mass increase below 2% (USER CONSTRAINT). CTE match to electrolyte within ~1x10-6/K (STANDARD PRACTICE). Compressive load per stack design (STANDARD PRACTICE per OEM stack hardware).
3. **Expected effect.** CTE matching minimizes the differential expansion that loads the seal each cycle; the compliant glass phase and compression keep microcracks closed; controlled ramping limits transient gradients that concentrate stress at the cathode-electrolyte interface.
4. **Constraint respect.** All four numeric constraints are addressed by design (no added mass beyond the seal and existing loading hardware — the mass budget 2% is respected by a seal-layer-only change). The known weaknesses: glass-ceramic seals age (devitrification shifts CTE and compliance over hundreds of cycles), and the residual stress at the cathode-electrolyte interface is only partially relieved by seal-side measures — the standard practice manages, but does not eliminate, the interface cracking mechanism.
5. **Falsification test.** Run the full 500-cycle protocol (25-800 C at 5 C/min) on sealed button or short stacks with per-cycle OCV and leakage measurement: if OCV falls below 1.0 V, or leakage exceeds 1% of fuel flow at any cycle, or post-test microscopy shows seal microcracking beyond the acceptance limit, the standard CTE-matched seal + controlled-ramp practice fails the stated duty.
"""

records = []
for pid, text in B.items():
    rec = {
        "problem_id": pid,
        "baseline_type": "STANDARD_REFERENCE",
        "baseline_answer": text.strip(),
        "authored_by": "builder (R11 R8 round, D2 supplement — the "
                       "dev12 pairs whose committed records carry an "
                       "empty baseline_answer)",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "method_note": (
            "Curated standard-practice baseline (same discipline as "
            "the 18 fresh baselines): conventional field answer, "
            "labeled USER CONSTRAINT / STANDARD PRACTICE / ASSUMPTION "
            "provenance, concrete falsification test, honest "
            "weaknesses. Builder-attributed for auditor adoption "
            "(F21)."),
    }
    out = REPO / "eval" / "baselines_curated" / f"{pid}.json"
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    records.append(pid)
    print("written:", out.name)

# update the INDEX
idx_path = REPO / "eval" / "baselines_curated" / "INDEX.json"
idx = json.loads(idx_path.read_text())
idx["n"] = idx["n"] + len(records)
idx["problem_ids"] = sorted(set(idx["problem_ids"]) | set(records))
idx["supplement"] = ("dev-fu-004-fouling + eval-sofc-thermal-cycling "
                     "added R8 round: the two dev12 pairs with empty "
                     "committed baseline_answer, needed to complete "
                     "the 30-pair F26 battery pool")
idx_path.write_text(json.dumps(idx, indent=1) + "\n", encoding="utf-8")
print(f"INDEX updated — {len(records)} supplements, total {idx['n']}")
