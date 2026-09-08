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
MECHANISM_SOURCE_SPAN: <verbatim substring from abstract supporting MECHANISM>
"""

def _hash(s): return hashlib.sha256(s.encode()).hexdigest()[:16]

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
        policy = reg.SelectionPolicy(
            preferred_providers=[override], max_preference_fallback=0,
            purpose="synthesis")
    else:
        policy = reg.SelectionPolicy(
            preferred_providers=["openrouter", "deepseek", "anthropic",
                                 "openai", "gemini", "qwen", "nvidia"],
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

    fields = ["MECHANISM", "INTERVENTION", "EXPECTED_EFFECT", "FALSIFICATION_TEST", "MECHANISM_SOURCE_SPAN"]
    _ROTATION_PAPERS = 3          # operational bound, disclosed here
    _ROTATION_BACKOFF_S = (0, 8, 20)  # MODEL_DERIVED operational bound:
    #  the measured flap window is ~1-4 min; 0/8/20 s spreads three real
    #  attempts across it without stretching a run's wall time

    def _parse_fields(text):
        parsed = {f.lower(): "" for f in fields}
        pattern = re.compile(rf'^({"|".join(fields)})\s*:\s*(.*)$', re.MULTILINE)
        for m in pattern.finditer(text or ""):
            parsed[m.group(1).lower()] = m.group(2).strip()
        return parsed

    papers_tried = []
    for attempt, paper in enumerate(evidence[:_ROTATION_PAPERS]):
        backoff = _ROTATION_BACKOFF_S[attempt] if attempt < len(
            _ROTATION_BACKOFF_S) else 0
        if backoff:
            print(f"  [synthesize] rotation attempt {attempt + 1} after "
                  f"{backoff} s backoff (paper {attempt + 1} of "
                  f"{min(len(evidence), _ROTATION_PAPERS)})")
            time.sleep(backoff)
        papers_tried.append(paper.get("id"))
        prompt = SYNTHESIS_PROMPT.format(
            device=problem["device"], failure=problem["failure"], constraint=problem["constraint"],
            title=paper["title"], abstract=paper["abstract"][:1200])
        print(f"  [synthesize] calling LLM (paper {attempt + 1}: "
              f"{str(paper.get('title'))[:60]})...")
        resp = llm_chat(prompt, system="You are a medical device engineer.")
        if not resp:
            print("  [synthesize] LLM failed on this paper")
            continue
        parsed = _parse_fields(resp)
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
            resp2 = llm_chat(prompt, system="You are a medical device engineer.",
                             max_tokens=1024)
            if resp2:
                parsed2 = _parse_fields(resp2)
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
        candidate = _candidate_from(resp, parsed)
        if retry_note:
            candidate["synthesis_retry_note"] = retry_note
        if attempt > 0 or len(papers_tried) > 1:
            # R422: the rotation record — WHICH paper produced the candidate
            # and how many real attempts preceded it (provenance, not noise)
            candidate["synthesis_rotation"] = {
                "attempt_index": attempt,
                "papers_tried": papers_tried,
                "evidence_available": len(evidence),
                "note": ("candidate produced on a rotated evidence paper "
                         "after earlier synthesis attempts failed — "
                         "recorded, never silent"),
            }
        print(f"  [synthesize] intervention: {candidate['intervention'][:60]}")
        return candidate
    return None

def parse_candidate(response):
    fields = ["MECHANISM","INTERVENTION","EXPECTED_EFFECT","FALSIFICATION_TEST","MECHANISM_SOURCE_SPAN"]
    parsed = {f.lower(): "" for f in fields}
    pattern = re.compile(rf'^(MECHANISM|INTERVENTION|EXPECTED_EFFECT|FALSIFICATION_TEST|MECHANISM_SOURCE_SPAN)\s*:\s*(.*)$', re.MULTILINE)
    for m in pattern.finditer(response):
        parsed[m.group(1).lower()] = m.group(2).strip()
    return parsed
