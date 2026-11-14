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

Owner round 2026-11-12, item 1 (COMPOSE -> VALIDATE -> REPAIR):
a truncated composition — the API's typed finish-reason report says
the output was cut at the token budget ("length"), or, when no
finish reason was reported, the plainly cut sentence — is NEVER
shipped: ONE retry runs at a larger budget (the recorded multiplier
constant, a retry budget and never a verdict gate), and a
still-truncated retry is the typed COMPOSE_TRUNCATED no-answer
(Art. LXI: an infrastructure state, never a scientific refusal;
Art. XXV: the typed detail stays in the record's truncation
metadata; the plain-language caveat rides in `caveats`).

Owner round 2026-11-12, item 2 (deterministic tech-sanity A/B
candidate, NOT a new gate): when the flag is on (explicit
`tech_sanity=` arm selection, else the ENGINE_TECH_SANITY env
flag), the composer runs three PURE deterministic checks on the
complete composition — a resistance/impedance quantity stated in
the voltage unit or a voltage quantity in the resistance unit
(V-vs-ohm dimensional consistency), an efficiency/yield above 100
percent (second law; the 100 percent bound is physical law, not an
invented threshold), and a declared sampling rate below the Nyquist
bound (2x) of a band top stated by the answer or the user's stated
sensor variables. Findings NEVER change the record's state: they
ride the typed `tech_sanity` metadata and plain-language caveats,
and — only when the deterministic contract already scheduled the
ONE repair call — their plain lines join that same repair prompt
(call budget unchanged). The flag defaults OFF: the candidate stays
off on the measured path until the owner's ablation + auditor
judgement places it (Art. LIX).

The composer grants no epistemic authority (Art. XVIII): it WRITES the
engineer-facing answer; every claim's provenance comes from the packet
and the candidate records, and unverified numbers stay labeled.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# 1.1.0 (owner round 2026-11-12, item 1): the typed truncation
# signal (the transport's normalized finish-reason report), the one
# larger-budget truncation retry (purpose answer_composer_truncation),
# the COMPOSE_TRUNCATED no-answer state, and the plain-language
# caveats (typed states stay in the metadata only).
# 1.2.0 (owner round 2026-11-12, item 2): the deterministic
# tech-sanity candidate (unit consistency V-vs-ohm, implausible
# efficiency/rates, band/sampling Nyquist feasibility vs the stated
# sensor) as a FLAG-CONTROLLED A/B ablation candidate inside the
# composer — never a gate: it changes no state, adds no call; the
# ablation arm decides on/off.
# 1.3.0 (owner AUDIT round 2026-11-12, directives 1/2/4/6):
#   (a) CLEAN OUTPUT — the composer system prompt forbids internal
#       state names and pipeline-history narration; the deterministic
#       contract now rejects them (answer_contract.
#       INTERNAL_NARRATION_TOKENS), so a narrating composition is
#       repaired, never shipped;
#   (b) COMPOSE -> VALIDATE -> REPAIR UNTIL VALID — the one repair
#       retry became a bounded loop (max MAX_REPAIR_ROUNDS) that ends
#       early on validity; the harness never prepends a
#       contract-invalid banner and never ships a final invalid
#       composition (the typed no-answer state replaces it);
#   (c) the CONSTRAINT-COMPLIANCE AUDIT (constraint_audit.py) runs on
#       every pass; its typed violations join the repair prompt (same
#       call, no added calls);
#   (d) dict-valued clarification_answer records (sofc's 0.15 glass
#       phase fraction) render into the constraint context instead of
#       being dropped;
#   (e) HYPOTHESIS DELIVERY per the approved attack semantics: when
#       every recorded kill's typed cause is KILL_CAUSE_NOT_IN_RECORD
#       (the evidence coverage of THIS retrieval, not a physical
#       impossibility), the record-bound raw candidate is admissible
#       as a clearly flagged UNVERIFIED hypothesis — one plain-language
#       line, never a typed no-answer, never internal jargon.
ANSWER_COMPOSER_VERSION = "answer_composer/1.5.0"

#: bounded repair loop (compose -> validate -> repair until valid or
#: cap). Calls per composition: 1 compose + <=1 truncation retry
#: + <= MAX_REPAIR_ROUNDS repairs. The cap keeps the composer inside
#: the per-problem call governor (<=12 healthy calls).
MAX_REPAIR_ROUNDS = 2

#: the ONE plain-language caveat the composer may add for a
#: hypothesis-class delivery (directive 1: one plain-language caveat
#: line at most; typed detail stays in metadata)
HYPOTHESIS_CAVEAT_LINE = (
    "Note: this proposal is delivered as an unverified engineering "
    "hypothesis — the retrieved record does not directly support it, "
    "so treat the stated falsification test as a precondition, not a "
    "validated recommendation.")

_COMPOSER_SYSTEM = (
    "You write the final engineer-facing answer for an engineering "
    "discovery request. You receive the problem's constraints, the "
    "user's stated variables, candidate intervention proposals with "
    "their support status, the supporting records, and a support "
    "summary. You write ONE complete, specific, testable engineering "
    "answer. Rules: (1) every number you state either comes from the "
    "supporting records or the user's variables, or is labeled "
    "ASSUMPTION on the same line, or is given as a defined calibration "
    "rule (e.g. baseline + 3 sigma from 14 days of healthy data); "
    "(2) CLEAN OUTPUT: the reader sees only engineering content — NO "
    "internal state names, NO process narration. Never write phrases "
    "like \"CONTRACT-INVALID\", \"NO SURVIVING CANDIDATES\", \"ALL "
    "KILLED\", \"the previous attempt\", \"the pipeline\", \"the "
    "gauntlet\", \"verification verdict\", \"packet\", \"candidate "
    "envelope\", \"AUTOMATED_INVENTION_CANDIDATE\", or candidate ids "
    "like \"[cand:A2]\". If the supporting evidence is not strong "
    "enough to endorse the proposal confidently, present the best "
    "engineering proposal and state plainly in ONE sentence that it is "
    "UNVERIFIED and needs the stated test — nothing about internal "
    "processing; (3) respect the user's stated variables exactly (a "
    "constraint the user fixed must stay fixed; the proposal's "
    "measurements, inputs and dimensions must be inside the allowed "
    "set, and the proposal must CHANGE something relative to the given "
    "device — never restate the given design or the constraints as the "
    "answer); (4) name the falsification test concretely; (5) every "
    "EVIDENCE-BACKED label MUST be followed on the SAME line by the "
    "bracketed record id that supports it, e.g. \"EVIDENCE-BACKED "
    "[record-id]\" — a label with no bracketed id fails the "
    "deterministic contract; (6) English only, no markdown headings, "
    "plain text; (7) END your response with the required "
    "CONSTRAINT-CHECK block (the specification below) — it is "
    "machine-stripped before delivery and is your own audit of the "
    "answer you just wrote: audit honestly, quote exactly.")

_COMPOSER_PROMPT = """Write the final engineering answer for this problem.

PROBLEM:
- Device: {device}
- Failure: {failure}
- Failure mode: {failure_mode}

USER'S STATED CONSTRAINTS AND VARIABLES (must be respected exactly;
numbered for the audit block):
{variables_block}

NUMBERED USER CONSTRAINTS (audit units — one verdict line each):
{numbered_constraints}

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
{shape_block}

{constraint_check_spec}"""

_REPAIR_PROMPT = """Your previous answer violated the deterministic
answer-shape contract or the constraint audit:

VIOLATIONS:
{violations}

PREVIOUS ANSWER (with its constraint-audit block):
{previous}

PROBLEM (for context): {device} — {failure}
USER'S STATED CONSTRAINTS AND VARIABLES:
{variables_block}

NUMBERED USER CONSTRAINTS (audit units — one verdict line each):
{numbered_constraints}

Rewrite the FULL answer fixing every violation. Same rules as before:
numbers come from packet/candidates or carry ASSUMPTION or a defined
calibration rule; respect the user's variables; name the falsification
test. Contract{shape_hint}:
{shape_block}

{constraint_check_spec}"""


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
    # OWNER AUDIT ROUND 2026-11-13, DIRECTIVE 1: ONE PRIMARY CANDIDATE.
    # The FIRST candidate is THE proposal the composer writes; every
    # other candidate is a NAMED ALTERNATIVE for context ONLY — its
    # design must never be mixed into the answer (the measured new07
    # defect: indicator lead design + nanofluid claims from a different
    # candidate in one answer). Alternatives render as one-line names
    # without their full design detail, so the composer cannot blend
    # their mechanisms into the proposal.
    def _one(c: Dict[str, Any]) -> str:
        verdict = str(c.get("attack_verdict") or c.get("verdict")
                      or c.get("state") or "NO_VERDICT")
        if c.get("hypothesis_unverified") or _is_hypothesis_verdict(verdict):
            status = ("status: UNVERIFIED — the supporting record does "
                      "not directly support this proposal; the answer "
                      "must say plainly that it is unverified and needs "
                      "the stated test")
        else:
            status = ("status: supported — it survived the adversarial "
                      "check")
        mech = str(c.get("mechanism") or "")[:280]
        interv = str(c.get("intervention") or "")[:280]
        eff = str(c.get("expected_effect") or c.get("predicted_effect")
                  or "")[:200]
        return (f"{status}\n"
                f"   mechanism: {mech}\n"
                f"   intervention: {interv}\n"
                f"   expected effect: {eff}")

    def _alt_line(c: Dict[str, Any]) -> str:
        mech = str(c.get("mechanism") or "")[:90]
        return f"   (alternative) {mech}"

    lines = ["THE PROPOSAL TO ANSWER WITH (the ONE primary candidate "
             "— the mechanism, the measured quantity and the "
             "falsification test must ALL describe THIS ONE design):",
             _one(cands[0])]
    alts = [c for c in cands[1:5] if isinstance(c, dict)]
    if alts:
        lines.append("NAMED ALTERNATIVES (for context only — do NOT "
                     "mix their designs into the proposal; at most, "
                     "mention one by name in a single clause as an "
                     "unexplored option):")
        lines.extend(_alt_line(c) for c in alts)
    return "\n".join(lines)


def _variables_block(problem: Dict[str, Any]) -> str:
    rows = []
    if problem.get("constraint"):
        rows.append(f"- CONSTRAINT: {problem['constraint']}")
    if problem.get("clarification_text"):
        rows.append(f"- USER-STATED CLARIFICATION: "
                    f"{problem['clarification_text']}")
    # 1.3.0: dict-valued clarification records render too (the stated
    # variable must be usable in the design — directive 4)
    _ca = problem.get("clarification_answer")
    if isinstance(_ca, dict):
        for _k, _v in _ca.items():
            if _k == "note":
                rows.append(f"- USER-STATED CLARIFICATION NOTE: {_v}")
            else:
                rows.append(f"- USER-STATED VARIABLE: {_k} = {_v}")
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


# ------------------------------------------------------------------
# R6 owner round 2026-11-12 item 1 — typed truncation detection.
# The transport's normalized finish-reason report ("length" = cut
# at the token budget) is the truncation signal when present; when
# the API reported no finish reason ("unknown"/absent) the plainly
# cut sentence is the SECONDARY signal — a binary exact-text check
# (the last character is not a sentence terminal), not a threshold
# (Art. XXVII). A typed non-length finish reason ("stop" or a raw
# newer value) is the API's own report that the completion is what
# the model produced: a missing period is a style issue, never a
# truncation claim (Art. XXV).
_TRUNCATION_FINISH = "length"
#: the larger budget for the ONE truncation retry — a recorded retry
#: budget, not a verdict gate (the multiplier rides in every
#: truncation record: truncation.retry_max_tokens)
_TRUNCATION_BUDGET_MULTIPLIER = 2
_SENTENCE_TERMINALS = frozenset(".!?;:\"'\u2019\u201d)]}>")


def _recorded_finish_reason(res: Dict[str, Any]) -> Optional[str]:
    """The transport's normalized finish-reason report for one result
    meta dict (None when the record carries it absent — legacy or
    failure shapes)."""
    fr = res.get("finish_reason")
    return str(fr) if fr else None


def _is_answer_truncated(text: str, res: Dict[str, Any]) -> bool:
    """Typed truncation check for one composed text + its result
    meta (see the block above): "length" is the API's own report of
    a cut; without a typed signal the secondary cut-sentence check
    applies (binary, no threshold)."""
    fr = _recorded_finish_reason(res)
    if fr == _TRUNCATION_FINISH:
        return True
    if fr is not None and fr != "unknown":
        return False
    t = (text or "").rstrip()
    if not t:
        return True
    return t[-1] not in _SENTENCE_TERMINALS


# ------------------------------------------------------------------
# R6 owner round 2026-11-12 item 2 — deterministic tech-sanity
# checks, the A/B ablation candidate (see the module docstring):
# PURE text analysis, no LLM, no verdict gate, no invented
# thresholds (Art. XXVII) — every verdict below is a binary
# physical / dimensional law:
#   - unit_consistency: a resistance/impedance quantity stated in
#     the voltage unit, or a voltage quantity in the resistance
#     unit (V vs ohm — different dimensions);
#   - efficiency_plausibility: an efficiency / yield percentage
#     above 100 (second law; 100 percent is a physical bound, not
#     a tunable threshold);
#   - nyquist_feasibility: a declared sampling rate below 2x the
#     band top stated by the answer or the user's stated sensor
#     variables (the sampling theorem).
# The scan windows are DOCUMENTED regex structure (how far a
# quantity-word and its number may sit apart in the text); they are
# not verdict values.
_TECH_SANITY_FLAG = "ENGINE_TECH_SANITY"
_UNIT_SCAN_WINDOW = 40
_PCT_SCAN_WINDOW = 60
_FREQ_SCAN_WINDOW = 30
_HZ_SCALE = {"hz": 1.0, "khz": 1e3, "mhz": 1e6}

_TECH_RESISTANCE_IN_VOLTS = re.compile(
    r"(?:resistan|resistive|impedan)\w*"
    r"(?:[^.!?]{0,%d}\b\d+(?:\.\d+)?)\s*V\b"
    % _UNIT_SCAN_WINDOW, re.IGNORECASE)
_TECH_VOLTAGE_IN_OHMS = re.compile(
    r"(?:volt\w*|potential difference)\s*"
    r"(?:[^.!?]{0,%d}?\b\d+(?:\.\d+)?)\s*(?:\u03a9|ohms?)\b"
    % _UNIT_SCAN_WINDOW, re.IGNORECASE)
_TECH_EFFICIENCY_PCT = re.compile(
    r"(?:efficien|yield)\w*[^.!?]{0," + str(_PCT_SCAN_WINDOW) +
    r"}?(\d+(?:\.\d+)?)\s*%", re.IGNORECASE)
_TECH_SAMPLE_RATE = re.compile(
    r"(?:sample\s+rate|sampling\s+rate|sample\s+frequency)\w*"
    r"[^.!?]{0,%d}?(\d+(?:\.\d+)?)\s*(Hz|kHz|MHz)\b"
    % _FREQ_SCAN_WINDOW, re.IGNORECASE)
_TECH_RATE_INTEXT = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(Hz|kHz|MHz)\b[^.!?]{0,%d}?"
    r"(?:samples?/s|samples?\s+per\s+second|sampling|sampled)\b"
    % _FREQ_SCAN_WINDOW, re.IGNORECASE)
_TECH_BAND_TOP = re.compile(
    r"(?:band|cutoff|corner|upper)\w*[^.!?]{0,%d}?"
    r"(\d+(?:\.\d+)?)\s*(Hz|kHz|MHz)\b" % _FREQ_SCAN_WINDOW,
    re.IGNORECASE)
_TECH_TOP_INTEXT = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(Hz|kHz|MHz)\b[^.!?]{0,%d}?"
    r"\b(?:band|cutoff|corner|upper)\w*" % _FREQ_SCAN_WINDOW,
    re.IGNORECASE)


def _tech_sanity_enabled(tech_sanity: Optional[bool]) -> bool:
    """The flag authority: an explicit `tech_sanity=` selection
    (the ablation arm) overrides the env flag; the DEFAULT is OFF —
    the candidate stays off on the measured path until the owner's
    ablation + auditor judgement places it (Art. LIX)."""
    if tech_sanity is not None:
        return bool(tech_sanity)
    return os.environ.get(_TECH_SANITY_FLAG, "").strip().lower() \
        in ("1", "true", "on", "yes")


def _tech_sanity_findings(text: str,
                          user_variables: Optional[List[Any]]
                          ) -> List[Dict[str, Any]]:
    """The pure deterministic tech-sanity scan (see the block
    above). The Nyquist check also reads the user's STATED
    variables (the stated sensor authority); the other two scan
    the composed text alone. Never raises: unparseable or absent
    declarations yield no finding — a scan miss is NOT a pass
    certification (Art. XXV: unknown stays unknown)."""
    findings: List[Dict[str, Any]] = []
    composed = str(text or "")
    stated = [str(v) for v in (user_variables or [])]
    for m in _TECH_RESISTANCE_IN_VOLTS.finditer(composed):
        findings.append({
            "check": "unit_consistency",
            "typed": "RESISTANCE_QUANTITY_IN_VOLT_UNIT",
            "span": m.group(0)[:120],
            "plain": ("A resistance or impedance quantity is "
                      "stated with the voltage unit: volts (V) and "
                      "ohms are different units.")})
    for m in _TECH_VOLTAGE_IN_OHMS.finditer(composed):
        findings.append({
            "check": "unit_consistency",
            "typed": "VOLTAGE_QUANTITY_IN_RESISTANCE_UNIT",
            "span": m.group(0)[:120],
            "plain": ("A voltage quantity is stated with the "
                      "resistance unit: ohms and volts are "
                      "different units.")})
    for m in _TECH_EFFICIENCY_PCT.finditer(composed):
        val = float(m.group(1))
        if val > 100.0:
            findings.append({
                "check": "efficiency_plausibility",
                "typed": "EFFICIENCY_ABOVE_100_PERCENT",
                "span": m.group(0)[:120],
                "plain": (f"The stated efficiency/yield "
                          f"({m.group(1)} percent) is above 100 "
                          "percent, which is not physically "
                          "possible.")})
    # ---- Nyquist: every declared rate vs every declared band top
    # (stated variables first, then the composed text; the
    # feasibility verdict is the strictest pair — the LOWEST
    # declared rate against the HIGHEST declared band top)
    rates: List[float] = []
    tops: List[float] = []
    for src in stated + [composed]:
        for m in _TECH_SAMPLE_RATE.finditer(src):
            rates.append(float(m.group(1)) *
                         _HZ_SCALE[m.group(2).lower()])
        for m in _TECH_RATE_INTEXT.finditer(src):
            rates.append(float(m.group(1)) *
                         _HZ_SCALE[m.group(2).lower()])
        for m in _TECH_BAND_TOP.finditer(src):
            tops.append(float(m.group(1)) *
                        _HZ_SCALE[m.group(2).lower()])
        for m in _TECH_TOP_INTEXT.finditer(src):
            tops.append(float(m.group(1)) *
                        _HZ_SCALE[m.group(2).lower()])
    if rates and tops:
        r_min, t_max = min(rates), max(tops)
        if r_min < 2.0 * t_max:
            findings.append({
                "check": "nyquist_feasibility",
                "typed": "SAMPLING_BELOW_NYQUIST_OF_STATED_BAND",
                "span": (f"rate={r_min:g} Hz band_top={t_max:g} Hz"),
                "plain": (f"The stated sampling rate ({r_min:g} "
                          "Hz) is below the Nyquist bound — at "
                          "least 2x the stated band top "
                          f"({t_max:g} Hz) — so the stated sensor "
                          "setup cannot capture that band.")})
    return findings


#: the composition generation budget (ENGINEERING class, Art. XXVII —
#: a generation budget, never a verdict gate; measured live 2026-11-12:
#: glm-4-plus cut at 1000 tokens AND at the 2000-token truncation retry
#: on the predictor answer shape; the call COUNT is unchanged).
COMPOSE_MAX_TOKENS = 3000


def compose_answer(problem: Dict[str, Any],
                   packet: Optional[List[Dict[str, Any]]],
                   candidates: List[Dict[str, Any]],
                   verification: Optional[Dict[str, Any]],
                   question_type: str,
                   llm_generate=None,
                   max_tokens: Optional[int] = None,
                   tech_sanity: Optional[bool] = None,
                   ) -> Dict[str, Any]:
    if max_tokens is None:
        max_tokens = COMPOSE_MAX_TOKENS
    """ONE LLM call writes the full engineer-facing answer; when the
    transport's typed finish-reason report says the draft was
    truncated at the token budget — or, when no finish reason was
    recorded, the plainly cut sentence does — ONE retry runs at a
    LARGER budget (owner round 2026-11-12 item 1; the multiplier and
    the retried budget ride in the record's truncation metadata). The
    deterministic contract is applied to the composed text; ONE
    repair retry on violation (a truncated repair is never adopted).
    A truncated answer — a still-truncated retry — is NEVER shipped:
    the typed COMPOSE_TRUNCATED no-answer replaces it (Art. LXI: an
    infrastructure state, never a scientific refusal). Item 2: when
    the tech-sanity flag is on, the three deterministic
    physical-law checks run on the complete composition (findings
    ride the typed `tech_sanity` record + plain caveats; they join
    the ONE scheduled repair prompt when one is scheduled — no
    state change, no added call). Returns a record (never raises to
    the caller):
    {answer, composer: {...}, contract: {...}, state, truncation,
    tech_sanity, caveats}.

    `llm_generate` is injectable for tests (the engine's
    mechanism_space.llm_generate by default — ONE transport path,
    Art. X). `tech_sanity` is the ablation arm's explicit on/off
    selection; None defers to the ENGINE_TECH_SANITY env flag
    (default off)."""
    from .answer_contract import validate_answer, ANSWER_SHAPE_BLOCK
    from .constraint_audit import (
        CONSTRAINT_CHECK_BLOCK_SPEC, strip_constraint_check,
        parse_constraint_check, merge_constraint_check,
        numbered_constraints_block)
    if llm_generate is None:
        from .mechanism_space import llm_generate
    # item 2: the flag-controlled deterministic tech-sanity
    # candidate (explicit arm selection > env flag > off)
    _ts_on = _tech_sanity_enabled(tech_sanity)
    # P0-5 (owner directive 2026-11-11, item 5): the user's clarified
    # text is a citable provenance span for the contract — it travels
    # into validate_answer on BOTH compose paths (compose + repair),
    # as its own entry (a number in the clarification is not support
    # for a quantity it never names, and vice versa).
    # 1.3.0: a dict-valued clarification_answer (sofc's
    # {"intergranular glass phase fraction": 0.15, "note": ...})
    # renders into the context instead of being silently dropped
    # (directive 4: the stated variable must be usable in the design).
    _clar_text = str(problem.get("clarification_text") or "").strip()
    _clar_ans = problem.get("clarification_answer")
    if not _clar_text and isinstance(_clar_ans, str):
        _clar_text = _clar_ans.strip()
    elif isinstance(_clar_ans, dict):
        _dict_lines = []
        for _k, _v in _clar_ans.items():
            if _k == "note" and isinstance(_v, str):
                _dict_lines.append(f"note: {_v}")
            else:
                _dict_lines.append(f"{_k}: {_v}")
        _clar_text = "; ".join(_dict_lines)
    _clarification = _clar_text or None
    _ncons = numbered_constraints_block(problem)
    shape = ANSWER_SHAPE_BLOCK.get(question_type, "")
    shape_hint = "" if shape else " (none — unknown question type)"
    prompt = _COMPOSER_PROMPT.format(
        device=problem.get("device", ""),
        failure=problem.get("failure", ""),
        failure_mode=problem.get("failure_mode", ""),
        variables_block=_variables_block(problem),
        numbered_constraints=_ncons,
        candidates_block=_candidates_block(candidates or []),
        packet_block=_packet_block(packet),
        verification_block=_verification_block(verification),
        shape_hint=shape_hint, shape_block=shape,
        constraint_check_spec=CONSTRAINT_CHECK_BLOCK_SPEC)
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
    # DIRECTIVE 1 (R6 auditor round 2026-11-12): the structured
    # constraint check RIDES THIS CALL — the block is machine-stripped
    # from the delivered text and parsed into typed verdicts (no extra
    # call, Art. X: one check shape on every compose path).
    answer, _ck_block = strip_constraint_check(answer)
    rec["output_sha256"] = res.get("output_hash")
    # ---- typed truncation detection + ONE larger-budget retry
    # (owner round 2026-11-12 item 1): the typed finish-reason
    # report is the signal when present; without one, the cut
    # sentence. The same prompt is re-sent at the larger budget —
    # prompt_sha256 above stays the (identical) prompt's hash.
    trunc: Dict[str, Any] = {
        "first_call_finish_reason": _recorded_finish_reason(res),
        "first_call_truncated": _is_answer_truncated(answer, res),
        "n_truncation_retries": 0,
    }
    rec["truncation"] = trunc
    if trunc["first_call_truncated"]:
        _budget2 = _TRUNCATION_BUDGET_MULTIPLIER * max_tokens
        res2 = llm_generate(prompt, system=_COMPOSER_SYSTEM,
                            max_tokens=_budget2,
                            purpose="answer_composer_truncation")
        rec["n_llm_calls"] += 1
        trunc.update({
            "n_truncation_retries": 1,
            "retry_max_tokens": _budget2,
            "retry_purpose": "answer_composer_truncation",
            "retry_finish_reason": _recorded_finish_reason(res2),
            "retry_prompt_sha256": res2.get("prompt_hash"),
            "retry_output_sha256": res2.get("output_hash"),
        })
        if not res2.get("ok") or not (res2.get("content") or "").strip():
            # the truncated first draft is NEVER shipped: a transport
            # failure on the retry is a typed transport state (Art.
            # LXI — infrastructure, never a scientific verdict)
            trunc["retry_failed"] = True
            rec["state"] = "COMPOSE_FAILED_TRANSPORT"
            rec["error"] = ("truncation retry failed: "
                            + str(res2.get("error")
                                  or res2.get("status"))[:300])
            rec["answer"] = None
            rec["caveats"] = [
                ("The first draft was cut off at the model's output "
                 "budget, and the larger-budget recomposition failed "
                 "on the provider transport, so no answer is released "
                 "for this problem.")]
            rec["finished_at"] = _utc_now()
            return rec
        answer = res2["content"].strip()
        answer, _ck_block = strip_constraint_check(answer)
        trunc["retry_truncated"] = _is_answer_truncated(answer, res2)
        if trunc["retry_truncated"]:
            # DOWNGRADE, DON'T DISCARD (owner directive 2): a truncated
            # draft delivered at the last complete sentence with ONE
            # plain caveat beats a blank (the typed detail rides the
            # truncation metadata; never a banner, never internal
            # narration). The downgrade pass still runs so the shipped
            # text carries no unsupported certainty.
            from .answer_downgrade import (downgrade_answer,
                                           DOWNGRADE_CAVEAT_LINE,
                                           truncate_at_sentence)
            dg_t = downgrade_answer(answer, [], packet)
            _cut = truncate_at_sentence(dg_t["answer"])
            if _cut.strip():
                rec["state"] = "COMPOSED_TRUNCATED_DELIVERED"
                rec["answer"] = _cut
                rec["downgrade"] = {
                    "applied": True,
                    "n_relabels": dg_t["n_relabels"],
                    "n_citations_dropped": dg_t["n_citations_dropped"],
                    "n_jargon_stripped": dg_t["n_jargon_stripped"],
                    "valid_after_downgrade": False}
                rec["caveats"] = [
                    DOWNGRADE_CAVEAT_LINE,
                    "Note: this answer was shortened at the model's "
                    "output budget and may be incomplete."]
                rec["finished_at"] = _utc_now()
                return rec
            rec["state"] = "COMPOSE_TRUNCATED"
            rec["answer"] = None
            rec["caveats"] = [
                ("The first draft was cut off at the model's output "
                 "budget, and the larger-budget recomposition "
                 f"({_budget2} tokens) was cut off as well, so no "
                 "answer is released for this problem.")]
            rec["finished_at"] = _utc_now()
            return rec
        rec["output_sha256"] = res2.get("output_hash")
        rec["model"] = res2.get("model")
        rec["provider_route"] = res2.get("provider_route") \
            or res2.get("provider")
    # ---- the deterministic contract + the constraint-compliance
    # audit, then the bounded COMPOSE -> VALIDATE -> REPAIR UNTIL
    # VALID loop (directive 1 + 2). Every round feeds back the
    # contract violations AND the constraint-audit violations (and
    # the tech-sanity lines when the flag is on) into the SAME repair
    # call shape; the loop ends early on a valid-and-clean pass and
    # never ships a truncated repair. DIRECTIVE 5 (ablation arms):
    # FABRIC_CONSTRAINT_AUDIT=0 disables the audit leg for the
    # leave-it-out arm (explicit arm selection, default on).
    from .constraint_audit import audit_constraints
    _ca_on = os.environ.get("FABRIC_CONSTRAINT_AUDIT", "1") != "0"
    rec["constraint_audit_arm"] = "on" if _ca_on else "off"
    _uvs = list(problem.get("user_variables") or [])
    # the check parsed from THIS response (compose or truncation retry)
    ck = parse_constraint_check(_ck_block, answer)
    rec["constraint_check_first_pass"] = {
        "state": ck.get("state"), "n_violations": ck.get("n_violations"),
        "verdicts": ck.get("verdicts"),
        "restates_device": ck.get("restates_device"),
        "restates_constraint": ck.get("restates_constraint")}
    contract = validate_answer(answer, question_type,
                               packet=packet or [],
                               user_variables=_uvs,
                               clarification=_clarification)
    caudit = (audit_constraints(problem, answer) if _ca_on
              else {"audit_version": "constraint_audit/1.0.0",
                    "state": "CONSTRAINT_AUDIT_PASS",
                    "violations": [], "n_violations": 0,
                    "allowed_measurements": {"mode": "arm_off"}})
    # the floor stays; the LLM check MERGES into the same typed list
    caudit = merge_constraint_check(caudit, ck) if _ca_on else caudit
    # OWNER AUDIT ROUND 2026-11-13, DIRECTIVE 1: the ONE-design
    # consistency check (deterministic, zero-LLM) rides every pass;
    # its typed violations join the SAME repair call (no added calls)
    from .answer_consistency import consistency_check as _cons_check
    cons = _cons_check(answer, candidates or [], problem)
    rec["consistency_check_first_pass"] = {
        "state": cons.get("state"),
        "n_violations": cons.get("n_violations"),
        "violations": cons.get("violations")}
    rec["contract_first_pass"] = {"valid": contract.get("valid"),
                                  "violations": contract.get("violations")}
    rec["constraint_audit_first_pass"] = {
        "state": caudit.get("state"),
        "n_violations": caudit.get("n_violations"),
        "violations": caudit.get("violations")}
    _repair_round = 0
    while _repair_round < MAX_REPAIR_ROUNDS:
        _contract_bad = contract.get("valid") is not True
        _audit_bad = caudit.get("state") == "CONSTRAINT_VIOLATIONS"
        # R9 P0 (owner round 2026-11-13): CHECK_ABSENT is NOT a pass —
        # a missing falsification-test section must trigger the repair
        # exactly like violations do (the measured defect: only
        # CONSISTENCY_VIOLATIONS was treated as bad, so a missing check
        # terminated the repair loop without the check having passed).
        _cons_bad = cons.get("state") in ("CONSISTENCY_VIOLATIONS",
                                          "CHECK_ABSENT")
        if not (_contract_bad or _audit_bad or _cons_bad):
            break
        _repair_round += 1
        # deterministic feedback: contract violations + constraint
        # violations + consistency violations travel back in (no gate
        # widening, Art. VII)
        _viol_lines = list(contract.get("violations") or [])
        _viol_lines += [
            ("CONSTRAINT VIOLATION [" + v.get("type", "") + "]: "
             + v.get("detail", ""))
            for v in (caudit.get("violations") or [])]
        _viol_lines += [
            ("DESIGN CONSISTENCY [" + v.get("type", "") + "]: "
             + v.get("detail", ""))
            for v in (cons.get("violations") or [])]
        if _ts_on and _repair_round == 1:
            # item 2 (2026-11-12): the plain tech-sanity lines ride the
            # SAME scheduled repair call (no added call, no gate)
            _viol_lines += ["TECH SANITY: " + f["plain"]
                            for f in _tech_sanity_findings(
                                answer, _uvs)]
        repair_prompt = _REPAIR_PROMPT.format(
            violations="\n".join(f"- {v}" for v in _viol_lines[:12]),
            previous=answer[:3000],
            device=problem.get("device", ""),
            failure=problem.get("failure", ""),
            variables_block=_variables_block(problem),
            numbered_constraints=_ncons,
            shape_hint=shape_hint, shape_block=shape,
            constraint_check_spec=CONSTRAINT_CHECK_BLOCK_SPEC)
        res3 = llm_generate(repair_prompt, system=_COMPOSER_SYSTEM,
                            max_tokens=max_tokens,
                            purpose="answer_composer_repair")
        rec["n_llm_calls"] += 1
        if not (res3.get("ok") and (res3.get("content") or "").strip()):
            trunc["repair_transport_failed"] = True
            break
        answer3 = res3["content"].strip()
        answer3, _ck_block3 = strip_constraint_check(answer3)
        contract3 = validate_answer(answer3, question_type,
                                    packet=packet or [],
                                    user_variables=_uvs,
                                    clarification=_clarification)
        ck3 = parse_constraint_check(_ck_block3, answer3)
        caudit3 = audit_constraints(problem, answer3)
        caudit3 = merge_constraint_check(caudit3, ck3) if _ca_on \
            else caudit3
        cons3 = _cons_check(answer3, candidates or [], problem)
        # a truncated repair is NEVER adopted (never ship a
        # truncated answer): the pre-existing improvement rule
        # applies to COMPLETE repairs only
        trunc["repair_finish_reason"] = _recorded_finish_reason(res3)
        trunc["repair_truncated"] = _is_answer_truncated(answer3, res3)
        rec[f"contract_after_repair_{_repair_round}"] = {
            "valid": contract3.get("valid"),
            "violations": contract3.get("violations")}
        rec[f"constraint_audit_after_repair_{_repair_round}"] = {
            "state": caudit3.get("state"),
            "n_violations": caudit3.get("n_violations")}
        rec[f"consistency_after_repair_{_repair_round}"] = {
            "state": cons3.get("state"),
            "n_violations": cons3.get("n_violations")}
        if trunc["repair_truncated"]:
            break
        # adopt only a COMPLETE repair that does not regress (the
        # improvement rule: fewer contract violations, or valid, and
        # no worse on the constraint audit or the consistency check)
        _improved = (contract3.get("valid") is True
                     or (len(contract3.get("violations") or [])
                         < len(contract.get("violations") or [])))
        _audit_not_worse = (caudit3.get("n_violations") or 0) <= (
            caudit.get("n_violations") or 0)
        _cons_not_worse = (cons3.get("n_violations") or 0) <= (
            cons.get("n_violations") or 0)
        if _improved and _audit_not_worse and _cons_not_worse:
            answer = answer3
            contract = contract3
            caudit = caudit3
            cons = cons3
            rec["output_sha256"] = res3.get("output_hash")
            rec["repaired"] = True
            rec["repair_rounds_used"] = _repair_round
            if (contract.get("valid") is True
                    and caudit.get("state") == "CONSTRAINT_AUDIT_PASS"
                    and cons.get("state") == "CONSISTENCY_PASS"):
                # R9 P0: the post-repair break now demands the check
                # PASSED — "not violations" (CHECK_ABSENT) is not a
                # pass and never silently ends the loop as one.
                break
    rec["repair_rounds_used"] = rec.get("repair_rounds_used", _repair_round)
    # ---- STRICT PROVENANCE DOWNGRADE (owner audit round 2026-11-13,
    # directive 2): an EVIDENCE-BACKED PARAMETER whose VALUE is not in
    # the CITED record is relabeled ASSUMPTION — or ASSUMPTION (User
    # Constraint) when the value IS the user's own stated text — even
    # when the citation id itself is valid. Deterministic, zero-LLM,
    # runs on EVERY delivered answer (the measured fu-005 defect shipped
    # contract-VALID with false EVIDENCE-BACKED labels). The relabel
    # only removes certainty, so the contract re-validation can only
    # hold or improve; the typed detail rides rec["strict_provenance"].
    from .answer_downgrade import strict_provenance_downgrade
    _dg_on = os.environ.get("FABRIC_ANSWER_DOWNGRADE", "1") != "0"
    rec["downgrade_arm"] = "on" if _dg_on else "off"
    _strict = (strict_provenance_downgrade(answer, packet, problem)
               if _dg_on else {"n_relabels": 0, "answer": answer,
                               "relabels": [],
                               "n_user_constraint_relabels": 0})
    if _strict["n_relabels"]:
        _sv = validate_answer(_strict["answer"], question_type,
                              packet=packet or [],
                              user_variables=_uvs,
                              clarification=_clarification)
        _sc = (audit_constraints(problem, _strict["answer"])
               if _ca_on else caudit)
        rec["strict_provenance"] = {
            "applied": True,
            "n_relabels": _strict["n_relabels"],
            "n_user_constraint_relabels":
                _strict["n_user_constraint_relabels"],
            "relabels": _strict["relabels"],
            "contract_valid_after": _sv.get("valid") is True}
        answer = _strict["answer"]
        if _sv.get("valid") is True and not contract.get("valid"):
            contract = _sv
        if (_sc.get("n_violations") or 0) <= (caudit.get("n_violations")
                                              or 0):
            caudit = _sc
    # ---- DOWNGRADE, DON'T DISCARD (owner directive 2, 2026-11-12):
    # a contract-invalid composition is no longer discarded into a
    # typed no-answer. Deterministic relabel: failing EVIDENCE-BACKED
    # claims become ASSUMPTION, invalid citations drop, internal
    # candidate ids strip; the downgraded text re-validates and SHIPS
    # with ONE plain-language caveat. Typed no-answer stays only for
    # transport failure and the composer's scientific refusals.
    from .answer_downgrade import (downgrade_answer,
                                   DOWNGRADE_CAVEAT_LINE,
                                   truncate_at_sentence)
    _delivered_note: Optional[str] = None
    if contract.get("valid") is not True and _dg_on:
        dg = downgrade_answer(answer, contract.get("violations") or [],
                              packet)
        contract_dg = validate_answer(dg["answer"], question_type,
                                      packet=packet or [],
                                      user_variables=_uvs,
                                      clarification=_clarification)
        caudit_dg = (audit_constraints(problem, dg["answer"])
                     if _ca_on else caudit)
        rec["downgrade"] = {
            "applied": True,
            "n_relabels": dg["n_relabels"],
            "n_citations_dropped": dg["n_citations_dropped"],
            "n_jargon_stripped": dg["n_jargon_stripped"],
            "relabels": dg["relabels"],
            "citations_dropped": dg["citations_dropped"],
            "valid_after_downgrade": contract_dg.get("valid") is True}
        answer = dg["answer"]
        if (contract_dg.get("valid") is True
                and (caudit_dg.get("n_violations") or 0)
                <= (caudit.get("n_violations") or 0)):
            contract = contract_dg
            caudit = caudit_dg
        else:
            caudit = caudit_dg
    rec["answer"] = answer
    rec["contract"] = {"valid": contract.get("valid"),
                       "violations": contract.get("violations"),
                       "bindings": contract.get("bindings"),
                       "question_type": question_type}
    # directive 2: the constraint audit's final state rides the record
    # (typed metadata — the shipped text itself must be clean;
    # constraint violations that survived every bounded repair are
    # delivered with ONE plain-language caveat line by the harness)
    rec["constraint_audit"] = {"state": caudit.get("state"),
                               "n_violations": caudit.get("n_violations"),
                               "violations": caudit.get("violations")}
    rec["constraint_check"] = ck
    # the consistency check's FINAL state rides the record (the check
    # drove the repair loop above; a violation that survived every
    # bounded repair ships with ONE plain caveat, typed detail in
    # metadata — never silent, Art. XXV)
    cons_final = _cons_check(answer, candidates or [], problem)
    rec["consistency_check"] = {"state": cons_final.get("state"),
                                "n_violations":
                                    cons_final.get("n_violations"),
                                "violations":
                                    cons_final.get("violations")}
    if contract.get("valid") is True:
        rec["state"] = "COMPOSED_CONTRACT_VALID"
    elif rec.get("downgrade", {}).get("applied"):
        # delivered at the last complete sentence; the typed detail
        # (open violations) rides rec["contract"], never a banner
        rec["state"] = "COMPOSED_CONTRACT_DOWNGRADED"
        _delivered_note = DOWNGRADE_CAVEAT_LINE
    else:
        rec["state"] = "COMPOSED_CONTRACT_INVALID"
    # item 2: the deterministic tech-sanity record (typed detail;
    # NEVER a gate — the state above stays contract-only)
    _ts_final = (_tech_sanity_findings(
        answer, problem.get("user_variables") or [])
        if _ts_on else [])
    rec["tech_sanity"] = {"enabled": _ts_on,
                          "flag": _TECH_SANITY_FLAG,
                          "findings": _ts_final,
                          "n_findings": len(_ts_final)}
    # plain-language caveats (the typed detail stays in the
    # truncation / contract / tech_sanity metadata above — Art. XXV)
    _caveats: List[str] = []
    if _delivered_note:
        _caveats.append(_delivered_note)
    if trunc["n_truncation_retries"]:
        _caveats.append(
            "The first draft was cut off at the model's output "
            "budget; the answer above is the larger-budget "
            "recomposition.")
    if trunc.get("repair_truncated"):
        _caveats.append(
            "The repair attempt was also cut off at the output "
            "budget and was not used; the answer above is the "
            "complete pre-repair draft, still carrying its open "
            "contract violations.")
    for _f in _ts_final:
        _caveats.append(_f["plain"])
    if cons_final.get("state") == "CONSISTENCY_VIOLATIONS" \
            and rec.get("state") in ("COMPOSED_CONTRACT_VALID",
                                     "COMPOSED_CONTRACT_DOWNGRADED"):
        from .answer_consistency import CONSISTENCY_CAVEAT_LINE
        if CONSISTENCY_CAVEAT_LINE not in _caveats:
            _caveats.append(CONSISTENCY_CAVEAT_LINE)
    if cons_final.get("state") == "CHECK_ABSENT" \
            and rec.get("state") in ("COMPOSED_CONTRACT_VALID",
                                     "COMPOSED_CONTRACT_DOWNGRADED"):
        # R9 P0: a check that could not run is delivered as exactly
        # that — the answer carries the typed absent-caveat (never a
        # silent pass, Art. XXV)
        from .answer_consistency import CONSISTENCY_ABSENT_CAVEAT_LINE
        if CONSISTENCY_ABSENT_CAVEAT_LINE not in _caveats:
            _caveats.append(CONSISTENCY_ABSENT_CAVEAT_LINE)
    if _caveats:
        rec["caveats"] = _caveats
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


def _is_infrastructure_verdict(v: str) -> bool:
    """Art. LXI typed classes: an evaluator / evaluation / transport
    failure or an INCOMPLETE_* state is INFRASTRUCTURE, never a
    scientific rejection. Directive 2 (owner audit round 2026-11-12):
    the typed no-answer is reserved for scientific kills — an
    infrastructure-typed verdict on the record-bound raw candidate
    delivers as a clearly flagged UNVERIFIED hypothesis instead."""
    u = str(v or "").strip().upper()
    if not u:
        return False
    if u in ("EVALUATOR_CALL_FAILED", "EVALUATION_FAILED",
             "PROVIDER_UNAVAILABLE", "PENDING"):
        return True
    return (u.startswith("EVALUATOR_") or u.startswith("EVALUATION_")
            or u.startswith("INCOMPLETE_") or u.startswith("PENDING_"))


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


def _kf_fallback_candidate(env_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """A SURVIVING knowledge-first candidate from the recorded mechanism
    space (owner audit round 2026-11-13, directive 3): transformation
    operator DOMAIN_KNOWLEDGE_FIRST, state exactly CANDIDATE (it passed
    the same deterministic gates as every other candidate), candidate
    id not a noncand: rejection id. Returns the FIRST such candidate in
    the space's recorded order (None when none survives) — the fallback
    order authority: when the evidence-anchored candidates are killed,
    the knowledge-first candidate is delivered; an evidence-anchored
    killed candidate only when no knowledge-first candidate survives."""
    ms = env_dict.get("mechanism_space") or {}
    for c in (ms.get("candidates") or []) if isinstance(ms, dict) else []:
        if not isinstance(c, dict):
            continue
        if str(c.get("transformation_operator") or "") \
                != "DOMAIN_KNOWLEDGE_FIRST":
            continue
        if str(c.get("candidate_state") or "") != "CANDIDATE":
            continue
        if str(c.get("candidate_id") or "").startswith("noncand:"):
            continue
        return c
    return None


def _admission_gate_checks(problem: Optional[Dict[str, Any]],
                           cand: Dict[str, Any]) -> List[Dict[str, Any]]:
    """R11 owner item 6: the DETERMINISTIC pre-admission instruments,
    run on EVERY candidate any admission branch would deliver (the
    audited live regression: fu-004's tanh-PID controller shipped on
    the infrastructure-verdict hypothesis path where NO deterministic
    gate ran — the mechanism_space assembly checks never saw it).
    Two instruments, zero LLM:
      1. question_type_match_check — a predictor question's candidate
         must be an indicator, never a controller;
      2. mechanism_to_failure_link_check — the gimmick-anchor
         rejection (the KF candidate is exempt: its anchor IS the
         problem statement; the A2 raw candidate's anchor is its
         source_evidence record).
    Returns the typed rejection reasons (empty list = admitted)."""
    if not problem:
        return []
    from .intervention_gate import question_type_match_check
    from .mechanism_link import mechanism_to_failure_link_check
    reasons: List[Dict[str, Any]] = []
    fields = {
        "intervention": str(cand.get("intervention") or ""),
        "mechanism": str(cand.get("mechanism") or ""),
        "expected_effect": str(cand.get("expected_effect") or ""),
        "predicted_effect": str(cand.get("predicted_effect") or ""),
        "falsification_test": str(cand.get("falsification_test")
                                  or ""),
    }
    qtm = question_type_match_check(problem, fields)
    if qtm.get("rejected"):
        reasons.append({
            "source": "admission_gate",
            "candidate_id": str(cand.get("candidate_id") or ""),
            "instrument": qtm.get("instrument"),
            "reason": qtm.get("reason"),
            "reason_class": qtm.get("reason_class"),
            "n_controller_signatures":
                qtm.get("n_controller_signatures")})
        return reasons  # the routing failure is decisive on its own
    if cand.get("candidate_source") == "DOMAIN_KNOWLEDGE_FIRST":
        return reasons  # the KF anchor IS the problem statement
    anchor_text = " ".join(str(cand.get(k) or "") for k in
                           ("mechanism_source_span",))
    se = cand.get("source_evidence") or {}
    structured_item = {
        "item_id": str(se.get("source_id")
                       or cand.get("anchor_item_id") or ""),
        "_record_text": " ".join(
            str(se.get(k) or "") for k in
            ("source_title", "title", "source_span", "abstract"))
        or anchor_text,
    }
    if not str(structured_item.get("_record_text") or "").strip():
        # Art. XXV: a candidate with NO bound anchor record gives the
        # link check nothing to verify — the typed state is
        # INDETERMINATE (disclosed in the admission record), never a
        # rejection manufactured from a missing observation. The
        # mechanism_space path still hard-gates (its candidates
        # always carry their anchor item).
        return reasons
    ml = mechanism_to_failure_link_check(problem, structured_item,
                                         fields,
                                         operator_id=str(
                                             cand.get("operator_id")
                                             or "A2_RAW"))
    if ml.get("verdict") in ("NO_FAILURE_PHENOMENON", "ANCHOR_OFF_DOMAIN",
                             "GIMMICK_ANCHOR_NO_LINK"):
        reasons.append({
            "source": "admission_gate",
            "candidate_id": str(cand.get("candidate_id") or ""),
            "instrument": ml.get("instrument_version"),
            "reason": ml.get("reason"),
            "reason_class": ml.get("verdict")})
    return reasons


def _admission_analysis(env_dict: Dict[str, Any],
                       top_n: int = 5,
                       problem: Optional[Dict[str, Any]] = None):
    """P0-2: one admission audit. Returns (admissible_cands, reasons):
    the gate-admissible candidates, and the typed reasons for every
    recorded verdict that FAILED the allowlist (recorded in the
    NO_ADMISSIBLE state — Art. XXV). R11: `problem` enables the
    deterministic pre-admission instruments (question-type routing +
    the gimmick-anchor link check) on EVERY admission branch."""
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
        _gate = _admission_gate_checks(problem, rr)
        if _gate:
            reasons.extend(_gate)
            continue
        rr["admission"]["gate_checks"] = "PASSED"
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
        # 3. DIRECTIVE 6 (owner audit round 2026-11-12) — the approved
        #    attack semantics for "not in the record" kills: when the
        #    ONLY recorded kills are typed KILL_CAUSE_NOT_IN_RECORD
        #    (the retrieved evidence does not contain the support the
        #    candidate claimed — an evidence-coverage limitation of
        #    THIS retrieval, never a physical impossibility), the
        #    record-bound raw candidate is admissible as a clearly
        #    flagged UNVERIFIED hypothesis instead of a typed
        #    no-answer. The typed kill-cause classification rides the
        #    record (never self-judged: the auditor reads the class).
        #    ANY scientific kill keeps the kill (no delivery).
        from .mechanism_link import kill_cause_record
        kc = kill_cause_record(env_dict.get("attack_results") or {})
        if (att in _KILL_STATES or "KILL" in att) \
                and kc.get("all_not_in_record") \
                and binding is None:
            # OWNER AUDIT ROUND 2026-11-13, DIRECTIVE 3 (fallback
            # order): when the evidence-anchored candidate is killed,
            # deliver the SURVIVING knowledge-first candidate; the
            # killed evidence-anchored candidate delivers only when no
            # knowledge-first candidate survives. The KF candidate
            # here is equally unadjudicated (ranked survivors were
            # empty), so it ships as the same clearly flagged
            # UNVERIFIED hypothesis class — never an endorsement.
            kf = _kf_fallback_candidate(env_dict)
            if kf is not None:
                rec_kf = dict(kf)
                rec_kf["attack_verdict"] = att
                rec_kf["verdict"] = att
                rec_kf["admission"] = {
                    "class": "HYPOTHESIS",
                    "hypothesis": True,
                    "reason": "KF_FALLBACK_EVIDENCE_CANDIDATE_KILLED",
                    "binding": "mechanism_space_record",
                    "candidate_source": "DOMAIN_KNOWLEDGE_FIRST",
                    "delivery_semantics":
                        "FLAGGED_UNVERIFIED_HYPOTHESIS_DELIVERED",
                    "kill_cause_record": kc}
                rec_kf["hypothesis_unverified"] = True
                rec_kf["candidate_source"] = "DOMAIN_KNOWLEDGE_FIRST"
                _gate = _admission_gate_checks(problem, rec_kf)
                if _gate:
                    reasons.extend(_gate)
                    return [], reasons
                cands.append(rec_kf)
                return cands, reasons
            rec2 = dict(raw)
            rec2["attack_verdict"] = att
            rec2["verdict"] = att
            rec2["admission"] = {
                "class": "HYPOTHESIS",
                "hypothesis": True,
                "reason": "ALL_KILLS_NOT_IN_RECORD",
                "binding": "attack_record_bound",
                "kill_cause_record": kc}
            rec2["hypothesis_unverified"] = True
            rec2["kill_cause_record"] = kc
            _gate = _admission_gate_checks(problem, rec2)
            if _gate:
                reasons.extend(_gate)
                return [], reasons
            cands.append(rec2)
            return cands, reasons
        # DIRECTIVE 2 (owner audit round 2026-11-12): the typed
        # no-answer is reserved for SCIENTIFIC kills. An
        # infrastructure-typed verdict (evaluator / evaluation /
        # transport failure, INCOMPLETE_*) on the record-bound raw
        # candidate is Art. LXI infrastructure — it delivers as a
        # clearly flagged UNVERIFIED hypothesis (one plain-language
        # line, never silence, never a scientific claim).
        if _is_infrastructure_verdict(att) and binding is None:
            rec2 = dict(raw)
            rec2["attack_verdict"] = att
            rec2["verdict"] = att
            rec2["admission"] = {
                "class": "HYPOTHESIS",
                "hypothesis": True,
                "reason": "VERDICT_IS_INFRASTRUCTURE_NOT_SCIENTIFIC",
                "binding": "attack_record_bound"}
            _gate_early = _admission_gate_checks(problem, rec2)
            if _gate_early:
                reasons.extend(_gate_early)
                return [], reasons
            rec2["hypothesis_unverified"] = True
            rec2["own_recorded_states"] = {
                "evidence_verification": "NOT_RECORDED",
                "contradictions": "NOT_RECORDED",
                "technical_gates": {
                    "not_an_intervention":
                        raw.get("not_an_intervention_check",
                                "NOT_RECORDED"),
                    "anchor_domain":
                        raw.get("anchor_domain_check", "NOT_RECORDED")},
            }
            cands.append(rec2)
            return cands, reasons
        # DIRECTIVE 2+6 (owner audit round 2026-11-12, measured on the
        # fu-005 live run of this round): a run that STARVES BEFORE THE
        # ATTACK (typed MECHANISM_STARVED at the mechanism-space
        # distinctness gate) leaves the envelope's evidence-SUPPORTED
        # raw candidate NEVER ADJUDICATED (binding = ATTACK_RECORD_
        # ABSENT). That is an adjudication-infrastructure absence, not
        # a scientific kill and not a binding break: the record-bound
        # raw candidate delivers as a clearly flagged UNVERIFIED
        # hypothesis (one plain-language caveat line) — the same
        # FLAGGED_UNVERIFIED_HYPOTHESIS_DELIVERED semantics the
        # committed kill record for this problem pre-approves
        # (eval/kills/r6_dev12/), never an endorsement. Guards: the
        # binding must be exactly the never-adjudicated class (a broken
        # binding still refuses), and the envelope's own evidence
        # verification must have SUPPORTED the candidate (an
        # evidence-failed candidate is never delivered).
        if binding is not None \
                and binding.startswith("ATTACK_RECORD_ABSENT"):
            ev = ((env_dict.get("adjudication") or {}).get(
                "evidence_verification") or {})
            if ev.get("verified") is True:
                # OWNER AUDIT ROUND 2026-11-13, DIRECTIVE 3 (fallback
                # order, the measured fu-005 case): the starved run
                # left the evidence-anchored candidate NEVER
                # ADJUDICATED; the surviving knowledge-first candidate
                # is the preferred delivery (the killed/never-
                # adjudicated evidence-anchored candidate delivers
                # only when no knowledge-first candidate survives).
                kf = _kf_fallback_candidate(env_dict)
                if kf is not None:
                    rec_kf = dict(kf)
                    rec_kf["attack_verdict"] = att
                    rec_kf["verdict"] = att
                    rec_kf["admission"] = {
                        "class": "HYPOTHESIS",
                        "hypothesis": True,
                        "reason":
                            "KF_FALLBACK_EVIDENCE_CANDIDATE_KILLED",
                        "binding": "mechanism_space_record",
                        "candidate_source": "DOMAIN_KNOWLEDGE_FIRST",
                        "delivery_semantics":
                            "FLAGGED_UNVERIFIED_HYPOTHESIS_DELIVERED",
                        "attack_record":
                            "ABSENT (the run starved before the attack "
                            "stage — the knowledge-first candidate is "
                            "equally unadjudicated, never endorsed)"}
                    rec_kf["hypothesis_unverified"] = True
                    rec_kf["candidate_source"] = "DOMAIN_KNOWLEDGE_FIRST"
                    cands.append(rec_kf)
                    return cands, reasons
                rec2 = dict(raw)
                rec2["attack_verdict"] = att
                rec2["verdict"] = att
                rec2["admission"] = {
                    "class": "HYPOTHESIS",
                    "hypothesis": True,
                    "reason": "ATTACK_NEVER_ADJUDICATED_STARVED_RUN",
                    "binding": "raw_candidate_record_bound",
                    "delivery_semantics":
                        "FLAGGED_UNVERIFIED_HYPOTHESIS_DELIVERED"}
                rec2["hypothesis_unverified"] = True
                rec2["own_recorded_states"] = {
                    "evidence_verification": "VERIFIED",
                    "attack_record": "ABSENT (the run starved before "
                                     "the attack stage — never "
                                     "adjudicated, never endorsed)"}
                cands.append(rec2)
                return cands, reasons
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
                          top_n: int = 5,
                          problem: Optional[Dict[str, Any]] = None
                          ) -> List[Dict[str, Any]]:
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
    recommendation. R11: `problem` enables the deterministic
    pre-admission instruments on every branch."""
    return _admission_analysis(env_dict, top_n=top_n,
                               problem=problem)[0]


def admission_reasons_from_state(env_dict: Dict[str, Any],
                                 top_n: int = 5,
                                 problem: Optional[Dict[str, Any]] = None
                                 ) -> List[Dict[str, Any]]:
    """P0-2: the typed reasons NO candidate is admissible (one entry
    per recorded verdict that failed the allowlist — recorded in the
    NO_ADMISSIBLE_CANDIDATES state; the unknown is typed, not
    buried; Art. XXV)."""
    return _admission_analysis(env_dict, top_n=top_n,
                               problem=problem)[1]


def compose_if_admissible(env_dict: Dict[str, Any],
                         problem: Dict[str, Any],
                         packet: Optional[List[Dict[str, Any]]],
                         verification: Optional[Dict[str, Any]],
                         question_type: str,
                         llm_generate=None,
                         top_n: int = 5,
                         max_tokens: int = 1000,
                         tech_sanity: Optional[bool] = None,
                         ) -> Dict[str, Any]:
    """P0-2 engine gate — ONE entry point for admission + composition.

    Admission runs FIRST. No admissible candidate: the typed
    NO_ADMISSIBLE_CANDIDATES record with its typed reasons and ZERO
    composer LLM calls (never an invented recommendation, Art.
    XVIII/XXV/LXI). No frozen packet with admissible candidates:
    the typed SKIPPED_NO_PACKET refusal, zero LLM calls.
    Otherwise: compose_answer over the ADMITTED candidates only."""
    cands = candidates_from_state(env_dict, top_n=top_n,
                                  problem=problem)
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
                admission_reasons_from_state(env_dict, top_n=top_n,
                                             problem=problem),
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
                        max_tokens=max_tokens,
                        tech_sanity=tech_sanity)
    out["admitted_candidates"] = [
        {"candidate_id": str(c.get("candidate_id") or ""),
         "attack_verdict": c.get("attack_verdict"),
         "hypothesis": bool(c.get("hypothesis_unverified"))}
        for c in cands]
    return out
