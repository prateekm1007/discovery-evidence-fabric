#!/usr/bin/env python3
"""R451-C1.1 Step 3 — the LOCAL_PROVIDER_READY proof chain.

The directive (verbatim):

    Require:
    binary available
    ↓
    model available
    ↓
    server starts
    ↓
    HTTP endpoint responds
    ↓
    tiny completion succeeds
    ↓
    Toscanini structured-output completion succeeds

    Only then:
    LOCAL_PROVIDER_READY = true

    Do not equate process health with usable inference.

Every rung is MEASURED (a real probe / a real completion), each rung's
result is recorded, and the flag is true ONLY when every rung passed.
The record persists to R451/LOCAL_PROVIDER_READY.json with the model
card and each rung's measured latency.

Usage: python3 scripts/r451_local_provider_ready.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r451_local_qwen as lq  # noqa: E402

OUT_PATH = REPO / "R451" / "LOCAL_PROVIDER_READY.json"

#: a real scientific abstract for the structured-output rung (the same
#: evidence shape the synthesis stage consumes — open access, quoted
#: for the probe only)
PROBE_PAPER = {
    "title": "Erosion-resistant materials in slurry transport",
    "abstract": (
        "Slurry erosion of white cast irons was measured in quartz "
        "slurry at 40 percent solids. Erosion rate falls with carbide "
        "volume fraction above 35 percent, while toughness falls above "
        "45 percent. Natural rubber linings outlast white iron by 3x "
        "below 60 C in abrasive acid slurry, but degrade above 80 C."),
}


def _rung(name: str, ok: bool, detail: str, **extra) -> dict:
    return {"rung": name, "ok": bool(ok), "detail": detail[:400], **extra}


def main() -> int:
    rungs = []

    # ---- rung 1: binary available -----------------------------------
    binary = lq.BIN / "llama-server"
    version = ""
    if binary.exists() and os.access(str(binary), os.X_OK):
        try:
            env = dict(os.environ)
            env["LD_LIBRARY_PATH"] = str(lq.BIN)
            r = subprocess.run(
                [str(binary), "--version"], capture_output=True,
                text=True, timeout=30, env=env)
            version = (r.stdout or r.stderr or "").strip().splitlines()[
                0][:120]
        except Exception as exc:  # noqa: BLE001
            version = f"version probe failed: {exc}"
        rungs.append(_rung("binary_available", True,
                           f"{binary} executable; {version}",
                           path=str(binary), version=version))
    else:
        rungs.append(_rung("binary_available", False,
                           f"llama-server binary missing at {binary}"))

    # ---- rung 2: model available (sha256 VERIFIED) -------------------
    import hashlib
    if lq.GGUF.exists():
        h = hashlib.sha256()
        with open(lq.GGUF, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        digest = h.hexdigest()
        expected = lq.MODEL_CARD["gguf_sha256"]
        rungs.append(_rung("model_available", digest == expected,
                           f"GGUF present; sha256 "
                           f"{'VERIFIED' if digest == expected else 'MISMATCH'}",
                           path=str(lq.GGUF),
                           sha256=digest,
                           sha256_verified=digest == expected,
                           size_bytes=lq.GGUF.stat().st_size))
    else:
        rungs.append(_rung("model_available", False,
                           f"GGUF missing at {lq.GGUF}"))

    # ---- rung 3: server starts ---------------------------------------
    t0 = time.time()
    server_up = lq.ensure_server()
    startup_s = round(time.time() - t0, 1)
    rungs.append(_rung("server_starts", server_up,
                       f"llama-server health endpoint reachable "
                       f"({'already up' if startup_s < 0.5 else f'started in {startup_s}s'} "
                       f"at {lq.BASE})",
                       startup_s=startup_s, endpoint=lq.BASE + "/health"))

    # ---- rung 4: HTTP endpoint responds -------------------------------
    # a POST with an invalid body on the REAL inference route: a
    # live endpoint answers 400 (bad request) — the route exists and
    # the server is answering; a dead port answers nothing at all
    import urllib.request
    endpoint_ok, endpoint_detail = False, ""
    try:
        req = urllib.request.Request(
            lq.BASE + "/v1/chat/completions", data=b"{}",
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            endpoint_detail = f"unexpected 200 for an empty body: {resp.status}"
    except Exception as exc:  # noqa: BLE001
        code = getattr(exc, "code", None)
        endpoint_ok = code in (400, 422, 500)
        endpoint_detail = (f"POST /v1/chat/completions (empty body) -> "
                           f"HTTP {code} — the inference route "
                           f"responds") if endpoint_ok else \
            f"endpoint did not respond: {exc}"
    rungs.append(_rung("http_endpoint_responds", endpoint_ok,
                       endpoint_detail))

    # ---- rung 5: tiny completion succeeds -----------------------------
    tiny_ok, tiny_detail, tiny_latency = False, "", None
    if server_up:
        try:
            content, dt, _usage = lq.chat(
                "Reply with exactly: READY", "transport health probe", 8)
            tiny_latency = round(dt, 2)
            tiny_ok = "READY" in (content or "").strip().upper()
            tiny_detail = (f"tiny completion in {dt:.1f}s -> "
                           f"{(content or '').strip()[:40]!r}")
        except Exception as exc:  # noqa: BLE001
            tiny_detail = f"tiny completion failed: {exc}"
    rungs.append(_rung("tiny_completion_succeeds", tiny_ok,
                       tiny_detail, latency_s=tiny_latency))

    # ---- rung 6: Toscanini structured-output completion ---------------
    # the REAL synthesis FIELD-line contract, through the REAL registry
    # (localqwen), parsed by the REAL parser
    structured_ok, structured_detail = False, ""
    fields_present: dict = {}
    if tiny_ok:
        os.environ["LOCAL_QWEN_BASE_URL"] = lq.BASE + \
            "/v1/chat/completions"
        os.environ.setdefault("ENGINE_MODEL_COST_POLICY",
                              "ZERO_PAID_COST")
        try:
            from discovery_fabric.a2.synthesize import SYNTHESIS_PROMPT
            from discovery_fabric.engine.llm_registry import (
                SelectionPolicy, generate)
            prompt = SYNTHESIS_PROMPT.format(
                device="tailings slurry pump impeller",
                failure="hydro-abrasive erosion destroys the "
                        "chromium-molybdenum white-iron impeller every "
                        "1100 running hours in acidic quartz slurry",
                constraint="service life beyond 6000 hours; weldable "
                           "on site; efficiency within 2 points of "
                           "optimal",
                title=PROBE_PAPER["title"],
                abstract=PROBE_PAPER["abstract"])
            res = generate(prompt, system="You are a mechanism "
                           "interpreter for engineering problem-solving",
                           max_tokens=400,
                           policy=SelectionPolicy(purpose="synthesis"))
            if not res.ok:
                structured_detail = (f"registry call failed: "
                                     f"{res.status} {res.error}")
            else:
                fields = ["MECHANISM", "INTERVENTION",
                          "EXPECTED_EFFECT", "FALSIFICATION_TEST",
                          "MECHANISM_SOURCE_SPAN"]
                parsed = {f.lower(): "" for f in fields}
                pattern = re.compile(
                    rf"^({'|'.join(fields)})\s*:\s*(.*)$",
                    re.MULTILINE)
                for m in pattern.finditer(res.content or ""):
                    parsed[m.group(1).lower()] = m.group(2).strip()
                fields_present = parsed
                required = ["mechanism", "intervention",
                            "expected_effect"]
                structured_ok = all(parsed[f] for f in required)
                missing = [f for f in fields
                           if not parsed[f.lower()]]
                structured_detail = (
                    f"provider={res.provider_id} model={res.model}; "
                    f"required fields present: {structured_ok}; "
                    f"missing: {missing or 'none'}; "
                    f"span verbatim: "
                    f"{bool(parsed['mechanism_source_span'] and parsed['mechanism_source_span'][:60] in PROBE_PAPER['abstract'])}")
        except Exception as exc:  # noqa: BLE001
            structured_detail = f"structured probe failed: {exc}"
    rungs.append(_rung("toscanini_structured_output_succeeds",
                       structured_ok, structured_detail,
                       fields=fields_present))

    ready = all(r["ok"] for r in rungs)
    from datetime import datetime, timezone
    record = {
        "artifact_type": "LOCAL_PROVIDER_READY",
        "round": "R451-C1.1",
        "local_provider_ready": ready,
        "rule": ("LOCAL_PROVIDER_READY is true ONLY when all six rungs "
                 "pass: binary -> model (sha256 verified) -> server -> "
                 "HTTP endpoint -> tiny completion -> Toscanini "
                 "structured-output completion. Process health is "
                 "never equated with usable inference."),
        "model_card": lq.MODEL_CARD,
        "rungs": rungs,
        "checked_at": datetime.now(timezone.utc).isoformat(
            timespec="seconds"),
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(record, indent=1, ensure_ascii=False))
    print(json.dumps(record, indent=1, ensure_ascii=False)[:2400])
    print(f"\nLOCAL_PROVIDER_READY = {ready}")
    print(f"record: {OUT_PATH}")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
