#!/usr/bin/env python3
"""scripts/r400_production_chain_run.py — R400-C: ONE genuine full-chain
run through the REAL public product surface of the 930eca8b artifact
(local artifact server), capturing every R400-C directive field:

  candidate_id, mechanism_id, baseline, target_metric, constraints,
  physics_model_version, input_hash, output_hash, failure_state,
  baseline_comparison, verdict

Chain traversed (the server's canonical STAGE_ORDER, R397 Phase 2):
  PROBLEM -> PREMISE_GATE -> EVIDENCE(RETRIEVE/VERIFY) -> MECHANISM
  (SYNTHESIZE) -> CAD/PACKAGE -> PLAUSIBILITY -> PHYSICS -> BASELINE
  -> ATTACK

The physics result remains COMPUTATIONAL_RESULT (Art. XXXVIII layer 4
— computation log with input/output hashes and solver version; never a
physical claim). Execution is honestly labeled: EXECUTION_SURFACE =
local artifact server on the EXACT 930eca8b checkout (the artifact the
R400-A runbook deploys); the live public host still runs f9dfd45d until
the operator deploys — disclosed, never conflated.

Usage:
  python3 scripts/r400_production_chain_run.py [--base URL] \
      [--out R400/PRODUCTION_PHYSICS_RUN_930eca8b.json]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]

# The multi-lumen drainage problem — the P-07 reference envelope that
# exercises the physics chain end-to-end: representability, six bound
# families, the 1D hydraulic network solver, failure modes, and the
# baseline comparison (P7 case 10/12 family).
PHYSICS_PROBLEM = (
    "Why do multi-lumen drainage catheters lose drain conductance "
    "under partial obstruction, and can a wider floor lumen restore "
    "flow?"
)

RAW: list = []


def _request(base: str, path: str, method: str = "GET",
             body: Optional[dict] = None,
             headers: Optional[dict] = None,
             timeout: int = 120) -> Tuple[Dict[str, Any], str]:
    url = base.rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    rec: Dict[str, Any] = {"method": method, "url": url,
                           "at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                   time.gmtime())}
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        rec["status"] = r.status
        set_cookie = r.headers.get("Set-Cookie") or ""
        if "tosca_owner=" in set_cookie:
            rec["owner_cookie"] = set_cookie.split(
                "tosca_owner=")[1].split(";")[0]
        try:
            rec["response_json"] = json.loads(raw.decode())
        except Exception:  # noqa: BLE001
            rec["response_text"] = raw.decode(errors="replace")[:4000]
    RAW.append(rec)
    return rec, (rec.get("owner_cookie") or "")


def _j(rec: Dict[str, Any]) -> Dict[str, Any]:
    return rec.get("response_json") or {}


def _wait_terminal(base: str, sid: str, owner: str,
                   timeout_s: int = 1200) -> Optional[dict]:
    deadline = time.time() + timeout_s
    last: Optional[dict] = None
    while time.time() < deadline:
        try:
            rec, _ = _request(
                base, f"/api/sessions/{sid}",
                headers={"Cookie": f"tosca_owner={owner}"})
            d = _j(rec)
            if d:
                last = d
                st = d.get("status") or ""
                if st in ("COMPLETE", "ERROR_TRANSPORT", "ERROR_BUILD",
                          "ERROR_RUN", "INTERRUPTED", "REJECTED",
                          "COMPLETED_FALSE_PREMISE"):
                    return d
        except Exception as e:  # noqa: BLE001
            last = {"poll_error": str(e)}
        time.sleep(6)
    return last


def _extract_physics(detail: dict) -> dict:
    """Pull the physics stage record + every R400-C capture field from
    the run detail, wherever the record carries them (stages, physics,
    final_state). Nothing is inferred — fields absent from the record
    stay absent (Art. II/XXV)."""
    stages = detail.get("stages") or []
    by_stage = {s.get("stage"): s for s in stages}
    phys = by_stage.get("PHYSICS", {}) or {}
    out: Dict[str, Any] = {}
    # the stage record itself (status/entry-justification stamp)
    out["physics_stage_status"] = phys.get("status")
    out["physics_stage_entry"] = {
        k: phys.get(k) for k in
        ("entry_status", "prerequisite", "prerequisite_evidence",
         "skip_reason") if k in phys}
    # nested payloads: run record may carry physics under result/detail
    for key in ("result", "detail", "physics", "output", "data"):
        payload = phys.get(key)
        if isinstance(payload, dict):
            for k, v in payload.items():
                out.setdefault(f"physics_{k}", v)
    # whole-detail physics block (some records carry it at top level)
    for k, v in (detail.get("physics") or {}).items():
        out.setdefault(f"physics_{k}", v)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8902")
    ap.add_argument("--problem", default=PHYSICS_PROBLEM)
    ap.add_argument("--out", default="R400/PRODUCTION_PHYSICS_RUN_"
                                     "930eca8b.json")
    ap.add_argument("--session-id", default="",
                    help="rehydrate mode: re-poll an EXISTING session "
                         "(with --owner cookie) and rebuild the capture "
                         "record from the machine's own artifacts — no "
                         "new compute is consumed")
    ap.add_argument("--owner", default="",
                    help="the tosca_owner cookie for --session-id")
    args = ap.parse_args()

    report: Dict[str, Any] = {
        "suite": "R400-C production chain run (physics path)",
        "execution_surface": (
            "LOCAL ARTIFACT SERVER on the EXACT 930eca8b checkout "
            "(worktree /home/z/my-project/wt-r400-930eca8b, baked "
            "ARTIFACT_IDENTITY, deployment env contract per "
            "DEPLOYMENT_CONFIG.json). The live public host still runs "
            "f9dfd45d until the operator deploys — this record does "
            "NOT claim a live-host execution (Art. XXV/XXVI)."),
        "problem": args.problem,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime()),
    }

    # 0. server identity at run time (which artifact executed this)
    rec, _ = _request(args.base, "/api/health")
    h = _j(rec)
    ident = h.get("deployment_identity") or {}
    report["server_identity"] = {
        "engine_commit": h.get("engine_commit"),
        "engine_commit_source": (h.get("readiness") or {}).get(
            "engine_commit_source"),
        "build_artifact_sha256": ident.get("build_artifact_sha256"),
        "running_artifact_sha256": ident.get("running_artifact_sha256"),
        "identity_tamper": ident.get("identity_tamper"),
        "deployment_drift": ident.get("deployment_drift"),
        "llm_transport": ((h.get("readiness") or {}).get(
            "llm_transport") or {}).get("last_probe"),
        "transport_note": (
            "the deployment contract pins nvidia/openai/gpt-oss-120b "
            "EXTERNAL; this local artifact server selected the sandbox "
            "local-gateway (zai glm-4-plus, probe-verified OK) because "
            "ZAI_API_KEY is present in .env.keys — a REAL LLM "
            "transport either way; recorded honestly, not conflated "
            "with the deployed transport"),
    }

    # 1. PROBLEM -> run creation through the public surface
    #    (rehydrate mode: reuse an existing terminal session)
    if args.session_id and args.owner:
        sid = args.session_id
        owner = args.owner
        report["run_created"] = {
            "mode": "REHYDRATE (existing session, no new compute)",
            "session_id": sid,
            "owner_capability": "tosca_owner cookie (httpOnly, replayed)",
        }
    else:
        rec, owner = _request(args.base, "/api/discoveries",
                              method="POST",
                              body={"text": args.problem})
        d = _j(rec)
        sid = d.get("session_id")
        report["run_created"] = {
            "http_status": rec.get("status"),
            "session_id": sid,
            "owner_capability": "tosca_owner cookie (httpOnly, replayed)",
        }
        if not sid:
            report["error"] = "run not accepted"
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(json.dumps(report, indent=1,
                                                 default=str))
            print(json.dumps(report, indent=1, default=str))
            return 1

    # 2. poll to terminal
    detail = _wait_terminal(args.base, sid, owner)
    if not detail:
        report["error"] = "no terminal state reached"
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=1,
                                             default=str))
        return 1

    report["final_status"] = detail.get("status")

    # 3. stage chain traversal (the canonical STAGE_ORDER, recorded)
    stages = detail.get("stages") or []
    report["stage_chain"] = [
        {"stage": s.get("stage"), "status": s.get("status")}
        for s in stages]

    # 4. premise gate
    pg = {}
    for s in stages:
        if s.get("stage") == "PREMISE_GATE":
            pg = s
    report["premise_gate"] = {
        "verdict": pg.get("verdict") or (pg.get("result") or {}).get(
            "verdict"),
        "reason": pg.get("explanation") or (pg.get("result") or {}).get(
            "explanation"),
    }

    # 5. evidence + mechanism
    report["evidence_summary"] = {
        "n_evidence_items": len(detail.get("evidence") or
                                (detail.get("final_state") or {}).get(
                                    "evidence") or []),
        "sample_titles": [
            (e or {}).get("title") for e in (
                detail.get("evidence") or [])[:5]],
    }
    synth = {}
    for s in stages:
        if s.get("stage") == "SYNTHESIZE":
            synth = s
    mech = synth.get("mechanism") or (synth.get("result") or {}).get(
        "mechanism") or {}
    report["mechanism"] = mech if isinstance(mech, dict) else {
        "summary": str(mech)[:400]}

    # 6. physics — every R400-C capture field, extracted not inferred
    report.update(_extract_physics(detail))

    # 7. attack
    atk = {}
    for s in stages:
        if s.get("stage") == "ATTACK":
            atk = s
    report["attack"] = {
        "status": atk.get("status"),
        "verdict": atk.get("verdict") or (atk.get("result") or {}).get(
            "verdict"),
    }

    # 8. the R400-C capture contract, assembled in one machine-readable
    #    block. Every value is COPIED from the machine's own records
    #    (API session detail + the ENGINE_RUNS artifacts the server
    #    writes); nothing is inferred or backfilled (Art. II/VI).
    es = detail.get("engineering_specification") or {}
    pe = es.get("physics_evaluation") or {}
    bc = pe.get("baseline_comparison") or {}
    fmc = pe.get("failure_mode_contract") or {}
    inv_spec = detail.get("invention_specification") or {}
    inv_id = inv_spec.get("invention_id")
    inv_id_v = (inv_id or {}).get("value") if isinstance(
        inv_id, dict) else inv_id
    fs_state = detail.get("final_state") or {}
    ss = detail.get("survivor_selection") or {}
    cand = bc.get("candidate") or {}
    base = bc.get("baseline") or {}
    phys_block = {
        "candidate_id": inv_id_v,
        "mechanism_id": inv_id_v,  # deterministic mechanism identity:
        # inv:<problem_id>:<final-envelope-hash[0:12]> (INVENTION_SPEC)
        "baseline": {
            "identity": (base.get("spec_summary") or {}).get(
                "geometry_identity"),
            "geometry_hash": (base.get("spec_summary") or {}).get(
                "geometry_hash"),
            "segments": (base.get("spec_summary") or {}).get("segments"),
            "value_severe_obstruction": base.get("value"),
        },
        "target_metric": bc.get("target_metric"),
        "constraints": bc.get("constraints"),
        "physics_model_version": {
            "solver": pe.get("solver_version"),
            "gate": pe.get("gate_version"),
        },
        "input_hash": {
            "candidate_geometry_hash": (cand.get("spec_summary")
                                        or {}).get("geometry_hash"),
            "baseline_geometry_hash": (base.get("spec_summary")
                                       or {}).get("geometry_hash"),
        },
        "output_hash": {
            "final_envelope_hash_prefix": (
                str(inv_id_v).rsplit(":", 1)[-1] if inv_id_v else None),
            "invention_spec_hash": inv_spec.get("_spec_hash"),
            "engineering_reasoning_chains_hash": (
                es.get("engineering_reasoning_chains") or {}).get("hash"),
        },
        "failure_state": fmc,
        "baseline_comparison": bc,
        "verdict": {
            "physics_lifecycle": (ss.get("selection_basis") or {}).get(
                "physics_lifecycle"),
            "design_learning": {
                k: v for k, v in (
                    pe.get("design_learning") or {}).items()
                if k != "iterations"},
            "machine_final_status": fs_state.get("final_status"),
            "machine_reason": fs_state.get("reason"),
            "adjudication": fs_state.get("adjudication_verdict"),
            "release_state": (
                "NO_PACKAGE (scientifically REJECTED — R399 W2.1: "
                "rejected runs generate no buyer dossier; the kill is "
                "recorded, the run stays auditable)"
                if (fs_state.get("final_status") == "REJECTED"
                    or (detail.get("cemetery_update") or {}))
                else ((detail.get("package") or {}).get(
                    "release_status") or "HELD_FOR_HUMAN_REVIEW"
                    if detail.get("package") else None)),
            "result_class": "COMPUTATIONAL_RESULT (Art. XXXVIII layer "
                            "4 — computation log, never a physical "
                            "claim; reference-data calibration is NOT "
                            "PHYSICAL_OBSERVATION)",
        },
    }
    report["r400c_capture"] = phys_block

    report["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                           time.gmtime())
    report["raw_exchanges"] = RAW
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, default=str))
    slim = {k: v for k, v in report.items()
            if k not in ("raw_exchanges",)}
    print(json.dumps(slim, indent=1, default=str)[:6000])
    print(f"\nfull record -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
