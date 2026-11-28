#!/usr/bin/env python3
"""r129_bon_run.py — the Phase-B lever 1 RUN (claim c-0205; the prereg
eval/r129_bon_prereg.json governs).

24 r125_f31e_set items, the ablation arm: TWO independent bare-author
candidates per item (the F31e draw mechanics, byte-identical authoring
bytes) -> the canonical check_layer bind battery on each -> reviewer
fix only candidates with findings (frozen v1 directive bytes + the
accepted Phase-A one-field response_format contract) -> selection by
the deterministic bill_defect_classes byte rule on the delivered bytes
(fewer classes wins; tie -> candidate 1; typed-fail -> +inf; both fail
-> item TYPED_CALL_FAIL). Parse failures are typed and NEVER retried.
Zero engine lines: scripts/ + eval/ only (Art. 27 disclosure).

Usage: python3 scripts/r129_bon_run.py [--workers 2]
Writes: eval/r129_bon_run/bon_{pid}.json (byte-resume)
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

OUT = REPO / "eval" / "r129_bon_run"
OUT.mkdir(parents=True, exist_ok=True)

from r7_queue_runner import _load_key_vault  # noqa: E402

_load_key_vault()

import discovery_fabric.engine.route_adapter as ra  # noqa: E402
from r121_successor_run import check_layer  # noqa: E402
from r125_f31e_run import IMPROVED_DIRECTIVE, authoring_prompt  # noqa: E402

V = "agnes-3.0-flash"
WORKERS = 2
SPACING_S = 8
PRINT_LOCK = threading.Lock()

# the accepted Phase-A output contract (the prereg: reviewer bytes +
# contract are the FROZEN accepted config; the only variable is
# candidate count + selection)
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
                                what: str = "",
                                attempts_out: list | None = None) -> dict:
    """The ESTABLISHED AGNES transport pattern (the committed Phase-A
    amendment: 4 attempts, 120 s sleeps, rate_limited/transport ONLY;
    auth/missing_key fail immediately; parse failures NEVER retried).
    Per-leg transport_attempts lands in the records (r128 dir-5)."""
    last: Exception | None = None
    for attempt in (1, 2, 3, 4):
        if attempts_out is not None:
            attempts_out.append(attempt)
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
    return {"prompt_tokens": u.get("prompt_tokens") or 0,
            "completion_tokens": u.get("completion_tokens"),
            "cached_tokens": ptd.get("cached_tokens")}


def one_candidate(prob: dict, pid: str, cand: str, t0: float) -> dict:
    """One candidate: author -> bind battery -> reviewer-if-findings
    -> delivered bytes. Terminal states: DELIVERED_REVIEWED,
    DELIVERED_BARE, TYPED_CALL_FAIL, TYPED_PARSE_FAIL."""
    rec: dict = {"candidate": cand, "calls": [], "parse_retries": 0}
    # leg 1: bare author (byte-identical composition, F31e mechanics)
    ca = {"leg": "author", "transport_attempts": 1}
    att_a: list = []
    try:
        time.sleep(SPACING_S)
        ta = time.monotonic()
        resp = call_with_transport_backoff(
            authoring_prompt(prob), 1200,
            what=f"{pid}/{cand}/author", attempts_out=att_a)
        ca["transport_attempts"] = len(att_a)
        ca["latency_s"] = round(time.monotonic() - ta, 2)
        ca["usage"] = usage_snapshot(resp)
        bill = resp.get("content") or ""
        rec["authored_bill"] = bill
    except Exception as e:  # noqa: BLE001
        ca["typed_fail"] = f"{type(e).__name__}: {str(e)[:140]}"
        rec["calls"].append(ca)
        rec["status"] = "TYPED_CALL_FAIL"
        return rec
    rec["calls"].append(ca)
    # leg 2: the canonical bind battery (deterministic, zero LLM)
    vio = check_layer(prob, bill, None)
    findings = [f"{k}: {'; '.join(map(str, v))[:110]}"
                for k, v in vio.items() if v]
    rec["surfaced_findings"] = findings
    rec["surfaced_scan"] = {k: list(v) for k, v in vio.items()}
    if not findings:
        rec["delivered_bill"] = bill
        rec["reviewer_skipped"] = True
        rec["post_review_scan"] = {}
        rec["status"] = "DELIVERED_BARE"
        return rec
    # leg 3: the schema-enforced reviewer (frozen v1 bytes)
    cr = {"leg": "reviewer", "transport_attempts": 1}
    att_r: list = []
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
            what=f"{pid}/{cand}/reviewer", attempts_out=att_r)
        cr["transport_attempts"] = len(att_r)
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
            rec["status"] = "TYPED_PARSE_FAIL"
            return rec
    except Exception as e:  # noqa: BLE001
        cr["typed_fail"] = f"{type(e).__name__}: {str(e)[:140]}"
        rec["calls"].append(cr)
        rec["status"] = "TYPED_CALL_FAIL"
        return rec
    rec["calls"].append(cr)
    rec["delivered_bill"] = delivered
    rescan = check_layer(prob, delivered, None)
    rec["post_review_scan"] = {k: list(v) for k, v in rescan.items()}
    rec["status"] = "DELIVERED_REVIEWED"
    return rec


def one_problem(prob: dict) -> dict:
    pid = prob["problem_id"]
    rec: dict = {"problem_id": pid, "registered_model": V,
                 "arm": "bon2-bindselect (the r129 prereg; selection "
                        "by bill_defect_classes on delivered bytes, "
                        "tie -> candidate 1, typed-fail -> +inf)",
                 "wall_clock_s": None}
    t0 = time.monotonic()
    cands = [one_candidate(prob, pid, f"c{i+1}", t0) for i in (0, 1)]
    rec["candidates"] = cands
    # selection by the deterministic defect classes (the prereg rule)
    from r121_successor_score import bill_defect_classes  # noqa: E402
    scores = []
    for c in cands:
        if c.get("delivered_bill"):
            scores.append(len(bill_defect_classes(prob,
                                                  c["delivered_bill"])))
        else:
            scores.append(10 ** 6)  # typed-fail -> +inf (prereg)
    rec["selection_scores"] = scores
    win = min(range(len(scores)), key=lambda i: (scores[i], i))
    rec["selected_candidate"] = f"c{win + 1}"
    rec["selection_tie"] = scores[0] == scores[1]
    sel = cands[win]
    rec["delivered_bill"] = sel.get("delivered_bill")
    rec["selected_defect_classes"] = (bill_defect_classes(
        prob, rec["delivered_bill"]) if rec["delivered_bill"] else None)
    both_fail = all(c.get("status") in ("TYPED_CALL_FAIL",
                                        "TYPED_PARSE_FAIL")
                    for c in cands)
    rec["status"] = "TYPED_CALL_FAIL" if both_fail else sel["status"]
    rec["wall_clock_s"] = round(time.monotonic() - t0, 2)
    return rec


def main() -> int:
    workers = WORKERS
    if "--workers" in sys.argv:
        workers = int(sys.argv[sys.argv.index("--workers") + 1])
    print(f"BON2-BINDSELECT RUN: 24 items x 2 candidates, "
          f"{workers} workers (the prereg governs)", flush=True)
    if not quota_probe():
        (OUT.parent / "r129_bon_INFRA_QUOTA_WALL").write_text(
            "the quota probe failed at run start\n", encoding="utf-8")
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
            (OUT / f"bon_{rec['problem_id']}.json").write_text(
                json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            done += 1
            with PRINT_LOCK:
                print(f"  [{done}/24] {rec['problem_id']}: "
                      f"{rec['status']} sel=c{rec['selected_candidate']} "
                      f"scores={rec['selection_scores']} "
                      f"wall={rec['wall_clock_s']}s", flush=True)
    print(f"ALL DONE in {round(time.monotonic() - t0, 1)}s "
          f"wall (pool of {workers})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
