#!/usr/bin/env python3
"""scripts/r446_hf_production_verify.py — R446-HF Phases 8-9: fresh
production runs on the Hugging Face deployment (Cases A/B/C).

The directive's three test classes, as THREE GENUINELY NEW problems (never
submitted to any environment — not the Render production service, not the
sandbox batteries):

  hf-case-a  (Case A: fresh multi-component engineering problem)
             liquid-cooled cold-plate architecture for EV fast-charging
             battery packs (thermal-fluid; 12 modules x 44 cells)
  hf-case-b  (Case B: fresh structurally different problem)
             piezoelectric energy-harvesting floor tile (electromechanical
             energy conversion; structurally unlike Case A)
  hf-case-c  (Case C: large/high-detail geometry stress case)
             diffusion-bonded printed-circuit microchannel heat exchanger
             (60 etched sheets, 200 um channels — dense geometry)

Per run the driver records the directive's full chain:
  problem -> evidence -> candidate -> attack -> evolution/diagnosis ->
  technical state -> geometry -> CIO -> package -> visual state -> release

PLUS the R446-HF-specific evidence:
  - the canonical GLB BYTES captured + sha256 (the Phase 10 geometry
    differentiation audit compares ACROSS cases: different mechanism ->
    different parameterization -> different GLB, never 'different text,
    same geometry')
  - the render_record + visual_gate bodies (the visual compiler's TYPED
    state on the 16 GB host: does the visual stage actually RUN where the
    512 MB Render host typed-skipped RENDER_SKIPPED_LOW_MEMORY?)
  - the run's own version_check (engine identity for the run)

Slice-resumable (sandbox reaps processes): session id + owner cookie
persist to R446/HF_PRODUCTION_SESSION.json; re-invocation resumes the
SAME run. The cookie is presented exactly as the original browser session
would present it; the HF bearer is required because the Space is PRIVATE
(access transport, not an operator backdoor — the engine sees only the
ordinary user path).

The acceptance is COVERAGE + TRUTHFUL STATE (Art. XV/LXI): honest
INVENTION_REQUIRES_EXPERIMENT / NO_DEFENSIBLE_INVENTION / transport
failures are recorded exactly as the product states them.

Usage:
  python3 scripts/r446_hf_production_verify.py   (re-invoke to resume)
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT))

from r446_cio_extraction import summarize_for_record  # noqa: E402

BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
HF_TOKEN_FILE = Path("/home/z/my-project/.secrets/hf_token")
OUT = REPO_ROOT / "R446" / "HF_PRODUCTION_RUNS.json"
RUNS_DIR = REPO_ROOT / "R446" / "HF_PRODUCTION_RUNS"
SESSION = REPO_ROOT / "R446" / "HF_PRODUCTION_SESSION.json"

SLICE_POLL_S = 420       # poll budget per invocation (sandbox-safe)
POLL_INTERVAL_S = 20
POST_RUN_VISUAL_WAIT_S = 300  # async render job settle window

CASES: List[Dict[str, str]] = [
    {
        "case_id": "hf-case-a-cold-plate",
        "directive_class": "Case A: fresh multi-component engineering problem",
        "text": (
            "An EV fast-charging battery pack overheats unevenly during "
            "350 kW charging: cell-to-cell temperature gradients reach "
            "11 degrees C, accelerating cell degradation and risking "
            "thermal runaway propagation between modules. Design a "
            "liquid-cooled cold-plate architecture that keeps the "
            "cell-to-cell gradient below 5 degrees C across 12 modules of "
            "44 prismatic cells each, holds coolant pressure drop under "
            "20 kPa at the required flow rate, and keeps inlet coolant at "
            "25 degrees C. The solution must fit under the pack's 90 mm "
            "floor and survive 10-year coolant exposure."),
    },
    {
        "case_id": "hf-case-b-piezo-tile",
        "directive_class": "Case B: fresh structurally different engineering problem",
        "text": (
            "Railway-station corridor lighting beacons are powered by "
            "wiring that is expensive to retrofit. Pedestrian footfall "
            "under the station's busiest tiles averages 800 N peak force "
            "at 2 Hz, 18 hours per day. Design a piezoelectric "
            "energy-harvesting floor tile that converts this footfall into "
            "stored electricity with at least 15 percent conversion "
            "efficiency, sustains 200 mW average continuous output per "
            "tile for the wireless beacons, and keeps vertical deflection "
            "under 8 mm for accessibility compliance, with a 10-million-"
            "step fatigue life."),
    },
    {
        "case_id": "hf-case-c-microchannel-hx",
        "directive_class": "Case C: large/high-detail geometry stress case",
        "text": (
            "A two-phase cooling system for a data-center GPU rack must "
            "remove 5 kW from a 700 W/cm2 hotspot using a "
            "diffusion-bonded printed-circuit heat exchanger. Design the "
            "channel architecture: 60 chemically-etched stainless steel "
            "sheets, 200 micrometer channel widths, a 120 mm by 80 mm "
            "footprint, vapor-side pressure drop under 3 kPa, and "
            "uniform flow distribution across all 60 layers within 10 "
            "percent. The evaporator must survive 5000 thermal cycles "
            "between 25 and 85 degrees C."),
    },
]


def _log(msg: str) -> None:
    print(f"[r446-hf-prod] {msg}", flush=True)


def _bearer() -> str:
    return HF_TOKEN_FILE.read_text().strip()


def _req(path: str, body: Optional[Dict[str, Any]] = None,
         timeout: int = 120, cookie: Optional[str] = None,
         binary: bool = False) -> Dict[str, Any]:
    """One HTTP request to the PRIVATE Space: HF bearer (access) + the
    session owner cookie (user path), exactly as an authenticated browser
    session would present them."""
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json",
               "Authorization": f"Bearer {_bearer()}"}
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
        return {"http_status": None, "error": f"{type(exc).__name__}: "
                                              f"{str(exc)[:200]}"}


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
# visual-state capture (async render job; the 16 GB experiment's core)
# ---------------------------------------------------------------------------
def _visual_state(session_id: str, cookie: Optional[str]) -> Dict[str, Any]:
    """The render artifacts settle asynchronously after COMPLETE. Probe the
    typed records: render_record.json (the finalized R443-schema record),
    visual_gate.json, scene_spec.json, hero.png bytes (sha256), poster.png.
    Missing files are HONEST states (NOT_RUN / typed skip), never errors."""
    out: Dict[str, Any] = {}
    for name in ("render_record.json", "visual_gate.json",
                 "scene_spec.json"):
        r = _req(f"/api/run/{session_id}/render/{name}",
                 timeout=60, cookie=cookie)
        entry: Dict[str, Any] = {"http_status": r.get("http_status")}
        if r.get("http_status") == 200:
            entry["body"] = r.get("body")
        out[name] = entry
    for name in ("hero.png", "poster.png"):
        r = _req(f"/api/run/{session_id}/render/{name}",
                 timeout=120, cookie=cookie, binary=True)
        entry = {"http_status": r.get("http_status")}
        if r.get("http_status") == 200 and r.get("bytes"):
            entry["bytes"] = len(r["bytes"])
            entry["sha256"] = hashlib.sha256(r["bytes"]).hexdigest()
        out[name] = entry
    return out


def _model_bytes(session_id: str, cookie: Optional[str]) -> Dict[str, Any]:
    r = _req(f"/api/run/{session_id}/model", timeout=180, cookie=cookie,
             binary=True)
    out: Dict[str, Any] = {"http_status": r.get("http_status")}
    if r.get("http_status") == 200 and r.get("bytes") is not None:
        blob = r["bytes"]
        (RUNS_DIR / f"{session_id}_canonical.glb").write_bytes(blob)
        out["bytes"] = len(blob)
        out["sha256"] = hashlib.sha256(blob).hexdigest()
    return out


def _chain_record(problem: Dict[str, Any], result_body: Dict[str, Any],
                  cio_body: Any, cio_resp: Dict[str, Any],
                  model_resp: Dict[str, Any],
                  visual: Dict[str, Any],
                  session_id: str) -> Dict[str, Any]:
    rs = result_body.get("run_state") or {}
    inv = result_body.get("invention_specification") or {}
    eng = result_body.get("engineering_specification") or {}
    dex = result_body.get("decisive_experiment") or {}
    _gens = rs.get("generations")
    if isinstance(_gens, dict):
        _gens = _gens.get("generations") or []
    gens = _gens if isinstance(_gens, list) else []

    def _unwrap_v(field: Any) -> Any:
        if isinstance(field, dict) and "value" in field and set(
                field.keys()) <= {"value", "epistemic_class",
                                  "origin_stage", "evidence_ids", "note",
                                  "source_span", "provenance"}:
            return field.get("value")
        return field

    geo = (cio_body or {}).get("geometry") or {} if isinstance(
        cio_body, dict) else {}
    rr = (visual.get("render_record.json") or {}).get("body") or {}
    vg = (visual.get("visual_gate.json") or {}).get("body") or {}
    return {
        "problem": {
            "case_id": problem["case_id"],
            "directive_class": problem["directive_class"],
            "submitted_text": problem["text"],
        },
        "evidence": {
            "record_count": ((rs.get("evidence_state") or {}).get(
                "records_found")),
        },
        "candidate": {
            "mechanism_state": rs.get("mechanism_state"),
            "gen1_mechanism": (_unwrap_v(inv.get("mechanism"))
                               if isinstance(inv.get("mechanism"), dict)
                               else inv.get("mechanism")),
            "invention_id": _unwrap_v(inv.get("invention_id")),
        },
        "attack": {
            "state": rs.get("attack_state"),
            "note": ("abstain/escalate gate IN FORCE (attacker "
                     "NOT_CALIBRATED): raw KILL travels as "
                     "ESCALATED_OBJECTION; SKIPPED = honest blocker "
                     "cascade, never a scientific verdict (Art. LXI)"),
        },
        "evolution_diagnosis": {
            "state": rs.get("evolution_state"),
            "n_generations": len(gens),
            "generations": [
                {"gen": g.get("gen") or g.get("generation"),
                 "label": g.get("label"),
                 "origin": g.get("origin"),
                 "state": g.get("state"),
                 "has_causal_delta": bool(
                     g.get("causal_delta") or
                     (g.get("architecture") or {}).get("causal_delta"))}
                for g in gens[:6]],
            "outcome": rs.get("outcome"),
            "outcome_label": rs.get("outcome_label"),
            "outcome_basis": rs.get("outcome_basis"),
        },
        "technical_state": {
            "canonical_domain": ((eng.get("why_this_domain") or {}).get(
                "canonical_family")),
            "n_parameters": len(eng.get("parameters") or [])
            if isinstance(eng.get("parameters"), list) else None,
            "decisive_experiment_present": bool(dex),
            "falsification_contract_present": bool(
                (dex.get("falsification_contract") or {})
                if isinstance(dex, dict) else None),
        },
        "geometry": {
            "glb_http": model_resp.get("http_status"),
            "glb_bytes": model_resp.get("bytes"),
            "glb_sha256": model_resp.get("sha256"),
            "components": geo.get("components"),
            "domain_family": geo.get("domain_family"),
            "bridge_outcome": geo.get("bridge_outcome"),
        },
        "cio": summarize_for_record(cio_resp.get("http_status"), cio_body),
        "package_state": {
            "downloads": (cio_body or {}).get("downloads")
            if isinstance(cio_body, dict) else None,
            "package_state": rs.get("package_state"),
        },
        "visual_state": {
            "render_record_status": (visual.get("render_record.json") or
                                     {}).get("http_status"),
            "render_verdict": rr.get("verdict") or rr.get("status"),
            "render_states": rr.get("statuses") or rr.get("artifact_states"),
            "visual_gate_status": (visual.get("visual_gate.json") or
                                   {}).get("http_status"),
            "visual_gate_verdict": vg.get("verdict") or vg.get("gate"),
            "hero_png": visual.get("hero.png"),
            "poster_png": visual.get("poster.png"),
        },
        "user_visible_state": {
            "status": result_body.get("status"),
            "final_status": result_body.get("final_status"),
        },
        "engine_identity_for_run": result_body.get("version_check"),
        "run_id": session_id,
    }


def _case_key(c: Dict[str, Any]) -> Optional[str]:
    """The case id at EITHER nesting level (the chain record nests it
    under problem; the in-flight/error records carry it top-level). The
    R446-HF driver's first version read only the top level and
    RE-SUBMITTED a completed case (duplicate run ts_34e9979b5b84,
    disclosed in the report) — this accessor is the fix."""
    return c.get("case_id") or ((c.get("problem") or {}).get("case_id"))


def _run_case(problem: Dict[str, Any], report: Dict[str, Any],
              completed: List[str]) -> Optional[Dict[str, Any]]:
    case_id = problem["case_id"]
    if case_id in completed:
        _log(f"{case_id}: already recorded (resume)")
        return None

    sess = _resume()
    if sess and sess.get("case") == case_id and sess.get("session_id") \
            and sess.get("cookie"):
        session_id = sess["session_id"]
        cookie = sess["cookie"]
        _log(f"{case_id}: resuming session {session_id}")
    else:
        _log(f"{case_id}: submitting ({len(problem['text'])} chars)")
        create = _req("/api/run", {"text": problem["text"]}, timeout=120)
        if create.get("http_status") not in (200, 201, 202):
            return {"case_id": case_id, "outcome": "SUBMIT_FAILED",
                    "submit": {k: create.get(k) for k in
                               ("http_status", "error")}}
        body = create.get("body") or {}
        session_id = body.get("session_id") or body.get("id") or \
            body.get("run_id")
        if not session_id:
            return {"case_id": case_id, "outcome": "NO_SESSION_ID",
                    "submit_body_keys": list(body.keys())}
        cookie = create.get("set_cookie")
        SESSION.write_text(json.dumps({
            "case": case_id, "session_id": session_id, "cookie": cookie,
            "submitted_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                              time.gmtime())}))
        _log(f"{case_id}: session {session_id} "
             f"(cookie {'set' if cookie else 'ABSENT'})")

    result = _poll_slice(session_id, cookie, SLICE_POLL_S)
    if result.get("http_status") == "SLICE_DEADLINE":
        _log(f"{case_id}: slice deadline — RE-INVOKE to resume polling")
        return {"case_id": case_id, "outcome": "IN_FLIGHT",
                "session_id": session_id}
    if result.get("http_status") != 200:
        return {"case_id": case_id, "outcome": "RESULT_ENDPOINT_ERROR",
                "result": {k: result.get(k) for k in
                           ("http_status", "error")}}

    result_body = result.get("body") or {}
    _log(f"{case_id}: terminal status="
         f"{result_body.get('status')} final={result_body.get('final_status')}")

    # the async visual job settle window (only when the run produced
    # something renderable; honest no-op otherwise)
    time.sleep(POST_RUN_VISUAL_WAIT_S)

    cio_resp = _req(f"/api/run/{session_id}/cio", timeout=120, cookie=cookie)
    cio_body = cio_resp.get("body")
    model_resp = _model_bytes(session_id, cookie)
    visual = _visual_state(session_id, cookie)

    if cio_resp.get("http_status") == 200:
        (RUNS_DIR / f"{session_id}_cio.json").write_text(
            json.dumps(cio_body, indent=2))
    chain = _chain_record(problem, result_body, cio_body, cio_resp,
                          model_resp, visual, session_id)
    # the session cookie persisted per case (the R446-C1 precedent:
    # post-run probes — render re-checks, package fetches — present the
    # SAME owner cookie the original browser session held)
    chain["session_cookie"] = cookie
    SESSION.unlink(missing_ok=True)
    return chain


def main() -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    report = {"artifact_type": "R446-HF fresh production runs (Phases 8-9)",
              "base": BASE,
              "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                              time.gmtime()),
              "cases": []}
    if OUT.exists():
        try:
            prior = json.loads(OUT.read_text())
            report["started_at_utc"] = prior.get("started_at_utc")
            report["cases"] = prior.get("cases") or []
            if prior.get("finished_at_utc"):
                report["finished_at_utc"] = prior.get("finished_at_utc")
        except Exception:  # noqa: BLE001
            pass
    completed = [c.get("case_id") or ((c.get("problem") or {}).get(
        "case_id")) for c in report["cases"]
        if (c.get("case_id") or ((c.get("problem") or {}).get(
            "case_id"))) and c.get("outcome") not in (
                "IN_FLIGHT", "SUBMIT_FAILED")]
    for problem in CASES:
        if len(completed) >= len(CASES):
            break
        rec = _run_case(problem, report, completed)
        if rec:
            _key = _case_key(rec)
            report["cases"] = [c for c in report["cases"]
                               if _case_key(c) != _key]
            report["cases"].append(rec)
            OUT.write_text(json.dumps(report, indent=2))
            completed.append(_key)
            if rec.get("outcome") == "IN_FLIGHT":
                _log("stopping this slice (run in flight)")
                break
    done = [c for c in report["cases"]
            if _case_key(c) and c.get("outcome") != "IN_FLIGHT"]
    if len(done) >= len(CASES):
        report["finished_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                  time.gmtime())
        OUT.write_text(json.dumps(report, indent=2))
        _log(f"ALL {len(CASES)} CASES RECORDED -> {OUT}")
    else:
        _log(f"{len(done)}/{len(CASES)} recorded — re-invoke to continue")


if __name__ == "__main__":
    main()
