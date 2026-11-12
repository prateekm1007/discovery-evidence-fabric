#!/usr/bin/env python3
"""R6 A1 replay-lookup microbenchmark — local, deterministic, zero LLM.

Measures the shipped record/replay primitives on THIS machine:

  * `llm_cache_key` (hash construction)
  * `cache_get` on a recorded hit (JSON read + parse)
  * `stage_memo_key` (stage identity + config + engine-code digest +
    canonical upstream state)
  * `stage_memo_lookup` on a recorded hit

These are LOOKUP costs, not live-run latency: a provider call is orders
of magnitude slower, and no claim about provider wall time is made here
(Art. XXV). The benchmark uses a temporary economy store, so it never
touches the repo's `.llm_cache/`.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

OUT = REPO / "eval" / "score" / "R6_REPLAY_LATENCY.json"
#: stage_memo_key re-scans the engine/retrieval file tree for its code
#: signature on every call (~10s of ms on Windows), so it gets a smaller
#: sample than the pure hash/file-read primitives.
N = 2000
N_STAGE_KEY = 200


def _pct(values: list[float], p: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    idx = min(len(ordered) - 1, int(round((p / 100.0) * (len(ordered) - 1))))
    return ordered[idx]


def _bench(fn, n: int = N) -> dict:
    samples: list[float] = []
    for _ in range(n):
        t0 = time.perf_counter_ns()
        fn()
        samples.append((time.perf_counter_ns() - t0) / 1000.0)  # us
    return {
        "n": n,
        "p50_us": round(_pct(samples, 50), 3),
        "p95_us": round(_pct(samples, 95), 3),
        "p99_us": round(_pct(samples, 99), 3),
        "mean_us": round(statistics.mean(samples), 3),
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="r6_replay_lat_") as tmp:
        os.environ["FABRIC_LLM_CACHE"] = "rw"
        os.environ["FABRIC_LLM_ECONOMY_DIR"] = tmp
        from discovery_fabric.engine import llm_economy as econ

        messages = [{"role": "system", "content": "s"},
                    {"role": "user", "content": "u" * 200}]
        key = econ.llm_cache_key("provider", "model", messages, 1024, None)
        econ.cache_put(key, {"content": "answer", "finish_reason": "stop"})
        assert econ.cache_get(key) is not None

        stage_key = econ.stage_memo_key(
            "MECHANISM_SPACE", "cap/1.0", "mod.py", "fn",
            "def fn(env):\n    return {'a': 1}\n",
            {"upstream": {"hash": "x" * 64}, "problem": "p"})
        econ.stage_memo_put(stage_key, {"payload": "x" * 200})
        assert econ.stage_memo_lookup(stage_key) is not None

        result = {
            "instrument": ("r6_replay_latency/1.0 — local lookup "
                           "microbenchmark; zero LLM spend"),
            "machine": {"platform": sys.platform, "python": sys.version},
            "cache_mode": econ.cache_mode(),
            "measurements": {
                "llm_cache_key": _bench(
                    lambda: econ.llm_cache_key(
                        "provider", "model", messages, 1024, None)),
                "cache_get_hit": _bench(lambda: econ.cache_get(key)),
                "stage_memo_key": _bench(lambda: econ.stage_memo_key(
                    "MECHANISM_SPACE", "cap/1.0", "mod.py", "fn",
                    "def fn(env):\n    return {'a': 1}\n",
                    {"upstream": {"hash": "x" * 64}, "problem": "p"}),
                    n=N_STAGE_KEY),
                "stage_memo_lookup_hit": _bench(
                    lambda: econ.stage_memo_lookup(stage_key)),
            },
            "disclosures": [
                ("These are LOCAL lookup costs on the reporting machine, "
                 "not live end-to-end run latency. Provider round-trip "
                 "time is not measured here."),
                ("A replay hit spends zero provider calls; the cache_get "
                 "measurement is the local price paid instead of a "
                 "provider request."),
                ("stage_memo_key includes the engine/retrieval code+JSON "
                 "digest; the digest is process-cached and refreshed only "
                 "when a file size/mtime changes."),
            ],
        }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(json.dumps(result["measurements"], indent=1))
    print(f"written {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
