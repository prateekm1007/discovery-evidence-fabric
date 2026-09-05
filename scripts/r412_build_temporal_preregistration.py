#!/usr/bin/env python3
"""scripts/r412_build_temporal_preregistration.py — freeze the R412
30-Years-Later experiment BEFORE the first 30Y model call (CEO
directive §1; Art. LIX pre-registration).

Emits R412/R412_30Y_PRESENT_CAPABILITY_REDISCOVERY_PREREGISTRATION.json
from FROZEN inputs only (the R411 candidate population, its evidence
pools, the death-cause waterfall, and the machinery's versioned
prompts). The population is NOT replaced with newly retrieved
candidates; the R411 records are immutable inputs (Art. XI).
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.r412.temporal import (  # noqa: E402
    TEMPORAL_VERSION, classify_eligibility, build_evolution_prompt)
from discovery_fabric.r412 import temporal_pipeline as tp  # noqa: E402
from discovery_fabric.r412.temporal import build_decomposition_prompt  # noqa: E402
from discovery_fabric.r412.temporal_pipeline import (  # noqa: E402
    build_novelty_prompt, build_temporal_attack_prompt)

RUN = REPO / "R411" / "DISCOVERY_RUN"
WATERFALL = REPO / "R412" / "R412_DEATH_CAUSE_WATERFALL.json"
OUT = REPO / "R412" / "R412_30Y_PRESENT_CAPABILITY_REDISCOVERY_PREREGISTRATION.json"

MODEL_ID = "minimax/minimax-m3:free"
MODEL_PINS = {
    "ENGINE_LLM_PROVIDER": "openrouter",
    "OPENROUTER_MODEL": "minimax/minimax-m3:free",
}

# Pre-registered budgets (declared before any call; Art. XXVII)
MAX_EVOLUTION_CALLS = 14          # 13 eligible/special + 1 retry headroom
MAX_DECOMPOSITION_CALLS = 14
MAX_NOVELTY_CALLS = 14
MAX_ATTACK_CALLS = 14
MAX_CAPABILITY_FABRIC_CALLS = 24  # <= 3 per attempted candidate
OUT_TOKENS_PER_CALL = 2600


def _sha(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def _candidate_hash(cand: dict) -> str:
    payload = json.dumps(
        {k: cand.get(k) for k in (
            "candidate_id", "technology_name", "problem",
            "causal_chain", "unexploited_phenomenon", "intervention",
            "governing_variables", "predicted_effect", "equations",
            "boundary_conditions", "evidence_refs",
            "cross_domain_transition", "baseline", "killer_experiment",
            "failure_modes")},
        sort_keys=True)
    return _sha(payload)


def main() -> int:
    scored = json.loads((RUN / "scored_pool.json").read_text())
    shortlist = json.loads((RUN / "shortlist.json").read_text())
    waterfall = json.loads(WATERFALL.read_text())
    by_id = {c["candidate_id"]: c for c in shortlist}
    deaths = {d["candidate_id"]: d for d in waterfall["deaths"]}

    # the exact candidate population: the 400 unique scored-pool
    # candidates (per-candidate content hashes); the raw-accepted 550
    # recorded as context
    raw_accepted = 0
    for f in (RUN / "candidates").glob("*.json"):
        d = json.loads(f.read_text())
        raw_accepted += len(d.get("accepted") or [])

    population = []
    for c in scored:
        cid = c["candidate_id"]
        population.append({
            "candidate_id": cid,
            "candidate_sha256": _candidate_hash(c),
            "shortlisted": cid in by_id,
            "present_death": (
                deaths[cid]["death_cause"] if cid in deaths else None),
        })

    # eligibility classification (deterministic, from the waterfall)
    eligibility = []
    for d in waterfall["deaths"]:
        eligibility.append(classify_eligibility(d))
    eligible_ids = [e["candidate_id"] for e in eligibility
                    if e["eligibility"] == "ELIGIBLE"]
    special_ids = [e["candidate_id"] for e in eligibility
                   if e["eligibility"] == "PRIOR_ART_SPECIAL_ROUTE"]
    ineligible_ids = [e["candidate_id"] for e in eligibility
                      if e["eligibility"] == "INELIGIBLE"]

    # pre-shortlist rejection causes (deterministic, from recorded
    # state — the present-day rejection census over the 400)
    n_low = sum(1 for c in scored
                if (c.get("scoring") or {}).get("confidence") == "LOW")
    n_eligible = sum(1 for c in scored
                     if (c.get("scoring") or {}).get(
                         "finalist_eligible"))
    n_ranked_out = n_eligible - len(shortlist)

    # prompt hashes (the machinery's ACTUAL templates, hashed at
    # freeze time; the runner must use the same machinery)
    demo_evo = build_evolution_prompt(by_id[eligible_ids[0]],
                                      deaths[eligible_ids[0]])
    demo_decomp = build_decomposition_prompt({
        "fields": {"NEW_ARCHITECTURE": "x", "MECHANISM_CHAIN": "x",
                   "INTERVENTION": "x", "PREDICTED_EFFECT": "x",
                   "BOUNDARY_CONDITIONS": "x"},
        "capabilities": [{"parse_status": "OK", "name": "n",
                          "required_value": "r", "current_value": "c",
                          "trend_model": "t",
                          "extrapolated_2055_value": "2",
                          "essential_today": "yes"}]})
    demo_novelty = build_novelty_prompt(
        {"new_candidate_id": "X", "fields": {
            "MECHANISM_CHAIN": "m", "INTERVENTION": "i",
            "PREDICTED_EFFECT": "p", "WHY_CAUSAL_CHANGE": "w"}},
        [{"record_id": "r", "title": "t"}])
    demo_attack = build_temporal_attack_prompt(
        {"new_candidate_id": "X"}, {"fields": {
            "MECHANISM_CHAIN": "m", "INTERVENTION": "i",
            "PREDICTED_EFFECT": "p", "BOUNDARY_CONDITIONS": "b",
            "KILL_CONDITION": "k", "LEADING_INDICATOR": "l"}},
        [{"record_id": "r", "title": "t"}])

    # evidence snapshot hashes
    pool_hashes = {}
    for f in (RUN / "evidence").glob("*.json"):
        if f.stem.endswith("_canonical"):
            continue
        d = json.loads(f.read_text())
        pool_hashes[d.get("domain_id") or f.stem] = {
            "pool_sha256": d.get("pool_sha256"),
        }

    prereg = {
        "artifact_type":
            "R412_30Y_PRESENT_CAPABILITY_REDISCOVERY_PREREGISTRATION",
        "created_in": "R412",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reviewer_provenance": "AI_REVIEW",
        "purpose": (
            "test INVENTION capacity, not rejection capacity: when "
            "the discovery machine rejects a technologically "
            "plausible candidate, can a constrained temporal-evolution "
            "process discover a genuinely new causal architecture "
            "built from capabilities that already exist today, and "
            "can that descendant survive the same epistemic and "
            "adversarial machinery as an ordinary invention?"),
        "source_campaign": {
            "run_id": "r411:1788584836",
            "campaign_version": "R411-CAMPAIGN-V1",
            "engine_commit": "bf89f095192e299cd436462ff4e98b3c004041f0",
            "run_record": "R411/R411_DISCOVERY_RUN.json",
            "death_cause_waterfall": (
                "R412/R412_DEATH_CAUSE_WATERFALL.json (sha256 "
                + _sha(WATERFALL.read_text()) + ")"),
        },
        "exact_candidate_population": {
            "population_definition": (
                "the frozen R411 scored pool (unique post-collision "
                "candidate ids with full Art. XLI records) — NOT "
                "replaced with newly retrieved candidates; the raw "
                "extraction set is recorded as context"),
            "raw_accepted_candidates": raw_accepted,
            "unique_scored_candidates": len(scored),
            "candidates": population,
            "rejection_census": {
                "evidence_floor_LOW_confidence": n_low,
                "ranked_out_pre_attack": n_ranked_out,
                "killed_in_tournament": len(shortlist),
                "note": (
                    "the 27 ranked-out candidates were never "
                    "terminally adjudicated (no attack ran); they are "
                    "present-day rejections WITHOUT a technological "
                    "death cause and are NOT 30Y-eligible (evolving a "
                    "rejection whose cause was never established "
                    "would manufacture a death cause)"),
            },
        },
        "evidence_snapshot": {
            "pools": pool_hashes,
            "note": ("the frozen R411 evidence pools; the ONLY new "
                     "retrieval in this experiment is (a) independent "
                     "capability verification and (b) fresh prior-art "
                     "retrieval for promoted rediscoveries — both "
                     "permitted by the directive (§5 backward "
                     "decomposition, §8 fresh pipeline)"),
        },
        "model_versions": {
            "evolution_decomposition_novelty_attack": MODEL_ID,
            "transport_pins": MODEL_PINS,
            "attacker_independence": (
                "SEPARATE_CONTEXT (same provider family as the "
                "campaign; disclosed, never labelled independent "
                "validation — Art. XLV); the attacker family is "
                "measured NOT_CALIBRATED (R412/P0-1: FPR 0.8 on "
                "known-good) and every verdict carries that caveat"),
        },
        "prompts": {
            "temporal_version": TEMPORAL_VERSION,
            "temporal_attack_version": tp.TEMPORAL_ATTACK_VERSION,
            "temporal_novelty_version": tp.TEMPORAL_NOVELTY_VERSION,
            "evolution_prompt_sha256": _sha(demo_evo[0]),
            "decomposition_prompt_sha256": _sha(demo_decomp),
            "novelty_prompt_sha256": _sha(demo_novelty),
            "temporal_attack_prompt_sha256": _sha(demo_attack),
            "note": ("template hashes over the machinery's actual "
                     "prompt builders (parameterized examples); the "
                     "runner uses the SAME committed machinery, "
                     "unmodified"),
        },
        "token_and_cost_budgets": {
            "evolution_calls_max": MAX_EVOLUTION_CALLS,
            "decomposition_calls_max": MAX_DECOMPOSITION_CALLS,
            "novelty_calls_max": MAX_NOVELTY_CALLS,
            "attack_calls_max": MAX_ATTACK_CALLS,
            "capability_fabric_calls_max": MAX_CAPABILITY_FABRIC_CALLS,
            "out_tokens_per_llm_call": OUT_TOKENS_PER_CALL,
            "retry_policy": (
                "one bounded retry per LLM stage per candidate on "
                "INCOMPLETE transport; budget-exhausted stages stay "
                "INCOMPLETE (Art. LXI)"),
        },
        "eligibility_rules": {
            "eligible_causes": list(
                __import__("discovery_fabric.r412.temporal",
                           fromlist=["ELIGIBLE_CAUSES"]
                           ).ELIGIBLE_CAUSES),
            "conditional_baseline": {
                "rule": ("economic/operational limitation with a "
                         "concrete enabling technological trajectory"),
                "per_candidate_basis": (
                    "discovery_fabric/r412/temporal.py::"
                    "BASELINE_ELIGIBLE_JUSTIFICATIONS"),
            },
            "ineligible_causes": list(
                __import__("discovery_fabric.r412.temporal",
                           fromlist=["INELIGIBLE_CAUSES"]
                           ).INELIGIBLE_CAUSES),
            "prior_art_special_route": (
                "temporal evolution ONLY via transformation to "
                "NEW_MECHANISM / NEW_CAUSAL_ARCHITECTURE followed by "
                "a fresh collision search; a better implementation of "
                "the existing mechanism is not enough (directive §2)"),
            "classified_eligible": eligible_ids,
            "classified_special_route": special_ids,
            "classified_ineligible": ineligible_ids,
        },
        "temporal_evolution_rules": [
            "the 2055 step is a CONSTRAINED thought experiment: the "
            "descendant must specifically overcome the RECORDED cause "
            "of death (the 5-question chain: what killed it / what "
            "prevented it / what capability removes the constraint / "
            "why the causal mechanism changes / what new architecture "
            "results)",
            "'10x better, cheaper, faster, smaller' without the "
            "causal chain is invalid",
            "the temporal stage NEVER overwrites or reinterprets the "
            "original death (the original record is an immutable "
            "input; the lineage is machine-readable end to end)",
        ],
        "capability_rules": [
            "every assumed capability gets an evidence record with "
            "the directive §4 fields; epistemic_class is "
            "EXTRAPOLATED_TREND, set by the machinery, never FACT or "
            "EVIDENCE",
            "required values derive from the descendant's engineering "
            "requirements FIRST; never a convenient trend with "
            "requirements calculated around it",
            "extrapolated_2055_value < required_value FAILS the "
            "assumption deterministically; no rhetorical rescue",
            "backward decomposition: 2055 invention -> capabilities -> "
            "subsystems -> physical effects -> enabling technologies, "
            "each independently evidenced ('AI/sensors/materials "
            "exist' is NOT sufficient — the record must show the "
            "capability at the required operating regime)",
        ],
        "present_capability_promotion_rules": [
            "promotion ONLY when every essential capability: trend "
            "gate PASS + decomposition exists_today=yes + operating "
            "regime match + INDEPENDENT retrieval verification "
            "(distinctive-term coverage >= 0.5 AND a regime token in "
            "the same record)",
            "a near-term leading indicator with measurement method, "
            "window, expected signal, and failure threshold is "
            "required (directive §10)",
            "'the ingredients exist' is never sufficient: the "
            "promotion test is capabilities + operating conditions + "
            "coupling -> NEW CAUSAL ARCHITECTURE -> NEW FUNCTIONAL "
            "BEHAVIOR -> MEASURABLE ADVANTAGE",
        ],
        "novelty_rules": [
            "fresh novelty classification over freshly retrieved "
            "prior art, in the 5-class taxonomy "
            "KNOWN_MECHANISM_KNOWN_APPLICATION / "
            "KNOWN_MECHANISM_NEW_APPLICATION / "
            "KNOWN_MECHANISM_NEW_INTEGRATION / NEW_CAUSAL_ARCHITECTURE "
            "/ NEW_MECHANISM",
            "only KNOWN_MECHANISM_NEW_INTEGRATION / "
            "NEW_CAUSAL_ARCHITECTURE / NEW_MECHANISM have a "
            "realistic path to the invention pipeline; "
            "NEW_APPLICATION is commercially interesting but never "
            "mislabeled as novel mechanism",
            "the fresh pipeline inherits NOTHING but lineage (fresh "
            "mechanism characterization, distinctness, collision, "
            "prior art, evidence, engineering, attack — directive §8)",
        ],
        "attack_rules": [
            "the temporal attacker is a fresh context (R412-TEMPORAL-"
            "ATTACK-V1): it sees the evolved mechanism, claimed "
            "capabilities, and fresh retrieval — NEVER the original "
            "candidate or its 2026 verdict",
            "the RECOMBINATION_CHALLENGE ('new causal architecture "
            "using demonstrated capabilities, or recombined known "
            "technology renamed?') is an explicit first challenge "
            "class (directive §11)",
            "the attacker family's NOT_CALIBRATED state (FPR 0.8) "
            "travels with every verdict as a recorded caveat",
        ],
        "cemetery_rules": [
            "candidates failing both stages get the FULL lineage "
            "entry: ORIGINAL -> CAUSE_OF_DEATH -> 2055_EVOLUTION -> "
            "EVOLUTION_DEATH (evolutionary negative knowledge)",
            "TEMPORAL_PROJECTION descendants enter the TECHNOLOGY_"
            "RADAR with watch conditions (the missing capability); "
            "the schema barrier machine-blocks their entry into "
            "buyer transfer states",
        ],
        "stopping_rules": [
            "the experiment runs the eligible + special-route set to "
            "completion; the funnel reports every level honestly",
            "transport failures are INCOMPLETE and re-queued once "
            "within budget; exhausted stages stay INCOMPLETE",
            "the experiment STOPS before any physical spend; no "
            "buyer packages are constructed (buyer_qualified_packages "
            "counts fresh-pipeline survivors only, honestly 0 unless "
            "survivors exist)",
        ],
        "no_quota_forcing_declaration": (
            "ZERO is an acceptable scientific outcome. No threshold "
            "is lowered, no quota forces a rediscovery, and an empty "
            "result is reported as measured (Art. LXVIII; the "
            "directive's own declaration)"),
        "frozen_inputs_integrity": {
            "r411_run_dir_readonly": True,
            "waterfall_readonly": True,
            "rule": ("the replay NEVER writes into R411/ or the "
                     "waterfall; outputs go to R412/TEMPORAL_REPLAY/ "
                     "only (pinned by test)"),
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(prereg, indent=1))
    print(f"preregistration written: {OUT}")
    print(f"sha256: {_sha(OUT.read_text())}")
    print(f"population: {len(scored)} unique "
          f"(raw {raw_accepted}); deaths: {len(deaths)}")
    print(f"eligible: {eligible_ids}")
    print(f"special route: {special_ids}")
    print(f"ineligible: {ineligible_ids}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
