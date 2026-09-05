#!/usr/bin/env python3
"""scripts/r412_build_gradient_preregistration.py — SEAL the R412
gradient/recovery arm BEFORE the first gradient model call (owner
directive 2026-09-06, item 11; Art. LIX pre-registration).

Commits, before any gradient/frontier model call:
  machinery        (discovery_fabric/r412/recovery.py + gradient.py,
                    committed with this seal)
  tests            (tests/test_r412_recovery_arm.py)
  schemas          (the TVM entry schema, the stage-record schemas,
                    the report headline schema)
  preregistration  (this artifact)
  population hash  (R412/RECOVERY_ARM/R412_POPULATION_ACCOUNTING.json
                    -> population_sha256)
  velocity-map snapshot/hash (R412/RECOVERY_ARM/TVM_V0_SNAPSHOT.json
                    -> v0 schema+protocol, sha256; the CONSTRUCTED map
                    gets its own snapshot+hash+commit before the
                    first GA-4 call)
  prompts/model identifiers (every post-seal LLM stage's prompt
                    hash + the transport pins)
  budget           (per-stage call caps, tokens, fabric calls)
  stopping rules   (budget/transport/cheapest-kill/zero-acceptable)

Then SEALED. No after-the-fact changes (Art. LIX).

The design directive (df9ce243) is SUPERSEDED on exactly one point by
this seal: its §3 population paragraph ("the honest denominator is
13") is replaced by the owner's item-3/5 directive — the experimental
population is the ENTIRE frozen R411 population (raw=550,
unique=400), the 13-candidate technical-death subset is a separately
reported subset, and no denominator may be hidden. Everything else in
the design directive carries into this preregistration.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.r412.gradient import (  # noqa: E402
    GRADIENT_VERSION, TVM_VERSION,
    build_deficit_extraction_prompt, build_tvm_proposal_prompt,
    build_backcast_prompt, build_feasibility_prompt,
    build_why_not_prompt, verify_seal)
from discovery_fabric.r412.recovery import (  # noqa: E402
    RECOVERY_VERSION, GRADIENT_ELIGIBLE,
    GRADIENT_PRIOR_ART_SPECIAL_ROUTE, GRADIENT_INELIGIBLE,
    CAPABILITY_DEFICIT_CLASSIFICATIONS, WHY_NOT_ALLOWED_FINDINGS,
    ATTACKER_CALIBRATION_STATUS, AVAILABILITY_STATES,
    CAUSAL_DELTA_REQUIRED_FIELDS)

RUN = REPO / "R411" / "DISCOVERY_RUN"
WATERFALL = REPO / "R412" / "R412_DEATH_CAUSE_WATERFALL.json"
ACCOUNTING = REPO / "R412" / "RECOVERY_ARM" / \
    "R412_POPULATION_ACCOUNTING.json"
TVM_V0 = REPO / "R412" / "RECOVERY_ARM" / "TVM_V0_SNAPSHOT.json"
OUT = REPO / "R412" / "R412_GRADIENT_RECOVERY_PREREGISTRATION.json"

MODEL_ID = "minimax/minimax-m3:free"
MODEL_PINS = {
    "ENGINE_LLM_PROVIDER": "openrouter",
    "OPENROUTER_MODEL": "minimax/minimax-m3:free",
}

# Pre-registered budgets (declared before any call; Art. XXVII).
# The resource allocation (10 seeds in frozen priority order) is the
# authoritative attempted-set plan; every cap below covers it with
# bounded retry headroom. Budget exhaustion leaves stages INCOMPLETE
# (Art. LXI) — never a verdict.
BUDGETS = {
    "ga1b_extraction_calls_max": 13,          # one per tech-death seed
    "tvm_construction_fabric_calls_max": 12,  # one per distinct rung
    "tvm_construction_llm_calls_max": 12,
    "ga4_backcast_calls_max": 10,
    "ga5_feasibility_calls_max": 10,
    "ga5_anchor_fabric_calls_max": 10,        # one per backcast
    "ga55_why_not_calls_max": 10,
    "ga55_target_fabric_calls_max": 20,       # <= 2 per seed
    "ga6_decomposition_calls_max": 10,        # one per backcast
    "ga6_capability_fabric_calls_max": 30,    # <= 3 per descendant
    "ga8_novelty_calls_max": 10,
    "ga8_prior_art_fabric_calls_max": 10,
    "ga9_attack_calls_max": 10,
    "out_tokens_per_llm_call": 2600,
    "retry_policy": (
        "one bounded retry per LLM stage per seed on INCOMPLETE "
        "transport; budget-exhausted stages stay INCOMPLETE "
        "(Art. LXI)"),
}

STOPPING_RULES = [
    "the run REFUSES to start unless verify_seal(prereg) passes "
    "(machinery + schemas + population hash + TVM snapshot hash + "
    "prompts + model identifiers + budget + stopping rules all "
    "committed first — directive item 11)",
    "budget exhausted -> the stage stays INCOMPLETE, never a "
    "verdict (Art. LXI)",
    "transport failure -> INCOMPLETE + one bounded retry; a second "
    "failure leaves INCOMPLETE recorded",
    "DEAD_AT_TVM_QUERY (no measured fast-mover on the rung) -> the "
    "seed dies at the cheapest stage: fabric calls only, no "
    "mechanism writing",
    "INSUFFICIENT_FRONTIER (the backcast honestly reports the "
    "ranked frontier does not carry the required capability) -> "
    "honest terminal stop for that seed",
    "NO_TECH_DEATH_CAUSE seeds and non-technical rejections are "
    "NEVER attempted (evolving them would manufacture a death "
    "cause)",
    "zero is an acceptable outcome: no quota forces a rediscovery "
    "(Art. LXVIII)",
    "no threshold, prompt, rule, population, or map change after "
    "the seal (Art. LIX); a changed TVM is a NEW snapshot + NEW "
    "freeze + NEW epistemic version (Art. XLIV)",
    "the run STOPS at the final report: physical spend, buyer "
    "contact, and commercial transactions remain human decisions "
    "(the reality boundary, Art. XXXVIII)",
    "every attack verdict and every headline metric carries "
    "attacker_calibration_status=NOT_CALIBRATED until the "
    "attacker-specificity problem is actually resolved (directive "
    "item 10) — never a silent green signal",
]


def _sha(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def _sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    accounting = json.loads(ACCOUNTING.read_text())
    waterfall = json.loads(WATERFALL.read_text())
    deaths = {d["candidate_id"]: d for d in waterfall["deaths"]}

    # --- the TVM v0 snapshot (schema + protocol + empty entries) ---
    seed_rungs = []
    for cid, frozen in CAPABILITY_DEFICIT_CLASSIFICATIONS.items():
        if frozen.get("axis_class") == "CAPABILITY_DEFICIT":
            seed_rungs.append({
                "expected_rung_for": cid,
                "deficit_class": frozen.get("deficit_class"),
                "named_deficit": frozen.get("named_deficit"),
            })
    tvm_v0 = {
        "artifact_type": "R412_TVM_V0_SNAPSHOT",
        "tvm_version": TVM_VERSION,
        "created_in": "R412",
        "reviewer_provenance": "AI_REVIEW",
        "entries": [],
        "n_entries": 0,
        "schema": {
            "entry": {
                "capability_rung": "str",
                "domain": "str (application domain of the record)",
                "metric": "str",
                "value": "number",
                "unit": "str",
                "year": "int (year of the measured value)",
                "source": {
                    "record_id": "str",
                    "citation": "str (title, <=200 chars)"},
                "provenance": {
                    "span": "str (verbatim quote)",
                    "verified_verbatim": "true (gate-admitted only)"},
                "confidence": "SPAN_VERIFIED",
            },
            "hard_rule": (
                "NO LLM-asserted numbers: every value enters only "
                "through a span-verified proposal against a retrieved "
                "record (the R411 F4a instrument pattern); rejected "
                "spans count as nothing"),
        },
        "construction_protocol": [
            "rungs are named by verified GA-1b extractions (and the "
            "frozen seed expectations below); the map grows per "
            "campaign as death records name new rungs — no fixed "
            "industry list (Art. XLIII/LXIX)",
            "per rung: one fabric retrieval for performance-trend "
            "records (pre-registered lane caps)",
            "an untrusted LLM (SEPARATE_CONTEXT_ONLY, never labelled "
            "independent) proposes entries with EXACT QUOTED SPANS",
            "the deterministic verbatim-containment gate verifies "
            "each span against the retrieved pool; rejected entries "
            "are recorded, never repaired",
            "measured slopes require >= 2 admitted entries from the "
            "SAME domain with the SAME metric+unit at different "
            "years — movement must be measured, not asserted",
            "frontier ranking is per rung from measured slopes only "
            "(steepest first: a SEARCH-ORDER policy, never a "
            "hard-coded belief about industries)",
            "after construction: the map is SNAPSHOTTED + HASHED + "
            "COMMITTED before the first GA-4 backcast call; no "
            "after-the-fact entry edits (Art. XLIV)",
        ],
        "seed_rung_expectations": seed_rungs,
        "freeze_rule": (
            "this v0 snapshot (schema + protocol + empty entries) is "
            "hashed and committed BEFORE the first gradient model "
            "call; the CONSTRUCTED map gets its own snapshot + "
            "sha256 + commit before its first use (GA-4)"),
    }
    TVM_V0.parent.mkdir(parents=True, exist_ok=True)
    TVM_V0.write_text(json.dumps(tvm_v0, indent=1) + "\n")

    # --- prompt hashes over the machinery's ACTUAL builders, on REAL
    # frozen data (the first priority target) ---
    first = accounting["resource_allocation"]["priority_order"][0]
    cand_first = next(
        c for c in json.loads(
            (RUN / "scored_pool.json").read_text())
        if c["candidate_id"] == first)
    demo_deficit = build_deficit_extraction_prompt(
        cand_first, deaths[first],
        CAPABILITY_DEFICIT_CLASSIFICATIONS[first])
    demo_tvm = build_tvm_proposal_prompt("actuation active alignment", [
        {"record_id": "demo-1", "title": "demo title",
         "abstract": "demo abstract"}])
    demo_query = {
        "ranked": [{"domain": "d", "metric": "m", "slope": 1.0,
                    "unit": "u"}]}
    demo_backcast = build_backcast_prompt(
        cand_first, deaths[first],
        {"deficit_span": "deflection", "required_value": "NOT_STATED",
         "named_deficit": "alignment"}, demo_query)
    demo_feasibility = build_feasibility_prompt(
        {"fields": {"OUTCOME": "o", "PHYSICAL_MECHANISM": "m"}},
        {"target_constraint": "c", "deficit_span": "d"})
    demo_why_not = build_why_not_prompt(
        "wind energy", "active alignment", [
            {"record_id": "demo-1", "title": "t", "abstract": "a"}])

    # --- the frozen eligibility classification ---
    elig_rows = accounting["gradient_eligibility"]["rows"]
    eligible_ids = [r["candidate_id"] for r in elig_rows
                    if r["eligibility"] == GRADIENT_ELIGIBLE]
    special_ids = [r["candidate_id"] for r in elig_rows
                   if r["eligibility"] ==
                   GRADIENT_PRIOR_ART_SPECIAL_ROUTE]
    ineligible_ids = [r["candidate_id"] for r in elig_rows
                      if r["eligibility"] == GRADIENT_INELIGIBLE]

    prereg = {
        "artifact_type":
            "R412_GRADIENT_RECOVERY_PREREGISTRATION",
        "run_id": "r412:gradient-recovery-v1",
        "created_in": "R412",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reviewer_provenance": "AI_REVIEW",
        "status": "SEALED_BY_COMMIT",
        "seal_declaration": (
            "this preregistration + machinery + tests + schemas + "
            "population accounting + TVM v0 snapshot are committed "
            "BEFORE the first gradient model call; no gradient or "
            "frontier model call may run while this artifact is "
            "absent from the repository; no after-the-fact changes "
            "(Art. LIX; directive item 11)"),
        "purpose": (
            "the invention-recovery objective (directive item 6): "
            "REJECTED SEED -> 30 YEARS LATER -> FRONTIER-TO-LAGGARD "
            "TRANSFER -> CAPABILITY BACKCAST -> 'DO THESE "
            "CAPABILITIES ALREADY EXIST TODAY?' -> YES -> "
            "PRESENT_CAPABILITY_REDISCOVERY -> NEW CAUSAL "
            "ARCHITECTURE -> FRESH NOVELTY -> FRESH ATTACK -> "
            "NORMAL INVENTION PIPELINE. The principal success "
            "metric is PRESENT_RECOVERY (existing capabilities + "
            "genuinely new causal architecture/application). A "
            "2055-only invention is a useful RADAR result, not the "
            "principal invention-recovery success metric."),
        "supersession": {
            "supersedes": (
                "R412/R412_GRADIENT_ARM_THREE_ENGINE_DESIGN_"
                "DIRECTIVE.md (df9ce243) §3 population paragraph"),
            "what_changed": (
                "the design directive's 'the honest denominator is "
                "13' is replaced by the owner's directive: the "
                "experimental population is the ENTIRE frozen R411 "
                "population (raw=550, unique=400); the 13-candidate "
                "technical-death subset is a separately reported "
                "subset, never the headline population; no "
                "denominator may be hidden"),
            "carried_forward": (
                "everything else in the design directive (the "
                "GA pipeline shape, the TVM design, the "
                "phantom-arbitrage guard, LIRY with dual "
                "denominators, the 0/13 temporal control arm "
                "standing unmodified)"),
        },
        "source_campaign": {
            "run_id": "r411:1788584836",
            "engine_commit":
                "bf89f095192e299cd436462ff4e98b3c004041f0",
            "population_accounting": str(
                ACCOUNTING.relative_to(REPO)),
            "population_accounting_sha256": _sha_file(ACCOUNTING),
            "death_cause_waterfall": str(
                WATERFALL.relative_to(REPO)),
            "death_cause_waterfall_sha256": _sha_file(WATERFALL),
        },
        "population": {
            "population_sha256": accounting["population_sha256"],
            "population_hash_basis":
                accounting["population_hash_basis"],
            "experimental_population": (
                "the ENTIRE frozen R411 population: raw accepted=550 "
                "-> unique scored=400 (medical=8, collision=142, "
                "dedup=0); the four terminal classes partition the "
                "400: technical death=13, non-technical rejection="
                "387, no death cause=0, other=0"),
            "technical_death_subset": (
                "13 candidates (SUBSET, separately reported): the "
                "seeds whose recorded outcome establishes a "
                "technological death cause; only these may receive "
                "gradient attempts"),
            "headline_denominators_required": [
                "raw_accepted", "unique_scored",
                "recorded_technical_death",
                "recorded_nontechnical_rejection",
                "recorded_no_death_cause", "other_terminal_state",
                "gradient_eligible", "gradient_attempted",
            ],
            "no_new_retrieval_for_population": True,
        },
        "tvm_v0": {
            "path": str(TVM_V0.relative_to(REPO)),
            "sha256": _sha_file(TVM_V0),
            "tvm_version": TVM_VERSION,
            "construction_freeze_rule": tvm_v0["freeze_rule"],
        },
        "model_versions": {
            "all_gradient_llm_stages": MODEL_ID,
            "transport_pins": MODEL_PINS,
            "transport_basis": (
                "the measured working free transport from the R411/"
                "R412 campaigns (minimax-m3: 2.9s, line-protocol "
                "clean); glm-4-plus gateway and glm-5.3 measured as "
                "proposer alternates in R411 F4a"),
            "proposer_independence": (
                "SEPARATE_CONTEXT_ONLY, never labelled independent "
                "(Art. XLV)"),
            "attacker_independence": (
                "SEPARATE_PROVIDER (openrouter vs the zai generator "
                "family), disclosed, never labelled independent "
                "validation — Art. XLV; the attacker family is "
                "measured NOT_CALIBRATED"),
            "attacker_calibration_status": dict(
                ATTACKER_CALIBRATION_STATUS),
        },
        "prompts": {
            "gradient_version": GRADIENT_VERSION,
            "recovery_version": RECOVERY_VERSION,
            "deficit_extraction_prompt_sha256": _sha(demo_deficit),
            "tvm_proposal_prompt_sha256": _sha(demo_tvm),
            "backcast_prompt_sha256": _sha(demo_backcast),
            "feasibility_prompt_sha256": _sha(demo_feasibility),
            "why_not_prompt_sha256": _sha(demo_why_not),
            "reused_sealed_instruments": {
                "verify_capability": (
                    "discovery_fabric/r412/temporal_pipeline.py::"
                    "verify_capability — reused UNCHANGED for GA-6 "
                    "(import, never a copy)"),
                "novelty_and_attack": (
                    "discovery_fabric/r412/temporal_pipeline.py "
                    "novelty + attack builders — reused for GA-8/9"),
            },
            "note": (
                "template hashes over the machinery's actual prompt "
                "builders (parameterized with the first frozen "
                "target); the runner uses the SAME committed "
                "machinery, unmodified"),
        },
        "eligibility_rules": {
            "axis": "capability-deficit (frozen, verbatim-cited)",
            "gradient_eligible": eligible_ids,
            "prior_art_special_route": special_ids,
            "gradient_ineligible": ineligible_ids,
            "frozen_table": (
                "discovery_fabric/r412/recovery.py::"
                "CAPABILITY_DEFICIT_CLASSIFICATIONS (13 rows, each "
                "basis span verbatim-verified against the recorded "
                "death reason at classification time; disputes fail "
                "closed)"),
            "no_tech_death_cause_rule": (
                "NO_TECH_DEATH_CAUSE and non-technical rejections "
                "are never attempted (directive item 3: no LLM may "
                "invent a missing death cause)"),
        },
        "invention_recovery_rules": {
            "availability_taxonomy": list(AVAILABILITY_STATES),
            "only_available_today_qualifies": (
                "ONLY AVAILABLE_TODAY auto-qualifies for "
                "PRESENT_CAPABILITY_REDISCOVERY; NEAR_TERM and "
                "FUTURE are future-dependence (radar results); "
                "UNKNOWN blocks promotion (a five-year "
                "technological expectation is not today's "
                "technology — directive item 7)"),
            "causal_delta_required_fields": list(
                CAUSAL_DELTA_REQUIRED_FIELDS),
            "causal_delta_gate": (
                "the delta is machine-computed (set operations over "
                "the parent and descendant graphs); 'better sensor / "
                "faster processor / different material / new "
                "industry alone' is INSUFFICIENT — the gate answers "
                "'what causal relationship exists in the descendant "
                "that did not exist in the parent?' (directive "
                "item 8)"),
            "why_not_allowed_findings": list(WHY_NOT_ALLOWED_FINDINGS),
            "why_not_gate": (
                "every promising transfer investigates "
                "WHY_NOT_ALREADY_ADOPTED; a non-UNKNOWN finding "
                "requires a span-verified target-domain record; "
                "UNKNOWN blocks promotion on the absence claim "
                "(phantom-arbitrage guard — directive item 9)"),
        },
        "token_and_cost_budgets": BUDGETS,
        "stopping_rules": STOPPING_RULES,
        "resource_allocation": {
            "priority_order":
                accounting["resource_allocation"]["priority_order"],
            "order_rationale":
                accounting["resource_allocation"]["order_rationale"],
            "budget_shortfall_rule":
                accounting["resource_allocation"]
                ["budget_shortfall_rule"],
            "population_stays_500_note": (
                "the experimental population remains the frozen R411 "
                "population even when 390 members correctly become "
                "NOT_ELIGIBLE — scientific honesty preserved without "
                "sacrificing the discovery objective (directive "
                "item 12)"),
        },
        "headline_schema": {
            "required_fields": [
                "raw_accepted", "unique_scored",
                "recorded_technical_death",
                "recorded_nontechnical_rejection",
                "recorded_no_death_cause", "other_terminal_state",
                "gradient_eligible", "gradient_attempted",
            ],
            "emission_guard": (
                "build_recovery_funnel + verify_population_funnel "
                "raise on any missing/hidden denominator or "
                "non-closing funnel — the report is un-emittable"),
            "outcome_decomposition": [
                "PRESENT_RECOVERY (the principal metric)",
                "FUTURE_ONLY (radar results, separately reported)",
                "UNRESOLVED (availability unknown; blocked, "
                "recorded)"],
            "the_13_subset": (
                "reported as a separately reported subset — never "
                "the headline population"),
        },
        "temporal_control_arm": {
            "status": "PRESERVED_UNMODIFIED",
            "sealed_result": "0/13 present-capability rediscoveries",
            "run_record_sha256":
                accounting["sealed_temporal_control_arm"]
                ["run_record_sha256"],
            "note": ("the sealed temporal replay is the control arm; "
                     "its artifact is never retro-edited"),
        },
        "reviewer_provenance_note": (
            "every verdict and artifact in this arm carries "
            "reviewer_provenance=AI_REVIEW (Art. LXVII)"),
    }

    # the fail-closed seal check must PASS on the emitted artifact
    check = verify_seal(prereg)
    if not check["seal_valid"]:
        raise SystemExit(f"seal check failed: {check}")

    OUT.write_text(json.dumps(prereg, indent=1) + "\n")
    print(f"seal check: {check['action']}")
    print(f"population_sha256: "
          f"{prereg['population']['population_sha256']}")
    print(f"tvm_v0 sha256: {prereg['tvm_v0']['sha256']}")
    print(f"prompt hashes: {len(prereg['prompts'])} entries")
    print(f"budgets: {len(BUDGETS)} fields; stopping rules: "
          f"{len(STOPPING_RULES)}")
    print(f"resource allocation: "
          f"{len(prereg['resource_allocation']['priority_order'])} "
          f"seeds")
    print(f"written: {OUT.relative_to(REPO)}")
    print("NO gradient model call has run (seal before first call)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
