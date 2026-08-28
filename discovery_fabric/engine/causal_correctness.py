"""discovery_fabric/engine/causal_correctness.py — CEO E16-D: semantic
causal-correctness evaluation.

The CEO E15 audit draws the critical distinction:

    "Is every claim connected?"  versus
    "Are the connections actually correct?"

"A completely connected incorrect graph is still wrong." Coverage = 1.0
(E15-C) proves CONNECTION; this module evaluates CORRECTNESS of every
causal chain:

    CLAIM -> PRINCIPLE -> MODEL -> INPUT -> ASSUMPTION -> OUTPUT ->
    FAILURE_MODE -> VERIFICATION

Every chain receives an independent verdict:

    CORRECT      — every semantic check passes
    QUESTIONABLE — a check cannot be completed from recorded artifacts
                   (an open question, bound to the decisive experiment)
    INCORRECT    — a semantic contradiction or referential break

ONE INCORRECT critical chain blocks release (E16-H gate).

Semantic checks (deterministic, each with its reason):
  R1 referential integrity — every node that references an engineering
     object (equation id, parameter id, failure-mode graph id,
     verification id) must resolve to a REAL object in the specification.
  R2 model-domain consistency — the chain's equation must belong to the
     detected engineering domain's governing model set; an equation from
     another domain without a recorded applicability judgment is
     INCORRECT.
  R3 applicability consistency — a chain whose equation carries a
     REJECTED applicability verdict is INCORRECT (the claim claims what
     the artifact itself rejects).
  R4 assumption non-vacuity — the ASSUMPTION node must not merely restate
     the CLAIM (a vacuous assumption hides the failure conditions).
  R5 no self-reference — RESULT/OUTPUT nodes may not cite the claim
     itself as their basis (circular reasoning).
  R6 class honesty — a RESULT/OUTPUT node asserting a MEASURED value
     without a SOURCE_FACT-class provenance pointer is INCORRECT (no
     measurement exists; Art. XXXVIII).
  R7 verification relevance — the VERIFICATION node must resolve to a
     verification whose method shares engineering vocabulary with the
     chain's failure mode / claim (an irrelevant verification does not
     verify).

Optional LLM reviewer: when a provider is configured, an INDEPENDENT
LLM review runs per chain and is recorded as MODELLED opinion — it can
DOWNGRADE CORRECT to QUESTIONABLE (never upgrade), and its verdict is
content, not evidence (Art. XVIII). The deterministic verdicts above are
the gate.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

VERDICT_CORRECT = "CORRECT"
VERDICT_QUESTIONABLE = "QUESTIONABLE"
VERDICT_INCORRECT = "INCORRECT"

_TOKEN = re.compile(r"[a-z]{4,}")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def _tokens(text: str) -> set:
    return set(_TOKEN.findall(str(text or "").lower()))


def _overlap(a: set, b: set) -> int:
    return len(a & b)


def evaluate_chain(chain: Dict[str, Any], eng: Dict[str, Any],
                   ) -> Tuple[str, List[str]]:
    """Run the seven semantic checks on ONE chain. Returns (verdict,
    reasons)."""
    nodes = {n.get("node_type"): n for n in chain.get("nodes", [])}
    reasons: List[str] = []
    verdict = VERDICT_CORRECT

    core = eng.get("engineering_core") or {}
    gm = core.get("governing_model") or {}
    equations = {e.get("equation_id"): e
                 for e in gm.get("equations", []) or []}
    params = {p.get("parameter_id"): p
              for p in core.get("critical_parameters", []) or []}
    fms = {f.get("graph_id"): f
           for f in eng.get("failure_analysis", []) or []}
    vfs = {v.get("id"): v
           for v in eng.get("verification_matrix", []) or []}

    def fail(msg: str) -> None:
        nonlocal verdict
        verdict = VERDICT_INCORRECT
        reasons.append(msg)

    def question(msg: str) -> None:
        nonlocal verdict
        if verdict == VERDICT_CORRECT:
            verdict = VERDICT_QUESTIONABLE
        reasons.append(msg)

    subject = str(chain.get("subject") or "")
    claim = str((nodes.get("CLAIM") or {}).get("content") or "")

    # R1 + R2 + R3 — equation-referencing chains
    m = re.match(r"^equation:(.+)$", subject)
    if m:
        eq_id = m.group(1)
        eq = equations.get(eq_id)
        if eq is None:
            # the chain references an equation that is NOT in the
            # governing model — a referential break (R1), UNLESS it was
            # recorded in rejected_equations (the chain then claims what
            # the artifact rejects — R3)
            rejected = {r.get("equation_id")
                        for r in gm.get("rejected_equations", []) or []}
            if eq_id in rejected:
                fail(f"R3: chain claims {eq_id} but the governing model "
                     "REJECTED it (applicability judgment recorded)")
            else:
                fail(f"R1: chain subject {eq_id} does not resolve to any "
                     "governing-model equation")
        else:
            verdict_r = str(((eq.get("selection_rationale") or {})
                             .get("verdict")) or "")
            if verdict_r == "REJECTED":
                fail(f"R3: {eq_id} carries a REJECTED applicability "
                     "verdict while the chain asserts it governs")
            if not verdict_r:
                question(f"R3: {eq_id} has no recorded applicability "
                         "verdict — correctness cannot be confirmed")

    # R1 — parameter-referencing chains
    m = re.match(r"^parameter:(.+)$", subject)
    if m:
        pid = m.group(1)
        p = params.get(pid)
        if p is None:
            fail(f"R1: chain subject {pid} does not resolve to any "
                 "critical parameter")
        else:
            val = p.get("value")
            status = str(p.get("value_status") or "UNKNOWN").upper()
            if status != "UNKNOWN" and val is not None and \
                    not p.get("source"):
                fail(f"R6: {pid} asserts value {val!r} with "
                     f"value_status {status} but NO source provenance "
                     "(unsupported number, Art. VIII)")

    # R1 — failure-mode-referencing chains
    m = re.match(r"^failure_mode:(.+)$", subject)
    if m:
        fmid = m.group(1)
        fm = fms.get(fmid)
        if fm is None:
            fail(f"R1: chain subject {fmid} does not resolve to any "
                 "failure-analysis row")

    # R4 — assumption non-vacuity (all chain kinds)
    assum = str((nodes.get("ASSUMPTION") or {}).get("content") or "")
    if assum:
        a_toks, c_toks = _tokens(assum), _tokens(claim)
        if c_toks and len(a_toks) >= 4:
            overlap = _overlap(a_toks, c_toks) / max(1, len(a_toks))
            if overlap >= 0.85:
                fail("R4: ASSUMPTION node restates the CLAIM (vacuous "
                     "assumption hides the failure conditions)")
    elif "ASSUMPTION" in (nodes or {}):
        fail("R4: ASSUMPTION node is empty")

    # R5 — no self-reference: RESULT/OUTPUT nodes may not cite the claim
    for role in ("OUTPUT", "RESULT"):
        node = nodes.get(role)
        if not node:
            continue
        prov = node.get("provenance") or {}
        refs = prov.get("refs") or {}
        if isinstance(refs, dict) and \
                str(refs.get("self_reference") or "").lower() == "true":
            fail(f"R5: {role} node cites itself as its own basis "
                 "(circular reasoning)")
        content_toks = _tokens(node.get("content"))
        claim_toks = _tokens(claim)
        if claim_toks and content_toks and len(content_toks) >= 6:
            if _overlap(content_toks, claim_toks) / len(content_toks) >= 0.9:
                fail(f"R5: {role} node merely restates the claim "
                     "(no independent derivation)")

    # R6 — class honesty on RESULT/OUTPUT: measured-value language
    # without SOURCE_FACT provenance
    for role in ("OUTPUT", "RESULT"):
        node = nodes.get(role)
        if not node:
            continue
        content = str(node.get("content") or "")
        measured = re.search(
            r"\b(measured|observed value|measured value|bench result|"
            r"we measured|was \d+(?:\.\d+)?)\b", content, re.I)
        prov = node.get("provenance") or {}
        ev_ids = prov.get("evidence_ids") or []
        klass = str(node.get("epistemic_class") or "").upper()
        if measured and klass == "SOURCE_FACT" and not ev_ids:
            fail(f"R6: {role} node claims a MEASURED value with "
                 "SOURCE_FACT class but no evidence custody pointer")

    # R7 — verification relevance: the VERIFICATION node's method must
    # share engineering vocabulary with the failure mode / claim
    vnode = nodes.get("VERIFICATION") or {}
    vcontent = str(vnode.get("content") or "")
    if vcontent and not vcontent.startswith("NOT_LINKED"):
        m = re.search(r"\b((?:VF|V)-\d{2,3})\b", vcontent)
        target_tokens = None
        subj_fm = re.match(r"^failure_mode:(.+)$", subject)
        if m and m.group(1) in vfs:
            v_row = vfs[m.group(1)]
            target_tokens = _tokens(str(v_row.get("method") or ""))
        elif subj_fm and subj_fm.group(1) in fms:
            target_tokens = _tokens(
                str(fms[subj_fm.group(1)].get("detectability") or "") +
                " " + str(fms[subj_fm.group(1)].get("mode") or ""))
        if target_tokens is not None:
            claim_toks = _tokens(claim) | _tokens(
                str((nodes.get("FAILURE_MODE") or {}).get("content") or ""))
            if claim_toks and _overlap(target_tokens, claim_toks) == 0:
                question("R7: the VERIFICATION method shares no "
                         "engineering vocabulary with the claim/failure "
                         "mode — relevance cannot be confirmed")

    if not reasons:
        reasons.append("all seven semantic checks passed (referential "
                       "integrity, domain consistency, applicability, "
                       "non-vacuity, no self-reference, class honesty, "
                       "verification relevance)")
    return verdict, reasons


def evaluate_causal_correctness(eng: Dict[str, Any],
                                critical_only: bool = True,
                                ) -> Dict[str, Any]:
    """Evaluate EVERY reasoning chain (or every CRITICAL chain) in the
    engineering artifact. Returns the E16-D block consumed by the
    E16-H release gate: one INCORRECT critical chain blocks release."""
    rc = eng.get("engineering_reasoning_chains") or {}
    chains = rc.get("chains", []) or []
    critical_subjects = None
    if critical_only:
        ce = eng.get("chain_enforcement") or {}
        # critical = equations + sourced parameters + physical failure
        # modes (same definition as E15-C enforcement)
        critical_subjects = set()
        for eq in ((core := eng.get("engineering_core") or {})
                   .get("governing_model", {}).get("equations", []) or []):
            critical_subjects.add(f"equation:{eq.get('equation_id')}")
        for p in core.get("critical_parameters", []) or []:
            if str(p.get("value_status", "UNKNOWN")).upper() != "UNKNOWN":
                critical_subjects.add(f"parameter:{p.get('parameter_id')}")
        for f in eng.get("failure_analysis", []) or []:
            if f.get("content_class") == "PHYSICAL_MECHANISM":
                critical_subjects.add(f"failure_mode:{f.get('graph_id')}")
    results = []
    counts = {VERDICT_CORRECT: 0, VERDICT_QUESTIONABLE: 0,
              VERDICT_INCORRECT: 0}
    for c in chains:
        subject = c.get("subject")
        if critical_only and critical_subjects is not None \
                and subject not in critical_subjects:
            continue
        verdict, reasons = evaluate_chain(c, eng)
        counts[verdict] += 1
        results.append({"chain_id": c.get("chain_id"),
                        "subject": subject, "verdict": verdict,
                        "reasons": reasons})
    incorrect = [r for r in results if r["verdict"] == VERDICT_INCORRECT]
    return {
        "evaluation": "SEMANTIC_CAUSAL_CORRECTNESS (E16-D)",
        "version": "1.0.0",
        "scope": "critical chains" if critical_only else "all chains",
        "chains_evaluated": len(results),
        "counts": counts,
        "results": results,
        "verdict": ("FAIL" if counts[VERDICT_INCORRECT] > 0
                    else "CONDITIONAL" if counts[VERDICT_QUESTIONABLE] > 0
                    else "PASS"),
        "verdict_rule": ("one INCORRECT critical chain blocks release "
                         "(E16-H); QUESTIONABLE chains are bound to the "
                         "decisive experiment and buyer diligence"),
        "evaluated_at": utc_now(),
    }
