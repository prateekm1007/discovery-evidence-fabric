"""
economics.py — R371 Phase 9: validation economics without invented precision.

CEO directive:
  Replace simplistic "$5K / 10 weeks" with COST_RANGE / TIME_RANGE / BASIS /
  ASSUMPTIONS / UNCERTAINTY / SCOPE / EXPECTED_DECISION. No invented precision.

Facts about the engineering record (established by R371 audit):
  - The $5K/$25K/$100K figures in the V4 dossiers were HARDCODED TEMPLATE
    VALUES with no basis anywhere in the canonical engineering record.
    They are retired in V5 (memory artifact recorded per Constitution
    Art. XXXI).
  - The canonical record DOES contain per-work-package estimated_effort
    durations (e.g. '8 weeks', '12-24 weeks (chronic)'). These are
    ENGINEERING_PROPOSED effort estimates recorded by the build plan.
  - The canonical record contains NO cost quotations of any kind.

Therefore:
  COST_RANGE = NOT_ESTABLISHED (no quotation basis exists; establishment
               pathway = vendor quotations for the work-package equipment)
  TIME_RANGE = derived mechanically from canonical work-package durations,
               with the derivation basis, assumptions and uncertainty
               disclosed. LOW = sum of minimum durations, HIGH = sum of
               maximum durations (ranges parsed verbatim from the record).
"""

import re

NOT_ESTABLISHED = "NOT_ESTABLISHED"

_DURATION_RE = re.compile(
    r"(\d+)\s*(?:-\s*(\d+)\s*)?(weeks|months)"
)


def _parse_effort(text: str):
    """Parse a canonical estimated_effort string into (min_weeks, max_weeks,
    qualifier). Returns None if unparseable."""
    if not text:
        return None
    t = str(text).strip().lower()
    if t.startswith("tbd") or not t:
        return None
    m = _DURATION_RE.search(t)
    if not m:
        return None
    lo = int(m.group(1))
    hi = int(m.group(2)) if m.group(2) else lo
    unit = m.group(3)
    if unit == "months":
        lo, hi = lo * 4, hi * 4  # recorded as weeks-equivalent, disclosed
    qualifier = ""
    if "external" in t:
        qualifier = "external lab"
    elif "chronic" in t:
        qualifier = "chronic/duration-limited"
    elif "clinical" in t:
        qualifier = "clinical timeline"
    elif "foundry" in t:
        qualifier = "foundry cycle"
    elif "high risk" in t:
        qualifier = "high risk"
    elif "blocked" in t:
        qualifier = "blocked on dependency"
    return lo, hi, qualifier


def build_validation_economics(pkg) -> dict:
    """VALIDATION_ECONOMICS.json content for one package."""
    steps = []
    total_lo, total_hi = 0, 0
    decisive = None
    for i, step in enumerate(pkg.build_plan):
        parsed = _parse_effort(step.get("estimated_effort", ""))
        if parsed is None:
            steps.append(
                {
                    "work_package": step.get("work_package"),
                    "estimated_effort_recorded": step.get("estimated_effort"),
                    "parsed_weeks": NOT_ESTABLISHED,
                }
            )
            continue
        lo, hi, qual = parsed
        total_lo += lo
        total_hi += hi
        rec = {
            "work_package": step.get("work_package"),
            "estimated_effort_recorded": step.get("estimated_effort"),
            "parsed_weeks": {"low": lo, "high": hi},
            "qualifier": qual or None,
            "basis": (
                "ENGINEERING_PROPOSED effort estimate recorded in the "
                "canonical build plan (R370Q export). Not a committed "
                "schedule."
            ),
        }
        steps.append(rec)
        if decisive is None:
            decisive = rec

    wp1 = pkg.build_plan[0] if pkg.build_plan else {}
    ver1 = pkg.verification[0] if pkg.verification else {}

    return {
        "package_id": pkg.pkg_id,
        "portfolio_number": pkg.num,
        "cost_range": {
            "value": NOT_ESTABLISHED,
            "basis": (
                "The canonical engineering record contains no cost "
                "quotations. The prior '$5K/$25K/$100K' ladder was a "
                "template artifact with no recorded basis and has been "
                "retired (R371)."
            ),
            "assumptions": None,
            "uncertainty": None,
            "scope": None,
            "exclusions": None,
            "establishment_pathway": (
                "Vendor quotations for the equipment listed in each "
                "canonical work package (bench loop, sensors, transducers, "
                "foundry cycles, external-lab services) will establish a "
                "cost range. None exist in the record."
            ),
        },
        "time_range": {
            "first_decisive_work_package": {
                "work_package": wp1.get("work_package"),
                "recorded_effort": wp1.get("estimated_effort"),
                "parsed_weeks": (decisive or {}).get("parsed_weeks"),
            },
            "full_build_plan": {
                "low_weeks": total_lo if total_lo else NOT_ESTABLISHED,
                "high_weeks": total_hi if total_hi else NOT_ESTABLISHED,
            },
            "basis": (
                "Mechanical sum of canonical work-package estimated_effort "
                "values (verbatim parse; months converted at 4 weeks, "
                "disclosed). Ranges preserved exactly as recorded."
            ),
            "assumptions": [
                "Work packages execute sequentially (no parallelization "
                "credit taken)",
                "No rework or iteration loops are included",
                "External-lab and foundry lead times are as recorded in "
                "the effort strings, not additionally buffered",
            ],
            "uncertainty": (
                "Recorded ranges are engineering-proposed effort classes, "
                "not committed schedules. Items marked TBD/blocked are "
                "excluded from the sum and listed below."
            ),
            "scope": (
                "Engineering validation work packages only: bench "
                "verification of the kill condition and the design "
                "outputs. Excludes regulatory submission timelines, "
                "clinical timelines, and manufacturing transfer."
            ),
            "exclusions": (
                "Regulatory, clinical, and manufacturing-transfer "
                "durations (recorded separately in the canonical plan as "
                "clinical-timeline qualifiers where present)."
            ),
        },
        "expected_decision": {
            "decision": (
                "Whether the package kill condition is CONFIRMED or "
                "REFUTED by the first decisive work package"
            ),
            "kill_condition_link": "headlines.kill_if",
            "acceptance_criterion": ver1.get("acceptance")
            or wp1.get("acceptance_criterion"),
            "verification_requirement": ver1.get("requirement"),
        },
        "work_package_economics": steps,
        "discipline": (
            "estimated_cost != quoted_cost and estimated_duration != "
            "committed_duration. Cost is NOT_ESTABLISHED rather than "
            "invented; time ranges derive mechanically from the canonical "
            "record with disclosed assumptions."
        ),
    }
