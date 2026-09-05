#!/usr/bin/env python3
"""scripts/r412_recovery_accounting.py — run the DETERMINISTIC
recovery accounting across the ENTIRE frozen R411 population (owner
directive 2026-09-06, items 3/4/5/12) BEFORE any gradient model call.

Emits R412/RECOVERY_ARM/R412_POPULATION_ACCOUNTING.json:
  - GA-0   the four-class terminal classification over all 400
           unique-scored candidates (from the frozen records only)
  - GA-1a  DEATH_CAUSE_RECOVERY over the entire population (evidence
           recovery from existing records; no LLM — structurally)
  - GA-2   the frozen capability-deficit-axis eligibility
           classification over the recovered records (the frozen
           table's basis spans verified verbatim)
  - the frozen resource allocation (priority order over the
           gradient-eligible + special-route seeds)
  - the complete headline denominators (raw=550, unique=400, ...;
           no denominator hidden; the emission guard runs at build)

No LLM, no retrieval, no network: this script is a deterministic
measurement over frozen artifacts (Art. XLIV/LXII). Zero gradient
model calls occur here — the seal (preregistration) lands in a
sibling script BEFORE the first gradient model call (Art. LIX).
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.r412.recovery import (  # noqa: E402
    RECOVERY_VERSION, RECORDED_TECHNICAL_DEATH,
    GRADIENT_ELIGIBLE, GRADIENT_PRIOR_ART_SPECIAL_ROUTE,
    GRADIENT_INELIGIBLE,
    CAPABILITY_DEFICIT_CLASSIFICATIONS, verify_population_funnel,
    build_population_accounting, recover_death_causes,
    classify_gradient_eligibility)

RUN = REPO / "R411" / "DISCOVERY_RUN"
WATERFALL = REPO / "R412" / "R412_DEATH_CAUSE_WATERFALL.json"
OUT_DIR = REPO / "R412" / "RECOVERY_ARM"
OUT = OUT_DIR / "R412_POPULATION_ACCOUNTING.json"

# The frozen resource allocation (pre-registered priority order over
# the seeds that may receive gradient attempts; committed in the
# accounting so the preregistration and the runner share one source).
# Order rationale, recorded: eligible seeds first (capability-deficit
# deaths are the gradient channel's native targets), ordered by the
# quantified-gap magnitude in the recorded bases (10-100x actuation
# gap > operating-point baseline inversion > ungrounded control
# mathematics > qualitative measurement conflation); then the special
# route in the frozen waterfall record order (no invented ranking).
GRADIENT_ATTEMPT_PRIORITY = [
    "C-wind-2",
    "C-power_electronics-1",
    "C-chemical_process-1~3",
    "C-batteries_ev-1~3",
    # special route (waterfall record order):
    "C-carbon_capture-2~3",
    "C-carbon_capture-7~3",
    "C-data_center_thermal-1~2",
    "C-power_electronics-6~2",
    "C-semiconductor_fab-7~4",
    "C-wind-2~2",
]


def main() -> int:
    scored = json.loads((RUN / "scored_pool.json").read_text())
    shortlist = json.loads((RUN / "shortlist.json").read_text())
    selection = json.loads((RUN / "selection.json").read_text())
    waterfall = json.loads(WATERFALL.read_text())
    funnel = json.loads((RUN / "funnel_collision.json").read_text())

    # GA-0: the four-class accounting over the entire population
    accounting = build_population_accounting(
        funnel, scored, shortlist, selection, waterfall)

    # GA-1a: DEATH_CAUSE_RECOVERY over the ENTIRE population
    recovery_rows = recover_death_causes(accounting,
                                         waterfall["deaths"])

    # GA-2: the frozen capability-deficit-axis eligibility
    eligibility_rows = classify_gradient_eligibility(
        recovery_rows, waterfall["deaths"])

    n_established = sum(
        1 for r in recovery_rows
        if r.get("technological_death_cause_established"))
    n_eligible = sum(
        1 for e in eligibility_rows
        if e["eligibility"] == GRADIENT_ELIGIBLE)
    n_special = sum(
        1 for e in eligibility_rows
        if e["eligibility"] == GRADIENT_PRIOR_ART_SPECIAL_ROUTE)
    n_ineligible = sum(
        1 for e in eligibility_rows
        if e["eligibility"] == GRADIENT_INELIGIBLE)

    # the frozen priority order must exactly cover the eligible +
    # special-route set (guard: no seed silently added or dropped)
    priority_set = set(GRADIENT_ATTEMPT_PRIORITY)
    attempted_set = {
        e["candidate_id"] for e in eligibility_rows
        if e["eligibility"] in (GRADIENT_ELIGIBLE,
                                GRADIENT_PRIOR_ART_SPECIAL_ROUTE)}
    if priority_set != attempted_set:
        raise SystemExit(
            f"resource allocation mismatch: priority={sorted(priority_set)} "
            f"vs classified={sorted(attempted_set)} — refuse to emit")

    # headline denominators (item 5): the gradient_eligible field is
    # filled from the frozen classification; gradient_attempted is
    # the pre-registered budget target (the run records the actual)
    hl = accounting["headline_denominators"]
    hl["gradient_eligible"] = n_eligible + n_special
    hl["gradient_attempted"] = 0  # filled by the sealed gradient run
    hl["gradient_attempted_pre_registered"] = len(
        GRADIENT_ATTEMPT_PRIORITY)
    hl["note"] = (
        "gradient_eligible is the frozen GA-2 classification "
        "(eligible + special route; the special route may only "
        "promote via NEW_CAUSAL_ARCHITECTURE + fresh collision "
        "search). gradient_attempted is written by the sealed "
        "gradient run's stage records; 0 here because NO gradient "
        "model call has run (directive: no model call before the "
        "seal)")

    # re-run the emission guard with the filled fields
    verify_population_funnel(accounting)

    # the sealed temporal arm is preserved untouched (read-only use)
    temporal_run = REPO / "R412" / "TEMPORAL_REPLAY" / \
        "R412_TEMPORAL_REPLAY_RUN.json"

    artifact = {
        "artifact_type": "R412_POPULATION_ACCOUNTING",
        "run_id": "r412:recovery-accounting-v1",
        "recovery_version": RECOVERY_VERSION,
        "created_in": "R412",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reviewer_provenance": "AI_REVIEW",
        "directive": (
            "CODER DIRECTIVE R412 RECOVERY ARM (2026-09-06): the "
            "gradient/recovery experiment uses the SAME frozen R411 "
            "candidate population — never newly retrieved "
            "candidates, never a silent redefinition as 13 "
            "candidates; the 13-candidate technical-death subset is "
            "a separately reported subset, never the headline"),
        "no_model_calls": {
            "declaration": (
                "this artifact was produced with ZERO LLM calls and "
                "ZERO retrieval: every field is a deterministic "
                "function of frozen R411/R412 records"),
            "llm_calls": 0,
            "retrieval_calls": 0,
        },
        "population_funnel": accounting["funnel"],
        "headline_denominators": accounting["headline_denominators"],
        "terminal_classification": {
            "counts": accounting["terminal_classification"]["counts"],
            "rejection_surfaces":
                accounting["terminal_classification"]
                ["rejection_surfaces"],
            "rule": accounting["terminal_classification"]["rule"],
        },
        "population_sha256": accounting["population_sha256"],
        "population_hash_basis":
            accounting["integrity"]["population_hash_basis"],
        "technical_death_subset": accounting["technical_death_subset"],
        "death_cause_recovery": {
            "stage": "DEATH_CAUSE_RECOVERY",
            "population": "the entire frozen population (400)",
            "flow": (
                "R411 RECORDED OUTCOME -> DEATH_CAUSE_RECOVERY -> "
                "TECHNOLOGICAL DEATH CAUSE ESTABLISHED? YES -> "
                "CAPABILITY-DEFICIT EXTRACTION (GA-1b, post-seal); "
                "NO -> NO_TECH_DEATH_CAUSE (terminal; no invention)"),
            "n_established": n_established,
            "n_no_tech_death_cause": len(recovery_rows) - n_established,
            "extraction_basis": (
                "existing R411/R412 records only; exact source "
                "references and verbatim spans; no LLM; no new "
                "scientific adjudication (directive item 4)"),
            "rows": recovery_rows,
        },
        "gradient_eligibility": {
            "stage": "GA2_GRADIENT_ELIGIBILITY",
            "rule_basis": (
                "the frozen capability-deficit axis: every row's "
                "basis span must be verbatim-contained in the "
                "recorded death reason (verified at classification "
                "time; disputes fail closed)"),
            "counts": {
                "gradient_eligible": n_eligible,
                "prior_art_special_route": n_special,
                "gradient_ineligible": n_ineligible,
            },
            "rows": eligibility_rows,
        },
        "resource_allocation": {
            "priority_order": GRADIENT_ATTEMPT_PRIORITY,
            "order_rationale": (
                "eligible seeds first (capability-deficit deaths are "
                "the gradient channel's native targets), ordered by "
                "quantified-gap magnitude in the recorded bases; "
                "then the special route in frozen waterfall record "
                "order (no invented ranking)"),
            "budget_shortfall_rule": (
                "if the pre-registered budget cannot cover the full "
                "priority order, later seeds stay INCOMPLETE "
                "(recorded, never silently dropped, never "
                "re-allocated to non-eligible candidates — "
                "directive item 12)"),
            "the_13_subset_status": (
                "SUBSET of the 400-population, separately reported; "
                "the experimental population remains the frozen "
                "R411 population (raw=550, unique=400)"),
        },
        "sealed_temporal_control_arm": {
            "status": "PRESERVED_UNMODIFIED",
            "run_record": str(temporal_run.relative_to(REPO)),
            "run_record_sha256": hashlib.sha256(
                temporal_run.read_bytes()).hexdigest(),
            "result": "0/13 present-capability rediscoveries (the "
                      "honest sealed result; never retro-edited)",
            "note": ("the temporal replay artifact is read-only for "
                     "this arm; the 0/13 result stands as the "
                     "control arm"),
        },
        "emission_guard": (
            "verify_population_funnel passed at build time: raw = "
            "medical + collision + dedup + unique; the four "
            "terminal classes sum to unique; every headline "
            "denominator field present — no denominator hidden"),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(artifact, indent=1) + "\n")

    print(f"GA-0 population funnel: {artifact['population_funnel']}")
    print(f"terminal classes: "
          f"{artifact['terminal_classification']['counts']}")
    print(f"rejection surfaces: "
          f"{artifact['terminal_classification']['rejection_surfaces']}")
    print(f"DEATH_CAUSE_RECOVERY: {n_established} established / "
          f"{len(recovery_rows) - n_established} NO_TECH_DEATH_CAUSE")
    print(f"GA-2 gradient eligibility: {n_eligible} eligible, "
          f"{n_special} special-route, {n_ineligible} ineligible")
    print(f"resource allocation: {len(GRADIENT_ATTEMPT_PRIORITY)} "
          f"seeds in frozen priority order")
    print(f"population_sha256: {artifact['population_sha256']}")
    print(f"written: {OUT.relative_to(REPO)}")
    print("model calls: 0 (deterministic accounting only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
