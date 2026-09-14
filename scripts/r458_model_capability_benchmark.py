#!/usr/bin/env python3
"""scripts/r458_model_capability_benchmark.py — R458-C1 §2/§3: the
model-capability benchmark (models, not providers).

Directive (verbatim intent): "Benchmark models—not providers. Do not
ask: Which provider is best? Ask: Which model produces the best
defensible discovery? Start with the strongest currently available
free routes already surfaced by the live ecosystem ... Measure the
actual science ... Do not use generic benchmarks as the decision
criterion."

DESIGN (Art. XLVII — the measurement instrument identical on every
arm; the MODEL is the only variable):

  - The FROZEN R458 benchmark corpus (r458_benchmark.py): 14 authored
    problems, 7 domain families, DEV/HOLDOUT split sealed at freeze.
    Model arms run ONLY the DEV problems (BS-016: the holdout is
    mechanically refused outside the blind phase; the blind phase
    itself refuses to run before the dev record exists).
  - The FROZEN R458 quality instrument (r458_quality_instrument.py):
    the thirteen directive metrics + wall clock, deterministic over
    each run's OWN persisted artifacts; apply refuses on instrument
    drift (Art. LIX).
  - Each arm runs the REAL engine (discovery_fabric.engine.run) on
    each DEV problem: the problem is BUILT through the arm's own route
    (the MODEL_DERIVED extraction is the first measured LLM step — the
    r452 discipline), then the full stage chain executes with the
    arm's model as the only eligible route.
  - THE MODEL-PURITY INVARIANT (fail-closed, every run): every
    run-owned routing-ledger line must carry the arm's provider AND
    model — a cross-arm model line or a paid-cost line anywhere fails
    the arm closed (Art. IV/VII).

THE ARMS (the honest reachable set from THIS coding environment,
measured 2026-09-15; every unreachable route is TYPED, never silently
omitted — Art. XXV / LXI):

  RUNNABLE:
    glm-4-plus            the sandbox z-ai gateway's served model
                          (ENVIRONMENT_GRANT — the platform's embedded
                          grant; honest scope: this is the GLM family
                          arm ACTUALLY reachable here; GLM-5.3 itself
                          requires unorouter whose key is not present
                          in this environment)
    glm-4-plus-thinking   the same served model with the CLI's own
                          reasoning mode ON (transport-plumbing mode
                          switch, disclosed in zai_gateway.mjs; the
                          reasoning axis of the capability question)
    qwen3-1.7b            the self-hosted zero-paid baseline (the
                          R451 pinned llama.cpp b10930 + sha-pinned
                          Qwen3-1.7B Q4_K_M GGUF — the zero-cost floor)

  TYPED-UNAVAILABLE (recorded with the Art. LXV escalation — the
  operator's four free-tier router keys exist only as HF Space
  secrets, env-injected at deploy; they are NOT present in this
  sandbox, and BS-021 forbids any other storage):
    unorouter glm-5.3:free / glm-5.3-flash:free / qwen3.8-27b:free
    xkiro qwen/qwen3.8-max:free, minimax/minimax-m3:free (+ the
    directive-listed qwen3.7/qwen3.6 variants the operator reports
    newly exposed)
    apinex free/deepseek-v4.1-flash (+ deepseek v4 pro where free)
    bai qwen3.8-flash
    NVIDIA Nemotron free offerings (no NVIDIA_API_KEY here)
    HF router zai-org/GLM-5.3 (re-measured 2026-09-15: 402 monthly
    credits depleted — CREDIT_EXHAUSTED)
    OpenRouter free pool (no OPENROUTER_API_KEY here)

MODEL SELECTION RULE (declared BEFORE any dev result is looked at —
this IS the dev set's purpose, Art. LIX): the selected model is the
arm with the highest QUALITY COMPOSITE = mean of the normalized
quality metrics (problem_understanding, evidence_synthesis,
mechanism_quality, mechanism_differentiation, candidate_quality,
attack_quality, contradiction_detection, engineering_reasoning,
structured_output_reliability, 1 - hallucination_rate,
1 - failure_rate; UNKNOWN metrics are EXCLUDED from that arm's mean,
never zero-filled — Art. XXV). Latency and token cost are the COST
axis, recorded alongside, never part of the quality ranking. The
selected model then runs the BLIND HOLDOUT (the only phase allowed
to touch it).

Usage:
  python scripts/r458_model_capability_benchmark.py probe
  python scripts/r458_model_capability_benchmark.py run ARM [budget_s]
  python scripts/r458_model_capability_benchmark.py measure
  python scripts/r458_model_capability_benchmark.py blind [budget_s]
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

OUT_ROOT = REPO_ROOT / "R458"
ARMS_ROOT = OUT_ROOT / "MODEL_ARMS"
DEV_RECORD = OUT_ROOT / "MODEL_CAPABILITY_BENCHMARK.json"
BLIND_RECORD = OUT_ROOT / "BLIND_TEST_RESULTS.json"
DIRECTIVE_RECORD = REPO_ROOT / "R458_C1_MODEL_CAPABILITY_BENCHMARK.json"

import r458_benchmark as bench           # noqa: E402  (frozen corpus)
import r458_quality_instrument as qi     # noqa: E402  (frozen metrics)

#: the self-hosted transport (the R451 pinned assets)
LLAMA_BIN = Path("/home/z/my-project/local_llm/bin/llama-b10930/"
                 "llama-server")
GGUF_1_7B = Path("/home/z/my-project/local_llm/models/"
                 "Qwen3-1.7B-Q4_K_M.gguf")
GGUF_1_7B_SHA256 = ("72c5c3cb38fa32d5256e2fe30d03e7a64c6c79e668"
                    "ad84057e3bd66e250b24fb")

#: the z-ai gateway (sandbox-local; key kept OUTSIDE the repo, BS-021)
GATEWAY_KEY_FILE = Path("/home/z/my-project/local_llm/zai_gateway_key")

#: every credential that could route a PAID_API call — stripped from
#: EVERY arm's environment (the benchmark's zero-paid contract is
#: structural: no arm can make a paid call even under UNRESTRICTED)
PAID_ENV_VARS = [
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY",
    "NVIDIA_API_KEY", "DEEPSEEK_API_KEY", "MISTRAL_API_KEY",
    "GEMINI_API_KEY", "QWEN_API_KEY", "TOKEN_ROUTER_API_KEY",
    "UNOROUTER_API_KEY", "XKIRO_API_KEY", "APINEX_API_KEY",
    "BAI_API_KEY", "HF_TOKEN", "HUGGINGFACE_API_TOKEN",
]

RUNNABLE_ARMS: Dict[str, Dict[str, Any]] = {
    "glm-4-plus": {
        "provider": "zai",
        "model": "glm-4-plus",
        "policy": "UNRESTRICTED",
        "cost_basis": "ENVIRONMENT_GRANT",
        "allowed_providers": ["zai"],
        "allowed_models": ["glm-4-plus"],
        "run_id_prefix": "r458mca",
        "llm_timeout_s": "300",
        "arm_note": (
            "the sandbox z-ai gateway's served model under the "
            "platform's embedded grant — the GLM family arm actually "
            "reachable from this environment; the operator escape "
            "hatch ENGINE_MODEL_COST_POLICY=UNRESTRICTED is required "
            "because the grant basis is ENVIRONMENT_GRANT (ineligible "
            "under ZERO_PAID_COST by design); every PAID key is "
            "structurally stripped so no paid call is possible"),
    },
    "glm-4-plus-thinking": {
        "provider": "zai",
        "model": "glm-4-plus-thinking",
        "policy": "UNRESTRICTED",
        "cost_basis": "ENVIRONMENT_GRANT",
        "allowed_providers": ["zai"],
        "allowed_models": ["glm-4-plus-thinking", "glm-4-plus"],
        "run_id_prefix": "r458mcb",
        "llm_timeout_s": "600",
        "arm_note": (
            "the same served model with the z-ai CLI's own reasoning "
            "mode ON (the gateway maps the -thinking model id to the "
            "CLI --thinking flag — transport plumbing, disclosed in "
            "zai_gateway.mjs; the served weights are identical): the "
            "reasoning-mode axis of the capability question"),
    },
    "qwen3-1.7b": {
        "provider": "localqwen",
        "model": "qwen3-1.7b",
        "policy": "ZERO_PAID_COST",
        "cost_basis": "ZERO_PAID_COST_SELF_HOSTED",
        "allowed_providers": ["localqwen"],
        "allowed_models": ["qwen3-1.7b"],
        "run_id_prefix": "r458mcc",
        "llm_timeout_s": "600",
        "arm_note": (
            "the self-hosted zero-paid baseline (the R451 pinned "
            "llama.cpp b10930 + the sha-verified Qwen3-1.7B Q4_K_M "
            "GGUF) — the zero-cost floor the strong routes are "
            "compared against"),
    },
}

#: the directive-listed models NOT runnable from this environment —
#: typed, with the honest measured reason + the Art. LXV escalation
UNAVAILABLE_ARMS: List[Dict[str, Any]] = [
    {"models": ["unorouter:glm-5.3:free", "unorouter:glm-5.3-flash:free",
                "unorouter:qwen3.8-27b:free"],
     "state": "CREDENTIAL_UNAVAILABLE",
     "reason": ("UNOROUTER_API_KEY exists only as an env-injected HF "
                "Space secret (BS-021); not present in this coding "
                "environment — the arm cannot run HERE (Art. LXI: "
                "infrastructure, never a model-quality verdict)")},
    {"models": ["xkiro:qwen/qwen3.8-max:free",
                "xkiro:minimax/minimax-m3:free",
                "xkiro:qwen/qwen3.7-max:free (operator-reported)",
                "xkiro:qwen/qwen3.6-35b-a3b:free (operator-reported)"],
     "state": "CREDENTIAL_UNAVAILABLE",
     "reason": ("XKIRO_API_KEY exists only as an env-injected HF Space "
                "secret; not present in this coding environment")},
    {"models": ["apinex:free/deepseek-v4.1-flash",
                "apinex:free/deepseek-v4-pro (where genuinely free)"],
     "state": "CREDENTIAL_UNAVAILABLE",
     "reason": ("APINEX_API_KEY exists only as an env-injected HF "
                "Space secret; not present in this coding "
                "environment")},
    {"models": ["bai:qwen3.8-flash"],
     "state": "CREDENTIAL_UNAVAILABLE",
     "reason": ("BAI_API_KEY exists only as an env-injected HF Space "
                "secret; not present in this coding environment")},
    {"models": ["nvidia:nemotron free offerings"],
     "state": "CREDENTIAL_UNAVAILABLE",
     "reason": ("NVIDIA_API_KEY not present in this environment and "
                "the account/provider does not currently permit them "
                "(the directive's own qualifier)")},
    {"models": ["hf-router:zai-org/GLM-5.3",
                "hf-router:zai-org/GLM-5.3-Flash"],
     "state": "CREDIT_EXHAUSTED",
     "reason": ("re-measured 2026-09-15 from this environment: HTTP "
                "402 'You have depleted your monthly included "
                "credits' with zero is_free catalog models — the same "
                "state R452-A3 measured")},
    {"models": ["openrouter:free pool"],
     "state": "CREDENTIAL_UNAVAILABLE",
     "reason": ("OPENROUTER_API_KEY not present in this environment "
                "(the paid-tier spec is PAID_API-ineligible under the "
                "cost policy regardless)")},
]


def _log(msg: str) -> None:
    print(f"[r458mc {datetime.now(timezone.utc).isoformat(timespec='seconds')}] "
          f"{msg}", flush=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def _arm_dir(arm: str, case: str) -> Path:
    return ARMS_ROOT / f"{arm.upper().replace('-', '_')}_RUN_{case}"


def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        if p.is_file():
            data = json.loads(p.read_text())
            return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None
    return None


# ---------------------------------------------------------------------------
# Arm environment (fail-closed key hygiene — the r452 discipline)
# ---------------------------------------------------------------------------

def arm_env(arm: str) -> Dict[str, str]:
    spec = RUNNABLE_ARMS[arm]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["ENGINE_MODEL_COST_POLICY"] = spec["policy"]
    for k in PAID_ENV_VARS:
        env.pop(k, None)
    env.pop("ZAI_API_KEY", None)
    env.pop("ZAI_MODEL", None)
    env.pop("ZAI_BASE_URL", None)
    env.pop("LOCAL_QWEN_BASE_URL", None)
    env.pop("LOCALQWEN_BASE_URL", None)
    env.pop("LOCAL_QWEN_MODEL", None)
    env.pop("LOCALQWEN_MODEL", None)
    if spec["provider"] == "zai":
        if not GATEWAY_KEY_FILE.is_file():
            raise SystemExit("z-ai gateway key file missing "
                             "(local_llm/zai_gateway_key — env-only, "
                             "BS-021)")
        env["ZAI_API_KEY"] = GATEWAY_KEY_FILE.read_text().strip()
        env["ZAI_MODEL"] = spec["model"]
        env["ENGINE_LLM_TIMEOUT_S"] = spec["llm_timeout_s"]
    elif spec["provider"] == "localqwen":
        env["LOCAL_QWEN_BASE_URL"] = \
            "http://127.0.0.1:8790/v1/chat/completions"
        env["LOCALQWEN_BASE_URL"] = \
            "http://127.0.0.1:8790/v1/chat/completions"
        env["ENGINE_LLM_TIMEOUT_S"] = spec["llm_timeout_s"]
    else:
        raise SystemExit(f"unknown arm provider {spec['provider']}")
    return env


# ---------------------------------------------------------------------------
# Transport watchdogs
# ---------------------------------------------------------------------------

def _http_ok(url: str, timeout: float = 5.0,
             key: Optional[str] = None) -> bool:
    import urllib.request
    req = urllib.request.Request(url)
    if key:
        req.add_header("Authorization", f"Bearer {key}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def _serves_model(url: str, model_alias: str) -> bool:
    """The transport-health check must verify the SERVED MODEL, not
    just HTTP liveness (the Art. XXXI defect caught this session: the
    R456 session's leftover bge EMBEDDING server answered /health on
    port 8790, which a plain liveness probe would have mistaken for
    the qwen3-1.7b transport — a model-capability benchmark probing
    the wrong model silently)."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"{url}/v1/models",
                                    timeout=5.0) as r:
            data = json.loads(r.read())
    except Exception:  # noqa: BLE001
        return False
    ids = {m.get("id") or m.get("model")
           for m in (data.get("data") or [])}
    return model_alias in ids


def ensure_zai_gateway() -> bool:
    key = GATEWAY_KEY_FILE.read_text().strip() \
        if GATEWAY_KEY_FILE.is_file() else ""
    if _http_ok("http://127.0.0.1:8787/healthz"):
        return True
    if not key:
        return False
    log = open("/home/z/my-project/local_llm/zai_gateway.log", "ab")
    subprocess.Popen(["node", "scripts/zai_gateway.mjs", "8787"],
                     cwd=str(REPO_ROOT), env={
                         **os.environ, "ZAI_GATEWAY_KEY": key},
                     stdout=log, stderr=subprocess.STDOUT,
                     start_new_session=True)
    time.sleep(2.0)
    return _http_ok("http://127.0.0.1:8787/healthz")


_LLAMA_PID_FILE = Path("/home/z/my-project/local_llm/llama_qwen3-1.7b.pid")


def ensure_llama_server() -> bool:
    # the health check verifies the SERVED MODEL (bge embedding
    # servers etc. must never pass for the qwen transport)
    if _serves_model("http://127.0.0.1:8790", "qwen3-1.7b"):
        return True
    if not (LLAMA_BIN.is_file() and GGUF_1_7B.is_file()):
        return False
    # sha pin (fail-closed, the R451 discipline)
    h = hashlib.sha256()
    with open(GGUF_1_7B, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    if h.hexdigest() != GGUF_1_7B_SHA256:
        _log("GGUF sha pin FAILED — refusing to serve")
        return False
    try:
        pid = int(_LLAMA_PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return False   # alive but wrong model — engine records it
    except (OSError, ValueError):
        pass
    log_fh = open("/home/z/my-project/local_llm/llama_qwen3-1.7b.log",
                  "ab")
    server_env = dict(os.environ)
    server_env["LD_LIBRARY_PATH"] = str(LLAMA_BIN.parent)
    cmd = [str(LLAMA_BIN), "-m", str(GGUF_1_7B),
           "--host", "127.0.0.1", "--port", "8790",
           "-c", "8192", "-t", "2",
           "--alias", "qwen3-1.7b", "--no-webui"]
    proc = subprocess.Popen(cmd, stdout=log_fh,
                            stderr=subprocess.STDOUT,
                            env=server_env, start_new_session=True)
    _LLAMA_PID_FILE.write_text(str(proc.pid))
    for _ in range(30):
        time.sleep(2.0)
        if _serves_model("http://127.0.0.1:8790", "qwen3-1.7b"):
            return True
    return False


def ensure_transport(arm: str) -> bool:
    if RUNNABLE_ARMS[arm]["provider"] == "zai":
        return ensure_zai_gateway()
    return ensure_llama_server()


# ---------------------------------------------------------------------------
# Probe (typed, every route — the honest reachable-set record)
# ---------------------------------------------------------------------------

def cmd_probe() -> int:
    ARMS_ROOT.mkdir(parents=True, exist_ok=True)
    reachable: Dict[str, Any] = {}
    for arm, spec in RUNNABLE_ARMS.items():
        ok = ensure_transport(arm)
        reachable[arm] = {
            "state": "TRANSPORT_OK" if ok else "TRANSPORT_UNAVAILABLE",
            "provider": spec["provider"],
            "model": spec["model"],
            "cost_basis": spec["cost_basis"],
            "policy": spec["policy"],
        }
        if arm == "qwen3-1.7b" and not ok:
            reachable[arm]["state_detail"] = (
                "llama-server b10930 build in progress or GGUF/assets "
                "missing in this sandbox (the environment reset wiped "
                "the R451 assets; being rebuilt — the arm is dropped "
                "typed-honestly if the build does not land)")
    record = {
        "artifact_type": "R458_ARM_PROBE/1.0.0",
        "probed_at_utc": _now(),
        "directive_quote": (
            "Start with the strongest currently available free routes "
            "already surfaced by the live ecosystem"),
        "runnable_arms": reachable,
        "unavailable_arms": UNAVAILABLE_ARMS,
        "escalation_art_lxv": (
            "the four free-tier router keys (unorouter/xkiro/apinex/"
            "bai) are env-injected HF Space secrets and are NOT "
            "present in this coding environment; the benchmark driver "
            "reads them from env when present — the moment the "
            "operator re-injects them, the router model arms run with "
            "ZERO driver changes; the model-quality question for "
            "those arms stays open with the operator (Art. LXV: the "
            "gate is named, not silently dropped)"),
    }
    (ARMS_ROOT / "ARM_PROBE.json").write_text(
        json.dumps(record, indent=1, sort_keys=True))
    for arm, r in reachable.items():
        _log(f"probe {arm}: {r['state']}")
    for u in UNAVAILABLE_ARMS:
        for m in u["models"]:
            _log(f"probe {m}: {u['state']}")
    print(json.dumps(record, indent=1, sort_keys=True))
    return 0


# ---------------------------------------------------------------------------
# Engine runs (the r452 detached pattern)
# ---------------------------------------------------------------------------

def _corpus_cases(split: str) -> Dict[str, Dict[str, Any]]:
    corpus = bench.load_corpus()
    return {k: p for k, p in corpus["problems"].items()
            if p["split"] == split}


def build_engine_problem(arm: str, case: str) -> Path:
    spec = RUNNABLE_ARMS[arm]
    corpus = bench.load_corpus()
    case_spec = corpus["problems"][case]
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
        f"built = build_problem({case_spec['text']!r});\n"
        "problem = built.get('problem') if isinstance("
        "built.get('problem'), dict) else built;\n"
        f"problem['problem_id'] = {case_spec['case_id']!r};\n"
        "problem['r458_benchmark'] = {\n"
        "    'class': 'FROZEN_BENCHMARK_DEV',\n"
        f"    'arm': {arm!r},\n"
        "    'content_sha256': "
        f"{hashlib.sha256(case_spec['text'].encode()).hexdigest()!r},\n"
        "    'corpus_freeze': 'R458/BENCHMARK_FREEZE.json',\n"
        "};\n"
        f"json.dump(problem, open({str(problem_json)!r}, 'w'), "
        "indent=1)\n"
    )
    r = subprocess.run([sys.executable, "-c", code], cwd=str(REPO_ROOT),
                       env=env, capture_output=True, text=True,
                       timeout=900)
    if r.returncode != 0 or not problem_json.exists():
        out_dir.joinpath("problem_build_error.txt").write_text(
            r.stdout[-3000:] + "\n" + r.stderr[-3000:])
        raise SystemExit(f"problem build failed for {arm}/{case}")
    _log(f"{arm}/{case}: engine problem built through the arm route")
    return problem_json


def _pid_alive(pid: Optional[int]) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:
        with open(f"/proc/{pid}/status") as fh:
            for line in fh:
                if line.startswith("State:"):
                    if line.split()[1].startswith("Z"):
                        return False
                    break
    except (OSError, IndexError):
        pass
    return True


def run_engine(arm: str, case: str, budget_s: int,
               run_id_suffix: str = "") -> None:
    spec = dict(RUNNABLE_ARMS[arm])
    corpus = bench.load_corpus()
    case_spec = corpus["problems"][case]
    suffix = f" {run_id_suffix}" if run_id_suffix else ""
    run_id = (f"{spec['run_id_prefix']}-{case}: "
              f"{case_spec['case_id']}{suffix}")
    session_id = f"{spec['run_id_prefix']}-{case.lower()}"
    out_dir = _arm_dir(arm, case)
    out_dir.mkdir(parents=True, exist_ok=True)
    problem_json = build_engine_problem(arm, case)
    env = arm_env(arm)
    pid_file = out_dir / "ENGINE_PID"

    def _engine_pid() -> Optional[int]:
        try:
            return int(pid_file.read_text().strip())
        except Exception:  # noqa: BLE001
            return None

    assert ensure_transport(arm), f"{arm}: transport failed to start"
    pid = _engine_pid()
    if _pid_alive(pid):
        _log(f"{arm}/{case}: attaching to live engine pid={pid}")
    else:
        cmd = [sys.executable, "-m", "discovery_fabric.engine.run",
               "--problem-json", str(problem_json),
               "--out", str(out_dir), "--no-package",
               "--run-id", run_id,
               "--session-id", session_id]
        if (out_dir / "problem.json").exists():
            cmd.append("--resume")
            _log(f"{arm}/{case}: starting DETACHED engine (resume)")
        else:
            _log(f"{arm}/{case}: starting DETACHED engine (fresh)")
        log_fh = open(out_dir / "engine.log", "ab")
        proc = subprocess.Popen(cmd, cwd=str(REPO_ROOT), env=env,
                                stdout=log_fh, stderr=subprocess.STDOUT,
                                start_new_session=True)
        pid_file.write_text(str(proc.pid))
        _log(f"{arm}/{case}: detached engine pid={proc.pid}")

    start = time.time()
    while True:
        if not _pid_alive(_engine_pid()):
            _log(f"{arm}/{case}: engine exited")
            try:
                pid_file.unlink()
            except FileNotFoundError:
                pass
            _verify_purity_invariant(arm, case)
            return
        if time.time() - start > budget_s:
            _log(f"{arm}/{case}: budget {budget_s}s reached — "
                 "re-invoke to continue waiting")
            return
        time.sleep(10)
        if not ensure_transport(arm):
            _log(f"{arm}/{case}: WARNING transport DOWN (recorded)")


def _verify_purity_invariant(arm: str, case: str) -> bool:
    """Fail-closed: every run-owned ledger line carries the arm's
    provider AND model; a paid-cost line fails the arm closed."""
    spec = RUNNABLE_ARMS[arm]
    prefix = spec["run_id_prefix"]
    ledger = REPO_ROOT / "ENGINE_RUNS" / "model_routing" / "ledger.jsonl"
    lines: List[Dict[str, Any]] = []
    if ledger.exists():
        for raw in ledger.read_text().splitlines()[-4000:]:
            try:
                d = json.loads(raw)
            except Exception:  # noqa: BLE001
                continue
            if str(d.get("run_id") or "").startswith(prefix + "-"):
                lines.append(d)
    bad_model = [l for l in lines
                 if l.get("model") not in spec["allowed_models"]]
    bad_paid = [l for l in lines
                if str(l.get("cost_class") or "").startswith("PAID")]
    ok = not bad_model and not bad_paid
    record = {
        "arm": arm, "case": case,
        "n_run_owned_lines": len(lines),
        "models_observed": sorted({l.get("model") for l in lines
                                   if l.get("model")}),
        "providers_observed": sorted({l.get("provider") for l in lines
                                      if l.get("provider")}),
        "cross_arm_model_lines": len(bad_model),
        "paid_cost_lines": len(bad_paid),
        "verdict": "PURE" if ok else "CONTAMINATED",
    }
    (_arm_dir(arm, case) / "PURITY_INVARIANT.json").write_text(
        json.dumps(record, indent=1, sort_keys=True))
    if not ok:
        _log(f"{arm}/{case}: PURITY INVARIANT FAILED — {record}")
    return ok


def cmd_run(arm: str, budget_s: int = 1800) -> int:
    if arm not in RUNNABLE_ARMS:
        print(f"unknown arm {arm}; runnable: "
              f"{sorted(RUNNABLE_ARMS)}", file=sys.stderr)
        return 2
    for case in sorted(_corpus_cases("DEV")):
        bench.assert_dev_only(case)
        run_engine(arm, case, budget_s)
    return 0


# ---------------------------------------------------------------------------
# Measure (the frozen instrument over every completed run)
# ---------------------------------------------------------------------------

#: the frozen selection rule (declared in this driver's header BEFORE
#: any dev result was produced; computed here verbatim)
QUALITY_METRICS = (
    "problem_understanding", "evidence_synthesis", "mechanism_quality",
    "mechanism_differentiation", "candidate_quality", "attack_quality",
    "contradiction_detection", "engineering_reasoning",
    "structured_output_reliability", "hallucination_rate",
    "failure_rate",
)


def _normalize(metric: str, value: Any) -> Optional[float]:
    """Normalize a metric value to [0,1] quality-higher-is-better.
    UNKNOWN / NOT_REACHED / non-numeric verdicts -> None (excluded
    from the arm's mean, Art. XXV)."""
    if value is None or isinstance(value, str):
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if metric in ("hallucination_rate", "failure_rate"):
        return 1.0 - v
    return v


def _case_measurement(arm: str, case: str,
                      corpus: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    d = _arm_dir(arm, case)
    if not (d / "final_state.json").is_file():
        return None
    text = corpus["problems"][case]["text"]
    try:
        m = qi.apply_to_run_dir(d, text)
    except SystemExit as e:
        return {"case": case, "instrument_refused": str(e)}
    purity = _read_json(d / "PURITY_INVARIANT.json") or {}
    m["purity"] = purity
    m["case"] = case
    m["domain_family"] = corpus["problems"][case]["domain_family"]
    return m


def _arm_aggregate(arm: str, cases: Dict[str, Dict[str, Any]],
                   corpus: Dict[str, Any]) -> Dict[str, Any]:
    measurements = []
    for case in sorted(cases):
        m = _case_measurement(arm, case, corpus)
        if m is not None:
            measurements.append(m)
    per_metric: Dict[str, Dict[str, Any]] = {}
    for metric in QUALITY_METRICS + ("latency", "token_cost"):
        # RAW per-case values in the aggregate table (never inverted —
        # failure_rate 0.0 displays as 0.0); the quality
        # NORMALIZATION happens ONLY inside the composite below
        raws, unknowns, lat_vals = [], 0, []
        for m in measurements:
            v = (m.get("metrics") or {}).get(metric, {}).get("value")
            if metric == "latency":
                if isinstance(v, dict) and isinstance(
                        v.get("mean_ms"), (int, float)):
                    lat_vals.append(v["mean_ms"])
                else:
                    unknowns += 1
                continue
            if isinstance(v, (int, float)):
                raws.append(float(v))
            elif v is None or isinstance(v, str):
                unknowns += 1
        if metric == "latency":
            per_metric[metric] = {
                "mean_ms": (round(sum(lat_vals) / len(lat_vals), 1)
                            if lat_vals else "ALL_UNKNOWN"),
                "n_measured": len(lat_vals), "n_unknown": unknowns}
            continue
        per_metric[metric] = {
            "mean": (round(sum(raws) / len(raws), 3) if raws
                     else "ALL_UNKNOWN"),
            "n_measured": len(raws),
            "n_unknown": unknowns,
        }
    # the quality composite: normalized quality-higher-is-better,
    # UNKNOWN excluded (Art. XXV), latency/token cost excluded (the
    # cost axis, recorded alongside — never part of the ranking)
    def _norm_vals(metric):
        out = []
        for m in measurements:
            v = (m.get("metrics") or {}).get(metric, {}).get("value")
            n = _normalize(metric, v) if metric in QUALITY_METRICS \
                else None
            if n is not None:
                out.append(n)
        return out
    quality_vals = []
    for metric in QUALITY_METRICS:
        vals = _norm_vals(metric)
        if vals:
            quality_vals.append(sum(vals) / len(vals))
    composite = (round(sum(quality_vals) / len(quality_vals), 3)
                 if quality_vals else "ALL_UNKNOWN")
    contaminated = [m["case"] for m in measurements
                    if (m.get("purity") or {}).get("verdict")
                    == "CONTAMINATED"]
    lat_mean = per_metric["latency"]["mean_ms"]
    tok_mean = per_metric["token_cost"]["mean"]
    return {
        "arm": arm,
        "spec": {k: RUNNABLE_ARMS[arm][k]
                 for k in ("provider", "model", "policy", "cost_basis",
                           "arm_note")},
        "n_cases_measured": len(measurements),
        "cases": measurements,
        "metric_aggregates": per_metric,
        "metric_aggregates_note": (
            "RAW per-case values (never inverted): failure_rate and "
            "hallucination_rate display their measured rates; the "
            "quality composite below is where the 1-x normalization "
            "applies (declared selection rule)"),
        "quality_composite": composite,
        "cost_axis": {
            "latency_mean_ms": lat_mean
            if isinstance(lat_mean, (int, float)) else "UNKNOWN",
            "token_cost_total": tok_mean
            if isinstance(tok_mean, (int, float)) else "UNKNOWN",
            "token_cost_note": (
                "UNKNOWN this round: the engine's generate path "
                "records latency but not usage tokens on the "
                "run-owned ledger (recorded gap, never fabricated — "
                "Art. XXV)"),
        },
        "purity": ("PURE" if not contaminated
                   else f"CONTAMINATED:{contaminated}"),
    }


def cmd_measure() -> int:
    corpus = bench.load_corpus()
    dev_cases = _corpus_cases("DEV")
    arms: List[Dict[str, Any]] = []
    for arm in sorted(RUNNABLE_ARMS):
        if not any((_arm_dir(arm, c) / "final_state.json").is_file()
                   for c in dev_cases):
            transport_probe = _read_json(
                ARMS_ROOT / "ARM_PROBE.json") or {}
            arms.append({
                "arm": arm,
                "state": "NOT_RUN",
                "reason": (transport_probe.get("runnable_arms", {})
                           .get(arm, {}).get("state_detail")
                           or "no completed dev runs"),
                "spec": {k: RUNNABLE_ARMS[arm][k]
                         for k in ("provider", "model", "policy",
                                   "cost_basis", "arm_note")},
            })
            continue
        arms.append(_arm_aggregate(arm, dev_cases, corpus))
    measured = [a for a in arms
                if isinstance(a.get("quality_composite"), float)]
    selected = (max(measured, key=lambda a: a["quality_composite"])[
        "arm"] if measured else None)
    record = {
        "artifact_type": "R458_MODEL_CAPABILITY_BENCHMARK/1.0.0",
        "phase": "DEV",
        "measured_at_utc": _now(),
        "directive_quote": (
            "Benchmark models—not providers. Which model produces the "
            "best defensible discovery?"),
        "benchmark_freeze": {
            "corpus_hash": json.loads(
                (OUT_ROOT / "BENCHMARK_FREEZE.json").read_text())
            ["corpus_hash"],
            "n_dev_problems": len(dev_cases),
            "holdout_policy": "sealed (BS-016) — this record touches "
                              "DEV problems only"},
        "instrument_freeze_sha256": json.loads(
            (OUT_ROOT / "QUALITY_INSTRUMENT_FREEZE.json").read_text())
        ["instrument_script_sha256"],
        "selection_rule": (
            "declared before any dev result: highest quality composite "
            "= mean of normalized quality metrics; UNKNOWN excluded "
            "never zero-filled; latency and token cost are the cost "
            "axis, recorded alongside, never part of the ranking"),
        "arms": arms,
        "unavailable_arms": UNAVAILABLE_ARMS,
        "selected_model": selected,
        "reviewer_provenance": "AI_REVIEW",
    }
    DEV_RECORD.write_text(json.dumps(record, indent=1, sort_keys=True))
    for a in arms:
        if "quality_composite" in a:
            _log(f"arm {a['arm']}: quality_composite="
                 f"{a['quality_composite']} "
                 f"(n={a.get('n_cases_measured')})")
        else:
            _log(f"arm {a['arm']}: {a.get('state')} — "
                 f"{a.get('reason', '')[:80]}")
    _log(f"selected_model={selected}")
    return 0


# ---------------------------------------------------------------------------
# The blind phase (the ONLY code path allowed to touch the holdout)
# ---------------------------------------------------------------------------

def cmd_blind(budget_s: int = 1800) -> int:
    bench.assert_blind_test_allowed()
    dev = _read_json(DEV_RECORD) or {}
    selected = dev.get("selected_model")
    if not selected or selected not in RUNNABLE_ARMS:
        print("blind test requires a selected runnable model "
              "(run measure first)", file=sys.stderr)
        return 2
    corpus = bench.load_corpus()
    holdout = _corpus_cases("HOLDOUT")
    measurements = []
    for case in sorted(holdout):
        run_engine(selected, case, budget_s,
                   run_id_suffix="(blind holdout)")
        m = _case_measurement(selected, case, corpus)
        if m is not None:
            measurements.append(m)
    record = {
        "artifact_type": "R458_BLIND_TEST_RESULTS/1.0.0",
        "phase": "BLIND_TEST",
        "measured_at_utc": _now(),
        "selected_model": selected,
        "dev_quality_composite": dev.get("arms") and next(
            (a.get("quality_composite") for a in dev["arms"]
             if a.get("arm") == selected), None),
        "n_holdout_problems": len(holdout),
        "holdout_cases": measurements,
        "blind_discipline": (
            "the holdout problems were sealed at corpus freeze and "
            "mechanically refused to every non-blind driver; this "
            "phase ran only after the dev-phase record existed; NO "
            "prompt/threshold/model tuning was performed against "
            "holdout content (Art. LIX / BS-016)"),
    }
    BLIND_RECORD.write_text(json.dumps(record, indent=1,
                                       sort_keys=True))
    _log(f"blind test recorded: {len(measurements)} holdout cases "
         f"on {selected}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    if cmd == "probe":
        return cmd_probe()
    if cmd == "run":
        arm = sys.argv[2] if len(sys.argv) > 2 else ""
        budget = int(sys.argv[3]) if len(sys.argv) > 3 else 1800
        return cmd_run(arm, budget)
    if cmd == "measure":
        return cmd_measure()
    if cmd == "blind":
        budget = int(sys.argv[2]) if len(sys.argv) > 2 else 1800
        return cmd_blind(budget)
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
