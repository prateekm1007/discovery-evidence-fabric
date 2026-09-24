"""A2 synthesize — LLM generates candidate from frozen evidence.

E1 bridge: transport is delegated to discovery_fabric.engine.llm_registry
(seven-provider registry; missing keys are PROVIDER_UNAVAILABLE, never a
silent downgrade — Constitution Art. IV/XXV). Prompt, parsing and candidate
assembly (business logic) are UNCHANGED from the frozen A2 implementation.
"""
from __future__ import annotations
import os
import json, re, hashlib, ssl, time, urllib.request
from datetime import datetime, timezone

# Set by llm_chat() on every call: provenance of the transport actually used.
# Art. VI: only real call metadata is recorded here, never placeholders.
_LAST_PROVIDER_META: dict = {"status": "NEVER_CALLED"}

FROZEN_MODEL = "deepseek/deepseek-v4-flash-0731"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE

SYNTHESIS_PROMPT = """You are a mechanism interpreter for engineering problem-solving.

Given a device failure and a retrieved scientific paper, extract a mechanism that could
address the failure. The paper may be from any domain.

DEVICE FAILURE:
- Device: {device}
- Failure: {failure}
- Constraint: {constraint}

RETRIEVED PAPER:
- Title: {title}
- Abstract: {abstract}

Respond in EXACTLY this format (each field on ONE line):
MECHANISM: <mechanism from the paper>
INTERVENTION: <specific intervention transferring mechanism to device>
EXPECTED_EFFECT: <expected effect>
FALSIFICATION_TEST: <concrete test>
{span_instruction}
"""

# R469 (the evidence-span citation contract — the R468 measured gap:
# 'mechanism_span_not_verbatim; the proposer model did not emit a
# verbatim evidence-bound span'): the span instruction becomes a
# mechanical rule block. The verifier (a2/verify.py) stays byte-exact —
# the fix is claimant-side only (Art. II/III: the verifier is never
# loosened; exact evidence beats semantic plausibility).
SPAN_INSTRUCTION = (
    "MECHANISM_SOURCE_SPAN: <verbatim substring from THIS abstract "
    "supporting MECHANISM>\n\n"
    "Mechanical rules for MECHANISM_SOURCE_SPAN (the verifier checks "
    "this byte-for-byte against the abstract; a paraphrase is a hard "
    "failure that blocks the whole run):\n"
    "- Open THIS abstract and COPY at least 8 consecutive words "
    "character-for-character, including punctuation, capitalization "
    "and numbers, exactly as written.\n"
    "- Do NOT paraphrase, re-order, shorten, lengthen, fix grammar, "
    "or join words that are not adjacent in the abstract.\n"
    "- The span MUST come from the ABSTRACT text below — never from "
    "the Title line and never from your own words (a span quoted from "
    "the title fails the byte check: the verifier checks against the "
    "abstract only).\n"
    "- Example of RIGHT (abstract says 'Platelets adhere to the "
    "injured endothelium within seconds'): Platelets adhere to the "
    "injured endothelium within seconds.\n"
    "- Example of WRONG: platelet adhesion to damaged vessel lining "
    "(that is a paraphrase — it fails the byte check).\n"
    "- If you cannot find 8 consecutive words that support the "
    "MECHANISM, copy the longest exact phrase that does (10+ words "
    "preferred; 8 minimum).")

# R470 (external re-audit P0-5, the POWER leg): the steering directive
# constraint — when the round was opened under an exclusion-class
# directive (CHANGE_MECHANISM / RESEARCH), the spawn site derives a
# typed constraint from the PARENT'S RECORDED mechanism identity and
# the problem carries it here. The block is appended to the prompt
# (after the span rules) and a mechanical post-parse check runs the
# SAME shared compliance function the outcome card uses (one
# instrument, Art. X). A violation gets ONE recorded repair retry; a
# still-violating candidate is returned with violation_final: true —
# honest either way (the ladder's own gates still run; nothing is
# hidden, nothing is fabricated).
CONSTRAINT_INSTRUCTION = (
    "\n\nOPERATOR DIRECTIVE — MECHANICAL COMPLIANCE CHECK (a checker "
    "runs on your answer):\n"
    "The operator's direction for this round explicitly excludes a "
    "recorded mechanism. The EXCLUDED mechanism is:\n"
    "\"{forbidden}\"\n"
    "- Do NOT restate it, minimally rephrase it, or re-derive it under "
    "new wording.\n"
    "- A MECHANISM whose identity repeats the excluded one is a "
    "compliance violation: it will be REJECTED and you will be asked "
    "again.\n"
    "- Propose a genuinely different mechanism from THIS abstract.")

def _hash(s): return hashlib.sha256(s.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# R469 — the mechanical evidence-span repair (the engineer's design,
# CTO-reviewed). Claimant-side only: a2/verify.py is UNTOUCHED and stays
# byte-exact. The promoted span is SLICED FROM THE ABSTRACT'S OWN
# CHARACTERS, so it is a byte-exact substring of the abstract by
# construction; the verifier then re-checks it with the identical gate.
# A repair that cannot find >=8 consecutive verbatim words leaves the
# candidate unchanged — the typed failure stands (Art. XXV honesty).
# ---------------------------------------------------------------------------
SPAN_MIN_WORDS = 8

#: R483 — the abstract-bearing paper floor (the synthesis rotation's
#: gate): a record carrying fewer abstract characters cannot satisfy
#: the verbatim span contract (8+ consecutive words to quote) or feed
#: the LLM-quote assist (sentence context). DECLARED, never tuned
#: (Art. XXVII). The geothermal specimen (doi:10.1186/s40517-019-0138-3,
#: abstract "") is the canonical excluded record.
SPAN_ABSTRACT_MIN_CHARS = 200


def _strip_quotes(text):
    """Byte-identical to the stripping step in a2/verify.py (the CTO
    correction to the engineer's draft: no extra quote characters — the
    'already verbatim' early-exit must agree with the verifier)."""
    return text.strip().strip('"').strip("'").strip()


def _token_offsets(text):
    """Tokens with character offsets (\\S+ splits like str.split())."""
    return [(m.group(0), m.start(), m.end())
            for m in re.finditer(r"\S+", text)]


def _longest_common_token_run(emit, abstract, case_insensitive):
    """Longest run of tokens contiguous in BOTH strings. Exact token
    comparison, or case-insensitive when case_insensitive=True. NO other
    normalization (no stemming, no punctuation stripping, no whitespace
    collapsing) — the repair must never become the fuzzy matcher the
    Constitution forbids. Ties break by first occurrence in `emit`
    (strict >), so the result is deterministic."""
    e = _token_offsets(emit)
    a = _token_offsets(abstract)
    e_tok = [t[0].lower() if case_insensitive else t[0] for t in e]
    a_tok = [t[0].lower() if case_insensitive else t[0] for t in a]
    n, m = len(e_tok), len(a_tok)
    if n == 0 or m == 0:
        return None
    prev = [0] * (m + 1)
    best_len, best_e, best_a = 0, 0, 0
    for i in range(1, n + 1):
        cur = [0] * (m + 1)
        ei = e_tok[i - 1]
        for j in range(1, m + 1):
            if ei == a_tok[j - 1]:
                v = prev[j - 1] + 1
                cur[j] = v
                if v > best_len:
                    best_len, best_e, best_a = v, i - v, j - v
        prev = cur
    if best_len == 0:
        return None
    return best_len, best_e, best_a


def _promote_window(abstract, run):
    """The abstract's OWN text for the run, or None below the floor.
    Sliced from `abstract` — byte-exact substring by construction."""
    if run is None:
        return None
    length, _e_start, a_start = run
    if length < SPAN_MIN_WORDS:
        return None
    a = _token_offsets(abstract)
    return abstract[a[a_start][1]:a[a_start + length - 1][2]]


def repair_mechanism_span(candidate, abstract):
    """Mechanical, provenance-recorded repair of a non-verbatim span.
    In-place; if no >=8-word verbatim contiguous window exists, the
    candidate is returned UNCHANGED and the typed failure stands."""
    raw = candidate.get("mechanism_source_span")
    if not raw:
        return candidate
    span = _strip_quotes(raw)
    # Already passes the gate exactly as emitted -> never touch, never mark.
    if span in abstract or span.lower() in abstract.lower():
        return candidate
    # Mirror verify.py's documented fallback order: exact, then case fold.
    for case_insensitive in (False, True):
        promoted = _promote_window(
            abstract, _longest_common_token_run(span, abstract,
                                                case_insensitive))
        if promoted is not None:
            candidate["mechanism_source_span"] = promoted
            candidate["span_repair"] = {
                "original": span,
                "promoted": promoted,
                "method": "verbatim-subwindow",
                "case_insensitive": case_insensitive,
            }
            return candidate
    return candidate

def llm_chat(prompt, system="", max_retries=2, timeout=240,
             max_tokens=512):
    """E1: delegate transport to the provider registry. Returns content or
    None exactly as before; _LAST_PROVIDER_META records what happened
    (OK / PROVIDER_UNAVAILABLE / CALL_FAILED) for the provenance chain.
    timeout=240: the frozen synthesis model measured 140-151 s end-to-end on
    NVIDIA (verified live 2026-08-27); 60 s produced systematic timeouts.
    OPERATOR OVERRIDE: ENGINE_SYNTHESIS_PROVIDER=<provider_id> pins the
    transport to one provider with fallback forbidden — an EXPLICIT,
    logged, meta-recorded substitution for degraded-endpoint situations
    (never silent: the override is echoed here and travels in the
    candidate provenance). Default remains the frozen-model policy."""
    global _LAST_PROVIDER_META
    try:
        from discovery_fabric.engine import llm_registry as reg
    except Exception as exc:  # registry import broken -> explicit, not silent
        _LAST_PROVIDER_META = {"status": "CALL_FAILED", "error": f"registry import failed: {exc}"}
        return None
    override = os.environ.get("ENGINE_SYNTHESIS_PROVIDER", "").strip()
    if override:
        print(f"  [synthesize] OPERATOR OVERRIDE: synthesis provider pinned "
              f"to '{override}' (fallback forbidden; recorded in meta)")
        # R519 §5/§7: honoring the ENGINE_* env pin is an explicit
        # operator act — marked as such so the single routing-retirement
        # authority keeps (and records) the override instead of silently
        # blocking it. Retirement still filters ORDINARY routing.
        policy = reg.SelectionPolicy(
            preferred_providers=[override], max_preference_fallback=0,
            purpose="synthesis", operator_override=True)
    else:
        # R518: Atria retired from synthesis (R517 battery: 12-128s latency)
        policy = reg.SelectionPolicy(
            preferred_providers=["openrouter", "deepseek",
                                 "anthropic", "openai", "gemini",
                                 "qwen", "nvidia"],
            purpose="synthesis")
    # max_tokens=512: the FIELD-line protocol needs ~150-250 tokens; wall
    # time on the deepseek reasoning endpoint scales with the cap (measured
    # 2026-08-27). Empty-content (reasoning exhaustion) retries bump the cap
    # inside llm_registry automatically and are recorded in retry_notes.
    res = reg.generate(prompt, system=system, timeout=timeout,
                       max_retries=max_retries, policy=policy,
                       max_tokens=max_tokens)
    _LAST_PROVIDER_META = res.to_meta()
    _LAST_PROVIDER_META["selection_ledger"] = res.selection_ledger
    if res.ok:
        time.sleep(0.5)
        return res.content
    print(f"  [synthesize] LLM transport status: {res.status}"
          f"{(' — ' + res.error[:160]) if res.error else ''}")
    return None

def synthesize(problem: dict, evidence: list[dict]) -> dict | None:
    """Step 3: LLM synthesis from frozen evidence.

    R422 (the LLM chokepoint directive — measured live 2026-09-08):
    the probe completes ("Reply with exactly: READY") while the REAL
    synthesis call fails on the free tier — OBSERVED: a live run
    (ts_12ad5b143371) with 16 custody-frozen evidence records died at
    SYNTHESIZE/FAILED_EXPLICIT after ONE call on evidence[0] (route:
    openrouter free rungs; per-model flakiness flaps on minute scales).
    The reliability lever that does NOT touch frozen business logic:
    rotate through the first N evidence papers with a short backoff —
    (a) a transport failure is time-flappy, so a delayed second call
    often succeeds (probe OK 4 min after a total ladder failure,
    same window); (b) a format-hostile response gets two more chances
    with different (shorter/different) abstracts through the UNCHANGED
    prompt/parser/candidate-assembly. Each attempt is a real, recorded
    call; the winning candidate's provenance records the rotation
    (papers tried, attempt index) like the E15 same-provider retry.
    All-attempts-failed still returns None -> FAILED_EXPLICIT (Art. XXV:
    honest; Art. LXI: infrastructure is never a scientific rejection).
    """
    if not evidence:
        print("  [synthesize] no evidence, cannot synthesize")
        return None

    # R525 Q-A (behavior-neutral span instrumentation): read-only
    # perf_counter deltas around the phases that actually exist in this
    # implementation. No prompt, budget, retry, gate, parse, repair, or
    # assembly logic is touched — the record rides the candidate into
    # the durable envelope so the harvester can split stage wall from
    # provider wall without inventing sub-phases. Anything unmeasured
    # stays UNATTRIBUTED downstream (never force-fit).
    _t_entry = time.perf_counter()
    _spans = {"abstract_gate_s": 0.0, "prompt_construction_total_s": 0.0,
              "llm_chat_total_s": 0.0, "n_llm_chat_calls": 0,
              "rotation_backoff_sleep_s": 0.0, "parse_total_s": 0.0,
              "span_repair_check_s": 0.0, "candidate_assembly_s": 0.0}

    def _timed_chat(_prompt, system="", max_tokens=512):
        _t0 = time.perf_counter()
        try:
            return llm_chat(_prompt, system=system,
                            max_tokens=max_tokens)
        finally:
            _spans["llm_chat_total_s"] += time.perf_counter() - _t0
            _spans["n_llm_chat_calls"] += 1

    fields = ["MECHANISM", "INTERVENTION", "EXPECTED_EFFECT", "FALSIFICATION_TEST", "MECHANISM_SOURCE_SPAN"]
    _ROTATION_PAPERS = 3          # operational bound, disclosed here
    _ROTATION_BACKOFF_S = (0, 8, 20)  # MODEL_DERIVED operational bound:
    #  the measured flap window is ~1-4 min; 0/8/20 s spreads three real
    #  attempts across it without stretching a run's wall time

    # R483 (the measured production blocker — THREE consecutive runs
    # ended honestly typed INCOMPLETE_INFERENCE_FAILURE but were
    # structurally caused by this): a retrieved record with an EMPTY/short abstract
    # (the geothermal run's doi:10.1186/s40517-019-0138-3 is the
    # canonical specimen: title-only, abstract "") makes the span
    # contract STRUCTURALLY unsatisfiable — there is no abstract text
    # to quote, so the proposer can only cite the title, verify
    # correctly refuses, and the assist has nothing to quote. The
    # claimant-side repair (Art. VII: fix the claimant, never the
    # verifier): the rotation serves only ABSTRACT-BEARING papers; each
    # skipped record is typed and recorded; if NO paper carries a
    # quotable abstract the honest None stands (the run types
    # INCOMPLETE — infrastructure, never a scientific rejection).
    # The floor is the module's DECLARED bound SPAN_ABSTRACT_MIN_CHARS.
    _SPAN_ABSTRACT_MIN_CHARS = SPAN_ABSTRACT_MIN_CHARS

    def _paper_abstract_ok(paper):
        return len(str(paper.get("abstract") or "").strip()) >= \
            _SPAN_ABSTRACT_MIN_CHARS

    _t0 = time.perf_counter()
    _papers_skipped = [
        {"id": p.get("id"), "title": str(p.get("title"))[:120],
         "abstract_chars": len(str(p.get("abstract") or "").strip()),
         "reason": ("SYNTHESIS_PAPER_SKIPPED_NO_ABSTRACT — the record "
                    f"carries < {_SPAN_ABSTRACT_MIN_CHARS} abstract "
                    "chars; the verbatim span contract is structurally "
                    "unsatisfiable against it (R483 gate)")}
        for p in (evidence or []) if not _paper_abstract_ok(p)]
    _spans["abstract_gate_s"] += time.perf_counter() - _t0
    if _papers_skipped:
        print(f"  [synthesize] R483 abstract gate: {len(_papers_skipped)} "
              f"record(s) skipped (no quotable abstract) of "
              f"{len(evidence)} retrieved")
    _t0 = time.perf_counter()
    _rotation_set = [p for p in evidence if _paper_abstract_ok(p)
                     ][:_ROTATION_PAPERS]
    _spans["abstract_gate_s"] += time.perf_counter() - _t0
    if not _rotation_set:
        print("  [synthesize] no abstract-bearing paper in the frozen "
              "evidence — the span contract cannot be served by ANY "
              "record (typed skip, never a silent degraded serve; "
              "Art. XXV)")
        return None

    # R470 (audit P0-5 POWER): the directive constraint from the problem
    # (built at the spawn site from the parent's recorded mechanism
    # identity; the worker persists it and attaches it to the problem).
    # NAMED _dir_* deliberately — problem["constraint"] is the device's
    # engineering constraint and must never be shadowed.
    _dir_constraint = (problem.get("directive_constraint")
                       if isinstance(problem, dict) else None)
    _dir_block = ""
    _dir_record = {"applied": False}
    if (isinstance(_dir_constraint, dict)
            and _dir_constraint.get("forbidden_mechanism")):
        from discovery_fabric.engine.directive_compliance import (
            territory_violation as _territory_violation)
        _dir_block = CONSTRAINT_INSTRUCTION.format(
            forbidden=str(_dir_constraint.get("forbidden_mechanism")))
        _dir_record = {
            "applied": True,
            "version": _dir_constraint.get("version"),
            "verb": _dir_constraint.get("verb"),
            "forbidden_mechanism": _dir_constraint.get(
                "forbidden_mechanism"),
            "violation_detected": False,
            "repair_attempted": False,
            "repair_succeeded": None,
            "violation_final": False,
        }
        print("  [synthesize] directive constraint active (verb "
              f"{_dir_record['verb']}; mechanical compliance check "
              "armed)")

    def _parse_fields(text):
        parsed = {f.lower(): "" for f in fields}
        pattern = re.compile(rf'^({"|".join(fields)})\s*:\s*(.*)$', re.MULTILINE)
        for m in pattern.finditer(text or ""):
            parsed[m.group(1).lower()] = m.group(2).strip()
        return parsed

    papers_tried = []
    for attempt, paper in enumerate(_rotation_set):
        backoff = _ROTATION_BACKOFF_S[attempt] if attempt < len(
            _ROTATION_BACKOFF_S) else 0
        if backoff:
            print(f"  [synthesize] rotation attempt {attempt + 1} after "
                  f"{backoff} s backoff (paper {attempt + 1} of "
                  f"{min(len(evidence), _ROTATION_PAPERS)})")
            _t0 = time.perf_counter()
            time.sleep(backoff)
            _spans["rotation_backoff_sleep_s"] += \
                time.perf_counter() - _t0
        papers_tried.append(paper.get("id"))
        # the engineer's pass-2 F1: the verdict fields reset EVERY
        # candidate iteration — a stale violation from an earlier paper
        # can never ride a later, clean candidate (honest typing)
        _dir_record.update({"violation_detected": False,
                            "repair_attempted": False,
                            "repair_succeeded": None,
                            "violation_final": False})
        _t0 = time.perf_counter()
        prompt = SYNTHESIS_PROMPT.format(
            device=problem["device"], failure=problem["failure"], constraint=problem["constraint"],
            title=paper["title"], abstract=paper["abstract"][:1200],
            span_instruction=SPAN_INSTRUCTION + _dir_block)
        _spans["prompt_construction_total_s"] += time.perf_counter() - _t0
        print(f"  [synthesize] calling LLM (paper {attempt + 1}: "
              f"{str(paper.get('title'))[:60]})...")
        resp = _timed_chat(prompt, system="You are a medical device engineer.")
        if not resp:
            print("  [synthesize] LLM failed on this paper")
            continue
        _t0 = time.perf_counter()
        parsed = _parse_fields(resp)
        _spans["parse_total_s"] += time.perf_counter() - _t0
        # E15 recorded same-provider retry: the MECHANISM_SOURCE_SPAN is the
        # LAST field line and fast endpoints occasionally spend the token cap
        # before emitting it. One retry with a larger budget ON THE SAME
        # provider/model — explicitly recorded in the candidate provenance,
        # never a silent transport change (Art. XXVII).
        retry_note = None
        if parsed.get("intervention") and not parsed.get("mechanism_source_span"):
            retry_note = ("same-provider retry with max_tokens=1024: "
                          "MECHANISM_SOURCE_SPAN missing from the first "
                          "response (token-cap truncation suspected)")
            print("  [synthesize] recorded retry: " + retry_note)
            resp2 = _timed_chat(prompt, system="You are a medical device engineer.",
                                max_tokens=1024)
            if resp2:
                _t0 = time.perf_counter()
                parsed2 = _parse_fields(resp2)
                _spans["parse_total_s"] += time.perf_counter() - _t0
                if (parsed2.get("intervention")
                        and parsed2.get("mechanism_source_span")):
                    resp = resp2
                    parsed = parsed2
                elif parsed2.get("mechanism_source_span"):
                    # keep the retry's span (verbatim) with the first response
                    parsed["mechanism_source_span"] = parsed2[
                        "mechanism_source_span"]
                    resp = resp + "\n" + resp2
        if not parsed.get("intervention"):
            print("  [synthesize] no intervention in response")
            continue

        def _candidate_from(text, parsed):
            return {
                "candidate_id": f"cand:A2:{problem['problem_id']}:{_hash(text[:200])}",
                "problem_id": problem["problem_id"],
                "device": problem["device"],
                "failure_mode": problem["failure_mode"],
                "failure": problem["failure"],
                "constraint": problem["constraint"],
                "mechanism": parsed.get("mechanism", ""),
                "intervention": parsed.get("intervention", ""),
                "expected_effect": parsed.get("expected_effect", ""),
                "falsification_test": parsed.get("falsification_test", ""),
                "mechanism_source_span": parsed.get("mechanism_source_span", ""),
                "source_evidence": {
                    "source_id": paper["id"],
                    "source_hash": paper["content_hash"],
                    "source_title": paper["title"],
                    "source_span": paper["abstract"][:2000],
                    "retrieval_timestamp": paper["retrieval_timestamp"],
                },
                "model": (_LAST_PROVIDER_META.get("model") or FROZEN_MODEL),
                "provider": _LAST_PROVIDER_META.get("provider", "legacy-direct"),
                "transport_status": _LAST_PROVIDER_META.get("status", "UNKNOWN"),
                "prompt_hash": _hash(SYNTHESIS_PROMPT),
                "input_hash": _hash(prompt),
                "output_hash": _hash(text),
                "synthesis_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        _t0 = time.perf_counter()
        candidate = _candidate_from(resp, parsed)
        _spans["candidate_assembly_s"] += time.perf_counter() - _t0
        # R469 evidence-span contract: the mechanical claimant-side
        # repair — the promoted span is the abstract's own characters
        # and verify.py re-checks it byte-exactly (the gate is never
        # loosened; the repair never fires on an already-verbatim span,
        # and provenance records every repair).
        _t0 = time.perf_counter()
        repair_mechanism_span(candidate, paper["abstract"])
        _spans["span_repair_check_s"] += time.perf_counter() - _t0

        # R483 span-format hardening (the second measured failure
        # class, distinct from the empty-abstract gate): the proposer
        # emitted a span line but it is neither verbatim in the served
        # paper's abstract nor mechanically promotable by
        # repair_mechanism_span (no >=8-word verbatim window). The
        # R401 corrective-retry pattern (mechanism_space.py — ONE
        # recorded same-provider retry, defect-specific: the model is
        # shown its own span and the exact defect), claimant-side only
        # (Art. VII: correct the claim, never weaken the verifier —
        # verify.py is untouched). The check uses the SAME two-step
        # ladder a2/verify.py uses (verbatim, then whitespace-normalized
        # case-insensitive) — one contract, Art. X.
        def _span_in_abstract(span, abstract):
            s = str(span or "").strip().strip("\"'").strip()
            if not s:
                return False
            if s in abstract:
                return True
            _n = (lambda t: " ".join(str(t or "").split()).lower())
            return _n(s) in _n(abstract)

        _span_corr_record = None
        _span_src = parsed.get("mechanism_source_span")
        _t0 = time.perf_counter()
        _span_ok = _span_in_abstract(
            candidate.get("mechanism_source_span"),
            paper["abstract"]) if _span_src else True
        _spans["span_repair_check_s"] += time.perf_counter() - _t0
        if _span_src and not _span_ok:
            _corr_note = (
                "R483 span corrective retry: the emitted "
                "MECHANISM_SOURCE_SPAN was not a verbatim substring of "
                "the served paper's abstract (and no >=8-word verbatim "
                "window was promotable); one recorded same-provider "
                "retry with the defect stated")
            print("  [synthesize] " + _corr_note)
            _t0 = time.perf_counter()
            _corr_prompt = (
                prompt + "\n\nCORRECT YOUR PREVIOUS ATTEMPT — its "
                "MECHANISM_SOURCE_SPAN (\"" +
                str(candidate.get("mechanism_source_span"))[:200] +
                "\") is NOT a verbatim substring of THIS abstract; it "
                "was paraphrased or quoted from the wrong part of the "
                "record. Answer again in the SAME format with "
                "MECHANISM_SOURCE_SPAN copied character-for-character "
                "from the ABSTRACT text above (8+ consecutive words "
                "exactly as written; never from the Title line).")
            _spans["prompt_construction_total_s"] += \
                time.perf_counter() - _t0
            _corr_resp = _timed_chat(
                _corr_prompt, system="You are a medical device engineer.",
                max_tokens=1024)
            _t0 = time.perf_counter()
            _corr_parsed = _parse_fields(_corr_resp) if _corr_resp else {}
            _spans["parse_total_s"] += time.perf_counter() - _t0
            _corr_ok = bool(
                _corr_parsed.get("intervention")
                and _corr_parsed.get("mechanism_source_span"))
            if _corr_ok:
                _t0 = time.perf_counter()
                _cand2 = _candidate_from(_corr_resp, _corr_parsed)
                _spans["candidate_assembly_s"] += \
                    time.perf_counter() - _t0
                _t0 = time.perf_counter()
                repair_mechanism_span(_cand2, paper["abstract"])
                _spans["span_repair_check_s"] += \
                    time.perf_counter() - _t0
                _t0 = time.perf_counter()
                _cand2_span_ok = _span_in_abstract(
                    _cand2.get("mechanism_source_span"),
                    paper["abstract"])
                _spans["span_repair_check_s"] += \
                    time.perf_counter() - _t0
                if _cand2_span_ok:
                    _cand2["span_corrective_retry"] = {
                        "attempted": True, "succeeded": True,
                        "note": _corr_note,
                        "original_span": str(
                            candidate.get("mechanism_source_span"))[:200],
                    }
                    _span_corr_record = True
                    candidate = _cand2
            if _span_corr_record is None:
                # the retry did not produce a verbatim span: the
                # ORIGINAL candidate returns unchanged and the typed
                # failure stands downstream (verify + classify — the
                # honest path; the retry is recorded on the candidate)
                candidate["span_corrective_retry"] = {
                    "attempted": True, "succeeded": False,
                    "note": _corr_note,
                    "retry_had_intervention": _corr_ok,
                }
        # R470 (audit P0-5 POWER): the mechanical compliance check — the
        # SAME shared instrument the outcome card uses. On violation: ONE
        # recorded repair retry (the constraint restated, the violating
        # mechanism shown as rejected); a still-violating candidate is
        # returned with violation_final: true — the honest typed state
        # (never hidden, never a fabricated compliance; the ladder's own
        # adversarial gates still judge the candidate independently).
        if _dir_record.get("applied"):
            _terms = _dir_constraint.get("forbidden_terms") or []
            if not _terms:
                # the engineer's pass-2 F2: armed with no terms would be
                # silent false assurance — stated loudly, never silent
                _dir_record["check_skipped"] = "no_forbidden_terms"
                print("  [synthesize] WARNING: directive constraint "
                      "active with ZERO forbidden terms — the "
                      "mechanical check cannot fire (record states it)")
            _t0 = time.perf_counter()
            _tv = _territory_violation(
                candidate.get("mechanism", ""), _terms,
                _dir_constraint.get("threshold")
                if isinstance(_dir_constraint.get("threshold"),
                              (int, float)) else 0.5)
            _spans["candidate_assembly_s"] += time.perf_counter() - _t0
            _dir_record["overlap_ratio"] = _tv["overlap_ratio"]
            _dir_record["overlapping_terms"] = _tv["overlapping_terms"]
            if _tv["violation"]:
                _dir_record["violation_detected"] = True
                _dir_record["repair_attempted"] = True
                print("  [synthesize] directive violation (overlap "
                      f"{_tv['overlap_ratio']}) — one recorded repair "
                      "retry")
                _t0 = time.perf_counter()
                _rej = (
                    prompt + "\n\nCOMPLIANCE REJECTION: your MECHANISM "
                    "restated the explicitly excluded mechanism (\""
                    + str(candidate.get("mechanism", ""))[:300]
                    + "\") — that identity is forbidden this round. "
                    "Answer again in the SAME format; the MECHANISM line "
                    "must be a genuinely different mechanism from THIS "
                    "abstract.")
                _spans["prompt_construction_total_s"] += \
                    time.perf_counter() - _t0
                _resp2 = _timed_chat(_rej,
                                     system="You are a medical device engineer.")
                _t0 = time.perf_counter()
                _parsed2 = _parse_fields(_resp2) if _resp2 else {}
                _spans["parse_total_s"] += time.perf_counter() - _t0
                if _parsed2.get("mechanism"):
                    # the engineer's pass-2 F3: the compliance judgment
                    # gates on the MECHANISM (the thing the directive
                    # excludes), not the intervention line — a retry
                    # with a different mechanism is judged on it
                    _t0 = time.perf_counter()
                    _tv2 = _territory_violation(
                        _parsed2.get("mechanism", ""),
                        _dir_constraint.get("forbidden_terms") or [],
                        _dir_constraint.get("threshold")
                        if isinstance(_dir_constraint.get("threshold"),
                                      (int, float)) else 0.5)
                    _spans["candidate_assembly_s"] += \
                        time.perf_counter() - _t0
                    _dir_record["repaired_overlap_ratio"] = _tv2[
                        "overlap_ratio"]
                    if not _tv2["violation"]:
                        if _parsed2.get("intervention"):
                            _dir_record["repair_succeeded"] = True
                            _t0 = time.perf_counter()
                            candidate = _candidate_from(_resp2, _parsed2)
                            _spans["candidate_assembly_s"] += \
                                time.perf_counter() - _t0
                            _t0 = time.perf_counter()
                            repair_mechanism_span(candidate,
                                                  paper["abstract"])
                            _spans["span_repair_check_s"] += \
                                time.perf_counter() - _t0
                        else:
                            # a compliant mechanism in an unusable
                            # answer: the ORIGINAL (violating)
                            # candidate returns — stated, not softened
                            _dir_record["repair_succeeded"] = False
                            _dir_record["violation_final"] = True
                            _dir_record["retry_mechanism_compliant"] = True
                    else:
                        _dir_record["repair_succeeded"] = False
                        _dir_record["violation_final"] = True
                else:
                    _dir_record["repair_succeeded"] = False
                    _dir_record["violation_final"] = True
            candidate["directive_constraint"] = _dir_record
            _LAST_PROVIDER_META["directive_constraint"] = dict(
                _dir_record)
        if retry_note:
            candidate["synthesis_retry_note"] = retry_note
        if attempt > 0 or len(papers_tried) > 1:
            # R422: the rotation record — WHICH paper produced the candidate
            # and how many real attempts preceded it (provenance, not noise)
            candidate["synthesis_rotation"] = {
                "attempt_index": attempt,
                "papers_tried": papers_tried,
                "evidence_available": len(evidence),
                **({"papers_skipped_no_abstract": _papers_skipped}
                   if _papers_skipped else {}),
                "note": ("candidate produced on a rotated evidence paper "
                         "after earlier synthesis attempts failed — "
                         "recorded, never silent"),
            }
        elif _papers_skipped:
            # R483: the gate's skip record rides even a first-attempt
            # candidate — the skipped records are provenance, not noise
            candidate["synthesis_rotation"] = {
                "attempt_index": attempt,
                "papers_tried": papers_tried,
                "evidence_available": len(evidence),
                "papers_skipped_no_abstract": _papers_skipped,
                "note": ("first eligible paper served; abstract-less "
                         "records skipped by the R483 gate"),
            }
        print(f"  [synthesize] intervention: {candidate['intervention'][:60]}")
        _spans["synthesize_total_s"] = round(
            time.perf_counter() - _t_entry, 6)
        candidate["synthesis_span_timings"] = {
            "instrument": "synth_spans/1.0",
            **{k: (v if k == "n_llm_chat_calls" else round(v, 6))
               for k, v in _spans.items()},
        }
        return candidate
    return None

def parse_candidate(response):
    fields = ["MECHANISM","INTERVENTION","EXPECTED_EFFECT","FALSIFICATION_TEST","MECHANISM_SOURCE_SPAN"]
    parsed = {f.lower(): "" for f in fields}
    pattern = re.compile(rf'^(MECHANISM|INTERVENTION|EXPECTED_EFFECT|FALSIFICATION_TEST|MECHANISM_SOURCE_SPAN)\s*:\s*(.*)$', re.MULTILINE)
    for m in pattern.finditer(response):
        parsed[m.group(1).lower()] = m.group(2).strip()
    return parsed
