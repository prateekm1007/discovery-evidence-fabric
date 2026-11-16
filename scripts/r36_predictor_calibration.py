#!/usr/bin/env python3
"""r36_predictor_calibration.py — the c-0026 PREDICTOR HALF (claim c-0042).

The auditor's 015340a3c published 12 per-row predictor anchors (novelty
delta + a1/baseline feasibility + gap + rationale) so the c-0026 predictor
axis (>= 10/12 within +/-1 of the auditor) is MEASURABLE. This sibling
completes that measurement.

DISCIPLINE (no edits to the pre-registered instrument):
  - scripts/r29_judge_calibration.py is hardwired to the 18 intervention
    rows (asserts). It is imported UNCHANGED and its functions are reused
    verbatim: judge_slot (the canonical ladder), _v3_prompt (the byte
    discipline), K/ladder/pace/max-tokens constants. The judge prompt
    bytes are therefore IDENTICAL to the interventions half.
  - Row selector: the packet complement (question_type NOT starting with
    "intervention"), asserted == 12.
  - Anchor: the auditor's per-row predictor anchors ride `git show` from
    the audit tip that published them (015340a3c) — auditor-controlled
    bytes are never copied into the queue tree.
  - Route: UNCHANGED — crowllm/qwen-3.8-max:free (the canonical c-0026
    route; DeepSeek-V4-Flash liveness is a different route and is NOT
    used; Art. 26 no route swap).
  - Zero generator calls: pure judge measurement on frozen packet bytes.

Usage: python3 scripts/r36_predictor_calibration.py [probe|run|assemble]
"""
import json, subprocess, sys, time, statistics, hashlib, os
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import r29_judge_calibration as cal  # the pre-registered instrument, UNCHANGED

ANCHOR_SHA = "015340a3c"
ANCHOR_REF = ("audit/r11-auditor-verdict-20261114 @ 015340a3c:"
              "eval/auditor_predictor_row_anchors.json")
PARTIAL = REPO / "eval" / "judge_feasibility_calibration_r29_predictors.partial.json"
OUT = REPO / "eval" / "judge_feasibility_calibration_r29_predictors.json"
RUN_LOG = REPO / "ENGINE_RUNS" / "r36_predictor_calibration.log"
ACCEPT_WITHIN = 1
ACCEPT_MIN_ROWS = 10  # >= 10 of the 12 predictor rows


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _log(msg):
    line = f"[{_now()}] {msg}"
    print(line, flush=True)
    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(RUN_LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _sha16(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _predictor_rows():
    packet = json.loads(cal.PACKET.read_text(encoding="utf-8"))
    rows = [r for r in packet["rows"]
            if not str(r.get("question_type", "")).startswith("intervention")]
    assert len(rows) == 12, f"expected 12 predictor rows: {len(rows)}"
    return rows


def _anchor():
    out = subprocess.run(
        ["git", "-C", str(REPO), "show",
         f"{ANCHOR_SHA}:eval/auditor_predictor_row_anchors.json"],
        capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def probe():
    """Servability gate on the ACTUAL route — mirrors the original probe's
    shape: tiny call + verdict-shaped trials via the harness's own
    cal.probe-style path (PROBE_RUBRIC + _judge_judgment_call)."""
    ok, detail = cal.judge_transport_ready()
    if not ok:
        _log(f"[probe] FAIL {detail}")
        print(json.dumps({"probe": "FAIL", "class": "NO_CREDENTIAL", "detail": detail}))
        return 1
    t0 = time.time()
    r = cal._transport_call(cal.JUDGE[0], cal.JUDGE[1],
                            "Reply with exactly: OK",
                            "You are a servability probe. English only.",
                            max_tokens=20)
    tiny = {"status": r.get("status"),
            "content_chars": len(str(r.get("content") or "")),
            "error": (r.get("error") or "")[:120],
            "latency_s": round(time.time() - t0, 1)}
    _log(f"[probe][tiny] {tiny}")
    if r.get("status") != "OK" or not str(r.get("content") or "").strip():
        print(json.dumps({"probe": "FAIL", "class": "TINY_CALL_FAILED", "tiny": tiny}))
        return 1
    trials = []
    for i in (1, 2):
        jc = cal._judge_judgment_call(cal.JUDGE[0], cal.JUDGE[1],
                                      cal.PROBE_RUBRIC, max_tokens=cal.MAX_TOKENS)
        trials.append({"trial": i, "outcome": jc.get("outcome"),
                       "valid": bool(jc.get("valid")),
                       "raw_excerpt": str(jc.get("raw") or "")[:160]})
        _log(f"[probe][verdict-shaped {i}] outcome={jc.get('outcome')} valid={jc.get('valid')}")
        time.sleep(8.0)
    n_valid = sum(1 for t in trials if t["valid"])
    gate = "PASS" if n_valid >= 1 else "VERDICT_JSON_NOT_SERVED"
    _log(f"[probe] gate={gate} n_valid={n_valid}")
    print(json.dumps({"probe": gate, "tiny": tiny, "trials": trials,
                      "n_verdict_valid": n_valid}))
    return 0 if gate == "PASS" else 1


def run():
    rows = _predictor_rows()
    anchor = {r["problem_id"]: r for r in _anchor()["rows"]}
    missing = [r["problem_id"] for r in rows if r["problem_id"] not in anchor]
    assert not missing, f"predictor rows missing from the auditor anchor: {missing}"
    prior = {}
    if PARTIAL.exists():
        for r in json.loads(PARTIAL.read_text(encoding="utf-8")):
            prior[r["problem_id"]] = r
    results = []
    n_calls = 0
    n_ladder = 0
    t0 = time.time()
    for row in rows:
        pid = row["problem_id"]
        if pid in prior:
            results.append(prior[pid])
            _log(f"[run] {pid[:40]:<42} resumed (F_A={prior[pid].get('machine_a1_feasibility_median')})")
            continue
        prompt = cal._v3_prompt(row)
        assert prompt.endswith(cal.V3_SUFFIX)
        draws = []
        for k in range(cal.K):
            jc, outcome, atts = cal.judge_slot(pid, k, prompt)
            n_calls += len(atts)
            n_ladder += max(0, len(atts) - 1)
            draws.append({"k": k, "outcome": outcome,
                          "axes": cal.parse_axes(jc),
                          "transport_attempts": atts})
            if k < cal.K - 1:
                time.sleep(cal.PACE_S)
        valid_axes = [d["axes"] for d in draws
                      if d["outcome"] == "JUDGE_VALID" and d["axes"]]
        f_vals = sorted(a["F_A"] for a in valid_axes if "F_A" in a)
        n_vals = sorted(a["N_A"] for a in valid_axes if "N_A" in a)
        med = (f_vals[len(f_vals) // 2] if f_vals else None)
        med_n = (n_vals[len(n_vals) // 2] if n_vals else None)
        entry = {"problem_id": pid,
                 "question_type": row.get("question_type"),
                 "stage": row.get("stage"),
                 "judge": list(cal.JUDGE),
                 "axis_suffix": "v3 (calibrated F pins)",
                 "v3_prompt_sha256_16": _sha16(prompt),
                 "packet_prefix_byte_identical": True,
                 "draws": draws,
                 "n_valid_draws": sum(1 for d in draws
                                      if d["outcome"] == "JUDGE_VALID"),
                 "machine_a1_feasibility_median": med,
                 "machine_a1_feasibility_values": f_vals,
                 "machine_a1_novelty_median": med_n}
        results.append(entry)
        _log(f"[run] {pid[:40]:<42} F_A={med} (vals {f_vals}) N_A={med_n} "
             f"valid={entry['n_valid_draws']}/{cal.K} ({time.time()-t0:.0f}s)")
        PARTIAL.write_text(
            json.dumps(results, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
    _log(f"[run] COMPLETE: {len(results)} rows in {time.time()-t0:.0f}s "
         f"(logical calls {n_calls}, ladder retries {n_ladder})")
    print(json.dumps({"rows": len(results),
                      "logical_calls": n_calls,
                      "ladder_retries": n_ladder}))


def assemble():
    rows = json.loads(PARTIAL.read_text(encoding="utf-8"))
    assert len(rows) == 12, f"partial incomplete: {len(rows)}/12"
    anchor = {r["problem_id"]: r for r in _anchor()["rows"]}
    comparison = []
    tally = 0
    for r in rows:
        pid = r["problem_id"]
        a = anchor[pid]
        m_f = r["machine_a1_feasibility_median"]
        a_f = a["auditor_a1_feasibility"]
        dlt = None if m_f is None else m_f - a_f
        w1 = (dlt is not None and abs(dlt) <= ACCEPT_WITHIN)
        if w1:
            tally += 1
        comparison.append({
            "problem_id": pid,
            "stage": r.get("stage"),
            "machine": {"a1_feasibility": m_f,
                        "values": r["machine_a1_feasibility_values"],
                        "novelty_median": r["machine_a1_novelty_median"],
                        "n_valid_draws": r["n_valid_draws"]},
            "auditor_predictor_anchor": {
                "a1_feasibility": a_f,
                "baseline_feasibility": a.get("auditor_baseline_feasibility"),
                "feasibility_abs_gap": a.get("auditor_feasibility_abs_gap"),
                "novelty_delta": a.get("auditor_novelty_delta"),
                "rationale": a.get("rationale")},
            "delta": dlt,
            "within_1": w1})
    met = tally >= ACCEPT_MIN_ROWS
    rec = {
        "record": "JUDGE_FEASIBILITY_CALIBRATION_R29_PREDICTORS/1.0.0",
        "at": _now(),
        "typed": ("CROSS-CHECK INSTRUMENT CALIBRATION — the PREDICTOR HALF of "
                  "the AM33-chat D2 bar; the machine judge is an INPUT, never "
                  "the verdict; the builder never scores its own generation"),
        "claim": {"claim_id": "c-0042", "work_id": "r36-c0026-predictor-half",
                  "session": "builder-r35s1", "base_sha": "f85d0dbbf"},
        "input": {"packet": "eval/r27_judge_packet.json", "rows": 12,
                  "row_selector": "packet complement of the 18 intervention rows (question_type NOT starting with 'intervention')",
                  "prompt_discipline": "identical to the interventions half: cal._v3_prompt from the UNCHANGED pre-registered harness (byte-identical suffix swap; asserted)",
                  "auditor_anchor": {"provenance": ANCHOR_REF, "sha": ANCHOR_SHA,
                                     "basis": "the auditor's 12 per-row predictor judgments (novelty + a1/baseline feasibility + gap + rationale), published 2026-11-16 to make this axis measurable"}},
        "judge": {"route": [cal.JUDGE[0], cal.JUDGE[1]], "k": cal.K,
                  "pace_s": cal.PACE_S,
                  "transport_ladder": list(cal.LADDER_BACKOFF_S),
                  "independence": "crowllm/Qwen vs zai/GLM generator — provider AND family independent (Art. 10/26); the canonical c-0026 route, UNCHANGED"},
        "results": rows,
        "comparison": comparison,
        "acceptance": {"rule": "judge a1_feasibility within +/-1 of the auditor on >= 10/12 predictor rows (AM33-chat D2 predictor clause)",
                       "n_rows": 12, "n_compared": len(comparison),
                       "n_within_1": tally, "met": met,
                       "disposition": ("machine judge feasibility axis calibrated on the predictor half"
                                       if met else
                                       "NOVELTY-ONLY CROSS-CHECK stands (the auditor's feasibility read governs; the builder never scores)")},
        "quota": {"judge_slot_attempts": sum(len(d.get("transport_attempts", [])) for r in rows for d in r["draws"]),
                  "ladder_retries": sum(1 for r in rows for d in r["draws"] for t in d.get("transport_attempts", []) if t.get("n", 1) > 1),
                  "budget": "12 rows x K=3 = 36 logical judge calls + typed ladder retries"},
        "generation": {"calls": 0, "note": "zero generator calls — pure judge measurement on frozen packet bytes"},
        "art_27": "NO CAPABILITY CHANGE (cross-check instrument measurement only)"}
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
    _log(f"[assemble] {tally}/12 within +/-1 -> clause {'MET' if met else 'NOT MET'}")
    print(json.dumps({"n_within_1": tally, "met": met,
                      "out": str(OUT.relative_to(REPO))}))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "probe"
    {"probe": probe, "run": run, "assemble": assemble}[cmd]()
