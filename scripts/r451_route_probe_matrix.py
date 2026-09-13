#!/usr/bin/env python3
"""R451-C1.2 — the ROUTE PROBE MATRIX driver (operator directive,
2026-09-13, section 14, verbatim order):

    Qwen3.8-27B / Novita
    Qwen3.8-27B / DeepInfra
    GLM-5.3-Flash / Together
    GLM-5.3-Flash / Fireworks
    Gemma 4 26B A4B / DeepInfra
    Qwen3-14B / DeepInfra
    Qwen3-4B-Thinking / ZeroGPU/self-hosted
    (+ resource-class completeness rows: tokenrouter external API,
     the sandbox gateway, and the localqwen self-hosted route)

For each route record (operator's 11 fields):
    provider, model, HTTP status, latency, token usage, tool support,
    structured-output support, response validity, failure class,
    quota/credit behavior, timestamp

The output is a TRANSPORT CAPABILITY MATRIX, not a model ranking
(the operator's explicit framing: "The output should be a transport
capability matrix, not a model ranking").

Honest expected state for THIS environment (recorded, never assumed):
  - HF_TOKEN is NOT present in this coding session (it was
    session-scoped in R450 and is never persisted — BS-021). Every
    HF-router route therefore measures PROVIDER_UNAVAILABLE
    (credential absent), with the R450-recorded account state (402
    'depleted monthly included credits' on every model, token auth
    fine) quoted as PRIOR evidence — not claimed as this session's
    measurement (Art. XXV).
  - The operator action that unblocks the hosted-route probes is
    recorded in the artifact (Art. LXXI §4 escalation discipline):
    export HF_TOKEN into this session.

Usage: python3 scripts/r451_route_probe_matrix.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from discovery_fabric.engine import transport_capability as tc  # noqa: E402

OUT_PATH = REPO / "R451" / "TRANSPORT_CAPABILITY_MATRIX.json"


def main() -> int:
    # the same call-time credential bootstrap the engine uses
    from discovery_fabric.engine.adapters import load_credentials
    loaded = load_credentials()
    print(f"[0] credentials loaded: {sorted(loaded)} "
          f"(HF_TOKEN present: {bool(os.environ.get('HF_TOKEN', ''))})")

    # the local llama-server must be alive for the self-hosted probe;
    # the CAD bridge driver's watchdog normally keeps it up — probe
    # with a generous timeout because a long generation may hold the
    # single slot (measured queueing behind the CAD driver is honest)
    import r451_local_qwen as lq  # noqa: E402
    if not lq._proc_alive():
        print("[0] llama-server down — starting it for the local probe")
        assert lq.ensure_server(), "llama-server failed to start"
    os.environ.setdefault("LOCAL_QWEN_BASE_URL",
                          lq.BASE + "/v1/chat/completions")

    probes = {}
    for route in tc.ROUTE_CATALOG:
        print(f"[probe] {route.route_id} ...", flush=True)
        timeout_s = 240 if route.provider == "localqwen" else 45
        rec = tc.probe_route(route, timeout_s=timeout_s)
        probes[route.route_id] = rec
        print(f"    -> class={rec.get('failure_class')} "
              f"http={rec.get('http_status')} "
              f"latency={rec.get('latency_ms')}ms "
              f"fields={rec.get('field_lines_found') or '-'}")

    matrix = tc.capability_matrix(probes=probes, persist=True)

    # the operator action that would complete the hosted-route probes
    matrix["blocked_operator_action"] = {
        "article": "LXXI §4",
        "missing_credential": "HF_TOKEN (session-scoped; never persisted "
                              "in the repo — BS-021)",
        "action": ("export HF_TOKEN into the coding session, then "
                   "re-run scripts/r451_route_probe_matrix.py — the "
                   "probe matrix then measures the account state "
                   "directly (R450's recorded measurement: HTTP 402 "
                   "'You have depleted your monthly included credits' "
                   "on every probed model while the token itself "
                   "authenticated; buying credits is NOT required to "
                   "probe — a 402 is itself the honest measurement)"),
        "escalation_note": ("the zero-paid local route is NOT blocked "
                            "by this: discovery runs without any hosted "
                            "credential (the R451-C1.1 acceptance chain "
                            "proved this with 82 local / 0 paid calls)"),
    }

    # ---- the LIVE smoke call through the ADMITTED route (the matrix's
    # whole purpose: which route may the ENGINE actually use right now).
    # One tiny FIELD-line generation through the ORDINARY registry path
    # (llm_registry.generate, cost-policy-filtered) — no special-case
    # transport, no bypassed policy. This connects the capability
    # matrix to the engine's real call path TODAY (the full fresh
    # problem -> candidate chain is the recorded ACCEPTANCE_RUN_P2).
    smoke = None
    try:
        from discovery_fabric.engine.llm_registry import (
            SelectionPolicy, generate)
        res = generate(
            "Reply with exactly one line:\n"
            "MECHANISM: a thicker septum resists suction collapse",
            system="RESPOND IN ENGLISH ONLY. Follow the requested "
                   "output format exactly; no preamble, no markdown "
                   "fences.",
            policy=SelectionPolicy(
                preferred_providers=["localqwen"], purpose="general"),
            max_tokens=48, timeout=240)
        smoke = {
            "purpose": "admitted-route live smoke (FIELD-line contract "
                       "through the ordinary registry path)",
            "status": res.status,
            "provider": res.provider_id,
            "model": res.model,
            "latency_ms": res.latency_ms,
            "field_line_ok": bool(
                res.ok and "MECHANISM:" in (res.content or "")),
            "cost_provenance": res.cost_provenance,
            "route": res.route,
        }
    except Exception as exc:  # noqa: BLE001 — disclosed, never silent
        smoke = {"status": "CALL_FAILED", "error": f"{type(exc).__name__}"
                                               f": {exc}"}
    matrix["admitted_route_live_smoke"] = smoke

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(matrix, indent=1, ensure_ascii=False,
                                   default=str))

    # ---- the honest summary (never a model ranking) -------------------
    print("\n=== TRANSPORT CAPABILITY MATRIX (capability, not ranking) ===")
    for row in matrix["routes"]:
        p = row["probe"] or {}
        print(f"{row['route_id']:<48} "
              f"class={str(p.get('failure_class')):<20} "
              f"admitted={row['admitted']}")
    print(f"admitted routes: {matrix['admitted_routes']}")
    print(f"economic redundancy: "
          f"{matrix['economic_redundancy']['distinct_economic_domains']} "
          f"distinct account domain(s)")
    for w in (matrix["economic_redundancy"].get("shared_domain_warning")
              or []):
        print(f"  WARNING (same economic account): {w}")
    print(f"\nrecord: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
