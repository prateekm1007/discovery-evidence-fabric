"""discovery_fabric/engine/answer_composer.py — the ANSWER COMPOSER
(R6 owner directive 2026-11-11, item 3: "ANSWER COMPOSER first (as
specified): one LLM call writes the full engineer-facing answer from
constraints + variables + top candidates + packet + verification;
contract applied to the composed answer").

What this replaces (Art. LXIV: superseded implementations are retired
in the same change): the harness's `_extract_pipeline_answer`
field-concatenation (mechanism + causal_chain + killer_experiment
lines stitched from the invention spec / candidate envelope) was the
de-facto answer writer. The composed answer supersedes it when the
composer ran; the concatenation stays as the honest fallback when the
composer is disabled (ablation arm COMPOSE-leave-one-out) or failed
(typed INCOMPLETE, never a fake composition).

ONE LLM call (the owner's "fast and lean" directive): the composer
prompt carries constraints + user variables + top candidates (with
attack/verification verdicts) + the frozen packet + the verification
summary; the model writes the full engineer-facing answer in one shot.
The deterministic answer-shape contract (answer_contract.py) runs on
the composed text; on violation there is ONE repair retry with the
violation list fed back (deterministic feedback, no gate widening,
Art. VII). A composer that fails twice returns the typed failure and
the harness falls back to the superseded extraction — never a silent
regression (Art. IV).

The composer grants no epistemic authority (Art. XVIII): it WRITES the
engineer-facing answer; every claim's provenance comes from the packet
and the candidate records, and unverified numbers stay labeled.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

ANSWER_COMPOSER_VERSION = "answer_composer/1.0.0"

_COMPOSER_SYSTEM = (
    "You write the final engineer-facing answer of a discovery pipeline. "
    "You receive the problem's constraints, the user's stated variables, "
    "the pipeline's top intervention candidates WITH their attack and "
    "verification verdicts, the frozen evidence packet, and a verification "
    "summary. You write ONE complete, specific, testable engineering "
    "answer. Rules: (1) every number you state either comes from the "
    "packet/user variables/candidates, or is labeled ASSUMPTION on the "
    "same line, or is given as a defined calibration rule (e.g. baseline "
    "+ 3 sigma from 14 days of healthy data); (2) a killed candidate is "
    "NEVER presented as the recommendation — if everything was killed, "
    "say so and present the best surviving hypothesis as UNVERIFIED; "
    "(3) respect the user's stated variables exactly (a constraint the "
    "user fixed must stay fixed); (4) name the falsification test "
    "concretely; (5) English only, no markdown headings, plain text.")

_COMPOSER_PROMPT = """Write the final engineering answer for this problem.

PROBLEM:
- Device: {device}
- Failure: {failure}
- Failure mode: {failure_mode}

USER'S STATED CONSTRAINTS AND VARIABLES (must be respected exactly):
{variables_block}

TOP CANDIDATES FROM THE PIPELINE (with verification verdicts):
{candidates_block}

FROZEN EVIDENCE PACKET (the only citable evidence; cite item ids):
{packet_block}

VERIFICATION SUMMARY:
{verification_block}

Write the full engineer-facing answer now (max ~450 words): the
recommended intervention/design with concrete parameter values, the
expected measurable effect, how it respects each stated constraint, the
falsification test, and which evidence items support it. Answer-shape
contract{shape_hint}:
{shape_block}"""

_REPAIR_PROMPT = """Your previous answer violated the deterministic
answer-shape contract:

VIOLATIONS:
{violations}

PREVIOUS ANSWER:
{previous}

PROBLEM (for context): {device} — {failure}
USER'S STATED CONSTRAINTS AND VARIABLES:
{variables_block}

Rewrite the FULL answer fixing every violation. Same rules as before:
numbers come from packet/candidates or carry ASSUMPTION or a defined
calibration rule; respect the user's variables; name the falsification
test. Contract{shape_hint}:
{shape_block}"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def _packet_block(packet: Optional[List[Dict[str, Any]]]) -> str:
    if not packet:
        return "(no frozen packet available for this composition — state "
        "that no retrieved evidence supports the answer and label "
        "accordingly)"
    lines = []
    for i, e in enumerate(packet[:14], 1):
        if not isinstance(e, dict):
            continue
        title = str(e.get("title") or "(untitled)")[:120]
        eid = str(e.get("id") or e.get("source_id") or f"item{i}")
        abstract = str(e.get("abstract") or e.get("text") or "")[:600]
        lines.append(f"[{eid}] {title}\n  {abstract}")
    return "\n".join(lines) if lines else "(packet carried no readable items)"


def _candidates_block(cands: List[Dict[str, Any]]) -> str:
    if not cands:
        return "(no candidates reached this composition — compose from the "
        "constraints and state the evidence status honestly)"
    lines = []
    for i, c in enumerate(cands[:5], 1):
        if not isinstance(c, dict):
            continue
        cid = str(c.get("candidate_id") or f"candidate{i}")
        verdict = str(c.get("attack_verdict") or c.get("verdict")
                      or c.get("state") or "NO_VERDICT")
        mech = str(c.get("mechanism") or "")[:280]
        interv = str(c.get("intervention") or "")[:280]
        eff = str(c.get("expected_effect") or c.get("predicted_effect")
                  or "")[:200]
        lines.append(
            f"{i}. {cid} verdict={verdict}\n"
            f"   mechanism: {mech}\n"
            f"   intervention: {interv}\n"
            f"   expected effect: {eff}")
    return "\n".join(lines)


def _variables_block(problem: Dict[str, Any]) -> str:
    rows = []
    if problem.get("constraint"):
        rows.append(f"- CONSTRAINT: {problem['constraint']}")
    if problem.get("clarification_text"):
        rows.append(f"- USER-STATED CLARIFICATION: "
                    f"{problem['clarification_text']}")
    for v in problem.get("user_variables") or []:
        rows.append(f"- {v}")
    return "\n".join(rows) or "(none stated)"


def _verification_block(verification: Optional[Dict[str, Any]]) -> str:
    if not verification:
        return "(no verification summary recorded)"
    rows = []
    for k in ("attack_overall", "physics_status", "contradiction_status",
              "premise_gate", "final_status"):
        v = verification.get(k)
        if v:
            rows.append(f"- {k}: {v}")
    unv = verification.get("unverified_numbers")
    if unv:
        rows.append(f"- numbers absent from the packet (label or drop "
                    f"them): {unv}")
    return "\n".join(rows) or "(verification recorded no typed states)"


def compose_answer(problem: Dict[str, Any],
                   packet: Optional[List[Dict[str, Any]]],
                   candidates: List[Dict[str, Any]],
                   verification: Optional[Dict[str, Any]],
                   question_type: str,
                   llm_generate=None,
                   max_tokens: int = 1000,
                   ) -> Dict[str, Any]:
    """ONE LLM call writes the full engineer-facing answer; the
    deterministic contract is applied to the composed text; ONE repair
    retry on violation. Returns a record (never raises to the caller):
    {answer, composer: {...}, contract: {...}, state}.

    `llm_generate` is injectable for tests (the engine's
    mechanism_space.llm_generate by default — ONE transport path,
    Art. X)."""
    from .answer_contract import validate_answer, ANSWER_SHAPE_BLOCK
    if llm_generate is None:
        from .mechanism_space import llm_generate
    shape = ANSWER_SHAPE_BLOCK.get(question_type, "")
    shape_hint = "" if shape else " (none — unknown question type)"
    prompt = _COMPOSER_PROMPT.format(
        device=problem.get("device", ""),
        failure=problem.get("failure", ""),
        failure_mode=problem.get("failure_mode", ""),
        variables_block=_variables_block(problem),
        candidates_block=_candidates_block(candidates or []),
        packet_block=_packet_block(packet),
        verification_block=_verification_block(verification),
        shape_hint=shape_hint, shape_block=shape)
    rec: Dict[str, Any] = {
        "composer_version": ANSWER_COMPOSER_VERSION,
        "n_llm_calls": 0,
        "question_type": question_type,
        "started_at": _utc_now(),
    }
    res = llm_generate(prompt, system=_COMPOSER_SYSTEM, max_tokens=max_tokens,
                       purpose="answer_composer")
    rec["n_llm_calls"] += 1
    rec["prompt_sha256"] = res.get("prompt_hash")
    rec["provider_route"] = res.get("provider_route") or res.get("provider")
    rec["model"] = res.get("model")
    rec["cost_provenance"] = res.get("cost_provenance")
    if not res.get("ok") or not (res.get("content") or "").strip():
        rec["state"] = "COMPOSE_FAILED_TRANSPORT"
        rec["error"] = str(res.get("error") or res.get("status"))[:300]
        rec["answer"] = None
        rec["finished_at"] = _utc_now()
        return rec
    answer = res["content"].strip()
    rec["output_sha256"] = res.get("output_hash")
    contract = validate_answer(answer, question_type,
                               packet=packet or [],
                               user_variables=list(
                                   problem.get("user_variables") or []))
    rec["contract_first_pass"] = {"valid": contract.get("valid"),
                                  "violations": contract.get("violations")}
    if contract.get("valid") is not True:
        # ONE deterministic repair retry: the violations travel back in
        repair_prompt = _REPAIR_PROMPT.format(
            violations="\n".join(f"- {v}" for v in
                                 contract.get("violations") or []),
            previous=answer[:3000],
            device=problem.get("device", ""),
            failure=problem.get("failure", ""),
            variables_block=_variables_block(problem),
            shape_hint=shape_hint, shape_block=shape)
        res2 = llm_generate(repair_prompt, system=_COMPOSER_SYSTEM,
                            max_tokens=max_tokens,
                            purpose="answer_composer_repair")
        rec["n_llm_calls"] += 1
        if res2.get("ok") and (res2.get("content") or "").strip():
            answer2 = res2["content"].strip()
            contract2 = validate_answer(answer2, question_type,
                                        packet=packet or [],
                                        user_variables=list(
                                            problem.get("user_variables")
                                            or []))
            rec["contract_after_repair"] = {
                "valid": contract2.get("valid"),
                "violations": contract2.get("violations")}
            if contract2.get("valid") is True or (
                    len(contract2.get("violations") or []) <
                    len(contract.get("violations") or [])):
                answer = answer2
                contract = contract2
                rec["output_sha256"] = res2.get("output_hash")
                rec["repaired"] = True
    rec["answer"] = answer
    rec["contract"] = {"valid": contract.get("valid"),
                       "violations": contract.get("violations"),
                       "bindings": contract.get("bindings"),
                       "question_type": question_type}
    rec["state"] = ("COMPOSED_CONTRACT_VALID"
                    if contract.get("valid") is True
                    else "COMPOSED_CONTRACT_INVALID")
    rec["finished_at"] = _utc_now()
    return rec


def candidates_from_state(env_dict: Dict[str, Any],
                          top_n: int = 5) -> List[Dict[str, Any]]:
    """Pull the top candidates (post-attack, ranked) from the run
    envelope dict. Reads ONLY recorded state (no re-derivation)."""
    cands: List[Dict[str, Any]] = []
    rs = env_dict.get("ranked_results") or {}
    ranked = rs.get("results") or rs.get("candidates") or []
    for r in ranked[:top_n]:
        if isinstance(r, dict):
            cands.append(r)
    if not cands:
        mm = env_dict.get("mechanism_map") or {}
        raw = mm.get("raw_candidate")
        if isinstance(raw, dict):
            raw = dict(raw)
            raw.setdefault("attack_verdict",
                           mm.get("attack_overall") or "NO_VERDICT")
            cands.append(raw)
    if not cands:
        for m in (env_dict.get("mechanisms") or [])[:top_n]:
            if isinstance(m, dict):
                cands.append(m)
    return cands
