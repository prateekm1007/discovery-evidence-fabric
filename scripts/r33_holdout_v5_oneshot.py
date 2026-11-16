#!/usr/bin/env python3
"""r33_holdout_v5_oneshot.py — the ACCEPTANCE one-shot (AM31 D1).

Protocol (audit/holdout_v5/PREREGISTRATION.json, tip 622450281):
  1. the claim (r33-holdout-v5-oneshot, EXECUTOR builder-r20s1) is
     PUSHED before any problem read (Art. 29(b) push-as-mutex);
  2. problems ONLY (the PRIVATE rubric is never read by the builder);
  3. generate ONCE with the FROZEN V7.6 machine — contract_for_v72,
     the V76 directive, BOTH AM29 binds in the path, critic, type
     gate, typed scans, NEUTRAL repair directive, budget 3, K_GEN=1;
     no contract edits, no tuning;
  4. rows commit as produced (resume anchors; a crashed run resumes
     from committed rows only, disclosed — the R21 chunked precedent);
  5. the auditor scores with the PRIVATE rubric; acceptance bar:
     mean >=3.0/4 AND 0 allowed-measures violations AND 0
     inverted-direction mechanisms; the set burns after use.

Transport honesty: every attempt records route/route_model/
fallback_reason (the primary local gateway first; the amended NVIDIA
chain per c-0031 amendments #2/#3 — including the disclosed
model-family change). The packet copy the builder received is
committed with its sha256 for custody (Art. 1).
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
import os  # noqa: E402
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
os.environ.setdefault(
    "ZAI_GATEWAY_LOG",
    str(REPO / "ENGINE_RUNS" / "zai_gateway_calls.jsonl"))

from r11_a1f_v3_generate import start_gateway  # noqa: E402
from r30_tune_battery_v76 import (  # noqa: E402
    _gen_fb, machine_generate_v76, _sha)

PACKET = REPO / "eval" / "holdout_v5_problems.json"
OUT_DIR = REPO / "eval" / "pairs" / "holdout_v5_generation"
LEDGER = REPO / "eval" / "holdout_v5_run.json"
LOCK = REPO / "eval" / ".r33_v5_oneshot.lock"
# AM32 D3: durable append-per-fire events log + AM32 D1: committed
# gateway-log slice (the served-identity evidence must be a run artifact)
EVENTS = REPO / "eval" / "holdout_v5_run_events.jsonl"
GW_SLICE = REPO / "eval" / "holdout_v5_gateway_log_slice.jsonl"
RUN_NAME = "v5"

CLAIM = ("r33-holdout-v5-oneshot (c-0034, pre-registered and PUSHED "
         "BEFORE any problem read; one-shot/sealed per Art. 29(c): "
         "K_GEN=1, one run, resume from committed rows only)")


def main() -> int:
    import fcntl
    lock_fh = open(LOCK, "w")
    try:
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("[v5-oneshot] another fire holds the lease — exit 0",
              flush=True)
        return 0

    if not PACKET.exists():
        print(f"[v5-oneshot] TYPED: packet missing ({PACKET}) — "
              f"claim-before-read order requires the claim PUSHED "
              f"before extraction; extract first, then run", flush=True)
        return 2
    packet_sha = hashlib.sha256(PACKET.read_bytes()).hexdigest()
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    rows = packet.get("rows") or packet.get("problems") or []
    # the v5 packet is FLAT (problem fields at row level); the dev
    # packet nested them under "problem" — accept both shapes
    probs = {r["problem_id"]: (r.get("problem") or r) for r in rows}
    print(f"[v5-oneshot] packet sha256_16={packet_sha[:16]} "
          f"problems={len(probs)} (claim: {CLAIM})", flush=True)

    gw, gw_key = start_gateway()
    # DURABLE LEDGER (AM32 D3 fix): merge rows AND provenance keys from
    # the existing ledger AND the events log — a process restart can
    # never drop rows or launder the backfill flags again
    base = {"packet_sha256": packet_sha,
            "claim": CLAIM,
            "machine": "frozen V7.6 (V7.4 path + V76 directive + "
                       "AM29 class-bind + direction-bind in path; "
                       "budget 3; K_GEN=1)",
            "acceptance_bar": "auditor mean >=3.0/4 AND 0 "
                              "allowed-measures violations AND 0 "
                              "inverted-direction mechanisms"}
    prior = {}
    if LEDGER.exists():
        try:
            prior = json.loads(LEDGER.read_text(encoding="utf-8")) or {}
        except Exception:
            prior = {}
    ledger = {**prior, **base, "rows": dict(prior.get("rows") or {})}
    if EVENTS.exists():
        for line in EVENTS.read_text(encoding="utf-8").splitlines():
            try:
                ev = json.loads(line)
                if ev.get("kind") == "row":
                    ledger["rows"][ev["problem_id"]] = ev["row"]
            except Exception:
                pass
    try:
        for pid, prob in probs.items():
            dst = OUT_DIR / f"{pid}.json"
            if dst.exists():
                print(f"  [v5] {pid[:36]:<38} exists (skip — one "
                      f"generation, never re-drawn)", flush=True)
                continue
            t0 = time.time()
            ans, attempts, meta = machine_generate_v76(prob, gw_key)
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            dst.write_text(
                json.dumps({"problem_id": pid,
                            "question_type": prob.get("question_type"),
                            "a1_answer": ans, "meta": meta,
                            "attempts": attempts,
                            "generated_at": time.strftime(
                                "%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                           indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            row_rec = {
                "repairs": meta["repairs"],
                "residual_findings": meta["residual_findings"],
                "chars": len(ans),
                "routes": sorted({a.get("route") for a in attempts
                                  if a.get("route")}),
                "models": sorted({a.get("route_model") for a in attempts
                                  if a.get("route_model")})}
            ledger["rows"][pid] = row_rec
            # append-per-fire: the event survives even if the process
            # dies before the next JSON rewrite
            with EVENTS.open("a", encoding="utf-8") as ef:
                ef.write(json.dumps({"kind": "row", "problem_id": pid,
                                     "row": row_rec,
                                     "ts": time.strftime(
                                         "%Y-%m-%dT%H:%M:%SZ",
                                         time.gmtime())}) + "\n")
            LEDGER.write_text(
                json.dumps(ledger, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            print(f"  [v5] {pid[:36]:<38} repairs={meta['repairs']} "
                  f"residual={list(meta['residual_findings']) or 'CLEAN'} "
                  f"({time.time()-t0:.0f}s)", flush=True)
    finally:
        try:
            gw.terminate()
        except Exception:
            pass

    # ---- AM32 D1: PRE-SCORING SERVED-MODEL ATTESTATION GATE ----------
    # commit the gateway-log slice for the run window as a run artifact
    # (the v5 run's serving evidence lived in an uncommitted gitignored
    # log — the custody gap typed in eval/holdout_v5_attestation.json)
    try:
        import r34_served_model_attestation as att
        times = sorted(str(d.get("generated_at", ""))
                       for d in ledger["rows"].values())
        win_start = win_end = None
        if times and att.GW_LOG.exists():
            win_start, win_end = times[0][:13], times[-1][:13]
            lines = [ln for ln in
                     att.GW_LOG.read_text(encoding="utf-8").splitlines()
                     if win_start <= json.loads(ln).get("ts", "")[:13]
                     <= win_end]
            GW_SLICE.write_text("\n".join(lines) + ("\n" if lines else ""),
                                encoding="utf-8")
            print(f"[v5-oneshot] gateway-log slice committed: "
                  f"{len(lines)} calls ({GW_SLICE.name})", flush=True)
        gw_hist = (att.gateway_window(win_start, win_end)
                   if win_start and win_end else {})
        summary_serving = None
        verdict = att.attest(
            att.load_rows(OUT_DIR), gw_hist, summary_serving,
            f"{RUN_NAME} one-shot (this driver)")
        ledger["served_model_attestation"] = {
            "registered_model": att.REGISTERED_MODEL,
            "n_equal": verdict["n_equal"], "n_rows": verdict["n_rows"],
            "verdict": verdict["verdict"],
            "gate": "pre-scoring (AM32 D1)",
            "gateway_log_slice": str(GW_SLICE.name),
            "serving_histogram": gw_hist}
        run_void = verdict["verdict"] != "PASS"
        ledger["run_verdict"] = ("VOID — served-model substitution "
                                 "(registered machine did not execute; "
                                 "scoring refused, Art. 3 fail-closed)"
                                 if run_void else "VALID — 12/12 rows "
                                 "attested equal to the registered model")
        ledger["acceptance_eligible"] = not run_void
        print(f"[v5-oneshot] ATTESTATION: {verdict['n_equal']}/"
              f"{verdict['n_rows']} equal -> {verdict['verdict']}",
              flush=True)
    except Exception as e:  # gate failure fails CLOSED, never open
        ledger["run_verdict"] = (f"UNPROVABLE — attestation gate error: "
                                 f"{type(e).__name__}: {e}")
        ledger["acceptance_eligible"] = False
        print(f"[v5-oneshot] ATTESTATION ERROR (fail-closed): {e}",
              flush=True)
    LEDGER.write_text(
        json.dumps(ledger, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"-> {OUT_DIR} + {LEDGER} "
          f"(run_verdict: {ledger.get('run_verdict')})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
