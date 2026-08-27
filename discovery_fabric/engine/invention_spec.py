"""discovery_fabric/engine/invention_spec.py — E2 canonical invention artifact.

The survivor of RANK becomes a canonical INVENTION_SPECIFICATION.json — the
missing bridge between the discovery engine and the dossier factory (CEO E2).

Every field carries an explicit epistemic class (Art. XXVIII no silent
semantic promotion; Art. XXXVIII reality boundary):

    SOURCE_FACT           originated in custodied external evidence
    COMPUTED              derived deterministically by engine code (hashes,
                          scores, counts) from recorded inputs
    MODELLED              LLM-proposed content (mechanism, effect, test)
    ENGINEERING_PROPOSED  derived by deterministic engineering heuristics
    UNKNOWN               absent — recorded, never fabricated (Art. VI/XXV)

Rule enforced by `assert_no_fact_promotion`: a field tagged SOURCE_FACT must
cite at least one evidence id from the frozen custody chain. LLM text can
never be SOURCE_FACT (Art. XXXVIII: AI may propose, AI may not claim reality).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .candidate import Candidate, canonical_json, sha256_obj, utc_now

# The CEO E2 field list — canonical, complete, ordered.
SPEC_FIELDS = [
    "invention_id", "problem", "user_need", "mechanism", "causal_chain",
    "novelty_hypothesis", "prior_art", "distinguishing_features",
    "constraints", "failure_modes", "killer_experiment",
    "engineering_parameters", "evidence", "uncertainties", "assumptions",
    "provenance",
]

EPISTEMIC_CLASSES = ("SOURCE_FACT", "COMPUTED", "MODELLED",
                     "ENGINEERING_PROPOSED", "UNKNOWN")


def tagged(value: Any, epistemic_class: str, stage: str,
           evidence_ids: Optional[List[str]] = None,
           note: str = "") -> Dict[str, Any]:
    """Wrap a value with its epistemic identity. One authority for the whole
    post-RANK pipeline so classes cannot drift between stages (Art. X)."""
    if epistemic_class not in EPISTEMIC_CLASSES:
        raise ValueError(f"unknown epistemic class: {epistemic_class!r}")
    if epistemic_class == "SOURCE_FACT" and not evidence_ids:
        raise ValueError(
            "SOURCE_FACT requires evidence_ids (Art. XXXVIII: no AI-created "
            "reality; every fact cites its custody chain)")
    return {
        "value": value,
        "epistemic_class": epistemic_class,
        "origin_stage": stage,
        "evidence_ids": list(evidence_ids or []),
        "note": note,
    }


def assert_no_fact_promotion(spec: Dict[str, Any]) -> List[str]:
    """Adversarial check (Art. XVII): attempt to find a field tagged
    SOURCE_FACT whose evidence ids do not exist in the spec's evidence
    index. Returns list of violations (empty = pass)."""
    violations: List[str] = []
    known_ev = set((spec.get("_evidence_index") or {}).keys())

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            if node.get("epistemic_class") == "SOURCE_FACT":
                cited = node.get("evidence_ids") or []
                if not cited:
                    violations.append(f"{path}: SOURCE_FACT without evidence_ids")
                else:
                    bad = [c for c in cited if c not in known_ev]
                    if bad:
                        violations.append(
                            f"{path}: cites unknown evidence {bad}")
            for k, v in node.items():
                if k != "_evidence_index":
                    walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk({k: v for k, v in spec.items() if k != "_evidence_index"}, "spec")
    return violations


# --------------------------------------------------------------------------
def _survivor_gate(env: Candidate) -> Dict[str, Any]:
    """Decide whether the envelope is a SURVIVOR eligible for specification.
    No new thresholds: reuse the classification and adjudication recorded by
    the loop itself (Art. XXVII)."""
    eps = env.epistemic_state or {}
    final_status = eps.get("final_status", "")
    verdict = (env.adjudication or {}).get("council", {}).get("verdict", "")
    if final_status in ("AUTOMATED_INVENTION_CANDIDATE",
                        "ESTABLISHED_PROVISIONALLY") and \
            verdict != "INSUFFICIENT_ADJUDICATION":
        return {"survivor": True, "final_status": final_status,
                "verdict": verdict}
    return {"survivor": False, "final_status": final_status,
            "verdict": verdict,
            "reason": ("only a classified candidate with sufficient "
                       "adjudication may be specified (Art. XXVIII: no "
                       "promotion by narrative)")}


def build_invention_spec(env: Candidate, run_ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Construct the canonical invention specification from a survivor
    envelope. Deterministic extraction — no new claims are created here;
    every value is copied from a recorded stage output with its class."""
    gate = _survivor_gate(env)
    mm = env.mechanism_map or {}
    problem = env.problem or {}
    ev_index = {e.get("id"): e for e in (env.evidence or []) if e.get("id")}
    # The operator problem statement is itself a custodied artifact (the run's
    # problem.json, content-hashed) — registered so problem-derived SOURCE_FACT
    # fields can cite it honestly without manufacturing evidence (Art. VI).
    problem_artifact_id = "problem:" + sha256_obj(problem)[:8]
    ev_index[problem_artifact_id] = {
        "id": problem_artifact_id,
        "title": "operator problem statement (problem.json)",
        "content_hash": sha256_obj(problem),
        "custody": "engine run problem.json artifact"}
    ev_ids = sorted(k for k in ev_index if k != problem_artifact_id)

    def ev(*ids: str) -> List[str]:
        return [i for i in ids if i in ev_index]

    invention_id = f"inv:{env.problem_id}:{env.envelope_hash()[:12]}"

    spec: Dict[str, Any] = {}

    spec["invention_id"] = tagged(
        invention_id, "COMPUTED", "INVENTION_SPEC",
        note="deterministic id inv:<problem_id>:<final envelope hash[:12]>")

    spec["problem"] = tagged(
        {"problem_id": env.problem_id,
         "device": problem.get("device", ""),
         "failure": problem.get("failure", ""),
         "failure_mode": problem.get("failure_mode", ""),
         "constraint": problem.get("constraint", "")},
        "SOURCE_FACT", "PROBLEM", evidence_ids=[problem_artifact_id],
        note="operator-supplied problem statement, custodied as the run's "
             "content-hashed problem.json artifact")

    user_need = (problem.get("user_need") or
                 (f"reliable operation of {problem.get('device', 'the device')}"
                  if problem.get("device") else ""))
    spec["user_need"] = tagged(
        user_need, "ENGINEERING_PROPOSED", "INVENTION_SPEC",
        note="derived from problem statement; not independently documented")

    spec["mechanism"] = tagged(
        {"mechanism": mm.get("mechanism", ""),
         "intervention": mm.get("intervention", ""),
         "expected_effect": mm.get("expected_effect", ""),
         "mechanism_source_span": mm.get("mechanism_source_span", "")},
        "MODELLED", "SYNTHESIZE",
        note="LLM-proposed transfer mechanism from custodied evidence; "
             "proposal, not fact (Art. XVIII)")

    raw = mm.get("raw_candidate") or {}
    spec["causal_chain"] = tagged(
        {"source_observation": (ev_index[raw.get("source_evidence", {})
                                 .get("source_id", "")].get("title", "")
                                 if raw.get("source_evidence", {}).get("source_id")
                                 in ev_index else "UNKNOWN"),
         "mechanism": mm.get("mechanism", ""),
         "intervention_site": problem.get("device", ""),
         "expected_effect": mm.get("expected_effect", ""),
         "falsification_test": mm.get("falsification_test", "")},
        "MODELLED", "SYNTHESIZE",
        note="source -> mechanism -> intervention -> effect chain; "
             "links are proposals until physically observed")

    novelty = {
        "collision_novelty_risk": (env.collision_results or {}).get("novelty_risk"),
        "prior_art_status": (env.prior_art or {}).get("prior_art_status"),
        "multi_source_directions": {
            d: {"sources_recorded": len(((env.multi_source or {}).get(d) or {})
                                        .get("searches", [])),
                "sources_errored": len([s for s in ((env.multi_source or {})
                                                    .get(d) or {})
                                        .get("searches", []) if s.get("error")])}
            for d in ("discovery", "destruction", "transfer", "reality")
            if (env.multi_source or {}).get(d)},
    }
    spec["novelty_hypothesis"] = tagged(
        novelty, "COMPUTED", "COLLISION",
        note="novelty is a HYPOTHESIS bounded by searched sources; zero hits "
             "is not proof of novelty (Art. XXI.2)")

    spec["prior_art"] = tagged(
        {"status": (env.prior_art or {}).get("prior_art_status", ""),
         "legacy_status": (env.prior_art or {}).get("legacy_status", ""),
         "nearest": (env.collision_results or {}).get("nearest_prior_art", []),
         "queries": (env.collision_results or {}).get("patent", {}).get("queries", []),
         "scientific": ((env.prior_art or {}).get("scientific_report") or {})
                       .get("results", [])[:5]},
        "COMPUTED", "COLLISION",
        note="search RESULTS with source errors preserved as UNRESOLVED, "
             "never converted to absence (Art. XXV)")

    spec["distinguishing_features"] = tagged(
        {"intervention": mm.get("intervention", ""),
         "vs_nearest_prior_art": [
             {"title": p.get("title"), "patent_id": p.get("patent_id")}
             for p in (env.collision_results or {})
             .get("nearest_prior_art", [])],
         "note": "differences are asserted by synthesis and NOT yet claim-"
                 "audited against the nearest patents"},
        "MODELLED", "SYNTHESIZE",
        note="claim-level differentiation requires the inspection action "
             "recorded in next_best_action")

    constraints = {
        "stated_constraint": problem.get("constraint", ""),
        "failure_mode_of_device": problem.get("failure_mode", ""),
    }
    spec["constraints"] = tagged(constraints, "SOURCE_FACT", "PROBLEM",
                                 evidence_ids=[problem_artifact_id],
                                 note="operator-stated constraints, custodied "
                                      "with the problem.json artifact")

    fms: List[Dict[str, Any]] = []
    for dim, verdict in (env.attack_results or {}).get("attacks", {}).items():
        fms.append({
            "dimension": dim, "attack_verdict": verdict,
            "epistemic_class": "COMPUTED",
            "origin_stage": "ATTACK"})
    spec["failure_modes"] = tagged(
        fms, "COMPUTED", "ATTACK",
        note="adversarial dimensions recorded by the attack engine")

    ke = env.killer_experiment or {}
    spec["killer_experiment"] = tagged(
        {"selected": (ke.get("selected") or {}).get("name", "UNKNOWN"),
         "eig": (ke.get("selected") or {}).get("eig"),
         "eig_per_cost": (ke.get("selected") or {}).get("eig_per_cost"),
         "definition": (ke.get("selected") or {}).get("definition", ""),
         "hypotheses": ke.get("hypotheses", []),
         "options_ranked": ke.get("options_ranked", []),
         "epistemic_note": ke.get("epistemic_note", "")},
        "COMPUTED", "KILLER_EXPERIMENT",
        note="Bayesian EIG over MODEL_DERIVED priors; no physical claim")

    spec["engineering_parameters"] = tagged(
        {}, "UNKNOWN", "INVENTION_SPEC",
        note="no engineering parameters exist yet; physical geometry, "
             "materials and setpoints are ENGINEERING_PROPOSED at best and "
             "are produced by the engineering specification stage, never "
             "invented here")

    spec["evidence"] = tagged(
        [{"id": e.get("id"), "title": e.get("title"),
          "source_uri": e.get("source_uri"), "doi": e.get("doi"),
          "content_hash": e.get("content_hash"),
          "frozen": bool(e.get("frozen", e.get("custody")))} for e in env.evidence],
        "SOURCE_FACT", "RETRIEVE+FREEZE",
        evidence_ids=ev_ids or None,
        note="custodied evidence with content hashes") if env.evidence else \
        tagged([], "UNKNOWN", "RETRIEVE",
               note="no evidence reached the envelope")

    uncertainties: List[Dict[str, Any]] = []
    for c in (env.contradictions or {}).get("contradictions", []):
        if c.get("currently_unresolved"):
            uncertainties.append({
                "contradiction_id": c.get("contradiction_id"),
                "description": c.get("description"),
                "severity": c.get("severity")})
    for src_err in (env.collision_results or {}).get(
            "patent", {}).get("source_errors", []):
        uncertainties.append({
            "unresolved_source": src_err.get("query"),
            "error": src_err.get("error")})
    spec["uncertainties"] = tagged(
        uncertainties, "COMPUTED", "CONTRADICTION",
        note="unresolved contradictions and source failures preserved "
             "as unknowns (Art. XXV)")

    spec["assumptions"] = tagged(
        [{"assumption": "mechanism transfers across domain context",
          "basis": "MODELLED", "test": mm.get("falsification_test", "")},
         {"assumption": "searched sources approximate the prior-art universe",
          "basis": "MODELLED",
          "test": "expand sources (see next_best_action)"}],
        "MODELLED", "INVENTION_SPEC",
        note="explicit assumptions each carrying its own falsification path")

    spec["provenance"] = tagged(
        {"run_id": run_ctx.get("run_id"),
         "final_envelope_hash": env.envelope_hash(),
         "final_status": gate.get("final_status"),
         "adjudication_verdict": gate.get("verdict"),
         "ranking": env.ranking,
         "survivor_gate": gate,
         "code_commit": (env.provenance or {}).get("code_commit"),
         "built_at": utc_now()},
        "COMPUTED", "INVENTION_SPEC",
        note="every value above traces to a stage output in the envelope")

    # Non-canonical companions (underscore = not part of the CEO field list,
    # used by downstream machinery and the adversarial checker)
    spec["_evidence_index"] = ev_index
    spec["_survivor_gate"] = gate
    spec["_spec_hash"] = sha256_obj(
        {k: v for k, v in spec.items() if not k.startswith("_")})

    violations = assert_no_fact_promotion(spec)
    spec["_integrity"] = {
        "no_fact_promotion_violations": violations,
        "passed": not violations,
        "checked_at": utc_now(),
    }
    return spec


def spec_violations_or_raise(spec: Dict[str, Any]) -> None:
    v = spec.get("_integrity", {}).get(
        "no_fact_promotion_violations", ["_integrity missing"])
    if v:
        raise RuntimeError(
            f"invention spec integrity FAILED: {v} (Art. XXXVIII)")


def to_canonical_json(spec: Dict[str, Any]) -> str:
    return canonical_json({k: v for k, v in spec.items()
                           if not k.startswith("_")})
