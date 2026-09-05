"""discovery_fabric/r411/attack.py — Directive s13: the adversarial
tournament. generator vs verifier vs attacker.

The attacker receives the candidate and tries to destroy it across the
directive's eight surfaces:
  mechanism, evidence, prior art, physics, baseline, manufacturability,
  commercial rationale, experiment design.

Constitutional grounding:
  - Art. XLV: generator/verifier separation — the attacker runs in a
    SEPARATE LLM context from the extraction that generated the
    candidate, and the engine records the independence mode
    (SEPARATE_CONTEXT when only one provider is credentialed — never
    labelled "independent adversarial validation"; SEPARATE_PROVIDER
    when a second provider exists).
  - Art. LII: the attack on the experiment design checks the
    falsification contract (an experiment with no kill outcome is
    ranking, not science).
  - Art. L: attacker calibration — run_attacker_calibration() measures
    sensitivity on known-defect synthetic candidates before attack
    results are allowed to influence selection (causal-invalidity +
    baseline-equivalence minimum classes).
  - Art. LXI: an attacker TRANSPORT FAILURE is INCOMPLETE, never KILLED.
  - The threshold is NOT lowered to force five winners (directive s13
    final rule; s14: never fabricate a fifth).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

ATTACK_VERSION = "R411-ATTACK-V1"

ATTACK_SURFACES = [
    "mechanism", "evidence", "prior_art", "physics", "baseline",
    "manufacturability", "commercial_rationale", "experiment_design",
]

ATTACK_PROMPT = """You are a hostile independent engineering attacker. Your job is to DESTROY the following technology candidate. Attack every surface; a candidate that survives you has earned it.

CANDIDATE:
- name: {name}
- problem: {problem}
- mechanism chain: {mechanism}
- unexploited phenomenon: {phenomenon}
- intervention: {intervention}
- predicted effect: {predicted}
- equations: {equations}
- boundary conditions: {boundary}
- evidence records: {evidence}
- baseline: {baseline}
- killer experiment: {experiment}
- kill condition: {kill}
- buyer: {buyer}

ADVERSARIAL PRIOR-ART RECORDS FOUND (independent retrieval):
{prior_art_lines}

ATTACK ALL EIGHT SURFACES. For each, output one block:
ATTACK <surface>: <your strongest attack on that surface>
VERDICT <surface>: KILL | WOUND | HOLDS
BASIS <surface>: <the concrete basis — a specific number, record, physical law, or manufacturing fact. "Seems unlikely" is not a basis.>

Rules:
- A KILL on mechanism/physics means: the causal chain violates a physical law or the phenomenon does not produce the predicted effect at the stated conditions.
- A KILL on evidence means: the cited records do not actually support the mechanism claims.
- A KILL on prior_art means: a retrieved record already teaches the same mechanism+intervention+effect.
- A KILL on experiment_design means: no experimental outcome in the design can kill the mechanism (unfalsifiable).
- Be specific. Cite record ids, equations, or laws. Blanket skepticism without basis scores as HOLDS.
FINAL: <SURVIVED | KILLED>, followed by the single most dangerous surviving objection.
"""

KNOWN_DEFECT_PROMPT = """You are a hostile independent engineering attacker. Attack this candidate:

CANDIDATE:
- name: {name}
- problem: {problem}
- mechanism chain: {mechanism}
- predicted effect: {predicted}
- kill condition: {kill}

Output the same ATTACK/VERDICT/BASIS blocks for: mechanism, physics, experiment_design, and a FINAL: <SURVIVED | KILLED> line."""


def _evidence_lines(candidate: Dict[str, Any],
                    pool: List[Dict[str, Any]], limit: int = 6) -> str:
    by_id = {str(r.get("record_id") or r.get("id")): r for r in pool}
    out = []
    for rid in (candidate.get("evidence_refs") or [])[:limit]:
        r = by_id.get(str(rid))
        if r:
            out.append(f"- [{rid}] {str(r.get('title') or '')[:120]}")
    return "\n".join(out) or "(no evidence records bound)"


def _prior_art_lines(pa: Dict[str, Any], limit: int = 8) -> str:
    lines = []
    for r in (pa.get("relevant_records") or [])[:limit]:
        lines.append(
            f"- [{r.get('record_id')}] ({r.get('perspective')}) "
            f"{str(r.get('title') or '')[:120]}")
    return "\n".join(lines) or ("(prior-art retrieval found no "
                                "relevant records — attack on that "
                                "basis alone is NOT allowed)")


def build_attack_prompt(candidate: Dict[str, Any],
                        pool: List[Dict[str, Any]],
                        prior_art: Dict[str, Any]) -> str:
    ke = candidate.get("killer_experiment") or {}
    return ATTACK_PROMPT.format(
        name=str(candidate.get("technology_name") or "")[:120],
        problem=str(candidate.get("problem") or "")[:400],
        mechanism=" -> ".join(str(s) for s in
                              candidate.get("causal_chain") or [])[:600],
        phenomenon=str(candidate.get("unexploited_phenomenon") or "")[:300],
        intervention=str(candidate.get("intervention") or "")[:400],
        predicted=str(candidate.get("predicted_effect") or "")[:400],
        equations="; ".join(candidate.get("equations") or [])[:300],
        boundary=str(candidate.get("boundary_conditions") or "")[:300],
        evidence=_evidence_lines(candidate, pool),
        baseline=str((candidate.get("baseline") or {}).get(
            "baseline_incumbent") or "")[:300],
        experiment=str(ke.get("experiment") or "")[:400],
        kill=str(ke.get("kill_condition") or "")[:300],
        buyer=str((candidate.get("commercial_path") or {}).get(
            "buyer") or "")[:200],
        prior_art_lines=_prior_art_lines(prior_art),
    )


def parse_attack(text: str) -> Dict[str, Any]:
    """Deterministic parse of the attacker's output into per-surface
    verdicts + the final verdict."""
    surfaces: Dict[str, Dict[str, str]] = {}
    current = None
    for line in (text or "").splitlines():
        line = line.strip()
        m = re.match(r"^ATTACK\s+([a-z_]+)\s*:\s*(.*)$", line, re.I)
        if m:
            current = m.group(1).lower()
            surfaces.setdefault(current, {"attack": m.group(2)})
            continue
        m = re.match(r"^VERDICT\s+([a-z_]+)\s*:\s*(\S+)", line, re.I)
        if m:
            surfaces.setdefault(m.group(1).lower(), {})[
                "verdict"] = m.group(2).upper()
            continue
        m = re.match(r"^BASIS\s+([a-z_]+)\s*:\s*(.*)$", line, re.I)
        if m:
            surfaces.setdefault(m.group(1).lower(), {})[
                "basis"] = m.group(2)
            continue
    final = "UNKNOWN"
    final_objection = ""
    m = re.search(r"^FINAL\s*:\s*(.+)$", text or "", re.MULTILINE | re.I)
    if m:
        final_line = m.group(1).strip()
        if final_line.upper().startswith("KILLED"):
            final = "KILLED"
        elif final_line.upper().startswith("SURVIVED"):
            final = "SURVIVED"
        final_objection = final_line
    # verdict without a concrete basis is downgraded to HOLDS-with-note
    # (blanket skepticism is not an attack — the prompt's own rule)
    for s, v in surfaces.items():
        if v.get("verdict") in ("KILL", "WOUND") and not v.get("basis"):
            v["verdict"] = "HOLDS"
            v["note"] = "verdict without concrete basis — downgraded by " \
                        "the deterministic parser (blanket skepticism " \
                        "is not an attack)"
    kills = [s for s, v in surfaces.items() if v.get("verdict") == "KILL"]
    wounds = [s for s, v in surfaces.items() if v.get("verdict") == "WOUND"]
    return {
        "attack_version": ATTACK_VERSION,
        "surfaces": surfaces,
        "kill_surfaces": kills,
        "wound_surfaces": wounds,
        "final": final,
        "final_objection": final_objection,
        "final_basis_present": bool(
            any(v.get("basis") for v in surfaces.values())),
    }


def attack_candidate(candidate: Dict[str, Any],
                     pool: List[Dict[str, Any]],
                     prior_art: Dict[str, Any],
                     generator_provider: Optional[str],
                     llm_generate=None) -> Dict[str, Any]:
    """Run one attack. llm_generate: the engine's mechanism-space wrapper
    (provider matrix + recorded hashes). Transport failure => INCOMPLETE
    (Art. LXI), never KILLED."""
    from discovery_fabric.engine.mechanism_space import llm_generate as \
        default_generate
    gen = llm_generate or default_generate
    prompt = build_attack_prompt(candidate, pool, prior_art)
    meta = gen(
        prompt,
        system="You are a hostile independent engineering reviewer. "
               "Every KILL must cite a specific concrete basis.",
        purpose="r411_independent_attack",
        exclude_providers=[generator_provider]
        if generator_provider else None,
        max_tokens=900)
    if not meta.get("ok"):
        return {
            "attack_version": ATTACK_VERSION,
            "candidate_id": candidate.get("candidate_id"),
            "status": "INCOMPLETE_ATTACK_TRANSPORT",
            "error": str(meta.get("error") or meta.get("status"))[:300],
            "survived": None,
            "verdict": "INCOMPLETE",
            "independence_mode": "TRANSPORT_FAILED",
        }
    parsed = parse_attack(meta.get("content") or "")
    independence = (
        "SEPARATE_PROVIDER"
        if (generator_provider and meta.get("provider")
            and meta.get("provider") != generator_provider)
        else "SEPARATE_CONTEXT")
    survived: Optional[bool]
    if parsed["final"] == "KILLED" and parsed["kill_surfaces"]:
        survived = False
    elif parsed["final"] == "SURVIVED":
        survived = True
    else:
        survived = None  # parser could not determine -> INCOMPLETE
    verdict = "KILLED" if survived is False else (
        "SURVIVED" if survived is True else "CONDITIONAL" if parsed[
            "wound_surfaces"] else "INCOMPLETE")
    return {
        "attack_version": ATTACK_VERSION,
        "candidate_id": candidate.get("candidate_id"),
        "status": "OK",
        "attacker_provider": meta.get("provider"),
        "attacker_model": meta.get("model"),
        "generator_provider": generator_provider,
        "independence_mode": independence,
        "independence_note": (
            "the attacker ran on a different provider than the "
            "candidate's generator" if independence == "SEPARATE_PROVIDER"
            else "only one provider credentialed: the attacker ran in a "
                 "separate LLM context (disclosed; NOT labelled "
                 "independent adversarial validation, Art. XLV)"),
        "surfaces": parsed["surfaces"],
        "kill_surfaces": parsed["kill_surfaces"],
        "wound_surfaces": parsed["wound_surfaces"],
        "final_objection": parsed["final_objection"],
        "prompt_hash": meta.get("prompt_hash"),
        "output_hash": meta.get("output_hash"),
        "survived": survived,
        "verdict": verdict,
    }


# ---------------------------------------------------------------------------
# Art. L calibration: known-defect synthetic candidates
# ---------------------------------------------------------------------------

def known_defect_corpus() -> List[Dict[str, Any]]:
    """Synthetic candidates with KNOWN defects (authored here, before the
    campaign, not derived from the attacker's own behavior — Art. VIII).
    The attacker must KILL these; if it does not, its sensitivity is
    recorded and its verdicts carry reduced weight."""
    return [
        {
            "candidate_id": "CAL-CAUSAL-INVALIDITY",
            "technology_name": "Perpetual thermal gradient extractor",
            "problem": "waste heat recovery",
            "causal_chain": [
                "temperature gradient exists between two points",
                "heat flows from cold to hot without work input",
                "net positive power is extracted from a single reservoir"],
            "unexploited_phenomenon": "thermoelectric self-bias",
            "intervention": "a single thermoelectric leg across one "
                            "reservoir",
            "predicted_effect": "net power from a single thermal "
                                "reservoir",
            "equations": ["P = 0 (second law)"],
            "boundary_conditions": "any",
            "evidence_refs": [],
            "baseline": {"baseline_incumbent": "heat engines",
                         "baseline_metric": "requires two reservoirs"},
            "killer_experiment": {
                "experiment": "measure net power of a single-reservoir "
                              "device",
                "kill_condition": "P <= 0",
                "cost_class": "BENCH"},
            "defect_class": "causal-invalidity (violates the second law)",
            "expected_attack_outcome": "KILLED",
        },
        {
            "candidate_id": "CAL-BASELINE-EQUIVALENCE",
            "technology_name": "Identical incumbent with a new name",
            "problem": "pipeline corrosion monitoring cost",
            "causal_chain": [
                "ultrasonic thickness measurement at fixed intervals",
                "wall loss estimated from thickness delta",
                "inspection interval scheduled"],
            "unexploited_phenomenon": "ultrasonic pulse-echo",
            "intervention": "ultrasonic thickness gauges on a schedule",
            "predicted_effect": "same detection performance as the "
                                "incumbent NDT program",
            "equations": ["t = t0 - dR"],
            "boundary_conditions": "same as incumbent",
            "evidence_refs": [],
            "baseline": {
                "baseline_incumbent": "ultrasonic thickness gauges on a "
                                      "schedule (the incumbent itself)",
                "baseline_metric": "identical"},
            "killer_experiment": {
                "experiment": "A/B the candidate against the identical "
                              "incumbent program",
                "kill_condition": "no measurable difference",
                "cost_class": "BENCH"},
            "defect_class": "baseline-equivalence (the candidate IS the "
                            "incumbent)",
            "expected_attack_outcome": "KILLED",
        },
    ]


def run_attacker_calibration(llm_generate=None) -> Dict[str, Any]:
    """Art. L minimum: measure the attacker's sensitivity on the
    known-defect corpus. Results travel with the campaign record; a
    low-sensitivity attacker's verdicts are weighted accordingly (and
    the human surface sees it)."""
    results = []
    for defect in known_defect_corpus():
        pa = {"relevant_records": []}
        rec = attack_candidate(defect, [], pa, generator_provider=None,
                               llm_generate=llm_generate)
        results.append({
            "defect_class": defect["defect_class"],
            "expected": defect["expected_attack_outcome"],
            "attacker_verdict": rec.get("verdict"),
            "killed_as_expected": rec.get("verdict") == "KILLED",
        })
    n_correct = sum(1 for r in results if r["killed_as_expected"])
    return {
        "calibration_version": "R411-ATTACK-CAL-V1",
        "n_defects": len(results),
        "n_killed_as_expected": n_correct,
        "sensitivity_by_defect_class": {
            r["defect_class"]: r["killed_as_expected"] for r in results},
        "false_kill_rate_note": (
            "false-kill rate on known-good mechanisms is not measurable "
            "in this calibration (no known-good corpus is available "
            "pre-campaign); recorded honestly as NOT_MEASURED"),
        "results": results,
    }
