#!/usr/bin/env python3
"""r127_phaseA_gate.py — the Phase-A SPEED GATE RUN (claim c-0200;
the prereg eval/r127_phaseA_prereg.json governs).

12 r125_f31e_set problems, one fresh draw, the full chain per
problem (bare author -> canonical check -> schema-enforced reviewer
-> rescan), timed end-to-end, the independent problems run in a
4-worker thread pool. The reviewer directive stays the FROZEN v1
bytes (the twin's clause is NOT mixed in); the ONLY lever under test
is the output contract (response_format json_schema, one required
field) + the instrumentation. Parse failures are typed
TYPED_PARSE_FAIL (fail-closed, NO retry loop).

Usage: python3 scripts/r127_phaseA_gate.py [--workers 4]
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT = REPO / "eval" / "r127_phaseA" / "gate"
OUT.mkdir(parents=True, exist_ok=True)
OUT.parent.mkdir(parents=True, exist_ok=True)

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

import discovery_fabric.engine.route_adapter as ra  # noqa: E402
from r121_successor_run import check_layer  # noqa: E402
from r125_f31e_run import IMPROVED_DIRECTIVE, authoring_prompt  # noqa: E402

V = "agnes-3.0-flash"
WORKERS = 2
SPACING_S = 8
PRINT_LOCK = threading.Lock()

# the Phase-A output contract (the prereg's variable): one required
# field, minimal, neutral — no duty language (the twin's lever)
FIX_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "reviewer_fix",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {"corrected_proposal": {"type": "string"}},
            "required": ["corrected_proposal"],
            "additionalProperties": False,
        },
    },
}


def items():
    return [json.loads(l) for l in (REPO / "eval" / "r125_f31e_set"
            / "items.jsonl").read_text(encoding="utf-8").strip()
            .split("\n") if l]


def quota_probe() -> bool:
    try:
        r = ra.agnes_chat(
            [{"role": "user", "content": "Reply with the single word: READY."}],
            model=V, visible_target=20, timeout_s=120.0)
        return bool((r.get("content") or "").strip())
    except Exception as e:  # noqa: BLE001
        print(f"quota probe FAILED: {type(e).__name__}: {str(e)[:120]}",
              flush=True)
        return False


def call_with_transport_backoff(prompt: str, visible_target: int,
                                response_format=None,
                                what: str = "") -> dict:
    """The ESTABLISHED AGNES transport pattern (the committed F31e
    runner: 4 attempts, 120 s sleeps) restored by the amendment —
    catching ONLY the rate_limited/transport refusal classes;
    auth/missing_key fail immediately. PARSE failures are NEVER
    retried (that is the g2 gate, fail-closed elsewhere)."""
    last: Exception | None = None
    for attempt in (1, 2, 3, 4):
        try:
            return ra.agnes_chat(
                [{"role": "user", "content": prompt}],
                model=V, visible_target=visible_target,
                timeout_s=300.0, response_format=response_format)
        except ra.RouteRefused as e:
            if e.kind in ("auth", "missing_key"):
                raise
            last = e
            print(f"    {what} transport attempt {attempt} "
                  f"refused ({e.kind}); backoff 120s", flush=True)
            if attempt < 4:
                time.sleep(120)
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"    {what} transport attempt {attempt} "
                  f"failed {type(e).__name__}; backoff 120s",
                  flush=True)
            if attempt < 4:
                time.sleep(120)
    raise last if last else RuntimeError("transport backoff exhausted")


def usage_snapshot(resp: dict) -> dict:
    u = (resp or {}).get("usage") or {}
    ptd = u.get("prompt_tokens_details") or {}
    pt = u.get("prompt_tokens") or 0
    return {"prompt_tokens": pt,
            "completion_tokens": u.get("completion_tokens"),
            "cached_tokens": ptd.get("cached_tokens"),
            "cache_hit_rate": (ptd.get("cached_tokens") / pt)
            if pt and ptd.get("cached_tokens") is not None else None}


def one_problem(prob: dict) -> dict:
    pid = prob["problem_id"]
    rec: dict = {"problem_id": pid, "registered_model": V,
                 "arm": "phaseA speed gate (frozen v1 reviewer bytes "
                        "+ response_format contract; bare arm "
                        "byte-identical to F31e)",
                 "calls": [], "parse_retries": 0}
    t0 = time.monotonic()
    # leg 1: bare author (byte-identical composition)
    ca = {"leg": "author", "attempts": 1}
    try:
        ta = time.monotonic()
        resp = call_with_transport_backoff(
            authoring_prompt(prob), 1200,
            what=f"{pid}/author")
        ca["latency_s"] = round(time.monotonic() - ta, 2)
        ca["usage"] = usage_snapshot(resp)
        bill = resp.get("content") or ""
        rec["authored_bill"] = bill
    except Exception as e:  # noqa: BLE001
        ca["typed_fail"] = f"{type(e).__name__}: {str(e)[:140]}"
        rec["calls"].append(ca)
        rec["wall_clock_s"] = round(time.monotonic() - t0, 2)
        rec["status"] = "TYPED_CALL_FAIL"
        return rec
    rec["calls"].append(ca)
    # leg 2: the canonical check (deterministic, untimed LLM-wise)
    vio = check_layer(prob, bill, None)
    findings = [f"{k}: {'; '.join(map(str, v))[:110]}"
                for k, v in vio.items() if v]
    rec["surfaced_findings"] = findings
    rec["surfaced_scan"] = {k: list(v) for k, v in vio.items()}
    if not findings:
        rec["delivered_bill"] = bill
        rec["reviewer_skipped"] = True
        rec["post_review_scan"] = {}
        rec["wall_clock_s"] = round(time.monotonic() - t0, 2)
        rec["status"] = "DELIVERED_BARE"
        return rec
    # leg 3: the schema-enforced reviewer (frozen v1 bytes)
    cr = {"leg": "reviewer", "attempts": 1}
    prompt = (IMPROVED_DIRECTIVE + "\n\nORIGINAL PROBLEM:\n"
              + json.dumps({k: prob.get(k, "") for k in
                            ("problem_id", "device", "failure",
                             "constraint")}, ensure_ascii=False)
              + "\n\nPROPOSAL UNDER REVIEW:\n" + bill
              + "\n\nSURFACED FINDINGS (fix these):\n"
              + "\n".join(f"- {f}" for f in findings))
    try:
        time.sleep(SPACING_S)
        tr = time.monotonic()
        resp = call_with_transport_backoff(
            prompt, 4000, response_format=FIX_SCHEMA,
            what=f"{pid}/reviewer")
        cr["latency_s"] = round(time.monotonic() - tr, 2)
        cr["usage"] = usage_snapshot(resp)
        raw = resp.get("content") or ""
        cr["raw_head"] = raw[:100]
        try:
            obj = json.loads(raw)
            delivered = str(obj.get("corrected_proposal") or "")
            if not delivered.strip():
                raise ValueError("empty corrected_proposal")
            cr["schema_parsed_first_try"] = True
        except Exception as e:  # noqa: BLE001
            cr["schema_parsed_first_try"] = False
            cr["parse_fail"] = f"{type(e).__name__}: {str(e)[:140]}"
            rec["calls"].append(cr)
            rec["delivered_bill"] = None
            rec["parse_retries"] = 0  # NO retry loop, by prereg
            rec["wall_clock_s"] = round(time.monotonic() - t0, 2)
            rec["status"] = "TYPED_PARSE_FAIL"
            return rec
    except Exception as e:  # noqa: BLE001
        cr["typed_fail"] = f"{type(e).__name__}: {str(e)[:140]}"
        rec["calls"].append(cr)
        rec["wall_clock_s"] = round(time.monotonic() - t0, 2)
        rec["status"] = "TYPED_CALL_FAIL"
        return rec
    rec["calls"].append(cr)
    rec["delivered_bill"] = delivered
    rescan = check_layer(prob, delivered, None)
    rec["post_review_scan"] = {k: list(v) for k, v in rescan.items()}
    rec["wall_clock_s"] = round(time.monotonic() - t0, 2)
    rec["status"] = "DELIVERED_REVIEWED"
    return rec


def main() -> int:
    workers = 4
    if "--workers" in sys.argv:
        workers = int(sys.argv[sys.argv.index("--workers") + 1])
    print(f"PHASE-A SPEED GATE RUN: 12 problems x 1 draw, "
          f"{workers} workers (the prereg governs)", flush=True)
    if not quota_probe():
        (OUT.parent / "INFRA_QUOTA_WALL").write_text(
            "the quota probe failed at gate-run start\n",
            encoding="utf-8")
        print("REFUSED (typed INFRA_QUOTA_WALL)", flush=True)
        return 3
    probs = items()
    t0 = time.monotonic()
    done = 0
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(one_problem, p): p["problem_id"]
                for p in probs}
        for fut in cf.as_completed(futs):
            rec = fut.result()
            (OUT / f"gate_{rec['problem_id']}.json").write_text(
                json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            done += 1
            with PRINT_LOCK:
                print(f"  [{done}/12] {rec['problem_id']}: "
                      f"{rec['status']} wall={rec['wall_clock_s']}s "
                      f"parse_retries={rec['parse_retries']}",
                      flush=True)
    print(f"ALL DONE in {round(time.monotonic() - t0, 1)}s "
          f"wall (pool of {workers})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
