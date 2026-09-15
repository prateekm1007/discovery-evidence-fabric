#!/usr/bin/env python3
"""R467 — the registry smoke: the engine's own generate() path with the
ATRIA_API_KEY present (the registration's end-to-end verification —
the same call path the worker's preflight probe and every stage uses).

Records: the route walked (provider/model per hop), the typed result,
the task-degradation record, and the cost provenance. Run with the key
in the environment (BS-021); the artifact records fingerprints only.
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import llm_registry as reg  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "R467" / "REGISTRY_SMOKE.json"


def main() -> int:
    key = os.environ.get("ATRIA_API_KEY", "").strip()
    if not key:
        print("FATAL: ATRIA_API_KEY unset")
        return 2
    out = {"round": "R467", "measured_at": time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "key_fingerprint": f"{key[:6]}...{key[-4:]} (len {len(key)})"}

    # the default policy walk (what preflight_probe does)
    res = reg.generate(prompt="Reply with exactly: READY",
                       system="transport health probe",
                       timeout=120, max_retries=0)
    out["default_walk"] = {
        "status": res.status, "provider": res.provider_id,
        "model": res.model, "latency_ms": res.latency_ms,
        "content_head": (res.content or "")[:80],
        "task_degradation": res.task_degradation,
        "cost_provenance": res.cost_provenance,
        "route": [
            {"provider": h.get("provider_attempted"),
             "model": h.get("model"),
             "failure_type": h.get("failure_type")}
            for h in (res.route or [])]}
    print(f"[default walk] {res.status} via {res.provider_id}/"
          f"{res.model} in {res.latency_ms}ms")

    # the STRONG synthesis walk (the MECHANISM-stage question): the
    # role->task mapping resolves synthesis -> TASK_STRONG (the exact
    # request class MECHANISM_SPACE makes)
    res2 = reg.generate(
        prompt="Answer with EXACTLY three lines starting FIELD_, keys "
               "MECHANISM, KEY_VARIABLE, FALSIFIER. Topic: why does a "
               "copper pipe corrode faster in hot acidic water?",
        system="mechanism synthesis", timeout=180, max_retries=0,
        max_tokens=2000, role="synthesis")
    deg = res2.task_degradation or {}
    out["strong_walk"] = {
        "status": res2.status, "provider": res2.provider_id,
        "model": res2.model, "latency_ms": res2.latency_ms,
        "requested_task": deg.get("requested_task"),
        "served_capability": deg.get("served_capability")
        or deg.get("capability"),
        "degraded": deg.get("degraded"),
        "content_head": (res2.content or "")[:200],
        "task_degradation": deg}
    n_field = sum(1 for ln in (res2.content or "").splitlines()
                  if ln.strip().startswith("FIELD_"))
    out["strong_walk"]["field_lines"] = n_field
    print(f"[strong walk] {res2.status} via {res2.provider_id}/"
          f"{res2.model} in {res2.latency_ms}ms field_lines={n_field} "
          f"degraded={deg.get('degraded')}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"artifact -> {OUT.relative_to(OUT.parents[1])}")
    ok = (res.status == "OK" and res.provider_id == "atria"
          and res2.status == "OK" and res2.provider_id == "atria"
          and n_field >= 3 and not deg.get("degraded"))
    print("SMOKE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
