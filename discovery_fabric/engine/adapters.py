"""discovery_fabric/engine/adapters.py — D5 runtime adapters.

Each adapter wraps exactly ONE canonical implementation chosen in
RUNTIME_CAPABILITY_REGISTRY.json (with rationale and rejected alternatives).
Adapters translate between the canonical envelope (candidate.py) and the
legacy module interfaces. They contain glue — never duplicated business
logic, never copies of historical round scripts.

Failure doctrine (Constitution):
  - No fallback epistemology (Art. IV): a failed external stage records an
    explicit failure; downstream stages depending on it record
    SKIPPED_UPSTREAM_FAILURE. Nothing is silently degraded into "success".
  - Unknown stays unknown (Art. XXV): unresolved external results (e.g. a
    dead patent source) become UNRESOLVED_*, never "no prior art exists".
  - Explicit vocabulary promotion (Art. XXVII): the legacy a2 prior-art
    status vocabulary is translated to the classify/v4_corrections state
    vocabulary by an explicit, documented map below.
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from .candidate import Candidate, sha256_obj, utc_now

REPO_ROOT = Path(__file__).resolve().parents[2]

# --------------------------------------------------------------------------
# Credential bootstrap (handles the repo's two credential mechanisms).
# Mechanism 1: env vars OPENROUTER_API_KEY / NVIDIA_API_KEY — but a2 modules
# capture them AT IMPORT, so this must run before those modules are imported.
# Mechanism 2: KEY=VALUE config file `.env.keys` (prior_art_v2 / elite_v3).
# --------------------------------------------------------------------------

def load_credentials(path: Optional[str] = None) -> Dict[str, str]:
    """Populate os.environ from <repo>/.env.keys (if present). Idempotent."""
    loaded: Dict[str, str] = {}
    p = Path(path) if path else REPO_ROOT / ".env.keys"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if k and v and not os.environ.get(k):
                os.environ[k] = v
                loaded[k] = f"<set:{len(v)} chars>"
    return loaded


def _import_with_env(module: str):
    load_credentials()
    return importlib.import_module(module)


def _load_by_path(name: str, relpath: str):
    """Import a submodule without executing its package __init__ chain."""
    import sys
    full = REPO_ROOT / relpath
    spec = importlib.util.spec_from_file_location(name, full)
    mod = importlib.util.module_from_spec(spec)
    # Required: register before exec so dataclasses.asdict() can resolve
    # cls.__module__ (Art. XXIV: exact mechanics matter).
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# Explicit prior-art vocabulary promotion map (Art. XXVII).
# Legacy a2/prior_art.py statuses -> classify/v4_corrections state vocabulary.
# Each mapping records provenance, rationale and uncertainty. The legacy
# 'LIKELY_PRIOR_ART_EXISTS' is EuropePMC-abstract-limited evidence, NOT a
# confirmed specific disclosure: promoting it to a KILL state would convert
# unresolved into negative evidence (forbidden by Art. XXV) — it maps to
# UNRESOLVED_INSUFFICIENT_EVIDENCE instead, and the COLLISION stage performs
# the patent-grade search that CAN legitimately produce SPECIFIC_DISCLOSURE.
# --------------------------------------------------------------------------

PRIOR_ART_STATUS_MAP = {
    "NO_MATCHING_EVIDENCE_FOUND": {
        "mapped": "NO_MATCH_FOUND",
        "rationale": "direct vocabulary alignment; EuropePMC-only search",
        "epistemic_class": "SEARCH_RESULT",
    },
    "PARTIAL_PRIOR_ART": {
        "mapped": "POSSIBLE_RELEVANCE",
        "rationale": "partial textual overlap in abstracts only",
        "epistemic_class": "SEARCH_RESULT",
    },
    "LIKELY_PRIOR_ART_EXISTS": {
        "mapped": "UNRESOLVED_INSUFFICIENT_EVIDENCE",
        "rationale": ("legacy 'likely' is not a specific disclosure; patent-grade "
                      "collision search is required before any KILL promotion"),
        "epistemic_class": "SEARCH_RESULT",
    },
}

# Deterministic functional-equivalence expansion (Gate-Q doctrine, R274/R275
# worklog lessons: engines fail when they search terminology, not causal
# equivalents). Recorded as MODEL_DERIVED heuristic — small, explicit list.
FUNCTION_EQUIV_EXPANSION = {
    "valve": ["regulator", "flow control element"],
    "osmotic": ["osmolarity", "osmotic pressure"],
    "sensor": ["transducer", "detector"],
    "catheter": ["cannula", "tube assembly"],
    "drainage": ["cerebrospinal fluid shunting", "CSF diversion"],
    "flow": ["perfusion", "fluid transport"],
    "pressure": ["intracranial pressure", "ICP"],
    "coating": ["surface modification", "film"],
    "prediction": ["forecasting", "prognostication"],
}

ADJACENT_INDUSTRY_MAP = {
    "valve": ["automotive fluid systems", "aerospace hydraulics"],
    "sensor": ["automotive sensing", "industrial instrumentation"],
    "battery": ["consumer electronics power", "automotive energy"],
    "coating": ["marine anti-fouling", "medical device surfaces"],
    "catheter": ["minimally invasive surgery", "interventional radiology"],
    "flow": ["process industry fluidics", "aerospace fuel systems"],
}
DEFAULT_ADJACENT = ["aerospace", "automotive", "industrial automation"]


def _keyword_hits(text: str, table: Dict[str, List[str]]) -> List[str]:
    t = text.lower()
    out: List[str] = []
    for k, vs in table.items():
        if k in t:
            out.extend(vs)
    return out


def _engine_result(apply_to: Dict[str, Any], **meta) -> Dict[str, Any]:
    d = {"_engine_result": True, "apply_to": apply_to}
    d.update(meta)
    return d


def _first(evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    return evidence[0] if evidence else {}


# ==========================================================================
# Adapters
# ==========================================================================

class BaseAdapter:
    capability_id = "BASE"
    module_path = ""
    canonical_fn = ""
    needs_network = False
    depends_on: List[str] = []

    input_contract = {}
    output_contract = {}
    provenance_contract = "adapter records module_path, function, args_sha256, utc time"

    def execute(self, env: Candidate, run_ctx: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class A2RetrievalAdapter(BaseAdapter):
    """Canonical: discovery_fabric/a2/retrieve.py::retrieve (ACTIVE)."""
    capability_id = "A2_RETRIEVAL"
    module_path = "discovery_fabric/a2/retrieve.py"
    canonical_fn = "retrieve(problem)"
    needs_network = True

    input_contract = {"problem": "problem dict (device/failure/constraint/...)"}
    output_contract = "envelope.evidence = list of evidence dicts (content_hashed)"

    def execute(self, env, run_ctx):
        mod = _import_with_env("discovery_fabric.a2.retrieve")
        items = mod.retrieve(env.problem) or []
        return _engine_result(
            {"evidence": items,
             "evidence_ids": [i.get("id", "") for i in items]},
            retrieved_count=len(items))


class EvidenceFreezeAdapter(BaseAdapter):
    """Canonical: orchestrator/evidence_custody.py::promote_to_evidence +
    snapshot hashing pattern from a2/run.py FREEZE (snapshot sha256)."""
    capability_id = "EVIDENCE_FREEZE"
    module_path = "orchestrator/evidence_custody.py"
    canonical_fn = "promote_to_evidence(record, source, query, class, binding)"
    depends_on = ["A2_RETRIEVAL"]

    def execute(self, env, run_ctx):
        ec = importlib.import_module("orchestrator.evidence_custody")
        records = []
        for it in env.evidence:
            rec = ec.promote_to_evidence(
                record={"record_id": it.get("id", ""),
                        "raw_content": it.get("abstract", ""),
                        "exact_span": (it.get("abstract") or "")[:500],
                        "content_hash": it.get("content_hash", ""),
                        "url": it.get("source_uri", ""),
                        "doi": it.get("doi", "")},
                source=it.get("source", "UNKNOWN"),
                query=run_ctx.get("problem_id", ""),
                evidence_class="SCIENTIFIC_ABSTRACT",
                proposition_binding="candidate_mechanism_input")
            if rec is not None:
                records.append(rec)
        ok = all(r.verify() for r in records) if records else False
        snapshot = {
            "run_id": run_ctx["run_id"],
            "problem_id": env.problem_id,
            "frozen_at": utc_now(),
            "evidence_count": len(env.evidence),
            "custody_records": [asdict(r) for r in records],
            "hash_verification_all_pass": ok,
        }
        snapshot["snapshot_hash"] = sha256_obj(snapshot)
        return _engine_result(
            {"provenance": {**env.provenance, "evidence_freeze": snapshot}},
            custody_records=len(records), hash_ok=ok)


class SynthesizeAdapter(BaseAdapter):
    """Canonical: discovery_fabric/a2/synthesize.py::synthesize (ACTIVE)."""
    capability_id = "SYNTHESIS"
    module_path = "discovery_fabric/a2/synthesize.py"
    canonical_fn = "synthesize(problem, evidence)"
    needs_network = True
    depends_on = ["A2_RETRIEVAL"]

    def execute(self, env, run_ctx):
        if not env.evidence:
            raise RuntimeError(
                "synthesis impossible: zero evidence items retrieved (explicit)")
        mod = _import_with_env("discovery_fabric.a2.synthesize")
        cand = mod.synthesize(env.problem, env.evidence)
        if not cand:
            # E1 semantics: distinguish credential absence from mechanism
            # failure (Art. XXIX). PROVIDER_UNAVAILABLE is infrastructure,
            # never a negative-knowledge event and never NO_INVENTION.
            from .llm_registry import availability_statement
            avail = availability_statement()
            if not avail["any_provider_available"]:
                raise RuntimeError(
                    "PROVIDER_UNAVAILABLE: no LLM provider credential in "
                    f"environment; unblock with env {avail['unblock_with_env']} "
                    "or .env.keys (E1 llm_registry; no silent substitution)")
            raise RuntimeError(
                "synthesize returned None: LLM refused, errored, or produced "
                "an empty intervention (transport/CALL_FAILED — see stage log; "
                "available providers: " + str(avail["available_providers"]) + ")")
        return _engine_result(
            {"candidate_id": cand.get("candidate_id", ""),
             "mechanism_ids": ["mech:" + sha256_obj(
                 cand.get("mechanism", ""))[:12]],
             "mechanism_map": {
                 "mechanism": cand.get("mechanism", ""),
                 "intervention": cand.get("intervention", ""),
                 "expected_effect": cand.get("expected_effect", ""),
                 "falsification_test": cand.get("falsification_test", ""),
                 "mechanism_source_span": cand.get("mechanism_source_span", ""),
                 "raw_candidate": cand},
             "provenance": {**env.provenance, "synthesis": {
                 "model": cand.get("model"),
                 "provider": cand.get("provider"),
                 "transport_status": cand.get("transport_status"),
                 "prompt_hash": cand.get("prompt_hash"),
                 "input_hash": cand.get("input_hash"),
                 "output_hash": cand.get("output_hash"),
                 "synthesis_timestamp": cand.get("synthesis_timestamp")}}},
        model=cand.get("model"), provider=cand.get("provider"))


class EvidenceVerifyAdapter(BaseAdapter):
    """Canonical: discovery_fabric/a2/verify.py::verify_evidence (ACTIVE)."""
    capability_id = "EVIDENCE_VERIFY"
    module_path = "discovery_fabric/a2/verify.py"
    canonical_fn = "verify_evidence(candidate, evidence)"
    depends_on = ["SYNTHESIS"]

    def execute(self, env, run_ctx):
        mod = importlib.import_module("discovery_fabric.a2.verify")
        raw = env.mechanism_map.get("raw_candidate") or {}
        res = mod.verify_evidence(raw, env.evidence)
        return _engine_result(
            {"adjudication": {**env.adjudication,
                              "evidence_verification": res}},
            verified=res.get("verified"))


class MultiSourceDiscoveryAdapter(BaseAdapter):
    """Canonical: orchestrator/multi_source_discovery.py::run_four_search_attack
    (the CEO v28.3 four-direction search: discovery/destruction/transfer/reality)."""
    capability_id = "MULTI_SOURCE_DISCOVERY"
    module_path = "orchestrator/multi_source_discovery.py"
    canonical_fn = "run_four_search_attack(name, mechanism, problem, failure_mode, adjacent)"
    needs_network = True
    depends_on = ["SYNTHESIS"]

    def execute(self, env, run_ctx):
        msd = importlib.import_module("orchestrator.multi_source_discovery")
        mm = env.mechanism_map
        text = " ".join([mm.get("intervention", ""), mm.get("mechanism", ""),
                         env.problem.get("failure", "")]).lower()
        adjacent = _keyword_hits(text, ADJACENT_INDUSTRY_MAP) or DEFAULT_ADJACENT
        res = msd.run_four_search_attack(
            candidate_name=(mm.get("intervention") or env.problem_id)[:100],
            mechanism_description=mm.get("mechanism", "")[:400],
            physical_problem=env.problem.get("failure", "")[:300],
            failure_mode=env.problem.get("failure_mode", ""),
            adjacent_industries=adjacent)
        d = asdict(res) if not hasattr(res, "to_dict") else res.to_dict()
        d["adjacent_industries_derivation"] = {
            "value": adjacent, "epistemic_class": "MODEL_DERIVED",
            "method": "keyword map ADJACENT_INDUSTRY_MAP in adapters.py"}
        sources_hit = []
        for direction in ("discovery", "destruction", "transfer", "reality"):
            for s in (d.get(direction) or {}).get("searches", []):
                if s.get("total") not in (None, 0) or s.get("error"):
                    sources_hit.append(
                        {"source": s.get("source"), "total": s.get("total"),
                         "error": s.get("error")})
        d["sources_hit"] = sources_hit
        return _engine_result({"multi_source": d},
                              directions=["discovery", "destruction",
                                          "transfer", "reality"])


class CollisionEngineAdapter(BaseAdapter):
    """Canonical composite (R376 mechanism-centered collision):
    patent side = prior_art_v2.collision_resolution.run_collision —
    multi-query ladder (entity/mechanism/distinguishing/adjacent) over
    google_patents + lens_patent, mechanism-level adjudication against
    the candidate profile, deterministic family clustering, and a
    resolution state machine (RESOLVED_DIFFERENTIATED /
    RESOLVED_ANTICIPATED / UNRESOLVED_*). Scientific side =
    a2/prior_art.search_prior_art (EuropePMC, keyword_form queries).
    Rejected alternatives (recorded): scripts/r258+r259 one-shot round
    scripts (not importable); retrieval_v4 full stack (requires NVIDIA
    key; promoted later)."""
    capability_id = "COLLISION_ENGINE"
    module_path = ("discovery_fabric/prior_art_v2/collision_resolution.py + "
                   "discovery_fabric/a2/prior_art.py")
    canonical_fn = "run_collision (mechanism-centered) + search_prior_art"
    needs_network = True
    depends_on = ["SYNTHESIS"]

    def execute(self, env, run_ctx):
        # ---------------- scientific side (EuropePMC) -------------------
        # QUERY-FORM (R375/R376): keyword_form of device+failure and of
        # the mechanism — the old raw '{device} {intervention[:50]}'
        # queries measured as filler-polluted ('knee prosthesis Implement
        # a comprehensive post-market surveillance').
        pa = importlib.import_module("discovery_fabric.a2.prior_art")
        mm = env.mechanism_map
        intervention = mm.get("intervention", "") or env.problem.get("failure", "")
        from discovery_fabric.source_registry.query_relevance import (
            keyword_form as _kwf)
        device = env.problem.get("device", "")
        failure = env.problem.get("failure", "")
        sci_queries = [
            _kwf(f"{device} {failure}", max_terms=6),
            _kwf(str(mm.get("mechanism") or intervention), max_terms=6),
        ]
        sci_queries = [q for q in sci_queries if q.strip()] or \
            [_kwf(intervention, max_terms=6)]
        sci = pa.search_prior_art_with_queries(sci_queries)
        legacy = sci.get("prior_art_status", "")
        mapping = PRIOR_ART_STATUS_MAP.get(legacy)
        if mapping is None:
            raise RuntimeError(
                f"unmapped legacy prior-art status: {legacy!r} — refuse to guess "
                "(Art. XXVII: no silent semantic promotion)")

        # ---------------- patent side: mechanism-centered collision -----
        # R376 (CEO prior-art differentiation + resolution directive):
        # the measured defects (F/E/B/M, PRIOR_ART_FAILURE_TRACE.json)
        # are fixed HERE — multi-query ladder around the mechanism and
        # distinguishing technical features, two patent sources,
        # mechanism-level adjudication BEFORE nearest-prior-art status,
        # family clustering, honest resolution states.
        cr = importlib.import_module(
            "discovery_fabric.prior_art_v2.collision_resolution")
        collision = cr.run_collision(mm, env.problem)
        resolution = collision["differentiation_resolution"]
        novelty_risk = collision["novelty_risk"]

        collision["scientific"] = {
            "legacy_status": legacy,
            "mapped_status": mapping["mapped"],
            "mapping_rationale": mapping["rationale"],
            "result_count": sci.get("result_count"),
            "results": sci.get("results", []),
            "queries": sci.get("queries", []),
            "limitations": sci.get("limitations", []),
        }
        # prior_art_status: the PATENT-SIDE resolution state is the
        # prior-art position (patents are the differentiation universe);
        # the scientific mapping stays recorded alongside (no silent
        # promotion of literature evidence either way — Art. XXVII)
        collision["prior_art_status"] = resolution["state"]
        collision["prior_art_status_basis"] = {
            "authority": "patent-side differentiation_resolution",
            "scientific_mapped_status": mapping["mapped"],
            "note": ("scientific (EuropePMC) status recorded; the "
                     "prior-art POSITION comes from the patent-side "
                     "resolution with per-family evidence tiers"),
        }

        prior_art_ids = [p.get("patent_id") for p in
                         collision.get("nearest_prior_art", [])
                         if p.get("patent_id")] or \
                        [h.get("patent_id") for h in
                         (collision.get("patent", {}).get("hits") or [])
                         if h.get("patent_id")]
        return _engine_result(
            {"collision_results": collision,
             "prior_art": {"prior_art_status": resolution["state"],
                           "legacy_status": legacy,
                           "differentiation_resolution": resolution,
                           "scientific_report": sci,
                           "state_vocabulary":
                               "collision_resolution R376 + classify/v4"},
             "prior_art_ids": [p for p in prior_art_ids if p]},
            novelty_risk=novelty_risk)


class AttackEngineAdapter(BaseAdapter):
    """Canonical: discovery_fabric/a2/adversarial.py::adversarial_challenge
    (ACTIVE; NVIDIA->OpenRouter; v4_corrections applied inside).
    Rejected: scripts/r255-r257 one-shot optimizers (HISTORICAL)."""
    capability_id = "ATTACK_ENGINE"
    module_path = "discovery_fabric/a2/adversarial.py"
    canonical_fn = "adversarial_challenge(candidate, evidence_verified, prior_art_state)"
    needs_network = True
    depends_on = ["SYNTHESIS", "EVIDENCE_VERIFY", "COLLISION_ENGINE"]

    def execute(self, env, run_ctx):
        mod = _import_with_env("discovery_fabric.a2.adversarial")
        raw = env.mechanism_map.get("raw_candidate") or {}
        ev_ok = bool((env.adjudication.get("evidence_verification") or {})
                     .get("verified", False))
        pa_state = env.prior_art.get("prior_art_status", "UNRESOLVED_INSUFFICIENT_EVIDENCE")
        res = mod.adversarial_challenge(raw, evidence_verified=ev_ok,
                                        prior_art_state=pa_state)
        res = dict(res or {})
        # E1: record which provider actually executed the attack (Art. VI:
        # real transport metadata only; NEVER_CALLED stays NEVER_CALLED).
        res["transport"] = getattr(mod, "_LAST_ATTACK_PROVIDER_META", {})
        return _engine_result({"attack_results": res},
                              overall=res.get("overall"))


class ContradictionQueueAdapter(BaseAdapter):
    """Canonical: orchestrator/contradiction_queue.py (6-field register)."""
    capability_id = "CONTRADICTION_QUEUE"
    module_path = "orchestrator/contradiction_queue.py"
    canonical_fn = "ContradictionQueue.add / to_dict"
    depends_on = ["ATTACK_ENGINE", "COLLISION_ENGINE"]

    def execute(self, env, run_ctx):
        from orchestrator.contradiction_queue import ContradictionQueue
        from orchestrator.evidence_graph import Contradiction
        q = ContradictionQueue()
        n = 0
        attack = env.attack_results or {}
        for dim, verdict in (attack.get("attacks") or {}).items():
            if str(verdict).upper() in ("KILL", "KILLED", "FAIL"):
                q.add(Contradiction(
                    contradiction_id=f"con:attack:{dim}",
                    description=f"attack dimension {dim} returned KILL",
                    claim_or_limitation_affected=dim,
                    severity="HIGH", probability=0.7,
                    evidence_quality="MODERATE", decision_impact=0.8,
                    currently_unresolved=True))
                n += 1
        for iss in ((env.adjudication.get("evidence_verification") or {})
                    .get("issues") or []):
            q.add(Contradiction(
                contradiction_id=f"con:verify:{sha256_obj(iss)[:8]}",
                description=f"evidence verification issue: {iss}",
                claim_or_limitation_affected="evidence_binding",
                severity="MEDIUM", probability=0.5,
                evidence_quality="STRONG", decision_impact=0.5,
                currently_unresolved=True))
            n += 1
        if env.collision_results.get("novelty_risk") == \
                "ADJACENT_COLLISION_CANDIDATES":
            q.add(Contradiction(
                contradiction_id="con:collision:adjacent",
                description="patent-side collision found adjacent candidates; "
                            "claims not yet inspected",
                claim_or_limitation_affected="novelty",
                severity="MEDIUM", probability=0.5,
                evidence_quality="WEAK", decision_impact=0.4,
                currently_unresolved=True))
            n += 1
        d = q.to_dict()
        return _engine_result({"contradictions": d}, added=n)


class KillerExperimentAdapter(BaseAdapter):
    """Canonical: epistemic_integrity/invention_loop_engine/bayesian_eig.py
    (pure Bayesian EIG). Priors are MODEL_DERIVED from adjudication text —
    labeled EXPERT_PRIOR/MODEL_DERIVED explicitly, never EXPERIMENTALLY_ESTIMATED."""
    capability_id = "KILLER_EXPERIMENT"
    module_path = "epistemic_integrity/invention_loop_engine/bayesian_eig.py"
    canonical_fn = "BayesianEIGCalculator.rank_experiments"
    depends_on = ["CONTRADICTION_QUEUE", "SYNTHESIS"]

    def execute(self, env, run_ctx):
        beig = _load_by_path(
            "engine_bayesian_eig",
            "epistemic_integrity/invention_loop_engine/bayesian_eig.py")
        mm = env.mechanism_map
        support = bool((env.adjudication.get("evidence_verification") or {})
                       .get("verified", False))
        prior_hold = 0.6 if support else 0.45
        prov = beig.EIGProvenance(
            source="adjudication.evidence_verification + candidate text",
            epistemic_class=beig.EIGEpistemicClass.MODEL_DERIVED,
            uncertainty="priors/likelihoods derived from text analysis, "
                        "not measurement")
        hypotheses = [
            beig.Hypothesis(
                name="H_effect_holds",
                description=f"expected effect holds: {mm.get('expected_effect','')[:200]}",
                prior_probability=prior_hold,
                provenance=prov),
            beig.Hypothesis(
                name="H_effect_fails",
                description="expected effect does not reproduce outside source context",
                prior_probability=round(1 - prior_hold, 3),
                provenance=prov),
        ]

        def _outcome(name, desc, like):
            return beig.ExperimentalOutcome(
                name=name, description=desc, likelihoods=like, provenance=prov)

        options = []
        if mm.get("falsification_test"):
            options.append({
                "name": "falsification_test_from_candidate",
                "outcomes": [
                    _outcome("effect_reproduces", "candidate effect observed in bench rep",
                             {"H_effect_holds": 0.85, "H_effect_fails": 0.15}),
                    _outcome("effect_fails", "candidate effect not observed",
                             {"H_effect_holds": 0.10, "H_effect_fails": 0.90})],
                "cost": 1.0, "risk": 1.0, "feasibility": 1.0})
        unresolved = (env.contradictions or {}).get("unresolved_count", 0)
        if unresolved:
            options.append({
                "name": "contradiction_attacking_experiment",
                "outcomes": [
                    _outcome("contradiction_dissolved",
                             "targeted experiment dissolves the blocking contradiction",
                             {"H_effect_holds": 0.7, "H_effect_fails": 0.2}),
                    _outcome("contradiction_confirmed",
                             "targeted experiment confirms the contradiction",
                             {"H_effect_holds": 0.15, "H_effect_fails": 0.8})],
                "cost": 1.5, "risk": 1.2, "feasibility": 0.9})
        if not options:
            options.append({
                "name": "generic_bench_reproduction",
                "outcomes": [
                    _outcome("reproduces", "independent reproduction",
                             {"H_effect_holds": 0.75, "H_effect_fails": 0.2}),
                    _outcome("does_not_reproduce", "no reproduction",
                             {"H_effect_holds": 0.2, "H_effect_fails": 0.8})],
                "cost": 2.0, "risk": 1.0, "feasibility": 0.8})
        calc = beig.BayesianEIGCalculator()
        ranked = calc.rank_experiments(hypotheses, options)
        best_name, best_trace = ranked[0]
        payload = {
            "hypotheses": [h.to_dict() for h in hypotheses],
            "options_ranked": [
                {"name": nm, "eig": tr.eig, "eig_per_cost": tr.eig_per_cost,
                 "minimum_epistemic_class": str(tr.minimum_epistemic_class),
                 "can_influence_real_experiment": tr.can_influence_real_experiment}
                for nm, tr in ranked],
            "selected": {
                "name": best_name,
                "eig": best_trace.eig,
                "eig_per_cost": best_trace.eig_per_cost,
                "rationale": "highest eig_per_cost (cheapest decisive experiment)",
                "definition": "physical bench/clinical experiment — NOT simulation",
            },
            "epistemic_note": ("all priors MODEL_DERIVED; no EXPERIMENTALLY_ESTIMATED "
                               "inputs exist at this stage (Art. XXVIII/XXXVIII: no "
                               "synthetic shortcut to physical observation)"),
            "timestamp": utc_now(),
        }
        return _engine_result({"killer_experiment": payload},
                              selected=best_name)


class AdjudicationAdapter(BaseAdapter):
    """Deterministic, hash-bound adjudication council. Canonical building
    blocks: a2/verify output, attack verdicts, contradiction register,
    cemetery verdict, collision novelty risk. Rationale for NOT using
    ai_adjudication_ensemble (requires multi-model analyses unavailable at
    HEAD) or deterministic_evidence_arbiter (hardcoded to patent C04-L5) is
    recorded in RUNTIME_CAPABILITY_REGISTRY.json."""
    capability_id = "ADJUDICATION"
    module_path = "discovery_fabric/engine/adapters.py (glue over canonical inputs)"
    canonical_fn = "deterministic check aggregation"
    depends_on = ["EVIDENCE_VERIFY", "ATTACK_ENGINE", "CONTRADICTION_QUEUE",
                  "COLLISION_ENGINE"]

    def execute(self, env, run_ctx):
        ev = env.adjudication.get("evidence_verification") or {}
        attack = env.attack_results or {}
        cemetery = _CemeterySubCheck.verdict(env)
        checks = [
            {"check": "evidence_span_verified", "result": bool(ev.get("verified")),
             "inputs_hash": sha256_obj(ev)},
            {"check": "adversarial_not_killed",
             "result": attack.get("overall") == "PASS",
             "inputs_hash": sha256_obj({k: v for k, v in attack.items()
                                        if k not in ("timestamp",)})},
            {"check": "no_blocking_contradictions",
             "result": (env.contradictions or {}).get("blocking_count", 0) == 0,
             "inputs_hash": sha256_obj(env.contradictions)},
            {"check": "no_specific_prior_disclosure",
             "result": env.prior_art.get("prior_art_status") not in
                       ("SPECIFIC_DISCLOSURE",
                        "IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE",
                        # R376: search-derived specific-disclosure-class
                        # finding (claim/abstract-level full coverage of
                        # mechanism + distinguishing terms; per-family
                        # evidence in collision_results)
                        "RESOLVED_ANTICIPATED"),
             "inputs_hash": sha256_obj(env.prior_art.get("prior_art_status", ""))},
            {"check": "collision_not_unresolved",
             "result": env.collision_results.get("novelty_risk") not in
                       ("UNRESOLVED_INSUFFICIENT_EVIDENCE",),
             "inputs_hash": sha256_obj(env.collision_results.get("novelty_risk"))},
            {"check": "cemetery_not_hard_blocked",
             "result": cemetery.get("verdict") != "BLOCKED",
             "module_path": "orchestrator/mechanism_cemetery.py",
             "inputs_hash": sha256_obj(cemetery.get("full", {}))},
        ]
        failed = [c["check"] for c in checks if not c["result"]]
        if env.attack_results.get("overall") == "EVALUATION_FAILED":
            verdict = "INSUFFICIENT_ADJUDICATION"
        elif failed:
            verdict = "CONTESTED"
        else:
            verdict = "ESTABLISHED_PROVISIONALLY"
        payload = {
            "verdict": verdict,
            "checks": checks,
            "failed_checks": failed,
            "inputs_sha256": sha256_obj({"checks": checks}),
            "note": ("adjudication is deterministic aggregation of stage outputs; "
                     "it never overrides a KILL and never rescues a failed claim "
                     "(Art. VII)"),
            "timestamp": utc_now(),
        }
        return _engine_result(
            {"adjudication": {**env.adjudication, "council": payload},
             "cemetery_check": cemetery},
            verdict=verdict)


class EpistemicClassificationAdapter(BaseAdapter):
    """Canonical: discovery_fabric/a2/classify.py::classify (ACTIVE)."""
    capability_id = "EPISTEMIC_CLASSIFICATION"
    module_path = "discovery_fabric/a2/classify.py"
    canonical_fn = "classify(candidate, evidence_verification, prior_art, adversarial)"
    depends_on = ["ADJUDICATION"]

    def execute(self, env, run_ctx):
        mod = importlib.import_module("discovery_fabric.a2.classify")
        raw = env.mechanism_map.get("raw_candidate") or {}
        res = mod.classify(
            raw,
            env.adjudication.get("evidence_verification") or {},
            {"prior_art_status": env.prior_art.get("prior_art_status",
             "UNRESOLVED_INSUFFICIENT_EVIDENCE")},
            env.attack_results or {})
        return _engine_result({"epistemic_state": res},
                              final_status=res.get("final_status"))


class NextBestActionAdapter(BaseAdapter):
    """Canonical: orchestrator/next_best_action.py (score = gain*p_change*
    impact/cost - redundancy_penalty)."""
    capability_id = "NEXT_BEST_ACTION"
    module_path = "orchestrator/next_best_action.py"
    canonical_fn = "NextBestAction.rank_actions/select_best"
    depends_on = ["CONTRADICTION_QUEUE", "KILLER_EXPERIMENT", "ADJUDICATION"]

    def execute(self, env, run_ctx):
        from orchestrator.next_best_action import Action, NextBestAction
        actions: List[Action] = []
        for c in (env.contradictions or {}).get("contradictions", []):
            if c.get("currently_unresolved"):
                actions.append(Action(
                    action_id=c["contradiction_id"],
                    description=f"attack contradiction: {c['description'][:120]}",
                    evidence_question_id=c["contradiction_id"],
                    provider="internal_attack",
                    expected_information_gain=0.5 * c.get("decision_impact", 0.5) + 0.2,
                    probability_of_decision_change=c.get("probability", 0.5),
                    decision_impact=c.get("decision_impact", 0.5),
                    cost=1.0))
        ke = (env.killer_experiment or {}).get("selected") or {}
        if ke:
            actions.append(Action(
                action_id="action:killer_experiment",
                description=f"run killer experiment: {ke.get('name','')}",
                evidence_question_id="killer_experiment",
                provider="physical_lab",
                expected_information_gain=ke.get("eig", 0.0),
                probability_of_decision_change=0.8,
                decision_impact=0.9,
                cost=max(ke.get("eig_per_cost", 0.5), 0.05) * 2.0))
        if (env.collision_results or {}).get("novelty_risk") == \
                "ADJACENT_COLLISION_CANDIDATES":
            actions.append(Action(
                action_id="action:inspect_patent_claims",
                description="fetch and audit claims of nearest collision patents",
                evidence_question_id="collision_claims",
                provider="google_patents",
                expected_information_gain=0.6,
                probability_of_decision_change=0.6,
                decision_impact=0.7,
                cost=0.5))
        nba = NextBestAction()
        ranked = nba.rank_actions(actions)
        best = nba.select_best(actions)
        payload = {
            "ranked_actions": [a.to_dict() for a in ranked][:8],
            "selected_best": best.to_dict() if best else None,
            "selection_rule": "score = (gain * p_change * impact)/cost - redundancy",
            "timestamp": utc_now(),
        }
        return _engine_result({"next_best_action": payload},
                              n_actions=len(actions))


class PortfolioRankingAdapter(BaseAdapter):
    """Canonical: orchestrator/portfolio.py scoreboard context + deterministic
    candidate score recorded with its formula. This is an ALLOCATION policy,
    not a truth claim (Art. XXVII: explicit formula, no invented threshold)."""
    capability_id = "PORTFOLIO_RANKING"
    module_path = "orchestrator/portfolio.py + deterministic score in adapter"
    canonical_fn = "Portfolio.get_portfolio_scoreboard"
    depends_on = ["ADJUDICATION", "NEXT_BEST_ACTION"]

    def execute(self, env, run_ctx):
        from orchestrator.portfolio import Portfolio
        verdict_weights = {"ESTABLISHED_PROVISIONALLY": 1.0,
                           "CONTESTED": 0.4,
                           "INSUFFICIENT_ADJUDICATION": 0.1}
        adv = env.adjudication.get("council", {}).get("verdict",
                                                      "INSUFFICIENT_ADJUDICATION")
        w_adv = verdict_weights.get(adv, 0.1)
        attack_ok = 1.0 if (env.attack_results or {}).get("overall") == "PASS" else 0.0
        nr = (env.collision_results or {}).get("novelty_risk", "")
        novelty = {"NO_MATCH_FOUND": 1.0,
                   "SEARCHED_NO_DIRECT_TITLE_MATCH": 0.8,
                   "ADJACENT_COLLISION_CANDIDATES": 0.4}.get(nr, 0.2)
        eig_pc = (env.killer_experiment or {}).get("selected", {}).get(
            "eig_per_cost", 0.0)
        score = round(0.35 * w_adv + 0.25 * attack_ok + 0.20 * novelty
                      + 0.20 * min(eig_pc, 1.0), 4)
        portfolio = Portfolio()
        scoreboard = portfolio.get_portfolio_scoreboard()
        payload = {
            "formula": ("score = 0.35*adjudication_w + 0.25*attack_pass "
                        "+ 0.20*novelty_w + 0.20*min(eig_per_cost,1)"),
            "formula_version": "engine-ranking-v1",
            "components": {"adjudication": w_adv, "attack_pass": attack_ok,
                           "novelty": novelty,
                           "eig_per_cost_capped": min(eig_pc, 1.0)},
            "score": score,
            "portfolio_context": {
                "target_invention_count": scoreboard.get("target_invention_count"),
                "survivors": scoreboard.get("survivors"),
                "active": scoreboard.get("active")},
            "is_allocation_policy_not_truth": True,
            "timestamp": utc_now(),
        }
        return _engine_result({"ranking": payload}, score=score)


class MechanismCemeteryAdapter(BaseAdapter):
    """Canonical: orchestrator/mechanism_cemetery.py (append-only negative
    knowledge). CHECK runs inside the loop; UPDATE (save) happens only at
    conductor level after a final KILL/REJECT, keeping D8's stage list exact."""
    capability_id = "MECHANISM_CEMETERY"
    module_path = "orchestrator/mechanism_cemetery.py"
    canonical_fn = "check_candidate_against_cemetery"
    depends_on = ["SYNTHESIS"]

    def execute(self, env, run_ctx):
        mc = importlib.import_module("orchestrator.mechanism_cemetery")
        mm = env.mechanism_map
        desc = " ".join([mm.get("intervention", ""), mm.get("mechanism", ""),
                         mm.get("expected_effect", "")])[:2000]
        res = mc.check_candidate_against_cemetery(desc)
        return _engine_result({"cemetery_check": res},
                              verdict=res.get("verdict"))


class _CemeterySubCheck:
    """Internal helper used by AdjudicationAdapter (keeps D8 stage list exact
    while still consulting negative knowledge inside the loop)."""

    @staticmethod
    def verdict(env) -> Dict[str, Any]:
        try:
            mc = importlib.import_module("orchestrator.mechanism_cemetery")
            mm = env.mechanism_map
            desc = " ".join([mm.get("intervention", ""),
                             mm.get("mechanism", "")])[:2000]
            res = mc.check_candidate_against_cemetery(desc)
            return {"verdict": res.get("verdict"),
                    "hard_blocks": len(res.get("hard_blocks", [])),
                    "warnings": len(res.get("warnings", [])),
                    "lessons_consulted": res.get("total_lessons_consulted"),
                    "full": res}
        except Exception as exc:  # noqa: BLE001
            return {"verdict": "UNRESOLVED", "error": str(exc)}


ADAPTERS = {
    "RETRIEVE": A2RetrievalAdapter(),
    "FREEZE": EvidenceFreezeAdapter(),
    "SYNTHESIZE": SynthesizeAdapter(),
    "VERIFY": EvidenceVerifyAdapter(),
    "MULTI_SOURCE_DISCOVERY": MultiSourceDiscoveryAdapter(),
    "COLLISION": CollisionEngineAdapter(),
    "ATTACK": AttackEngineAdapter(),
    "CONTRADICTION": ContradictionQueueAdapter(),
    "KILLER_EXPERIMENT": KillerExperimentAdapter(),
    "ADJUDICATION": AdjudicationAdapter(),
    "CLASSIFY": EpistemicClassificationAdapter(),
    "NEXT_BEST_ACTION": NextBestActionAdapter(),
    "RANK": PortfolioRankingAdapter(),
    "CEMETERY_CHECK": MechanismCemeteryAdapter(),
}

# Stage order per CEO directive D8 (exact chain; cemetery negative-knowledge
# check is a sub-check of ADJUDICATION; cemetery UPDATE is conductor-level).
STAGE_ORDER = ["RETRIEVE", "FREEZE", "SYNTHESIZE", "VERIFY",
               "MULTI_SOURCE_DISCOVERY", "COLLISION", "ATTACK",
               "CONTRADICTION", "KILLER_EXPERIMENT", "ADJUDICATION",
               "CLASSIFY", "NEXT_BEST_ACTION", "RANK"]
