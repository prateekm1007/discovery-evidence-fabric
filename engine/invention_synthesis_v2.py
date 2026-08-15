#!/usr/bin/env python3
"""
INVENTION SYNTHESIS ENGINE V2 — full pipeline, no reductions, no hard-coded secrets.

DIFFERENCES FROM V1:
  1. NO hard-coded secrets. All keys from environment variables only.
  2. Primary model: meta/llama-3.1-8b-instruct on NVIDIA (0.9s/call, fast, JSON-capable)
  3. Full pipeline restored: 5 architectures, 3 refinement rounds, ALL adversarial dims
  4. Operational failures distinguished from scientific rejections
  5. Adversarial UNKNOWN = NOT_EVALUATED (never SURVIVED)
  6. REFINEMENT_EXHAUSTED = REFINEMENT_LIMIT_REACHED (not success)
  7. Final gate required for INVENTION_CANDIDATE status
  8. Per-stage checkpointing (lineage retained even if later stage fails)

PROTOCOL (frozen in INVENTION_GENERATION_PROTOCOL_V2.json):
  - routing_policy: NVIDIA llama-3.1-8b primary, Mistral fallback, z-ai fallback
  - per_call_timeout: 60s
  - per_call_retries: 2
  - max_architectures: 5
  - max_refinement_rounds: 3
  - adversarial_dimensions: 7 (mechanism, transfer, boundary, obviousness, prior_art, feasibility, falsifiability)
  - temperature: 0.0
  - max_tokens: 2000
"""
from __future__ import annotations
import json, os, sys, time, ssl, hashlib, re, urllib.request, subprocess, tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ===== ROUTING (V2 protocol — NO hard-coded secrets) =====
# Keys come from environment ONLY. No default fallback values.
NVIDIA_KEY = os.environ.get("NVIDIA_API_KEY")
if not NVIDIA_KEY:
    raise RuntimeError("NVIDIA_API_KEY environment variable not set. No hard-coded secrets in V2.")
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

MISTRAL_KEY = os.environ.get("MISTRAL_API_KEY")  # optional fallback
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"

# Cerebras (Cloudflare-blocked in testing, kept as optional fallback)
CEREBRAS_KEY = os.environ.get("CEREBRAS_API_KEY")  # optional
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"

# Primary model: fast NVIDIA llama-3.1-8b
NVIDIA_PRIMARY_MODEL = "meta/llama-3.1-8b-instruct"
NVIDIA_FALLBACK_MODEL = "deepseek-ai/deepseek-v4-flash-0731"
MISTRAL_PRIMARY_MODEL = "mistral-medium-latest"

ROUTING_POLICY_SHA = "79a928166bce6fb9faf2368c9aba2ffc9f1aaeacc4e73bbade25218d4f76470d"
INVENTION_PROTOCOL_SHA = "pending"  # set after protocol file is frozen

_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE

PER_CALL_RETRIES = 2
PER_CALL_TIMEOUT = 60


def _nvidia_call(prompt, model=NVIDIA_PRIMARY_MODEL, max_tokens=2000):
    """Call NVIDIA API. Returns (content, model, provider, routing_reason, usage)."""
    payload = {"model": model, "messages":[{"role":"user","content":prompt}],
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
                usage = data.get("usage", {})
                return content, model, "NVIDIA", "NVIDIA_PRIMARY", {
                    "input_tokens": usage.get("prompt_tokens", 0),
                    "output_tokens": usage.get("completion_tokens", 0),
                }
        except Exception:
            if attempt < PER_CALL_RETRIES - 1: time.sleep(3)
    return None, model, "NVIDIA", "NVIDIA_FAILED", {}

def _mistral_call(prompt, max_tokens=2000):
    if not MISTRAL_KEY:
        return None, "unknown", "Mistral", "MISTRAL_NO_KEY", {}
    payload = {"model": MISTRAL_PRIMARY_MODEL, "messages":[{"role":"user","content":prompt}],
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
                return content, MISTRAL_PRIMARY_MODEL, "Mistral", "MISTRAL_FALLBACK", {
                    "input_tokens": usage.get("prompt_tokens", 0),
                    "output_tokens": usage.get("completion_tokens", 0),
                }
        except Exception:
            if attempt < PER_CALL_RETRIES - 1: time.sleep(3)
    return None, "unknown", "Mistral", "MISTRAL_FAILED", {}

def _nvidia_fallback_call(prompt, max_tokens=2000):
    """Fallback to NVIDIA deepseek model."""
    return _nvidia_call(prompt, model=NVIDIA_FALLBACK_MODEL, max_tokens=max_tokens)

def routed_call(prompt, max_tokens=2000):
    """Routing order: NVIDIA llama-3.1-8b (primary) → NVIDIA deepseek (fallback) → Mistral."""
    # Primary: NVIDIA llama-3.1-8b (fast, 0.9s/call)
    content, model, provider, reason, usage = _nvidia_call(prompt, max_tokens=max_tokens)
    if content:
        return content, model, provider, reason, usage
    # Fallback 1: NVIDIA deepseek
    content, model, provider, reason, usage = _nvidia_fallback_call(prompt, max_tokens=max_tokens)
    if content:
        return content, model, provider, reason, usage
    # Fallback 2: Mistral (if key available)
    return _mistral_call(prompt, max_tokens=max_tokens)


# ===== PROMPT TEMPLATES (same as V1, frozen) =====

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

Respond in EXACTLY this JSON format (no markdown, no commentary):
{{"failure_definition": "<precise definition>", "causal_mechanism": "<what causes the failure>", "current_device_behavior": "<what the device currently does>", "failure_point": "<where exactly it fails>", "blocking_constraint": "<what blocks the obvious solution>"}}"""

PASS2_MECHANISM_EXPANSION = """You are an invention synthesis engine. Generate 5 MATERIALLY DIFFERENT mechanisms capable of improving this AIC. They must NOT be synonyms.

AIC:
- Device: {device}
- Failure: {failure}
- Proposed Modification: {modification}
- Causal Mechanism: {causal_mechanism}
- Blocking Constraint: {blocking_constraint}

Generate 5 mechanisms from DIFFERENT engineering families:
  - passive structural reinforcement
  - active sensing/control
  - material-state transition
  - interface modification
  - energy redistribution

Respond in EXACTLY this JSON format (no markdown):
{{"mechanisms": [{{"id": "MECH_A", "family": "<family>", "mechanism": "<specific mechanism>", "how_it_addresses_failure": "<causal explanation>", "key_components": ["component1"], "falsifier": "<what observation would prove this wrong>"}}]}}"""

PASS3_ARCHITECTURES = """You are an invention synthesis engine. Generate 5 competing invention architectures.

AIC: Device={device}, Failure={failure}, Modification={modification}

Available mechanisms:
{mechanisms_json}

For each mechanism, design a concrete invention architecture. Each must have:
  - inventive_nucleus (one SPECIFIC sentence, not vague)
  - structure, components, interfaces, materials, control_logic
  - interaction, operating_condition, failure_containment
  - expected_effect, causal_chain (6 steps: failure→cause→intervention→mechanism→effect→response)

GOOD nucleus: "A co-located, electrically isolated state-transition reference element that estimates local treatment exposure and normalizes a treatment-site signal before adaptive energy control."
BAD nucleus: "An improved electrosurgical system."

Respond in EXACTLY this JSON format (no markdown):
{{"architectures": [{{"id": "ARCH_A", "mechanism_id": "MECH_A", "inventive_nucleus": "<one specific sentence>", "structure": "<layout>", "components": ["comp1"], "interfaces": ["int1"], "materials": ["mat1"], "control_logic": ["step1"], "interaction": "<how they interact>", "operating_condition": "<when>", "failure_containment": "<how>", "expected_effect": "<effect>", "causal_chain": ["step1","step2","step3","step4","step5","step6"]}}]}}"""

PASS4_ADVERSARIAL = """You are an adversarial reviewer. Attack this invention architecture across 7 dimensions.

Architecture:
{arch_json}

For each dimension, respond KILL or SURVIVE with a specific reason and required evidence:
1. MECHANISM_VALIDITY: Could the mechanism physically work?
2. TRANSFER_LEGITIMACY: Is the transfer justified?
3. BOUNDARY_CONDITION: Where does it fail? (require specific boundary + external evidence)
4. OBVIOUSNESS: Would an expert naturally combine these elements?
5. PRIOR_ART_RISK: Does an existing reference disclose the same nucleus?
6. ENGINEERING_FEASIBILITY: Can it actually be built?
7. FALSIFIABILITY: What experiment could kill it?

Respond in EXACTLY this JSON format (no markdown):
{{"attacks": [{{"dimension": "MECHANISM_VALIDITY", "verdict": "KILL", "reason": "<specific>", "evidence_required": "<what evidence needed>"}}], "overall": "KILLED", "killed_dimensions": ["list"], "refinement_needed": "<what to refine if KILLED>"}}"""

PASS5_REFINEMENT = """You are an invention refinement engine. Refine this architecture to address adversarial attacks.

Original architecture:
{arch_json}

Adversarial attacks:
{attacks_json}

Refine to address each KILL. Identify:
- KNOWN_ELEMENTS (what's already known)
- NEW_RELATIONSHIP (what new relationship creates technical effect)
- NEW_CONFIGURATION (what new configuration)
- NEW_CONTROL_RULE (what new control rule)
The inventive step is the RELATIONSHIP/CONFIGURATION/CONTROL_RULE, not the known elements.

Respond in EXACTLY this JSON format (no markdown):
{{"refined_nucleus": "<one specific sentence>", "known_elements": ["elem1"], "new_relationship": "<relationship>", "new_configuration": "<config>", "new_control_rule": "<rule>", "refined_structure": "<layout>", "refined_components": ["comp1"], "refined_causal_chain": ["step1","step2","step3","step4","step5","step6"], "addresses_attacks": ["which addressed"], "remaining_risks": ["unresolved"]}}"""

PREDICTION_PROMPT = """You are a scientific prediction engine. Given this invention, produce a SPECIFIC, falsifiable prediction.

Invention:
- Nucleus: {nucleus}
- Mechanism: {mechanism}
- Expected Effect: {effect}

All fields mandatory. Respond in EXACTLY this JSON format (no markdown):
{{"predictions": [{{"observable": "<what to measure>", "baseline": "<comparison>", "expected_direction": "<increase/decrease>", "expected_magnitude": "<size>", "conditions": "<conditions>", "uncertainty": 0.3, "falsifier": "<what refutes>"}}]}}"""

EXPERIMENT_PROMPT = """You are an experiment design engine. Design a controlled experiment.

Invention:
- Nucleus: {nucleus}
- Mechanism: {mechanism}
- Predictions: {predictions_json}

All fields mandatory. Controls and falsification are REQUIRED. Respond in EXACTLY this JSON format (no markdown):
{{"experiment": {{"objective": "<objective>", "independent_variables": ["var1"], "dependent_variables": ["var1"], "controls": ["control1"], "baseline": "<baseline>", "procedure": ["step1","step2"], "expected_result": "<expected>", "falsification_condition": "<what falsifies>", "sample_requirements": "<samples>", "safety_constraints": "<safety>", "estimated_cost": "<cost>", "estimated_duration": "<duration>", "information_gain": "<what you learn>"}}}}"""

PRIOR_ART_PROMPT = """You are a prior-art analysis engine. Assess prior-art risk for this invention nucleus.

Invention Nucleus: {nucleus}

Do NOT call this novel. Classify as:
  - NO_MATCH_FOUND: no match in searched universe (NOT the same as novel)
  - ADJACENT_PRIOR_ART: related prior art exists but doesn't disclose the exact nucleus
  - SPECIFIC_DISCLOSURE_RISK: a specific reference likely discloses the same nucleus
  - UNRESOLVED: cannot determine without a formal search

Respond in EXACTLY this JSON format (no markdown):
{{"prior_art_assessment": {{"classification": "NO_MATCH_FOUND", "known_elements": ["elem1"], "adjacent_references": ["ref1"], "inventive_step": "<what makes it different>", "search_universe_limitation": "<what was NOT searched>"}}}}"""


def _hash(s):
    return hashlib.sha256(s.encode()).hexdigest()[:16]

def _try_parse_json(content):
    """Try to extract JSON from LLM response."""
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


# ===== V2 SYNTHESIS (full pipeline, no reductions) =====

MAX_ARCHITECTURES = 5
MAX_REFINEMENT_ROUNDS = 3
ADVERSARIAL_DIMENSIONS = [
    "MECHANISM_VALIDITY", "TRANSFER_LEGITIMACY", "BOUNDARY_CONDITION",
    "OBVIOUSNESS", "PRIOR_ART_RISK", "ENGINEERING_FEASIBILITY", "FALSIFIABILITY",
]

def synthesize_invention_v2(aic: dict, seed_id: str, checkpoint_dir: Path = None) -> dict:
    """Full V2 pipeline. No reductions. Per-stage checkpointing."""
    t0 = time.time()
    manifests = []
    lineage = {}  # per-stage artifacts retained even if later stage fails
    refinement_history = []

    device = aic.get("device_class", "")
    failure = aic.get("documented_failure", "")
    failure_mode = aic.get("failure_mode", "")
    modification = aic.get("proposed_modification", "")
    reasoning = aic.get("mechanistic_reasoning", "")
    ftest = aic.get("falsification_test", "")

    def _checkpoint(stage, data):
        """Persist each stage independently."""
        lineage[stage] = data
        if checkpoint_dir:
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
            (checkpoint_dir / f"{seed_id}_{stage}.json").write_text(
                json.dumps(data, indent=2, default=str))

    # ===== PASS 1: RECONSTRUCT =====
    try:
        prompt = PASS1_RECONSTRUCT.format(
            device=device, failure=failure, failure_mode=failure_mode,
            modification=modification, reasoning=reasoning[:500], ftest=ftest[:300])
        content, model, provider, reason, usage = routed_call(prompt)
        manifests.append({"pass": "pass1", "provider": provider, "model": model,
            "routing_reason": reason, "response_hash": _hash(content or ""),
            "input_tokens": usage.get("input_tokens",0), "output_tokens": usage.get("output_tokens",0),
            "timestamp": datetime.now(timezone.utc).isoformat()})
        reconstruction = _try_parse_json(content) or {}
        _checkpoint("pass1_reconstruction", reconstruction)
        if not reconstruction:
            return _failed_invention(aic, seed_id, "PASS1_CALL_FAILED", manifests, lineage, refinement_history, t0)
    except Exception as e:
        return _failed_invention(aic, seed_id, f"PASS1_CALL_FAILED: {str(e)[:80]}", manifests, lineage, refinement_history, t0)

    # ===== PASS 2: MECHANISM EXPANSION (5 mechanisms) =====
    try:
        prompt = PASS2_MECHANISM_EXPANSION.format(
            device=device, failure=failure, modification=modification,
            causal_mechanism=reconstruction.get("causal_mechanism", ""),
            blocking_constraint=reconstruction.get("blocking_constraint", ""))
        content, model, provider, reason, usage = routed_call(prompt)
        manifests.append({"pass": "pass2", "provider": provider, "model": model,
            "routing_reason": reason, "response_hash": _hash(content or ""),
            "input_tokens": usage.get("input_tokens",0), "output_tokens": usage.get("output_tokens",0),
            "timestamp": datetime.now(timezone.utc).isoformat()})
        mech_result = _try_parse_json(content) or {}
        mechanisms = mech_result.get("mechanisms", [])
        _checkpoint("pass2_mechanisms", mechanisms)
        if not mechanisms:
            return _failed_invention(aic, seed_id, "PASS2_CALL_FAILED", manifests, lineage, refinement_history, t0)
    except Exception as e:
        return _failed_invention(aic, seed_id, f"PASS2_CALL_FAILED: {str(e)[:80]}", manifests, lineage, refinement_history, t0)

    # ===== PASS 3: COMPETING ARCHITECTURES (5) =====
    try:
        prompt = PASS3_ARCHITECTURES.format(
            device=device, failure=failure, modification=modification,
            mechanisms_json=json.dumps(mechanisms, indent=2)[:2000])
        content, model, provider, reason, usage = routed_call(prompt)
        manifests.append({"pass": "pass3", "provider": provider, "model": model,
            "routing_reason": reason, "response_hash": _hash(content or ""),
            "input_tokens": usage.get("input_tokens",0), "output_tokens": usage.get("output_tokens",0),
            "timestamp": datetime.now(timezone.utc).isoformat()})
        arch_result = _try_parse_json(content) or {}
        architectures = arch_result.get("architectures", [])
        _checkpoint("pass3_architectures", architectures)
        if not architectures:
            return _failed_invention(aic, seed_id, "PASS3_CALL_FAILED", manifests, lineage, refinement_history, t0)
    except Exception as e:
        return _failed_invention(aic, seed_id, f"PASS3_CALL_FAILED: {str(e)[:80]}", manifests, lineage, refinement_history, t0)

    # ===== PASS 4: ADVERSARIAL EVALUATION OF ALL ARCHITECTURES =====
    surviving_arch = None
    for arch in architectures[:MAX_ARCHITECTURES]:
        try:
            prompt = PASS4_ADVERSARIAL.format(arch_json=json.dumps(arch, indent=2)[:2000])
            content, model, provider, reason, usage = routed_call(prompt, max_tokens=1500)
            manifests.append({"pass": "pass4_adversarial", "architecture_id": arch.get("id",""),
                "provider": provider, "model": model, "routing_reason": reason,
                "response_hash": _hash(content or ""),
                "input_tokens": usage.get("input_tokens",0), "output_tokens": usage.get("output_tokens",0),
                "timestamp": datetime.now(timezone.utc).isoformat()})
            adv_result = _try_parse_json(content) or {}
            arch["adversarial"] = adv_result
            _checkpoint(f"pass4_adversarial_{arch.get('id','unknown')}", adv_result)
            if adv_result.get("overall") == "SURVIVED":
                surviving_arch = arch
                break
            else:
                refinement_history.append({"round": 0, "architecture_id": arch.get("id",""),
                    "outcome": adv_result.get("overall","UNKNOWN"),
                    "killed_dimensions": adv_result.get("killed_dimensions",[])})
        except Exception as e:
            refinement_history.append({"round": 0, "architecture_id": arch.get("id",""),
                "outcome": "PASS4_CALL_FAILED", "error": str(e)[:80]})

    # ===== PASS 5: REFINEMENT (max 3 rounds) =====
    refinement_rounds = 0
    if not surviving_arch and architectures:
        arch_to_refine = architectures[0]
        for refinement_round in range(1, MAX_REFINEMENT_ROUNDS + 1):
            refinement_rounds = refinement_round
            try:
                adv = arch_to_refine.get("adversarial", {})
                prompt = PASS5_REFINEMENT.format(
                    arch_json=json.dumps(arch_to_refine, indent=2)[:2000],
                    attacks_json=json.dumps(adv.get("attacks", []), indent=2)[:1500])
                content, model, provider, reason, usage = routed_call(prompt, max_tokens=2000)
                manifests.append({"pass": f"pass5_refine_r{refinement_round}", "provider": provider,
                    "model": model, "routing_reason": reason, "response_hash": _hash(content or ""),
                    "input_tokens": usage.get("input_tokens",0), "output_tokens": usage.get("output_tokens",0),
                    "timestamp": datetime.now(timezone.utc).isoformat()})
                refined = _try_parse_json(content) or {}
                _checkpoint(f"pass5_refinement_round{refinement_round}", refined)
                refinement_history.append({"round": refinement_round,
                    "refined_nucleus": refined.get("refined_nucleus",""),
                    "addresses_attacks": refined.get("addresses_attacks",[]),
                    "remaining_risks": refined.get("remaining_risks",[])})

                refined_arch = dict(arch_to_refine)
                refined_arch["inventive_nucleus"] = refined.get("refined_nucleus", arch_to_refine.get("inventive_nucleus",""))
                refined_arch["refined_structure"] = refined.get("refined_structure","")
                refined_arch["refined_components"] = refined.get("refined_components",[])
                refined_arch["refined_causal_chain"] = refined.get("refined_causal_chain",[])
                refined_arch["known_elements"] = refined.get("known_elements",[])
                refined_arch["new_relationship"] = refined.get("new_relationship","")
                refined_arch["new_configuration"] = refined.get("new_configuration","")
                refined_arch["new_control_rule"] = refined.get("new_control_rule","")

                # Re-attack refined architecture
                prompt = PASS4_ADVERSARIAL.format(arch_json=json.dumps(refined_arch, indent=2)[:2000])
                content, model, provider, reason, usage = routed_call(prompt, max_tokens=1500)
                manifests.append({"pass": f"pass4_adversarial_r{refinement_round}", "provider": provider,
                    "model": model, "routing_reason": reason, "response_hash": _hash(content or ""),
                    "input_tokens": usage.get("input_tokens",0), "output_tokens": usage.get("output_tokens",0),
                    "timestamp": datetime.now(timezone.utc).isoformat()})
                adv_result = _try_parse_json(content) or {}
                refined_arch["adversarial"] = adv_result
                _checkpoint(f"pass4_adversarial_r{refinement_round}", adv_result)
                if adv_result.get("overall") == "SURVIVED":
                    surviving_arch = refined_arch
                    break
                else:
                    arch_to_refine = refined_arch
                    refinement_history.append({"round": refinement_round,
                        "outcome": adv_result.get("overall","UNKNOWN"),
                        "killed_dimensions": adv_result.get("killed_dimensions",[])})
            except Exception as e:
                refinement_history.append({"round": refinement_round, "outcome": f"PASS5_CALL_FAILED: {str(e)[:60]}"})
                break

        if not surviving_arch:
            surviving_arch = arch_to_refine
            surviving_arch["status"] = "REFINEMENT_LIMIT_REACHED"

    if not surviving_arch:
        return _failed_invention(aic, seed_id, "NO_SURVIVING_ARCHITECTURE", manifests, lineage, refinement_history, t0)

    # ===== PREDICTION GENERATION =====
    nucleus = surviving_arch.get("inventive_nucleus","") or surviving_arch.get("refined_nucleus","")
    mechanism = surviving_arch.get("interaction","") or str(surviving_arch.get("mechanism_id",""))
    effect = surviving_arch.get("expected_effect","")

    try:
        prompt = PREDICTION_PROMPT.format(nucleus=nucleus, mechanism=mechanism, effect=effect)
        content, model, provider, reason, usage = routed_call(prompt, max_tokens=1500)
        manifests.append({"pass": "prediction", "provider": provider, "model": model,
            "routing_reason": reason, "response_hash": _hash(content or ""),
            "input_tokens": usage.get("input_tokens",0), "output_tokens": usage.get("output_tokens",0),
            "timestamp": datetime.now(timezone.utc).isoformat()})
        pred_result = _try_parse_json(content) or {}
        predictions = pred_result.get("predictions", [])
        _checkpoint("predictions", predictions)
    except Exception as e:
        predictions = []
        manifests.append({"pass": "prediction", "error": str(e)[:80]})

    # ===== EXPERIMENT DESIGN =====
    try:
        prompt = EXPERIMENT_PROMPT.format(nucleus=nucleus, mechanism=mechanism,
            predictions_json=json.dumps(predictions, indent=2)[:1000])
        content, model, provider, reason, usage = routed_call(prompt, max_tokens=2000)
        manifests.append({"pass": "experiment", "provider": provider, "model": model,
            "routing_reason": reason, "response_hash": _hash(content or ""),
            "input_tokens": usage.get("input_tokens",0), "output_tokens": usage.get("output_tokens",0),
            "timestamp": datetime.now(timezone.utc).isoformat()})
        exp_result = _try_parse_json(content) or {}
        experiment_plan = exp_result.get("experiment", {})
        _checkpoint("experiment_plan", experiment_plan)
    except Exception as e:
        experiment_plan = {}
        manifests.append({"pass": "experiment", "error": str(e)[:80]})

    # ===== PRIOR-ART ASSESSMENT =====
    try:
        prompt = PRIOR_ART_PROMPT.format(nucleus=nucleus)
        content, model, provider, reason, usage = routed_call(prompt, max_tokens=1500)
        manifests.append({"pass": "prior_art", "provider": provider, "model": model,
            "routing_reason": reason, "response_hash": _hash(content or ""),
            "input_tokens": usage.get("input_tokens",0), "output_tokens": usage.get("output_tokens",0),
            "timestamp": datetime.now(timezone.utc).isoformat()})
        pa_result = _try_parse_json(content) or {}
        prior_art = pa_result.get("prior_art_assessment", {})
        _checkpoint("prior_art", prior_art)
    except Exception as e:
        prior_art = {}
        manifests.append({"pass": "prior_art", "error": str(e)[:80]})

    # ===== FINAL GATE EVALUATION =====
    # Determine final epistemic state
    adv = surviving_arch.get("adversarial", {})
    adv_overall = adv.get("overall", "UNKNOWN")
    pa_class = prior_art.get("classification", "UNRESOLVED")
    has_predictions = len(predictions) > 0 and all(p.get("falsifier") for p in predictions)
    has_experiment = bool(experiment_plan.get("falsification_condition") and experiment_plan.get("controls"))

    # Check all 7 adversarial dimensions have explicit verdicts
    attacks = adv.get("attacks", [])
    all_dims_evaluated = len(attacks) >= 7 and all(a.get("verdict") in ("KILL","SURVIVE") for a in attacks)

    if surviving_arch.get("status") == "REFINEMENT_LIMIT_REACHED":
        # Run final gate on the last refined architecture
        if adv_overall == "SURVIVED" and all_dims_evaluated and has_predictions and has_experiment:
            if pa_class in ("NO_MATCH_FOUND", "ADJACENT_PRIOR_ART"):
                final_epistemic = "INVENTION_CANDIDATE"
                final_status = "SURVIVED_FINAL_GATE"
            elif pa_class == "UNRESOLVED":
                final_epistemic = "PRIOR_ART_UNRESOLVED"
                final_status = "PRIOR_ART_UNRESOLVED"
            else:  # SPECIFIC_DISCLOSURE_RISK
                final_epistemic = "INVENTION_KILLED"
                final_status = "PRIOR_ART_SPECIFIC_DISCLOSURE"
        else:
            final_epistemic = "INVENTION_KILLED"
            final_status = "FINAL_GATE_FAILED"
    elif adv_overall == "SURVIVED" and all_dims_evaluated and has_predictions and has_experiment:
        if pa_class in ("NO_MATCH_FOUND", "ADJACENT_PRIOR_ART"):
            final_epistemic = "INVENTION_CANDIDATE"
            final_status = "SURVIVED_FINAL_GATE"
        elif pa_class == "UNRESOLVED":
            final_epistemic = "PRIOR_ART_UNRESOLVED"
            final_status = "PRIOR_ART_UNRESOLVED"
        else:
            final_epistemic = "INVENTION_KILLED"
            final_status = "PRIOR_ART_SPECIFIC_DISCLOSURE"
    else:
        final_epistemic = "INVENTION_KILLED"
        final_status = "FINAL_GATE_FAILED"

    # ===== BUILD FINAL INVENTION CANDIDATE =====
    t1 = time.time()
    invention_id = f"INV_V2_{seed_id.replace('TOP20_','')}"

    design_parameters = _extract_parameters(surviving_arch)

    invention = {
        "invention_id": invention_id,
        "parent_aic_id": f"{aic['arm']}_{aic['problem_id']}",
        "architecture_origin": aic.get("arm",""),
        "problem_id": aic.get("problem_id",""),
        "device_class": device,
        "failure_mode": failure_mode,

        "problem_definition": reconstruction.get("failure_definition", failure),
        "baseline_architecture": reconstruction.get("current_device_behavior", ""),

        "inventive_nucleus": nucleus,
        "mechanism": mechanism,
        "causal_chain": surviving_arch.get("refined_causal_chain") or surviving_arch.get("causal_chain",[]),

        "system_architecture": [surviving_arch.get("refined_structure") or surviving_arch.get("structure","")],
        "components": surviving_arch.get("refined_components") or surviving_arch.get("components",[]),
        "interfaces": surviving_arch.get("interfaces",[]),
        "materials": surviving_arch.get("materials",[]),
        "control_logic": surviving_arch.get("control_logic",[]),

        "operating_conditions": [surviving_arch.get("operating_condition","")],
        "design_parameters": design_parameters,
        "boundary_conditions": _extract_boundary_conditions(surviving_arch),

        "expected_effect": effect,
        "technical_advantage": [surviving_arch.get("new_relationship",""),
                                surviving_arch.get("new_configuration",""),
                                surviving_arch.get("new_control_rule","")],
        "secondary_advantages": [],

        "novelty_hypothesis": prior_art.get("inventive_step",""),
        "prior_art_risks": [{"classification": pa_class,
            "known_elements": prior_art.get("known_elements",[]),
            "adjacent_references": prior_art.get("adjacent_references",[]),
            "search_universe_limitation": prior_art.get("search_universe_limitation","")}],

        "falsification_tests": [p.get("falsifier","") for p in predictions if p.get("falsifier")],
        "predictions": predictions,
        "experiment_plan": experiment_plan,

        "engineering_feasibility": {"feasibility_verdict": adv_overall},
        "regulatory_considerations": {"assessment": "Not yet assessed. Requires formal regulatory review."},

        "adversarial_analysis": adv,
        "refinement_history": refinement_history,
        "refinement_rounds": refinement_rounds,

        "epistemic_state": final_epistemic,
        "status": final_status,
        "patentability_status": "NOT_ESTABLISHED",

        "all_adversarial_dimensions_evaluated": all_dims_evaluated,
        "has_predictions": has_predictions,
        "has_experiment_plan": has_experiment,

        "provider": manifests[-1].get("provider","") if manifests else "",
        "model": manifests[-1].get("model","") if manifests else "",
        "prompt_hash": _hash(PASS1_RECONSTRUCT+PASS2_MECHANISM_EXPANSION+PASS3_ARCHITECTURES+PASS4_ADVERSARIAL+PASS5_REFINEMENT+PREDICTION_PROMPT+EXPERIMENT_PROMPT+PRIOR_ART_PROMPT),
        "response_hash": hashlib.sha256(json.dumps([m.get("response_hash","") for m in manifests]).encode()).hexdigest()[:16],
        "source_ids": aic.get("source_ids",[]),
        "source_hashes": aic.get("source_hashes",[]),
        "source_spans": aic.get("source_spans",[]),
        "packet_hash": aic.get("packet_hash",""),
        "routing_policy_sha256": ROUTING_POLICY_SHA,

        "provider_call_manifests": manifests,
        "total_llm_calls": len(manifests),
        "wall_clock_s": round(t1-t0, 1),
        "generated_at": datetime.now(timezone.utc).isoformat(),

        "lineage": list(lineage.keys()),

        "disclaimer": (
            "This INVENTION_CANDIDATE was generated by the invention synthesis engine V2. "
            "It has NOT been independently validated by a corrected adversarial pipeline. "
            "PATENTABILITY_STATUS: NOT_ESTABLISHED. "
            "Not a claim of novelty, patentability, clinical safety, or commercial viability."
        ),
    }
    _checkpoint("final_invention", invention)
    return invention


def _extract_parameters(arch):
    params = []
    text = json.dumps(arch)
    for match in re.finditer(r'(\d+\.?\d*)\s*(mm|nm|μm|µm|V|Hz|MPa|kPa|°C|seconds?|hours?|cycles?|%|dB|mg/mL|μg|μJ)', text):
        params.append({"value": match.group(1), "unit": match.group(2), "provenance": "HYPOTHESIS"})
    return params

def _extract_boundary_conditions(arch):
    bc = arch.get("failure_containment","")
    return [bc] if bc else []

def _failed_invention(aic, seed_id, failure_reason, manifests, lineage, refinement_history, t0):
    t1 = time.time()
    return {
        "invention_id": f"INV_V2_{seed_id.replace('TOP20_','')}",
        "parent_aic_id": f"{aic['arm']}_{aic['problem_id']}",
        "architecture_origin": aic.get("arm",""),
        "problem_id": aic.get("problem_id",""),
        "device_class": aic.get("device_class",""),
        "failure_mode": aic.get("failure_mode",""),
        "epistemic_state": "PIPELINE_CALL_FAILED",
        "status": failure_reason,
        "refinement_history": refinement_history,
        "provider_call_manifests": manifests,
        "total_llm_calls": len(manifests),
        "wall_clock_s": round(t1-t0, 1),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lineage": list(lineage.keys()),
        "disclaimer": "PIPELINE_CALL_FAILED. See status for reason. This is an operational failure, not a scientific rejection.",
    }
