"""discovery_fabric/engine/dry_run.py — deterministic dry-run mode.

ONE cliff (final-stretch directive): make the real EngineRun path
executable end-to-end (SUBMITTED -> RANKED + honest downstream funnel)
without live model credentials, so the actual candidate bottleneck
becomes measurable.

Design (Constitution Arts. X, XXV, LXI, LXXVII-LXXIX):
- FixtureTransport is a TEST TRANSPORT, never an epistemic fallback.
  It serves deterministic canned text at the single llm_registry
  seam, ONLY while explicitly bound in a dry-run EngineRun. LIVE
  behavior (no bound fixture) is byte-identical: one None check.
- Unmapped purposes fail fast with an honest typed refusal (never
  fabricated content, never a paid call, never a stall).
- Every dry-run artifact carries DRY_RUN_FIXTURE provenance and
  r506_eligible=False (fixture output can never enter the R506
  discovery-yield evidence population).
- Ranking is deterministic over RECORDED fields with fixed,
  recorded weights. A rank is a selection aid: rank 1 stays
  CANDIDATE, never DISCOVERY/INVENTION.
"""
from __future__ import annotations

import hashlib
import json as _json
import os as _os
import subprocess as _sp
from typing import Any, Dict, List, Optional

FIXTURE_PROVIDER_ID = "DRY_RUN_FIXTURE"
DRY_RUN_PROVENANCE = "DRY_RUN_FIXTURE"

PORTFOLIO_SCHEMA = "CANDIDATE_PORTFOLIO/1.0.0"
FUNNEL_SCHEMA = "DRY_RUN_FUNNEL/1.0.0"

# Stable dry-run candidate identity: the SCIENTIFIC content fields.
# The engine candidate_id rides verbatim (Art. X — one authority);
# `identity` is the repeatability comparator (timestamp-derived engine
# id suffixes are classified as permitted runtime metadata, never
# mixed into the scientific identity).
IDENTITY_FIELDS = (
    "mechanism", "intervention", "predicted_effect",
    "falsification_test", "mechanism_source_span",
    "novel_design_variable", "origin", "exploration_angle",
    "transformation_operator", "evidence_refs",
)


def _canonical(obj: Any) -> str:
    return _json.dumps(obj, sort_keys=True, ensure_ascii=False,
                       default=str)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()


def _stable_identity(fields: Dict[str, Any]) -> Dict[str, Any]:
    snap = {}
    for k in IDENTITY_FIELDS:
        v = fields.get(k)
        snap[k] = sorted(v) if isinstance(v, list) else (v or "")
    return {"identity": "dryid:" + _sha256_text(_canonical(snap))[:16],
            "identity_fields": list(IDENTITY_FIELDS)}


def _read_json(path: str) -> tuple:
    """Read a JSON artifact: (object_or_None, sha256_or_None)."""
    try:
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
        return _json.loads(raw), _sha256_text(raw)
    except Exception:
        return None, None


def _engine_commit() -> str:
    """Code commit for reproducibility (Art. LXII). Best-effort and
    honest: the git binary first, then a direct .git/HEAD read (no
    PATH dependence); UNKNOWN_GIT_UNAVAILABLE when neither answers
    — never fabricated (Art. VI)."""
    here = _os.path.dirname(_os.path.abspath(__file__))
    try:
        out = _sp.run(["git", "rev-parse", "HEAD"], cwd=here,
                      capture_output=True, text=True, timeout=15)
        sha = (out.stdout or "").strip()
        if out.returncode == 0 and len(sha) == 40:
            return sha
    except Exception:
        pass
    try:
        repo = here
        for _ in range(6):
            if _os.path.isdir(_os.path.join(repo, ".git")):
                break
            repo = _os.path.dirname(repo)
        head = _os.path.join(repo, ".git", "HEAD")
        with open(head, encoding="utf-8") as fh:
            ref = (fh.read() or "").strip()
        if ref and not ref.startswith("ref:"):
            if len(ref) == 40:
                return ref
        else:
            refpath = _os.path.join(
                repo, ".git", *ref.split(":", 1)[1].strip().split(
                    "/"))
            if _os.path.exists(refpath):
                with open(refpath, encoding="utf-8") as fh:
                    sha = (fh.read() or "").strip()
                if len(sha) == 40:
                    return sha
            packed = _os.path.join(repo, ".git", "packed-refs")
            want = ref.split(":", 1)[1].strip()
            with open(packed, encoding="utf-8") as fh:
                for line in fh:
                    parts = line.strip().split()
                    if len(parts) == 2 and parts[1] == want:
                        return parts[0]
    except Exception:
        pass
    return "UNKNOWN_GIT_UNAVAILABLE"

RANK_WEIGHTS = {
    "mechanism_support": 3,
    "span_bound": 2,
    "distinctness_distinct": 2,
    "evidence_refs": 1,
    "attack_survived": 2,
    "testability": 1,
}
RANKING_RULE = ("fixed weights v1 (support 3, span 2, distinct 2, "
                "evidence 1, attack-survived 2, testability 1); "
                "tie-break candidate_id asc; deterministic")


class FixtureTransport:
    """Deterministic canned-text transport for dry runs.

    specs: [{purpose_prefix?, purpose_exact?, route_exact?,
              prompt_contains?, content, status?}]. Matching is by
    DETERMINISTIC SPECIFICITY PRECEDENCE (never first-match-wins):
      1. exact purpose/stage match (purpose_exact);
      2. exact declared route match (route_exact — the call's pinned
         first-preferred provider);
      3. narrower prompt match (longer prompt_contains wins);
      4. otherwise no fixture match.
    A broad fixture can never capture a more specific request: among
    all specs whose declared constraints hold, the most specific wins;
    full ties break to the lowest spec index (stable, recorded). No
    match -> fast honest PROVIDER_UNAVAILABLE refusal (never
    fabricated). Every served call is logged (telemetry: purpose
    counts, zero paid calls by construction — no credential is ever
    consulted).
    """

    def __init__(self, specs: List[Dict[str, Any]],
                 bundle_id: str = "dry-run-bundle/1"):
        self.specs = list(specs or [])
        self.bundle_id = bundle_id
        self.served: List[Dict[str, Any]] = []
        self.refused: List[Dict[str, Any]] = []

    @staticmethod
    def _specificity(spec: Dict[str, Any]) -> tuple:
        """Specificity rank: exact purpose > exact route > narrower
        prompt (longer prompt_contains) > narrower prefix (longer
        purpose_prefix). Compared lexicographically; ties broken by
        spec index at the call site (stable)."""
        return (
            1 if spec.get("purpose_exact") is not None else 0,
            1 if spec.get("route_exact") is not None else 0,
            len(str(spec.get("prompt_contains") or "")),
            len(str(spec.get("purpose_prefix") or "")),
        )

    def match(self, purpose: str, prompt: str,
              route: str = "") -> Optional[Dict]:
        purpose = str(purpose or "")
        prompt = str(prompt or "")
        route = str(route or "")
        best = None
        best_key = None
        best_index = -1
        for i, spec in enumerate(self.specs):
            if not isinstance(spec, dict):
                continue
            pre = spec.get("purpose_prefix")
            if pre is not None and not purpose.startswith(str(pre)):
                continue
            ex = spec.get("purpose_exact")
            if ex is not None and purpose != str(ex):
                continue
            rt = spec.get("route_exact")
            if rt is not None and route != str(rt):
                continue
            pc = spec.get("prompt_contains")
            if pc is not None and str(pc) not in prompt:
                continue
            key = self._specificity(spec) + (-i,)
            if best_key is None or key > best_key:
                best, best_key, best_index = spec, key, i
        if best is None:
            return None
        return dict(best, _spec_index=best_index)

    def serve(self, prompt: str, system: str = "",
              purpose: str = "", run_id: Optional[str] = None,
              timeout: int = 0, route: str = ""):
        from .llm_registry import LLMCallResult
        from . import call_context as _cctx
        prompt = str(prompt or "")
        prompt_hash = hashlib.sha256(prompt.encode(
            "utf-8", "replace")).hexdigest()
        ctx = _cctx.current() or {}
        base_provenance = {
            "run_id": ctx.get("run_id", run_id),
            "session_id": ctx.get("session_id"),
            "engine_stage": ctx.get("stage"),
            "call_class": ctx.get("run_id") and "RUN_OWNED"
            or "STANDALONE",
            "dry_run_fixture": True,
            "fixture_bundle": self.bundle_id,
            "live_transport_bypassed": True,
        }
        spec = self.match(purpose, prompt, route)
        if spec is None:
            self.refused.append({"purpose": purpose,
                                 "route": str(route or ""),
                                 "prompt_hash": prompt_hash})
            return LLMCallResult(
                status="PROVIDER_UNAVAILABLE",
                content=None,
                provider_id=FIXTURE_PROVIDER_ID,
                model="fixture-refusal/1",
                prompt_hash=prompt_hash,
                output_hash=None,
                latency_ms=0,
                error=("dry-run fixture has no spec for purpose "
                       f"'{purpose}' — honest refusal, never "
                       "fabricated (Art. XXV)"),
                call_provenance=base_provenance,
                cost_provenance={"model_id": FIXTURE_PROVIDER_ID,
                                 "cost_basis": "no-charge-fixture",
                                 "local_or_remote": "in-process"})
        content = str(spec.get("content") or "")
        output_hash = hashlib.sha256(content.encode(
            "utf-8", "replace")).hexdigest()
        self.served.append({"purpose": purpose,
                            "route": str(route or ""),
                            "prompt_hash": prompt_hash,
                            "output_hash": output_hash,
                            "spec_index": spec.get("_spec_index")})
        return LLMCallResult(
            status=str(spec.get("status") or "OK"),
            content=content,
            provider_id=FIXTURE_PROVIDER_ID,
            model="fixture-text/1",
            prompt_hash=prompt_hash,
            output_hash=output_hash,
            latency_ms=0,
            call_provenance={**base_provenance,
                             "fixture_spec": {
                                 k: v for k, v in spec.items()
                                 if k not in ("content", "_spec_index")},
                             "matched_spec_index": spec.get(
                                 "_spec_index")},
            cost_provenance={"model_id": FIXTURE_PROVIDER_ID,
                             "cost_basis": "no-charge-fixture",
                             "local_or_remote": "in-process"})

    def input_identity(self) -> str:
        """Deterministic identity of the fixture bundle's DECLARED
        inputs (order-independent): sha256 over the sorted per-spec
        content hashes + match keys. Two bundles with the same texts
        and match keys share the identity regardless of spec order."""
        parts = []
        for spec in self.specs:
            if not isinstance(spec, dict):
                continue
            parts.append(_canonical({
                "purpose_prefix": spec.get("purpose_prefix"),
                "purpose_exact": spec.get("purpose_exact"),
                "route_exact": spec.get("route_exact"),
                "prompt_contains": spec.get("prompt_contains"),
                "status": spec.get("status") or "OK",
                "content_sha256": _sha256_text(
                    str(spec.get("content") or "")),
            }))
        return "drybundle:" + _sha256_text(
            _canonical(sorted(parts)))[:16]

    def telemetry(self) -> Dict[str, Any]:
        by_purpose: Dict[str, int] = {}
        prompt_counts: Dict[str, int] = {}
        for s in self.served:
            by_purpose[s["purpose"]] = by_purpose.get(
                s["purpose"], 0) + 1
            _ph = s.get("prompt_hash") or ""
            prompt_counts[_ph] = prompt_counts.get(_ph, 0) + 1
        # A re-served prompt hash is a transport-level retry (the
        # fixture short-circuits before any live retry loop, so this
        # is the complete retry count — mechanical, never inferred).
        retries = sum(max(0, n - 1)
                      for n in prompt_counts.values())
        refused_purposes = sorted({r["purpose"] for r in self.refused})
        return {"provider_id": FIXTURE_PROVIDER_ID,
                "bundle_id": self.bundle_id,
                "bundle_identity": self.input_identity(),
                "n_calls_served": len(self.served),
                "n_calls_refused": len(self.refused),
                "served_by_purpose": by_purpose,
                "refused_purposes": refused_purposes,
                "retries": retries,
                "paid_calls": 0,
                "live_calls": 0,
                "credentials_consulted": False}


def _support_points(mechanism_support: Any) -> int:
    verdict = ""
    if isinstance(mechanism_support, dict):
        verdict = str(mechanism_support.get("verdict") or
                       mechanism_support.get("state") or
                       mechanism_support.get("mechanism_support_state")
                       or "")
    return {"SUPPORTS": 3, "PARTIALLY_SUPPORTS": 2,
            "NOT_ENOUGH_EVIDENCE": 1}.get(verdict, 0)


def rank_candidates(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deterministic portfolio ranking over RECORDED fields only.
    Returns [{candidate_id, rank, score, basis}] with rank 1..N.
    Pure function (no I/O, no LLM, no timestamps)."""
    scored = []
    for it in items:
        if not isinstance(it, dict):
            continue
        parts = {
            "mechanism_support": _support_points(
                it.get("mechanism_support")),
            "span_bound": 2 if it.get("span_bound") else 0,
            "distinctness_distinct": 2
            if it.get("distinctness_verdict") == "DISTINCT" else 0,
            "evidence_refs": min(1, len(
                it.get("evidence_refs") or [])),
            "attack_survived": 2
            if it.get("attack_status") == "SURVIVED" else 0,
            "testability": 1 if it.get("testable") else 0,
        }
        capped = {k: min(int(v), int(RANK_WEIGHTS[k]))
                  for k, v in parts.items()}
        total = sum(capped.values())
        scored.append({"candidate_id": it.get("candidate_id"),
                       "score": total, "parts": capped})
    scored.sort(key=lambda s: (-s["score"],
                               str(s.get("candidate_id") or "")))
    out = []
    for i, s in enumerate(scored):
        out.append({"candidate_id": s["candidate_id"], "rank": i + 1,
                    "score": s["score"], "basis": dict(s["parts"]),
                    "rule": RANKING_RULE})
    return out


def _grid_to_mechanism(entry: Dict[str, Any], constraint: str,
                        evidence_ids: List[str]) -> Dict[str, Any]:
    """Mechanical grid->mechanism mapping (r510 dry-run precedent,
    documented): fields ride verbatim (including the source span);
    empty dims stay empty (the distinctness adjudicator types thin
    pairs INDETERMINATE, never counted)."""
    from . import mechanism_space as _ms
    f = entry.get("fields") or {}
    modes = [f["failure_mode"]] if f.get("failure_mode") else []
    graph_fields = {"mechanism": f.get("mechanism", ""),
                    "intervention": f.get("intervention", ""),
                    "expected_effect": f.get("predicted_effect",
                                             f.get("effect", ""))}
    return {
        "candidate_id": entry.get("candidate_id"),
        "candidate_hash": str(entry.get("prompt_hash") or "") + str(
            entry.get("candidate_id") or "")[-12:],
        "candidate_state": "CANDIDATE" if f.get("intervention")
        else "DRAFT",
        "intervention": f.get("intervention", ""),
        "mechanism": f.get("mechanism", ""),
        "predicted_effect": f.get("predicted_effect",
                                  f.get("effect", "")),
        "novel_design_variable": f.get("design_variable",
                                       f.get("variable", "")),
        "known_failure_modes": modes,
        "constraint_set": {"boundary_conditions": constraint},
        "mechanism_graph": _ms.mechanism_graph_from_fields(
            graph_fields),
        "testable_prediction": f.get("falsification_test", ""),
        "falsification_test": f.get("falsification_test", ""),
        "mechanism_source_span": f.get("mechanism_source_span", ""),
        "span_derivation": f.get("span_derivation"),
        "evidence_refs": list(evidence_ids),
        "exploration_angle": entry.get("angle"),
        "transformation_operator": "",
        "origin": "EXPLORATION_GRID",
        "fixture_provenance": DRY_RUN_PROVENANCE,
    }


def _diversity_gate(n_distinct: int) -> Dict[str, Any]:
    """Art. LXXXIV minimum-diversity presentation: fewer than 2
    materially distinct candidates is MECHANISM_STARVED (may not
    report attack/contradiction/experiment results as discovery
    evidence). A presentation rule over the measured count — never a
    new gate on the science."""
    return {"rule": "Art. LXXXIV (>=2 materially distinct candidates)",
            "n_distinct": int(n_distinct),
            "gate": "PASS" if int(n_distinct) >= 2
            else "MECHANISM_STARVED"}


def _attack_transport_state(obj: Any) -> str:
    """Attack transport state from the independent-attack record's own
    llm_status — the honest infrastructure classification, never a
    scientific verdict (Art. XXV/LXI). PROVIDER_UNAVAILABLE (the
    dry-run fixture refusal) is transport unavailable, distinct from a
    kill and from a survival."""
    st = str((obj or {}).get("llm_status") or "")
    if st in ("PROVIDER_UNAVAILABLE", "AUTH_FAILED", "TIMEOUT",
              "RATE_LIMITED", "SEARCH_FAILED"):
        return "TRANSPORT_UNAVAILABLE"
    if st in ("OK", "SERVED", "COMPLETED"):
        return "TRANSPORT_AVAILABLE"
    return "TRANSPORT_UNKNOWN" if st else "UNKNOWN"


def _attack_independence_state(obj: Any) -> str:
    """Independence classification from the record's own
    independence_mode. SEPARATE_PROVIDER = true provider separation;
    SEPARATE_CONTEXT = separate reasoning context only (never claimed
    as provider separation — Art. XLV); absence of a record is
    INDEPENDENCE_UNAVAILABLE, not PASS."""
    mode = str((obj or {}).get("independence_mode") or "")
    if mode == "SEPARATE_PROVIDER":
        return "SEPARATE_PROVIDER"
    if mode == "SEPARATE_CONTEXT":
        return "SEPARATE_CONTEXT_ONLY"
    return "INDEPENDENCE_UNAVAILABLE"


def _attack_drop_transition(indep_overall: str, reached: bool) -> str:
    """Attack survivor-eligibility loss, from measured states only.
    ATTACK_INCOMPLETE is NEVER converted into KILLED or SURVIVED
    (Art. XXV/LXI/XXIX: an attack that did not run is not a kill and
    is not a survival)."""
    if not reached:
        return "ATTACK_NOT_REACHED"
    if indep_overall == "KILLED":
        return "ATTACK_KILLED"
    # the real instrument emits overall="SURVIVED" (independent_attack.py)
    # for a surviving candidate; "PASS" is kept for any legacy consumer.
    if indep_overall in ("SURVIVED", "PASS"):
        return "ATTACK_SURVIVED"
    if indep_overall in ("ATTACK_INCOMPLETE", "UNKNOWN", ""):
        return "ATTACK_INCOMPLETE"
    return "UNKNOWN"


def _pool_attack_states(run_dir: str) -> Dict[str, Dict[str, Any]]:
    """Per-candidate attack states from the run's own persisted pool
    records. INDEPENDENT_ATTACK_{key}.json carries candidate_id;
    ENGINEERING_ATTACK_{key}.json pairs by pool key. Missing files =
    attack never reached for that candidate (NOT_RUN — never
    inferred). The attack is MEASURED, never assumed: transport,
    independence and drop-transition are read from the records' own
    persisted fields (llm_status / independence_mode / overall),
    keeping ATTACK_INCOMPLETE distinct from KILLED and SURVIVED."""
    states: Dict[str, Dict[str, Any]] = {}
    by_key: Dict[str, str] = {}
    try:
        names = _os.listdir(run_dir)
    except Exception:
        return states
    for n in names:
        if n.startswith("INDEPENDENT_ATTACK_") and n.endswith(".json"):
            obj, _ = _read_json(_os.path.join(run_dir, n))
            if not isinstance(obj, dict):
                continue
            cid = obj.get("candidate_id")
            if not cid:
                continue
            key = n[len("INDEPENDENT_ATTACK_"):-len(".json")]
            by_key[key] = str(cid)
            reached = str(obj.get("overall") or "") != "NOT_RUN"
            states[str(cid)] = {
                "independent_attack_overall": obj.get("overall"),
                "independent_attack_attempted": reached,
                "independent_attack_state": obj.get("state"),
                "attack_reached": reached,
                "attack_transport_state": _attack_transport_state(obj),
                "attack_independence_state": _attack_independence_state(
                    obj),
                "pool_key": key,
            }
    for n in names:
        if n.startswith("ENGINEERING_ATTACK_") and n.endswith(".json"):
            obj, _ = _read_json(_os.path.join(run_dir, n))
            if not isinstance(obj, dict):
                continue
            key = n[len("ENGINEERING_ATTACK_"):-len(".json")]
            cid = by_key.get(key)
            if cid is None:
                continue
            states[cid]["engineering_attack_overall"] = obj.get(
                "overall")
    for cid, s in states.items():
        s["attack_drop_transition"] = _attack_drop_transition(
            str(s.get("independent_attack_overall") or ""),
            bool(s.get("attack_reached")))
    return states


def _frozen_evidence_ids(run_dir: str) -> List[str]:
    """Frozen evidence item ids from the run's own FREEZE envelope
    (fallback: final candidate envelope). Empty when unfrozen —
    never invented."""
    for name in ("envelope_FREEZE.json", "candidate_envelope.json"):
        obj, _ = _read_json(_os.path.join(run_dir, name))
        if isinstance(obj, dict):
            ev = obj.get("evidence") or []
            ids = [str(e.get("id")) for e in ev
                   if isinstance(e, dict) and e.get("id")]
            if ids:
                return ids
    return []


def build_portfolio(run_dir: str, problem: Dict[str, Any],
                    run_id: str, bundle_id: str,
                    bundle_identity: str = "") -> Dict:
    """Canonical ranked candidate portfolio from a dry-run's own
    persisted artifacts (EXPLORATION_GRID.json +
    envelope_MECHANISM_SPACE.json + envelope_FREEZE.json + per-key
    pool attack records). Real distinctness adjudicator,
    deterministic ranking. Rank never promotes epistemic state."""
    run_dir = str(run_dir)
    constraint = str((problem or {}).get("constraint") or "")
    sources: List[Dict[str, Any]] = []

    def _load(name: str) -> Optional[Dict]:
        obj, sha = _read_json(_os.path.join(run_dir, name))
        sources.append({"file": name, "sha256": sha,
                        "present": obj is not None})
        return obj if isinstance(obj, dict) else None

    ms_env = _load("envelope_MECHANISM_SPACE.json") or {}
    ms = ms_env.get("mechanism_space", ms_env) or {}
    if not isinstance(ms, dict):
        ms = {"state": "UNKNOWN_UNREADABLE"}
    _load("envelope_FREEZE.json")
    grid_doc = _load("EXPLORATION_GRID.json")
    grid_usable: List[Dict] = []
    grid_state = "UNKNOWN_NO_GRID_FILE"
    if grid_doc is not None:
        grid_state = str(grid_doc.get("status") or "UNKNOWN")
        for c in grid_doc.get("candidates", []):
            if isinstance(c, dict) and (c.get("fields") or {}).get(
                    "intervention"):
                grid_usable.append(c)
    frozen_ids = _frozen_evidence_ids(run_dir)
    # R510 transition ledger (adapter-observed, read verbatim from
    # the run's own MS envelope): MS-origin entries carry their
    # transition record; grid candidates never traverse the MS path
    # (null — never inferred).
    _trans_by_id: Dict[str, Dict[str, Any]] = {}
    _ms_trans = ms.get("candidate_transitions") or {}
    for _t in (_ms_trans.get("candidate_traces") or []):
        if isinstance(_t, dict) and _t.get("candidate_id"):
            _trans_by_id[str(_t["candidate_id"])] = _t
    mechs: List[Dict] = []
    for c in grid_usable:
        mechs.append(_grid_to_mechanism(c, constraint, frozen_ids))
    for c in (ms.get("candidates") or []):
        if not isinstance(c, dict):
            continue
        refs = []
        _eb = c.get("evidence_bundle") or {}
        if _eb.get("primary_item_id"):
            refs.append(_eb.get("primary_item_id"))
        mechs.append({
            "candidate_id": c.get("candidate_id"),
            "candidate_hash": c.get("candidate_hash"),
            "candidate_state": c.get("candidate_state"),
            "intervention": c.get("intervention", ""),
            "mechanism": c.get("mechanism", ""),
            "predicted_effect": c.get("predicted_effect", ""),
            "novel_design_variable": c.get(
                "novel_design_variable", ""),
            "known_failure_modes": c.get("known_failure_modes", []),
            "constraint_set": c.get("constraint_set", {}),
            "mechanism_graph": c.get("mechanism_graph", {}),
            "testable_prediction": c.get("testable_prediction", ""),
            "falsification_test": c.get("falsification_test", ""),
            "mechanism_source_span": c.get(
                "mechanism_source_span", ""),
            "span_binding": c.get("span_binding"),
            "mechanism_support": c.get("mechanism_support"),
            "evidence_refs": refs,
            "exploration_angle": "",
            "transformation_operator": c.get(
                "transformation_operator", ""),
            "transition_trace": _trans_by_id.get(
                str(c.get("candidate_id"))),
            "origin": "MECHANISM_SPACE",
            "fixture_provenance": DRY_RUN_PROVENANCE,
        })
    from . import mechanism_space as _ms
    ded = _ms.deduplicate_candidates(mechs)
    distinct = [c for c in mechs
                if c.get("distinctness_verdict") == "DISTINCT"]
    attacks = _pool_attack_states(run_dir)
    rank_inputs = []
    for c in distinct:
        _span = c.get("span_derivation") or {}
        _atk = attacks.get(str(c.get("candidate_id")), {})
        rank_inputs.append({
            "candidate_id": c.get("candidate_id"),
            "mechanism_support": c.get("mechanism_support"),
            "span_bound": bool(c.get("mechanism_source_span"))
            or not bool(_span.get("underived", True)),
            "distinctness_verdict": "DISTINCT",
            "evidence_refs": c.get("evidence_refs") or [],
            "attack_status": _atk.get("independent_attack_overall",
                                      "NOT_RUN"),
            "testable": bool(c.get("testable_prediction")
                             or c.get("falsification_test")),
        })
    ranking = rank_candidates(rank_inputs)
    rank_by_id = {r["candidate_id"]: r for r in ranking}
    # Scientific identities (stable across repeats; engine ids ride
    # verbatim). Computed once here so the portfolio entries and the
    # stable ranking hash share the exact same values.
    def _ident_of(c: Dict[str, Any]) -> Dict[str, Any]:
        return _stable_identity({
            "mechanism": c.get("mechanism", ""),
            "intervention": c.get("intervention", ""),
            "predicted_effect": c.get("predicted_effect", ""),
            "falsification_test": c.get("falsification_test", ""),
            "mechanism_source_span": c.get(
                "mechanism_source_span", ""),
            "novel_design_variable": c.get(
                "novel_design_variable", ""),
            "origin": c.get("origin", ""),
            "exploration_angle": c.get("exploration_angle", ""),
            "transformation_operator": c.get(
                "transformation_operator", ""),
            "evidence_refs": c.get("evidence_refs") or [],
        })
    _ident_map = {str(c.get("candidate_id")): _ident_of(c)
                  for c in distinct}
    # Stable ranking hash: the scoring-relevant projection of the
    # rank inputs with timestamp-derived engine ids replaced by
    # scientific identities AND the mechanism_support record reduced
    # to its verdict (the full support record embeds the engine
    # candidate_id; only the verdict affects the score via
    # _support_points). The engine-id ranking_inputs_hash rides
    # alongside for audit.
    def _support_verdict(sup: Any) -> str:
        if isinstance(sup, dict):
            return str(sup.get("verdict") or sup.get("state")
                       or sup.get("mechanism_support_state") or "")
        return ""
    _stable_inputs = [
        {"candidate_id": _ident_map.get(
            str(ri.get("candidate_id")), {}).get(
                "identity", ri.get("candidate_id")),
         "support_verdict": _support_verdict(
             ri.get("mechanism_support")),
         "span_bound": bool(ri.get("span_bound")),
         "distinctness_verdict": ri.get("distinctness_verdict"),
         "evidence_refs": ri.get("evidence_refs") or [],
         "attack_status": ri.get("attack_status"),
         "testable": bool(ri.get("testable"))}
        for ri in rank_inputs]
    candidates = []
    for c in distinct:
        _cid = str(c.get("candidate_id"))
        r = rank_by_id.get(c.get("candidate_id"), {})
        _atk = attacks.get(_cid, {})
        empty_dims = sum(1 for k in (
            "mechanism", "intervention", "predicted_effect",
            "falsification_test") if not c.get(k))
        ident = _ident_map.get(_cid, {"identity": "",
                                      "identity_fields": []})
        candidates.append({
            "candidate_id": c.get("candidate_id"),
            "identity": ident["identity"],
            "identity_fields": ident["identity_fields"],
            "candidate_hash": c.get("candidate_hash"),
            "rank": r.get("rank"),
            "ranking_basis": r.get("basis"),
            "ranking_rule": RANKING_RULE,
            "mechanism": c.get("mechanism", ""),
            "intervention": c.get("intervention", ""),
            "predicted_effect": c.get("predicted_effect", ""),
            "falsification_test": c.get("falsification_test", ""),
            "testable_prediction": c.get("testable_prediction", ""),
            "mechanism_source_span": c.get(
                "mechanism_source_span", ""),
            "novel_design_variable": c.get(
                "novel_design_variable", ""),
            "distinctness": "DISTINCT",
            "distinctness_state": "DISTINCT",
            "distinctness_basis": c.get("distinctness_basis"),
            "state": c.get("candidate_state"),
            "evidence_refs": c.get("evidence_refs") or [],
            "attack": {
                "independent_attack_overall": _atk.get(
                    "independent_attack_overall", "NOT_RUN"),
                "independent_attack_attempted": bool(
                    _atk.get("independent_attack_attempted")),
                "independent_attack_status": _atk.get(
                    "independent_attack_overall", "NOT_RUN"),
                "engineering_attack_overall": _atk.get(
                    "engineering_attack_overall", "NOT_RUN"),
                "engineering_attack_status": _atk.get(
                    "engineering_attack_overall", "NOT_RUN"),
                "attack_reached": bool(_atk.get("attack_reached")),
                "attack_transport_state": _atk.get(
                    "attack_transport_state", "UNKNOWN"),
                "attack_independence_state": _atk.get(
                    "attack_independence_state",
                    "INDEPENDENCE_UNAVAILABLE"),
                "attack_drop_transition": _atk.get(
                    "attack_drop_transition", "ATTACK_NOT_REACHED"),
                "pool_key": _atk.get("pool_key"),
            },
            "attack_status": _atk.get("attack_drop_transition",
                                      "ATTACK_NOT_REACHED"),
            "uncertainties": {
                "empty_mechanism_dims": empty_dims,
                "feasibility": "UNKNOWN",
                "note": "feasibility unevaluated in dry-run funnel "
                        "(never guessed)",
            },
            "origin": c.get("origin"),
            "exploration_angle": c.get("exploration_angle", ""),
            "transformation_operator": c.get(
                "transformation_operator", ""),
            "transitions": (
                None if (c.get("origin") or "").startswith(
                    "EXPLORATION_GRID") else {
                        "drop_transition": (
                            c.get("transition_trace") or {}).get(
                                "drop_transition"),
                        "cemetery_state": (
                            c.get("transition_trace") or {}).get(
                                "cemetery_state"),
                        "support_state": (
                            c.get("transition_trace") or {}).get(
                                "support_state"),
                        "pipeline_retained": (
                            c.get("transition_trace") or {}).get(
                                "pipeline_retained"),
                        "survivor_eligible": (
                            c.get("transition_trace") or {}).get(
                                "survivor_eligible"),
                    }),
            "provenance": DRY_RUN_PROVENANCE,
        })
    candidates.sort(key=lambda c: (c.get("rank") or 10 ** 9))
    problem_id = (problem or {}).get("problem_id")
    det_input = "dryinput:" + _sha256_text(_canonical({
        "problem": problem or {},
        "fixture_bundle": bundle_id,
        "bundle_identity": bundle_identity or "",
    }))[:16]
    return {
        "artifact_type": PORTFOLIO_SCHEMA,
        "schema_version": PORTFOLIO_SCHEMA,
        "request_id": run_id,
        "run_id": run_id,
        "problem_id": problem_id,
        "mode": DRY_RUN_PROVENANCE,
        "fixture_bundle": bundle_id,
        "bundle_identity": bundle_identity or "",
        "deterministic_input_identity": det_input,
        "source_artifacts": sources,
        "engine": {"runner": "EngineRun",
                   "code_commit": _engine_commit()},
        "candidate_count_generated": len(grid_usable) + int(
            ms.get("n_candidates_generated") or 0),
        "candidate_count_distinct": len(distinct),
        "candidate_count_ranked": len(candidates),
        "minimum_diversity_gate": _diversity_gate(len(distinct)),
        "ranking_inputs_hash": _sha256_text(
            _canonical(rank_inputs)),
        "ranking_stable_hash": _sha256_text(
            _canonical(_stable_inputs)),
        "distinctness": {
            "instrument": "mechanism_distinctness/2.0.0",
            "n_distinct": ded.get("n_distinct", 0),
            "n_indeterminate": ded.get("n_indeterminate", 0),
            "n_equivalent_merged": ded.get(
                "n_equivalent_merged", 0) + ded.get(
                    "n_equivalent", 0),
        },
        "grid_state": grid_state,
        "mechanism_space_state": ms.get("state", "UNKNOWN_NO_RECORD"),
        "candidates": candidates,
        "epistemic_use": "DRY_RUN_ORCHESTRATION_ONLY",
        "r506_eligible": False,
        "rank_is_selection_aid_only": True,
    }


def build_funnel(run_dir: str, stage_log: List[Dict],
                 fixture_telemetry: Dict, portfolio: Dict,
                 run_id: str, bundle_id: str,
                 problem: Optional[Dict[str, Any]] = None,
                 bundle_identity: str = "",
                 final_status: str = "",
                 tail: Optional[Dict[str, Any]] = None) -> Dict:
    """Dry-run funnel telemetry: counts at every transition + stage
    durations + provider calls + blocking stage + typed reasons.
    Zeros are data (unreached stages recorded, never skipped
    silently). Durations prefer the monotonic high-resolution stage
    timer (candidate.run_stage duration_monotonic_s); the wall-clock
    ISO delta is the fallback only. Provenance timestamps are never
    rewritten here."""
    import datetime as _dt
    stages = {}
    for e in (stage_log or []):
        if not isinstance(e, dict):
            continue
        name = str(e.get("stage") or "UNKNOWN")
        dur = e.get("duration_monotonic_s")
        try:
            dur = float(dur) if dur is not None else None
        except Exception:
            dur = None
        if dur is None:
            try:
                _s = _dt.datetime.fromisoformat(
                    str(e.get("started_at") or "").replace(
                        "Z", "+00:00"))
                _f = _dt.datetime.fromisoformat(
                    str(e.get("finished_at") or "").replace(
                        "Z", "+00:00"))
                dur = max(0.0, (_f - _s).total_seconds())
            except Exception:
                dur = None
        stages[name] = {"status": e.get("status"),
                        "duration_s": dur}
    blocking = None
    for e in (stage_log or []):
        if isinstance(e, dict) and str(e.get("status") or "") not in (
                "OK", "DISABLED_BY_CONFIG"):
            blocking = {"stage": e.get("stage"),
                        "status": e.get("status"),
                        "reason": e.get("skip_reason")
                        or e.get("upstream_failure")
                        or e.get("error") or "see stage record"}
            break
    dist = (portfolio or {}).get("distinctness") or {}
    port_cands = (portfolio or {}).get("candidates") or []
    atk_reached = sum(
        1 for c in port_cands
        if isinstance(c, dict) and ((c.get("attack") or {}).get(
            "independent_attack_overall", "NOT_RUN") != "NOT_RUN"))
    atk_survived = sum(
        1 for c in port_cands
        if isinstance(c, dict) and ((c.get("attack") or {}).get(
            "independent_attack_overall")) in ("SURVIVED", "PASS"))
    naive_attack_overall = None
    _atk_env, _ = _read_json(_os.path.join(run_dir,
                                           "envelope_ATTACK.json"))
    if isinstance(_atk_env, dict):
        naive_attack_overall = ((_atk_env.get("attack_results")
                                 or {}).get("overall"))
    _port_cands = port_cands
    atk_detail = "; ".join(
        "%s=%s/%s(%s)" % (
            str(c.get("candidate_id") or "?")[-12:],
            ((c.get("attack") or {}).get(
                "independent_attack_overall") or "NOT_RUN"),
            ((c.get("attack") or {}).get(
                "engineering_attack_overall") or "NOT_RUN"),
            ((c.get("attack") or {}).get(
                "attack_drop_transition") or "ATTACK_NOT_REACHED"))
        for c in _port_cands if isinstance(c, dict)) or "no candidates"
    atk_state = ("naive=%s; pool: %s" % (
        naive_attack_overall or "NO_ATTACK_STAGE", atk_detail))
    # Art. LXXXIII/LXI: attack is MEASURED, never assumed — classify
    # each pool candidate's transport/independence/drop from the
    # persisted records, keeping ATTACK_INCOMPLETE distinct from
    # KILLED and SURVIVED. Infrastructure failure (transport
    # unavailable in the dry-run) is never a scientific rejection.
    attack_measurement = {}
    for c in _port_cands:
        if not isinstance(c, dict):
            continue
        _a = (c.get("attack") or {})
        attack_measurement[str(c.get("candidate_id"))] = {
            "attack_reached": bool(_a.get("attack_reached")),
            "independent_attack_attempted": bool(
                _a.get("independent_attack_attempted")),
            "independent_attack_status": _a.get(
                "independent_attack_overall", "NOT_RUN"),
            "engineering_attack_status": _a.get(
                "engineering_attack_overall", "NOT_RUN"),
            "attack_transport_state": _a.get(
                "attack_transport_state", "UNKNOWN"),
            "attack_independence_state": _a.get(
                "attack_independence_state",
                "INDEPENDENCE_UNAVAILABLE"),
            "attack_drop_transition": _a.get(
                "attack_drop_transition", "ATTACK_NOT_REACHED"),
        }
    attack_agg = {
        "NOT_REACHED": 0, "ATTEMPTED": 0, "COMPLETED": 0,
        "INCOMPLETE": 0, "KILLED": 0, "SURVIVED": 0, "UNKNOWN": 0}
    for _m in attack_measurement.values():
        dt = _m["attack_drop_transition"]
        key = {"ATTACK_NOT_REACHED": "NOT_REACHED",
               "ATTACK_INCOMPLETE": "INCOMPLETE",
               "ATTACK_KILLED": "KILLED",
               "ATTACK_SURVIVED": "SURVIVED"}.get(dt, "UNKNOWN")
        attack_agg[key] += 1
    problem = problem or {}
    # The run's terminal status is final_state.json (post-evolution);
    # the passed final_status (naive candidate level) is the fallback.
    _final = final_status or ""
    _fs_doc, _ = _read_json(_os.path.join(run_dir, "final_state.json"))
    if isinstance(_fs_doc, dict) and _fs_doc.get("final_status"):
        _final = str(_fs_doc["final_status"])
    det_input = "dryinput:" + _sha256_text(_canonical({
        "problem": problem,
        "fixture_bundle": bundle_id,
        "bundle_identity": bundle_identity or "",
    }))[:16]
    return {
        "artifact_type": FUNNEL_SCHEMA,
        "schema_version": FUNNEL_SCHEMA,
        "request_id": run_id,
        "run_id": run_id,
        "problem_id": problem.get("problem_id"),
        "mode": DRY_RUN_PROVENANCE,
        "fixture_bundle": bundle_id,
        "bundle_identity": bundle_identity or "",
        "deterministic_input_identity": det_input,
        "engine": {"runner": "EngineRun",
                   "code_commit": _engine_commit()},
        "final_status": _final,
        "submitted": 1,
        "premise": 1 if stages.get("PREMISE_GATE", {}).get(
            "status") == "OK" else 0,
        "evidence": len(_frozen_evidence_ids(run_dir)),
        "mechanisms": int((portfolio or {}).get(
            "candidate_count_generated") or 0),
        "distinct": int(dist.get("n_distinct") or 0),
        "ranked": int((portfolio or {}).get(
            "candidate_count_ranked") or 0),
        "attack_reached": 1 if "ATTACK" in stages or
        "INDEPENDENT_ATTACK" in stages else 0,
        "attack_naive_overall": naive_attack_overall,
        "attack_candidates_reached": atk_reached,
        "attack_survived": atk_survived,
        "attack_state": atk_state,
        "attack_measurement": attack_measurement,
        "attack_state_aggregate": attack_agg,
        "contradiction_survived": 0,
        "experimentally_discriminated": 0,
        "mutated_survivors": 0,
        "buyer_ready": 0,
        "stage_statuses": {k: v["status"]
                           for k, v in stages.items()},
        "stage_durations_s": {k: v["duration_s"]
                              for k, v in stages.items()},
        "provider_calls": fixture_telemetry or {},
        "retries": int((fixture_telemetry or {}).get("retries", 0)),
        "tail_durations_s": dict(tail or {}),
        "tail_total_s": round(sum(
            float(v) for v in (tail or {}).values()), 3),
        "skipped_stages": sorted(
            k for k, v in stages.items()
            if str(v["status"] or "").startswith("SKIP")),
        "blocking_stage": blocking,
        "epistemic_use": "DRY_RUN_ORCHESTRATION_ONLY",
        "r506_eligible": False,
    }
