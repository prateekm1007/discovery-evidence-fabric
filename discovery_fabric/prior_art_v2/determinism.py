"""discovery_fabric/prior_art_v2/determinism.py — R396 Phase C (P6):
the run-record determinism block.

The R396 directive (P6) requires the RUN RECORD ITSELF to carry, per
run: verdict, model/relevance version, relevant-evidence-set identity,
and — across identical replays — a variance/difference summary and a
DETERMINISTIC / NON_DETERMINISTIC classification.

Mechanism (pure, LLM-free, deterministic):
  fingerprint     sha256 over (problem device/failure/mode + candidate
                  mechanism profile terms) — the "identical problem"
                  identity.
  evidence_set    sha256 over the sorted per-family adjudicated-text
  identity        custody hashes + family ids + relevance model version
                  (the "relevant evidence set" identity).
  replay ledger   append-only JSONL; every collision appends one entry;
                  the block compares THIS entry with every PRIOR entry
                  carrying the same fingerprint.
  classification  BASELINE_RUN (first occurrence — no comparison basis,
                  honest), DETERMINISTIC (verdict + evidence-set
                  identity + model version all equal on every replay),
                  NON_DETERMINISTIC (any divergence — flagged, never
                  silently resolved; Art. XXI/XXV).

The ledger is RUNTIME state (ENGINE_RUNTIME/, gitignored); tests
redirect it via the autouse conftest guard (the e11 contamination
class). Divergence between search RESULTS (providers return different
records) is reported as variance in the evidence-set identity but only
classifies NON_DETERMINISTIC when the VERDICT or the RELEVANT SET
CHANGES — result-count noise that does not move the verdict stays
deterministic-with-disclosed-delta.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
LEDGER_PATH = Path(
    os.environ.get("COLLISION_REPLAY_LEDGER")
    or REPO_ROOT / "ENGINE_RUNTIME" / "collision_replay_ledger.jsonl")

DETERMINISM_MODEL_VERSION = "determinism/1.0.0"


def _sha(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False,
                   default=str).encode("utf-8")).hexdigest()


def problem_fingerprint(problem: Dict[str, Any],
                        mechanism_map: Dict[str, Any]) -> str:
    """The 'identical problem' identity: problem core + candidate
    mechanism core. Deliberately excludes timestamps, run ids, and any
    volatile field (a different problem OR a different candidate is a
    different fingerprint — never a false determinism claim)."""
    core = {
        "device": str(problem.get("device") or ""),
        "failure": str(problem.get("failure") or ""),
        "failure_mode": str(problem.get("failure_mode") or ""),
        "mechanism": str(mechanism_map.get("mechanism") or ""),
        "intervention": str(mechanism_map.get("intervention") or ""),
        "expected_effect": str(mechanism_map.get("expected_effect") or ""),
    }
    return _sha(core)


def evidence_set_identity(resolution: Dict[str, Any]) -> str:
    """Identity of the RELEVANT evidence set the verdict stands on: the
    per-family custody hashes + family ids, bound to the relevance
    model version that judged them."""
    per_family = resolution.get("per_family") or []
    payload = {
        "families": sorted(
            (str(f.get("family_id") or ""),
             str(f.get("adjudicated_text_sha256") or ""))
            for f in per_family),
        "n_families": len(per_family),
        "relevance_model_version":
            str(resolution.get("relevance_model_version") or ""),
        "search_errors": sorted(
            str(e) for e in (resolution.get("search_errors") or [])[:12]),
    }
    return _sha(payload)


def _read_ledger(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not path.exists():
        return out
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
    except Exception:  # noqa: BLE001 — a corrupt ledger is disclosed
        return [{"_corrupt": True}]
    return out


def record_and_compare(fingerprint: str,
                       verdict: str,
                       relevance_model_version: str,
                       evset_identity: str,
                       run_id: str = "",
                       ledger_path: Optional[Path] = None) -> Dict[str, Any]:
    """Append this run to the replay ledger and build the determinism
    block by comparing with every prior same-fingerprint entry."""
    path = Path(ledger_path) if ledger_path else LEDGER_PATH
    prior = [e for e in _read_ledger(path)
             if not e.get("_corrupt")
             and e.get("fingerprint") == fingerprint]
    entry = {
        "fingerprint": fingerprint,
        "run_id": run_id,
        "verdict": verdict,
        "relevance_model_version": relevance_model_version,
        "evidence_set_identity": evset_identity,
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
    except Exception as exc:  # noqa: BLE001 — disclosed, never fatal
        return {
            "model_version": DETERMINISM_MODEL_VERSION,
            "classification": "LEDGER_UNAVAILABLE",
            "error": f"{type(exc).__name__}: {exc}"[:200],
            "verdict": verdict,
            "relevance_model_version": relevance_model_version,
            "evidence_set_identity": evset_identity,
            "n_prior_replays": len(prior),
            "note": ("the replay ledger could not be written; the "
                     "determinism comparison is honest about its own "
                     "unavailability (Art. XXV)"),
        }

    runs = [dict(p, position=i) for i, p in enumerate(prior)] + [entry]
    verdicts = [str(r.get("verdict")) for r in runs]
    evsets = [str(r.get("evidence_set_identity")) for r in runs]
    versions = [str(r.get("relevance_model_version")) for r in runs]

    differences: List[Dict[str, Any]] = []
    if prior:
        if len(set(verdicts)) > 1:
            differences.append({
                "field": "verdict", "values": verdicts,
                "basis": "identical problem produced different verdicts"})
        if len(set(evsets)) > 1:
            differences.append({
                "field": "evidence_set_identity", "values": evsets,
                "basis": ("the relevant evidence set (per-family custody "
                          "hashes) changed between identical replays")})
        if len(set(versions)) > 1:
            differences.append({
                "field": "relevance_model_version", "values": versions,
                "basis": "the relevance model changed between replays"})

    if not prior:
        classification = "BASELINE_RUN"
    elif not differences:
        classification = "DETERMINISTIC"
    else:
        classification = "NON_DETERMINISTIC"

    return {
        "model_version": DETERMINISM_MODEL_VERSION,
        "classification": classification,
        "verdict": verdict,
        "relevance_model_version": relevance_model_version,
        "evidence_set_identity": evset_identity,
        "problem_fingerprint": fingerprint,
        "n_prior_replays": len(prior),
        "variance_summary": {
            "n_runs_compared": len(runs),
            "verdicts": verdicts,
            "distinct_verdicts": sorted(set(verdicts)),
            "distinct_evidence_set_identities": sorted(set(evsets)),
            "differences": differences,
        } if prior else None,
        "rule": ("identical problem + identical relevant evidence set + "
                 "identical relevance model must yield the identical "
                 "verdict; any divergence is classified NON_DETERMINISTIC "
                 "and disclosed, never silently resolved (R396 P6 / "
                 "R394 s3)"),
    }
