"""discovery_fabric/r412/temporal.py — the R412 30-Years-Later
temporal-evolution experiment (CEO directive, 2026-09-05).

> "When our discovery machine rejects a technologically plausible
> candidate, can a constrained temporal-evolution process discover a
> genuinely new causal architecture built from capabilities that
> already exist today, and can that descendant survive the same
> epistemic and adversarial machinery as an ordinary invention?"

PIPELINE (the directive's §12 path):

    R411 candidate -> present-day rejection (recorded death cause)
        -> 30Y eligibility (deterministic, from the death-cause
           waterfall; the temporal stage NEVER overwrites the
           original death)
        -> 30Y evolution (constrained thought experiment: the
           descendant must specifically overcome the ORIGINAL cause
           of death; prior-art deaths may ONLY evolve via
           NEW_MECHANISM / NEW_CAUSAL_ARCHITECTURE transformation)
        -> capability evidence records (every assumed capability:
           required value derived from the invention's engineering
           requirements FIRST; trend extrapolation; epistemic_class
           EXTRAPOLATED_TREND, never FACT)
        -> backward decomposition (requirements -> capabilities ->
           subsystems -> physical effects -> enabling technologies;
           "does this capability demonstrably exist today?")
        -> independent verification (fabric retrieval per claimed-
           today capability; term-coverage adjudication)
        -> branch: TEMPORAL_PROJECTION (needs future progress ->
           TECHNOLOGY_RADAR, buyer-ineligible by schema barrier) or
           PRESENT_CAPABILITY_REDISCOVERY (all essential capabilities
           demonstrated today -> re-enter the invention machinery as
           a BRAND-NEW candidate with nothing inherited but lineage)

Constitutional grounding:
  - Art. LXVIII: zero is an acceptable scientific outcome; no quota
    forces a fifth... or a first rediscovery.
  - Art. XXV/XXVIII: EXTRAPOLATED_TREND is never FACT; the trend gate
    compares numbers deterministically and the model cannot rescue a
    failed assumption rhetorically.
  - Art. XLVI/LIX: the population, prompts, and rules are frozen in
    the preregistration BEFORE the first 30Y model call.
  - Art. XI/LXII: original death records are immutable inputs; every
    lineage link carries hashes.
  - Art. LXI: transport failures are INCOMPLETE, never verdicts.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

TEMPORAL_VERSION = "R412-TEMPORAL-V1"

# ---------------------------------------------------------------------------
# T0 — eligibility (deterministic; the directive's §2 class lists)
# ---------------------------------------------------------------------------

ELIGIBLE_CAUSES = ("physics", "engineering")
# manufacturing / sensing / computation / integration limitations map
# onto the R411 death taxonomy's engineering class; physics is its own.
CONDITIONAL_BASELINE = "baseline"
INELIGIBLE_CAUSES = ("evidence", "problem_premise", "attack", "other")
PRIOR_ART_SPECIAL_ROUTE = "prior_art"

# The one R411 baseline death: the limiting quantity (Esw, device
# switching energy) is a device-technology-dependent parameter with a
# concrete enabling trajectory (wide-bandgap semiconductor switching-
# energy trend) — the directive's "economic/operational limitation
# where a concrete enabling technological trajectory exists".
BASELINE_ELIGIBLE_JUSTIFICATIONS = {
    "C-power_electronics-1": (
        "the limiting quantity is Esw (device switching energy) — a "
        "device-technology-dependent parameter whose enabling "
        "trajectory (SiC/GaN wide-bandgap switching-energy trend) is "
        "concrete and measured in the literature; the directive's "
        "conditional economic/operational class applies"),
}


def classify_eligibility(death: Dict[str, Any]) -> Dict[str, Any]:
    """Map one waterfall death record to 30Y eligibility. The
    classification cites the verbatim death reason; the original death
    is NEVER reinterpreted here (its record is an immutable input)."""
    cause = str(death.get("death_cause") or "")
    cid = str(death.get("candidate_id") or "")
    reason = str(death.get("death_reason") or "")
    if cause in ELIGIBLE_CAUSES:
        eligibility = "ELIGIBLE"
        rule = f"death_cause '{cause}' is in the directive's primary "
        f"eligible classes"
    elif cause == CONDITIONAL_BASELINE and \
            cid in BASELINE_ELIGIBLE_JUSTIFICATIONS:
        eligibility = "ELIGIBLE"
        rule = BASELINE_ELIGIBLE_JUSTIFICATIONS[cid]
    elif cause == PRIOR_ART_SPECIAL_ROUTE:
        eligibility = "PRIOR_ART_SPECIAL_ROUTE"
        rule = ("prior-art collisions evolve ONLY via transformation "
                "to NEW_MECHANISM / NEW_CAUSAL_ARCHITECTURE followed "
                "by a fresh collision search; a better implementation "
                "of the existing mechanism is not enough (directive §2)")
    else:
        eligibility = "INELIGIBLE"
        rule = (f"death_cause '{cause}' is in the directive's "
                f"normally-ineligible classes" if cause in
                INELIGIBLE_CAUSES else
                f"death_cause '{cause}' is not an eligible class")
    return {
        "candidate_id": cid,
        "present_death_cause": cause,
        "present_death_reason_verbatim": reason[:400],
        "death_stage_verbatim": str(death.get("death_stage") or ""),
        "eligibility": eligibility,
        "eligibility_rule_basis": rule,
        "original_death_immutable": True,
    }


# ---------------------------------------------------------------------------
# T1 — the 30Y evolution (constrained thought experiment)
# ---------------------------------------------------------------------------

EVOLUTION_PROMPT = """Assume the year is 2055. You are a rigorous engineering scientist reconstructing a technology that was REJECTED in 2026, starting from its recorded cause of death. You must construct the most capable technically coherent DESCENDANT that specifically overcomes the original cause of death.

ORIGINAL CANDIDATE (rejected 2026):
- name: {name}
- problem: {problem}
- mechanism chain: {mechanism}
- intervention: {intervention}
- predicted effect: {predicted}
- boundary conditions: {boundary}

RECORDED CAUSE OF DEATH (2026, verbatim): {death_reason}

{special_route}

Answer in EXACTLY this field-line format (one line per field, no prose outside the fields):

WHAT_KILLED_IT: <one sentence: the specific technical cause of death>
PREVENTING_CONSTRAINT: <the physical/engineering constraint that prevented the 2026 mechanism from working>
REMOVING_CAPABILITY: <the capability whose availability would remove that constraint>
WHY_CAUSAL_CHANGE: <why that capability changes the CAUSAL MECHANISM itself, not just performance numbers>
NEW_ARCHITECTURE: <the resulting 2055 architecture, one sentence>
MECHANISM_CHAIN: <causal step 1 | causal step 2 | causal step 3 | causal step 4>
INTERVENTION: <the concrete 2055 intervention>
PREDICTED_EFFECT: <the predicted effect with honest bounds and units>
BOUNDARY_CONDITIONS: <the operating regime with values>
KILL_CONDITION: <the experimental outcome that would kill this descendant>
LEADING_INDICATOR: <a near-term measurable signal that would confirm or undermine the descendant's premise>
MEASUREMENT_METHOD: <how the leading indicator is measured now or in the near term>
MEASUREMENT_WINDOW: <when the measurement is checkable>
EXPECTED_SIGNAL: <the expected indicator value or direction>
FAILURE_THRESHOLD: <the indicator value that would falsify the premise>
CAPABILITY_1: <capability name> | <assumption it rests on> | <required value + unit, derived from THIS descendant's engineering requirements> | <current 2026 value + unit> | <historical trend evidence> | <trend period> | <trend model> | <2055 extrapolated value + unit> | <uncertainty> | <essential today: yes or no>
CAPABILITY_2: <same format if a second capability is essential>
CAPABILITY_3: <same format if a third capability is essential>

Hard rules:
- "10x better, cheaper, faster, smaller" WITHOUT the causal chain is an invalid answer.
- Every CAPABILITY's required value must be derived from this descendant's own engineering requirements first — never choose a convenient trend and then calculate requirements around it.
- If the credible 2055 extrapolated value is BELOW the required value, you must still state both honestly (the machinery will fail the assumption; do not hide it).
- At most 3 CAPABILITY lines. Fields left empty fail the gate.
"""

PRIOR_ART_SPECIAL_ROUTE_BLOCK = """
SPECIAL ROUTE (this candidate died because prior art already teaches its mechanism): a better implementation of the existing mechanism is NOT enough. Your descendant must be a NEW_MECHANISM or NEW_CAUSAL_ARCHITECTURE — different causal structure, not the same mechanism made more advanced. State the architectural difference explicitly in WHY_CAUSAL_CHANGE and NEW_ARCHITITECTURE. A fresh collision search will run against your descendant; if it still teaches the same mechanism, the descendant dies.
""".replace("ARCHITITECTURE", "ARCHITECTURE")


def build_evolution_prompt(candidate: Dict[str, Any],
                           death: Dict[str, Any]) -> Tuple[str, bool]:
    """Returns (prompt, special_route). The prompt embeds the original
    candidate + the VERBATIM death reason (the death is an input, never
    an output — the temporal stage cannot overwrite it)."""
    special = (str(death.get("death_cause")) ==
               PRIOR_ART_SPECIAL_ROUTE)
    prompt = EVOLUTION_PROMPT.format(
        name=str(candidate.get("technology_name") or "")[:120],
        problem=str(candidate.get("problem") or "")[:300],
        mechanism=" -> ".join(str(s) for s in
                              candidate.get("causal_chain") or [])[:500],
        intervention=str(candidate.get("intervention") or "")[:300],
        predicted=str(candidate.get("predicted_effect") or "")[:250],
        boundary=str(candidate.get("boundary_conditions") or "")[:200],
        death_reason=str(death.get("death_reason") or "")[:500],
        special_route=(PRIOR_ART_SPECIAL_ROUTE_BLOCK if special
                       else "(no special route)"),
    )
    return prompt, special


EVOLUTION_FIELDS = (
    "WHAT_KILLED_IT", "PREVENTING_CONSTRAINT", "REMOVING_CAPABILITY",
    "WHY_CAUSAL_CHANGE", "NEW_ARCHITECTURE", "MECHANISM_CHAIN",
    "INTERVENTION", "PREDICTED_EFFECT", "BOUNDARY_CONDITIONS",
    "KILL_CONDITION", "LEADING_INDICATOR", "MEASUREMENT_METHOD",
    "MEASUREMENT_WINDOW", "EXPECTED_SIGNAL", "FAILURE_THRESHOLD",
)

CAPABILITY_SLOTS = ("CAPABILITY_1", "CAPABILITY_2", "CAPABILITY_3")

CAPABILITY_PARTS = (
    "name", "assumption", "required_value", "current_value",
    "historical_evidence", "trend_period", "trend_model",
    "extrapolated_2055_value", "uncertainty", "essential_today",
)


def _field_lines(text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in (text or "").splitlines():
        m = re.match(r"^([A-Z_0-9]+)\s*:\s*(.*)$", line.strip())
        if m:
            out.setdefault(m.group(1), m.group(2).strip())
    return out


def _num(s: str) -> Optional[float]:
    """First numeric value in the string (handles '500 W/kg',
    '1.2e3', '0.85'). None when no number is present."""
    m = re.search(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", s or "")
    return float(m.group(0)) if m else None


def parse_capabilities(fields: Dict[str, str]) -> List[Dict[str, Any]]:
    """Parse the CAPABILITY_n lines into structured capability records.
    The epistemic_class is SET BY THE MACHINERY (EXTRAPOLATED_TREND),
    never by the model (directive §4: never FACT or EVIDENCE)."""
    caps: List[Dict[str, Any]] = []
    for slot in CAPABILITY_SLOTS:
        raw = fields.get(slot)
        if not raw:
            continue
        parts = [p.strip() for p in raw.split("|")]
        if len(parts) != len(CAPABILITY_PARTS):
            caps.append({
                "slot": slot, "raw": raw[:300],
                "parse_status": "MALFORMED",
                "epistemic_class": "EXTRAPOLATED_TREND",
            })
            continue
        cap = dict(zip(CAPABILITY_PARTS, parts))
        cap["slot"] = slot
        cap["epistemic_class"] = "EXTRAPOLATED_TREND"
        cap["parse_status"] = "OK"
        caps.append(cap)
    return caps


def validate_capability(cap: Dict[str, Any]) -> Dict[str, Any]:
    """The deterministic capability gate (directive §4).

    FAILS the assumption when the credible 2055 extrapolated value is
    below the required value (numeric comparison — the model cannot
    rescue it rhetorically). Missing/qualitative values fail as
    UNPARSABLE (conservative)."""
    if cap.get("parse_status") != "OK":
        return {"status": "MALFORMED", "gate": "FAIL",
                "reason": "capability line did not parse into the "
                          "required parts"}
    missing = [k for k in CAPABILITY_PARTS
               if not str(cap.get(k) or "").strip()]
    if missing:
        return {"status": "INCOMPLETE", "gate": "FAIL",
                "reason": f"missing parts: {missing}"}
    req = _num(str(cap.get("required_value")))
    ext = _num(str(cap.get("extrapolated_2055_value")))
    if req is None or ext is None:
        return {"status": "NON_NUMERIC", "gate": "FAIL",
                "reason": ("required/extrapolated values are not "
                           "numeric — the deterministic comparison "
                           "cannot run, so the assumption is not "
                           "admissible (fail closed)")}
    if ext < req:
        return {
            "status": "GAP", "gate": "FAIL",
            "required_value": req, "extrapolated_2055_value": ext,
            "ratio": round(ext / req, 4) if req else None,
            "reason": (f"credible 2055 projection {ext} < required "
                       f"{req} (directive §4: the assumption fails; "
                       f"no rhetorical rescue)"),
        }
    return {"status": "MEETS_REQUIREMENT", "gate": "PASS",
            "required_value": req, "extrapolated_2055_value": ext,
            "ratio": round(ext / req, 4) if req else None}


def parse_evolution(text: str, original_candidate_id: str,
                    death: Dict[str, Any]) -> Dict[str, Any]:
    """Parse the evolution output into the lineage record. The lineage
    is machine-readable end to end (directive §3); the original death
    is carried by reference, never rewritten."""
    fields = _field_lines(text)
    missing = [f for f in EVOLUTION_FIELDS if not fields.get(f)]
    caps = parse_capabilities(fields)
    evolution_id = "EVO-" + hashlib.sha256(
        (original_candidate_id + "|" + (text or "")).encode()
    ).hexdigest()[:12]
    return {
        "temporal_version": TEMPORAL_VERSION,
        "evolution_id": evolution_id,
        "original_candidate_id": original_candidate_id,
        "original_death": {
            "candidate_id": original_candidate_id,
            "death_cause": death.get("death_cause"),
            "death_stage": death.get("death_stage"),
            "death_reason_verbatim": str(
                death.get("death_reason") or "")[:400],
        },
        "parse_status": "OK" if not missing and caps else (
            "INCOMPLETE_FIELDS" if missing else "NO_CAPABILITIES"),
        "missing_fields": missing,
        "fields": {f: fields.get(f, "") for f in EVOLUTION_FIELDS},
        "capabilities": caps,
        "lineage": {
            "original_candidate_id": original_candidate_id,
            "evolution_id": evolution_id,
            "chain": [
                f"PRESENT:{original_candidate_id}",
                f"DEATH:{death.get('death_cause')}",
                f"EVOLUTION:{evolution_id}",
            ],
        },
    }


# ---------------------------------------------------------------------------
# T3 — the backward decomposition (directive §5: the crucial operation)
# ---------------------------------------------------------------------------

DECOMPOSITION_PROMPT = """Decompose the requirements of this 2055-descendant technology BACKWARD, and for each capability ask: does this capability already demonstrably exist TODAY at the required operating regime?

2055 DESCENDANT:
- new architecture: {architecture}
- mechanism chain: {mechanism}
- intervention: {intervention}
- predicted effect: {predicted}
- boundary conditions: {boundary}

ITS ASSUMED CAPABILITIES (decompose each one):
{capability_list}

Answer in EXACTLY this field-line format (one line per capability, in the SAME order):

SUBSYSTEM_1: <capability name> | <required subsystems> | <required physical effects> | <actual enabling technologies> | <exists today: yes or no or partial> | <the specific demonstrated capability and operating regime, or the gap> | <operating regime match: yes or no — does today's demonstration meet the required regime/value?>
SUBSYSTEM_2: <same format>
SUBSYSTEM_3: <same format>

Hard rules:
- "AI exists", "advanced sensors exist", "new materials exist" are NOT sufficient: name the specific capability, its demonstrated operating values, and the source domain of the demonstration.
- If today's demonstration does not meet the required regime, operating_regime_match is no — the machinery will treat the capability as NOT available today.
"""


def build_decomposition_prompt(evolution: Dict[str, Any]) -> str:
    caps = [c for c in evolution.get("capabilities") or []
            if c.get("parse_status") == "OK"]
    lines = []
    for i, c in enumerate(caps, 1):
        lines.append(
            f"{i}. {c['name']} — required {c['required_value']}; "
            f"current {c['current_value']}; trend {c['trend_model']}; "
            f"2055 projection {c['extrapolated_2055_value']}; "
            f"essential today: {c['essential_today']}")
    f = evolution.get("fields") or {}
    return DECOMPOSITION_PROMPT.format(
        architecture=str(f.get("NEW_ARCHITECTURE") or "")[:300],
        mechanism=str(f.get("MECHANISM_CHAIN") or "")[:400],
        intervention=str(f.get("INTERVENTION") or "")[:300],
        predicted=str(f.get("PREDICTED_EFFECT") or "")[:250],
        boundary=str(f.get("BOUNDARY_CONDITIONS") or "")[:200],
        capability_list="\n".join(lines) or "(no capabilities parsed)",
    )


DECOMP_PARTS = (
    "name", "required_subsystems", "physical_effects",
    "enabling_technologies", "exists_today", "exists_today_basis",
    "operating_regime_match",
)


def parse_decomposition(text: str) -> Dict[str, Any]:
    fields = _field_lines(text)
    rows: List[Dict[str, Any]] = []
    for i in range(1, 4):
        raw = fields.get(f"SUBSYSTEM_{i}")
        if not raw:
            continue
        parts = [p.strip() for p in raw.split("|")]
        if len(parts) != len(DECOMP_PARTS):
            rows.append({"slot": f"SUBSYSTEM_{i}", "raw": raw[:300],
                         "parse_status": "MALFORMED"})
            continue
        row = dict(zip(DECOMP_PARTS, parts))
        row["slot"] = f"SUBSYSTEM_{i}"
        row["parse_status"] = "OK"
        row["exists_today"] = row["exists_today"].lower()
        row["operating_regime_match"] = \
            row["operating_regime_match"].lower()
        rows.append(row)
    return {"rows": rows,
            "parse_status": "OK" if rows else "NO_ROWS"}


def cross_check_capabilities(evolution: Dict[str, Any],
                             decomposition: Dict[str, Any]
                             ) -> List[str]:
    """Every capability the evolution marked essential_today=yes must
    appear (name-level match, casefold containment either direction)
    in the decomposition — a missing row is a recorded defect, never a
    silent pass."""
    problems = []
    rows = [r for r in decomposition.get("rows") or []
            if r.get("parse_status") == "OK"]
    for cap in evolution.get("capabilities") or []:
        if str(cap.get("essential_today", "")).strip().lower() != "yes":
            continue
        name = str(cap.get("name") or "").casefold().strip()
        if not name:
            continue
        found = any(
            name in str(r.get("name") or "").casefold() or
            str(r.get("name") or "").casefold() in name
            for r in rows)
        if not found:
            problems.append(
                f"essential-today capability '{cap.get('name')}' has "
                f"no decomposition row")
    return problems
