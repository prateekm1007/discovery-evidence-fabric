"""A2 adversarial — adversarial challenge with V4 corrections wired in.

PRODUCTION PATH (corrected):
  candidate
  → evidence gate (skip_if_evidence_failed)
  → prior-art state (from frozen prior-art subsystem)
  → LLM adversarial challenge
  → V4 corrections:
      - enforce_prior_art_firewall (non-kill states cannot become PRIOR_ART=KILL)
      - evaluate_boundary_condition (external evidence required for BOUNDARY KILL)
      - check_adversarial_invalid (verdict/reason conflicts → ADVERSARIAL_INVALID)
  → corrected dimension verdicts
  → AIC gate

There is ONE authoritative implementation of each correction:
  discovery_fabric.v4_corrections

This module imports and delegates to it. No duplicated logic.
"""
from __future__ import annotations
import os
import json, re, hashlib, ssl, time, urllib.request
from datetime import datetime, timezone

# ===== V4 CORRECTIONS (authoritative implementation) =====
from discovery_fabric.v4_corrections import (
    skip_if_evidence_failed,
    evaluate_boundary_condition,
    enforce_prior_art_firewall,
    check_adversarial_invalid,
    resolve_boundary_evidence,
    NON_KILL_PRIOR_ART_STATES,
    KILL_PRIOR_ART_STATES,
)

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

def llm_chat(prompt, system="", max_retries=1, timeout=30):
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


def adversarial_challenge(candidate: dict, evidence_verified: bool = True,
                          prior_art_state: str = "UNKNOWN") -> dict:
    """Step 6: Adversarial challenge with V4 corrections.

    PRODUCTION PATH:
      1. Evidence gate: skip_if_evidence_failed()
      2. LLM adversarial challenge
      3. V4 corrections on each dimension:
         - enforce_prior_art_firewall() on PRIOR_ART dimension
         - evaluate_boundary_condition() on BOUNDARY_FAILURE dimension
         - check_adversarial_invalid() on all dimensions
      4. Corrected dimension verdicts
      5. AIC gate

    Args:
        candidate: The candidate to evaluate.
        evidence_verified: Whether evidence verification passed. If False, adversarial is NOT_RUN.
        prior_art_state: The frozen prior-art state from the prior-art subsystem.
            Must be one of: NO_MATCH_FOUND, TOPICAL_RELATED, POSSIBLE_RELEVANCE,
            UNRESOLVED_INSUFFICIENT_EVIDENCE, SPECIFIC_DISCLOSURE,
            IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE.
    """
    # ===== V4 CORRECTION 11: Evidence gate =====
    # If evidence fails, adversarial MUST NOT run.
    evidence_gate = skip_if_evidence_failed(evidence_verified)
    if not evidence_gate["adversarial_should_run"]:
        return {
            "overall": "NOT_RUN",
            "adversarial_status": "NOT_RUN",
            "adversarial_not_run_reason": evidence_gate["adversarial_not_run_reason"],
            "attacks": {},
            "killed_count": 0,
            "v4_corrections_applied": ["evidence_gate_skip"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ===== LLM adversarial challenge =====
    STRIP = {"candidate_id", "model", "prompt_hash", "input_hash", "output_hash", "synthesis_timestamp"}
    blinded = {k: v for k, v in candidate.items() if k not in STRIP}
    prompt = ATTACK_PROMPT.format(candidate_json=json.dumps(blinded, indent=2, default=str))
    print(f"  [adversarial] challenging candidate...")
    resp = llm_chat(prompt, system="You are a strict adversarial reviewer.")
    if not resp:
        # DEFECT FIX: LLM failure must NEVER become KILL.
        # This is an operational failure, not a scientific verdict.
        return {
            "overall": "EVALUATOR_CALL_FAILED",
            "adversarial_status": "EVALUATOR_CALL_FAILED",
            "reason": "LLM call failed (timeout, rate limit, or error)",
            "attacks": {},
            "killed_count": 0,
            "v4_corrections_applied": [],
            "is_scientific_verdict": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    fields = ["UNSUPPORTED_MECHANISM", "WEAK_TRANSFER", "OBVIOUS_COMBINATION", "PRIOR_ART",
              "CONTRADICTION", "BOUNDARY_FAILURE", "ENGINEERING_INFEASIBILITY",
              "REGULATORY_INCOMPATIBILITY", "OVERALL"]
    parsed = {f.lower(): "" for f in fields}
    pattern = re.compile(rf'^({"|".join(fields)})\s*:\s*(.*)$', re.MULTILINE)
    for m in pattern.finditer(resp):
        parsed[m.group(1).lower()] = m.group(2).strip()

    # ===== V4 CORRECTIONS on parsed verdicts =====
    v4_corrections_applied = []
    corrected_attacks = {}
    invalid_dimensions = []

    for field in fields[:-1]:  # skip OVERALL
        dim_name = field.lower()
        raw_verdict = parsed.get(dim_name, "UNKNOWN")
        is_killed = "KILLED" in raw_verdict.upper()
        reason = raw_verdict

        # Map A2 dimension names to V4 correction dimension names
        v4_dim_name = None
        if dim_name == "prior_art":
            v4_dim_name = "PRIOR_ART"
        elif dim_name == "boundary_failure":
            v4_dim_name = "BOUNDARY_CONDITION"

        # V4 CORRECTION 10: Prior-art firewall
        if v4_dim_name == "PRIOR_ART" and is_killed:
            fw = enforce_prior_art_firewall(prior_art_state, "KILL", "PRIOR_ART")
            if fw["firewall_applied"]:
                is_killed = False
                raw_verdict = f"SURVIVE (firewall: {fw['reason']})"
                v4_corrections_applied.append(f"prior_art_firewall:{fw['action']}")

        # V4 CORRECTION 5+9: Boundary condition evidence standard
        # Resolve external boundary evidence from the candidate's evidence packet
        if v4_dim_name == "BOUNDARY_CONDITION" and is_killed:
            # DEFECT FIX: resolve real external evidence, don't pass None
            external_evidence = resolve_boundary_evidence(candidate)
            bc = evaluate_boundary_condition(reason, external_evidence=external_evidence)
            if not bc["valid"]:
                is_killed = False
                raw_verdict = f"INSUFFICIENT_EVIDENCE ({bc['disposition']})"
                v4_corrections_applied.append(f"boundary_evidence:{bc['disposition']}")

        # V4 CORRECTION 6: Adversarial invalid check
        verdict_str = "KILL" if is_killed else "SURVIVE"
        invalid_check = check_adversarial_invalid(verdict_str, reason, True, prior_art_state)
        if invalid_check["disposition"] == "ADVERSARIAL_INVALID":
            invalid_dimensions.append({
                "dimension": dim_name,
                "invalid_reason": invalid_check["invalid_reason"],
            })
            v4_corrections_applied.append(f"adversarial_invalid:{dim_name}")
            # ADVERSARIAL_INVALID → not KILL, not SURVIVE, requires re-evaluation
            raw_verdict = f"ADVERSARIAL_INVALID ({invalid_check['invalid_reason'][:50]})"

        corrected_attacks[dim_name] = raw_verdict

    # ===== Compute corrected overall =====
    # If any dimension is still KILLED (after corrections), overall is KILLED
    # If any dimension is ADVERSARIAL_INVALID, overall is EVALUATION_FAILED
    any_killed = any("KILLED" in v.upper() and "ADVERSARIAL_INVALID" not in v.upper()
                     for v in corrected_attacks.values())
    any_invalid = len(invalid_dimensions) > 0

    if any_invalid:
        overall = "EVALUATION_FAILED"
    elif any_killed:
        overall = "KILLED"
    else:
        overall = "PASS"

    killed_count = sum(1 for v in corrected_attacks.values()
                       if "KILLED" in v.upper() and "ADVERSARIAL_INVALID" not in v.upper())

    result = {
        "overall": overall,
        "killed_count": killed_count,
        "reason": parsed.get("reason", ""),
        "attacks": corrected_attacks,
        "invalid_dimensions": invalid_dimensions,
        "v4_corrections_applied": v4_corrections_applied,
        "prior_art_state": prior_art_state,
        "evidence_verified": evidence_verified,
        "prompt_hash": _hash(ATTACK_PROMPT),
        "output_hash": _hash(resp),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    print(f"  [adversarial] overall={overall} killed={killed_count} corrections={len(v4_corrections_applied)}")
    return result
