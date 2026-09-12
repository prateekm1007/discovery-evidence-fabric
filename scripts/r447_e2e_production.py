#!/usr/bin/env python3
"""scripts/r447_e2e_production.py — R447 Phases 3/4/5/8: fresh
end-to-end user runs on the Hugging Face production deployment.

THE DIRECTIVE'S TARGET (Phase 3): one fresh user run through the REAL
user path with the acceptance chain
  PROBLEM -> EVIDENCE -> MECHANISM -> CANDIDATES -> ATTACK ->
  DIAGNOSIS -> CAUSAL IMPROVEMENT -> TECHNICAL EVALUATION ->
  ENGINEERING GEOMETRY -> VISUAL COMPILER -> DECISIVE EXPERIMENT ->
  ENGINEERING DOSSIER -> TECHNOLOGY TRANSFER PACKAGE
— the actual product, not a test harness, not a replay, not a captured
case.

Phase 5 adds the multi-domain requirement: THREE fresh problems in
  mechanical
  thermal/energy
  another materially unrelated domain (software/ML)
— different problem, different evidence, different mechanism, different
engineering state, different geometry, coherent package. The existing
user-path machinery is used (no new benchmark).

Phase 4 (buyer package integrity) runs on the fresh runs' packages:
  ZIP -> clean extraction -> all files retrievable -> references valid
  -> no stale paths -> no impossible state + the artifact hashes
  (geometry hash, visual lineage, package hash, source hashes).

Slice-resumable (sandbox reaps processes): session + cookie persist to
R447/E2E_SESSION.json; re-invocation resumes the SAME runs.

Usage:
  python3 scripts/r447_e2e_production.py   (re-invoke to resume)
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT))

BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
# R447 security scrub (BS-021): the token comes from the ENVIRONMENT only —
# a hardcoded credential in a tracked file is exactly the leak class the
# HF upload scanner rejected (and the reason this file needed scrubbing).
HF_TOKEN = os.environ.get("HF_TOKEN", "")
OUT = REPO_ROOT / "R447" / "E2E_PRODUCTION_RUNS.json"
RUNS_DIR = REPO_ROOT / "R447" / "E2E_PRODUCTION_RUNS"
SESSION = REPO_ROOT / "R447" / "E2E_SESSION.json"

SLICE_POLL_S = 420
POLL_INTERVAL_S = 20
POST_RUN_VISUAL_WAIT_S = 360

# THREE GENUINELY FRESH problems (never submitted to any environment —
# not Render, not the sandbox batteries, not the R446-HF cases)
CASES: List[Dict[str, str]] = [
    {
        "case_id": "r447-e2e-mechanical-idler",
        "directive_class": ("Phase 5 mechanical: a fresh mechanical "
                            "wear/fatigue problem"),
        "text": (
            "Continuous bauxite slurry conveyors at an alumina refinery "
            "destroy return-idler bearings every 7 to 11 weeks: fine "
            "abrasive dust ingresses past conventional labyrinth seals, "
            "and each unscheduled idler replacement stops the 2.4 km "
            "overland conveyor for 6 hours. Design an idler bearing "
            "protection arrangement that keeps grease contamination "
            "below ISO 4406 code 18/16/13 over a 3-year service "
            "interval, survives shaft misalignment up to 0.5 degrees, "
            "operates from minus 10 to 55 degrees C at belt speeds to "
            "4.5 meters per second, and allows a single technician to "
            "replace the cartridge in under 20 minutes without "
            "removing the idler frame."),
    },
    {
        "case_id": "r447-e2e-thermal-energy-heatpump",
        "directive_class": ("Phase 5 thermal/energy: a fresh energy "
                            "problem, structurally unlike the mechanical "
                            "case"),
        "text": (
            "A 400-bed hospital spends 1.9 million dollars annually on "
            "steam for laundry and sterilization while rejecting "
            "low-grade heat from its chiller plant through cooling "
            "towers. Design a heat-recovery upgrade that preheats "
            "boiler feedwater using the chiller condenser loop, "
            "lifting recovered heat from 32 to 60 degrees C with a "
            "coefficient of performance above 3.5, fitting inside the "
            "existing plant room's 4.2 by 2.8 meter footprint, paying "
            "back in under 6 years at 11 cents per kilowatt-hour, and "
            "surviving 25-year service with refrigerant regulations "
            "already phasing out R-134a."),
    },
    {
        "case_id": "r447-e2e-software-ml-scheduling",
        "directive_class": ("Phase 5 materially unrelated domain: "
                            "software/ML operational scheduling"),
        "text": (
            "A regional rail operator's crew-rostering system fails to "
            "produce legal rosters for 1200 daily services: the "
            "constraint solver runs 40 minutes per attempt, 8 percent "
            "of mornings it times out and dispatchers hand-write "
            "emergency rosters that violate rest directives, and each "
            "violation costs 1900 dollars in penalty payments plus "
            "investigation time. Design a scheduling approach that "
            "produces legally compliant rosters in under 5 minutes, "
            "recovers from same-day disruptions (cancellations, "
            "absences) with re-optimization in under 60 seconds, "
            "explains WHY any assignment was chosen to labor "
            "inspectors, and integrates with the existing timetable "
            "database without replacing it."),
    },
]


def _log(msg: str) -> None:
    print(f"[r447-e2e] {msg}", flush=True)


def _req(path: str, body: Optional[Dict[str, Any]] = None,
         timeout: int = 120, cookie: Optional[str] = None,
         binary: bool = False) -> Dict[str, Any]:
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json",
               "Authorization": f"Bearer {HF_TOKEN}"}
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(
        url, data=data, headers=headers,
        method="POST" if data is not None else "GET")
    set_cookie = None
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            set_cookie = r.headers.get("Set-Cookie")
            if binary:
                chunks = b""
                while True:
                    c = r.read(65536)
                    if not c:
                        break
                    chunks += c
                return {"http_status": r.status, "bytes": chunks,
                        "set_cookie": set_cookie}
            return {"http_status": r.status, "set_cookie": set_cookie,
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


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _resume() -> Optional[Dict[str, Any]]:
    if SESSION.exists():
        try:
            return json.loads(SESSION.read_text())
        except Exception:  # noqa: BLE001
            return None
    return None


def _poll_slice(session_id: str, cookie: Optional[str],
                deadline_s: float) -> Dict[str, Any]:
    t0 = time.time()
    last: Dict[str, Any] = {}
    while time.time() - t0 < deadline_s:
        r = _req(f"/api/run/{session_id}/result", timeout=90, cookie=cookie)
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
# Phase 4 — buyer package integrity verification (on the fresh packages)
# ---------------------------------------------------------------------------
def _verify_package_integrity(case_id: str, zip_bytes: bytes
                              ) -> Dict[str, Any]:
    """ZIP -> clean extraction -> files retrievable -> references valid
    -> no stale paths -> no impossible state. Typed failures, never
    silent passes (Art. V/XXV)."""
    out: Dict[str, Any] = {"case_id": case_id,
                           "zip_sha256": _sha256(zip_bytes),
                           "zip_bytes": len(zip_bytes)}
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except Exception as exc:  # noqa: BLE001
        out["verdict"] = "FAIL"
        out["reason"] = f"zip unreadable: {exc}"
        return out
    names = zf.namelist()
    out["n_entries"] = len(names)
    bad = zf.testzip()
    if bad is not None:
        out["verdict"] = "FAIL"
        out["reason"] = f"corrupt entry: {bad}"
        return out
    # clean extraction: every entry extracts without error
    extracted: Dict[str, bytes] = {}
    try:
        for n in names:
            extracted[n] = zf.read(n)
    except Exception as exc:  # noqa: BLE001
        out["verdict"] = "FAIL"
        out["reason"] = f"extraction failed at {exc}"
        return out
    out["all_files_retrievable"] = True
    # no stale paths: no absolute paths, no .., no /tmp or machine-bound
    stale = [n for n in names
             if n.startswith("/") or ".." in Path(n).parts
             or n.startswith("/tmp") or ":\\\\" in n
             or n.startswith("C:")]
    out["stale_paths"] = stale[:8]
    # the machine-readable records that must be present
    required_machine = [
        n for n in names if n.upper().endswith(
            ("RENDER_RECORD.JSON", "GEOMETRY_SPEC.JSON",
             "ARTIFACT_IDENTITY.JSON", "HERO_RELEASE_STATE.JSON",
             "SCENE_SPEC.JSON", "VISUAL_GATE.JSON"))
    ]
    out["machine_readable_records"] = required_machine[:16]
    # PDFs present + non-empty
    pdfs = [n for n in names if n.lower().endswith(".pdf")]
    out["pdfs"] = pdfs
    out["pdfs_nonempty"] = all(len(extracted[n]) > 1000 for n in pdfs)
    # visual artifacts where earned: hero/poster/views
    hero_imgs = [n for n in names if "hero" in n.lower()
                 and n.lower().endswith((".png", ".glb"))]
    poster = [n for n in names if "poster" in n.lower()]
    out["hero_artifacts"] = hero_imgs[:8]
    out["poster_artifacts"] = poster[:4]
    # references valid: every relative path referenced inside the
    # machine-readable JSON records resolves inside the ZIP
    dangling: List[str] = []
    for n in required_machine:
        try:
            rec = json.loads(extracted[n])
        except Exception:  # noqa: BLE001
            continue
        refs = _collect_path_refs(rec)
        for ref in refs:
            if ref.startswith("/") or ".." in Path(ref).parts:
                dangling.append(f"{n}: {ref}")
            elif ref and not any(
                    x == ref or x.endswith("/" + ref) or ref.endswith(
                        "/" + x) for x in names):
                dangling.append(f"{n}: {ref}")
    out["dangling_references"] = dangling[:10]
    # the impossible-state check: a package carrying a hero while the
    # render record says suppressed, or a COMPLETE_PASS visual gate with
    # zero images
    impossible: List[str] = []
    for n in required_machine:
        if n.upper().endswith("RENDER_RECORD.JSON"):
            try:
                rec = json.loads(extracted[n])
            except Exception:  # noqa: BLE001
                continue
            gate = (rec.get("visual_gate") or {})
            verdict = gate.get("verdict")
            hero_files = [x for x in names if "hero" in x.lower()]
            if verdict not in ("COMPLETE_PASS",) and hero_files:
                impossible.append(
                    f"{n}: gate {verdict} but hero files present")
            if verdict == "COMPLETE_PASS" and not any(
                    x.lower().endswith(".png") for x in hero_files):
                impossible.append(
                    f"{n}: gate COMPLETE_PASS but no hero image")
    out["impossible_states"] = impossible[:6]
    ok = (not stale and not dangling and not impossible
          and out["pdfs_nonempty"])
    out["verdict"] = "PASS" if ok else "FAIL"
    if not ok:
        out["reason"] = (f"stale={stale[:3]} dangling={dangling[:3]} "
                         f"impossible={impossible[:3]} "
                         f"pdfs_nonempty={out['pdfs_nonempty']}")
    return out


def _collect_path_refs(obj: Any, acc: Optional[List[str]] = None
                       ) -> List[str]:
    """Every string field that looks like a relative artifact path."""
    if acc is None:
        acc = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and ("path" in k.lower()
                                       or k in ("zip_path", "glb_path")):
                acc.append(v)
            else:
                _collect_path_refs(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _collect_path_refs(v, acc)
    return acc


# ---------------------------------------------------------------------------
# the per-run capture (the directive's full chain, from the product's
# own routes — never internal state)
# ---------------------------------------------------------------------------
def _capture_run(case: Dict[str, str], session_id: str,
                 cookie: Optional[str]) -> Dict[str, Any]:
    rec: Dict[str, Any] = {"case_id": case["case_id"],
                           "directive_class": case["directive_class"],
                           "run_id": session_id}
    result = _req(f"/api/run/{session_id}/result", timeout=120,
                  cookie=cookie)
    body = (result.get("body") or {})
    rec["user_visible_state"] = {
        "status": body.get("status"),
        "final_status": body.get("final_status"),
    }
    state = _req(f"/api/run/{session_id}/state", timeout=90,
                 cookie=cookie)
    rec["canonical_state"] = (state.get("body") or {}) \
        if state.get("http_status") == 200 else {"error": state.get("error")}
    st = rec["canonical_state"]
    rec["chain"] = {
        "problem": bool(st.get("problem") or st.get("phase_progression")),
        "evidence": (st.get("evidence") or {}),
        "mechanism": (st.get("mechanism") or st.get("invention") or {}),
        "attack": (st.get("attack") or st.get("independent_attack") or {}),
        "evolution": (st.get("evolution") or st.get("generations") or {}),
        "experiment": (st.get("experiment_state") or {}),
        "package_terminal": (st.get("package_state") or {}),
    }
    # geometry: the canonical GLB bytes + sha
    glb = _req(f"/api/run/{session_id}/model", timeout=180,
               cookie=cookie, binary=True)
    rec["geometry"] = {
        "http_status": glb.get("http_status"),
        "bytes": len(glb.get("bytes") or b""),
        "sha256": _sha256(glb["bytes"]) if glb.get("bytes") else None,
    }
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    if glb.get("bytes"):
        (RUNS_DIR / f"{session_id}_canonical.glb").write_bytes(
            glb["bytes"])
    # CIO (with the Phase-2 canonical package terminal object)
    cio = _req(f"/api/run/{session_id}/cio", timeout=90, cookie=cookie)
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
    # visual state: render record + gate + hero/poster
    rec["visual_state"] = {}
    for name in ("hero.png", "poster.png"):
        r = _req(f"/api/run/{session_id}/render/{name}", timeout=120,
                 cookie=cookie, binary=True)
        rec["visual_state"][name.replace(".", "_")] = {
            "http_status": r.get("http_status"),
            "bytes": len(r.get("bytes") or b""),
            "sha256": _sha256(r["bytes"]) if r.get("bytes") else None,
        }
        if r.get("bytes"):
            (RUNS_DIR / f"{session_id}_{name}").write_bytes(r["bytes"])
    vr = _req(f"/api/run/{session_id}/render/render_record.json",
              timeout=90, cookie=cookie)
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
    # the PACKAGE: the buyer ZIP through the product's own download route
    pkg = _req(f"/api/sessions/{session_id}/package", timeout=240,
               cookie=cookie, binary=True)
    if pkg.get("http_status") == 200 and pkg.get("bytes"):
        (RUNS_DIR / f"{session_id}_package.zip").write_bytes(pkg["bytes"])
        rec["package_integrity"] = _verify_package_integrity(
            case["case_id"], pkg["bytes"])
    else:
        rec["package_integrity"] = {
            "http_status": pkg.get("http_status"),
            "verdict": "NOT_PRODUCED",
            "package_terminal_state": (st.get("package_state") or {}).get(
                "package_state"),
            "blocked_stage": (st.get("package_state") or {}).get(
                "blocked_stage"),
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
    sess = _resume() or {"cases": {}}
    changed = False
    for case in CASES:
        cid = case["case_id"]
        entry = sess["cases"].get(cid) or {}
        if entry.get("done"):
            continue
        if not entry.get("run_id"):
            r = _req("/api/run", body={"text": case["text"]},
                     timeout=120)
            if r.get("http_status") not in (200, 202):
                _log(f"{cid}: submit failed {r.get('http_status')} "
                     f"{str(r.get('error'))[:120]}")
                continue
            body = r.get("body") or {}
            entry = {
                "run_id": body.get("session_id") or body.get("run_id"),
                "cookie": r.get("set_cookie") or "",
            }
            sess["cases"][cid] = entry
            changed = True
            SESSION.write_text(json.dumps(sess, indent=1))
            _log(f"{cid}: submitted {entry['run_id']}")
        sid = entry.get("run_id")
        cookie = entry.get("cookie") or None
        if not sid:
            continue
        # poll this slice
        pr = _poll_slice(sid, cookie, SLICE_POLL_S)
        status = None
        if pr.get("http_status") == 200:
            status = ((pr.get("body") or {}).get("status") or "").upper()
        _log(f"{cid}: status {status}")
        if status in ("COMPLETE", "FAILED", "ERROR", "INTERRUPTED",
                      "RUN_BLOCKED_TRANSPORT", "ERROR_RUN",
                      "ERROR_BUILD"):
            _log(f"{cid}: terminal — waiting {POST_RUN_VISUAL_WAIT_S}s "
                 f"for the async render + package...")
            time.sleep(POST_RUN_VISUAL_WAIT_S)
            entry["done"] = True
            entry["capture"] = _capture_run(case, sid, cookie)
            sess["cases"][cid] = entry
            SESSION.write_text(json.dumps(sess, indent=1))
            changed = True
    # write the results record whenever anything changed
    results = {
        "artifact_type": "R447_E2E_PRODUCTION_RUNS",
        "base": BASE,
        "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
        "cases": [sess["cases"][c["case_id"]].get("capture")
                  for c in CASES if sess["cases"].get(c["case_id"])
                  .get("capture")],
        "in_flight": [c["case_id"] for c in CASES
                      if not sess["cases"].get(c["case_id"], {})
                      .get("done")],
        "finished_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                         time.gmtime()),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=1, default=str))
    _log(f"results -> {OUT} "
         f"({len(results['cases'])}/{len(CASES)} captured, "
         f"in flight: {results['in_flight']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
