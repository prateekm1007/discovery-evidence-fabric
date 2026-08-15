#!/usr/bin/env python3
"""
INVENTION SYNTHESIS ENGINE V1 — the missing TEE stage.

This component does NOT exist in the TEE repository (CAPABILITY_STATUS.md
explicitly states: "Invention synthesis: ❌ NOT IMPLEMENTED"). This module
builds it.

Takes ONE REPLAY_AIC candidate at a time and transforms it through:

  AIC
    → Pass 1: mechanism reconstruction
    → Pass 2: mechanism expansion (3-5 materially different mechanisms)
    → Pass 3: competing invention architectures (3-5)
    → Pass 4: adversarial elimination
    → Pass 5: refinement (generation → attack → refinement → attack)
    → prediction generation
    → experiment design
    → final INVENTION_CANDIDATE

A paraphrase is a FAILURE. The engine must discover the engineering
architecture that makes the intervention substantially better.

Contracts followed (from TEE substrate):
  - Hypothesis: requires falsifier (non-empty)
  - Prediction: observable, baseline, expected_direction, expected_magnitude,
    conditions, uncertainty, falsifier
  - Experiment: controls (REQUIRED), falsification_condition (REQUIRED),
    cost, duration, information_gain
  - Prior-art: NO_MATCH_FOUND / ADJACENT_PRIOR_ART / SPECIFIC_DISCLOSURE / UNRESOLVED
    (never NOVEL)
  - Epistemic state: INVENTION_CANDIDATE / REFINEMENT_EXHAUSTED / KILLED

Parameter provenance: every numerical parameter tagged
  EVIDENCE_DERIVED / ENGINEERING_DERIVED / HYPOTHESIS / UNKNOWN
"""
from __future__ import annotations
import json, os, sys, time, ssl, hashlib, re, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ===== ROUTING (frozen V1 policy + z-ai GLM-4-plus as primary) =====
# Mistral is rate-limited (402), NVIDIA is slow (~110s/call).
# z-ai GLM-4-plus is fast and available, used as primary.
# The routing policy V1 SHA is preserved for provenance; the actual model
# used is recorded per-call in provider_call_manifests.

MISTRAL_KEY = os.environ.get("MISTRAL_API_KEY", "UsFQXJwSnuO9jaWJLw9eNKyStuwZ0BDs")
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
NVIDIA_KEY = os.environ.get("NVIDIA_API_KEY", "REDACTED-NVIDIA-KEY")
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL = "deepseek-ai/deepseek-v4-flash-0731"
MISTRAL_PRIMARY = "mistral-medium-latest"

# z-ai (GLM-4-plus) — used as primary due to Mistral rate-limit and NVIDIA latency
ZAI_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
ZAI_KEY = os.environ.get("ZAI_API_KEY", "")  # z-ai CLI handles auth
ZAI_MODEL = "glm-4-plus"

ROUTING_POLICY_SHA = "79a928166bce6fb9faf2368c9aba2ffc9f1aaeacc4e73bbade25218d4f76470d"

_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE

PER_CALL_RETRIES = 1
PER_CALL_TIMEOUT = 120


def _zai_call(prompt, max_tokens=2000):
    """Call z-ai (GLM-4-plus) via the CLI. Writes prompt to file to avoid shell escaping."""
    import subprocess, tempfile
    tmp_prompt = None
    tmp_out = None
    try:
        # Write prompt to temp file to avoid shell escaping issues with long prompts
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(prompt)
            tmp_prompt = f.name
        tmp_out = tmp_prompt + '.out.json'

        # Use --prompt with file content read via $(cat) alternative: just pass the prompt directly
        # but limit to reasonable size
        result = subprocess.run(
            ['z-ai', 'chat', '-p', prompt[:8000], '-o', tmp_out],
            timeout=PER_CALL_TIMEOUT, capture_output=True, text=True
        )
        if result.returncode != 0:
            return None, "unknown", "unknown", "ZAI_FAILED", {}
        with open(tmp_out) as f:
            data = json.load(f)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if content:
            usage = data.get("usage", {})
            return content, ZAI_MODEL, "ZAI", "ZAI_PRIMARY", {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
            }
    except subprocess.TimeoutExpired:
        return None, "unknown", "unknown", "ZAI_TIMEOUT", {}
    except Exception:
        pass
    finally:
        for p in [tmp_prompt, tmp_out]:
            if p and os.path.exists(p):
                try: os.unlink(p)
                except: pass
    return None, "unknown", "unknown", "ZAI_FAILED", {}

def _mistral_call(prompt, max_tokens=2000):
    payload = {"model": MISTRAL_PRIMARY, "messages":[{"role":"user","content":prompt}],
               "max_tokens": max_tokens, "temperature": 0.0}
    for attempt in range(PER_CALL_RETRIES):
        try:
            req = urllib.request.Request(MISTRAL_URL, data=json.dumps(payload).encode(),
                headers={"Authorization": f"Bearer {MISTRAL_KEY}", "Content-Type":"application/json"})
            resp = urllib.request.urlopen(req, timeout=PER_CALL_TIMEOUT, context=_SSL)
            data = json.loads(resp.read())
            content = data.get("choices",[{}])[0].get("message",{}).get("content","")
            if content:
                usage = data.get("usage", {})
                return content, MISTRAL_PRIMARY, "Mistral", "MISTRAL_PRIMARY", {
                    "input_tokens": usage.get("prompt_tokens", 0),
                    "output_tokens": usage.get("completion_tokens", 0),
                }
        except Exception:
            if attempt < PER_CALL_RETRIES - 1: time.sleep(3)
    return None, "unknown", "unknown", "MISTRAL_FAILED", {}

def _nvidia_call(prompt, max_tokens=2000):
    payload = {"model": NVIDIA_MODEL, "messages":[{"role":"user","content":prompt}],
               "max_tokens": max_tokens, "temperature": 0.0}
    for attempt in range(PER_CALL_RETRIES):
        try:
            req = urllib.request.Request(NVIDIA_URL, data=json.dumps(payload).encode(),
                headers={"Authorization": f"Bearer {NVIDIA_KEY}",
                         "Content-Type":"application/json", "Accept":"application/json"})
            resp = urllib.request.urlopen(req, timeout=PER_CALL_TIMEOUT, context=_SSL)
            data = json.loads(resp.read())
            content = data.get("choices",[{}])[0].get("message",{}).get("content","")
            if content:
                return content, NVIDIA_MODEL, "NVIDIA", "NVIDIA_FALLBACK", {}
        except Exception:
            if attempt < PER_CALL_RETRIES - 1: time.sleep(3)
    return None, "unknown", "unknown", "NVIDIA_FAILED", {}

def routed_call(prompt, max_tokens=2000):
    """Routing order: z-ai (primary) → Mistral → NVIDIA (fallback)."""
    # Primary: z-ai (GLM-4-plus)
    content, model, provider, reason, usage = _zai_call(prompt, max_tokens)
    if content:
        return content, model, provider, reason, usage
    # Fallback 1: Mistral
    content, model, provider, reason, usage = _mistral_call(prompt, max_tokens)
    if content:
        return content, model, provider, reason, usage
    # Fallback 2: NVIDIA
    return _nvidia_call(prompt, max_tokens)


# ===== PROMPT TEMPLATES =====

PASS1_RECONSTRUCT = """You are an invention synthesis engine. Reconstruct the problem space for this AIC.

AIC:
- Device: {device}
- Failure: {failure}
- Failure Mode: {failure_mode}
- Proposed Modification: {modification}
- Mechanistic Reasoning: {reasoning}
- Falsification Test: {ftest}

TASK: Reconstruct the problem space. Answer:
1. What exactly is the failure?
2. What causal mechanism produces it?
3. What does the current device do?
4. Where does it fail?
5. Which constraint blocks the obvious solution?

Respond in EXACTLY this JSON format:
{{
  "failure_definition": "<precise definition>",
  "causal_mechanism": "<what causes the failure>",
  "current_device_behavior": "<what the device currently does>",
  "failure_point": "<where exactly it fails>",
  "blocking_constraint": "<what blocks the obvious solution>"
}}"""

PASS2_MECHANISM_EXPANSION = """You are an invention synthesis engine. Generate 3-5 MATERIALLY DIFFERENT mechanisms capable of improving this AIC. They must NOT be synonyms.

AIC:
- Device: {device}
- Failure: {failure}
- Proposed Modification: {modification}
- Causal Mechanism: {causal_mechanism}
- Blocking Constraint: {blocking_constraint}

Generate 3-5 mechanisms from DIFFERENT engineering domains. Examples of different mechanism families:
  - passive structural reinforcement
  - active sensing/control
  - material-state transition
  - interface modification
  - energy redistribution

Respond in EXACTLY this JSON format:
{{
  "mechanisms": [
    {{
      "id": "MECH_A",
      "family": "<passive structural / active sensing / material-state / interface / energy>",
      "mechanism": "<specific mechanism>",
      "how_it_addresses_failure": "<causal explanation>",
      "key_components": ["component1", "component2"],
      "falsifier": "<what observation would prove this mechanism wrong>"
    }}
  ]
}}"""

PASS3_ARCHITECTURES = """You are an invention synthesis engine. Generate 3-5 competing invention architectures for this AIC.

AIC:
- Device: {device}
- Failure: {failure}
- Proposed Modification: {modification}

Available mechanisms:
{mechanisms_json}

TASK: For each mechanism, design a concrete invention architecture. Each architecture must have:
  - structure (physical layout)
  - mechanism (how it works)
  - components (named parts)
  - interaction (how components interact)
  - operating_condition (when it operates)
  - failure_containment (how it contains its own failure modes)
  - inventive_nucleus (one sentence: what exactly is the inventive thing?)

The inventive nucleus must be SPECIFIC, not vague. Example:
GOOD: "A co-located, electrically isolated state-transition reference element that estimates local treatment exposure and normalizes a treatment-site signal before adaptive energy control."
BAD: "An improved electrosurgical system."

Respond in EXACTLY this JSON format:
{{
  "architectures": [
    {{
      "id": "ARCH_A",
      "mechanism_id": "MECH_A",
      "inventive_nucleus": "<one specific sentence>",
      "structure": "<physical layout>",
      "components": ["comp1", "comp2"],
      "interfaces": ["interface1"],
      "materials": ["material1"],
      "control_logic": ["logic step1"],
      "interaction": "<how components interact>",
      "operating_condition": "<when it operates>",
      "failure_containment": "<how it contains failures>",
      "expected_effect": "<what it achieves>",
      "causal_chain": ["step1", "step2", "step3", "step4", "step5", "step6"]
    }}
  ]
}}"""

PASS4_ADVERSARIAL = """You are an adversarial reviewer for invention architectures. Attack each architecture across 7 dimensions.

Architecture:
{arch_json}

For each dimension, respond KILL or SURVIVE with a specific reason:
1. MECHANISM_VALIDITY: Could the mechanism physically work?
2. TRANSFER_LEGITIMACY: Is the transfer justified?
3. BOUNDARY_CONDITION: Where does it fail? (require specific boundary)
4. OBVIOUSNESS: Would an expert naturally combine these elements?
5. PRIOR_ART_RISK: Does an existing reference disclose the same nucleus?
6. ENGINEERING_FEASIBILITY: Can it actually be built?
7. FALSIFIABILITY: What experiment could kill it?

Respond in EXACTLY this JSON format:
{{
  "attacks": [
    {{
      "dimension": "MECHANISM_VALIDITY",
      "verdict": "KILL or SURVIVE",
      "reason": "<specific reason>",
      "evidence_required": "<what evidence would be needed to support this verdict>"
    }}
  ],
  "overall": "KILLED or SURVIVED",
  "killed_dimensions": ["list of killed dimensions"],
  "refinement_needed": "<if KILLED, what should be refined? empty if SURVIVED>"
}}"""

PASS5_REFINEMENT = """You are an invention refinement engine. Refine this architecture to address the adversarial attacks.

Original architecture:
{arch_json}

Adversarial attacks:
{attacks_json}

TASK: Refine the architecture to address each KILL. Do NOT just restate the original.
- Identify KNOWN_ELEMENTS (what's already known)
- Identify NEW_RELATIONSHIP (what new relationship is proposed)
- Identify NEW_CONFIGURATION (what new configuration is proposed)
- Identify NEW_CONTROL_RULE (what new control rule is proposed)
- The inventive step is the RELATIONSHIP/CONFIGURATION/CONTROL_RULE, not the known elements.

Respond in EXACTLY this JSON format:
{{
  "refined_nucleus": "<one specific sentence>",
  "known_elements": ["element1", "element2"],
  "new_relationship": "<the new relationship that creates technical effect>",
  "new_configuration": "<the new configuration>",
  "new_control_rule": "<the new control rule>",
  "refined_structure": "<refined physical layout>",
  "refined_components": ["comp1", "comp2"],
  "refined_causal_chain": ["step1", "step2", "step3", "step4", "step5", "step6"],
  "addresses_attacks": ["which attacks are addressed and how"],
  "remaining_risks": ["unresolved risks"]
}}"""

PREDICTION_PROMPT = """You are a scientific prediction engine. Given this invention, produce a SPECIFIC, falsifiable prediction.

Invention:
- Nucleus: {nucleus}
- Mechanism: {mechanism}
- Expected Effect: {effect}

Required (all fields mandatory):
  - observable: what to measure (a concrete quantity)
  - baseline: comparison baseline
  - expected_direction: increase/decrease/appear/disappear/etc.
  - expected_magnitude: estimated size (e.g. "10-30% improvement")
  - conditions: under what conditions
  - uncertainty: number in [0,1]
  - falsifier: what observation would refute — REQUIRED, non-empty

Respond in EXACTLY this JSON format:
{{
  "predictions": [
    {{
      "observable": "<what to measure>",
      "baseline": "<comparison baseline>",
      "expected_direction": "<increase/decrease/etc>",
      "expected_magnitude": "<estimated size>",
      "conditions": "<under what conditions>",
      "uncertainty": <number 0-1>,
      "falsifier": "<what observation would refute>"
    }}
  ]
}}"""

EXPERIMENT_PROMPT = """You are an experiment design engine. Design a controlled experiment for this invention.

Invention:
- Nucleus: {nucleus}
- Mechanism: {mechanism}
- Predictions: {predictions_json}

Required (all fields mandatory, controls and falsification are REQUIRED):
  - objective: what the experiment tests
  - independent_variables: what you vary
  - dependent_variables: what you measure
  - controls: control conditions (REQUIRED, non-empty)
  - baseline: comparison baseline
  - procedure: step-by-step protocol
  - expected_result: what you expect to see
  - falsification_condition: what result would falsify (REQUIRED, non-empty)
  - sample_requirements: how many samples/subjects
  - safety_constraints: safety considerations
  - estimated_cost: rough cost estimate
  - estimated_duration: time estimate
  - information_gain: what you learn from the experiment

Respond in EXACTLY this JSON format:
{{
  "experiment": {{
    "objective": "<objective>",
    "independent_variables": ["var1", "var2"],
    "dependent_variables": ["var1", "var2"],
    "controls": ["control1", "control2"],
    "baseline": "<baseline>",
    "procedure": ["step1", "step2", "step3"],
    "expected_result": "<expected>",
    "falsification_condition": "<what falsifies>",
    "sample_requirements": "<samples>",
    "safety_constraints": "<safety>",
    "estimated_cost": "<cost>",
    "estimated_duration": "<duration>",
    "information_gain": "<what you learn>"
  }}
}}"""

PRIOR_ART_PROMPT = """You are a prior-art analysis engine. Assess the prior-art risk for this invention nucleus.

Invention Nucleus: {nucleus}

Do NOT call this novel. Classify as:
  - NO_MATCH_FOUND: no match in searched universe (NOT the same as novel)
  - ADJACENT_PRIOR_ART: related prior art exists but doesn't disclose the exact nucleus
  - SPECIFIC_DISCLOSURE_RISK: a specific reference likely discloses the same nucleus
  - UNRESOLVED: cannot determine without a formal search

Identify:
  - known_elements: what's already known in the field
  - adjacent_references: related prior art (describe generally, no fabricated citations)
  - inventive_step: what makes the nucleus potentially different from known art

Respond in EXACTLY this JSON format:
{{
  "prior_art_assessment": {{
    "classification": "NO_MATCH_FOUND or ADJACENT_PRIOR_ART or SPECIFIC_DISCLOSURE_RISK or UNRESOLVED",
    "known_elements": ["element1", "element2"],
    "adjacent_references": ["reference description1"],
    "inventive_step": "<what makes the nucleus potentially different>",
    "search_universe_limitation": "<what was NOT searched>"
  }}
}}"""


def _hash(s):
    return hashlib.sha256(s.encode()).hexdigest()[:16]

def _try_parse_json(content):
    """Try to extract JSON from LLM response (may have markdown fences)."""
    if not content:
        return None
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', content)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None


def synthesize_invention(aic: dict, seed_id: str) -> dict:
    """Transform one AIC into an INVENTION_CANDIDATE through 5 passes."""
    t0 = time.time()
    manifests = []
    refinement_history = []

    device = aic.get("device_class", "")
    failure = aic.get("documented_failure", "")
    failure_mode = aic.get("failure_mode", "")
    modification = aic.get("proposed_modification", "")
    reasoning = aic.get("mechanistic_reasoning", "")
    ftest = aic.get("falsification_test", "")

    # ===== PASS 1: RECONSTRUCT =====
    prompt = PASS1_RECONSTRUCT.format(
        device=device, failure=failure, failure_mode=failure_mode,
        modification=modification, reasoning=reasoning[:500], ftest=ftest[:300])
    content, model, provider, reason, usage = routed_call(prompt)
    response_hash_1 = _hash(content or "")
    manifests.append({
        "pass": "pass1_reconstruct", "provider": provider, "model": model,
        "routing_reason": reason, "response_hash": response_hash_1,
        "input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    reconstruction = _try_parse_json(content) or {}
    if not reconstruction:
        return _failed_invention(aic, seed_id, "PASS1_RECONSTRUCT_FAILED", manifests, refinement_history, t0)

    # ===== PASS 2: MECHANISM EXPANSION =====
    prompt = PASS2_MECHANISM_EXPANSION.format(
        device=device, failure=failure, modification=modification,
        causal_mechanism=reconstruction.get("causal_mechanism", ""),
        blocking_constraint=reconstruction.get("blocking_constraint", ""))
    content, model, provider, reason, usage = routed_call(prompt)
    response_hash_2 = _hash(content or "")
    manifests.append({
        "pass": "pass2_mechanism_expansion", "provider": provider, "model": model,
        "routing_reason": reason, "response_hash": response_hash_2,
        "input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    mech_result = _try_parse_json(content) or {}
    mechanisms = mech_result.get("mechanisms", [])
    if not mechanisms:
        return _failed_invention(aic, seed_id, "PASS2_NO_MECHANISMS", manifests, refinement_history, t0)

    # ===== PASS 3: COMPETING ARCHITECTURES =====
    prompt = PASS3_ARCHITECTURES.format(
        device=device, failure=failure, modification=modification,
        mechanisms_json=json.dumps(mechanisms, indent=2)[:2000])
    content, model, provider, reason, usage = routed_call(prompt)
    response_hash_3 = _hash(content or "")
    manifests.append({
        "pass": "pass3_architectures", "provider": provider, "model": model,
        "routing_reason": reason, "response_hash": response_hash_3,
        "input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    arch_result = _try_parse_json(content) or {}
    architectures = arch_result.get("architectures", [])
    if not architectures:
        return _failed_invention(aic, seed_id, "PASS3_NO_ARCHITECTURES", manifests, refinement_history, t0)

    # ===== PASS 4: ADVERSARIAL ELIMINATION =====
    # Attack up to 3 architectures (limit for efficiency), pick the first survivor
    surviving_arch = None
    for arch in architectures[:3]:
        prompt = PASS4_ADVERSARIAL.format(arch_json=json.dumps(arch, indent=2)[:2000])
        content, model, provider, reason, usage = routed_call(prompt, max_tokens=1500)
        response_hash_4 = _hash(content or "")
        manifests.append({
            "pass": "pass4_adversarial", "provider": provider, "model": model,
            "routing_reason": reason, "response_hash": response_hash_4,
            "architecture_id": arch.get("id", ""),
            "input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        adv_result = _try_parse_json(content) or {}
        arch["adversarial"] = adv_result
        if adv_result.get("overall") == "SURVIVED":
            surviving_arch = arch
            break
        else:
            refinement_history.append({
                "round": 1,
                "architecture_id": arch.get("id", ""),
                "outcome": adv_result.get("overall", "UNKNOWN"),
                "killed_dimensions": adv_result.get("killed_dimensions", []),
                "refinement_needed": adv_result.get("refinement_needed", ""),
            })

    # ===== PASS 5: REFINEMENT =====
    refinement_rounds = 0
    if not surviving_arch and architectures:
        arch_to_refine = architectures[0]
        for refinement_round in range(1, 3):  # max 2 refinement rounds
            refinement_rounds = refinement_round
            adv = arch_to_refine.get("adversarial", {})
            prompt = PASS5_REFINEMENT.format(
                arch_json=json.dumps(arch_to_refine, indent=2)[:2000],
                attacks_json=json.dumps(adv.get("attacks", []), indent=2)[:1500])
            content, model, provider, reason, usage = routed_call(prompt, max_tokens=2000)
            response_hash_5 = _hash(content or "")
            manifests.append({
                "pass": f"pass5_refinement_round{refinement_round}", "provider": provider, "model": model,
                "routing_reason": reason, "response_hash": response_hash_5,
                "input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            refined = _try_parse_json(content) or {}
            refinement_history.append({
                "round": refinement_round,
                "refined_nucleus": refined.get("refined_nucleus", ""),
                "addresses_attacks": refined.get("addresses_attacks", []),
                "remaining_risks": refined.get("remaining_risks", []),
            })

            refined_arch = dict(arch_to_refine)
            refined_arch["inventive_nucleus"] = refined.get("refined_nucleus", arch_to_refine.get("inventive_nucleus", ""))
            refined_arch["refined_structure"] = refined.get("refined_structure", "")
            refined_arch["refined_components"] = refined.get("refined_components", [])
            refined_arch["refined_causal_chain"] = refined.get("refined_causal_chain", [])
            refined_arch["known_elements"] = refined.get("known_elements", [])
            refined_arch["new_relationship"] = refined.get("new_relationship", "")
            refined_arch["new_configuration"] = refined.get("new_configuration", "")
            refined_arch["new_control_rule"] = refined.get("new_control_rule", "")

            prompt = PASS4_ADVERSARIAL.format(arch_json=json.dumps(refined_arch, indent=2)[:2000])
            content, model, provider, reason, usage = routed_call(prompt, max_tokens=1500)
            response_hash_4b = _hash(content or "")
            manifests.append({
                "pass": f"pass4_adversarial_round{refinement_round}", "provider": provider, "model": model,
                "routing_reason": reason, "response_hash": response_hash_4b,
                "input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            adv_result = _try_parse_json(content) or {}
            refined_arch["adversarial"] = adv_result
            if adv_result.get("overall") == "SURVIVED":
                surviving_arch = refined_arch
                break
            else:
                arch_to_refine = refined_arch
                refinement_history.append({
                    "round": refinement_round,
                    "outcome": adv_result.get("overall", "UNKNOWN"),
                    "killed_dimensions": adv_result.get("killed_dimensions", []),
                })

        if not surviving_arch:
            surviving_arch = arch_to_refine
            surviving_arch["status"] = "REFINEMENT_EXHAUSTED"

    if not surviving_arch:
        return _failed_invention(aic, seed_id, "NO_SURVIVING_ARCHITECTURE", manifests, refinement_history, t0)

    # ===== PREDICTION GENERATION =====
    nucleus = surviving_arch.get("inventive_nucleus", "") or surviving_arch.get("refined_nucleus", "")
    mechanism = surviving_arch.get("interaction", "") or str(surviving_arch.get("mechanism_id", ""))
    effect = surviving_arch.get("expected_effect", "")

    prompt = PREDICTION_PROMPT.format(nucleus=nucleus, mechanism=mechanism, effect=effect)
    content, model, provider, reason, usage = routed_call(prompt, max_tokens=1500)
    response_hash_pred = _hash(content or "")
    manifests.append({
        "pass": "prediction", "provider": provider, "model": model,
        "routing_reason": reason, "response_hash": response_hash_pred,
        "input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    pred_result = _try_parse_json(content) or {}
    predictions = pred_result.get("predictions", [])

    # ===== EXPERIMENT DESIGN =====
    prompt = EXPERIMENT_PROMPT.format(
        nucleus=nucleus, mechanism=mechanism,
        predictions_json=json.dumps(predictions, indent=2)[:1000])
    content, model, provider, reason, usage = routed_call(prompt, max_tokens=2000)
    response_hash_exp = _hash(content or "")
    manifests.append({
        "pass": "experiment_design", "provider": provider, "model": model,
        "routing_reason": reason, "response_hash": response_hash_exp,
        "input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    exp_result = _try_parse_json(content) or {}
    experiment_plan = exp_result.get("experiment", {})

    # ===== PRIOR-ART ASSESSMENT =====
    prompt = PRIOR_ART_PROMPT.format(nucleus=nucleus)
    content, model, provider, reason, usage = routed_call(prompt, max_tokens=1500)
    response_hash_pa = _hash(content or "")
    manifests.append({
        "pass": "prior_art", "provider": provider, "model": model,
        "routing_reason": reason, "response_hash": response_hash_pa,
        "input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    pa_result = _try_parse_json(content) or {}
    prior_art = pa_result.get("prior_art_assessment", {})

    # ===== BUILD FINAL INVENTION CANDIDATE =====
    t1 = time.time()
    invention_id = f"INV_{seed_id}"

    design_parameters = _extract_parameters(surviving_arch)
    boundary_conditions = _extract_boundary_conditions(surviving_arch)

    invention = {
        "invention_id": invention_id,
        "parent_aic_id": f"{aic['arm']}_{aic['problem_id']}",
        "architecture_origin": aic.get("arm", ""),
        "problem_id": aic.get("problem_id", ""),
        "device_class": device,
        "failure_mode": failure_mode,

        "problem_definition": reconstruction.get("failure_definition", failure),
        "baseline_architecture": reconstruction.get("current_device_behavior", ""),

        "inventive_nucleus": nucleus,
        "mechanism": mechanism,
        "causal_chain": surviving_arch.get("refined_causal_chain") or surviving_arch.get("causal_chain", []),

        "system_architecture": [surviving_arch.get("refined_structure") or surviving_arch.get("structure", "")],
        "components": surviving_arch.get("refined_components") or surviving_arch.get("components", []),
        "interfaces": surviving_arch.get("interfaces", []),
        "materials": surviving_arch.get("materials", []),
        "control_logic": surviving_arch.get("control_logic", []),

        "operating_conditions": [surviving_arch.get("operating_condition", "")],
        "design_parameters": design_parameters,
        "boundary_conditions": boundary_conditions,

        "expected_effect": effect,
        "technical_advantage": [surviving_arch.get("new_relationship", ""),
                                surviving_arch.get("new_configuration", ""),
                                surviving_arch.get("new_control_rule", "")],
        "secondary_advantages": [],

        "novelty_hypothesis": prior_art.get("inventive_step", ""),
        "prior_art_risks": [{
            "classification": prior_art.get("classification", "UNRESOLVED"),
            "known_elements": prior_art.get("known_elements", []),
            "adjacent_references": prior_art.get("adjacent_references", []),
            "search_universe_limitation": prior_art.get("search_universe_limitation", ""),
        }],

        "falsification_tests": [p.get("falsifier", "") for p in predictions if p.get("falsifier")],
        "predictions": predictions,
        "experiment_plan": experiment_plan,

        "engineering_feasibility": {
            "assessment": "Derived from adversarial analysis",
            "feasibility_verdict": surviving_arch.get("adversarial", {}).get("overall", "UNKNOWN"),
        },
        "regulatory_considerations": {
            "assessment": "Regulatory pathway not yet assessed. Requires formal regulatory review.",
        },

        "adversarial_analysis": surviving_arch.get("adversarial", {}),
        "refinement_history": refinement_history,
        "refinement_rounds": refinement_rounds,

        "epistemic_state": "INVENTION_CANDIDATE" if surviving_arch.get("status") != "REFINEMENT_EXHAUSTED" else "REFINEMENT_EXHAUSTED",
        "status": surviving_arch.get("status", "SURVIVED"),
        "patentability_status": "NOT_ESTABLISHED",

        "provider": manifests[-1]["provider"] if manifests else "",
        "model": manifests[-1]["model"] if manifests else "",
        "prompt_hash": _hash(PASS1_RECONSTRUCT + PASS2_MECHANISM_EXPANSION + PASS3_ARCHITECTURES + PASS4_ADVERSARIAL + PASS5_REFINEMENT + PREDICTION_PROMPT + EXPERIMENT_PROMPT + PRIOR_ART_PROMPT),
        "response_hash": hashlib.sha256(json.dumps([m["response_hash"] for m in manifests]).encode()).hexdigest()[:16],
        "source_ids": aic.get("source_ids", []),
        "source_hashes": aic.get("source_hashes", []),
        "source_spans": aic.get("source_spans", []),
        "packet_hash": aic.get("packet_hash", ""),
        "routing_policy_sha256": ROUTING_POLICY_SHA,

        "provider_call_manifests": manifests,
        "total_llm_calls": len(manifests),
        "wall_clock_s": round(t1 - t0, 1),
        "generated_at": datetime.now(timezone.utc).isoformat(),

        "disclaimer": (
            "This INVENTION_CANDIDATE was generated by the invention synthesis engine (V1). "
            "It has NOT been independently validated by a corrected adversarial pipeline. "
            "PATENTABILITY_STATUS: NOT_ESTABLISHED. "
            "This is not a claim of novelty, patentability, clinical safety, or commercial viability."
        ),
    }

    return invention


def _extract_parameters(arch):
    params = []
    text = json.dumps(arch)
    for match in re.finditer(r'(\d+\.?\d*)\s*(mm|nm|μm|µm|V|Hz|MPa|kPa|°C|seconds?|hours?|cycles?|%|dB|mg/mL|μg|μJ)', text):
        params.append({
            "value": match.group(1),
            "unit": match.group(2),
            "provenance": "HYPOTHESIS",
        })
    return params

def _extract_boundary_conditions(arch):
    bc = arch.get("failure_containment", "")
    if bc:
        return [bc]
    return []

def _failed_invention(aic, seed_id, failure_reason, manifests, refinement_history, t0):
    t1 = time.time()
    return {
        "invention_id": f"INV_{seed_id}",
        "parent_aic_id": f"{aic['arm']}_{aic['problem_id']}",
        "architecture_origin": aic.get("arm", ""),
        "problem_id": aic.get("problem_id", ""),
        "device_class": aic.get("device_class", ""),
        "failure_mode": aic.get("failure_mode", ""),
        "epistemic_state": "INVENTION_GENERATION_FAILED",
        "status": failure_reason,
        "refinement_history": refinement_history,
        "provider_call_manifests": manifests,
        "total_llm_calls": len(manifests),
        "wall_clock_s": round(t1 - t0, 1),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "INVENTION_GENERATION_FAILED. See status for reason.",
    }
