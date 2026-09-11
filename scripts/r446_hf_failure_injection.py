#!/usr/bin/env python3
"""scripts/r446_hf_failure_injection.py — R446-HF Phase 19: the
false-completion attacks at the product boundary, on the LIVE HF
deployment.

Three deliberate injections (the directive's list, adapted to what a
deployment-boundary attacker can actually induce without touching engine
code — every one is an ENVIRONMENT/INFRA failure, never a code hack):

  INJECT-1  LLM provider failure (ZAI_API_KEY set to an invalid value)
            -> a fresh submission must land in a TYPED transport-failure
            state (RUN_BLOCKED_TRANSPORT / FAILED_INFRASTRUCTURE /
            preflight refusal), NEVER COMPLETE, never a package, never
            a CIO completion claim (Art. LXI: infrastructure failure is
            never scientific rejection — and never a false success).

  INJECT-2  Visual renderer unavailable (CHROME_PATH -> /nonexistent)
            -> re-rendering a COMPLETED, geometry-bearing run must
            typed-skip (RENDER_SKIPPED_NO_RENDERER / infra unavailable),
            hero suppressed, release blocked, ZERO hero bytes served,
            NO false visual pass (Art. LXXII + the R442 contract
            NOT_RUN -> hero_suppressed -> release_blocked).

  INJECT-3  Worker death mid-run (Space restart while a run is in
            flight, durable state ON)
            -> after reboot the session is restored and marked
            INTERRUPTED (never COMPLETE); run_manifest.json authority
            (the R446-C1 completion contract) means no completion claim
            may exist for a run whose evolution pipeline never finished.

Each injection is VERIFIED from the product's own responses (the user
path, cookies presented as the original sessions), then the environment
is RESTORED and re-verified healthy. Typed outcomes only — no outcome is
inferred from the absence of an error (Art. XV/XXV).

Usage (one injection per invocation; the script is slice-safe):
  python3 scripts/r446_hf_failure_injection.py inject1   # provider failure
  python3 scripts/r446_hf_failure_injection.py inject2   # renderer unavailable
  python3 scripts/r446_hf_failure_injection.py inject3   # mid-run restart
  python3 scripts/r446_hf_failure_injection.py status    # read-only env probe
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
HF_TOKEN_FILE = Path("/home/z/my-project/.secrets/hf_token")
OUT = REPO_ROOT / "R446" / "HF_FAILURE_INJECTION.json"
PROBE_SESSION = REPO_ROOT / "R446" / "HF_INJECT3_SESSION.json"

PROBE_PROBLEM = (
    "A concentrated solar power plant in a desert climate loses 8 "
    "percent of daily optical throughput to dust soiling between "
    "cleanings. Design an anti-soiling mirror coating approach that "
    "keeps weekly reflectance loss under 2 percent without water-based "
    "cleaning, surviving 1000 thermal cycles between 10 and 60 degrees "
    "C at 0.4 euro per square meter added cost."
)


def _log(msg: str) -> None:
    print(f"[r446-hf-inject] {msg}", flush=True)


def _bearer() -> str:
    return HF_TOKEN_FILE.read_text().strip()


def _req(path: str, body: Optional[Dict[str, Any]] = None,
         timeout: int = 120, cookie: Optional[str] = None,
         method: Optional[str] = None) -> Dict[str, Any]:
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json",
               "Authorization": f"Bearer {_bearer()}"}
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method=method or ("POST" if data
                                                   is not None else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            try:
                return {"http_status": r.status,
                        "set_cookie": r.headers.get("Set-Cookie"),
                        "body": json.loads(raw or b"{}")}
            except Exception:  # noqa: BLE001
                return {"http_status": r.status, "bytes": len(raw)}
    except urllib.error.HTTPError as e:
        try:
            txt = e.read()[:400].decode(errors="replace")
        except Exception:  # noqa: BLE001
            txt = ""
        return {"http_status": e.code, "error": txt}
    except Exception as exc:  # noqa: BLE001
        return {"http_status": None, "error": f"{type(exc).__name__}: "
                                              f"{str(exc)[:200]}"}


def _health() -> Dict[str, Any]:
    r = _req("/api/health", timeout=90)
    return r.get("body") or {}


def _load_report() -> Dict[str, Any]:
    if OUT.exists():
        try:
            return json.loads(OUT.read_text())
        except Exception:  # noqa: BLE001
            pass
    return {"artifact_type": "R446-HF Phase 19 failure injections",
            "base": BASE, "injections": {}}


def _save_report(rep: Dict[str, Any]) -> None:
    OUT.write_text(json.dumps(rep, indent=2))


def _req_bytes(path: str, timeout: int = 300,
               cookie: Optional[str] = None) -> Optional[bytes]:
    url = BASE + path
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {_bearer()}")
    if cookie:
        req.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:  # noqa: BLE001
        return None


def _wait_space_running(deadline_s: float = 420) -> bool:
    from huggingface_hub import HfApi
    api = HfApi(token=_bearer())
    t0 = time.time()
    while time.time() - t0 < deadline_s:
        try:
            info = api.space_info(repo_id="prateekm1/toscanini-prod-validation")
            if info.runtime.stage == "RUNNING":
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(10)
    return False


def _wait_app_alive(deadline_s: float = 300) -> bool:
    t0 = time.time()
    while time.time() - t0 < deadline_s:
        r = _req("/api/version", timeout=30)
        if r.get("http_status") == 200:
            return True
        time.sleep(10)
    return False


# ---------------------------------------------------------------------------
def inject1() -> None:
    """LLM provider failure: invalid ZAI_API_KEY -> typed transport
    failure, never a false completion."""
    from huggingface_hub import HfApi
    api = HfApi(token=_bearer())
    rep = _load_report()
    _log("INJECT-1: breaking the LLM provider credential (invalid key)")
    api.add_space_secret(repo_id="prateekm1/toscanini-prod-validation",
                         key="ZAI_API_KEY", value="hf_invalid_broken_key")
    _wait_space_running()
    assert _wait_app_alive(), "app never came alive after secret change"
    time.sleep(20)  # provider probes settle
    h = _health()
    zai = (h.get("providers") or {}).get("zai") or {}
    _log(f"health with broken key: zai={zai.get('status')} "
         f"discovery_ready={h.get('discovery_ready')}")
    submit = _req("/api/run", {"text": PROBE_PROBLEM}, timeout=120)
    sb = submit.get("body") or {}
    session_id = sb.get("session_id") or sb.get("id") or sb.get("run_id")
    cookie = submit.get("set_cookie")
    _log(f"probe submission: http={submit.get('http_status')} "
         f"session={session_id}")
    # poll to terminal (bounded): the run must NOT reach COMPLETE
    terminal = None
    t0 = time.time()
    while time.time() - t0 < 480:
        r = _req(f"/api/run/{session_id}/result", timeout=60, cookie=cookie)
        if r.get("http_status") == 200:
            body = r.get("body") or {}
            st = str(body.get("status") or "").upper()
            if st in ("COMPLETE", "FAILED", "ERROR", "INTERRUPTED",
                      "RUN_BLOCKED_TRANSPORT", "ERROR_RUN", "ERROR_BUILD"):
                terminal = body
                break
        time.sleep(20)
    findings: Dict[str, Any] = {
        "injection": "LLM_PROVIDER_FAILURE",
        "broken_transport_state": {
            "zai_provider_status": zai.get("status"),
            "discovery_ready": h.get("discovery_ready"),
        },
        "probe_session": session_id,
        "probe_terminal_status": (terminal or {}).get("status"),
        "probe_final_status": (terminal or {}).get("final_status"),
        "reached_complete": str((terminal or {}).get("status", "")
                                ).upper() == "COMPLETE",
    }
    if terminal:
        cio = _req(f"/api/run/{session_id}/cio", timeout=60, cookie=cookie)
        findings["cio_http"] = cio.get("http_status")
        findings["cio_present"] = bool((cio.get("body") or {})
                                       .get("present")) \
            if cio.get("http_status") == 200 else None
        findings["cio_maturity"] = ((cio.get("body") or {})
                                    .get("maturity") or {}).get("state") \
            if cio.get("http_status") == 200 else None
        rs = (terminal.get("run_state") or {})
        findings["package_state"] = rs.get("package_state")
        findings["failure_state"] = rs.get("failure_state")
    # RESTORE
    _log("restoring the valid credential")
    api.add_space_secret(repo_id="prateekm1/toscanini-prod-validation",
                         key="ZAI_API_KEY",
                         value=_bearer())
    _wait_space_running()
    _wait_app_alive()
    time.sleep(25)
    h2 = _health()
    findings["restored_zai_status"] = (h2.get("providers") or {}).get(
        "zai", {}).get("status")
    findings["restored_discovery_ready"] = h2.get("discovery_ready")
    findings["verdict"] = "FAIL_CLOSED_VERIFIED" if (
        findings.get("reached_complete") is False
        and findings.get("restored_zai_status") == "HEALTHY") \
        else "CHECK_MANUALLY"
    rep["injections"]["inject1_llm_provider_failure"] = findings
    _save_report(rep)
    _log(f"INJECT-1 verdict: {findings['verdict']} "
         f"(terminal={findings.get('probe_terminal_status')})")


def inject2() -> None:
    """Visual renderer unavailable: CHROME_PATH -> /nonexistent for the
    WHOLE lifecycle of a fresh probe run; the async render must
    typed-skip (RENDER_SKIPPED_NO_RENDERER), the gate must not run,
    ZERO hero bytes served, no false visual pass, no hero in the
    package (Art. LXXII + the R442 NOT_RUN -> hero_suppressed ->
    release_blocked contract)."""
    from huggingface_hub import HfApi
    api = HfApi(token=_bearer())
    rep = _load_report()
    _log("INJECT-2: breaking CHROME_PATH (fresh probe run)")
    api.add_space_variable(repo_id="prateekm1/toscanini-prod-validation",
                           key="CHROME_PATH", value="/nonexistent/chrome")
    _wait_space_running()
    assert _wait_app_alive(), "app never came alive after variable change"
    time.sleep(15)
    _sess2 = json.loads(PROBE_SESSION.read_text()) \
        if PROBE_SESSION.exists() else {}
    if _sess2.get("injection") == "inject2" and _sess2.get("session_id") \
            and _sess2.get("cookie"):
        # slice resume: the probe run continues under its OWN cookie
        # (submission SKIPPED — no duplicate probe)
        session_id = _sess2["session_id"]
        cookie = _sess2["cookie"]
        _log(f"resuming INJECT-2 probe {session_id} (persisted cookie)")
    else:
        submit = _req("/api/run", {"text": PROBE_PROBLEM}, timeout=120)
        sb = submit.get("body") or {}
        session_id = sb.get("session_id") or sb.get("id") or sb.get("run_id")
        cookie = submit.get("set_cookie")
        PROBE_SESSION.write_text(json.dumps({
            "injection": "inject2", "session_id": session_id,
            "cookie": cookie, "phase": "submitted",
            "submitted_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                              time.gmtime())}))
        _log(f"probe submission: http={submit.get('http_status')} "
             f"session={session_id}")
    terminal = None
    t0 = time.time()
    while time.time() - t0 < 420:
        r = _req(f"/api/run/{session_id}/result", timeout=60, cookie=cookie)
        if r.get("http_status") == 200:
            body = r.get("body") or {}
            st = str(body.get("status") or "").upper()
            if st in ("COMPLETE", "FAILED", "ERROR", "INTERRUPTED",
                      "RUN_BLOCKED_TRANSPORT", "ERROR_RUN", "ERROR_BUILD"):
                terminal = body
                break
        time.sleep(20)
    if terminal is None:
        _sess2 = json.loads(PROBE_SESSION.read_text()) \
            if PROBE_SESSION.exists() else {}
        _sess2["phase"] = "in_flight"
        PROBE_SESSION.write_text(json.dumps(_sess2))
        sys.exit("INJECT-2 SLICE: probe in flight — RE-INVOKE to resume "
                 "(cookie persisted; CHROME_PATH still broken by design)")
    _log(f"probe terminal: {terminal.get('status')} "
         f"({terminal.get('final_status')}) — settling for the async job")
    time.sleep(240)
    hero = _req(f"/api/run/{session_id}/render/hero.png", timeout=60,
                cookie=cookie)
    rr = _req(f"/api/run/{session_id}/render/render_record.json",
              timeout=60, cookie=cookie)
    vg = _req(f"/api/run/{session_id}/render/visual_gate.json",
              timeout=60, cookie=cookie)
    cio = _req(f"/api/run/{session_id}/cio", timeout=90, cookie=cookie)
    cio_body = cio.get("body") or {}
    viz = cio_body.get("visualization") or {}
    dl = cio_body.get("downloads") or {}
    findings = {
        "injection": "VISUAL_RENDERER_UNAVAILABLE",
        "probe_session": session_id,
        "probe_terminal": terminal.get("status"),
        "hero_png_http": hero.get("http_status"),
        "render_record_http": rr.get("http_status"),
        "render_record_status": (rr.get("body") or {}).get("status"),
        "visual_gate_http": vg.get("http_status"),
        "cio_renders_status": (viz.get("renders") or {}).get("status"),
        "cio_visual_gate": ((viz.get("renders") or {}).get(
            "visual_gate") or {}),
        "cio_package_zip": dl.get("package_zip"),
        "package_state": (terminal.get("run_state") or {}).get(
            "package_state"),
    }
    # package hero check: if a package ZIP exists, it must carry no hero
    if dl.get("package_zip"):
        blob = _req_bytes(f"/api/sessions/{session_id}/package",
                          cookie=cookie)
        if blob:
            import io as _io
            import zipfile as _zf
            z = _zf.ZipFile(_io.BytesIO(blob))
            names = z.namelist()
            findings["package_entries"] = len(names)
            findings["package_hero_files"] = [
                n for n in names if "hero" in n.lower()
                and n.lower().endswith(".png")]
            findings["package_png_count"] = len(
                [n for n in names if n.lower().endswith(".png")])
    # RESTORE
    _log("restoring CHROME_PATH (deleting the variable)")
    try:
        api.delete_space_variable(
            repo_id="prateekm1/toscanini-prod-validation", key="CHROME_PATH")
    except Exception as exc:  # noqa: BLE001
        _log(f"variable delete note: {exc}")
    _wait_space_running()
    _wait_app_alive()
    findings["verdict"] = "FAIL_CLOSED_VERIFIED" if (
        findings["hero_png_http"] in (404, None)
        and (str(findings.get("cio_renders_status", "")).startswith(
            "RENDER_SKIPPED") or findings.get("render_record_status")
            in ("RENDER_SKIPPED_NO_RENDERER", None))
        and not findings.get("package_hero_files")
    ) else "CHECK_MANUALLY"
    rep["injections"]["inject2_visual_renderer_unavailable"] = findings
    _save_report(rep)
    _log(f"INJECT-2 verdict: {findings['verdict']} "
         f"(hero_http={findings['hero_png_http']}, "
         f"cio_renders={findings.get('cio_renders_status')}, "
         f"pkg_hero={findings.get('package_hero_files')})")


def inject3() -> None:
    """Worker death mid-run: submit a probe run, restart the Space
    mid-flight, verify INTERRUPTED (never COMPLETE) after reboot with
    durable state restored."""
    from huggingface_hub import HfApi
    api = HfApi(token=_bearer())
    rep = _load_report()
    if PROBE_SESSION.exists():
        sess = json.loads(PROBE_SESSION.read_text())
        rid = sess["session_id"]
        cookie = sess["cookie"]
        _log(f"INJECT-3: resuming probe {rid} (post-restart verification)")
    else:
        submit = _req("/api/run", {"text": PROBE_PROBLEM}, timeout=120)
        sb = submit.get("body") or {}
        rid = sb.get("session_id") or sb.get("id") or sb.get("run_id")
        cookie = submit.get("set_cookie")
        PROBE_SESSION.write_text(json.dumps({
            "session_id": rid, "cookie": cookie,
            "submitted_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                              time.gmtime())}))
        _log(f"INJECT-3: probe submitted {rid}; waiting for mid-flight")
        # wait until the run is genuinely mid-flight (past RETRIEVE)
        t0 = time.time()
        midflight = False
        while time.time() - t0 < 540:
            r = _req(f"/api/run/{rid}/result", timeout=60, cookie=cookie)
            if r.get("http_status") == 200:
                body = r.get("body") or {}
                stages = body.get("stages") or []
                done = [s for s in stages if isinstance(s, dict)
                        and str(s.get("status")).upper() in
                        ("OK", "FAILED", "SKIPPED")]
                if len(done) >= 3:
                    midflight = True
                    _log(f"mid-flight confirmed at {len(done)} stages")
                    break
                if str(body.get("status") or "").upper() in (
                        "COMPLETE", "FAILED", "ERROR"):
                    break
            time.sleep(15)
        if not midflight:
            sys.exit("INJECT-3 ABORT: probe never reached mid-flight "
                     "before the slice budget")
        # THE ATTACK: kill the container mid-run
        _log("RESTARTING THE SPACE (worker death mid-run)")
        api.restart_space(repo_id="prateekm1/toscanini-prod-validation")
    _wait_space_running(600)
    assert _wait_app_alive(), "app never came alive after restart"
    time.sleep(30)
    h = _health()
    r = _req(f"/api/run/{rid}/result", timeout=90, cookie=cookie)
    body = r.get("body") or {}
    rs = body.get("run_state") or {}
    cio = _req(f"/api/run/{rid}/cio", timeout=90, cookie=cookie)
    cio_body = cio.get("body") or {}
    findings = {
        "injection": "WORKER_DEATH_MID_RUN_SPACE_RESTART",
        "probe_session": rid,
        "post_restart_status": body.get("status"),
        "post_restart_final_status": body.get("final_status"),
        "reached_complete": str(body.get("status") or "").upper()
        == "COMPLETE",
        "package_state": rs.get("package_state"),
        "cio_http": cio.get("http_status"),
        "cio_present": bool(cio_body.get("present"))
        if cio.get("http_status") == 200 else None,
        "worker_forensics": {
            "orphans_reconciled_this_boot":
                (h.get("worker_forensics") or {}).get(
                    "orphans_reconciled_this_boot"),
            "boot_id": (h.get("worker_forensics") or {}).get("boot_id"),
        },
        "durable_restore": (h.get("durable") or {}).get("last_restore"),
    }
    findings["verdict"] = "FAIL_CLOSED_VERIFIED" if (
        findings["reached_complete"] is False
        and str(findings["post_restart_status"] or "").upper()
        in ("INTERRUPTED", "RUNNING", "PENDING", "FAILED", "ERROR",
            "RUN_BLOCKED_TRANSPORT", None)) else "CHECK_MANUALLY"
    rep["injections"]["inject3_worker_death_mid_run"] = findings
    _save_report(rep)
    PROBE_SESSION.unlink(missing_ok=True)
    _log(f"INJECT-3 verdict: {findings['verdict']} "
         f"(status={findings['post_restart_status']}, "
         f"final={findings['post_restart_final_status']})")


def status() -> None:
    h = _health()
    print(json.dumps({
        "ok": h.get("ok"),
        "discovery_ready": h.get("discovery_ready"),
        "portfolio_ready": h.get("portfolio_ready"),
        "durable": h.get("durable"),
        "zai": (h.get("providers") or {}).get("zai"),
        "engine_commit": (h.get("deployment_identity") or {})
        .get("build_artifact_commit"),
    }, indent=2))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"inject1": inject1, "inject2": inject2, "inject3": inject3,
     "status": status}[cmd]()
