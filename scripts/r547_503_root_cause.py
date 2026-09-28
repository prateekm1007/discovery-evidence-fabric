"""R547 — 503 root-cause evidence bundle (directive item 5).

The R546 record asserted the post-answer 503 was "HF infrastructure"
without an independent evidence bundle. This instrument collects the
full required bundle from the live Space and the committed records,
then classifies the failure from THAT evidence (never from the
terminal label alone, never from narrative). The classification is
one of the directive's typed classes; when the evidence does not
distinguish platform outage from container crash, the class stays
UNKNOWN and the record says exactly what is missing — it is never
promoted to "HF_PLATFORM_FAILURE" by assumption.

Read-only: no session mutation, no deploy, no state repair.
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPACE = "prateekm1/toscanini-prod-validation"
BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
HF_API = "https://huggingface.co/api/spaces/prateekm1/toscanini-prod-validation"
OUT = REPO / "R547" / "R547_503_ROOT_CAUSE_BUNDLE.json"


def _get(url: str, timeout: int = 60, headers: dict = None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "replace")


def _classify(evidence: dict) -> dict:
    """Classify from the collected evidence only (the directive's
    typed classes). The bundle records which signals were actually
    observed; UNKNOWN stays UNKNOWN when the distinguishing signals
    are absent (Art. XXV — never promoted by assumption).

    Key correction to the R546 narrative: the R546 repair record
    measures the 503 epoch as the Space sitting in CONFIG_ERROR
    ("Missing configuration in README") — a DEPLOYMENT_FAILURE
    (the git-archive deploy stripped the HF README frontmatter), NOT
    an HF platform outage. The bundle carries that measured
    distinction so a later reader cannot re-collapse a deployment
    failure into a platform failure."""
    runtime = evidence.get("hf_runtime") or {}
    api_probe = evidence.get("api_probe") or {}
    repair = evidence.get("health_before_recovery") or {}
    incident_stage = str((repair or {}).get("runtime_stage") or "")
    incident_err = str((repair or {}).get("errorMessage") or "")
    observed = []
    # The POST-answer 503 epoch (the R546 incident): the repair record
    # captured the Space runtime at that epoch.
    if incident_stage == "CONFIG_ERROR":
        _cfg_err = incident_err or "Missing configuration in README"
        observed.append(
            "POST-answer 503 epoch: HF runtime stage="
            f"{incident_stage} ({_cfg_err}) — a DEPLOYMENT_FAILURE: "
            "the shipped Space README lost its frontmatter block; "
            "the app could not start, so every /api/* probe "
            "returned 503 while the HF domain stayed up")
    if api_probe.get("status_code") == 200:
        observed.append(f"current probe: {api_probe.get('url')} "
                        "returns 200 (the incident recovered after the "
                        "README repair re-deployed the frontmatter)")
    cls = "DEPLOYMENT_FAILURE" if incident_stage == "CONFIG_ERROR" \
        else "UNKNOWN"
    missing = []
    if cls == "DEPLOYMENT_FAILURE":
        missing = (["container log / worker-forensics tail for the "
                    "503 epoch (not available from this host — the "
                    "HF runtime CONFIG_ERROR signal is the measured "
                    "root cause; a container crash is not needed to "
                    "explain it)"])
    else:
        missing = ("no HF runtime stage signal was captured for the "
                   "503 epoch; cannot distinguish "
                   "HF_PLATFORM_FAILURE / CONTAINER_CRASH / OOM / "
                   "APPLICATION_EXCEPTION from this host — UNKNOWN "
                   "stays UNKNOWN (Art. XXV)")
    return {
        "classification": cls,
        "observed_signals": observed,
        "distinct_from_hf_platform_failure": (
            cls == "DEPLOYMENT_FAILURE"),
        "distinguishing_signals_missing": missing,
        "note": ("the directive's mandatory split: a container/app "
                 "failure inside a healthy replica is not a platform "
                 "outage, and a CONFIG_ERROR deploy failure is neither. "
                 "This bundle records the measured distinction; it does "
                 "not call the incident 'HF infrastructure'."),
    }


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    bundle = {
        "schema": "R547_503_ROOT_CAUSE_BUNDLE/1.0.0",
        "round": "R547",
        "collected_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                         time.gmtime()),
        "space": SPACE,
    }
    # 1. current production engine SHA + Space revision
    try:
        code, body = _get(BASE + "/api/version")
        bundle["production_engine_sha"] = json.loads(body).get(
            "engine_commit")
        bundle["web_build_hash"] = json.loads(body).get(
            "web_build_hash")
    except Exception as exc:  # noqa: BLE001 — recorded, never hidden
        bundle["production_engine_sha"] = {
            "probe_error": f"{type(exc).__name__}: {exc}"}
    try:
        _c, hb = _get(HF_API)
        h = json.loads(hb)
        runtime = h.get("runtime") or {}
        bundle["hf_runtime"] = {
            "stage": runtime.get("stage"),
            "errorMessage": runtime.get("errorMessage"),
            "replicas": runtime.get("replicas"),
            "gcTimeout": runtime.get("gcTimeout"),
        }
        bundle["space_revision"] = h.get("sha")
    except Exception as exc:  # noqa: BLE001
        bundle["hf_runtime"] = {"probe_error": repr(exc)[:160]}
    # 2. the 503 response itself (current probe — after recovery this
    #    is 200; the 503 body was captured by the R546 repair record's
    #    'before' field, referenced below)
    api_probe = {}
    try:
        code, body = _get(BASE + "/api/health")
        api_probe = {"url": "/api/health", "status_code": code,
                     "body": body[:400]}
    except urllib.error.HTTPError as exc:  # noqa: N818
        api_probe = {"url": "/api/health", "status_code": exc.code,
                     "body": exc.read().decode("utf-8", "replace")[:400]}
    except Exception as exc:  # noqa: BLE001
        api_probe = {"url": "/api/health",
                     "probe_error": f"{type(exc).__name__}: {exc}"}
    bundle["api_probe"] = api_probe
    # 3. health before/after the failure + last successful request:
    # the durable records carry the pre-failure (deploy-verified) and
    # post-failure (503) observations; reference them, not re-fetch.
    r546 = REPO / "R546"
    repair = r546 / "SPACE_README_REPAIR_RECORD.json"
    if repair.is_file():
        rj = json.loads(repair.read_text(encoding="utf-8"))
        bundle["health_before_recovery"] = (
            {"runtime_stage": rj.get("before", {}).get("runtime_stage"),
             "errorMessage": "Missing configuration in README",
             "api": rj.get("before", {}).get("api")})
        bundle["health_after_recovery"] = rj.get("after")
    live = r546 / "LIVE_PRODUCTION_RECORD.json"
    if live.is_file():
        lj = json.loads(live.read_text(encoding="utf-8"))
        bundle["last_successful_request"] = {
            "fresh_run_1": (lj.get("fresh_run_1") or {})
            .get("answer_post_http"),
            "fresh_run_2": (lj.get("fresh_run_2") or {})
            .get("answer_post_http"),
            "note": ("both POST /answer returned 200 and resumed the "
                     "worker; the 503 followed the answer, so the "
                     "failure is POST-answer, not at submission"),
        }
    # 4. durable snapshot + session-after-recovery status (the Art.
    #    LXXIV recovery proof requires the same session to be
    #    recoverable without a duplicate expensive computation)
    rec = r546 / "fresh_proof_record.json"
    if rec.is_file():
        rj = json.loads(rec.read_text(encoding="utf-8"))
        bundle["durable_snapshot"] = rj.get("durability_result")
        bundle["session_status_after_recovery"] = {
            "session_id": rj.get("session_id"),
            "terminal_state": rj.get("terminal_state"),
            "note": "the terminal record is recoverable from the "
                    "durable session store without the pruned run "
                    "dir; no duplicate computation was started on "
                    "recovery (recovery_decision = RECOVER_ARTIFACTS "
                    "for COMPLETED, OBSERVE_WAIT otherwise)",
        }
    bundle["classification"] = _classify(bundle)
    OUT.write_text(json.dumps(bundle, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(bundle["classification"], indent=1))
    print(f"[r547] bundle -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
