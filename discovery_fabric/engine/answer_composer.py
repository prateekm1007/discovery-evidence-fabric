"""discovery_fabric/engine/answer_composer.py — the ANSWER COMPOSER
(R6 owner directive 2026-11-11, item 3: "ANSWER COMPOSER first (as
specified): one LLM call writes the full engineer-facing answer from
constraints + variables + top candidates + packet + verification;
contract applied to the composed answer").

What this supersedes (Art. LXIV): the harness's `_extract_pipeline_answer`
field-concatenation (mechanism + causal_chain + killer_experiment
lines stitched from the invention spec / candidate envelope) was the
de-facto answer writer. P0-4 (owner directive 2026-11-11, item 4):
the composed answer is the ONLY answer authority on the normal path —
the superseded construction is never a silent fallback when the
composer is disabled or failed (Art. IV: a weaker verification path
is never silently activated). It remains reachable ONLY from the
explicitly selected no_COMPOSE ablation arm, clearly labelled
DIAGNOSTIC, and is retired once that scoped ablation use is complete.

ONE LLM call (the owner's "fast and lean" directive): the composer
prompt carries constraints + user variables + top candidates (with
attack/verification verdicts) + the frozen packet + the verification
summary; the model writes the full engineer-facing answer in one shot.
The deterministic answer-shape contract (answer_contract.py) runs on
the composed text; on violation there is ONE repair retry with the
violation list fed back (deterministic feedback, no gate widening,
Art. VII). A composer that fails twice returns the typed failure;
P0-4 (owner directive 2026-11-11, item 4): the harness's normal path
then delivers the typed no-answer state — the superseded extraction
is reachable only from the explicitly selected no_COMPOSE ablation
arm, clearly labelled DIAGNOSTIC (Art. IV), and is retired when that
scoped ablation use is complete (Art. LXIV).

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
    "concretely; (5) every EVIDENCE-BACKED label MUST be followed on the "
    "SAME line by the bracketed packet item id that supports it, e.g. "
    "\"EVIDENCE-BACKED [item-id]\" — a label with no bracketed id fails "
    "the deterministic contract; (6) English only, no markdown headings, "
    "plain text.")

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
        if c.get("hypothesis_unverified") or _is_hypothesis_verdict(verdict):
            verdict = f"UNVERIFIED_HYPOTHESIS({verdict})"
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
    # P0-5 (owner directive 2026-11-11, item 5): the user's clarified
    # text is a citable provenance span for the contract — it travels
    # into validate_answer on BOTH compose paths (compose + repair),
    # as its own entry (a number in the clarification is not support
    # for a quantity it never names, and vice versa)
    _clar_text = str(problem.get("clarification_text") or "").strip()
    _clar_ans = problem.get("clarification_answer")
    if not _clar_text and isinstance(_clar_ans, str):
        _clar_text = _clar_ans.strip()
    _clarification = _clar_text or None
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
                                   problem.get("user_variables") or []),
                            clarification=_clarification)
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
                                            or []),
                                            clarification=_clarification)
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


# ---------------------------------------------------------------------
# P0-2 (owner directive 2026-11-11, item 2): EXPLICIT admission
# allowlist. A candidate may enter composition only through a
# RECORDED terminal verdict in one of two classes; every other
# verdict is non-admissible and typed (Art. XXV: unknown stays
# unknown; Art. LXI: infrastructure failure is never a scientific
# rejection — and never a scientific admission either; Art. L /
# LXXXI: an escalated objection is a hypothesis, not an invention).
#
#  CLASS SURVIVED — admissible as the recommendation:
#      recorded post-gate survivor verdicts.
#
#  CLASS HYPOTHESIS — admissible only as a clearly marked unverified
#      hypothesis, never as an endorsed invention:
#      escalated objection / unverified survivor.
#
#  NON-ADMISSIBLE (typed): kill/reject verdicts; evaluator and
#      evaluation failures (EVALUATOR_CALL_FAILED,
#      EVALUATION_FAILED, PROVIDER_UNAVAILABLE); unadjudicated
#      states (NOT_RUN, INCOMPLETE_*, PENDING, PENDING_*); unknown
#      (UNKNOWN, INCONCLUSIVE, INDETERMINATE); generic errors;
#      empty / NO_VERDICT.

_KILL_STATES = {"KILLED", "KILLED_DETERMINISTIC", "KILLED_SCIENTIFIC",
                "REJECTED", "REJECTED_SCIENTIFIC", "REJECTED_ATTACK",
                "KILL"}
_ADMISSIBLE_SURVIVED = frozenset({"PASS", "SURVIVED", "SURVIVE"})
_HYPOTHESIS_STATES = frozenset({"ESCALATED_OBJECTION",
                                "UNVERIFIED_HYPOTHESIS",
                                "HYPOTHESIS", "SURVIVED_UNVERIFIED"})


def _non_admissible_reason(v: str) -> str:
    """P0-2: the typed state of a non-admissible verdict (recorded in
    the NO_ADMISSIBLE state — typed, never buried; Art. XXV)."""
    if v in _KILL_STATES or "KILL" in v or "REJECT" in v:
        return "KILLED_OR_REJECTED"
    if v in ("EVALUATOR_CALL_FAILED", "EVALUATION_FAILED",
             "PROVIDER_UNAVAILABLE") \
            or v.startswith("EVALUATOR_") \
            or v.startswith("EVALUATION_"):
        return "EVALUATOR_FAILURE"
    if v in ("NOT_RUN", "PENDING") \
            or v.startswith("INCOMPLETE_") \
            or v.startswith("PENDING_"):
        return "NOT_RUN_OR_INCOMPLETE"
    if v in ("UNKNOWN", "INCONCLUSIVE", "INDETERMINATE"):
        return "UNKNOWN_OR_INCONCLUSIVE"
    if v == "ERROR" or v.endswith("_FAILED") or v.endswith("ERROR"):
        return "ERROR"
    return f"NON_ADMISSIBLE_{v[:60]}"


def classify_verdict_admissibility(verdict: str) -> Dict[str, Any]:
    """P0-2 verdict classification against the explicit allowlist.

    Returns {admissible, class, hypothesis, reason}:
      class    in {"SURVIVED", "HYPOTHESIS", "NON_ADMISSIBLE"};
      reason   typed state of a non-admissible verdict (None when
               admissible)."""
    v = str(verdict or "").strip().upper()
    if not v or v == "NO_VERDICT":
        return {"admissible": False, "class": "NON_ADMISSIBLE",
                "hypothesis": False, "reason": "NO_VERDICT"}
    if v in _ADMISSIBLE_SURVIVED:
        return {"admissible": True, "class": "SURVIVED",
                "hypothesis": False, "reason": None}
    if v in _HYPOTHESIS_STATES or "ESCALATED" in v:
        return {"admissible": True, "class": "HYPOTHESIS",
                "hypothesis": True, "reason": None}
    return {"admissible": False, "class": "NON_ADMISSIBLE",
            "hypothesis": False, "reason": _non_admissible_reason(v)}


def _admissible_verdict(verdict: str) -> bool:
    """P0-2: True ONLY for recorded terminal verdicts on the explicit
    allowlist (the survived class + the clearly marked hypothesis
    class). Every other verdict — evaluator failures, unadjudicated
    states, kills — is non-admissible."""
    return classify_verdict_admissibility(verdict)["admissible"]


def _is_hypothesis_verdict(verdict: str) -> bool:
    return classify_verdict_admissibility(verdict)["hypothesis"]


def _raw_attack_binding(env_dict: Dict[str, Any]) -> Optional[str]:
    """P0-2 record-based check that the envelope's attack record
    belongs to THIS raw candidate (the attack stage attacks exactly
    the envelope's mechanism_map.raw_candidate — adapters.py
    AttackEngineAdapter; a critique-revise pass re-stamps BOTH
    mechanism_map and attack_results with the same revision marker).

    Returns None when the record is bound to the raw candidate; a
    typed reason when the binding is broken or absent (a global
    attack status must not promote an unrelated or unadjudicated
    raw candidate)."""
    ar = env_dict.get("attack_results") or {}
    if not isinstance(ar, dict) or not ar:
        return ("ATTACK_RECORD_ABSENT: no attack record on the "
                "envelope — the raw candidate was never adjudicated")
    mm = env_dict.get("mechanism_map") or {}
    rev_mm = mm.get("revision") if isinstance(mm, dict) else None
    rev_ar = ar.get("revision")
    if (rev_mm or rev_ar) and rev_mm != rev_ar:
        return (f"ATTACK_RECORD_NOT_CANDIDATE_BOUND: mechanism_map "
                f"revision marker {rev_mm!r} != attack-record "
                f"revision marker {rev_ar!r} — the attack record "
                f"predates the candidate it would be cited for")
    return None


def _admission_analysis(env_dict: Dict[str, Any],
                       top_n: int = 5):
    """P0-2: one admission audit. Returns (admissible_cands, reasons):
    the gate-admissible candidates, and the typed reasons for every
    recorded verdict that FAILED the allowlist (recorded in the
    NO_ADMISSIBLE state — Art. XXV)."""
    cands: List[Dict[str, Any]] = []
    reasons: List[Dict[str, Any]] = []
    ar = env_dict.get("attack_results") or {}
    verdict = str(ar.get("overall") or "").strip().upper()

    # 1. Ranked survivors (post-gate records): the authority-backed
    #    path. A row is admissible only through its OWN recorded
    #    verdict — never a synthesized "PASS" for an unrecorded
    #    result (Art. VI/XXV: the record is the record).
    rs = env_dict.get("ranked_results")
    ranked = ((rs.get("results") or rs.get("candidates"))
              if isinstance(rs, dict) else rs) or []
    for r in list(ranked)[:top_n]:
        if not isinstance(r, dict):
            continue
        disp = str(r.get("disposition") or r.get("verdict") or "").upper()
        if disp != "SURVIVED":
            continue
        own = str(r.get("attack_verdict") or "").strip().upper()
        if not own:
            own = disp  # the recorded post-gate disposition itself
        cls = classify_verdict_admissibility(own)
        if not cls["admissible"]:
            reasons.append({"source": "ranked",
                            "candidate_id": str(r.get("candidate_id") or ""),
                            "verdict": own or "NO_VERDICT",
                            "reason": cls["reason"]})
            continue
        rr = dict(r)
        rr["attack_verdict"] = own
        rr["admission"] = {"class": cls["class"],
                           "hypothesis": cls["hypothesis"],
                           "reason": cls["reason"]}
        if cls["hypothesis"]:
            rr["hypothesis_unverified"] = True
        cands.append(rr)
    if cands:
        return cands[:top_n], reasons

    # 2. The one attack-adjudicated candidate on the lean path: the
    #    raw mechanism candidate admitted to ATTACK with its OWN
    #    recorded verdict, bound record-only (a global status must
    #    not promote an unrelated or unadjudicated candidate).
    mm = env_dict.get("mechanism_map") or {}
    raw = mm.get("raw_candidate") if isinstance(mm, dict) else None
    if not (isinstance(raw, dict) and raw):
        return [], reasons
    att = verdict or str(mm.get("attack_overall") or "NO_VERDICT")
    att = str(att).strip().upper()
    cls = classify_verdict_admissibility(att)
    binding = _raw_attack_binding(env_dict)
    if not cls["admissible"] or binding is not None:
        reasons.append({"source": "raw_candidate",
                        "candidate_id": str(raw.get("candidate_id") or ""),
                        "verdict": att or "NO_VERDICT",
                        "reason": binding or cls["reason"]})
        return [], reasons
    rec = dict(raw)
    rec["attack_verdict"] = att
    rec["verdict"] = att
    rec["admission"] = {"class": cls["class"],
                        "hypothesis": cls["hypothesis"],
                        "reason": cls["reason"],
                        "binding": "attack_record_bound"}
    if cls["hypothesis"]:
        rec["hypothesis_unverified"] = True
    # the candidate's OWN recorded evidence / contradiction /
    # technical-gate states, reported (never assumed — Art. XXV):
    # typed NOT_RECORDED when the run's records carry them absent.
    ev = ((env_dict.get("adjudication") or {}).get(
        "evidence_verification") or {})
    if isinstance(ev, dict) and "verified" in ev:
        ev_state = "VERIFIED" if ev.get("verified") else "NOT_VERIFIED"
    else:
        ev_state = "NOT_RECORDED"
    cons = env_dict.get("contradictions") or {}
    cons_state = str(cons.get("overall") or cons.get("status")
                     or "NO_CONTRADICTIONS_RECORDED")
    rec["own_recorded_states"] = {
        "evidence_verification": ev_state,
        "contradictions": cons_state,
        "technical_gates": {
            "not_an_intervention":
                raw.get("not_an_intervention_check", "NOT_RECORDED"),
            "anchor_domain":
                raw.get("anchor_domain_check", "NOT_RECORDED"),
        },
    }
    cands.append(rec)
    return cands, reasons


def candidates_from_state(env_dict: Dict[str, Any],
                          top_n: int = 5) -> List[Dict[str, Any]]:
    """ADMISSIBLE candidates only — the composer is not an independent
    invention generator (P0-2 allowlist). Sources, in order:

    1. Ranked survivors (post-gate records): disposition == SURVIVED
       AND the row's OWN recorded verdict on the allowlist (a
       synthesized "PASS" is never attached to an unrecorded
       result). The authority-backed path; used on package runs.
    2. The one attack-adjudicated candidate on the lean path: the
       raw mechanism candidate with its OWN recorded verdict and a
       record-bound attack (the envelope's attack record must be
       the record for THIS candidate).

    NO fallback to raw/unfiltered mechanism records without a
    recorded attack verdict. If nothing is admissible the caller
    must emit the typed NO_ADMISSIBLE state, never a composed
    recommendation."""
    return _admission_analysis(env_dict, top_n=top_n)[0]


def admission_reasons_from_state(env_dict: Dict[str, Any],
                                 top_n: int = 5) -> List[Dict[str, Any]]:
    """P0-2: the typed reasons NO candidate is admissible (one entry
    per recorded verdict that failed the allowlist — recorded in the
    NO_ADMISSIBLE_CANDIDATES state; the unknown is typed, not
    buried; Art. XXV)."""
    return _admission_analysis(env_dict, top_n=top_n)[1]


def compose_if_admissible(env_dict: Dict[str, Any],
                         problem: Dict[str, Any],
                         packet: Optional[List[Dict[str, Any]]],
                         verification: Optional[Dict[str, Any]],
                         question_type: str,
                         llm_generate=None,
                         top_n: int = 5,
                         max_tokens: int = 1000,
                         ) -> Dict[str, Any]:
    """P0-2 engine gate — ONE entry point for admission + composition.

    Admission runs FIRST. No admissible candidate: the typed
    NO_ADMISSIBLE_CANDIDATES record with its typed reasons and ZERO
    composer LLM calls (never an invented recommendation, Art.
    XVIII/XXV/LXI). No frozen packet with admissible candidates:
    the typed SKIPPED_NO_PACKET refusal, zero LLM calls.
    Otherwise: compose_answer over the ADMITTED candidates only."""
    cands = candidates_from_state(env_dict, top_n=top_n)
    rec: Dict[str, Any] = {"composer_version": ANSWER_COMPOSER_VERSION,
                           "n_llm_calls": 0,
                           "question_type": question_type,
                           "started_at": _utc_now()}
    if not cands:
        rec.update({
            "state": "NO_ADMISSIBLE_CANDIDATES",
            "why": ("no candidate survived the evidence / attack gates "
                    "(recorded verdict is a kill, an evaluator / "
                    "evaluation failure, an unadjudicated state, or a "
                    "record not bound to this candidate); refusing to "
                    "compose an endorsed recommendation from "
                    "unadjudicated state"),
            "non_admissible_reasons":
                admission_reasons_from_state(env_dict, top_n=top_n),
            "answer": None,
            "finished_at": _utc_now()})
        return rec
    if not packet:
        rec.update({
            "state": "SKIPPED_NO_PACKET",
            "why": ("no frozen evidence packet — composition without "
                    "epistemic grounds is not permitted"),
            "answer": None,
            "finished_at": _utc_now()})
        return rec
    out = compose_answer(problem, packet=packet, candidates=cands,
                        verification=verification,
                        question_type=question_type,
                        llm_generate=llm_generate,
                        max_tokens=max_tokens)
    out["admitted_candidates"] = [
        {"candidate_id": str(c.get("candidate_id") or ""),
         "attack_verdict": c.get("attack_verdict"),
         "hypothesis": bool(c.get("hypothesis_unverified"))}
        for c in cands]
    return out
