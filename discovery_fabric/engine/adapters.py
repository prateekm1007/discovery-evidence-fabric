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
import time as _time
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
        for line in p.read_text(encoding="utf-8").splitlines():
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
        "precondition": ("every mandatory query executed OK — the a2 "
                         "layer guarantees this status is derived from "
                         "execution, never from outage (R394 s2)"),
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
    # R394 section 2: search-execution states NEVER map to absence or
    # differentiation. An outage is epistemic UNKNOWN (Art. XXI.3/XXV).
    "SEARCH_FAILED": {
        "mapped": "UNRESOLVED_INSUFFICIENT_EVIDENCE",
        "rationale": ("every scientific-side query failed (provider "
                      "outage/timeout); a search failure is not a "
                      "scientific conclusion — no absence, no "
                      "differentiation permitted from this report"),
        "epistemic_class": "SEARCH_EXECUTION",
        "epistemic_effect": "UNKNOWN",
    },
    "SEARCH_PARTIAL": {
        "mapped": "UNRESOLVED_PARTIAL_EVIDENCE",
        "rationale": ("some queries failed; findings stand as evidence "
                      "but the searched universe is incomplete — no "
                      "clean no-match claim permitted"),
        "epistemic_class": "SEARCH_EXECUTION",
        "epistemic_effect": "UNKNOWN",
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
    # R402 (audit NF-1): depends_on is declared in the STAGE-NAME
    # namespace — the SAME namespace as STAGE_ORDER. The v1 values used
    # capability IDs (A2_RETRIEVAL, SYNTHESIS, EVIDENCE_VERIFY, ...) which
    # resolve to NO stage: 12 of 16 stages' declared dependencies were
    # unresolvable at the time of the R402 audit (HISTORICAL count —
    # the live chain is 15 linear stages + IMPROVE as post-rank
    # kill-point per R515; see STAGE_ORDER below) and any consumer of
    # the declared graph (introspection tooling, auditors, future
    # orchestrators) got a false picture.
    # Contract (pinned by test): every entry resolves to a stage in
    # STAGE_ORDER. capability_id remains the CAPABILITY namespace —
    # the two vocabularies never mix in depends_on.
    depends_on: List[str] = []

    input_contract = {}
    output_contract = {}
    provenance_contract = "adapter records module_path, function, args_sha256, utc time"

    def execute(self, env: Candidate, run_ctx: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class A2RetrievalAdapter(BaseAdapter):
    """Canonical: discovery_fabric/a2/retrieve.py::retrieve (V1) /
    discovery_fabric/retrieval_fabric (V2 — R409 fabric, DEFAULT).

    R409 retrieval-fabric directive: the engine's retrieval universe was
    Europe PMC + OpenAlex (V1, preserved byte-unchanged for historical
    reproduction; its recorded corpus immutable). V2 is the multi-source
    open/free fabric: Europe PMC and OpenAlex become two nodes among
    materially different source families (scholarly graphs, DOI
    registrants, OA journal registry, repository aggregators, theses,
    preprints, patents), with canonical dedup, lineage attribution,
    publication-status labeling, per-run health states and diversity
    measurement. Dispatch is controlled by ENGINE_RETRIEVAL_FABRIC
    (default V2; 'V1' reproduces the legacy two-source pipeline).

    Output contract is UNCHANGED for downstream stages: evidence items
    carry the a2 schema; V2 items add fabric fields (publication_status,
    evidence_lane, canonical_id, ...) additively.
    """
    capability_id = "A2_RETRIEVAL"
    module_path = "discovery_fabric/retrieval_fabric/pipeline.py"
    canonical_fn = "retrieve_fabric(problem) [V2] / retrieve(problem) [V1]"
    needs_network = True

    input_contract = {"problem": "problem dict (device/failure/constraint/...)"}
    output_contract = "envelope.evidence = list of evidence dicts (content_hashed)"

    def execute(self, env, run_ctx):
        import os as _os
        fabric_version = (_os.environ.get("ENGINE_RETRIEVAL_FABRIC",
                                          "V2").strip().upper() or "V2")
        if fabric_version == "V1":
            mod = _import_with_env("discovery_fabric.a2.retrieve")
            items = mod.retrieve(env.problem) or []
            lanes = getattr(mod, "RETRIEVAL_LANES", {}) or {}
            return _engine_result(
                {"evidence": items,
                 "evidence_ids": [i.get("id", "") for i in items],
                 "provenance": {**env.provenance,
                                "retrieval_fabric": {
                                    "version": "V1",
                                    "sources": ["europepmc", "openalex"],
                                    "lane_states": lanes}}},
                retrieved_count=len(items),
                retrieval_fabric_version="V1")
        # V2 (default): the multi-source fabric
        fabric = _import_with_env("discovery_fabric.retrieval_fabric")
        _t0 = _time.monotonic()
        items, report = fabric.retrieve(env.problem)
        _t_fabric = _time.monotonic() - _t0
        stats = report.get("retrieval_stats", {})
        diversity = report.get("retrieval_diversity", {})
        # R449: the EVIDENCE-FABRIC channel — ADDITIVE federated evidence
        # from the HF-hosted production sources (patents / engineering
        # cases / materials / chemistry), normalized into the canonical
        # EvidenceRecord and merged into the SAME evidence pool the V2
        # fabric filled (engine-compatible items; the V2 fabric itself
        # is untouched). The channel is disabled with
        # ENGINE_EVIDENCE_FABRIC=0 (the comparison experiment's Arm A).
        ef_provenance = None
        try:
            from discovery_fabric import evidence_fabric as _ef
            if _ef.enabled():
                ef_items, ef_report = _ef.retrieve_evidence(env.problem)
                if ef_items:
                    # additive merge: evidence-fabric items carry the a2
                    # schema + `evidence_fabric` fields; ids are
                    # deterministic (ev:<hash>) so dedup with the V2 pool
                    # is by id
                    have = {i.get("id") for i in items}
                    items = items + [i for i in ef_items
                                     if i.get("id") not in have]
                ef_provenance = {
                    "version": ef_report.get("fabric_version"),
                    "federated": True,
                    "production_sources": sorted({
                        c.get("source_id") for c in
                        ef_report.get("channels", [])
                        if c.get("state") in ("SUCCESS", "EMPTY_RESULT")}),
                    "channels": len(ef_report.get("channels", [])),
                    "unknown_channels": len(
                        ef_report.get("source_failures", [])),
                    "substitutions": ef_report.get("substitutions", []),
                    "coverage_limitations": ef_report.get(
                        "coverage_limitations", []),
                    "pool_items": ef_report.get("pool", {}).get("items", 0),
                    "records_in_custody": len(
                        ef_report.get("records", [])),
                    "report_persisted": "EVIDENCE_FABRIC_REPORT.json",
                    # R521 observability-only: compact per-channel
                    # timing (the full report may be pruned from
                    # snapshots by size; this compact list rides the
                    # envelope which is always snapshotted). Read-only
                    # aggregation — no behavior change.
                    "channel_latencies": [
                        {"source_id": c.get("source_id"),
                         "state": c.get("state"),
                         "attempted_as": c.get("attempted_as"),
                         "latency_s": c.get("latency_s"),
                         "records": c.get("records")}
                        for c in ef_report.get("channels", [])],
                    "channel_latency_sum_s": ef_report.get(
                        "channel_latency_sum_s"),
                    "pacing_s": ef_report.get("pacing_s"),
                }
        except Exception as _ef_exc:  # noqa: BLE001 — infra, not verdict
            ef_provenance = {
                "state": "CHANNEL_ERROR",
                "reason": f"{type(_ef_exc).__name__}: {_ef_exc}"[:300],
                "note": "the evidence-fabric channel failed; the V2 fabric "
                        "pool is unchanged — an infrastructure state, "
                        "never a scientific result (Art. LXI)",
            }
        if ef_provenance is not None:
            # persist the full fabric report inside the run directory
            # (custody: an independent auditor can reconstruct the
            # federated retrieval event from it)
            try:
                import json as _json
                _p = Path(run_ctx.get("out_dir") or ".")
                _p.mkdir(parents=True, exist_ok=True)
                (_p / "EVIDENCE_FABRIC_REPORT.json").write_text(
                    _json.dumps(ef_report, indent=1, ensure_ascii=False,
                                default=str), encoding="utf-8")
            except Exception:  # noqa: BLE001 — best-effort persistence
                pass
        # R512: persist the retrieval attribution record inside the run
        # directory (same custody pattern as EVIDENCE_FABRIC_REPORT.json:
        # the next audit reads run bytes, not ephemeral module state).
        # Skipped when the caller supplies no out_dir (never write test
        # CWD pollution into the repo — production always passes the
        # run directory).
        try:
            import json as _json2
            _out_dir = run_ctx.get("out_dir")
            if _out_dir:
                _p2 = Path(_out_dir)
                _p2.mkdir(parents=True, exist_ok=True)
                (_p2 / "RETRIEVAL_ATTRIBUTION.json").write_text(
                    _json2.dumps(report.get("retrieval_attribution", {}),
                                 indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        except Exception:  # noqa: BLE001 — best-effort persistence
            pass
        # R517 Phase 1: per-operation retrieval attribution is
        # durable via the envelope (not the sidecar file alone —
        # the sidecar is best-effort and not yet on the durable
        # branch push allowlist). The envelope's provenance is the
        # single durable authority (Art. X).
        _retr_attr = report.get("retrieval_attribution") or {}
        return _engine_result(
            {"evidence": items,
             "evidence_ids": [i.get("id", "") for i in items],
             "provenance": {**env.provenance,
                            "retrieval_fabric": {
                                "version": report.get("fabric_version"),
                                "primary_query": report.get("primary_query"),
                                "query_variant_count": len(
                                    report.get("query_variants", [])),
                                "sources_attempted": stats.get(
                                    "sources_attempted", []),
                                "sources_succeeded": stats.get(
                                    "sources_succeeded", []),
                                "sources_failed": stats.get(
                                    "sources_failed", []),
                                "sources_rate_limited": stats.get(
                                    "sources_rate_limited", []),
                                # R522: centralized source exclusion is a
                                # routing state, never a provider outcome
                                # — it rides the durable envelope so an
                                # after-arm run is byte-distinguishable
                                # from a baseline run at the envelope
                                # level (Art. XXI.3 / LXI / LXII).
                                "sources_excluded": stats.get(
                                    "sources_excluded", []),
                                "unique_source_families": diversity.get(
                                    "unique_source_families", []),
                                "independent_source_families": diversity.get(
                                    "independent_source_families"),
                                "source_independence_score": diversity.get(
                                    "source_independence_score"),
                                "retrieval_blind_spots": report.get(
                                    "retrieval_blind_spots", []),
                                "canonical_record_count": report.get(
                                    "canonical_record_count"),
                                "evidence_fabric": ef_provenance,
                                "retrieval_attribution": _retr_attr,
                            }}},
            retrieved_count=len(items),
            retrieval_fabric_version="V2",
            retrieval_attribution=_retr_attr)


class EvidenceFreezeAdapter(BaseAdapter):
    """Canonical: orchestrator/evidence_custody.py::promote_to_evidence +
    snapshot hashing pattern from a2/run.py FREEZE (snapshot sha256)."""
    capability_id = "EVIDENCE_FREEZE"
    module_path = "orchestrator/evidence_custody.py"
    canonical_fn = "promote_to_evidence(record, source, query, class, binding)"
    depends_on = ["RETRIEVE"]

    def execute(self, env, run_ctx):
        # R537 §E: expose the verified custody ID set to the FREEZE-
        # observing downstream adapters (SYNTHESIZE / VERIFY) so the
        # machine-join can prove whether the post-FREEZE pipeline
        # consumed the frozen / custodied evidence authority.  Purely
        # additive telemetry; the admission semantics are UNCHANGED.
        env.evidence_freeze_snapshot = dict(
            (env.provenance or {}).get("evidence_freeze") or {})
        ec = importlib.import_module("orchestrator.evidence_custody")
        input_count = len(env.evidence or [])
        records = []
        promotion_attempts = 0
        failed_custody = 0
        hash_pass = 0
        hash_fail = 0
        for it in env.evidence:
            promotion_attempts += 1
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
            else:
                failed_custody += 1
        verified = []
        for r in records:
            if r.verify():
                verified.append(r)
                hash_pass += 1
            else:
                hash_fail += 1
        ok = bool(records) and (hash_fail == 0)
        snapshot = {
            "run_id": run_ctx["run_id"],
            "problem_id": env.problem_id,
            "frozen_at": utc_now(),
            "evidence_count": len(env.evidence),
            "custody_records": [asdict(r) for r in records],
            "hash_verification_all_pass": ok,
            # R536 §5: observational custody cardinality (input ->
            # promotion -> verified -> final frozen), with source
            # lineage.  Purely additive telemetry; the admission
            # semantics (custody_records / hash_ok) are UNCHANGED.
            "freeze_observational": {
                "input_evidence_count": input_count,
                "promotion_attempts": promotion_attempts,
                "custody_promoted_count": len(records),
                "custody_failed_count": failed_custody,
                "hash_verification_pass_count": hash_pass,
                "hash_verification_fail_count": hash_fail,
                "final_frozen_evidence_count": len(verified),
                "lineage": [
                    {"source": it.get("source", "UNKNOWN"),
                     "id": it.get("id", ""),
                     "content_hash": it.get("content_hash", "")}
                    for it in (env.evidence or [])],
                # R537 §E: the verified custody ID set (the records
                # that passed hash verification) — the machine-join
                # input that proves whether downstream consumed the
                # frozen authority.  Purely additive telemetry; the
                # admission semantics are UNCHANGED.
                "verified_custody_ids": [
                    r.record_id for r in verified],
                "verified_custody_hashes": [
                    r.content_hash for r in verified],
            },
        }
        snapshot["snapshot_hash"] = sha256_obj(snapshot)
        # R537 §E: expose the verified custody ID set to the FREEZE-
        # observing downstream adapters (SYNTHESIZE / VERIFY) so the
        # machine-join can prove whether the post-FREEZE pipeline
        # consumed the frozen / custodied evidence authority.  Purely
        # additive telemetry; the admission semantics are UNCHANGED.
        env.evidence_freeze_snapshot = dict(snapshot)
        return _engine_result(
            {"provenance": {**env.provenance, "evidence_freeze": snapshot}},
            custody_records=len(records), hash_ok=ok)


class PremiseGateAdapter(BaseAdapter):
    """R394 section 6 — the false-premise gate. Runs AFTER the problem
    is frozen and BEFORE candidate synthesis. Deterministic hard-rule
    table (definitional contradictions only — see premise_gate.py for
    the honest scope). A matched contradiction raises StageFailure
    (MALFORMED_OR_FALSE_PREMISE) so the conductor records the explicit
    stage failure, skips synthesis + everything downstream, and the
    run terminates honestly with the premise explanation (never a
    fabricated green path, never a burned-synthesis silent reject)."""
    capability_id = "PREMISE_GATE"
    module_path = "discovery_fabric/engine/premise_gate.py"
    canonical_fn = "check_premise(problem)"
    needs_network = False
    depends_on = []

    def execute(self, env, run_ctx):
        from discovery_fabric.engine.premise_gate import check_premise
        verdict = check_premise(env.problem)
        # The stage ALWAYS succeeds in executing (it is a deterministic
        # instrument); the CONDUCTOR decides fatality from the verdict —
        # so the envelope cleanly carries the full verdict record via
        # the standard apply_to path and the stage_log stays truthful.
        return _engine_result(
            {"premise_gate": verdict},
            premise_verdict=verdict["verdict"])


class SynthesizeAdapter(BaseAdapter):
    """Canonical: discovery_fabric/a2/synthesize.py::synthesize (ACTIVE)."""
    capability_id = "SYNTHESIS"
    module_path = "discovery_fabric/a2/synthesize.py"
    canonical_fn = "synthesize(problem, evidence)"
    needs_network = True
    depends_on = ["RETRIEVE"]

    def execute(self, env, run_ctx):
        if not env.evidence:
            raise RuntimeError(
                "synthesis impossible: zero evidence items retrieved (explicit)")
        mod = _import_with_env("discovery_fabric.a2.synthesize")
        cand = mod.synthesize(env.problem, env.evidence)
        # R537 §E: the authoritative input set this stage actually
        # consumed (ids + content-hashes) + whether it stayed inside
        # the verified FREEZE custody set (the machine-join proof of
        # whether the post-FREEZE pipeline consumed the frozen /
        # custodied evidence authority).  Purely additive telemetry;
        # the admission / synthesis semantics are UNCHANGED.
        _synth_input_set = [
            {"id": it.get("id", ""),
             "content_hash": it.get("content_hash", "")}
            for it in (env.evidence or [])]
        _freeze_snap = getattr(env, "evidence_freeze_snapshot", None)
        _verified_custody_ids = set(
            _freeze_snap.get("freeze_observational", {}).get(
                "verified_custody_ids", [])) if isinstance(
                _freeze_snap, dict) else set()
        _downstream_ids = [it.get("id", "") for it in (env.evidence or [])]
        _synth_consumed_verified_custody = (
            (not _downstream_ids)
            or (set(_downstream_ids) <= _verified_custody_ids))
        # R453-LEAN-CORE capability fail-closed: the registry's own
        # task-degradation record for the call that ACTUALLY served the
        # synthesis. A STRONG request served by CHEAP_EMERGENCY_FALLBACK
        # is CAPABILITY_INSUFFICIENT — NOT an ok synthesis. The
        # candidate is not promoted (no pseudo-invention on the
        # envelope), the degradation record IS (the downstream
        # admission reads it; the mandate: degraded STRONG is a hard
        # stop, never a cheap success).
        _meta = getattr(mod, "_LAST_PROVIDER_META", {}) or {}
        _deg = _meta.get("task_degradation") or {}
        _degraded = (_deg.get("task_capability_match") is False
                     and str(_deg.get("actual_task_capability")) ==
                     "CHEAP_EMERGENCY_FALLBACK")
        if cand is not None and _degraded:
            return _engine_result(
                {"provenance": {**env.provenance, "synthesis": {
                    "model": _meta.get("model"),
                    "provider": _meta.get("provider"),
                    "transport_status": _meta.get("status"),
                    "task_degradation": _deg,
                    "capability_state": "CAPABILITY_INSUFFICIENT",
                    "note": ("the degraded candidate is NOT promoted to "
                             "the envelope (never a pseudo-invention); "
                             "the record is retained for the audit "
                             "trail only")}}},
                state="CAPABILITY_INSUFFICIENT",
                capability_insufficient=True,
                degraded_candidate_rejected=True)
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
                 "task_degradation": _deg or None,
                 "prompt_hash": cand.get("prompt_hash"),
                 "input_hash": cand.get("input_hash"),
                 "output_hash": cand.get("output_hash"),
                 "synthesis_timestamp": cand.get("synthesis_timestamp"),
                # R537 §E: the SYNTHESIZE input evidence set (ids +
                # content-hashes) — the machine-join input that
                # proves whether this stage consumed the frozen /
                # custodied evidence authority (the verified FREEZE
                # set).  Purely additive telemetry; the admission /
                # synthesis semantics are UNCHANGED.
                "synthesis_input_evidence_set": _synth_input_set,
                "synthesis_consumed_verified_custody":
                    _synth_consumed_verified_custody,
                 # R483 (the dropped-ledger observability defect): the
                 # routing TRUTH rides the committed record — the walk
                 # (every hop incl. SKIPPED_NOT_ADMITTED with its
                 # capability_state), the retry notes (reasoning-cap
                 # escalations), the cost-policy refusals, and the
                 # ladder's head. The R483 diagnosis of the two campaign
                 # runs was blocked exactly here: the adapter kept the
                 # serving model and dropped WHY the walk reached it.
                 # Bounded: the availability matrix is NOT embedded.
                 "routing": {
                     "provider_route": _meta.get("provider_route") or [],
                     "retry_notes": _meta.get("retry_notes") or [],
                     "cost_policy_refusals": (
                         (_meta.get("selection_ledger") or {}).get(
                             "cost_policy_refusals") or []),
                     "ladder_head": [
                         {"provider": r.get("provider"),
                          "model": r.get("model"),
                          "band": r.get("band")}
                         for r in (((_meta.get("selection_ledger")
                                     or {}).get("ladder")
                                    or {}).get("rungs") or [])[:10]],
                 }}}},
        model=cand.get("model"), provider=cand.get("provider"))


class EvidenceVerifyAdapter(BaseAdapter):
    """Canonical: discovery_fabric/a2/verify.py::verify_evidence (ACTIVE)."""
    capability_id = "EVIDENCE_VERIFY"
    module_path = "discovery_fabric/a2/verify.py"
    canonical_fn = "verify_evidence(candidate, evidence)"
    depends_on = ["SYNTHESIZE"]

    def execute(self, env, run_ctx):
        mod = importlib.import_module("discovery_fabric.a2.verify")
        raw = env.mechanism_map.get("raw_candidate") or {}
        # R537 §E: the authoritative input set this stage actually
        # consumed (ids + content-hashes) — the machine-join input
        # that proves whether VERIFY consumed the frozen / custodied
        # evidence authority.  Purely additive telemetry; the
        # verification semantics are UNCHANGED.
        _verify_input_set = [
            {"id": it.get("id", ""),
             "content_hash": it.get("content_hash", "")}
            for it in (env.evidence or [])]
        _freeze_snap_v = getattr(env, "evidence_freeze_snapshot", None)
        _verified_custody_ids_v = set(
            _freeze_snap_v.get("freeze_observational", {}).get(
                "verified_custody_ids", [])) if isinstance(
                _freeze_snap_v, dict) else set()
        _downstream_ids_v = [it.get("id", "")
                             for it in (env.evidence or [])]
        _verify_consumed_verified_custody = (
            (not _downstream_ids_v)
            or (set(_downstream_ids_v) <= _verified_custody_ids_v))
        res = mod.verify_evidence(raw, env.evidence)
        # R483 span-outcome telemetry (the span-capable rung
        # preference): report the span contract's outcome for the rung
        # that actually served this candidate, so the routing ladder can
        # demote recently span-failing rungs for synthesis (ordering-
        # only, Art. V). Reporting rules (Art. LXI-safe): verified=True
        # -> span-ok; a NON-VERIFIED result whose issues are ALL in
        # a2/verify's SPAN_ISSUES (the R452 MODEL-CAPABILITY class) ->
        # span-fail; any MIXED issue set (scientific + capability) or an
        # unattributable candidate -> NOT reported (the routing layer
        # never records a scientific verdict — classify.py owns that).
        try:
            from discovery_fabric.a2.verify import SPAN_ISSUES as _SI
            from . import model_routing as _mr
            _prov = raw.get("provider") if isinstance(raw, dict) else None
            _model = raw.get("model") if isinstance(raw, dict) else None
            if _prov and _model:
                _issues = [str(i) for i in (res.get("issues") or [])]
                if res.get("verified") and not _issues:
                    _mr.record_span_outcome(_prov, _model, ok=True,
                                            run_id=run_ctx.get("run_id"))
                elif _issues and all(i in _SI for i in _issues):
                    _mr.record_span_outcome(_prov, _model, ok=False,
                                            run_id=run_ctx.get("run_id"))
                # else: mixed or non-span issues — not routing telemetry
        except Exception:  # noqa: BLE001 — telemetry best-effort, recorded
            pass
        # R394 section 5: claim-level evidence classification rides the
        # VERIFY stage (domain/failure-mode/mechanism/material/regime
        # relevance per item; DIRECT_SUPPORT..IRRELEVANT). It records —
        # it does NOT gate: the classification is evidence metadata for
        # adjudication and the dossier; a topically-relevant-but-
        # mechanism-irrelevant item is exactly the distinction buyers
        # need, and it must not silently disappear from the record.
        try:
            from discovery_fabric.engine.evidence_classification import (
                classify_evidence_set)
            classification = classify_evidence_set(
                env.evidence, env.problem, env.mechanism_map)
        except Exception as exc:  # noqa: BLE001 — recorded, never hidden
            classification = {
                "classifier_version": "evidence_classification/1.0.0",
                "error": f"{type(exc).__name__}: {exc}",
                "n_items": len(env.evidence or []),
                "note": "classification failed — recorded, not hidden; "
                        "verification result unaffected",
            }
        return _engine_result(
            {"adjudication": {**env.adjudication,
                              "evidence_verification": res,
                              # R537 §E: the VERIFY input evidence set
                              # (ids + content-hashes) — the machine-
                              # join input that proves whether VERIFY
                              # consumed the frozen / custodied
                              # evidence authority.  Rides the
                              # durable `adjudication` path (an
                              # existing Candidate attribute); purely
                              # additive telemetry, verification
                              # semantics UNCHANGED.
                              "verify_input_evidence_set":
                              _verify_input_set,
                              "verify_consumed_verified_custody":
                              _verify_consumed_verified_custody},
             "evidence_classification": classification},
            verified=res.get("verified"))


def _lean_rel_band(relevance):
    """Read the verifier's relevance measurement, if present.

    Returns {"domain": bool|None, "mechanism": bool|None} — None means
    the dimension was not measured (legacy envelopes), never False.
    """
    if not isinstance(relevance, dict):
        return None

    def _flag(dim):
        v = relevance.get(dim) or {}
        r = v.get("relevant")
        return r if isinstance(r, bool) else None

    return {"domain": _flag("domain"), "mechanism": _flag("mechanism")}


def _lean_select_operator(items, problem):
    """R510 production bridge: deterministic operator selection over the
    verified items using canonical evidence (no invented content).

    Routing (first satisfied wins, canonical OPERATOR_IDS order, so
    DIRECT_TRANSFER keeps priority wherever its conditions hold):
      - DIRECT_TRANSFER: the verifier's relevance measurement when
        present (domain AND mechanism relevant on the FULL record text
        under VERIFY's own rule table — strictly stronger than the
        title proxy, same bar family); legacy title-view contract when
        relevance is absent (preserved behavior, recorded as fallback).
      - CROSS_DOMAIN_ANALOGY: verifier relevance with foreign domain
        (domain False) AND mechanism overlap (the classifier's ANALOGY
        shape) — explicit analogy routing, never accidental failure;
        else the legacy contract.
      - GEOMETRIC/Boundary/FAILURE_PATH: the existing input contracts
        unchanged (no relevance equivalent exists; honestly recorded).
    One instantiation call downstream regardless of how many
    (item, operator) pairs are examined — contracts are pure
    deterministic predicates (zero LLM fan-out). Everything examined
    is recorded in evaluated; the selection basis is recorded.
    """
    from discovery_fabric.engine import mechanism_space as _ms
    evaluated = []
    selected = None
    for it in items:
        band = _lean_rel_band(it.get("relevance"))
        for o in _ms.TRANSFORMATION_OPERATORS:
            oid = o["operator_id"]
            contract = None
            satisfied = False
            basis = ""
            if oid == "DIRECT_TRANSFER" and band is not None \
                    and band["domain"] is not None \
                    and band["mechanism"] is not None:
                if band["domain"] and band["mechanism"]:
                    satisfied = True
                    basis = ("verifier relevance: domain+failure+mechanism "
                             "relevant on full record text (VERIFY rule "
                             "table; VERIFY's thresholds, unchanged here)")
                else:
                    basis = ("verifier relevance: domain=%s mechanism=%s "
                             "— not same-domain demonstrated; explicit "
                             "routing, not accidental failure"
                             % (band["domain"], band["mechanism"]))
                contract = {"operator": oid, "satisfied": satisfied,
                            "basis": basis, "route": "verifier-relevance"}
            elif oid == "CROSS_DOMAIN_ANALOGY" and band is not None \
                    and band["domain"] is False \
                    and band["mechanism"] is not None:
                if band["mechanism"]:
                    satisfied = True
                    basis = ("verifier relevance: foreign domain + "
                             "mechanism overlap (classifier ANALOGY "
                             "shape); explicit analogy routing")
                else:
                    basis = ("verifier relevance: no mechanism overlap "
                             "— analogy inapplicable")
                contract = {"operator": oid, "satisfied": satisfied,
                            "basis": basis, "route": "verifier-relevance"}
            else:
                c = o["input_contract"](it, problem)
                contract = c
                satisfied = bool(c.get("satisfied"))
                basis = ("legacy title-view contract: "
                         + str(c.get("basis", ""))[:200])
            evaluated.append({"item_id": it.get("item_id"),
                              "operator": oid, "satisfied": satisfied,
                              "basis": basis,
                              "route": (contract or {}).get("route",
                                                            "legacy-view")})
            if satisfied and selected is None:
                selected = (it, o, contract)
    if selected is None:
        return {"operator": None, "item": None, "contract": {
            "satisfied": False,
            "basis": "no (item, operator) pair satisfied any admission "
                     "contract — honest refusal (Art. XXV)"},
            "evaluated": evaluated,
            "selection_basis": "none-satisfied"}
    it, o, contract = selected
    return {"operator": o, "item": it, "contract": contract,
            "evaluated": evaluated,
            "selection_basis": ("first satisfied in canonical operator "
                                "order over verified items (deterministic; "
                                "one instantiation call downstream)")}


def _lean_mechanism_space(env, entry_block: Dict[str, Any]) -> Dict[str, Any]:
    """R453-LEAN-CORE: the lean mechanism-space construction (the
    external auditor mandate — no extraction fan-out; reuse the
    FREEZE/VERIFY structured facts; at most ONE operator generation
    call, only after admission passed).

    The structured items are built DETERMINISTICALLY from the frozen
    evidence records the FREEZE stage custodied, joined to their
    VERIFY-stage claim-level classification AND relevance measurement
    (the item's title is its system descriptor; the abstract rides
    as its own slot; the record text IS the evidence). ZERO LLM calls
    here. Then ONE instantiation call with the deterministically
    selected operator (canonical order, verifier-relevance routing
    with legacy title-view fallback — see _lean_select_operator),
    and the deterministic validation/distinctness/verification tail
    reuses the mechanism_space module's own instruments (same gates,
    no second evaluator — Art. IV)."""
    import hashlib as _h
    from . import stage_entry
    from . import mechanism_attribution as _mattr
    from discovery_fabric.engine import mechanism_space as _ms

    # R516 Part A: attribution clock (observational only — marks sit
    # between existing statements; no branch, threshold, or decision
    # below reads the clock).
    _clk = _mattr.AttributionClock()
    problem = env.problem or {}
    _clk.mark("entry_setup")
    verified = stage_entry.verified_evidence_items(env)
    by_id = {str(it.get("id")): it for it in (env.evidence or [])}
    _clk.mark("verified_evidence_collection",
              {"n_verified_items_examined": len(verified)})
    items: List[Dict[str, Any]] = []
    for cls_item in verified:
        rec = by_id.get(str(cls_item.get("source_id"))) or {}
        if not rec:
            # the classification's source no longer matches the frozen
            # set — honestly skipped, never fabricated
            continue
        title = str(rec.get("title") or "")
        abstract = str(rec.get("abstract") or "")
        record_text = f"{title}. {abstract}".strip()
        # The mechanism-level verifier reads the item's own
        # mechanism/effect vocabulary from the fields it custodies.
        # On the lean path the record's abstract IS the mechanism
        # statement (R453-LEAN: deterministic reuse of the frozen
        # FREEZE record — zero LLM calls, no extraction fan-out). We
        # surface it so the support instrument sees the record's real
        # mechanism vocabulary instead of an empty mechanism field
        # (which forced every lean verdict to NOT_ENOUGH_EVIDENCE —
        # phenomenon-only overlap was never mechanism support). The
        # instrument's thresholds/relations are untouched; an
        # unbound/unextracted mechanism still caps at
        # PARTIALLY_SUPPORTS (never direct SUPPORTS).
        items.append({
            "item_id": f"lean_{rec.get('id')}",
            "structured_hash": _h.sha256(
                record_text.encode("utf-8", "replace")).hexdigest(),
            "fields": {"system": {"value": title},
                       "abstract": {"value": abstract},
                       "mechanism": {"value": record_text},
                       "observed_effect": {"value": abstract}},
            "source": rec.get("source") or rec.get("id"),
            "provenance": {
                "content_hash": rec.get("content_hash"),
                "retrieval_timestamp": rec.get("retrieval_timestamp"),
                "construction": "R453_LEAN_REUSE_FREEZE_VERIFY_FACTS",
                "claim_classification": cls_item.get("classification"),
            },
            # the verifier's relevance measurement, verbatim when the
            # classifier emitted it (None on legacy envelopes): the
            # canonical full-text overlap basis the operator selection
            # consults instead of the title-only proxy (§6). Verbatim
            # custody, never re-derived here.
            "relevance": cls_item.get("relevance"),
            "_record_text": record_text,
        })
    _clk.mark("evidence_item_construction",
              {"n_structured_items": len(items)})
    space: Dict[str, Any] = {
        "mechanism_space_version": _ms.MECHANISM_SPACE_VERSION,
        "construction": "R453_LEAN (external auditor mandate: no "
                        "extraction fan-out; FREEZE/VERIFY facts "
                        "reused; at most one operator call)",
        "built_at": utc_now(),
        "problem_id": problem.get("problem_id", ""),
        "operator_ids": [],
        "n_structured_items": len(items),
    }
    if not items:
        space.update({
            "state": "NO_EVIDENCE", "candidates": [],
            "n_candidates_generated": 0,
            "n_candidates_retained": 0,
            "metrics": _ms._metrics(space, [], [], [], 0),
            "note": ("no frozen evidence record matched a verified "
                     "classification item — nothing was fabricated "
                     "(Art. XXV)"),
        })
        # R510 transition ledger: no operator call was attempted —
        # the empty ledger records the NOT_ATTEMPTED shape.
        from . import transition_trace as _tt0
        space["candidate_transitions"] = _tt0.build_transition_ledger(
            [], "NONE", "NO_EVIDENCE", {}, {"state": "NOT_CONSULTED",
                                            "blocked": []}, {}, [], {},
            {})
        space["runtime_attribution"] = _mattr.build_record(
            _clk,
            {"verified_evidence_items": 0,
             "applicable_operator_contracts": {
                 "n_evaluated": 0, "n_satisfied": 0},
             "selected_operator": "NONE",
             "llm_outcome": "NOT_ATTEMPTED",
             "terminal_reason": "NO_EVIDENCE",
             # R532 §3: the not-attempted shape carries the same
             # typed-attempt schema (uniform harvest) — classified
             # by the shared classifier, never hand-typed.
             "instantiation_attempts": [
                 {**_ms_attempt_outcome(
                     False, "NO_EVIDENCE", None, None, None,
                     None, None, None, False, None, False, None),
                  "attempt_index": 1,
                  "attempted": False,
                  "provider": None,
                  "model": None,
                  "operator": "NONE",
                  "terminal_reason": "NO_EVIDENCE"}]},
            _mattr.llm_call_detail(0, None),
            "NO_EVIDENCE")
        # the not-attempted attempt rides the space record too
        # (uniform schema with the executed path).
        space["instantiation_attempts"] = (
            space["runtime_attribution"]["funnel"].get(
                "instantiation_attempts") or [])
        return space
    space["structured_evidence"] = {
        "state": "BUILT", "n_items": len(items),
        "construction": "R453_LEAN_REUSE_FREEZE_VERIFY_FACTS",
        "items": [{k: v for k, v in it.items()
                   if not k.startswith("_")} for it in items],
    }
    # ---- the ONE operator generation call (deterministic selection
    #      over verified items via _lean_select_operator: canonical
    #      operator order, verifier-relevance routing with legacy title-
    #      view fallback; no corrective retry on the lean path: one call
    #      is one call, the span/semantic gates themselves are
    #      unchanged) ---------------------------------------------------
    sel = _lean_select_operator(items, problem)
    _clk.mark("operator_selection",
              {"n_contracts_evaluated": len(sel.get("evaluated") or []),
               "n_satisfied": sum(
                   1 for e in (sel.get("evaluated") or [])
                   if e.get("satisfied")),
               "selected_operator": (sel.get("operator") or {}).get(
                   "operator_id", "NONE") if sel.get("operator") else "NONE"})
    op = sel["operator"]
    item = sel["item"] if sel["item"] is not None else items[0]
    _llm_meta = None
    # R532 §3: the instantiation wall (None when no LLM call is
    # attempted — the typed attempt record reads it, never steers).
    _llm_wall = None
    # R532 §3: parse-level locals for the typed attempt record
    # (empty defaults when the LLM path failed or was never taken
    # — the classifier reads them, never steers). Initialized HERE
    # (all paths) so the no-contract path cannot NameError below.
    fields: Dict[str, Any] = {}
    _n_fields_nonempty: Optional[int] = None
    cand: Optional[Dict[str, Any]] = None
    sem: Optional[Dict[str, Any]] = None
    contract = sel["contract"]
    sel_id = op["operator_id"] if op else "NONE"
    space["operator_ids"] = [sel_id] if op else []
    operator_result: Dict[str, Any] = {
        "operator": sel_id,
        "operator_version": op["version"] if op else "unknown",
        "transformation_rule": op["transformation_rule"] if op else "",
        "search_constraint": op["search_constraint"] if op else "",
        "n_items_examined": len(items),
        "n_items_selected": 1 if contract.get("satisfied") else 0,
        "selected_item_ids": [item.get("item_id")]
        if contract.get("satisfied") else [],
        "input_contract": contract,
        "operator_selection": {
            "selected_operator": sel_id,
            "selected_item_id": item.get("item_id")
            if contract.get("satisfied") else None,
            "selection_basis": sel["selection_basis"],
            "contracts_evaluated": sel["evaluated"],
        },
        "lean_path": ("one instantiation call, no corrective retry "
                      "(R453-LEAN; deterministic operator selection; "
                      "the span/semantic gates unchanged)"),
        "candidates": [],
    }
    if not (op and contract.get("satisfied")):
        operator_result.update({
            "state": op["failure_state"] if op else "NO_APPLICABLE_EVIDENCE",
            "note": ("no (item, operator) pair satisfied any admission "
                     "contract — honest refusal, nothing fabricated "
                     "(Art. XXV)"),
        })
    else:
        item["_selection"] = {"selected_by": sel_id,
                              "contract": contract}
        prompt = _ms._OPERATOR_INSTANTIATION_PROMPTS[
            sel_id].format(
            system=item["fields"].get("system") or "(unextracted)",
            mechanism=_ms._field_val(item, "mechanism") or "(unextracted)",
            observed_effect=_ms._field_val(item, "observed_effect")
            or "(unextracted)",
            evidence_intervention=_ms._field_val(item, "intervention")
            or "(unextracted)",
            boundary_conditions=_ms._field_val(item, "boundary_conditions")
            or "(unextracted)",
            constraints=_ms._field_val(item, "constraints") or "(unextracted)",
            failure_mode=_ms._field_val(item, "failure_mode")
            or "(unextracted)",
            device=problem.get("device", ""),
            failure=problem.get("failure", ""),
            constraint=problem.get("constraint", ""),
            record_text=_ms._item_abstract(item)[:2600]
            or "(record text unavailable)")
        # R548: the generation-boundary change — the prompt now requests
        # up to N independently-parseable hypotheses in ONE response.
        # The deterministic validation tail (semantic check, cemetery,
        # distinctness) runs over every parsed block; the Art. LXXXIV
        # minimum is met by the distinctness instrument's own count,
        # not by a second LLM call (R517: model calls are the latency
        # sink; one call is one call).
        prompt += _ms._multi_hypothesis_prompt_suffix()
        # R516D: the initial budget is the rescue-proven level
        # (_ms.OPERATOR_INSTANTIATION_MAX_TOKENS), not the 700
        # default — 0/10 first-attempt successes at 700 across two
        # batteries is systematic budget starvation, not flakes.
        meta = _ms.llm_generate(
            prompt,
            system="You are a rigorous mechanism engineer. Every "
                   "claim must derive from the given evidence.",
            purpose=f"operator_{sel_id}",
            max_tokens=_ms.OPERATOR_INSTANTIATION_MAX_TOKENS)
        _llm_meta = meta
        # R532 §3: capture the instantiation wall for the typed
        # attempt record (mark() returns the span duration; the
        # span itself is unchanged).
        _llm_wall = _clk.mark("llm_instantiation_wall",
                              {"provider": meta.get("provider"),
                               "model": meta.get("model"),
                               "transport_status": meta.get("status")})
        if not meta.get("ok"):
            operator_result.update({
                "state": "OPERATOR_INSTANTIATION_FAILED",
                "llm_status": meta.get("status"),
                "llm_error": (meta.get("error") or "")[:200],
            })
        else:
            # R548: parse up to N independently-parseable hypothesis
            # blocks from the single LLM response. The multi-parse
            # falls back to the legacy single-candidate parse when no
            # HYPOTHESIS markers are present (backward compatible; the
            # ceiling remains in that case — the fix is the prompt,
            # and the parser never invents content the model did not
            # emit).
            field_blocks = _ms._parse_multi_candidate_fields(
                meta["content"] or "")
            # R532 §3: capture the parsed-field count for the typed
            # attempt record (same value the mark below records).
            _n_fields_nonempty = sum(
                1 for v in (field_blocks[0] if field_blocks else {}).values()
                if str(v or ""))
            _clk.mark("candidate_parsing",
                      {"n_fields_nonempty": _n_fields_nonempty,
                       "n_hypothesis_blocks": len(field_blocks)})
            # Assemble one candidate per parsed hypothesis block; each
            # goes through the same deterministic semantic check +
            # cemetery + distinctness tail (no second evaluator,
            # Art. IV). The candidate list now carries up to N
            # entries, lifting the structural ceiling.
            _cands = []
            for _blk_i, _blk_fields in enumerate(field_blocks, 1):
                _blk_fields = dict(_blk_fields)
                _blk_fields["_hypothesis_index"] = _blk_i
                _c = _ms.assemble_candidate(
                    op, item, _blk_fields, problem, meta)
                _sem = _ms.operator_semantic_check(
                    sel_id, item, _c, problem)
                _c["operator_semantic_check"] = _sem
                _c["hypothesis_index"] = _blk_i
                _cands.append(_c)
            cand = _cands[0] if _cands else None
            if cand is not None:
                operator_result["candidates"] = _cands
                operator_result["state"] = (
                    "OPERATED" if any(
                        c.get("candidate_state") == "CANDIDATE"
                        for c in _cands)
                    else "NO_VALID_CANDIDATE")
                operator_result["n_hypotheses_parsed"] = len(_cands)
            else:
                operator_result["candidates"] = []
                operator_result["state"] = "NO_VALID_CANDIDATE"
                operator_result["n_hypotheses_parsed"] = 0
    space["operator_results"] = [
        {k: v for k, v in operator_result.items()
         if k != "candidates"}]
    space["operator_candidates_full"] = [operator_result]
    # ---- the deterministic tail: the module's own instruments -------
    # R510 transition ledger (OBSERVATION ONLY): assembly states are
    # snapshotted before the instruments mutate them; every later read
    # comes from the instruments' own outputs. No semantic change —
    # the ledger watches, never steers.
    _assembled = [c for c in operator_result.get("candidates", [])
                  if isinstance(c, dict)]
    _pre_cem_states = {str(c.get("candidate_id")): str(
        c.get("candidate_state") or "") for c in _assembled}
    _sem_by_id = {str(c.get("candidate_id")): (
        c.get("operator_semantic_check") or {}) for c in _assembled}
    all_candidates = [c for c in operator_result.get("candidates", [])
                      if isinstance(c, dict)
                      and c.get("candidate_state") == "CANDIDATE"]
    space["cemetery_consumption"] = _ms._consult_cemetery(
        all_candidates, problem)
    _clk.mark("cemetery_consultation",
              {"n_consulted": (space["cemetery_consumption"] or {}).get(
                  "n_candidates_consulted", 0),
               "n_blocked": (space["cemetery_consumption"] or {}).get(
                   "n_blocked", 0)})
    dedup = _ms.deduplicate_candidates(all_candidates)
    space["distinctness"] = dedup
    _dd_by_id = {str(c.get("candidate_id")): {
        "verdict": c.get("distinctness_verdict"),
        "basis": c.get("distinctness_basis")} for c in all_candidates}
    retained = _ms._retained_candidates(all_candidates, dedup)
    _clk.mark("distinctness_dedup",
              {"n_distinct": dedup.get("n_distinct"),
               "n_indeterminate": dedup.get("n_indeterminate"),
               "n_retained": len(retained)})
    verifications = [_ms.verify_mechanism_support(c, items, problem)
                     for c in retained]
    for c, v in zip(retained, verifications):
        c["mechanism_support"] = v
    _clk.mark("mechanism_support_verification",
              {"support_states": [
                  (v.get("mechanism_support_state")
                   if isinstance(v, dict) else None)
                  for v in verifications]})
    from . import transition_trace as _tt
    space["candidate_transitions"] = _tt.build_transition_ledger(
        _assembled, sel_id, str(operator_result.get("state") or ""),
        _pre_cem_states, space["cemetery_consumption"], _dd_by_id,
        [str(c.get("candidate_id")) for c in retained],
        {str(c.get("candidate_id")): (c.get("mechanism_support") or {})
         for c in retained},
        _sem_by_id)
    space["candidates"] = [_ms._public_candidate(c) for c in retained]
    space["state"] = ("BUILT" if dedup.get("n_kept")
                      else "NO_CANDIDATES")
    space["n_candidates_generated"] = len(all_candidates)
    space["n_candidates_retained"] = len(retained)
    # R548: the Art. LXXXIV minimum is now enforced by the
    # distinctness instrument's own count — n_candidates_required
    # records the MINIMUM_DISTINCT_MECHANISMS bar (2), not the
    # old "at least 1 assembled" structural floor.
    space["min_candidates_required"] = (
        stage_entry.MINIMUM_DISTINCT_MECHANISMS
        if hasattr(stage_entry, "MINIMUM_DISTINCT_MECHANISMS")
        else 2)
    space["metrics"] = _ms._metrics(space, all_candidates, retained,
                                    verifications, len(items))
    # R516B-E section 2: named for the actual work (post-verification
    # assembly: transition ledger, public candidates, metrics) — the
    # old "serialization_persistence" label did not measure
    # persistence. Durations byte-identical; positional mapping pinned.
    _clk.mark("post_support_assembly")
    # R532 §3: typed instantiation-attempt record (observational
    # only — every value below was already computed; the
    # classifier in _ms_attempt_outcome reads, never steers). The
    # lean path attempts at most one instantiation; the list schema
    # is forward-compatible, never implying retries exist.
    _att_cand_id = (cand or {}).get("candidate_id")
    _att_blocked_ids = {
        str(b.get("candidate_id"))
        for b in ((space.get("cemetery_consumption") or {}).get(
            "blocked") or [])
        if isinstance(b, dict)}
    _att_retained_ids = {
        str(c.get("candidate_id")) for c in retained
        if isinstance(c, dict)}
    _att_dd = (_dd_by_id.get(str(_att_cand_id)) or {}) if _att_cand_id \
        else {}
    _att_sup = (cand or {}).get("mechanism_support") or {}
    _att_fields = (field_blocks[0] if field_blocks else {})
    _att_sem = ((operator_result.get("candidates") or [{}])[0]
                .get("operator_semantic_check") or {})
    _att_outcome = _ms_attempt_outcome(
        bool(contract.get("satisfied")),
        operator_result.get("state"),
        _llm_meta,
        _n_fields_nonempty,
        _att_fields.get("intervention"),
        _att_fields.get("mechanism"),
        (cand or {}).get("candidate_state"),
        _att_sem.get("semantic_verdict"),
        (str(_att_cand_id) in _att_blocked_ids
         if _att_cand_id else False),
        _att_dd.get("verdict"),
        (str(_att_cand_id) in _att_retained_ids
         if _att_cand_id else False),
        _att_sup.get("mechanism_support_state"),
    )
    _att_entry = {
        "attempt_index": 1,
        "attempted": bool(_llm_meta is not None),
        "provider": (_llm_meta or {}).get("provider"),
        "model": (_llm_meta.get("model")
                  if _llm_meta is not None else None),
        "operator": sel_id,
        "selected_item_id": (item.get("item_id")
                             if contract.get("satisfied") else None),
        "contract_satisfied": bool(contract.get("satisfied")),
        "provider_wall_s": (round(_llm_wall, 6)
                            if isinstance(_llm_wall,
                                          (int, float)) else None),
        "mechanism_space_wall_s": round(_clk.total_s(), 3),
        "output_nonempty_fields": _n_fields_nonempty,
        "semantic_verdict": (_att_sem.get("semantic_verdict")),
        "candidate_state": (cand or {}).get("candidate_state"),
        "candidate_id": _att_cand_id,
        "cemetery_blocked": (str(_att_cand_id) in _att_blocked_ids
                             if _att_cand_id else False),
        "distinctness_verdict": _att_dd.get("verdict"),
        "support_state": _att_sup.get("mechanism_support_state"),
        "typed_outcome": _att_outcome.get("outcome"),
        "outcome_detail": {k: v for k, v in _att_outcome.items()
                           if k != "outcome"},
        "terminal_reason": space.get("state"),
    }
    space["instantiation_attempts"] = [_att_entry]
    # R516 Part A: the candidate funnel + LLM detail, all counts and
    # states from the existing typed vocabulary (no new epistemic
    # states; unexecuted steps read as absent/None with the
    # terminal-state reason pointing at the responsible typed state).
    _assembled = operator_result.get("candidates") or []
    _sem_verdicts = [
        (c.get("operator_semantic_check") or {}).get("semantic_verdict")
        for c in _assembled]
    if _llm_meta is None:
        _llm_outcome = operator_result.get("state")
    else:
        _llm_outcome = _llm_meta.get("status")
    space["runtime_attribution"] = _mattr.build_record(
        _clk,
        {"verified_evidence_items": len(items),
         "applicable_operator_contracts": {
             "n_evaluated": len(sel.get("evaluated") or []),
             "n_satisfied": sum(
                 1 for e in (sel.get("evaluated") or [])
                 if e.get("satisfied"))},
         "selected_operator": sel_id,
         "llm_outcome": _llm_outcome,
         "llm_output_empty": (not bool(_llm_meta.get("content"))
                              if _llm_meta is not None else None),
         "n_assembled": len(_assembled),
         "semantic_verdicts": _sem_verdicts,
         "distinctness": {
             "n_distinct": dedup.get("n_distinct"),
             "n_indeterminate": dedup.get("n_indeterminate")},
         "n_retained": len(retained),
         "terminal_reason": space["state"],
         # R532 §3: the typed instantiation attempts ride the
         # funnel dict (free-form) so the existing harvester
         # extracts them with no second framework.
         "instantiation_attempts": space.get(
             "instantiation_attempts") or []},
        _mattr.llm_call_detail(
            0 if _llm_meta is None else 1, _llm_meta),
        space["state"])
    return space


# R532 §3: the typed instantiation-outcome taxonomy. Provenance:
# the outcome NAMES come from the R532 directive §3; each
# assignment rule below reads ONLY already-computed lean-path
# values (no recomputation, no new gates, no steering). Pure
# function — same inputs always yield the same outcome
# (Art. IX: observational). Precedence = earliest pipeline loss
# wins; later unexecuted steps read as None.
_SEMANTIC_REJECT_VERDICTS = frozenset({
    "TEXTUAL_REWRITE", "SEMANTIC_INVARIANT_BROKEN"})
_SEMANTIC_REJECT_STATES = frozenset({
    "NOT_A_CANDIDATE_TEXTUAL_REWRITE",
    "NOT_A_CANDIDATE_OPERATOR_INVARIANT_BROKEN",
    "NOT_A_CANDIDATE_SPAN_NOT_VERBATIM"})
# support states that mark weak/evidentially-insufficient backing
# (mechanism_space.verify_mechanism_support vocabulary).
_WEAK_SUPPORT_STATES = frozenset({
    "CONTESTED", "NOT_ENOUGH_EVIDENCE"})


def _ms_attempt_outcome(
    contract_satisfied: bool,
    prior_state: Optional[str],
    llm_meta: Optional[Dict[str, Any]],
    n_fields_nonempty: Optional[int],
    intervention: Optional[str],
    mechanism: Optional[str],
    candidate_state: Optional[str],
    semantic_verdict: Optional[str],
    cemetery_blocked: Optional[bool],
    distinctness_verdict: Optional[str],
    retained: Optional[bool],
    support_state: Optional[str],
) -> Dict[str, Any]:
    """Classify one operator-instantiation attempt into the R532 §3
    typed outcome. Every branch reads pre-computed values; None
    means the step never executed (earlier loss wins)."""
    if not contract_satisfied:
        return {"outcome": "NOT_ATTEMPTED",
                "prior_state": prior_state,
                "note": ("no (item, operator) pair satisfied any "
                         "admission contract — the existing state "
                         "stands, nothing fabricated")}
    if not llm_meta or not llm_meta.get("ok"):
        return {"outcome": "OPERATOR_INSTANTIATION_FAILED",
                "llm_status": ((llm_meta or {}).get("status")),
                "llm_error": str((llm_meta or {}).get("error") or "")[
                    :200]}
    if not (llm_meta.get("content") or ""):
        return {"outcome": "EMPTY_OUTPUT"}
    if (n_fields_nonempty or 0) == 0:
        return {"outcome": "PARSE_FAILURE",
                "n_fields_nonempty": 0}
    if not (intervention or "") and not (mechanism or ""):
        return {"outcome": "REQUIRED_FIELDS_MISSING",
                "n_fields_nonempty": n_fields_nonempty,
                "note": ("response parsed but carries no mechanism "
                         "content (mechanism + intervention both "
                         "empty)")}

    # R536 Cliff 1 (audit CB-classifier): the cemetery check MUST
    # precede the candidate_state check, independently of it.  A
    # cemetery hard-block overwrites candidate_state to
    # NOT_A_CANDIDATE_CEMETERY_PROVEN_INVARIANT — so when
    # cemetery_blocked is True the state is NOT an assembly failure
    # but the block itself.  Reading the state first (the R532
    # order) mislabels every cemetery block as ASSEMBLY_INVALID;
    # the raw cemetery_blocked boolean was the only record that told
    # the truth (the R535 4/5 NO_CANDIDATES rows).
    if cemetery_blocked:
        return {"outcome": "CEMETERY_BLOCK",
                "candidate_state": candidate_state}
    if (candidate_state or "") != "CANDIDATE" and \
            (semantic_verdict not in _SEMANTIC_REJECT_VERDICTS
             and (candidate_state or "")
             not in _SEMANTIC_REJECT_STATES):
        return {"outcome": "ASSEMBLY_INVALID",
                "candidate_state": candidate_state}
    if (semantic_verdict in _SEMANTIC_REJECT_VERDICTS
            or (candidate_state or "") in _SEMANTIC_REJECT_STATES):
        return {"outcome": "SEMANTIC_REJECT",
                "semantic_verdict": semantic_verdict,
                "candidate_state": candidate_state}
    if (distinctness_verdict or "") not in (
            "DISTINCT", "INDETERMINATE", None, "") \
            and not retained:
        return {"outcome": "DISTINCTNESS_DROP",
                "distinctness_verdict": distinctness_verdict}
    if (support_state in _WEAK_SUPPORT_STATES) and not retained \
            and not cemetery_blocked and (
                distinctness_verdict or "") in (
                    "DISTINCT", "INDETERMINATE", None, ""):
        # Safety net (documents a support-shaped loss the current
        # gates do not explain): on the present lean path support
        # is advisory (retained = dedup kept_ids), so this branch
        # is unreachable today — if it ever fires, that firing is
        # itself a finding (a gate drops on support without a
        # recorded cemetery/distinctness reason).
        return {"outcome": "MECHANISM_SUPPORT_DROP",
                "support_state": support_state}
    if retained:
        return {"outcome": "CANDIDATE_ACCEPTED",
                "support_state": support_state}
    return {"outcome": "UNKNOWN",
            "note": ("no taxonomy branch claimed this attempt — "
                     "recorded values preserved below, never "
                     "force-fit (Art. XXV)"),
            "candidate_state": candidate_state,
            "distinctness_verdict": distinctness_verdict,
            "support_state": support_state}


class MechanismSpaceAdapter(BaseAdapter):
    """R401: the structured mechanism space — a FIRST-CLASS stage
    between VERIFY and COLLISION. Canonical:
    discovery_fabric/engine/mechanism_space.py::build_mechanism_space.

    Converts custodied evidence into STRUCTURED data (11 fields),
    derives candidates through the five transformation operators
    (deterministic input contracts + LLM instantiation + span-bound
    validation), collapses wording-only duplicates (machine-checkable
    distinctness), and verifies each retained candidate's asserted
    mechanism against the evidence bundle (SUPPORTS /
    PARTIALLY_SUPPORTS / CONTRADICTS / IRRELEVANT /
    NOT_ENOUGH_EVIDENCE — contradictions stay visible).

    The stage is EXPENSIVE candidate generation: the R399 W2.3 gate
    applies (>= 1 VERIFIED_EVIDENCE_ITEM), stamped by the shared
    entry-justification helper; zero verified items -> the honest
    skipped state (never silent, never fabricated). The stage is
    NON-FATAL: a skipped/failed mechanism space leaves the primary
    discovery loop and the grid path untouched.

    R453-LEAN-CORE (the external auditor mandate): the LEAN
    construction — NO extraction fan-out (the R401 per-item
    structured-evidence extraction calls are retired from the
    production path); the structured items are the FREEZE/VERIFY facts
    (the frozen evidence records + their claim-level classification —
    deterministic, zero LLM calls), and AT MOST ONE operator
    instantiation call with the deterministically selected operator
    (canonical order over verified items; R510 bridge), only after
    admission passed. The module's own
    build_mechanism_space() remains the hermetic instrument its test
    battery exercises; the production role moved here (Art. LXIV:
    KEPT_BECAUSE test-covered instrument — the superseding production
    path is this adapter, disclosed in the space record).
    R532 (§2 audit): to prevent a future coder from "fixing" the
    wrong implementation — module_path/canonical_fn below name the
    CAPABILITY namespace (the hermetic instrument); production_impl
    names the code that actually serves live runs."""
    capability_id = "MECHANISM_SPACE"
    module_path = "discovery_fabric/engine/mechanism_space.py"
    canonical_fn = "build_mechanism_space(problem, evidence)"
    # R532 §2: explicit production-vs-instrument split. Live runs
    # execute production_impl (the lean path); the hermetic battery
    # exercises canonical_fn (the full expansion instrument). A
    # measurement or fix targeting live MECHANISM_SPACE behavior
    # belongs in production_impl, never in the instrument.
    production_impl = ("discovery_fabric/engine/adapters.py::"
                       "_lean_mechanism_space (R453 lean path: "
                       "FREEZE/VERIFY fact reuse, deterministic "
                       "items, deterministic operator selection, "
                       "at most ONE operator-instantiation LLM call, "
                       "deterministic validation tail)")
    hermetic_instrument = ("discovery_fabric/engine/mechanism_space.py::"
                           "build_mechanism_space (full expansion; "
                           "test-only, no production callers)")
    needs_network = True
    depends_on = ["RETRIEVE", "SYNTHESIZE"]

    input_contract = {"problem": "problem dict",
                      "evidence": "envelope.evidence (custodied items)"}
    output_contract = ("envelope.mechanism_space = {state, "
                       "structured_evidence, operator_results, "
                       "distinctness, candidates[], metrics}")

    def execute(self, env, run_ctx):
        from . import stage_entry
        entry_block = stage_entry.justify(
            "MECHANISM_SPACE", env, None, None)
        if entry_block["entry_status"] == "SKIPPED":
            return _engine_result(
                {"mechanism_space": {
                    "mechanism_space_version": "mechanism_space/1.0.0",
                    "state": "SKIPPED_EVIDENCE_VERIFICATION_FAILED",
                    "entry": entry_block,
                    "note": ("zero verified evidence items on the "
                             "envelope — the mechanism space would "
                             "build candidates on unverified evidence "
                             "(R399 W2.3 applies to ALL expensive "
                             "candidate generation); nothing was "
                             "fabricated (Art. XXV)"),
                    "candidates": []}},
                state="SKIPPED_EVIDENCE_VERIFICATION_FAILED")
        space = _lean_mechanism_space(env, entry_block)
        return _engine_result(
            {"mechanism_space": space},
            state=space.get("state"),
            n_candidates=space.get("n_candidates_retained", 0))


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
    depends_on = ["SYNTHESIZE"]

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
        # ENGINE_COLLISION_SOURCES (R378, CEO directive 'Use PatentBear
        # for patents'): explicit operator override of the patent source
        # list — same explicit, recorded pattern as the other
        # ENGINE_*_PROVIDER overrides. Default unchanged
        # (google_patents + lens_patent); patentbear is opt-in with its
        # persistent quota guard (reserve floor; refusals recorded as
        # errors, never absence).
        _collision_sources = [s.strip() for s in os.environ.get(
            "ENGINE_COLLISION_SOURCES", "").split(",") if s.strip()] or None
        collision = cr.run_collision(mm, env.problem,
                                     sources=_collision_sources)
        if _collision_sources:
            collision["operator_source_override"] = {
                "sources": _collision_sources,
                "note": ("ENGINE_COLLISION_SOURCES operator override "
                         "(R378; explicit, recorded, never silent)")}
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


class PhysicsStageAdapter(BaseAdapter):
    """R397 Phase 2 — PHYSICS as a FIRST-CLASS canonical stage.

    Canonical: discovery_fabric/engine/physics_stage.py::
    evaluate_envelope_physics + physics_core.py (the ONE solver).
    Executed for every ordinary user run (STAGE_ORDER) between
    COLLISION and ATTACK so the physics verdicts are ON THE ENVELOPE
    before the adversarial attack, the adjudication and the release.

    The consultant finding this closes: 'the physics solver is
    validated code but not part of the live run chain.' The full
    directive chain (PRE-REQUIREMENTS -> PLAUSIBILITY -> SOLVER ->
    FAILURE MODES -> BASELINE COMPARISON -> COMPUTATIONAL_RESULT)
    executes here at the mechanism level, and the gauntlet-level
    enforcement (run.py) applies the SAME gate to every pool candidate
    with real lifecycle effects (kill at bound violation, block
    automatic release on DOES_NOT_BEAT_BASELINE)."""
    capability_id = "PHYSICS_GATE"
    module_path = "discovery_fabric/engine/physics_stage.py"
    canonical_fn = "evaluate_envelope_physics(env, run_ctx)"
    needs_network = False
    depends_on = ["SYNTHESIZE"]

    input_contract = {"mechanism_map": "the synthesized mechanism",
                      "problem": "device/failure/constraint for domain "
                                 "classification"}
    output_contract = ("envelope.physics = verdict block: "
                       "lifecycle_verdict in {MECHANISM_NOT_SIMULATABLE, "
                       "PLAUSIBILITY_BOUND_VIOLATED, BEATS_BASELINE, "
                       "DOES_NOT_BEAT_BASELINE, INCONCLUSIVE} + the "
                       "directive chain record")

    def execute(self, env, run_ctx):
        from .physics_stage import evaluate_envelope_physics
        result = evaluate_envelope_physics(env, run_ctx)
        # A plausibility-bound violation is a FIRST-CLASS physics kill:
        # the mechanism violates a deterministic physical law —
        # research stops (Art. XIV: RED = STOP), never silently
        # proceeds to attack/dossier on a physically impossible basis.
        if result.get("lifecycle_verdict") == \
                "PLAUSIBILITY_BOUND_VIOLATED":
            from .candidate import StageFailure  # noqa: PLC0415
            raise StageFailure(
                "PHYSICS",
                "PLAUSIBILITY_BOUND_VIOLATED — the candidate's input "
                "envelope violates a deterministic physical bound: "
                + str(result.get("plausibility", {}).get("violations"))
                [:400])
        return _engine_result({"physics": result},
                              lifecycle_verdict=result.get(
                                  "lifecycle_verdict"),
                              chain=result.get("chain_executed"))


class AttackEngineAdapter(BaseAdapter):
    """Canonical: discovery_fabric/a2/adversarial.py::adversarial_challenge
    (ACTIVE; NVIDIA->OpenRouter; v4_corrections applied inside).
    Rejected: scripts/r255-r257 one-shot optimizers (HISTORICAL)."""
    capability_id = "ATTACK_ENGINE"
    module_path = "discovery_fabric/a2/adversarial.py"
    canonical_fn = "adversarial_challenge(candidate, evidence_verified, prior_art_state)"
    needs_network = True
    depends_on = ["SYNTHESIZE", "VERIFY", "COLLISION"]

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
    """Canonical: orchestrator/contradiction_queue.py (6-field register).

    R478 P0-2 (external audit): the queue previously ingested only
    attack-KILL, verify-issue and collision-adjacent contradictions —
    a user-evidence source classified CONTRADICTORY by the claim-level
    classifier changed VISIBILITY only (the audit's measured inertness:
    'B changes visibility only'). It now enters the queue as a typed
    contradiction with a DERIVED (formula-recorded, Art. XXVII)
    severity, and the queue payload carries the recorded belief update
    (support ratio + confidence delta) the rest of the chain consumes:
    the existing ADJUDICATION check no_blocking_contradictions then
    blocks promotion while the contradiction is unresolved — no new
    state machine, the queue's own is_blocking semantics are reused.
    """
    capability_id = "CONTRADICTION_QUEUE"
    module_path = "orchestrator/contradiction_queue.py"
    canonical_fn = "ContradictionQueue.add / to_dict"
    depends_on = ["ATTACK", "COLLISION"]

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
        # R478 P0-2: user-evidence contradictions enter the queue.
        # Severity derivation (declared, revisable — Art. XXVII): a
        # CONTRADICTORY source co-existing with DIRECT_SUPPORT threatens
        # a promotable state -> HIGH (the audit's blocking requirement);
        # with zero direct support the mechanism is already unsupported
        # -> MEDIUM, visible without changing the outcome. probability
        # 0.6 / quality MODERATE: the classifier is a transparent
        # lexical proxy, not a claim chart (its own words) — MODERATE
        # keeps is_blocking honest without overclaiming STRONG.
        ec = env.evidence_classification or {}
        ec_counts = ec.get("counts") or {}
        support = ec.get("mechanism_support") or {}
        n_direct = int(support.get("n_direct_support") or
                       ec_counts.get("DIRECT_SUPPORT") or 0)
        contra_items = [it for it in (ec.get("items") or [])
                        if isinstance(it, dict)
                        and it.get("classification") == "CONTRADICTORY"]
        n_contra = int(support.get("n_contradictory") or len(contra_items))
        for it in contra_items:
            basis = ((it.get("classification_basis") or {})
                     .get("contradiction_basis")) or ""
            q.add(Contradiction(
                contradiction_id=(f"con:evidence:"
                                  f"{it.get('source_id') or sha256_obj(it)[:8]}"),
                description=("user evidence contradicts the mechanism: "
                             + str(it.get("buyer_statement") or "")[:120]
                             + (f" [{basis[:160]}]" if basis else "")),
                claim_or_limitation_affected="mechanism",
                severity="HIGH" if n_direct > 0 else "MEDIUM",
                probability=0.6,
                evidence_quality="MODERATE", decision_impact=0.8,
                currently_unresolved=True))
            n += 1
        d = q.to_dict()
        # R478 P0-2: the recorded belief movement (Art. LI: learning/
        # contradiction must change future behavior — here it changes
        # the recorded confidence AND the promotion gate).
        denom = n_contra + n_direct
        belief = {
            "n_direct_support": n_direct,
            "n_contradictory": n_contra,
            "support_ratio": (round(n_direct / denom, 3)
                              if denom else None),
            "confidence_delta": (round(-0.4 * (n_contra / denom), 3)
                                 if denom else None),
            "basis": ("confidence_delta = -0.4 x n_contradictory / "
                      "(n_contradictory + n_direct_support); declared "
                      "linear penalty (max -0.4 at all-contradicting), "
                      "MODEL_DERIVED, revisable, never a silent number "
                      "(Art. XXVII); None typed ABSENT when the "
                      "classification produced no support items"),
        }
        d["belief_update"] = belief
        d["belief_update_note"] = (
            "R478 P0-2: contradictory user evidence now enters the "
            "queue (derived severity) and the recorded confidence "
            "moves; an unresolved HIGH/MODERATE contradiction keeps "
            "the ADJUDICATION no_blocking_contradictions check RED — "
            "promotion stays blocked until it is attacked and resolved")
        return _engine_result({"contradictions": d}, added=n)


class KillerExperimentAdapter(BaseAdapter):
    """Canonical: epistemic_integrity/invention_loop_engine/bayesian_eig.py
    (pure Bayesian EIG). Priors are MODEL_DERIVED from adjudication text —
    labeled EXPERT_PRIOR/MODEL_DERIVED explicitly, never EXPERIMENTALLY_ESTIMATED."""
    capability_id = "KILLER_EXPERIMENT"
    module_path = "epistemic_integrity/invention_loop_engine/bayesian_eig.py"
    canonical_fn = "BayesianEIGCalculator.rank_experiments"
    depends_on = ["CONTRADICTION", "SYNTHESIZE"]

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
        # R478 P0-4 (external audit): the outcome likelihoods were
        # literals (0.85/0.15 — the same constants the audit measured
        # as the constant R458 trace). They are now state-derived:
        # unresolved-contradiction pressure widens the spread (more
        # unresolved contradictions -> a less confident reproduction
        # likelihood), with the formula and inputs recorded here.
        # Declared, revisable, MODEL_DERIVED — never measured (Art.
        # XXVII: the label travels with the number).
        _unresolved_c = int((env.contradictions or {}).get(
            "unresolved_count", 0) or 0)
        _ec_counts = (env.evidence_classification or {}).get("counts") or {}
        _n_direct_c = int(_ec_counts.get("DIRECT_SUPPORT") or 0)
        _pressure_c = round(_unresolved_c / max(
            _unresolved_c + _n_direct_c, 1), 3)
        _p_repro = round(0.85 - 0.20 * _pressure_c, 3)
        _likelihood_basis = {
            "formula": ("p_reproduces(H_effect_holds|effect_reproduces) "
                        "= 0.85 - 0.20 x pressure; pressure = "
                        "unresolved_contradictions / (unresolved + "
                        "n_direct_support)"),
            "inputs": {"unresolved_contradictions": _unresolved_c,
                       "n_direct_support": _n_direct_c},
            "pressure": _pressure_c,
            "provenance": "MODEL_DERIVED (declared linear map; no "
                          "measured base rate exists — Art. XXV)",
        }
        if mm.get("falsification_test"):
            options.append({
                "name": "falsification_test_from_candidate",
                "outcomes": [
                    _outcome("effect_reproduces", "candidate effect observed in bench rep",
                             {"H_effect_holds": _p_repro,
                              "H_effect_fails": round(1.0 - _p_repro, 3)}),
                    _outcome("effect_fails", "candidate effect not observed",
                             {"H_effect_holds": 0.10, "H_effect_fails": 0.90})],
                "cost": 1.0, "risk": 1.0, "feasibility": 1.0,
                "likelihood_basis": _likelihood_basis})
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
            "likelihood_basis": _likelihood_basis,
            "epistemic_note": ("all priors MODEL_DERIVED; no EXPERIMENTALLY_ESTIMATED "
                               "inputs exist at this stage (Art. XXVIII/XXXVIII: no "
                               "synthetic shortcut to physical observation)"),
            "timestamp": utc_now(),
        }
        return _engine_result({"killer_experiment": payload},
                              selected=best_name)


class ImproveAdapter(BaseAdapter):
    """R481 (external-audit P0-1): the IMPROVE operation — the loop
    closure. Dead candidates are mutated FROM THEIR RECORDED KILL
    BASIS and the children RE-RUN the same gauntlet gates; a child
    that passes every gate re-enters the competition with fresh
    scores, one that fails dies again with a typed record.

    Execution point (the cemetery precedent): the Directive-1
    pipeline's kill-evidence point — invoked post-rank with
    kill evidence via the same env.run_stage first-class protocol
    (run.py kill point; stage_IMPROVE.json + IMPROVE_LEDGER.json
    persist the typed record). R515: NO linear D8 slot — the former
    loop-position entry only ever recorded DEFERRED_TO_KILL_POINT
    and is removed from STAGE_ORDER (the adapter stays registered
    because the kill-point caller addresses it by name; R402
    recorded asymmetry). The no-payload branch below is the
    defensive default for a payload-less invocation (fail-closed,
    never a synthetic child).

    Art. XXXVII guard: the loop is real or it does not exist — no
    kill evidence -> NO_KILL_EVIDENCE (never a synthetic child);
    transport failure -> IMPROVEMENT_BLOCKED_TRANSPORT (the dead stay
    dead, the run continues); every admitted child carries its
    lineage and fresh scores (nothing inherited).
    """
    capability_id = "IMPROVE"
    module_path = "discovery_fabric/engine/improve_stage.py"
    canonical_fn = "improve_stage.run_improve"
    depends_on = ["KILLER_EXPERIMENT", "CONTRADICTION"]
    needs_network = True

    def execute(self, env, run_ctx):
        payload = (run_ctx or {}).get("improve_payload")
        if not payload:
            # R515: the defensive default — the kill-point caller
            # always passes improve_payload, so a payload-less
            # invocation means the gauntlet has not run (or the
            # caller is not the kill point): the typed deferral,
            # never a fake no-op and never a synthetic child.
            return {"_engine_result": True, "apply_to": {},
                    "status": "DEFERRED_TO_KILL_POINT",
                    "stage_version": "improve_stage/1.0.0 (R481 P0-1)",
                    "note": ("the IMPROVE operation executes at the "
                              "Directive-1 pipeline's kill-evidence "
                              "point (the cemetery-update precedent); "
                              "invoked without kill evidence the "
                              "deferral is the recorded design")}
        from .improve_stage import run_improve
        return run_improve(payload)


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
    depends_on = ["VERIFY", "ATTACK", "CONTRADICTION",
                  "COLLISION"]

    def execute(self, env, run_ctx):
        ev = env.adjudication.get("evidence_verification") or {}
        attack = env.attack_results or {}
        cemetery = _CemeterySubCheck.verdict(env)
        # R537 P0 (audit fail-open finding): the cemetery sub-check
        # record is durably persisted under env.adjudication EVEN WHEN
        # the council aggregation below raises — an UNRESOLVED /
        # infrastructure-failure consultation must stay observable in
        # the durable adjudication record (Art. XXV: never hidden,
        # never fabricated), not only in the transient return value.
        env.adjudication["cemetery_check"] = cemetery
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
              # R537 P0 (audit fail-open finding): the gate is
              # fail-CLOSED on a UNRESOLVED cemetery consultation.
              # The old form (verdict != "BLOCKED") treated an
              # infrastructure failure (no consultation ever
              # completed) as a PASS — a cemetery verification
              # failure could not become favorable adjudication
              # merely because the result was not literally
              # BLOCKED.  Now: a non-BLOCKED verdict passes ONLY
              # when the consultation itself resolved; UNRESOLVED /
              # a missing resolved flag fails the check, so the
              # run cannot reach ESTABLISHED_PROVISIONALLY and earns
              # no discovery credit (Art. XXV: UNKNOWN stays
              # UNKNOWN; Art. LI: an unread cemetery is not a
              # memory).
              "result": (cemetery.get("verdict") != "BLOCKED"
                         and cemetery.get(
                             "cemetery_verdict_resolved") is True),
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
            {"adjudication": {**env.adjudication, "council": payload,
                              # the cemetery sub-check record is on the
                              # durable env path (set above before the
                              # council aggregation); the return
                              # envelope re-rides it so both paths agree
                              "cemetery_check": cemetery},
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
    depends_on = ["CONTRADICTION", "KILLER_EXPERIMENT", "ADJUDICATION"]

    def execute(self, env, run_ctx):
        from orchestrator.next_best_action import Action, NextBestAction
        actions: List[Action] = []
        # R478 P0-4: contradiction-action EIG now derives from the
        # queue's own recorded priority fields (severity weight x
        # probability x quality weight x decision impact — the
        # Contradiction.priority_score formula, orchestrator/
        # evidence_graph.py) instead of the 0.5ximpact+0.2 literal.
        _PRIORITY_W = {"HIGH": 1.0, "MEDIUM": 0.5, "LOW": 0.2}
        _QUALITY_W = {"STRONG": 1.0, "MODERATE": 0.7, "WEAK": 0.3,
                      "NONE": 0.1}
        for c in (env.contradictions or {}).get("contradictions", []):
            if c.get("currently_unresolved"):
                _prio = (_PRIORITY_W.get(str(c.get("severity", "")).upper(), 0.2)
                         * float(c.get("probability", 0.5) or 0.5)
                         * _QUALITY_W.get(str(c.get("evidence_quality", "")).upper(), 0.1)
                         * float(c.get("decision_impact", 0.5) or 0.5))
                actions.append(Action(
                    action_id=c["contradiction_id"],
                    description=f"attack contradiction: {c['description'][:120]}",
                    evidence_question_id=c["contradiction_id"],
                    provider="internal_attack",
                    expected_information_gain=round(0.2 + 0.6 * _prio, 3),
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


class _CemeterySubCheck:
    """Internal helper used by AdjudicationAdapter (keeps D8 stage list exact
    while still consulting negative knowledge inside the loop).

    R402 (audit CB-9): the STANDALONE MechanismCemeteryAdapter that was
    registered in ADAPTERS under "CEMETERY_CHECK" is REMOVED — it was
    registered but unreachable (absent from STAGE_ORDER: the cemetery
    check runs as THIS sub-check of ADJUDICATION and the cemetery
    UPDATE is conductor-level after a final KILL/REJECT, per the D8
    directive). A registered-but-unreachable adapter is a shadow
    capability (Art. X: one authority, no dead registrations).
    ADAPTERS keys now equal STAGE_ORDER entries exactly — pinned by
    test."""

    @staticmethod
    def verdict(env) -> Dict[str, Any]:
        try:
            mc = importlib.import_module("orchestrator.mechanism_cemetery")
            mm = env.mechanism_map
            desc = " ".join([mm.get("intervention", ""),
                             mm.get("mechanism", "")])[:2000]
            # R536 Cliff 2: pass the candidate's mechanism-graph terms
            # as the structural domain-identity signal (the same
            # graph the distinctness instrument compares).  Without a
            # graph (legacy / no-candidate state) the cemetery falls
            # back to the lexical signal only — never a fabricated
            # structural match.
            _cand = mm.get("raw_candidate") or {}
            _graph_terms: set = set()
            for _node in (_cand.get("mechanism_graph") or {}).get(
                    "nodes", {}).values():
                _graph_terms.update(_node.get("terms") or [])
            _cand_tokens = {w for w in (
                _graph_terms | {t.lower() for t in (
                    mm.get("intervention", "") + " " +
                    mm.get("mechanism", "")).split()
                    if len(t) >= 4 and t.isalpha()})
                if len(w) >= 4 and str(w).isalpha()}
            # R537: candidate and problem vocabularies are INDEPENDENT
            # inputs — the candidate carries the mechanism's own
            # words; the problem carries the device/failure/constraint
            # facts the mechanism must address.  Passing one set as
            # both (the R536 defect) silently collapsed the claimed
            # independent problem-domain signal; the filters below
            # are now actually two filters.
            _problem = getattr(env, "problem", None) or {}
            _prob_tokens = {w.lower() for w in " ".join(str(_problem.get(k) or "")
                                                        for k in
                                                        ("device", "failure",
                                                         "constraint",
                                                         "context")).split()
                            if len(w) >= 4 and w.isalpha()}
            # R537: the two independent domain-identity signals are
            # recorded accurately as ALTERNATIVES, not corroborating
            # (audit gap 6): the STRUCTURAL signal is the
            # candidate-terms set; the LEXICAL signal is the problem-
            # terms set.  The block's provenance (domain_identity)
            # names which alternative fired — never a fused
            # "both" reading.
            res = mc.check_candidate_against_cemetery(
                desc,
                candidate_terms=_cand_tokens or None,
                problem_terms=_prob_tokens or None)
            return {"verdict": res.get("verdict"),
                    "hard_blocks": len(res.get("hard_blocks", [])),
                    "warnings": len(res.get("warnings", [])),
                    "lessons_consulted": res.get("total_lessons_consulted"),
                    "full": res,
                    # R537 P0: the consultation SUCCEEDED — the
                    # negative-knowledge library was read; a BLOCKED
                    # verdict on this record is a real hard-block, and
                    # a non-BLOCKED verdict is a genuine clearance.
                    "cemetery_verdict_resolved": True}
        except Exception as exc:  # noqa: BLE001
            # R537 P0 (audit fail-open finding): a cemetery
            # consultation failure is a UNRESOLVED negative-knowledge
            # state — the caller MUST treat it as blocking, never as
            # a pass.  The AdjudicationAdapter gates its favorable
            # ESTABLISHED_PROVISIONALLY verdict on
            # cemetery_verdict_resolved (an explicit infrastructure
            # state, not the absence of a literal BLOCKED verdict).
            return {"verdict": "UNRESOLVED", "error": str(exc),
                    "cemetery_verdict_resolved": False,
                    "note": ("cemetery consultation failed (infrastructure "
                             "state, not a scientific verdict — Art. "
                             "XXV): no hard-block fired, but no "
                             "favorable adjudication may ride on an "
                             "unconsulted negative-knowledge library "
                             "either (Art. LI: a written-but-never-read "
                             "cemetery is a log, not a memory)")}


ADAPTERS = {
    "RETRIEVE": A2RetrievalAdapter(),
    "FREEZE": EvidenceFreezeAdapter(),
    "PREMISE_GATE": PremiseGateAdapter(),
    "SYNTHESIZE": SynthesizeAdapter(),
    "VERIFY": EvidenceVerifyAdapter(),
    "MECHANISM_SPACE": MechanismSpaceAdapter(),
    "COLLISION": CollisionEngineAdapter(),
    "PHYSICS": PhysicsStageAdapter(),
    "ATTACK": AttackEngineAdapter(),
    "CONTRADICTION": ContradictionQueueAdapter(),
    "KILLER_EXPERIMENT": KillerExperimentAdapter(),
    "IMPROVE": ImproveAdapter(),
    "ADJUDICATION": AdjudicationAdapter(),
    "CLASSIFY": EpistemicClassificationAdapter(),
    "NEXT_BEST_ACTION": NextBestActionAdapter(),
    "RANK": PortfolioRankingAdapter(),
}
# R402 (audit CB-9): the dead "CEMETERY_CHECK" registration is removed —
# one namespace, no unreachable registrations (the cemetery check is the
# ADJUDICATION sub-check via _CemeterySubCheck; the cemetery UPDATE is
# conductor-level after a final KILL/REJECT). R515: ADAPTERS ⊃
# STAGE_ORDER by exactly {"IMPROVE"} — the kill-point operation (see
# ImproveAdapter below; invoked post-rank with kill evidence, never in
# the linear chain). The asymmetry is the RECORDED, TESTED contract
# the R402 directive allows ("or the asymmetry is a recorded, tested
# contract", CODER_DIRECTIVE_R402.md W7). Pinned by test.

# Stage order per CEO directive D8 (exact chain; cemetery negative-knowledge
# check is a sub-check of ADJUDICATION; cemetery UPDATE is conductor-level).
# R394 section 6: PREMISE_GATE is a FIRST-CLASS stage between FREEZE and
# SYNTHESIZE — a malformed/false premise (e.g. grain boundaries in
# amorphous borosilicate glass) is rejected BEFORE candidate-generation
# compute is burned (directive: "first-class discovery stage, not an
# adversarial cleanup trick").
# R397 Phase 2: PHYSICS is a FIRST-CLASS stage between COLLISION and
# ATTACK — the physics solver (validated code) is now part of the LIVE
# RUN CHAIN for every ordinary user run: plausibility bounds before
# simulation, the four failure modes, the baseline comparison, and
# lifecycle verdicts that gate the candidate (consultant finding:
# "the physics solver is validated code but not part of the live run
# chain"). The D8 chain is 16 stages. [HISTORICAL — R397 era; see
# R532 note below for the current 15-stage canonical statement.]
# R394 section 6: PREMISE_GATE is a FIRST-CLASS stage between FREEZE and The D8 chain is 16 stages.
# R401: MECHANISM_SPACE is a FIRST-CLASS stage between VERIFY and
# COLLISION — the structured mechanism space (structured
# evidence -> five transformation operators -> distinctness ->
# mechanism-level verification). The chain is 16 stages. [HISTORICAL
# — R401 era.] Deliberate,
# documented contract change (same pattern as R394 PREMISE_GATE and
# R397 PHYSICS); pinned tests updated with the new arithmetic.
# R481 (external-audit P0-1): IMPROVE was a FIRST-CLASS stage between
# KILLER_EXPERIMENT and ADJUDICATION — the loop closure (dead ->
# mutated child -> the same gauntlet -> re-entry or typed re-kill).
# R515 (auditor directive): the linear D8 placeholder is REMOVED — its
# ordinary execution only ever recorded DEFERRED_TO_KILL_POINT (no
# work; measured milliseconds, R511). The chain is 15 stages. The
# real execution point is UNCHANGED: the Directive-1 pipeline's
# kill-evidence point (post-rank, kill evidence present) invokes the
# same ImproveAdapter through the same env.run_stage protocol; pinned
# tests updated with the new arithmetic.
# R532 doc-entropy repair (CANONICAL current statement — the "16
# stages" notes at R394/R397/R401 above are historical: they were
# true when written, while IMPROVE rode the linear chain):
#   15 linear live stages; IMPROVE = post-rank kill point;
#   ADAPTERS = STAGE_ORDER ∪ {IMPROVE} (intentional asymmetry,
#   recorded + tested contract per R402 W7).
STAGE_ORDER = ["RETRIEVE", "FREEZE", "PREMISE_GATE", "SYNTHESIZE",
               "VERIFY", "MECHANISM_SPACE",
               "COLLISION", "PHYSICS",
               "ATTACK", "CONTRADICTION", "KILLER_EXPERIMENT",
               "ADJUDICATION",
               "CLASSIFY", "NEXT_BEST_ACTION", "RANK"]
