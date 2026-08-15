"""A2 synthesize — LLM generates candidate from frozen evidence."""
from __future__ import annotations
import os
import json, re, hashlib, ssl, time, urllib.request
from datetime import datetime, timezone

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

def llm_chat(prompt, system="", max_retries=2, timeout=60):
    messages = []
    if system: messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": FROZEN_MODEL, "messages": messages, "max_tokens": 8000, "temperature": 0.0}
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(OPENROUTER_URL, data=json.dumps(payload).encode(),
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json",
                         "HTTP-Referer": "https://a2-discovery.local", "X-Title": "A2 Discovery"}, method="POST")
            resp = urllib.request.urlopen(req, timeout=timeout, context=_SSL)
            data = json.loads(resp.read())
            if "error" in data:
                if attempt < max_retries: time.sleep(3*(attempt+1)); continue
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if content: time.sleep(0.5); return content
            if attempt < max_retries: time.sleep(3*(attempt+1))
        except:
            if attempt < max_retries: time.sleep(3*(attempt+1))
    return None

def synthesize(problem: dict, evidence: list[dict]) -> dict | None:
    """Step 3: LLM synthesis from frozen evidence."""
    if not evidence:
        print("  [synthesize] no evidence, cannot synthesize")
        return None
    paper = evidence[0]
    prompt = SYNTHESIS_PROMPT.format(
        device=problem["device"], failure=problem["failure"], constraint=problem["constraint"],
        title=paper["title"], abstract=paper["abstract"][:1200])
    print(f"  [synthesize] calling LLM...")
    resp = llm_chat(prompt, system="You are a medical device engineer.")
    if not resp:
        print("  [synthesize] LLM failed")
        return None

    fields = ["MECHANISM", "INTERVENTION", "EXPECTED_EFFECT", "FALSIFICATION_TEST", "MECHANISM_SOURCE_SPAN"]
    parsed = {f.lower(): "" for f in fields}
    pattern = re.compile(rf'^({"|".join(fields)})\s*:\s*(.*)$', re.MULTILINE)
    for m in pattern.finditer(resp):
        parsed[m.group(1).lower()] = m.group(2).strip()
    if not parsed.get("intervention"):
        print("  [synthesize] no intervention in response")
        return None

    candidate = {
        "candidate_id": f"cand:A2:{problem['problem_id']}:{_hash(resp[:200])}",
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
        "model": FROZEN_MODEL,
        "prompt_hash": _hash(SYNTHESIS_PROMPT),
        "input_hash": _hash(prompt),
        "output_hash": _hash(resp),
        "synthesis_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    print(f"  [synthesize] intervention: {candidate['intervention'][:60]}")
    return candidate

def parse_candidate(response):
    fields = ["MECHANISM","INTERVENTION","EXPECTED_EFFECT","FALSIFICATION_TEST","MECHANISM_SOURCE_SPAN"]
    parsed = {f.lower(): "" for f in fields}
    pattern = re.compile(rf'^(MECHANISM|INTERVENTION|EXPECTED_EFFECT|FALSIFICATION_TEST|MECHANISM_SOURCE_SPAN)\s*:\s*(.*)$', re.MULTILINE)
    for m in pattern.finditer(response):
        parsed[m.group(1).lower()] = m.group(2).strip()
    return parsed
