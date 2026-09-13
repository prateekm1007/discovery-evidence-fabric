#!/usr/bin/env python3
"""scripts/r450_production_fresh_run.py — the R450 §14 fresh
production-run proof: ONE genuinely fresh problem through the REAL user
path on the deployed canonical Space (the R449 Evidence Fabric + the R450
Directional Improvement Engine build).

The problem below was authored for this proof and has NEVER been
submitted to any environment — not Render, not the sandbox batteries,
not the R446-HF cases, not the R447 e2e cases (conveyor idlers /
hospital heat pump / crew rostering), not the R447 live-test runs
(district heating), not the R449 two-arm benchmark (seawater condensers
/ the arm problem), not the R450 directional benchmark (battery thermal
runaway / slurry pump wear). Domain: hydropower runner erosion —
mechanically/physically distinct from every prior case (sediment
erosion + cavitation on a reaction turbine).

Transport: the FIXED owner-capability path (the R447 run-not-found
closure) — run creation with no cookie; the response carries the
caller's own owner_key; every subsequent request carries X-Tosca-Owner.
No cookie dependence (the embedded-iframe cookie policy was the defect).

Capture: the acceptance chain from the product's OWN routes (never
internal state): result -> state -> model (canonical GLB) -> CIO ->
render record + hero/poster -> buyer package ZIP with the R447 package
integrity verifier (ONE implementation, imported — Art. X).

Slice-resumable (the sandbox reaps processes at tool-call boundaries):
session persists to R450/PRODUCTION_FRESH_RUN_SESSION.json; re-invoke
to resume the SAME run.

Usage: HF_TOKEN=... python3 scripts/r450_production_fresh_run.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT))

# ONE package-integrity implementation (Art. X) — the R447 verifier
from r447_e2e_production import (  # noqa: E402
    _sha256, _verify_package_integrity)

BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
HF_TOKEN = os.environ.get("HF_TOKEN", "")
OUT = REPO_ROOT / "R450" / "PRODUCTION_FRESH_RUN.json"
RUNS_DIR = REPO_ROOT / "R450" / "PRODUCTION_FRESH_RUN"
SESSION = REPO_ROOT / "R450" / "PRODUCTION_FRESH_RUN_SESSION.json"

SLICE_POLL_S = 420
POLL_INTERVAL_S = 20
POST_RUN_VISUAL_WAIT_S = 360

CASE: Dict[str, str] = {
    "case_id": "r450-fresh-hydro-runner-erosion",
    "directive_class": (
        "R450 §14 fresh production-run proof: hydropower runner "
        "sediment-erosion + cavitation protection — a genuinely fresh "
        "problem/domain through the real user path on the deployed "
        "R449/R450 engine"),
    "text": (
        "Run-of-river hydropower units on a monsoon-fed river lose 8 to "
        "14 percent of turbine efficiency each dry season: abrasive "
        "suspended sediment (up to 2.5 grams per liter, "
        "quartz-dominant, D50 near 60 microns) combined with "
        "intermittent draft-tube vortex cavitation erodes the 13Cr4Ni "
        "runner blades and strips the hard-facing overlay within three "
        "seasons, forcing a full runner overhaul every 30 months at 1.4 "
        "million dollars per outage. Design a runner-blade protection "
        "and flow-management arrangement that keeps the "
        "leading-edge profile loss below 0.5 millimeter per season at "
        "the existing net head of 42 meters, maintains at least 91 "
        "percent best-efficiency-point output through the sediment "
        "season, avoids cavitation damage at part-load operation down "
        "to 40 percent of rated discharge, fits the existing embedded "
        "draft-tube geometry without civil works, and can be renewed "
        "during the annual 21-day maintenance window with equipment "
        "already on site."),
}


def _log(msg: str) -> None:
    print(f"[r450-fresh] {msg}", flush=True)


def _req(path: str, body: Optional[Dict[str, Any]] = None,
         timeout: int = 120, owner_key: Optional[str] = None,
         binary: bool = False) -> Dict[str, Any]:
    import urllib.error
    import urllib.request
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json",
               "Authorization": f"Bearer {HF_TOKEN}"}
    if owner_key:
        headers["X-Tosca-Owner"] = owner_key
    req = urllib.request.Request(
        url, data=data, headers=headers,
        method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if binary:
                chunks = b""
                while True:
                    c = r.read(65536)
                    if not c:
                        break
                    chunks += c
                return {"http_status": r.status, "bytes": chunks}
            return {"http_status": r.status,
                    "body": json.loads(r.read() or b"{}")}
    except urllib.error.HTTPError as e:
        try:
            txt = e.read()[:400].decode(errors="replace")
        except Exception:  # noqa: BLE001
            txt = ""
        return {"http_status": e.code, "error": txt}
    except Exception as exc:  # noqa: BLE001
        return {"http_status": None,
                "error": f"{type(exc).__name__}: {str(exc)[:200]}"}


def _resume() -> Optional[Dict[str, Any]]:
    if SESSION.exists():
        try:
            return json.loads(SESSION.read_text())
        except Exception:  # noqa: BLE001
            return None
    return None


def _poll_slice(session_id: str, owner_key: Optional[str],
                deadline_s: float) -> Dict[str, Any]:
    t0 = time.time()
    last: Dict[str, Any] = {}
    while time.time() - t0 < deadline_s:
        r = _req(f"/api/run/{session_id}/result", timeout=90,
                 owner_key=owner_key)
        if r.get("http_status") == 200:
            last = r
            body = r.get("body") or {}
            status = str(body.get("status") or "").upper()
            if status in ("COMPLETE", "FAILED", "ERROR", "DONE",
                          "INTERRUPTED", "RUN_BLOCKED_TRANSPORT",
                          "ERROR_RUN", "ERROR_BUILD"):
                return r
        elif r.get("http_status") is None and "error" in r:
            _log(f"poll transport hiccup: {r['error'][:80]}")
        time.sleep(POLL_INTERVAL_S)
    return {"http_status": "SLICE_DEADLINE", "last": last}


# ---------------------------------------------------------------------------
# the per-run capture — the product's own routes only
# ---------------------------------------------------------------------------
def _capture_run(session_id: str,
                 owner_key: Optional[str]) -> Dict[str, Any]:
    rec: Dict[str, Any] = {"case_id": CASE["case_id"],
                           "directive_class": CASE["directive_class"],
                           "run_id": session_id}
    result = _req(f"/api/run/{session_id}/result", timeout=120,
                  owner_key=owner_key)
    body = (result.get("body") or {})
    rec["user_visible_state"] = {
        "status": body.get("status"),
        "final_status": body.get("final_status"),
    }
    state = _req(f"/api/run/{session_id}/state", timeout=90,
                 owner_key=owner_key)
    st = (state.get("body") or {}) if state.get("http_status") == 200 \
        else {"error": state.get("error")}
    rec["canonical_state"] = st
    rec["chain"] = {
        "problem": bool(st.get("problem") or st.get("phase_progression")),
        "evidence": (st.get("evidence") or {}),
        "mechanism": (st.get("mechanism") or st.get("invention") or {}),
        "attack": (st.get("attack") or st.get("independent_attack") or {}),
        "evolution": (st.get("evolution") or st.get("generations") or {}),
        "experiment": (st.get("experiment_state") or {}),
        "package_terminal": (st.get("package_state") or {}),
    }
    # the R450 engine surface, recorded honestly whether present or
    # absent (Art. XV/XXV — never manufactured)
    ev = rec["chain"]["evolution"]
    rec["r450_engine_surface"] = {
        "directional_hypotheses_present": bool(
            ev.get("directional_hypotheses")
            or st.get("directional_hypotheses")),
        "improvement_trajectory_present": bool(
            ev.get("improvement_trajectory")
            or st.get("improvement_trajectory")),
        "evidence_fabric_fields": bool(
            (st.get("evidence") or {}).get("fabric")
            or (st.get("evidence") or {}).get("evidence_fabric")),
    }
    # geometry: the canonical GLB bytes + sha
    glb = _req(f"/api/run/{session_id}/model", timeout=180,
               owner_key=owner_key, binary=True)
    rec["geometry"] = {
        "http_status": glb.get("http_status"),
        "bytes": len(glb.get("bytes") or b""),
        "sha256": _sha256(glb["bytes"]) if glb.get("bytes") else None,
    }
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    if glb.get("bytes"):
        (RUNS_DIR / f"{session_id}_canonical.glb").write_bytes(
            glb["bytes"])
    # CIO (with the canonical package terminal object)
    cio = _req(f"/api/run/{session_id}/cio", timeout=90,
               owner_key=owner_key)
    cio_body = (cio.get("body") or {}) if cio.get("http_status") == 200 \
        else {}
    rec["cio_present"] = bool(cio_body.get("present"))
    rec["cio_geometry"] = {
        "present": (cio_body.get("geometry") or {}).get("present"),
        "class": (cio_body.get("geometry") or {}).get("class"),
        "components_n": len((cio_body.get("geometry") or {})
                            .get("components") or []),
    }
    rec["cio_package_terminal"] = (cio_body.get("downloads") or {}).get(
        "package_terminal")
    rec["cio_experiment_contract"] = (cio_body.get("experiment") or {})
    (RUNS_DIR / f"{session_id}_cio.json").write_text(
        json.dumps(cio_body, indent=1, default=str))
    # visual state: hero/poster + render record
    rec["visual_state"] = {}
    for name in ("hero.png", "poster.png"):
        r = _req(f"/api/run/{session_id}/render/{name}", timeout=120,
                 owner_key=owner_key, binary=True)
        rec["visual_state"][name.replace(".", "_")] = {
            "http_status": r.get("http_status"),
            "bytes": len(r.get("bytes") or b""),
            "sha256": _sha256(r["bytes"]) if r.get("bytes") else None,
        }
        if r.get("bytes"):
            (RUNS_DIR / f"{session_id}_{name}").write_bytes(r["bytes"])
    vr = _req(f"/api/run/{session_id}/render/render_record.json",
              timeout=90, owner_key=owner_key)
    if vr.get("http_status") == 200:
        rr = vr.get("body") or {}
        rec["visual_state"]["render_record"] = {
            "status": rr.get("status"),
            "gate_verdict": ((rr.get("visual_gate") or {})
                             .get("verdict")),
            "failed_rules": ((rr.get("visual_gate") or {})
                             .get("failed_rules") or [])[:6],
            "hero_suppressed": rr.get("hero_suppressed"),
            "release_blocked": rr.get("release_blocked"),
        }
    # the buyer package ZIP through the product's own download route
    pkg = _req(f"/api/sessions/{session_id}/package", timeout=240,
               owner_key=owner_key, binary=True)
    if pkg.get("http_status") == 200 and pkg.get("bytes"):
        (RUNS_DIR / f"{session_id}_package.zip").write_bytes(pkg["bytes"])
        rec["package_integrity"] = _verify_package_integrity(
            CASE["case_id"], pkg["bytes"])
    else:
        rec["package_integrity"] = {
            "http_status": pkg.get("http_status"),
            "verdict": "NOT_PRODUCED",
            "package_terminal_state": (st.get("package_state") or {})
            .get("package_state"),
            "blocked_stage": (st.get("package_state") or {})
            .get("blocked_stage"),
            "blocked_reason": str(
                (st.get("package_state") or {}).get("blocked_reason")
                or "")[:400],
            "next_action": (st.get("package_state") or {}).get(
                "next_action"),
            "release_verdict": (st.get("package_state") or {}).get(
                "release_verdict"),
        }
    return rec


def main() -> int:
    sess = _resume() or {}
    entry = sess.get("case") or {}
    if not entry.get("done"):
        if not entry.get("run_id"):
            # the FIXED transport: run creation with NO cookie; the
            # response carries the caller's own owner_key
            r = _req("/api/run", body={"text": CASE["text"]},
                     timeout=120)
            if r.get("http_status") not in (200, 202):
                _log(f"submit failed {r.get('http_status')} "
                     f"{str(r.get('error'))[:160]}")
                return 1
            body = r.get("body") or {}
            entry = {
                "run_id": body.get("session_id") or body.get("run_id"),
                "owner_key": body.get("owner_key"),
            }
            # BS-021 hygiene: the owner key is a session capability —
            # persisted OUTSIDE the tracked tree for the resume path,
            # redacted from the committed record
            sess["case"] = entry
            SESSION.parent.mkdir(parents=True, exist_ok=True)
            SESSION.write_text(json.dumps(sess, indent=1))
            _log(f"submitted {entry['run_id']} "
                 f"(owner transport: {bool(entry.get('owner_key'))})")
        sid = entry.get("run_id")
        owner = entry.get("owner_key")
        if not sid:
            return 1
        pr = _poll_slice(sid, owner, SLICE_POLL_S)
        status = None
        if pr.get("http_status") == 200:
            status = ((pr.get("body") or {}).get("status")
                      or "").upper()
        elif pr.get("http_status") == "SLICE_DEADLINE":
            status = "IN_FLIGHT"
        _log(f"status {status}")
        if status in ("COMPLETE", "FAILED", "ERROR", "INTERRUPTED",
                      "RUN_BLOCKED_TRANSPORT", "ERROR_RUN",
                      "ERROR_BUILD"):
            _log(f"terminal — waiting {POST_RUN_VISUAL_WAIT_S}s for the "
                 f"async render + package...")
            time.sleep(POST_RUN_VISUAL_WAIT_S)
            entry["done"] = True
            entry["capture"] = _capture_run(sid, owner)
            sess["case"] = entry
            SESSION.write_text(json.dumps(sess, indent=1))
    # write the results record (owner_key REDACTED — BS-021)
    results = {
        "artifact_type": "R450_PRODUCTION_FRESH_RUN",
        "base": BASE,
        "case_id": CASE["case_id"],
        "directive_class": CASE["directive_class"],
        "freshness_statement": (
            "authored for this proof; never submitted to any prior "
            "environment (Render, sandbox batteries, R446-HF, R447 e2e, "
            "R447 live tests, R449 two-arm benchmark, R450 directional "
            "benchmark)"),
        "transport": "X-Tosca-Owner header (the R447 run-not-found fix); "
                     "run creation with no cookie; owner_key returned to "
                     "the caller, redacted from this record (BS-021)",
        "started_at_utc": sess.get("started_at_utc")
        or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run_id": entry.get("run_id"),
        "captured": entry.get("capture"),
        "finished_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                         time.gmtime()),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=1, default=str))
    _log(f"results -> {OUT} (done={bool(entry.get('done'))})")
    return 0 if entry.get("done") else 1


if __name__ == "__main__":
    raise SystemExit(main())
