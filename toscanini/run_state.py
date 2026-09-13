"""toscanini/run_state.py — R414: the canonical DiscoveryRun object.

Operator directive (product integration, sections 1, 4, 5, 18):
  Every legitimate user query creates a discovery RUN that progresses
  through explicit states; the frontend reads THIS state and never
  infers that an invention exists because a GLB exists. Every terminal
  run lands in exactly one of four outcomes:

    INVENTION_SURVIVED            credible candidate progressed toward a
                                  technology package
    INVENTION_REQUIRES_EXPERIMENT strong enough conceptually, decisive
                                  physical evidence missing
    NO_DEFENSIBLE_INVENTION        the territory was explored and
                                  nothing survived
    RUN_BLOCKED                    infrastructure/evidence/provider
                                  failure prevented a scientifically
                                  meaningful conclusion

Constitutional contract (Art. X, XXV, LXI, LXVIII):
  - The run directory's persisted artifacts are the AUTHORITY; this
    module only PROJECTS them (it invents nothing).
  - RUN_BLOCKED is reserved for infrastructure-class terminations — a
    scientific rejection is NO_DEFENSIBLE_INVENTION, never RUN_BLOCKED
    (Art. LXI: infrastructure failure is never scientific rejection,
    and the converse holds here too).
  - The outcome is derived from RECORDED fields only; absence of a
    field is never evidence (Art. XXV).
  - No quota pressure: a weak architecture is presented with its true
    maturity, never softened into a survivor (Art. LXVIII).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# The four terminal outcomes (directive §18) + the non-terminal PENDING
# ---------------------------------------------------------------------------
OUTCOME_PENDING = "PENDING"
OUTCOME_SURVIVED = "INVENTION_SURVIVED"
OUTCOME_REQUIRES_EXPERIMENT = "INVENTION_REQUIRES_EXPERIMENT"
OUTCOME_UNDER_DEVELOPMENT = "INVENTION_UNDER_DEVELOPMENT"
OUTCOME_FALSE_PREMISE = "FALSE_PREMISE_INCOHERENT"
OUTCOME_NO_DEFENSIBLE = "NO_DEFENSIBLE_INVENTION"   # R416: legacy key —
#   no longer emitted as a terminal; kept so pre-R416 session records
#   map onto the UNDER_DEVELOPMENT projection instead of rendering the
#   banned dead-end sentence
OUTCOME_RUN_BLOCKED = "RUN_BLOCKED"
# R452 (external audit B1/AT-7): the typed terminal for an invention the
# machine's OWN adversarial challenge killed — the projection used to
# read only final_status and promoted the killed lineage to a positive
# outcome (measured 7/7 production runs)
OUTCOME_KILLED_BY_CHALLENGE = "INVENTION_KILLED_BY_CHALLENGE"

#: R452: the recorded kill_reason signature of a MODEL CAPABILITY failure
#: (the generator could not emit the required citation format). A kill
#: with this signature is an infrastructure/capability state, NEVER a
#: scientific rejection (Art. LXI) — the a2/classify.py fix stops
#: producing it; this detector keeps HISTORICAL records honest.
_CAPABILITY_KILL_SIGNATURE = "evidence verification failed"

OUTCOME_LABELS = {
    OUTCOME_PENDING: "Investigating",
    OUTCOME_SURVIVED: "Invention survived",
    OUTCOME_REQUIRES_EXPERIMENT: "Invention requires experiment",
    OUTCOME_UNDER_DEVELOPMENT: "Invention under development",
    OUTCOME_FALSE_PREMISE: "Premise incoherent — reformulate the problem",
    OUTCOME_NO_DEFENSIBLE: "Invention under development",
    OUTCOME_RUN_BLOCKED: "Run blocked — infrastructure, not a verdict",
    OUTCOME_KILLED_BY_CHALLENGE: "Killed by its own adversarial challenge",
}

_RUNNING_STATUSES = ("PENDING", "BUILDING_PROBLEM", "RUNNING", "")
_BLOCKED_STATUSES = ("INTERRUPTED", "ERROR_TRANSPORT", "ERROR_BUILD",
                     "ERROR_RUN", "ERROR_STUCK",
                     "RUN_BLOCKED_TRANSPORT")   # R415: the directive §8
#                    infrastructure-blocked state, distinct from every
#                    discovery verdict (Art. LXI)

# Engine stage -> product phase (directive §5: each UI state must
# correspond to a real backend stage). The canonical engine STAGE_ORDER
# is the authority; this map only groups it for display.
PHASES = [
    ("INVESTIGATING", "Investigating your problem",
     ["BUILDING_PROBLEM"]),
    ("GATHERING_EVIDENCE", "Gathering evidence",
     ["RETRIEVE", "FREEZE", "VERIFY"]),
    ("MAPPING_MECHANISMS", "Inventing architecture 1",
     ["PREMISE_GATE", "SYNTHESIZE", "MECHANISM_SPACE",
      "MULTI_SOURCE_DISCOVERY", "COLLISION"]),
    ("STRESS_TESTING", "Challenging architecture 1",
     ["PHYSICS", "ATTACK", "CONTRADICTION"]),
    ("PREPARING_PACKAGE", "Preparing technology package",
     ["KILLER_EXPERIMENT", "ADJUDICATION", "CLASSIFY",
      "NEXT_BEST_ACTION", "RANK", "PACKAGE"]),
]


def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        if p.exists():
            data = json.loads(p.read_text())
            return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001 — honest absent, never crash the UI
        return None
    return None


def _stage_status_map(session: Dict[str, Any],
                      run_dir: Optional[Path]) -> Dict[str, str]:
    """stage -> recorded status, from the run's own persisted records:
    the per-stage envelopes' stage_log entries (live during a run) and
    the run manifest's stage log (written at finalize). The LAST entry
    per stage wins. NOT from inference."""
    out: Dict[str, str] = {}
    if not run_dir or not run_dir.exists():
        return out
    sources: List[Path] = sorted(run_dir.glob("envelope_*.json"))
    manifest = run_dir / "run_manifest.json"
    if manifest.exists():
        sources.append(manifest)
    for env_path in sources:
        env = _read_json(env_path)
        for entry in (env or {}).get("stage_log") or []:
            if isinstance(entry, dict) and entry.get("stage"):
                out[entry["stage"]] = str(entry.get("status") or "UNKNOWN")
    return out


def _classify_stage(status: str) -> str:
    s = (status or "").upper()
    if s == "OK":
        return "DONE"
    if s.startswith("SKIPPED") or s.startswith("DISABLED"):
        return "SKIPPED"
    if s in ("", "UNKNOWN"):
        return "NOT_REACHED"
    return "FAILED"


def _envelope(run_dir: Optional[Path], stage: str) -> Optional[Dict]:
    if not run_dir:
        return None
    return _read_json(run_dir / f"envelope_{stage}.json")


# R443: provider records found under these keys are EVIDENCE-SOURCE
# provenance (retrieval providers: unpaywall, EuropePMC, arxiv...), not
# model execution. The fresh-production audit measured the defect: the
# walk attributed "provider: unpaywall" to 16 stage ROLES because every
# envelope embeds evidence records whose provenance.provider is a
# retrieval source — model_route must never report an evidence source
# as the provider that executed a stage's model work.
_EVIDENCE_CONTEXT_KEYS = {
    "evidence", "records", "retrieval", "sources", "provider_outcomes",
    "prior_art", "sample_titles", "collisions", "contradictions",
    "related_records", "cited_by",
}
# retrieval-provenance shape markers (a provider dict carrying these is
# describing a RETRIEVAL, not a model call)
_RETRIEVAL_PROVENANCE_KEYS = {
    "retrieved_at", "query_or_method", "api_version", "source_uri",
    "source_id",
}
_LLM_TRANSPORT_MARKERS = {
    "model", "prompt_hash", "output_hash", "transport_status",
    "failure_type", "latency_ms", "status", "retry_notes",
}


def _known_evidence_source(pid: str) -> bool:
    """A registered retrieval source id (or its normalized form) is
    never an LLM execution provider (one authority: the registry)."""
    low = str(pid).strip().lower()
    try:
        from discovery_fabric.source_registry.registry import (
            SOURCE_REGISTRY,
        )
        if low in SOURCE_REGISTRY:
            return True
    except Exception:  # noqa: BLE001 — registry absent: fall through
        pass
    norm = "".join(ch for ch in low if ch.isalnum())
    return norm in {
        "unpaywall", "europepmc", "arxiv", "crossref", "openalex",
        "pubmed", "semanticscholar", "core", "zenodo", "doaj",
        "openaire", "datacite", "cordis",
    }


def _is_model_call_record(obj: Dict[str, Any]) -> bool:
    """A provider record counts as MODEL EXECUTION only when it carries
    an LLM-transport marker AND is not retrieval provenance AND its
    provider is not a registered evidence source."""
    pid = obj.get("provider") or obj.get("provider_id")
    if not isinstance(pid, str) or not pid:
        return False
    if _known_evidence_source(pid):
        return False
    if (set(obj.keys()) & _RETRIEVAL_PROVENANCE_KEYS) and not (
            set(obj.keys()) & _LLM_TRANSPORT_MARKERS):
        return False
    return True


def _walk_providers(obj: Any, found: List[Dict[str, Any]],
                    depth: int = 0, parent_key: str = "") -> None:
    """Bounded recursive scan for persisted MODEL-CALL records
    (model_route is aggregated from what the run ACTUALLY recorded —
    never from configuration; R443: evidence-source provenance is
    excluded — a retrieval provider never executed a stage's model
    work). Depth-limited to keep the scan cheap on large envelopes."""
    if depth > 4:
        return
    if isinstance(obj, dict):
        pid = obj.get("provider") or obj.get("provider_id")
        if isinstance(pid, str) and pid and not str(pid).startswith("$") \
                and parent_key not in _EVIDENCE_CONTEXT_KEYS \
                and _is_model_call_record(obj):
            rec = {"provider": pid}
            for k_src, k_dst in (("model", "model"), ("status", "status"),
                                 ("latency_ms", "latency_ms"),
                                 ("purpose", "purpose"),
                                 ("failure_type", "failure_type")):
                v = obj.get(k_src)
                if isinstance(v, (str, int)) and v:
                    rec[k_dst] = v
            if rec not in found:
                found.append(rec)
        for k, v in obj.items():
            if k in _EVIDENCE_CONTEXT_KEYS and not isinstance(v, dict):
                continue
            _walk_providers(v, found, depth + 1, str(k))
    elif isinstance(obj, list):
        for v in obj[:60]:
            _walk_providers(v, found, depth + 1, parent_key)


def _model_route(session: Dict[str, Any],
                 run_dir: Optional[Path]) -> Dict[str, Any]:
    """Which providers/models actually executed work on this run, from
    persisted bytes: the evidence pack's extraction call, the run
    envelopes' provider records, and the preflight transport the worker
    verified (the gateway probe is recorded in the evidence pack llm
    block when a run exists)."""
    calls: List[Dict[str, Any]] = []
    ep = session.get("evidence_pack") or {}
    llm = ep.get("llm") or (ep.get("problem") or {}).get("llm") or {}
    if isinstance(llm, dict) and llm.get("provider"):
        calls.append({"role": "evidence_extraction",
                      "provider": llm.get("provider"),
                      "model": llm.get("model"),
                      "status": llm.get("status")})
    if run_dir and run_dir.exists():
        for env_path in sorted(run_dir.glob("envelope_*.json")):
            env = _read_json(env_path)
            if env:
                found: List[Dict[str, Any]] = []
                _walk_providers(env, found)
                for rec in found[:8]:
                    rec = dict(rec)
                    rec["role"] = env_path.stem.replace("envelope_", "")
                    if rec not in calls:
                        calls.append(rec)
    return {
        "calls": calls[:24],
        "call_count": len(calls),
        "note": ("aggregated from persisted run artifacts (envelopes, "
                 "evidence pack); configuration is never reported as "
                 "execution"),
    }


def _evidence_state(session: Dict, run_dir: Optional[Path]) -> Dict:
    ep = session.get("evidence_pack") or {}
    retrieval = ep.get("retrieval") or []
    env = _envelope(run_dir, "RETRIEVE") or {}
    evidence = env.get("evidence") or []
    sources = sorted({(e.get("source") or "?") for e in evidence
                      if isinstance(e, dict)}) if evidence else []
    failed = {}
    if run_dir:
        manifest = _read_json(run_dir / "run_manifest.json") or {}
        failed = manifest.get("failed_stages") or {}
    retrieve_failed = bool(failed.get("RETRIEVE"))
    return {
        "state": ("FAILED" if retrieve_failed else
                  "GATHERED" if (evidence or retrieval) else
                  "PENDING" if session.get("status") in _RUNNING_STATUSES
                  else "NOT_REACHED"),
        "records_found": len(evidence) or len(retrieval) or 0,
        "sources": sources[:10],
        "retrieval_route": ep.get("routing") or
        (ep.get("retrieval_route") or "UNKNOWN"),
        "provider_outcomes": ep.get("provider_outcomes") or [],
    }


def _mechanism_state(session: Dict, run_dir: Optional[Path],
                     stage_status: Dict[str, str]) -> Dict:
    syn = _envelope(run_dir, "SYNTHESIZE") or {}
    mm = syn.get("mechanism_map") or {}
    ms = _envelope(run_dir, "MECHANISM_SPACE") or {}
    candidates = ms.get("candidates") or []
    ok = any(_classify_stage(stage_status.get(s, "")) == "DONE"
             for s in ("SYNTHESIZE", "MECHANISM_SPACE"))
    failed = any(_classify_stage(stage_status.get(s, "")) == "FAILED"
                 for s in ("SYNTHESIZE", "MECHANISM_SPACE"))
    return {
        "state": ("FAILED" if failed else
                  "GENERATED" if ok or mm else
                  "PENDING" if session.get("status") in _RUNNING_STATUSES
                  else "NOT_REACHED"),
        "mechanism": mm.get("mechanism"),
        "intervention": mm.get("intervention"),
        "expected_effect": mm.get("expected_effect"),
        "candidate_count": (len(candidates)
                            if isinstance(candidates, list) else 0),
    }


def _invention_state(session: Dict, run_dir: Optional[Path]) -> Dict:
    final = (session.get("final_status") or "").upper()
    inv = _read_json(run_dir / "INVENTION_SPECIFICATION.json") \
        if run_dir else None
    surv = _read_json(run_dir / "SURVIVOR_SELECTION.json") \
        if run_dir else None
    pkg = session.get("package") or {}
    exists = bool(inv or surv or final == "AUTOMATED_INVENTION_CANDIDATE")
    return {
        "state": ("EXISTS" if exists else
                  "REJECTED" if final in ("REJECTED",
                                          "MALFORMED_OR_FALSE_PREMISE")
                  else "PENDING" if session.get("status") in
                  _RUNNING_STATUSES else "NONE"),
        "final_status": session.get("final_status"),
        "specification_present": bool(inv),
        "survivor_recorded": bool(surv or
                                  final == "AUTOMATED_INVENTION_CANDIDATE"),
        "package_built": bool(pkg.get("complete")),
    }


def _physics_state(session: Dict, run_dir: Optional[Path],
                   stage_status: Dict[str, str]) -> Dict:
    env = _envelope(run_dir, "PHYSICS") or {}
    ph = env.get("physics") or {}
    st = _classify_stage(stage_status.get("PHYSICS", ""))
    # MECHANISM_NOT_SIMULATABLE is the R413 decision machine's honest
    # refusal (no validated solver covers the mechanism's domain) —
    # reported as NOT_SIMULATABLE, never counted as a simulation
    verdict = ph.get("lifecycle_verdict")
    not_sim = verdict in (None, "NOT_APPLICABLE",
                          "MECHANISM_NOT_SIMULATABLE")
    state = ("SIMULATED" if st == "DONE" and not not_sim
             else "NOT_SIMULATABLE" if verdict == "MECHANISM_NOT_SIMULATABLE"
             else "FAILED" if st == "FAILED"
             else "SKIPPED" if st == "SKIPPED"
             else "PENDING" if session.get("status") in
             _RUNNING_STATUSES else "NOT_APPLICABLE")
    return {
        "state": state,
        "lifecycle_verdict": verdict,
        "baseline_outcome": (ph.get("baseline_comparison") or {}).get(
            "outcome"),
        "epistemic_class": "COMPUTATIONAL_RESULT"
        if (state == "SIMULATED") else None,
        "note": ("the physics decision system's honest refusal: the "
                 "mechanism's domain has no validated solver (R413 "
                 "registry)" if verdict == "MECHANISM_NOT_SIMULATABLE"
                 else None),
    }


def _novelty_state(session: Dict, run_dir: Optional[Path]) -> Dict:
    pa_env = _envelope(run_dir, "MULTI_SOURCE_DISCOVERY") or {}
    prior_art = pa_env.get("prior_art")
    if isinstance(prior_art, dict):
        prior_art = prior_art.get("results") or []
    col = _envelope(run_dir, "COLLISION") or {}
    return {
        "state": ("SEARCHED" if prior_art is not None else
                  "PENDING" if session.get("status") in _RUNNING_STATUSES
                  else "NOT_REACHED"),
        "prior_art_count": len(prior_art) if isinstance(prior_art, list)
        else 0,
        "collision_results_present": bool(col.get("collision_results")),
        "language_rule": ("novelty signals only — legal patentability "
                          "is NEVER asserted (not a patent court)"),
    }


def _attack_state(session: Dict, run_dir: Optional[Path],
                  stage_status: Dict[str, str]) -> Dict:
    env = _envelope(run_dir, "ATTACK") or {}
    ar = env.get("attack_results") or {}
    overall = ar.get("overall") if isinstance(ar, dict) else None
    st = _classify_stage(stage_status.get("ATTACK", ""))
    independence = None
    if isinstance(ar, dict):
        independence = ar.get("independence_mode") or \
            ar.get("independence")
    return {
        "state": ("EXECUTED" if st == "DONE" else
                  "FAILED" if st == "FAILED" else
                  "SKIPPED" if st == "SKIPPED" else
                  "PENDING" if session.get("status") in _RUNNING_STATUSES
                  else "NOT_REACHED"),
        "overall": overall,
        "independence": independence,
    }


def _experiment_state(session: Dict, run_dir: Optional[Path]) -> Dict:
    ke = _envelope(run_dir, "KILLER_EXPERIMENT") or {}
    experiment = ke.get("killer_experiment") or {}
    dex = _read_json(run_dir / "DECISIVE_EXPERIMENT.json") \
        if run_dir else None
    spec = experiment or dex or None
    executed = bool(
        (experiment.get("status") if isinstance(experiment, dict)
         else None) in ("EXECUTED", "COMPLETE", "RUN"))
    # R447 Phase 7 (attack 4 closed at the surface): an experiment
    # exists but its FALSIFICATION field may be absent — the canonical
    # state must NEVER collapse that into a fine-looking experiment.
    # The R444-D contract status (state_integrity) is consulted here so
    # the /state surface carries contract_complete + the Art. LII basis
    # (the engine-level presentation gate in run.py is unchanged).
    contract_status = None
    if spec:
        try:
            from discovery_fabric.engine.state_integrity import \
                falsification_contract_status
            contract_status = falsification_contract_status(spec)
        except Exception:  # noqa: BLE001 — typed surface, never fatal
            contract_status = None
    return {
        "state": ("SPECIFIED_NOT_EXECUTED" if spec and not executed
                  else "EXECUTED" if executed
                  else "PENDING" if session.get("status") in
                  _RUNNING_STATUSES else "NOT_SPECIFIED"),
        "decisive_experiment_present": bool(spec),
        "falsification_contract": contract_status,
        "note": ("the decisive physical experiment is the run's own "
                 "falsification contract (Art. LII); in this machine it "
                 "is specified for survivors and executed only through "
                 "the reality-loop interface"
                 + ("" if not contract_status else
                    "; the contract is COMPLETE only when the "
                    "FALSIFICATION_THRESHOLD answers what outcome kills "
                    "the mechanism — an experiment without that answer "
                    "is a specified experiment, never a complete one")),
    }


def package_terminal_state(session: Dict, run_dir: Optional[Path]) -> Dict:
    """R447 Phase 2 — THE canonical package terminal state.

    The R446-HF Case C defect: the package compiler wrote an honest
    PACKAGE_BUILD_BLOCKED.json (stage + detail) into the run dir, but
    no product route surfaced it — the canonical state said
    NOT_PRODUCED with the reason hidden on disk, and the dossier
    substituted a generic guess. This function is the ONE derivation
    every surface consumes (the /state route, the CIO downloads
    block, the dossier transfer tab — Art. X one authority):

      package_state    READY | BLOCKED | PENDING | NOT_PRODUCED
                       (BLOCKED = the compiler's own blocked record
                       exists; NOT_PRODUCED = no package attempt
                       record at all — distinct epistemic states,
                       Art. LXI)
      blocked_stage    the compiler's typed stage (e.g.
                       QUALITY_GATE_BLOCKED, MODEL_VALIDATION_FAILED,
                       COMPILE_ERROR) or None
      blocked_reason   the record's detail, verbatim (capped for the
                       surface, full text stays in the record)
      release_verdict  from the run's OWN gate records — never
                       guessed: the persisted
                       PACKAGE_QUALITY_GATE_VERDICT.json when present
                       (PASS/BLOCKED + failed gates), else typed
                       NOT_RUN with the honest note
      next_action      a deterministic typed action + one human
                       sentence derived from the same records — the
                       same object feeds the UI without frontend
                       guessing (directive: the canonical state
                       exposes it; the UI consumes it)
    """
    pkg = _package_artifact(run_dir)
    session_pkg = session.get("package") or {}
    complete = bool(pkg.get("complete") or session_pkg.get("complete"))
    blocked_rec = _read_json(run_dir / "PACKAGE_BUILD_BLOCKED.json") \
        if run_dir and run_dir.exists() else None
    gate_verdict = _read_json(
        run_dir / "PACKAGE_QUALITY_GATE_VERDICT.json") \
        if run_dir and run_dir.exists() else None
    running = session.get("status") in _RUNNING_STATUSES

    # --- release verdict: the run's own records, never inferred ------
    # R447 Phase 7 (attack 2 closed at the canonical object): a package
    # whose VISUAL release is blocked (Art. LXXII — HERO_RELEASE_STATE)
    # is never presented as release-ready — the verdict is the typed
    # VISUAL_RELEASE_BLOCKED with the gate's own verdict carried, BEFORE
    # the package quality gate is even consulted (the visual gate
    # outranks: no 3D artifact ships without it).
    hero_release = _read_json(
        run_dir / "MODEL" / "3D" / "HERO_RELEASE_STATE.json") \
        if run_dir and run_dir.exists() else None
    if hero_release and hero_release.get("release_blocked"):
        release_verdict = {
            "verdict": "VISUAL_RELEASE_BLOCKED",
            "visual_gate_verdict": hero_release.get("gate_verdict"),
            "failed_gates": [],
            "warned_gates": [],
            "source": "MODEL/3D/HERO_RELEASE_STATE.json",
            "note": ("the Visual Quality Gate did not pass/run "
                     "(Article LXXII): the package contains zero visual "
                     "artifacts by design and the buyer release stays "
                     "blocked until the visual gate passes"),
        }
    elif gate_verdict:
        release_verdict = {
            "verdict": gate_verdict.get("package_quality"),
            "failed_gates": (gate_verdict.get("failed_gates")
                             or [])[:8],
            "warned_gates": (gate_verdict.get("warned_gates")
                             or [])[:8],
            "source": "PACKAGE_QUALITY_GATE_VERDICT.json",
        }
    elif blocked_rec:
        release_verdict = {
            "verdict": "NOT_RUN",
            "failed_gates": [],
            "warned_gates": [],
            "source": None,
            "note": ("the package was blocked before the quality gate "
                     "ran — no release verdict exists to report (the "
                     "blocked stage is the reason)"),
        }
    else:
        release_verdict = {
            "verdict": None,
            "failed_gates": [],
            "warned_gates": [],
            "source": None,
            "note": ("no persisted package gate verdict for this run — "
                     "unknown stays unknown (Art. XXV)"),
        }

    # --- the blocked reason, verbatim from the record ----------------
    blocked_stage = None
    blocked_reason = None
    if blocked_rec:
        blocked_stage = blocked_rec.get("stage")
        detail = blocked_rec.get("detail")
        if isinstance(detail, str):
            blocked_reason = detail[:600]
        elif detail is not None:
            try:
                blocked_reason = json.dumps(detail, default=str)[:600]
            except Exception:  # noqa: BLE001 — record stands, cap fails
                blocked_reason = str(detail)[:600]

    # --- next_action: deterministic from the same records -------------
    if complete:
        if release_verdict.get("verdict") == "VISUAL_RELEASE_BLOCKED":
            next_action = {
                "action": "RESOLVE_VISUAL_GATE",
                "text": ("the technology package is built and downloadable "
                         "as an engineering evaluation draft, but the "
                         "Visual Quality Gate did not pass/run "
                         "(Article LXXII): the buyer release stays blocked "
                         "until the visual gate passes"),
            }
        else:
            next_action = {
                "action": "DOWNLOAD_PACKAGE",
                "text": ("the technology transfer package is built and "
                         "passed the recorded release gates — download it "
                         "and evaluate the dossier, the experiment plan, "
                         "and the engineering artifacts"),
            }
    elif blocked_rec:
        stage = blocked_stage or "UNKNOWN_STAGE"
        if stage == "QUALITY_GATE_BLOCKED":
            failed = ", ".join(
                str(g) for g in (release_verdict.get("failed_gates")
                                 or [])[:4]) or "recorded gate failures"
            next_action = {
                "action": "RESOLVE_GATE_FAILURES",
                "text": (f"the package quality gate blocked this build "
                         f"({failed}); the run's geometry, evidence and "
                         f"experiment records remain inspectable — no "
                         f"package is presented until the recorded "
                         f"gate failures are resolved"),
            }
        elif stage in ("MODEL_VALIDATION_FAILED", "COMPILE_ERROR"):
            next_action = {
                "action": "INSPECT_QUARANTINE",
                "text": (f"the package compiler blocked this build at "
                         f"{stage}; the quarantined build tree in "
                         f"PACKAGE_QUARANTINE/ carries the evidence — "
                         f"an honest absence, never a partial package"),
            }
        else:
            next_action = {
                "action": "INSPECT_BLOCKED_RECORD",
                "text": (f"the package build was blocked at {stage}; "
                         f"PACKAGE_BUILD_BLOCKED.json in the run "
                         f"directory carries the full record"),
            }
    elif running:
        next_action = {
            "action": "WAIT_FOR_RUN",
            "text": ("the run is still working — the package is built "
                     "automatically when the investigation completes "
                     "with a surviving architecture"),
        }
    else:
        next_action = {
            "action": "NO_PACKAGE_RECORD",
            "text": ("no package record exists for this run — the "
                     "package stage either did not run or its record "
                     "is absent; the run's own stage records are the "
                     "next place to look"),
        }

    # --- the terminal state resolution (the ONE place) -----------------
    if complete:
        package_state = "READY"
        # the promoted ZIP is the current terminal authority; a blocked
        # record from a superseded attempt stays ON DISK (history is
        # evidence, Art. XI) but never surfaces as the CURRENT reason
        blocked_stage = None
        blocked_reason = None
    elif blocked_stage is not None:
        # the compiler's own blocked record: a BLOCKED build is a
        # first-class terminal state, distinct from NOT_PRODUCED (no
        # attempt record) — Art. LXI discipline at the package layer
        package_state = "BLOCKED"
    elif running:
        package_state = "PENDING"
    else:
        package_state = "NOT_PRODUCED"

    return {
        "state": package_state,
        "package_state": package_state,
        "blocked_stage": blocked_stage,
        "blocked_reason": blocked_reason,
        "release_verdict": release_verdict,
        "next_action": next_action,
        "maturity": pkg.get("maturity") or session_pkg.get("maturity"),
        "zip_name": pkg.get("zip_name") or session_pkg.get("zip_name"),
        "package_kind": pkg.get("package_kind") or (
            "TECHNOLOGY_TRANSFER_PACKAGE" if complete else None),
        "package_origin": pkg.get("package_origin"),
    }


def _package_artifact(run_dir: Optional[Path]) -> Dict:
    # R414 fix: package presence from the run's own PACKAGE_REPORT +
    # DOWNLOAD dir (the worker persists it there; the session INDEX may
    # lag — the run dir is the authority, Art. X)
    #
    # R418: the BRIDGE technology package (TECHNOLOGY_PACKAGE_*.zip,
    # recorded in BRIDGE_REPORT.json) counts as an available package —
    # invention existence is separate from package maturity and from
    # buyer-readiness (operator §5). The kind is carried so the surface
    # can label it honestly; a bridge package never claims buyer-release
    # posture (Art. IV).
    pkg = {"complete": False, "maturity": None, "zip_name": None}
    if run_dir and run_dir.exists():
        report = _read_json(run_dir / "PACKAGE_REPORT.json") or {}
        dl = run_dir / "DOWNLOAD"
        zips = sorted(dl.glob("*.zip")) if dl.exists() else []
        if report.get("complete") and zips:
            pkg = {"complete": True,
                   "maturity": report.get("maturity"),
                   "zip_name": zips[0].name,
                   "package_kind": "TECHNOLOGY_TRANSFER_PACKAGE",
                   "package_origin": "BUYER_RELEASE_CHAIN"}
        else:
            br = _read_json(run_dir / "BRIDGE_REPORT.json") or {}
            bp = br.get("package_out") or {}
            zip_name = bp.get("zip_name")
            zp = run_dir / zip_name if zip_name else None
            if zp is None or not zp.exists():
                # R423A Phase 3: both naming generations resolve
                # (historical runs keep their old zip names)
                for pattern in ("TECHNOLOGY_PACKAGE_*.zip",
                                "TECHNOLOGY_TRANSFER_PACKAGE_*.zip"):
                    found = sorted(run_dir.glob(pattern))
                    if found:
                        zp = found[0]
                        break
            if zp is not None and zp.exists():
                pkg = {"complete": True,
                       "maturity": bp.get("package_maturity"),
                       "zip_name": zp.name,
                       "package_kind": "TECHNOLOGY_TRANSFER_PACKAGE",
                       "package_origin": "INVENTION_BRIDGE"}
    return pkg


def _package_state(session: Dict, run_dir: Optional[Path]) -> Dict:
    # R447 Phase 2: the canonical terminal object — the ONE derivation
    # (package_terminal_state) consumed by /state, the CIO downloads
    # block, and the dossier transfer tab; the blocked reason is never
    # hidden on disk again (the R446-HF Case C defect).
    #
    # R423A Phase 3: ONE package — the counsel export is no longer a
    # separate customer surface, so no counsel_package_available
    # field is projected (the technical evidence rides inside the
    # one technology transfer package).
    return package_terminal_state(session, run_dir)


def _failure_state(session: Dict, run_dir: Optional[Path]) -> Dict:
    status = session.get("status") or ""
    manifest = _read_json(run_dir / "run_manifest.json") \
        if run_dir else None
    failed_stages = (manifest or {}).get("failed_stages") or {}
    infra = status in _BLOCKED_STATUSES or status.startswith("ERROR")
    return {
        "state": ("INFRASTRUCTURE" if infra else
                  "STAGE_FAILURES" if failed_stages else
                  "NONE" if status == "COMPLETE" else "PENDING"),
        "error": session.get("error"),
        "failed_stages": {k: (v.get("status") if isinstance(v, dict)
                              else str(v))[:60]
                          for k, v in failed_stages.items()},
        "machine_status": status,
        "note": ("infrastructure failures are never scientific "
                 "rejections (Art. LXI) — RUN_BLOCKED exists so the "
                 "product can say THIS honestly"),
    }


def phase_progression(session: Dict, run_dir: Optional[Path],
                      stage_status: Dict[str, str]) -> List[Dict]:
    """The directive §5 UI phases (R416 Phase J wording: the machine
    WORKS the problem — 'Inventing architecture 1' -> 'Challenging
    architecture 1' -> ['Developing architecture 2' -> 'Testing
    architecture 2' -> ...] -> 'Preparing technology package'), each
    mapped to REAL backend stages or lineage records; a phase is DONE
    only when its stages are done, IN_PROGRESS while any runs, FAILED
    if any failed. Never fabricated progress."""
    running = session.get("status") in _RUNNING_STATUSES
    out: List[Dict] = []
    reached_any = False
    # the INVESTIGATING phase is the problem build: DONE when the run
    # dir carries a problem.json (the build's own artifact), never
    # while it is still being written
    problem_built = bool(run_dir and (run_dir / "problem.json").exists())
    for phase_id, label, stages in PHASES:
        if phase_id == "INVESTIGATING":
            phase_state = ("DONE" if problem_built else
                           "IN_PROGRESS" if running else "NOT_STARTED")
            out.append({"phase": phase_id, "label": label,
                        "state": phase_state, "stages": {}})
            if problem_built:
                reached_any = True
            continue
        states = [_classify_stage(stage_status.get(s, ""))
                  for s in stages if s in stage_status]
        phase_state = "NOT_STARTED"
        if states:
            if any(s == "FAILED" for s in states):
                phase_state = "FAILED"
            elif all(s == "DONE" for s in states):
                phase_state = "DONE"
                reached_any = True
            elif any(s == "DONE" for s in states):
                phase_state = "IN_PROGRESS"
                reached_any = True
            else:
                phase_state = "IN_PROGRESS" if reached_any \
                    else "NOT_STARTED"
        out.append({"phase": phase_id, "label": label,
                    "state": phase_state,
                    "stages": {s: stage_status.get(s)
                               for s in stages if s in stage_status}})

    # ---- R416: the evolution generations extend the progression ------
    # Each generation beyond the first appends 'Developing architecture
    # N' -> 'Testing architecture N' (Phase J wording), states derived
    # from the lineage's own records — never fabricated.
    if run_dir and run_dir.exists():
        lineage = _read_json(run_dir / "INVENTION_LINEAGE.json")
        for g in (lineage or {}).get("generations") or []:
            if not isinstance(g, dict):
                continue
            gen_n = g.get("gen")
            if not gen_n or gen_n == 1:
                continue
            ch = g.get("challenge") or {}
            if ch:
                out.append({
                    "phase": f"TESTING_{gen_n}",
                    "label": f"Testing architecture {gen_n}",
                    "state": ("DONE" if ch.get("survived") else
                              "FAILED" if ch.get("killed") else
                              "IN_PROGRESS" if running else "DONE"),
                    "stages": {f"EVOLUTION_GEN_{gen_n}":
                               g.get("state") or "UNKNOWN"},
                    "generation": gen_n})
        # a live evolution generation shows as Developing in progress
        live = _evolution_live_phase(session, run_dir)
        if live:
            out.append({
                "phase": f"DEVELOPING_{live['current_gen']}",
                "label": live["label"],
                "state": "IN_PROGRESS",
                "stages": {},
                "generation": live["current_gen"],
                "subline": live["subline"]})
    return out


def _lineage_challenge_verdict(run_dir: Optional[Path]) -> Optional[Dict[str, Any]]:
    """R452 (external audit B1): the CURRENT invention's own challenge
    verdict, read from the run's lineage records (the run dir is the
    authority, Art. X — this PROJECTS, never re-derives).

    The measured defect: the projection read final_status only and
    promoted a lineage whose generations were ALL killed (7/7
    production runs: EVOLUTION_GEN_1.state=INVENTION_REJECTED,
    challenge.killed=true, yet final_status positive and the product
    surface said found_something=true).

    Returns {current_killed, current_kill_genuine, any_kill_genuine,
    current_evidence_verified, survivor_reached, n_kills, kill_reasons}.
    None when no lineage exists (never fabricated).
    """
    lineage = _read_json(Path(run_dir) / "INVENTION_LINEAGE.json") \
        if run_dir else None
    if not lineage:
        return None
    gens = [g for g in (lineage.get("generations") or [])
            if isinstance(g, dict)]
    if not gens:
        return None
    current_gen = (lineage.get("current_invention") or {}).get("gen")
    cur = None
    for g in gens:
        if g.get("gen") == current_gen:
            cur = g
    cur = cur or gens[-1]
    ch = cur.get("challenge") or {}

    def _genuine(g: Dict[str, Any]) -> bool:
        """A kill is a GENUINE scientific verdict unless its recorded
        reason carries the capability-failure signature (Art. LXI)."""
        c = g.get("challenge") or {}
        if not c.get("killed"):
            return False
        reason = str(c.get("kill_reason") or "")
        return _CAPABILITY_KILL_SIGNATURE not in reason

    kill_reasons = [str((g.get("challenge") or {}).get("kill_reason") or "")
                    for g in gens
                    if (g.get("challenge") or {}).get("killed")]
    return {
        "current_killed": bool(ch.get("killed")),
        "current_kill_genuine": _genuine(cur),
        "any_kill_genuine": any(_genuine(g) for g in gens),
        "current_evidence_verified": bool(cur.get("evidence_verified"))
        if "evidence_verified" in cur else None,
        "survivor_reached": bool(lineage.get("survivor_reached")),
        "n_kills": len(kill_reasons),
        "kill_reasons": kill_reasons[:5],
    }


def terminal_outcome(session: Dict, run_dir: Optional[Path] = None) -> Dict:
    """The directive §18 four-state outcome + the recorded BASIS for it.
    PENDING while the run is live. Derived from recorded fields only.

    R452 (external audit B1/AT-7): for the POSITIVE final statuses the
    lineage's own challenge verdict is AUTHORITATIVE — the projection
    never reads final_status alone:
      * the current invention killed by a GENUINE adversarial verdict,
        or genuine kills in the lineage with no VERIFIED survivor
        replacing them  -> OUTCOME_KILLED_BY_CHALLENGE, rejected
        (the R452 authority decision: a lineage whose kills were never
        answered by a verified survivor is not "found something";
        a future run whose later generation VERIFIES and survives is
        found_something=true — the learning loop stays expressible);
      * a "survivor" whose evidence was never verified (a capability
        failure promoted it)             -> OUTCOME_UNDER_DEVELOPMENT,
        found_something=false (Art. XXVIII: the model -> validated
        transition requires evidence; Art. LXI: capability failure is
        never a rejection either — the basis names it);
      * no survivor at all               -> OUTCOME_UNDER_DEVELOPMENT
        (today's wording already says none survived).
    """
    status = session.get("status") or ""
    final = (session.get("final_status") or "").upper()
    pkg = session.get("package") or {}

    if status in _RUNNING_STATUSES:
        return {"outcome": OUTCOME_PENDING, "basis":
                f"machine status {status or 'PENDING'} — run in flight"}

    if status == "COMPLETE" and final in (
            "AUTOMATED_INVENTION_CANDIDATE", "EVOLVED_INVENTION_CANDIDATE",
            "INVENTION_REQUIRES_EXPERIMENT", "INVENTION_UNDER_DEVELOPMENT"):
        # R452: the lineage's challenge verdict is authoritative for the
        # positive statuses (the audit measured the promotion defect 7/7)
        verdict = _lineage_challenge_verdict(run_dir)
        if verdict is not None:
            found = (verdict["survivor_reached"]
                     and not verdict["current_killed"]
                     and verdict["current_evidence_verified"] is not False)
            if verdict["current_kill_genuine"] or (
                    verdict["any_kill_genuine"] and not found):
                reasons = "; ".join(verdict["kill_reasons"][:2]) or \
                    "no reason recorded"
                return {"outcome": OUTCOME_KILLED_BY_CHALLENGE,
                        "invention_found": False,
                        "invention_rejected": True,
                        "basis": (f"the machine's own challenge KILLED the "
                                  f"invention ({verdict['n_kills']} kill(s) "
                                  f"in the lineage; reasons: {reasons}) — "
                                  "a killed invention is never presented "
                                  "as found (external audit B1/AT-7)")}
            if not found:
                if verdict["survivor_reached"] and \
                        verdict["current_evidence_verified"] is False:
                    return {"outcome": OUTCOME_UNDER_DEVELOPMENT,
                            "invention_found": False,
                            "invention_rejected": False,
                            "basis": ("a generation passed the attack "
                                      "gauntlet but its evidence was "
                                      "never verified (a model "
                                      "capability failure promoted it) — "
                                      "presented as under development, "
                                      "never as a verified candidate "
                                      "(Art. XXVIII/LXI)")}
                return {"outcome": OUTCOME_UNDER_DEVELOPMENT,
                        "invention_found": False,
                        "invention_rejected": False,
                        "basis": (f"final_status={final} but the lineage "
                                  f"records {verdict['n_kills']} challenge "
                                  "kill(s) and no verified survivor — "
                                  "nothing is presented as found")}

    if status == "COMPLETE" and \
            final == "AUTOMATED_INVENTION_CANDIDATE":
        pkg_complete = bool(pkg.get("complete"))
        if not pkg_complete and run_dir and run_dir.exists():
            report = _read_json(run_dir / "PACKAGE_REPORT.json") or {}
            zips = sorted((run_dir / "DOWNLOAD").glob("*.zip")) \
                if (run_dir / "DOWNLOAD").exists() else []
            pkg_complete = bool(report.get("complete") and zips)
        if pkg_complete:
            return {"outcome": OUTCOME_SURVIVED,
                    "basis": ("final_status="
                              "AUTOMATED_INVENTION_CANDIDATE and the "
                              "technology package was built (recorded "
                              "package.complete=true)")}
        return {"outcome": OUTCOME_REQUIRES_EXPERIMENT,
                "basis": ("final_status="
                          "AUTOMATED_INVENTION_CANDIDATE but no "
                          "technology package on this run; the decisive "
                          "physical experiment is specified, not "
                          "executed (recorded fields: package.complete="
                          "false)")}
    if status == "COMPLETE" and final == "INVENTION_REQUIRES_EXPERIMENT":
        # R443 / TSC-008: the BASELINE FALLBACK survivor — the synthesis
        # path failed, the mandatory baseline architecture was created,
        # challenged, and survived. The idea is presented honestly: it
        # requires its decisive experiment. Never rejected, never
        # dressed as EVOLVED (Art. XXVIII).
        pkg_complete = bool(pkg.get("complete"))
        if not pkg_complete and run_dir and run_dir.exists():
            report = _read_json(run_dir / "PACKAGE_REPORT.json") or {}
            zips = sorted((run_dir / "DOWNLOAD").glob("*.zip")) \
                if (run_dir / "DOWNLOAD").exists() else []
            pkg_complete = bool(report.get("complete") and zips)
        if pkg_complete:
            return {"outcome": OUTCOME_REQUIRES_EXPERIMENT,
                    "basis": ("final_status="
                              "INVENTION_REQUIRES_EXPERIMENT — the "
                              "baseline fallback generation survived "
                              "the challenge gauntlet and a technology "
                              "package was built (0 evolution "
                              "generations; no evolution claimed — the "
                              "honest fallback presentation, TSC-008)")}
        return {"outcome": OUTCOME_REQUIRES_EXPERIMENT,
                "basis": ("final_status="
                          "INVENTION_REQUIRES_EXPERIMENT — the baseline "
                          "fallback generation survived the challenge "
                          "gauntlet; the decisive physical experiment "
                          "is specified, not executed (0 evolution "
                          "generations; no evolution claimed — the "
                          "honest fallback presentation, TSC-008)")}
    if status == "COMPLETE" and final == "EVOLVED_INVENTION_CANDIDATE":
        # R416: an evolution generation survived the re-evaluation
        # gauntlet. Package presence decides SURVIVED vs
        # REQUIRES_EXPERIMENT — the maturity label rides on the
        # generations projection, never asserted here.
        pkg_complete = bool(pkg.get("complete"))
        if not pkg_complete and run_dir and run_dir.exists():
            report = _read_json(run_dir / "PACKAGE_REPORT.json") or {}
            zips = sorted((run_dir / "DOWNLOAD").glob("*.zip")) \
                if (run_dir / "DOWNLOAD").exists() else []
            pkg_complete = bool(report.get("complete") and zips)
        if pkg_complete:
            return {"outcome": OUTCOME_SURVIVED,
                    "basis": ("final_status="
                              "EVOLVED_INVENTION_CANDIDATE and the "
                              "technology package was built (recorded "
                              "package.complete=true)")}
        return {"outcome": OUTCOME_REQUIRES_EXPERIMENT,
                "basis": ("final_status="
                          "EVOLVED_INVENTION_CANDIDATE; the decisive "
                          "physical experiment is specified, not "
                          "executed (recorded fields: package.complete="
                          "false)")}
    if status == "COMPLETE" and final == "INVENTION_UNDER_DEVELOPMENT":
        # R416: the evolution loop explored architectures and stopped
        # honestly (budget / information-gain / transport). The CURRENT
        # invention is presented with its true maturity — the lineage
        # projection carries the generations, the challenge history and
        # the stop reason. Never a dead-end sentence.
        n = None
        cur = None
        if run_dir and run_dir.exists():
            lineage = _read_json(run_dir / "INVENTION_LINEAGE.json") or {}
            n = lineage.get("n_generations")
            cur = lineage.get("current_invention") or {}
        return {"outcome": OUTCOME_UNDER_DEVELOPMENT,
                "basis": (f"final_status=INVENTION_UNDER_DEVELOPMENT — "
                          f"{n or 'multiple'} architecture generations "
                          f"explored; current invention GEN "
                          f"{(cur or {}).get('gen')} at maturity "
                          f"{(cur or {}).get('maturity')}; stop reason "
                          f"recorded on the lineage")}
    if status == "COMPLETE" and final in ("REJECTED",
                                          "MECHANISM_GENERATION_FAILED"):
        # legacy/pre-evolution records: an architecture WAS generated on
        # R416 runs; for pre-R416 records the exploration is still
        # presented as development state with the recorded basis — the
        # product never renders the banned dead-end sentence
        return {"outcome": OUTCOME_UNDER_DEVELOPMENT,
                "basis": f"final_status={final} — the recorded "
                         f"challenge outcome; the invention lineage "
                         f"(when present) carries the generations and "
                         f"their maturity"}
    if status == "COMPLETE" and final == "MALFORMED_OR_FALSE_PREMISE":
        return {"outcome": OUTCOME_FALSE_PREMISE,
                "basis": ("final_status=MALFORMED_OR_FALSE_PREMISE — "
                          "the problem as stated cannot physically "
                          "occur; reformulating the premise is the fix "
                          "(checked BEFORE inventing; nothing was "
                          "synthesized)")}
    if status == "COMPLETE":
        return {"outcome": OUTCOME_RUN_BLOCKED,
                "basis": ("terminal without a recorded verdict "
                          "(final_status empty/UNKNOWN) — a scientific "
                          "conclusion was not reached")}
    # INTERRUPTED / ERROR_* / RUN_BLOCKED_TRANSPORT : infrastructure-class
    # terminations (R415: RUN_BLOCKED_TRANSPORT is the P0 directive's §8
    # state — the machine genuinely exhausted its routes; the problem is
    # saved and resumable, NEVER a scientific rejection)
    return {"outcome": OUTCOME_RUN_BLOCKED,
            "basis": f"machine status {status} — infrastructure, "
                     f"never a scientific rejection (Art. LXI)"}


# ---------------------------------------------------------------------------
# R416: the invention generations projection (INVENTION_LINEAGE.json is
# the authority; this only PROJECTS it — Art. X)
# ---------------------------------------------------------------------------

def _gen_model_available(run_dir: Optional[Path], gen: int) -> bool:
    if not run_dir or not gen:
        return False
    return (run_dir / "MODEL" / f"model-{int(gen):03d}.glb").exists()


def generations_projection(session: Dict,
                           run_dir: Optional[Path]) -> Optional[Dict]:
    """The lineage generations for the UI: INVENTION 01, 02, ... with
    state, maturity, what changed, challenge history, and per-gen
    geometry availability. None when no lineage was recorded (standard
    single-generation runs still show the GEN-1 phases)."""
    if not run_dir or not run_dir.exists():
        return None
    lineage = _read_json(run_dir / "INVENTION_LINEAGE.json")
    if not lineage or not lineage.get("generations"):
        return None
    gens = []
    for g in lineage.get("generations") or []:
        if not isinstance(g, dict):
            continue
        gen_n = g.get("gen")
        ch = g.get("challenge") or {}
        cd = g.get("causal_delta") or {}
        gens.append({
            "gen": gen_n,
            "label": f"INVENTION {int(gen_n):02d}" if gen_n else None,
            "invention_id": g.get("invention_id"),
            "parent_id": g.get("parent_id"),
            "origin": g.get("origin"),
            "state": g.get("state"),
            "maturity": g.get("maturity"),
            "architecture": {
                "mechanism": (g.get("architecture") or {}).get(
                    "mechanism"),
                "intervention": (g.get("architecture") or {}).get(
                    "intervention"),
                "expected_effect": (g.get("architecture") or {}).get(
                    "expected_effect"),
                "falsification_test": (g.get("architecture") or {}).get(
                    "falsification_test"),
            },
            "what_changed": g.get("change_delta"),
            "reason_for_change": g.get("reason_for_change"),
            "causal_delta": {
                "causal_change": cd.get("causal_change"),
                "new_capability": cd.get("new_capability"),
                "new_interaction": cd.get("new_interaction"),
                "new_operating_regime": cd.get("new_operating_regime"),
                "predicted_effect": cd.get("predicted_effect"),
                "frontier_capability": cd.get("frontier_capability"),
                "thirty_year_engine": cd.get("thirty_year_engine") or None,
                "diagnosed_cause": cd.get("diagnosed_cause"),
            } if cd else None,
            "challenge": {
                "killed": ch.get("killed"),
                "kill_stage": ch.get("kill_stage"),
                "kill_reason": ch.get("kill_reason"),
                "attack_overall": ch.get("attack_overall"),
                "independent_attack": ch.get("independent_attack"),
                "physics_lifecycle": ch.get("physics_lifecycle"),
                "survived": ch.get("survived"),
                "evidence_verified": ch.get("evidence_verified"),
                # R417 attacker-calibration gate: the measured-
                # unselective independent attacker's KILL is escalated
                # (objection preserved verbatim, never executed) — the
                # product surface shows exactly what happened
                "escalated_objection": ch.get("escalated_objection"),
            },
            "diagnosis": {
                "cause": (g.get("diagnosis") or {}).get("cause"),
                "basis": ((g.get("diagnosis") or {}).get("basis")
                          or [])[:2],
            } if g.get("diagnosis") else None,
            "fresh_evidence": {
                "n_items": (g.get("fresh_evidence") or {}).get("n_items"),
                "query": (g.get("fresh_evidence") or {}).get("query"),
                "status": (g.get("fresh_evidence") or {}).get("status"),
                "snapshot_version": (g.get("fresh_evidence") or {}).get(
                    "snapshot_version"),
            } if g.get("fresh_evidence") else None,
            "model_available": _gen_model_available(run_dir, gen_n or 0),
            "stop_note": g.get("stop_note"),
        })
    return {
        "generations": gens,
        "n_generations": lineage.get("n_generations") or len(gens),
        "n_evolution_generations": lineage.get(
            "n_evolution_generations"),
        "current_invention": lineage.get("current_invention"),
        "survivor_reached": lineage.get("survivor_reached"),
        "survivor_gen": lineage.get("survivor_gen"),
        "stop_reason": lineage.get("stop_reason"),
        "status": lineage.get("status"),   # DISABLED / ERROR states
        "honesty_contract": lineage.get("honesty_contract"),
    }


def _evolution_live_phase(session: Dict,
                          run_dir: Optional[Path]) -> Optional[Dict]:
    """The live evolution state while the run works: which generation
    is being developed/tested right now, derived from persisted
    per-generation records (EVOLUTION_GEN_N.json presence + the last
    record's state). Absent when no evolution is in flight."""
    if not run_dir or not run_dir.exists():
        return None
    if session.get("status") not in _RUNNING_STATUSES:
        return None
    # the engine persists EVOLUTION_GEN_N.json as each generation
    # completes; the LIVE generation is one beyond the last record
    n = 0
    for i in range(1, 9):
        if (run_dir / f"EVOLUTION_GEN_{i}.json").exists():
            n = i
        else:
            break
    if n == 0:
        # no generation record yet: the run is still in the standard
        # stages — the evolution has not started (not a fake phase)
        return None
    return {
        "current_gen": n + 1,
        "phase": "DEVELOPING",
        "label": f"Developing architecture {n + 1}",
        "subline": ("Generation " + str(n + 1) +
                    " · Frontier transfer in progress"),
        "note": ("the causal evolution is running: diagnose -> causal "
                 "change -> re-evaluate; every step lands in the run "
                 "directory as it happens"),
    }


def canonical_run_state(session: Dict) -> Dict[str, Any]:
    """The directive §4 DiscoveryRun object. Backend-derived from the
    session record + run-dir artifacts; the frontend READS this and
    never re-derives states client-side."""
    run_dir = Path(session["run_dir"]) if session.get("run_dir") else None
    # R446-C1 Task 4: the completion reconciliation — a session record
    # that says COMPLETE is only user-visible COMPLETE when the run
    # dir's canonical marker (run_manifest.json) proves it. Historical
    # session records written before the marker authority (or restored
    # from durable snapshots of that era) reconcile HERE, read-only:
    # the projection reports the honest INTERRUPTED state with the
    # reconciliation basis; the session record itself is never mutated
    # during observation (Art. IX). No state may become user-visible
    # COMPLETE until the marker proves the relevant stages completed.
    projected_status = session.get("status")
    completion_reconciliation = None
    if projected_status == "COMPLETE":
        from . import completion as _completion
        marker = _completion.completion_marker_state(run_dir)
        if marker["completion"] != _completion.COMPLETE_MARKED:
            projected_status = "INTERRUPTED"
            completion_reconciliation = {
                "session_record_says": "COMPLETE",
                "projected_status": "INTERRUPTED",
                "authority": "run_manifest.json (the canonical "
                             "completion marker, R445-C)",
                "basis": marker.get("reason", ""),
                "note": ("the session record predates the completion "
                         "authority or was restored from a durable "
                         "snapshot of that era; the run dir's own "
                         "marker is the truth (Art. X/XXV)"),
            }
    reconciled = dict(session)
    if completion_reconciliation:
        reconciled["status"] = projected_status
    stage_status = _stage_status_map(session, run_dir)
    outcome = terminal_outcome(reconciled, run_dir)
    out = {
        "run_id": session.get("session_id"),
        "user_problem": session.get("user_text"),
        "created_at": session.get("created_at"),
        "status": projected_status,
        "model_route": _model_route(session, run_dir),
        "retrieval_route": _evidence_state(session, run_dir).get(
            "retrieval_route"),
        "evidence_state": _evidence_state(session, run_dir),
        "mechanism_state": _mechanism_state(session, run_dir,
                                            stage_status),
        "invention_state": _invention_state(session, run_dir),
        "physics_state": _physics_state(session, run_dir, stage_status),
        "novelty_state": _novelty_state(session, run_dir),
        "attack_state": _attack_state(session, run_dir, stage_status),
        "experiment_state": _experiment_state(session, run_dir),
        "package_state": _package_state(session, run_dir),
        "provenance": {
            "run_dir": session.get("run_dir"),
            "origin": session.get("origin"),
            "engine_authority": ("the run directory's persisted "
                                 "artifacts are authoritative; this "
                                 "object is their projection (Art. X)"),
        },
        "failure_state": _failure_state(session, run_dir),
        "outcome": outcome["outcome"],
        "outcome_label": OUTCOME_LABELS[outcome["outcome"]],
        "outcome_basis": outcome["basis"],
        "phase_progression": phase_progression(session, run_dir,
                                               stage_status),
        # R416: the invention generations (INVENTION 01, 02, ...) with
        # lineage, causal deltas, maturity and per-gen geometry — the
        # UI's generation navigation renders THIS, never client-side
        # inference. None for runs without a lineage record.
        "generations": generations_projection(session, run_dir),
        "evolution_state": _evolution_live_phase(session, run_dir),
        "schema_version": "1.1.0",
    }
    if completion_reconciliation:
        out["completion_reconciliation"] = completion_reconciliation
    return out
