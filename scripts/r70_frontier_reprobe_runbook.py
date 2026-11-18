#!/usr/bin/env python3
"""r70_frontier_reprobe_runbook.py — the AM63 directive 3 prep: the
frontier re-probe + contract-fit + registration runbook for v10.

The xkiro flagship namespace exits upstream 503 maintenance at
2026-11-19T16:25Z. This tool is the timestamp-gated prep stage:
  - BEFORE the window: typed refusal (zero probes — the gate is the
    auditor's directive, Art. 3);
  - AT/AFTER the window: pull the LIVE xkiro roster, probe candidate
    flagship ids at the REAL expansion contract (the full
    contract_for_v72 system text + max_tokens sized for the full
    deliverable — the r64s4 lesson: a 29-token or 4.6K-token probe is
    insufficient; AM63 d3: "contract-fit test at the 19K-char
    expansion contract"), and score every completion through the r70
    deliverable-class scans (refusal/identity/thrash at admission
    time). Emits eval/r70_frontier_reprobe_candidates.json — ids,
    latency, chars, findings; keys never printed (Art. 17).
cohere/command-a-plus is EXCLUDED outright (falsified c8cc5deb2).
Registration, the auditor's prereg amendment and the re-freeze remain
the gated chain AFTER the probe evidence lands (AM62 is the template).
"""
import datetime
import json
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from discovery_fabric.engine.route_adapter import (  # noqa: E402
    BROWSER_UA, resolve_vault_key)
from r40_machine_v77 import contract_for_v72  # noqa: E402
from r70_deliverable_class_scan import scan_deliverable_class  # noqa: E402
from r70_stated_formula_scan import (  # noqa: E402
    scan_stated_formula_direction)

OUT = REPO / "eval" / "r70_frontier_reprobe_candidates.json"
WINDOW_OPENS = datetime.datetime(2026, 11, 19, 16, 25,
                                 tzinfo=datetime.UTC)
BASE = "https://api.xkiro.com/v1"
EXCLUDED = {"cohere/command-a-plus"}          # falsified (c8cc5deb2)
MAX_PROBES = 6
PROBE_MT = 8192
PRIORITY = ("cohere", "openai", "anthropic", "deepseek", "qwen",
            "moonshot", "lg", "google", "meta-llama", "mistralai")

PROBE_PROBLEM = {
    "problem_id": "R70-PROBE-1", "device": "rooftop HVAC unit",
    "failure": "compressor overheating at high ambient",
    "question": "propose a passive fix and the falsification test",
    "question_type": "intervention-proposal",
    "user_variables": {}}


def _raw(key, model):
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": contract_for_v72(
                "intervention-proposal")},
            {"role": "user", "content": json.dumps(
                PROBE_PROBLEM, ensure_ascii=False)}],
        "max_tokens": PROBE_MT, "temperature": 0.0}).encode()
    req = urllib.request.Request(
        BASE.rstrip("/") + "/chat/completions", data=body, headers={
            "Authorization": f"Bearer {key}", "User-Agent": BROWSER_UA,
            "Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read())
    ch = (d.get("choices") or [{}])[0]
    txt = str((ch.get("message") or {}).get("content") or "")
    return {"served": d.get("model"),
            "finish": ch.get("finish_reason"),
            "chars": len(txt),
            "completion_tokens": (d.get("usage") or {})
            .get("completion_tokens"),
            "latency_s": round(time.time() - t0, 1),
            "deliverable_class_findings": sorted(
                set(list(scan_deliverable_class(txt).keys())
                    + list(scan_stated_formula_direction(txt).keys()))),
            "head": txt[:120].replace("\n", " ")}


def main() -> int:
    now = datetime.datetime.now(datetime.UTC)
    if now < WINDOW_OPENS:
        wait = WINDOW_OPENS - now
        print(f"WINDOW REFUSED (typed, Art. 3): the xkiro flagship "
              f"namespace is still in upstream 503 maintenance; the "
              f"re-probe window opens 2026-11-19T16:25Z "
              f"({wait.days}d {wait.seconds//3600}h "
              f"{(wait.seconds//60)%60}m from now). Zero probes fired.")
        return 3
    key = resolve_vault_key("XKIRO_API_KEY")
    req = urllib.request.Request(
        BASE.rstrip("/") + "/models",
        headers={"Authorization": f"Bearer {key}", "User-Agent":
                 BROWSER_UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        ids = [m.get("id") for m in json.loads(r.read()).get("data", [])
               if m.get("id")]
    cands = [i for i in ids if i not in EXCLUDED]
    cands.sort(key=lambda i: tuple(
        PRIORITY.index(i.split("/")[0]) if i.split("/")[0] in PRIORITY
        else len(PRIORITY) for _ in (0,)))
    cands = cands[:MAX_PROBES]
    print(f"[reprobe] roster live ({len(ids)} ids); probing "
          f"{len(cands)} flagship candidates at the FULL expansion "
          f"contract (max_tokens={PROBE_MT})", flush=True)
    results = []
    for i in cands:
        print(f"  {i} ...", flush=True)
        try:
            results.append({"model_id": i, **_raw(key, i)})
            print(f"    -> chars={results[-1]['chars']} "
                  f"lat={results[-1]['latency_s']}s "
                  f"findings={results[-1]['deliverable_class_findings']}",
                  flush=True)
        except Exception as e:  # noqa: BLE001 — typed probe telemetry
            results.append({"model_id": i,
                            "typed_error": type(e).__name__,
                            "detail": str(e)[:160]})
            print(f"    -> {type(e).__name__}", flush=True)
    record = {
        "record": "R70_FRONTIER_REPROBE_CANDIDATES/1.0.0",
        "session": "builder-r64s4 (continuation)",
        "window": "2026-11-19T16:25Z (maintenance exit)",
        "excluded": sorted(EXCLUDED),
        "full_contract": "contract_for_v72('intervention-proposal') + "
                         f"max_tokens={PROBE_MT} (the 19K-char class)",
        "candidates": results,
        "admission_note": "candidates whose completion carries a "
                          "deliverable-class finding are structurally "
                          "disqualified (the HO9-14 class is an "
                          "admission-time kill, not a score-time one)",
        "next_gates": [
            "register the strongest serving frontier id (one commit)",
            "auditor amends the prereg (AM62 is the template)",
            "re-freeze (the 9-item manifest convention, ONE commit)",
            "fresh sealed v10 (n>=30, domain-disjoint, confidential "
            "custody)",
        ],
        "note": "values live in .env.keys only; this record carries "
                "no secret bytes (Art. 17)",
    }
    OUT.write_text(json.dumps(record, indent=1) + "\n")
    print("record written:", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
