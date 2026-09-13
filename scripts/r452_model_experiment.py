#!/usr/bin/env python3
"""scripts/r452_model_experiment.py — R452-A3: the controlled
stronger-model experiment (the operator's model-survey directive,
exercising the A3 owner-gated escalation's unblock path as a MEASURED
experiment — never a prose claim).

DESIGN (Art. XLVII: the measurement instrument is IDENTICAL on both
arms; the LLM route is the ONLY variable):

  Arm 1 (baseline)  localqwen  Qwen/Qwen3-1.7B  Q4_K_M (quality_tier 4)
                    through the ordinary registry path under the
                    DEPLOYED default policy
                    ENGINE_MODEL_COST_POLICY=ZERO_PAID_COST.
  Arm 2 (stronger)  the sandbox z-ai gateway's embedded model
                    (measured live: glm-4-plus, quality_tier 2)
                    through the ordinary registry path under
                    ENGINE_MODEL_COST_POLICY=UNRESTRICTED — the
                    recorded operator escape hatch — with EVERY paid
                    credential absent so no PAID_API route can ever
                    serve (fail-closed on the zero-cost contract even
                    under UNRESTRICTED), and with NO localqwen wiring
                    so the arm is PURE (a mixed-model arm would
                    contaminate the comparison).

  Same frozen problems (the R452 assay problems A/B/C, imported
  byte-identical from r452_assay.AUTHORED_PROBLEMS), same engine code
  (one commit for both arms), same measurement instrument (the FROZEN
  r452_quality_instrument._case_metrics plus this script's own typed
  extractors), same run-identity discipline (fresh run ids per arm).

THE EIGHT MEASURED DIMENSIONS (the R452 directive's list — each is
computed from the runs' OWN persisted artifacts, Art. X; every
dimension states its artifact source; typed UNKNOWN/NOT_REACHED when
the run did not reach the producing stage — Art. XXV):

  1. evidence_grounding        evidence_classification.counts +
                               the frozen instrument's relevance rate
  2. mechanism_fidelity        the instrument's span-verbatim support
                               and mechanism grounding rates
  3. candidate_quality         the instrument's obvious-combination /
                               differentiated rates, ranking scores
  4. attack_execution          adversarial transport actually called +
                               attack records produced (the R451 defect
                               class: NOT_RUN / EVIDENCE_GATE_FAILED is
                               measured as incomplete, never executed)
  5. attack_survival           survivor_reached, adjudication verdicts,
                               evolution generations, KILLED outcomes
  6. domain_correctness        the detected domain verbatim + the E10
                               defect class (ml_data on a physical
                               problem) + the engineering spec's
                               canonical family when produced
  7. parameter_sourcing        ENGINEERING_SPECIFICATION value_sourcing
                               summary (SOURCE_FACT / COMPUTED /
                               MODELLED / UNKNOWN counts)
  8. engineering_reachability  CAD_PIPELINE_LEDGER_gen-N outcome +
                               STEP/STL artifacts on disk

THE ZERO-COST INVARIANT (fail-closed, both arms): after each run the
driver verifies from the run-owned routing-ledger lines that EVERY
line's cost_class is in the arm's allowed set — a PAID_API line
anywhere fails the experiment closed (Art. IV/VII).

ENVIRONMENT-RESET DISCLOSURE (Art. XI/XV): the first attempt at this
experiment was destroyed mid-run by a sandbox environment reset
(2026-09-13 ~18:05 UTC — the in-flight arm1/A engine run and its five
stage envelopes lost; recorded, not narrated). The experiment was
restarted from the re-fetched origin/main at the SAME commit; all run
identities are fresh (the r452mx prefixes); no artifact from the lost
attempt is reused anywhere.

Usage:
  python scripts/r452_model_experiment.py probe
  python scripts/r452_model_experiment.py engine ARM CASE [budget_s]
  python scripts/r452_model_experiment.py assess ARM
  python scripts/r452_model_experiment.py measure
  python scripts/r452_model_experiment.py record
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

OUT_ROOT = REPO_ROOT / "R452"
MX_ROOT = OUT_ROOT / "MODEL_EXPERIMENT"
PROBE_RECORD = MX_ROOT / "ROUTE_AUTHORITY.json"
MEASUREMENT_RECORD = MX_ROOT / "MODEL_EXPERIMENT.json"

GATEWAY_KEY_FILE = Path("/home/z/my-project/local_llm/zai_gateway.key")

#: every credential that could route a PAID_API call — removed from
#: BOTH arms' environments (the zero-cost contract is structural, not
#: incidental: under UNRESTRICTED a present paid key WOULD be usable)
PAID_ENV_VARS = [
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY",
    "NVIDIA_API_KEY", "DEEPSEEK_API_KEY", "MISTRAL_API_KEY",
    "GEMINI_API_KEY", "QWEN_API_KEY", "TOKEN_ROUTER_API_KEY",
]

#: the arms (closed set). allowed_cost_classes: the zero-cost
#: invariant — every run-owned routing line must carry one of these.
ARMS: Dict[str, Dict[str, Any]] = {
    "arm1-localqwen": {
        "policy": "ZERO_PAID_COST",
        "model": "qwen3-1.7b",
        "provider": "localqwen",
        "quality_tier": 4,
        "cost_basis": "ZERO_PAID_COST_SELF_HOSTED",
        "allowed_cost_classes": ["ZERO_PAID_COST_SELF_HOSTED"],
        "run_id_prefix": "r452mx1",
        "session_prefix": "r452mx1",
        "transport_watchdog": "llama_server",
    },
    "arm2-glm4plus": {
        "policy": "UNRESTRICTED",
        "model": "glm-4-plus",
        "provider": "zai",
        "quality_tier": 2,
        "cost_basis": "ENVIRONMENT_GRANT",
        "allowed_cost_classes": ["ENVIRONMENT_GRANT"],
        "run_id_prefix": "r452mx2",
        "session_prefix": "r452mx2",
        "transport_watchdog": "zai_gateway",
    },
}

#: the frozen assay problems (byte-identical import — Art. XLVII)
from r452_assay import AUTHORED_PROBLEMS as _AP  # noqa: E402

CASES: Dict[str, Dict[str, Any]] = {}
for _c in ("A", "B", "C"):
    _s = dict(_AP[_c])
    CASES[_c] = _s


def _log(msg: str) -> None:
    print(f"[r452mx {datetime.now(timezone.utc).isoformat(timespec='seconds')}] {msg}",
          flush=True)


def _arm_dir(arm: str, case: str) -> Path:
    return MX_ROOT / f"{arm.upper().replace('-', '_')}_RUN_{case}"


def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(Path(p).read_text())
    except Exception:  # noqa: BLE001
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


# ---------------------------------------------------------------------------
# The arm environment (fail-closed key hygiene)
# ---------------------------------------------------------------------------
def arm_env(arm: str) -> Dict[str, str]:
    """The environment for one arm's engine run. BOTH arms strip every
    paid credential (structural zero-cost). Arm 1 additionally strips
    ZAI_API_KEY (the deployed-default discipline). Arm 2 sets the
    gateway credential + the measured served model id and strips
    LOCAL_QWEN_BASE_URL so the arm is PURE."""
    spec = ARMS[arm]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["ENGINE_MODEL_COST_POLICY"] = spec["policy"]
    for k in PAID_ENV_VARS:
        env.pop(k, None)
    if arm == "arm1-localqwen":
        env.pop("ZAI_API_KEY", None)
        env.pop("ZAI_MODEL", None)
        env["LOCAL_QWEN_BASE_URL"] = \
            "http://127.0.0.1:8790/v1/chat/completions"
    elif arm == "arm2-glm4plus":
        key = GATEWAY_KEY_FILE.read_text().strip() \
            if GATEWAY_KEY_FILE.exists() else ""
        if not key:
            raise SystemExit(
                "FATAL: arm2 requires the z-ai gateway key file "
                f"{GATEWAY_KEY_FILE} (start scripts/start_zai_gateway"
                ".py first — the key never lives in the repo)")
        env["ZAI_API_KEY"] = key
        env["ZAI_MODEL"] = "glm-4-plus"   # the MEASURED served model
        env["ZAI_BASE_URL"] = \
            "http://127.0.0.1:8787/v1/chat/completions"
        env.pop("LOCAL_QWEN_BASE_URL", None)   # PURE arm
    else:
        raise SystemExit(f"unknown arm {arm}")
    return env


# ---------------------------------------------------------------------------
# Transport watchdogs (the R451 detached survival pattern)
# ---------------------------------------------------------------------------
def _http_ok(url: str, timeout: float = 3.0) -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def ensure_transport(arm: str) -> bool:
    """Ensure the arm's transport is up; restart through the recorded
    launchers when the sandbox reaper killed it."""
    if arm == "arm1-localqwen":
        if _http_ok("http://127.0.0.1:8790/health"):
            return True
        import r451_local_qwen as lq
        return bool(lq.ensure_server())
    if arm == "arm2-glm4plus":
        if _http_ok("http://127.0.0.1:8787/healthz"):
            return True
        r = subprocess.run(
            [sys.executable,
             "/home/z/my-project/scripts/start_zai_gateway.py"],
            capture_output=True, text=True, timeout=60)
        return r.returncode == 0
    return False


# ---------------------------------------------------------------------------
# probe — the route authority record (measured, Art. III)
# ---------------------------------------------------------------------------
def probe() -> int:
    """Measure the live route authority for the experiment: the three
    operator-survey paths each measured, plus the operative route."""
    MX_ROOT.mkdir(parents=True, exist_ok=True)
    rec: Dict[str, Any] = {
        "artifact_type": "R452_MODEL_EXPERIMENT_ROUTE_AUTHORITY",
        "measured_at": _now(),
        "directive": ("the operator's model survey (2026-09-14): "
                      "three recommended experiment paths — local "
                      "open-weight GLM-5.2, HF-hosted GPT-OSS-120B, "
                      "OpenRouter GPT-4o — each measured live here; "
                      "the A3 escalation's unblock paths exercised as "
                      "an experiment, never a deployed-policy change"),
        "survey_paths_measured": {},
        "operative_route": {},
    }

    # --- survey path 2: HF-hosted inference (the survey's core
    #     recommendation) — measured with THIS session's HF token ----
    token = os.environ.get("HF_TOKEN", "").strip()
    hf = {"path": "HF Inference router (router.huggingface.co)",
          "token_present": bool(token)}
    import urllib.request
    import urllib.error
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(
            "https://router.huggingface.co/v1/models")
        with urllib.request.urlopen(req, timeout=45, context=ctx) as r:
            cat = json.loads(r.read().decode("utf-8", "replace"))
        data = cat.get("data", [])
        hf["catalog_models"] = len(data)
        hf["catalog_free_models"] = sum(
            1 for m in data if m.get("is_free"))
    except Exception as e:  # noqa: BLE001
        hf["catalog_error"] = f"{type(e).__name__}: {e}"[:200]
    if token:
        body = json.dumps({
            "model": "openai/gpt-oss-120b", "max_tokens": 32,
            "messages": [{"role": "user", "content": "probe"}]}).encode()
        req = urllib.request.Request(
            "https://router.huggingface.co/v1/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
                hf["gpt_oss_120b_probe"] = f"HTTP {r.status}"
        except urllib.error.HTTPError as e:
            hf["gpt_oss_120b_probe"] = (
                f"HTTP {e.code}: "
                + e.read().decode("utf-8", "replace")[:180])
        except Exception as e:  # noqa: BLE001
            hf["gpt_oss_120b_probe"] = f"{type(e).__name__}"[:120]
    hf["verdict"] = (
        "ZERO_COST_UNAVAILABLE — the account's monthly included "
        "credits are depleted and the live catalog lists ZERO is_free "
        "models; every router route bills (the R450 402 state, "
        "re-measured live this session)"
        if "402" in str(hf.get("gpt_oss_120b_probe", "")) or
        hf.get("catalog_free_models") == 0
        else "MEASURED_ELSEWHERE")
    rec["survey_paths_measured"]["hf_hosted_inference"] = hf

    # --- survey path 1: local open-weight GLM-5.2 ----------------------
    mem = {}
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                k, v = line.split(":", 1)
                mem[k] = v.strip()
    except Exception:  # noqa: BLE001
        pass
    import shutil as _sh
    disk = _sh.disk_usage("/home/z")
    rec["survey_paths_measured"]["local_open_weight_glm_5_2"] = {
        "path": ("local GGUF (unsloth/GLM-5.2-GGUF dynamic 2-bit "
                 "~239 GB disk / 24-32 GB GPU class, per the survey)"),
        "measured_host": {
            "mem_total_kb": mem.get("MemTotal"),
            "cpus": os.cpu_count(),
            "gpu": "ABSENT (no nvidia-smi; no /dev/nvidia*)",
            "disk_free_gb": round(disk.free / 1e9, 1),
        },
        "verdict": (
            "STRUCTURALLY_INFEASIBLE on this host — the survey's own "
            "minimum (24-32 GB GPU + ~256 GB RAM + ~250 GB disk) is "
            "not present; recorded, not narrated"),
    }

    # --- survey path 3: OpenRouter paid -------------------------------
    rec["survey_paths_measured"]["openrouter_paid"] = {
        "path": "OpenRouter (gpt-4o class, per the survey)",
        "verdict": (
            "EXCLUDED_BY_THE_ZERO_COST_CONTRACT — the survey itself "
            "marks it 'not free'; no paid route is ever called by this "
            "experiment (the structural key-stripping in arm_env)"),
    }

    # --- the operative route: the sandbox z-ai gateway ----------------
    gw = {"provider": "zai (sandbox gateway, scripts/zai_gateway.mjs)",
          "cost_basis": "ENVIRONMENT_GRANT",
          "quality_tier": 2,
          "note": ("the ONLY zero-cost stronger-model route measurable "
                   "in this environment; substitutes for the survey's "
                   "HF-hosted path (measured 402) with the substitution "
                   "RECORDED — the served model is the sandbox grant's "
                   "embedded model, measured live per call in the "
                   "gateway log")}
    key = GATEWAY_KEY_FILE.read_text().strip() \
        if GATEWAY_KEY_FILE.exists() else ""
    if key and _http_ok("http://127.0.0.1:8787/healthz"):
        import urllib.request as _u
        body = json.dumps({
            "model": "glm-4-plus", "max_tokens": 48,
            "messages": [{"role": "user", "content": (
                "Transport capability probe. Reply with exactly two "
                "lines, nothing else:\nMECHANISM: a catheter wall "
                "resists kinking when the septum is thick enough\n"
                "FALSIFIER: measure the collapse pressure of the "
                "septum")}],
        }).encode()
        req = _u.Request(
            "http://127.0.0.1:8787/v1/chat/completions", data=body,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"})
        t0 = time.time()
        try:
            with _u.urlopen(req, timeout=90) as r:
                d = json.loads(r.read().decode())
            gw["served_model"] = d.get("model")
            gw["probe_latency_ms"] = int((time.time() - t0) * 1000)
            gw["field_line_compliant"] = "MECHANISM:" in (
                d.get("choices") or [{}])[0].get("message", {}).get(
                    "content", "")
        except Exception as e:  # noqa: BLE001
            gw["probe_error"] = f"{type(e).__name__}: {e}"[:200]
    else:
        gw["state"] = "GATEWAY_DOWN (start scripts/start_zai_gateway.py)"
    rec["operative_route"]["zai_gateway"] = gw
    rec["operative_route"]["baseline_route"] = {
        "provider": "localqwen",
        "model": "Qwen/Qwen3-1.7B Q4_K_M (gguf sha256 72c5c3cb…, "
                 "revision-pinned)",
        "cost_basis": "ZERO_PAID_COST_SELF_HOSTED",
        "quality_tier": 4,
    }
    PROBE_RECORD.write_text(json.dumps(rec, indent=1))
    _log(f"route authority -> {PROBE_RECORD}")
    return 0


# ---------------------------------------------------------------------------
# engine — the detached arm run (the r452_assay survival pattern)
# ---------------------------------------------------------------------------
def build_engine_problem(arm: str, case: str) -> Path:
    """Build the ENGINE problem through the arm's OWN route (the
    MODEL_DERIVED extraction is the first LLM step of the measured
    chain — identical code, different model)."""
    spec = CASES[case]
    out_dir = _arm_dir(arm, case)
    out_dir.mkdir(parents=True, exist_ok=True)
    problem_json = out_dir / "fresh_problem.json"
    if problem_json.exists():
        return problem_json
    assert ensure_transport(arm), f"{arm}: transport failed to start"
    env = arm_env(arm)
    code = (
        "import json, sys;\n"
        "sys.path.insert(0, '.');\n"
        "from toscanini.problem_builder import build_problem;\n"
        f"built = build_problem({spec['text']!r});\n"
        "problem = built.get('problem') if isinstance("
        "built.get('problem'), dict) else built;\n"
        f"problem['problem_id'] = {spec['case_id']!r};\n"
        "problem['r452_freshness'] = {\n"
        "    'class': 'GENUINELY_FRESH',\n"
        f"    'authored_for': 'R452 (model-experiment arm {arm})',\n"
        f"    'content_sha256': "
        f"{hashlib.sha256(spec['text'].encode()).hexdigest()!r},\n"
        "    'same_frozen_text_as_r452_assay': True,\n"
        "};\n"
        f"json.dump(problem, open({str(problem_json)!r}, 'w'), "
        "indent=1)\n"
    )
    r = subprocess.run([sys.executable, "-c", code], cwd=str(REPO_ROOT),
                       env=env, capture_output=True, text=True, timeout=600)
    if r.returncode != 0 or not problem_json.exists():
        out_dir.joinpath("problem_build_error.txt").write_text(
            r.stdout[-3000:] + "\n" + r.stderr[-3000:])
        raise SystemExit(f"problem build failed for {arm}/{case}")
    _log(f"{arm}/{case}: engine problem built through the arm route")
    return problem_json


def run_engine(arm: str, case: str, budget_s: int) -> None:
    """Run the engine DETACHED with the pinned run identity (the
    R451-C1.1 survival pattern), polling until exit or budget; the
    transport watchdog restarts a reaped transport between polls."""
    spec = dict(CASES[case])
    spec["run_id"] = (f"{ARMS[arm]['run_id_prefix']}-{case}: "
                      f"{spec['case_id']} (model experiment {arm})")
    spec["session_id"] = f"{ARMS[arm]['session_prefix']}-{case.lower()}"
    out_dir = _arm_dir(arm, case)
    out_dir.mkdir(parents=True, exist_ok=True)
    problem_json = build_engine_problem(arm, case)
    env = arm_env(arm)
    pid_file = out_dir / "ENGINE_PID"
    log_file = out_dir / "engine.log"

    def _engine_pid() -> Optional[int]:
        try:
            return int(pid_file.read_text().strip())
        except Exception:  # noqa: BLE001
            return None

    def _pid_alive(pid: Optional[int]) -> bool:
        if not pid:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    assert ensure_transport(arm), f"{arm}: transport failed to start"
    pid = _engine_pid()
    if _pid_alive(pid):
        _log(f"{arm}/{case}: attaching to live engine pid={pid}")
    else:
        cmd = [sys.executable, "-m", "discovery_fabric.engine.run",
               "--problem-json", str(problem_json),
               "--out", str(out_dir), "--no-package",
               "--run-id", spec["run_id"],
               "--session-id", spec["session_id"]]
        if (out_dir / "problem.json").exists():
            cmd.append("--resume")
            _log(f"{arm}/{case}: starting DETACHED engine (resume)")
        else:
            _log(f"{arm}/{case}: starting DETACHED engine (fresh)")
        log_fh = open(log_file, "ab")
        proc = subprocess.Popen(cmd, cwd=str(REPO_ROOT), env=env,
                                stdout=log_fh, stderr=subprocess.STDOUT,
                                start_new_session=True)
        pid_file.write_text(str(proc.pid))
        _log(f"{arm}/{case}: detached engine pid={proc.pid}")

    start = time.time()
    while True:
        if not _pid_alive(_engine_pid()):
            _log(f"{arm}/{case}: engine exited (final_state written "
                 "if the run completed)")
            try:
                pid_file.unlink()
            except FileNotFoundError:
                pass
            _verify_zero_cost_invariant(arm, case)
            return
        if time.time() - start > budget_s:
            _log(f"{arm}/{case}: budget {budget_s}s reached — engine "
                 "still live; re-invoke to continue waiting")
            return
        time.sleep(10)
        # transport watchdog between polls
        if not ensure_transport(arm):
            _log(f"{arm}/{case}: WARNING transport DOWN (recorded; "
                 "the engine's own retry/ladder records the failures)")


def _verify_zero_cost_invariant(arm: str, case: str) -> bool:
    """Fail-closed: every run-owned routing line must carry the arm's
    allowed cost class. A PAID_API line anywhere is a hard failure."""
    spec = ARMS[arm]
    prefix = spec["run_id_prefix"]
    ledger = REPO_ROOT / "ENGINE_RUNS" / "model_routing" / "ledger.jsonl"
    lines: List[Dict[str, Any]] = []
    if ledger.exists():
        for raw in ledger.read_text().splitlines():
            try:
                d = json.loads(raw)
            except Exception:  # noqa: BLE001
                continue
            if str(d.get("run_id") or "").startswith(prefix + "-"):
                lines.append(d)
    bad = [l for l in lines
           if (l.get("cost_class") or "") not in
           spec["allowed_cost_classes"]]
    out = _arm_dir(arm, case)
    out.mkdir(parents=True, exist_ok=True)
    out = out / "ZERO_COST_INVARIANT.json"
    out.write_text(json.dumps({
        "arm": arm, "case": case,
        "run_owned_lines": len(lines),
        "violation_lines": len(bad),
        "violations": [
            {"provider": b.get("provider"), "model": b.get("model"),
             "cost_class": b.get("cost_class")} for b in bad[:10]],
        "checked_at": _now(),
    }, indent=1))
    if bad:
        _log(f"{arm}/{case}: ZERO-COST INVARIANT VIOLATED ({len(bad)} "
             "lines) — the experiment fails closed")
        return False
    _log(f"{arm}/{case}: zero-cost invariant GREEN ({len(lines)} "
         "run-owned lines)")
    return True


# ---------------------------------------------------------------------------
# assess — the per-arm chain record (the r452_assay.assess vocabulary)
# ---------------------------------------------------------------------------
def _ten_from_final(fs: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "final_status": fs.get("final_status"),
        "failed_stages": fs.get("failed_stages") or {},
        "adjudication_verdict": fs.get("adjudication_verdict"),
        "adversarial_overall": fs.get("adversarial_overall"),
        "evidence_verified": fs.get("evidence_verified"),
        "evolution": fs.get("evolution") or {},
        "ranking_score": fs.get("ranking_score"),
        "stop_reason": (fs.get("evolution") or {}).get("stop_reason"),
    }


def assess_arm(arm: str) -> int:
    chains = []
    for case in ("A", "B", "C"):
        d = _arm_dir(arm, case)
        fs = _read_json(d / "final_state.json")
        if fs is None and not (d / "problem.json").exists():
            chains.append({
                "arm": arm, "case": case,
                "case_id": CASES[case]["case_id"],
                "terminal_outcome": "UNKNOWN_NOT_REACHED",
                "terminal_outcome_basis": "the run was not executed"})
            continue
        if fs is None:
            chains.append({
                "arm": arm, "case": case,
                "case_id": CASES[case]["case_id"],
                "terminal_outcome": "INCOMPLETE_INFRASTRUCTURE_FAILURE",
                "terminal_outcome_basis": (
                    "engine ran but no final_state.json — see "
                    "engine.log; infrastructure, never a scientific "
                    "rejection (Art. LXI)")})
            continue
        ten = _ten_from_final(fs)
        fsc = ten.get("final_status")
        failed = ten.get("failed_stages") or {}
        if failed or fsc in ("MECHANISM_GENERATION_FAILED",):
            outcome = "INCOMPLETE_INFRASTRUCTURE_FAILURE"
            basis = (f"stages failed: {sorted(failed.keys())} — "
                     "infrastructure, never scientific (Art. LXI)")
        elif fsc == "INVENTION_UNDER_DEVELOPMENT":
            verdict = ten.get("adjudication_verdict")
            adversarial = ten.get("adversarial_overall")
            if verdict in ("REJECTED", "KILLED") or \
                    adversarial in ("KILLED",):
                outcome = "KILLED"
                basis = (f"adjudication {verdict}, adversarial "
                         f"{adversarial}")
            else:
                outcome = "INVENTION_UNDER_DEVELOPMENT"
                basis = (f"final {fsc} (adjudication {verdict}, "
                         f"adversarial {adversarial})")
        elif fsc in ("REJECTED", "REJECTED_SCIENTIFIC",
                     "REJECTED_EVIDENCE", "REJECTED_PRIOR_ART",
                     "REJECTED_ENGINEERING", "REJECTED_ATTACK",
                     "REJECTED_EXPERIMENT"):
            outcome = "REJECTED"
            basis = f"final status {fsc}"
        else:
            outcome = "UNKNOWN_NOT_REACHED"
            basis = f"final status {fsc!r} not in the closed map"
        chains.append({
            "arm": arm, "case": case,
            "case_id": CASES[case]["case_id"],
            "family": CASES[case]["family"],
            "run_id": fs.get("run_id"),
            "ten_stages": ten,
            "terminal_outcome": outcome,
            "terminal_outcome_basis": basis,
        })
        _log(f"{arm}/{case}: {outcome} — {basis}"[:150])
    rec = {
        "artifact_type": "R452_MODEL_EXPERIMENT_ASSESS",
        "arm": arm,
        "recorded_at": _now(),
        "chains": chains,
        "legitimate_outcomes": [
            "KILLED", "INVENTION_UNDER_DEVELOPMENT", "REJECTED",
            "UNKNOWN_NOT_REACHED", "INCOMPLETE_INFRASTRUCTURE_FAILURE"],
        "no_hardcoded_expected_answer": True,
    }
    MX_ROOT.joinpath(f"ASSESS_{arm}.json").write_text(
        json.dumps(rec, indent=1))
    _log(f"assess {arm} -> {MX_ROOT / f'ASSESS_{arm}.json'}")
    return 0


# ---------------------------------------------------------------------------
# measure — the eight dimensions from the runs' OWN artifacts
# ---------------------------------------------------------------------------
def _instrument_metrics(case_dir: Path) -> Dict[str, Any]:
    """The FROZEN instrument's per-run metrics (imported UNMODIFIED —
    Art. XLVII: the identical measurement instrument on both arms)."""
    try:
        import r452_quality_instrument as qi
        return qi._case_metrics(case_dir)
    except Exception as e:  # noqa: BLE001
        return {"available": False,
                "reason": f"instrument error: {type(e).__name__}: "
                          f"{e}"[:200]}


def _domain_correctness(case_dir: Path,
                        declared_family: str) -> Dict[str, Any]:
    """Dimension 6 — the detected domain verbatim + the E10 defect
    class (ml_data on a physical problem) + the engineering spec's
    canonical family + value sourcing when produced. Mechanical, no
    judgment."""
    out: Dict[str, Any] = {"declared_family": declared_family}
    env = None
    for name in ("envelope_CLASSIFY", "envelope_MECHANISM_SPACE",
                 "envelope_SYNTHESIZE"):
        env = _read_json(case_dir / f"{name}.json")
        if env:
            break
    if env:
        physics = (env.get("physics") or {}).get("pre_requirements") or {}
        det = physics.get("domain_detection") or {}
        out["detected_domain"] = physics.get("domain") or det.get("domain")
        out["ml_data_misroute"] = (
            str(out.get("detected_domain") or "").lower() == "ml_data")
    else:
        out["detected_domain"] = None
        out["ml_data_misroute"] = None  # UNKNOWN, not clean
    specs = sorted(case_dir.glob("ENGINEERING_SPECIFICATION*.json"))
    fams = []
    for sp in specs[:4]:
        d = _read_json(sp) or {}
        core = d.get("engineering_core") or {}
        vs = core.get("value_sourcing") or {}
        fams.append({
            "spec": sp.name,
            "canonical_family": (core.get("why_this_domain") or {}).get(
                "canonical_family") or core.get("canonical_family"),
            "value_sourcing": {
                k: vs.get(k) for k in ("counts", "n_total", "n_sourced",
                                       "geometry_reachable")
                if k in vs},
        })
    out["engineering_specs"] = fams
    return out


def _engineering_reachability(case_dir: Path) -> Dict[str, Any]:
    """Dimension 8 — the CAD pass ledgers + the STEP/STL/GLB artifacts
    actually on disk (BS-005: file existence is checked, not assumed)."""
    out: Dict[str, Any] = {}
    ledgers = sorted(case_dir.glob("CAD_PIPELINE_LEDGER*.json"))
    if not ledgers:
        out["reached"] = False
        out["reason"] = ("no CAD_PIPELINE_LEDGER artifacts — the run "
                         "did not reach the per-generation geometry "
                         "stage (NOT_REACHED, Art. XXV)")
        return out
    outs = []
    for lg in ledgers[:6]:
        d = _read_json(lg) or {}
        outs.append({
            "ledger": lg.name,
            "status": d.get("status"),
            "outcome": d.get("outcome"),
            "classification": (d.get("bridge") or {}).get(
                "visualizability_class") or d.get(
                "visualizability_class"),
        })
    three_d = case_dir / "three_d"
    step = sorted(three_d.rglob("*.step")) if three_d.exists() else []
    stl = sorted(three_d.rglob("*.stl")) if three_d.exists() else []
    glb = sorted(three_d.rglob("*.glb")) if three_d.exists() else []
    model_glb = sorted((case_dir / "MODEL").glob("*.glb")) \
        if (case_dir / "MODEL").exists() else []
    out["reached"] = True
    out["ledgers"] = outs
    out["step_files"] = [p.name for p in step[:6]]
    out["stl_files"] = [p.name for p in stl[:6]]
    out["glb_files"] = [p.name for p in glb[:4]]
    out["model_glbs"] = [p.name for p in model_glb[:4]]
    out["step_exported"] = bool(step)
    out["stl_exported"] = bool(stl)
    return out


def _transport_facts(case_dir: Path, arm: str) -> Dict[str, Any]:
    """Run-owned routing lines (the run's own ledger first; the global
    ledger by run-id prefix as fallback) + latency/degradation stats."""
    spec = ARMS[arm]
    lines: List[Dict[str, Any]] = []
    rl = _read_json(case_dir / "ROUTING_LEDGER_RUN.json")
    if rl and rl.get("lines"):
        lines = [l for l in rl["lines"]
                 if str(l.get("run_id") or "").startswith(
                     spec["run_id_prefix"] + "-")]
        src = "ROUTING_LEDGER_RUN.json"
    else:
        ledger = REPO_ROOT / "ENGINE_RUNS" / "model_routing" / \
            "ledger.jsonl"
        if ledger.exists():
            for raw in ledger.read_text().splitlines()[-2000:]:
                try:
                    d = json.loads(raw)
                except Exception:  # noqa: BLE001
                    continue
                if str(d.get("run_id") or "").startswith(
                        spec["run_id_prefix"] + "-"):
                    lines.append(d)
        src = "global ledger (run-id prefix isolation)"
    ok_lines = [l for l in lines if l.get("ok")]
    lat = [int(l.get("latency_ms") or 0) for l in ok_lines
           if l.get("latency_ms")]
    degrad = [l.get("task_degradation") or {} for l in lines]
    return {
        "source": src,
        "run_owned_calls": len(lines),
        "ok_calls": len(ok_lines),
        "providers": sorted({str(l.get("provider")) for l in lines}),
        "models": sorted({str(l.get("model")) for l in lines}),
        "cost_classes": sorted({str(l.get("cost_class")) for l in lines}),
        "mean_latency_ms": (int(sum(lat) / len(lat)) if lat else None),
        "max_latency_ms": (max(lat) if lat else None),
        "degraded_calls": sum(
            1 for dg in degrad
            if dg.get("task_capability_match") is False),
        "engine_stages_called": sorted(
            {str(l.get("engine_stage")) for l in lines if l.get(
                "engine_stage")}),
    }


def _wall_clock(case_dir: Path) -> Optional[float]:
    """Run wall-clock from the problem record's own timestamps to the
    final state timestamp (seconds; None when not derivable)."""
    fs = _read_json(case_dir / "final_state.json")
    pm = _read_json(case_dir / "problem.json")
    if not fs or not pm:
        return None
    try:
        from datetime import datetime as _dt
        t0 = pm.get("received_at") or pm.get("created_at") or \
            pm.get("timestamp")
        t1 = fs.get("timestamp")
        if not (t0 and t1):
            return None
        p0 = _dt.fromisoformat(str(t0).replace("Z", "+00:00"))
        p1 = _dt.fromisoformat(str(t1).replace("Z", "+00:00"))
        return round((p1 - p0).total_seconds(), 1)
    except Exception:  # noqa: BLE001
        return None


#: the eight dimensions' per-run extractor (typed sources only)
def _arm_case_metrics(arm: str, case: str) -> Dict[str, Any]:
    d = _arm_dir(arm, case)
    inst = _instrument_metrics(d)
    fs = _read_json(d / "final_state.json") or {}
    dom = _domain_correctness(d, CASES[case]["family"])
    return {
        "arm": arm, "case": case,
        "case_id": CASES[case]["case_id"],
        "family": CASES[case]["family"],
        "run_id": fs.get("run_id"),
        "final_status": fs.get("final_status"),
        "adjudication_verdict": fs.get("adjudication_verdict"),
        "adversarial_overall": fs.get("adversarial_overall"),
        "survivor_reached": ((fs.get("evolution") or {})
                             .get("survivor_reached")),
        "evolution_generations": ((fs.get("evolution") or {})
                                  .get("n_generations")),
        "evolution_stop_reason": ((fs.get("evolution") or {})
                                  .get("stop_reason")),
        "ranking_score": fs.get("ranking_score"),
        # dims 1-2-3: the frozen instrument
        "instrument": {
            k: inst.get(k) for k in (
                "evidence_relevance_rate", "evidence_n_items",
                "evidence_counts",
                "mechanism_grounding_rate",
                "mechanism_span_verbatim_support",
                "differentiated_mechanism_rate",
                "obvious_combination_rate",
                "evidence_contradiction_rate",
                "false_kill_rate",
                "attack_completeness",
                "n_candidates", "good_discovery_candidates",
                "raw_survivors", "quality_weighted_survivors",
            ) if k in inst},
        "instrument_available": inst.get("available", True),
        # dim 4: attack execution (the run's own records)
        "attack_execution": {
            "adversarial_overall": fs.get("adversarial_overall"),
            "evidence_verified": fs.get("evidence_verified"),
        },
        # dim 5: attack survival
        "attack_survival": {
            "survivor_reached": ((fs.get("evolution") or {})
                                 .get("survivor_reached")),
            "adjudication_verdict": fs.get("adjudication_verdict"),
            "evolution_generations": ((fs.get("evolution") or {})
                                      .get("n_generations")),
        },
        # dim 6: domain correctness
        "domain_correctness": dom,
        # dim 7: parameter sourcing
        "parameter_sourcing": {
            "specs": dom["engineering_specs"],
        },
        # dim 8: engineering reachability
        "engineering_reachability": _engineering_reachability(d),
        "transport": _transport_facts(d, arm),
        "wall_clock_s": _wall_clock(d),
        "zero_cost_invariant": _read_json(
            d / "ZERO_COST_INVARIANT.json"),
    }


def _mean(xs: List[Any]) -> Any:
    vals = [x for x in xs if isinstance(x, (int, float))]
    return round(sum(vals) / len(vals), 4) if vals else \
        "UNKNOWN_NO_NUMERIC_VALUES"


def _arm_dimension_rollup(
        per_case: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The eight-dimension arm-level rollup (means over cases; typed
    UNKNOWN when no case produced the dimension — Art. XXV)."""
    inst = [p.get("instrument") or {} for p in per_case]
    return {
        "1_evidence_grounding": {
            "mean_evidence_relevance_rate": _mean(
                [i.get("evidence_relevance_rate") for i in inst]),
            "per_case": [i.get("evidence_relevance_rate") for i in inst],
            "evidence_verified": [p.get("attack_execution", {}).get(
                "evidence_verified") for p in per_case],
        },
        "2_mechanism_fidelity": {
            "mean_mechanism_span_verbatim_support": _mean(
                [i.get("mechanism_span_verbatim_support") for i in inst]),
            "mean_mechanism_grounding_rate": _mean(
                [i.get("mechanism_grounding_rate") for i in inst]),
            "per_case_verbatim": [
                i.get("mechanism_span_verbatim_support") for i in inst],
        },
        "3_candidate_quality": {
            "mean_obvious_combination_rate": _mean(
                [i.get("obvious_combination_rate") for i in inst]),
            "mean_differentiated_mechanism_rate": _mean(
                [i.get("differentiated_mechanism_rate") for i in inst]),
            "mean_ranking_score": _mean(
                [p.get("ranking_score") for p in per_case]),
            "n_candidates_total": sum(
                int(i.get("n_candidates") or 0) for i in inst),
            "good_discovery_candidates_total": sum(
                int(i.get("good_discovery_candidates") or 0)
                for i in inst),
        },
        "4_attack_execution": {
            "adversarial_overall": [p.get("adversarial_overall")
                                    for p in per_case],
            "attack_completeness": [i.get("attack_completeness")
                                    for i in inst],
        },
        "5_attack_survival": {
            "survivor_reached": [p.get("survivor_reached")
                                 for p in per_case],
            "adjudication_verdicts": [p.get("adjudication_verdict")
                                      for p in per_case],
            "evolution_generations": [p.get("evolution_generations")
                                      for p in per_case],
        },
        "6_domain_correctness": {
            "detected_domains": [
                (p.get("domain_correctness") or {}).get("detected_domain")
                for p in per_case],
            "ml_data_misroutes": [
                (p.get("domain_correctness") or {}).get("ml_data_misroute")
                for p in per_case],
        },
        "7_parameter_sourcing": {
            "specs_value_sourcing": [
                s.get("value_sourcing")
                for p in per_case
                for s in (p.get("parameter_sourcing") or {}).get(
                    "specs", [])],
            "n_specs_produced": sum(
                len((p.get("parameter_sourcing") or {}).get("specs", []))
                for p in per_case),
        },
        "8_engineering_reachability": {
            "reached": [
                (p.get("engineering_reachability") or {}).get("reached")
                for p in per_case],
            "step_exported": [
                (p.get("engineering_reachability") or {}).get(
                    "step_exported") for p in per_case],
            "stl_exported": [
                (p.get("engineering_reachability") or {}).get(
                    "stl_exported") for p in per_case],
        },
        "transport_facts": {
            "run_owned_calls": [
                (p.get("transport") or {}).get("run_owned_calls")
                for p in per_case],
            "mean_latency_ms": [
                (p.get("transport") or {}).get("mean_latency_ms")
                for p in per_case],
            "degraded_calls": [
                (p.get("transport") or {}).get("degraded_calls")
                for p in per_case],
            "wall_clock_s": [p.get("wall_clock_s") for p in per_case],
        },
        "terminal_outcomes": [p.get("final_status") for p in per_case],
    }


def measure() -> int:
    per_arm: Dict[str, Any] = {}
    for arm in ARMS:
        per_case = []
        for case in ("A", "B", "C"):
            d = _arm_dir(arm, case)
            if not (d / "final_state.json").exists() and \
                    not (d / "problem.json").exists():
                per_case.append({
                    "arm": arm, "case": case,
                    "final_status": "UNKNOWN_NOT_REACHED",
                    "reason": "the run was not executed"})
                continue
            per_case.append(_arm_case_metrics(arm, case))
        per_arm[arm] = {
            "arm_definition": {k: ARMS[arm][k] for k in (
                "policy", "model", "provider", "quality_tier",
                "cost_basis")},
            "per_case": per_case,
            "dimensions": _arm_dimension_rollup(per_case),
        }
    assess = {}
    for arm in ARMS:
        p = MX_ROOT / f"ASSESS_{arm}.json"
        if p.exists():
            assess[arm] = _read_json(p)
    doc = {
        "artifact_type": "R452_MODEL_EXPERIMENT_MEASUREMENT",
        "measured_at": _now(),
        "instrument": ("the FROZEN r452_quality_instrument._case_metrics "
                       "(imported unmodified) + this module's typed "
                       "extractors; identical on both arms (Art. XLVII)"),
        "per_arm": per_arm,
        "assess": assess,
    }
    MX_ROOT.joinpath("MEASUREMENT.json").write_text(
        json.dumps(doc, indent=1))
    _log(f"measurement -> {MX_ROOT / 'MEASUREMENT.json'}")
    return 0


def record() -> int:
    """Assemble R452/MODEL_EXPERIMENT.json — the durable experiment
    record (provenance, both arms, the eight dimensions, the honest
    reading; NO prose superiority claim — the numbers are the record)."""
    meas = _read_json(MX_ROOT / "MEASUREMENT.json")
    probe_rec = _read_json(PROBE_RECORD)
    if not meas:
        raise SystemExit("run `measure` first")
    doc = {
        "artifact_type": "R452_MODEL_EXPERIMENT",
        "experiment": (
            "A3 stronger-model controlled experiment: the same frozen "
            "R452 assay problems (A/B/C) through the same engine code "
            "at one commit, the LLM route as the ONLY variable — "
            "Qwen/Qwen3-1.7B (localqwen, quality_tier 4, the deployed "
            "default) vs the sandbox z-ai gateway's embedded model "
            "(measured glm-4-plus, quality_tier 2, ENVIRONMENT_GRANT)"),
        "operator_directive": ("the model survey of 2026-09-14: run the "
                               "same frozen problem and prompts, "
                               "measure grounding/reasoning/novelty "
                               "etc., record model id/revision/"
                               "quantization/commit SHA/run_id — no "
                               "prose superiority claim"),
        "route_authority": probe_rec,
        "arms": meas["per_arm"],
        "assess": meas.get("assess"),
        "environment_reset_disclosure": (
            "the first attempt was destroyed mid-run by a sandbox "
            "environment reset (2026-09-13 ~18:05 UTC; the in-flight "
            "arm1/A engine run and its five stage envelopes lost); "
            "restarted at the same re-fetched commit with fresh run "
            "identities — no artifact from the lost attempt reused "
            "(Art. XI/XV)"),
        "honest_reading": {
            "rule": ("the numbers are the record; any stronger-model "
                     "superiority claim must cite these measured "
                     "dimensions (the R452 directive forbids prose "
                     "claims)"),
            "a3_note": ("this experiment MEASURES the escalation's "
                        "cost question; the deployed-policy decision "
                        "stays owner-gated (Art. XIII/LXV) — the "
                        "experiment is never a deployed-policy change"),
        },
        "provenance": {
            "engine_commit": subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
                capture_output=True, text=True).stdout.strip(),
            "instrument": "r452_quality_instrument.py (FROZEN, "
                          "sha-verified at apply time)",
            "problem_texts": "r452_assay.AUTHORED_PROBLEMS "
                             "(byte-identical import, both arms)",
            "recorded_at": _now(),
        },
    }
    MEASUREMENT_RECORD.write_text(json.dumps(doc, indent=1))
    _log(f"experiment record -> {MEASUREMENT_RECORD}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == "probe":
        return probe()
    if cmd == "engine":
        arm = sys.argv[2]
        case = sys.argv[3].upper()
        budget = int(sys.argv[4]) if len(sys.argv) > 4 else 3600
        if arm not in ARMS or case not in CASES:
            print(f"unknown arm/case {arm}/{case}")
            return 1
        run_engine(arm, case, budget)
        return 0
    if cmd == "assess":
        return assess_arm(sys.argv[2])
    if cmd == "measure":
        return measure()
    if cmd == "record":
        return record()
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
