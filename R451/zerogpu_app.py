#!/usr/bin/env python3
"""R451-C1.9 — the ZeroGPU experiment app (a temporary canonical-Space
revision, never a second Space).

The operator's bounded question (verbatim intent): "Can a small
open-weight reasoning model actually run inside the canonical Space's
ZeroGPU allocation and serve Toscanini's transport contract?"

NOT a benchmark: ONE model, ONE probe, ONE measurement. The probe is
Toscanini's own transport contract (the FIELD-line structured-output
completion the engine's calls use — the same probe contract as
transport_capability.probe_route / runtime_admission.probe_capability).

Measured (the operator's field list):
  model, revision, load time, inference latency, token output,
  FIELD contract success, memory, GPU minutes consumed, failure class

The app is a minimal stdlib HTTP server (no framework deps) exposing:
  GET  /            status (no GPU consumption)
  POST /experiment  runs the ONE bounded ZeroGPU probe (idempotent-ish:
                     re-runs are re-measurements, each recorded with
                     its own timestamps; the driver calls it ONCE)

Fail-closed honesty: any failure (import, CUDA init, GPU scheduling,
load, generation, parse) returns a TYPED failure_class — the experiment
records the exact failure and stops (the directive's own rule).
"""
from __future__ import annotations

import json
import os
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# `spaces` must be imported BEFORE torch so its CUDA-zero shim can
# intercept device initialization (the ZeroGPU contract).
try:
    import spaces  # noqa: F401
    SPACES_AVAILABLE = True
except Exception as _exc:  # noqa: BLE001 — typed, recorded
    SPACES_AVAILABLE = False
    _SPACES_IMPORT_ERROR = f"{type(_exc).__name__}: {_exc}"

MODEL_ID = os.environ.get("ZEROGPU_MODEL", "Qwen/Qwen3-1.7B")
MODEL_REVISION = os.environ.get("ZEROGPU_MODEL_REVISION", "")
DURATION_S = int(os.environ.get("ZEROGPU_DURATION_S", "240"))

# Toscanini's transport contract probe (the same prompt the engine's
# capability probes use — MECHANISM/FALSIFIER field lines)
PROBE_PROMPT = (
    "Transport capability probe. Reply with exactly two lines, "
    "nothing else:\n"
    "MECHANISM: a catheter wall resists kinking when the septum is "
    "thick enough\n"
    "FALSIFIER: measure the collapse pressure of the septum"
)

_STATE = {"phase": "idle", "last": None}
_LOCK = threading.Lock()


def _field_lines(content: str) -> dict:
    out = {}
    for line in (content or "").splitlines():
        s = line.strip()
        if s.upper().startswith("MECHANISM:"):
            out["MECHANISM"] = s.split(":", 1)[1].strip()
        elif s.upper().startswith("FALSIFIER:"):
            out["FALSIFIER"] = s.split(":", 1)[1].strip()
    return out


def _run_probe_inner() -> dict:
    """The measurement body (runs INSIDE the ZeroGPU allocation when
    decorated). Returns the operator's 9-field record."""
    rec = {
        "artifact_type": "R451_ZEROGPU_EXPERIMENT",
        "question": ("Can a small open-weight reasoning model actually "
                     "run inside the canonical Space's ZeroGPU "
                     "allocation and serve Toscanini's transport "
                     "contract?"),
        "model": MODEL_ID,
        "revision": MODEL_REVISION or "(main, resolved at load)",
        "duration_budget_s": DURATION_S,
        "spaces_package_available": SPACES_AVAILABLE,
        "probe_contract": "FIELD lines: MECHANISM, FALSIFIER (the "
                          "engine's own transport probe)",
    }
    if not SPACES_AVAILABLE:
        rec.update({"failure_class": "SPACES_IMPORT_FAILED",
                    "failure_detail": _SPACES_IMPORT_ERROR,
                    "field_contract_success": False})
        return rec
    import torch  # after the spaces shim
    import transformers
    t_start = time.time()
    try:
        kw = {"torch_dtype": torch.bfloat16, "device_map": "auto"}
        if MODEL_REVISION:
            kw["revision"] = MODEL_REVISION
        tok = transformers.AutoTokenizer.from_pretrained(MODEL_ID, **(
            {"revision": MODEL_REVISION} if MODEL_REVISION else {}))
        model = transformers.AutoModelForCausalLM.from_pretrained(
            MODEL_ID, **kw)
        model.eval()
        load_s = time.time() - t_start
        rec["load_time_s"] = round(load_s, 2)
        rec["gpu_name"] = torch.cuda.get_device_name(0) \
            if torch.cuda.is_available() else None
        torch.cuda.reset_peak_memory_stats()
        messages = [
            {"role": "system", "content":
                "RESPOND IN ENGLISH ONLY. Follow the requested output "
                "format exactly; no preamble, no markdown fences."},
            {"role": "user", "content": PROBE_PROMPT},
        ]
        prompt = tok.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
            enable_thinking=False)
        ids = tok(prompt, return_tensors="pt").to(model.device)
        t_gen = time.time()
        with torch.no_grad():
            out_ids = model.generate(
                **ids, max_new_tokens=96, do_sample=False,
                pad_token_id=tok.eos_token_id)
        gen_s = time.time() - t_gen
        new_tokens = int(out_ids.shape[1] - ids["input_ids"].shape[1])
        text = tok.decode(out_ids[0][ids["input_ids"].shape[1]:],
                          skip_special_tokens=True)
        fields = _field_lines(text)
        rec.update({
            "inference_latency_s": round(gen_s, 2),
            "tokens_per_second": round(new_tokens / gen_s, 2) if gen_s
            else None,
            "token_output": new_tokens,
            "raw_output": text[:600],
            "field_contract_success": bool(fields),
            "field_lines_found": sorted(fields),
            "memory": {
                "max_allocated_gb": round(
                    torch.cuda.max_memory_allocated() / 1e9, 2),
                "total_reserved_gb": round(
                    torch.cuda.memory_reserved() / 1e9, 2),
                "device_total_gb": round(
                    torch.cuda.get_device_properties(0).total_memory
                    / 1e9, 2),
            },
            "gpu_minutes_consumed_estimate": round(
                (time.time() - t_start) / 60.0, 2),
            "failure_class": None,
        })
        return rec
    except Exception as exc:  # noqa: BLE001 — typed, recorded
        rec.update({
            "failure_class": type(exc).__name__.upper(),
            "failure_detail": f"{type(exc).__name__}: {exc}"[:400],
            "traceback_tail": traceback.format_exc()[-800:],
            "field_contract_success": False,
        })
        return rec


# The ZeroGPU-decorated entry point (the allocation attaches for the
# duration of ONE call — the bounded experiment)
if SPACES_AVAILABLE:
    @spaces.GPU(duration=DURATION_S)
    def run_probe() -> dict:
        return _run_probe_inner()
else:
    def run_probe() -> dict:
        return _run_probe_inner()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, indent=1, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 — stdlib naming
        if self.path in ("/", "/status", "/experiment/status"):
            with _LOCK:
                state = dict(_STATE)
            self._send(200, {
                "status": "ok",
                "experiment": "r451-c1.9 ZeroGPU bounded probe",
                "model": MODEL_ID,
                "revision": MODEL_REVISION or "(main)",
                "spaces_available": SPACES_AVAILABLE,
                "phase": state.get("phase"),
                "last": state.get("last"),
            })
            return
        self._send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802 — stdlib naming
        if self.path != "/experiment":
            self._send(404, {"error": "not found"})
            return
        if os.environ.get("ZEROGPU_EXPERIMENT_TOKEN"):
            auth = self.headers.get("Authorization", "")
            want = "Bearer " + os.environ["ZEROGPU_EXPERIMENT_TOKEN"]
            if auth != want:
                self._send(401, {"error": "unauthorized"})
                return
        with _LOCK:
            if _STATE.get("phase") == "running":
                self._send(409, {"error": "experiment already running"})
                return
            _STATE["phase"] = "running"
        started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            t0 = time.time()
            rec = run_probe()
            rec["wall_time_s"] = round(time.time() - t0, 2)
            rec["started_at"] = started
            rec["finished_at"] = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            rec["verdict"] = (
                "TRANSPORT_RESOURCE_CLASS_VIABLE"
                if rec.get("field_contract_success") else
                ("FAILED_" + str(rec.get("failure_class") or "UNKNOWN")))
            with _LOCK:
                _STATE["phase"] = "done"
                _STATE["last"] = rec
            self._send(200, rec)
        except Exception as exc:  # noqa: BLE001 — typed, recorded
            rec = {
                "failure_class": type(exc).__name__.upper(),
                "failure_detail": f"{type(exc).__name__}: {exc}"[:400],
                "traceback_tail": traceback.format_exc()[-800:],
                "field_contract_success": False,
                "started_at": started,
                "verdict": "FAILED_" + type(exc).__name__.upper(),
            }
            with _LOCK:
                _STATE["phase"] = "failed"
                _STATE["last"] = rec
            self._send(200, rec)

    def log_message(self, fmt, *args):  # quiet
        print("[zerogpu-app] " + (fmt % args), flush=True)


def main() -> int:
    port = int(os.environ.get("PORT", "7860"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"[zerogpu-app] listening on {port} "
          f"(spaces={SPACES_AVAILABLE}, model={MODEL_ID})", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
