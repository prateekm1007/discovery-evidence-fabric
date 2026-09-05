"""discovery_fabric/r412/synthesis_benchmark.py — P0-3: benchmark
synthesis models on frozen evidence (CEO R412 directive).

> Same evidence. Same candidate contract. Same downstream verifier.
> Compare models on: mechanism distinctness, evidence support,
> collision rate, physics coherence, testability, attacker survival,
> expected information gain / cost.
> The metric that matters: SURVIVING CAUSAL TECHNOLOGY PER UNIT
> COMPUTE. Not prose quality.

PROTOCOL (pre-registered before the live run; Art. XXVII/LIX):

  FROZEN INPUTS: three R411 domain evidence pools (heat_exchanger,
  power_electronics, data_center_thermal — pools that produced
  shortlisted candidates in R411), one extraction prompt per domain:
  the CROSS_DOMAIN_FORCING task (the R411 s6 call — the most
  productive single call class: 122/400 accepted candidates carried
  it). The prompt is built by the UNMODIFIED R411 machinery
  (extract.build_extraction_prompt) with the UNMODIFIED system string
  and the UNMODIFIED 2600-token cap: the candidate contract is exactly
  the contract R411 ran. No prompt tuning (Art. LIX).

  MODELS: one pass per model, pinned via the registry's operator-pin
  mechanism (the same env pins the R411 campaign and the R412
  calibration used). A model that cannot complete the protocol is
  recorded honestly (transport failure), never excluded silently.

  DETERMINISTIC DOWNSTREAM VERIFIERS (identical across models — the
  comparability requirement):
    1. no-fabrication parse gate        (R411 extract.parse_candidates)
    2. engineering gate                 (R411 structural checks)
    3. early collision screen           (R412 P0-2, vs the same pool)
    4. mechanism distinctness           (pairwise
       mechanism_space.compare_candidates within the model's accepted
       set: EQUIVALENT merges; DISTINCT counts; INDETERMINATE kept
       visible, never counted as distinct — Art. XLII)
    5. evidence support                 (distinct pool records cited;
       ref-per-candidate; the F4a span-verification proposer is NOT
       run here — recorded as not-run, the deterministic citation
       level only)
    6. attacker survival                (the R411 attacker on the
       candidates that passed every deterministic gate, CAPPED at 3
       per model; the attacker is measured NOT_CALIBRATED
       (R412/P0-1, FPR 0.8) — survival numbers are recorded WITH that
       caveat and are NOT a selection criterion)

  HEADLINE METRIC: qualified candidates per unit compute (wall
  seconds), with the attacker-survival variant reported alongside its
  caveat. Model selection itself is NOT performed by this benchmark
  (Art. LIX: this is a measurement; any selection is a separate,
  recorded operator decision).

Constitutional grounding:
  - Art. XLVII: the baseline (the prompt, the pool, the verifiers) is
    identical across arms — no arm gets a stage the other lacks.
  - Art. LVI: the objective is surviving technology per unit cost,
    not candidate count.
  - Art. LXII: per-call hashes, pinned models, and wall times are
    committed with the results.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

BENCHMARK_VERSION = "R412-SYNTHESIS-BENCHMARK-V1"

FROZEN_DOMAINS = [
    "heat_exchanger",
    "power_electronics",
    "data_center_thermal",
]

ATTACK_CAP_PER_MODEL = 3

MODEL_PASSES: Dict[str, Dict[str, str]] = {
    "minimax-m3:free": {
        "ENGINE_LLM_PROVIDER": "openrouter",
        "OPENROUTER_MODEL": "minimax/minimax-m3:free",
        "needs_gateway": "no",
    },
    "glm-4-plus": {
        "ENGINE_LLM_PROVIDER": "zai",
        "ZAI_MODEL": "glm-4-plus",
        "needs_gateway": "yes",
    },
    "glm-5.3-free": {
        "ENGINE_LLM_PROVIDER": "tokenrouter",
        "TOKENROUTER_MODEL": "z-ai/glm-5.3-free",
        "needs_gateway": "no",
    },
}

EXTRACTION_SYSTEM = (
    "You are a mechanism-discovery instrument. Ground every candidate "
    "in the evidence records. Never invent record ids or findings.")
EXTRACTION_MAX_TOKENS = 2600


def load_frozen_problem(domain_id: str, run_dir: Path) -> Dict[str, Any]:
    """The frozen pool + domain spec + entry for one benchmark problem."""
    from discovery_fabric.r411.domain_matrix import DOMAIN_MATRIX_SPEC
    snapshot = json_load(run_dir / "evidence" / f"{domain_id}.json")
    return {
        "domain_id": domain_id,
        "entry": {"domain_id": domain_id},
        "domain_spec": DOMAIN_MATRIX_SPEC[domain_id],
        "pool": snapshot["pool"],
        "pool_sha256": snapshot.get("pool_sha256"),
    }


def json_load(path: Path):
    import json
    return json.loads(Path(path).read_text())


def build_problem_prompt(problem: Dict[str, Any]) -> Tuple[str, str]:
    """The frozen CROSS_DOMAIN_FORCING prompt (identical for every
    model — the comparability requirement). Returns (prompt, marker)."""
    from discovery_fabric.r411.extract import (
        CROSS_DOMAIN_MARKER, build_extraction_prompt)
    prompt = build_extraction_prompt(
        problem["entry"], problem["domain_spec"], problem["pool"],
        pain_class=CROSS_DOMAIN_MARKER)
    return prompt, CROSS_DOMAIN_MARKER


def run_model_pass(model_id: str, problems: List[Dict[str, Any]],
                   run_dir: Path,
                   llm_generate: Optional[Callable] = None
                   ) -> Dict[str, Any]:
    """One model's pass over the frozen problems. llm_generate is
    injectable for hermetic tests (defaults to the engine wrapper,
    which honors the pass's env pins)."""
    from discovery_fabric.r411.extract import parse_candidates
    gen = llm_generate or _default_generate
    results: List[Dict[str, Any]] = []
    wall_seconds = 0.0
    calls = 0
    for problem in problems:
        prompt, marker = build_problem_prompt(problem)
        t0 = time.perf_counter()
        meta = gen(
            prompt,
            system=EXTRACTION_SYSTEM,
            purpose="r412_synthesis_benchmark",
            max_tokens=EXTRACTION_MAX_TOKENS)
        wall_seconds += time.perf_counter() - t0
        calls += 1
        if not meta.get("ok"):
            results.append({
                "domain_id": problem["domain_id"],
                "status": "INCOMPLETE_TRANSPORT",
                "error": str(meta.get("error") or meta.get("status")
                             )[:200],
                "prompt_hash": meta.get("prompt_hash"),
            })
            continue
        parsed = parse_candidates(
            meta.get("content") or "", problem["domain_id"],
            problem["pool"],
            generation_meta={
                "provider": meta.get("provider"),
                "model": meta.get("model"),
                "prompt_hash": meta.get("prompt_hash"),
                "output_hash": meta.get("output_hash"),
            })
        for c in parsed["accepted"]:
            c["extraction_call"] = "CROSS_DOMAIN_FORCING"
        results.append({
            "domain_id": problem["domain_id"],
            "status": "OK",
            "accepted": parsed["accepted"],
            "rejected": parsed["rejected"],
            "prompt_hash": meta.get("prompt_hash"),
            "output_hash": meta.get("output_hash"),
            "provider": meta.get("provider"),
            "model": meta.get("model"),
        })
    return {
        "model_id": model_id,
        "calls": calls,
        "wall_seconds": round(wall_seconds, 2),
        "per_problem": results,
    }


def _default_generate(prompt, **kw):
    from discovery_fabric.engine.adapters import load_credentials
    load_credentials()
    from discovery_fabric.engine.mechanism_space import llm_generate
    return llm_generate(prompt, **kw)


# ---------------------------------------------------------------------------
# Deterministic downstream verifiers (identical across models)
# ---------------------------------------------------------------------------

def engineering_gate(cand: Dict[str, Any]) -> Dict[str, Any]:
    """The R411 structural gate (byte-equivalent logic)."""
    checks = {
        "causal_chain_steps": len(cand.get("causal_chain") or []) >= 3,
        "governing_variables": bool(cand.get("governing_variables")),
        "equation_present": bool(cand.get("equations")),
        "boundary_conditions": bool(cand.get("boundary_conditions")),
        "intervention_realizable": bool(cand.get("intervention")),
        "kill_condition": bool(
            (cand.get("killer_experiment") or {}).get("kill_condition")),
        "cost_class_valid": (cand.get("killer_experiment") or {}).get(
            "cost_class") in ("BENCH", "LAB", "PILOT", "FIELD"),
        "baseline_metric": bool(
            (cand.get("baseline") or {}).get("baseline_metric")),
    }
    return {"passed": all(checks.values()),
            "failed_checks": [k for k, v in checks.items() if not v]}


def screen_collision(cand: Dict[str, Any],
                     pool: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The R412 P0-2 early collision screen against the problem's own
    pool."""
    from discovery_fabric.r412.collision_screen import screen_candidate
    return screen_candidate(cand, pool, [])


def distinctness_analysis(candidates: List[Dict[str, Any]]
                          ) -> Dict[str, Any]:
    """Pairwise mechanism-space comparison within one model's accepted
    set (Art. XLII: EQUIVALENT merges, DISTINCT counts, INDETERMINATE
    visible)."""
    from discovery_fabric.engine.mechanism_space import compare_candidates
    n = len(candidates)
    pairs = {"EQUIVALENT": 0, "DISTINCT": 0, "INDETERMINATE": 0}
    equivalent_pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            verdict = compare_candidates(candidates[i], candidates[j])
            v = verdict.get("verdict", "INDETERMINATE")
            pairs[v] = pairs.get(v, 0) + 1
            if v == "EQUIVALENT":
                equivalent_pairs.append(
                    [candidates[i]["candidate_id"],
                     candidates[j]["candidate_id"]])
    # distinct mechanism count: union-find over EQUIVALENT pairs
    parent = list(range(n))
    id_index = {c["candidate_id"]: i for i, c in enumerate(candidates)}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in equivalent_pairs:
        parent[find(id_index[a])] = find(id_index[b])
    distinct = len({find(i) for i in range(n)})
    return {
        "n_candidates": n,
        "pairwise": pairs,
        "equivalent_merge_pairs": equivalent_pairs,
        "distinct_mechanisms": distinct,
    }


def downstream_verdicts(model_pass: Dict[str, Any],
                        problems: List[Dict[str, Any]]
                        ) -> Dict[str, Any]:
    """Run every DETERMINISTIC verifier over one model's accepted
    candidates. Returns per-candidate verdicts + aggregates."""
    pool_by_domain = {p["domain_id"]: p["pool"] for p in problems}
    per_candidate = []
    qualified: List[Dict[str, Any]] = []
    for pr in model_pass["per_problem"]:
        if pr.get("status") != "OK":
            continue
        pool = pool_by_domain[pr["domain_id"]]
        for cand in pr["accepted"]:
            eng = engineering_gate(cand)
            scr = screen_collision(cand, pool)
            qualified_flag = (
                eng["passed"] and scr["decision"] == "PASS")
            row = {
                "candidate_id": cand["candidate_id"],
                "domain_id": pr["domain_id"],
                "no_fabrication_gate": True,  # accepted by the parser
                "engineering_passed": eng["passed"],
                "engineering_failed_checks": eng["failed_checks"],
                "collision_screen": scr["decision"],
                "collision_screen_matched": [
                    m["record_id"] for m in scr["matched_records"][:2]],
                "evidence_refs": cand.get("evidence_refs") or [],
                "qualified_deterministic": qualified_flag,
            }
            per_candidate.append(row)
            if qualified_flag:
                qualified.append(cand)
    return {
        "per_candidate": per_candidate,
        "qualified": qualified,
    }


def model_metrics(model_pass: Dict[str, Any], downstream: Dict[str, Any],
                  distinctness: Dict[str, Any],
                  attack_results: Optional[List[Dict[str, Any]]] = None
                  ) -> Dict[str, Any]:
    """The per-model metric block (the comparability contract)."""
    accepted_total = sum(
        len(pr.get("accepted") or []) for pr in model_pass["per_problem"])
    rejected_total = sum(
        len(pr.get("rejected") or []) for pr in model_pass["per_problem"])
    transport_failures = sum(
        1 for pr in model_pass["per_problem"]
        if pr.get("status") != "OK")
    wall = model_pass.get("wall_seconds") or 0.0
    qualified = len(downstream["qualified"])
    evidence_refs = [r for row in downstream["per_candidate"]
                     for r in row["evidence_refs"]]
    attacked = 0
    survived = 0
    for a in attack_results or []:
        attacked += 1
        if a.get("verdict") == "SURVIVED":
            survived += 1
    m = {
        "model_id": model_pass["model_id"],
        "calls": model_pass.get("calls"),
        "wall_seconds": wall,
        "transport_failures": transport_failures,
        "candidates_accepted": accepted_total,
        "candidates_rejected_by_gate": rejected_total,
        "contract_valid_rate": round(
            accepted_total / (accepted_total + rejected_total), 4)
        if (accepted_total + rejected_total) else None,
        "engineering_pass_rate": round(
            sum(1 for row in downstream["per_candidate"]
                if row["engineering_passed"])
            / len(downstream["per_candidate"]), 4)
        if downstream["per_candidate"] else None,
        "collision_screen_pass_rate": round(
            sum(1 for row in downstream["per_candidate"]
                if row["collision_screen"] == "PASS")
            / len(downstream["per_candidate"]), 4)
        if downstream["per_candidate"] else None,
        "distinct_mechanisms": distinctness["distinct_mechanisms"],
        "pairwise_verdicts": distinctness["pairwise"],
        "distinct_evidence_records_cited": len(set(evidence_refs)),
        "mean_evidence_refs_per_candidate": round(
            len(evidence_refs) / len(downstream["per_candidate"]), 3)
        if downstream["per_candidate"] else None,
        "qualified_deterministic": qualified,
        "attacker_attacked": attacked,
        "attacker_survived": survived,
        "attacker_survival_caveat": (
            "the attacker is measured NOT_CALIBRATED (R412/P0-1: FPR "
            "0.8 on known-good); survival numbers are recorded with "
            "that caveat and are NOT a selection criterion"),
    }
    # headline: qualified causal technology per unit compute
    m["qualified_per_compute_second"] = round(
        qualified / wall, 6) if wall > 0 else None
    m["distinct_mechanisms_per_compute_second"] = round(
        distinctness["distinct_mechanisms"] / wall, 6) if wall > 0 else None
    m["surviving_per_compute_second"] = round(
        survived / wall, 6) if wall > 0 else None
    return m
