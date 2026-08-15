"""A2 adversarial — adversarial challenge."""
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

ATTACK_PROMPT = """You are an adversarial reviewer for medical device invention candidates.

Attack this candidate on the following dimensions. For each, respond PASS (survives) or KILLED (fails):

1. UNSUPPORTED_MECHANISM: Is the mechanism unsupported by evidence?
2. WEAK_TRANSFER: Is the transfer from source to device weak or superficial?
3. OBVIOUS_COMBINATION: Is this an obvious combination of known techniques?
4. PRIOR_ART: Does this appear to be already known?
5. CONTRADICTION: Does the evidence contradict the claim?
6. BOUNDARY_FAILURE: Are boundary conditions missing or violated?
7. ENGINEERING_INFEASIBILITY: Is this engineering-infeasible?
8. REGULATORY_INCOMPATIBILITY: Would this face regulatory barriers?

Candidate (arm hidden):
{candidate_json}

Respond (each on ONE line):
UNSUPPORTED_MECHANISM: PASS | KILLED
WEAK_TRANSFER: PASS | KILLED
OBVIOUS_COMBINATION: PASS | KILLED
PRIOR_ART: PASS | KILLED
CONTRADICTION: PASS | KILLED
BOUNDARY_FAILURE: PASS | KILLED
ENGINEERING_INFEASIBILITY: PASS | KILLED
REGULATORY_INCOMPATIBILITY: PASS | KILLED
OVERALL: PASS | KILLED
REASON: <one sentence>
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
                         "HTTP-Referer": "https://a2-adversarial.local", "X-Title": "A2 Adversarial"}, method="POST")
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

def adversarial_challenge(candidate: dict) -> dict:
    """Step 6: Adversarial challenge."""
    # Strip evaluation fields (Defect A fix)
    STRIP = {"candidate_id", "model", "prompt_hash", "input_hash", "output_hash", "synthesis_timestamp"}
    blinded = {k: v for k, v in candidate.items() if k not in STRIP}
    prompt = ATTACK_PROMPT.format(candidate_json=json.dumps(blinded, indent=2, default=str))
    print(f"  [adversarial] challenging candidate...")
    resp = llm_chat(prompt, system="You are a strict adversarial reviewer.")
    if not resp:
        return {"overall": "KILLED", "reason": "LLM failed", "attacks": {}}

    fields = ["UNSUPPORTED_MECHANISM", "WEAK_TRANSFER", "OBVIOUS_COMBINATION", "PRIOR_ART",
              "CONTRADICTION", "BOUNDARY_FAILURE", "ENGINEERING_INFEASIBILITY",
              "REGULATORY_INCOMPATIBILITY", "OVERALL"]
    parsed = {f.lower(): "" for f in fields}
    pattern = re.compile(rf'^({"|".join(fields)})\s*:\s*(.*)$', re.MULTILINE)
    for m in pattern.finditer(resp):
        parsed[m.group(1).lower()] = m.group(2).strip()

    overall = "PASS" if "PASS" in parsed.get("overall", "") else "KILLED"
    killed_count = sum(1 for f in fields[:-1] if "KILLED" in parsed.get(f.lower(), ""))

    result = {
        "overall": overall,
        "killed_count": killed_count,
        "reason": parsed.get("reason", ""),
        "attacks": {f.lower(): parsed.get(f.lower(), "UNKNOWN") for f in fields[:-1]},
        "prompt_hash": _hash(ATTACK_PROMPT),
        "output_hash": _hash(resp),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    print(f"  [adversarial] overall={overall} killed={killed_count}")
    return result
