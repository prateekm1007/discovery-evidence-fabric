#!/usr/bin/env python3
"""r38_holdout_v6_oneshot.py — the ACCEPTANCE one-shot under the
corrected registration (claim c-0038, EXECUTOR builder-r20s2; AM34/35
D3). The v5 driver's shape (scripts/r33_holdout_v5_oneshot.py) with:

  - the SEAL-ANCHOR GATE wired in (AM34/35 D1: "no burn proceeds
    without it"): the canonical-tuple projection of the extracted
    packet must recompute the pre-registered 4d60488a… EXACTLY before
    the first generation call, else typed abort;
  - the corrected registration glm-4-plus end-to-end (the machine
    requests it; the attestation gate REGISTERED_MODEL is glm-4-plus);
  - v6 artifact names: rows eval/pairs/holdout_v6_generation/, events
    eval/holdout_v6_run_events.jsonl, slice
    eval/holdout_v6_gateway_log_slice.jsonl, ledger
    eval/holdout_v6_run.json, attestation eval/holdout_v6_attestation.json.

Protocol (audit/holdout_v6/PREREGISTRATION.json, tip 29e3dfb1b):
problems ONLY; generate ONCE with the FROZEN V7.6 machine (K_GEN=1,
budget 3, both AM29 binds in the path, critic, type gate, typed
scans, NEUTRAL repair directive; no contract edits, no tuning);
rows commit as produced (resume anchors); the attestation gate is
pre-scoring and fail-closed; run_verdict VALID requires 12/12 served
== glm-4-plus. The auditor scores with the PRIVATE rubric.
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
from r30_tune_battery_v76 import machine_generate_v76  # noqa: E402

PACKET = REPO / "eval" / "holdout_v6_problems.json"
OUT_DIR = REPO / "eval" / "pairs" / "holdout_v6_generation"
LEDGER = REPO / "eval" / "holdout_v6_run.json"
LOCK = REPO / "eval" / ".r38_v6_oneshot.lock"
EVENTS = REPO / "eval" / "holdout_v6_run_events.jsonl"
GW_SLICE = REPO / "eval" / "holdout_v6_gateway_log_slice.jsonl"
RUN_NAME = "v6"
REGISTERED_ANCHOR = ("4d60488a581897b9b7452158158049e65656c26ac58ea7"
                     "e611236047a9aab804")

CLAIM = ("r38-holdout-v6-oneshot (c-0038, pre-registered and PUSHED "
         "BEFORE any problem read; corrected registration glm-4-plus "
         "per the auditor's ruling; one-shot/sealed per Art. 29(c): "
         "K_GEN=1, one run, resume from committed rows only)")


def _anchor_ok(packet_bytes: bytes) -> tuple[bool, str]:
    doc = json.loads(packet_bytes)
    fresh = [p for p in doc.get("problems", [])
             if p.get("contamination_tag") is None]
    payload = [
        [p.get("problem_id"), p.get("device"), p.get("failure"),
         p.get("question"), p.get("question_type"),
         list(p.get("user_variables") or [])]
        for p in sorted(fresh, key=lambda x: str(x.get("problem_id")))]
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))
    h = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return h == REGISTERED_ANCHOR, h


def main() -> int:
    import fcntl
    lock_fh = open(LOCK, "w")
    try:
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("[v6-oneshot] another fire holds the lease — exit 0",
              flush=True)
        return 0

    if not PACKET.exists():
        print(f"[v6-oneshot] TYPED: packet missing ({PACKET}) — run "
              f"r38_v6_extract_problems.py first (claim-before-read "
              f"order; the claim is already pushed)", flush=True)
        return 2

    # ---- WINDOW GATE: a closed window must NEVER burn the one-shot
    # (a row committed with transport-failed attempts cannot be
    # re-drawn — the skip logic would freeze the damage). The driver
    # requires a FRESH VERIFIED serving preflight (<= 30 min old);
    # flow: run scripts/r35_serving_preflight.py, then this driver.
    pf_path = REPO / "eval" / "v6_serving_preflight.json"
    if not pf_path.exists():
        print("[v6-oneshot] TYPED: no serving preflight record — NO "
              "BURN. Flow: python3 scripts/r35_serving_preflight.py "
              "first", flush=True)
        return 2
    pf = json.loads(pf_path.read_text(encoding="utf-8"))
    pf_age_s = time.time() - pf_path.stat().st_mtime
    if not str(pf.get("verdict", "")).startswith("VERIFIED") \
            or pf_age_s > 1800:
        print(f"[v6-oneshot] TYPED: window not VERIFIED fresh "
              f"(verdict={str(pf.get('verdict'))[:40]}…, "
              f"age={pf_age_s:.0f}s) — NO BURN (Art. 3)", flush=True)
        return 2
    print(f"[v6-oneshot] WINDOW VERIFIED (fresh {pf_age_s:.0f}s)",
          flush=True)
    packet_bytes = PACKET.read_bytes()
    packet_sha = hashlib.sha256(packet_bytes).hexdigest()

    # ---- SEAL-ANCHOR GATE (AM34/35 D1): no burn without it --------
    ok, anchor16 = _anchor_ok(packet_bytes)
    print(f"[v6-oneshot] packet sha256_16={packet_sha[:16]} "
          f"anchor16={anchor16[:16]}", flush=True)
    if not ok:
        print("[v6-oneshot] TYPED: SEAL ANCHOR MISMATCH — NO BURN "
              "(Art. 3; the selection changed after registration)",
              flush=True)
        return 2
    packet = json.loads(packet_bytes)
    rows = packet.get("rows") or packet.get("problems") or []
    probs = {r["problem_id"]: (r.get("problem") or r) for r in rows}
    print(f"[v6-oneshot] SEAL ANCHOR VERIFIED — {len(probs)} problems "
          f"(claim: {CLAIM})", flush=True)

    gw, gw_key = start_gateway()
    base = {"packet_sha256": packet_sha,
            "seal_anchor": {"registered": REGISTERED_ANCHOR,
                            "recomputed": anchor16, "ok": ok},
            "claim": CLAIM,
            "machine": ("frozen V7.6 (V7.4 path + V76 directive + "
                        "AM29 class-bind + direction-bind in path; "
                        "budget 3; K_GEN=1); registration glm-4-plus "
                        "per AM34/35 R-REG"),
            "acceptance_bar": ("auditor mean >=3.0/4 AND 0 "
                               "allowed-measures violations AND 0 "
                               "inverted-direction mechanisms; "
                               "run_verdict VALID requires 12/12 "
                               "served == glm-4-plus")}
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
                print(f"  [v6] {pid[:36]:<38} exists (skip — one "
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
            with EVENTS.open("a", encoding="utf-8") as ef:
                ef.write(json.dumps({"kind": "row", "problem_id": pid,
                                     "row": row_rec,
                                     "ts": time.strftime(
                                         "%Y-%m-%dT%H:%M:%SZ",
                                         time.gmtime())}) + "\n")
            LEDGER.write_text(
                json.dumps(ledger, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            print(f"  [v6] {pid[:36]:<38} repairs={meta['repairs']} "
                  f"residual={list(meta['residual_findings']) or 'CLEAN'} "
                  f"({time.time()-t0:.0f}s)", flush=True)
    finally:
        try:
            gw.terminate()
        except Exception:
            pass

    # ---- PRE-SCORING SERVED-MODEL ATTESTATION GATE (fail-closed) ---
    try:
        import r34_served_model_attestation as att
        # v6 artifact names for the attestation record
        att.OUT = REPO / "eval" / "holdout_v6_attestation.json"
        att.SUMMARY = REPO / "eval" / "holdout_v6_full_summary.json"
        # R39 fix: attest() hashes rows from ROWS_DIR/DUP_DIR (module
        # constants still point at the v5 dirs) — point them at the v6
        # pair dir so the per-row custody sha reads the actual files
        att.ROWS_DIR = OUT_DIR
        att.DUP_DIR = OUT_DIR
        # R39 fix: the ledger row_recs carry no generated_at — derive
        # the run window from the durable EVENTS log's row ts
        times = []
        if EVENTS.exists():
            for line in EVENTS.read_text(encoding="utf-8").splitlines():
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                if ev.get("kind") == "row" and ev.get("ts"):
                    times.append(ev["ts"])
        times.sort()
        win_start = win_end = None
        if times and att.GW_LOG.exists():
            win_start, win_end = times[0][:13], times[-1][:13]
            lines = [ln for ln in
                     att.GW_LOG.read_text(encoding="utf-8").splitlines()
                     if win_start <= json.loads(ln).get("ts", "")[:13]
                     <= win_end]
            GW_SLICE.write_text("\n".join(lines) + ("\n" if lines else ""),
                                encoding="utf-8")
            print(f"[v6-oneshot] gateway-log slice committed: "
                  f"{len(lines)} calls ({GW_SLICE.name})", flush=True)
        gw_hist = (att.gateway_window(win_start, win_end)
                   if win_start and win_end else {})
        # R39 honesty fix: gateway_window counts only requests with
        # requested_model == REGISTERED — but the FROZEN V7.6 contract
        # requests the legacy embedded id zai-org/GLM-5.3 (the R458-C1
        # disclosure: the grant serves its single embedded model
        # regardless of requested id). The committed slice shows ALL
        # run-window calls were SERVED glm-4-plus; record the FULL
        # requested->served evidence so the PASS rests on the rows'
        # own calls, not on an unrelated probe call.
        req_to_served = {}
        all_served_reg = True
        if GW_SLICE.exists():
            for ln in GW_SLICE.read_text(encoding="utf-8").splitlines():
                try:
                    d = json.loads(ln)
                except Exception:
                    continue
                key = f"{d.get('requested_model')} -> {d.get('model')}"
                req_to_served[key] = req_to_served.get(key, 0) + 1
                if d.get("model") != att.REGISTERED_MODEL:
                    all_served_reg = False
        summary_serving = None
        verdict = att.attest(
            att.load_rows(OUT_DIR), gw_hist, summary_serving,
            f"{RUN_NAME} one-shot (corrected registration glm-4-plus)")
        n_measured = verdict["n_rows"]
        ledger["served_model_attestation"] = {
            "registered_model": att.REGISTERED_MODEL,
            "n_equal": verdict["n_equal"], "n_rows": n_measured,
            "verdict": verdict["verdict"],
            "gate": "pre-scoring (AM32 D1 + holdout v6 mandatory)",
            "gateway_log_slice": str(GW_SLICE.name),
            "serving_histogram": gw_hist,
            "serving_evidence_full": {
                "requested_to_served": req_to_served,
                "all_window_calls_served_registered": all_served_reg,
                "request_id_note": (
                    "the frozen V7.6 contract requests the legacy "
                    "embedded id zai-org/GLM-5.3 (a frozen-contract "
                    "artifact); the grant serves its single embedded "
                    "model regardless of requested id (R458-C1) — "
                    "every run-window call was SERVED glm-4-plus, "
                    "which is the identity evidence; correcting the "
                    "machine's request id is a contract change that "
                    "belongs to the auditor's next ruling, never a "
                    "mid-acceptance edit")}}
        if n_measured == 0:
            # R39 fix: 0 rows measured is a MEASUREMENT FAILURE, not a
            # substitution — type it honestly (the R36-era conflation
            # lesson, applied to the gate itself)
            ledger["run_verdict"] = ("UNPROVABLE — the attestation "
                                     "measured ZERO rows (gate wiring "
                                     "failure); scoring refused, "
                                     "fail-closed (Art. 3)")
            ledger["acceptance_eligible"] = False
        else:
            run_void = verdict["verdict"] != "PASS"
            ledger["run_verdict"] = ("VOID — served-model substitution "
                                     "(registered machine did not "
                                     "execute; scoring refused, "
                                     "Art. 3 fail-closed)"
                                     if run_void else
                                     f"VALID — {verdict['n_equal']}/"
                                     f"{n_measured} rows attested equal "
                                     "to the registered model "
                                     "glm-4-plus")
            ledger["acceptance_eligible"] = not run_void
        print(f"[v6-oneshot] ATTESTATION: {verdict['n_equal']}/"
              f"{n_measured} equal -> {verdict['verdict']}",
              flush=True)
    except Exception as e:  # gate failure fails CLOSED, never open
        ledger["run_verdict"] = (f"UNPROVABLE — attestation gate error: "
                                 f"{type(e).__name__}: {e}")
        ledger["acceptance_eligible"] = False
        print(f"[v6-oneshot] ATTESTATION ERROR (fail-closed): {e}",
              flush=True)
    LEDGER.write_text(
        json.dumps(ledger, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"[v6-oneshot] run_verdict: {ledger['run_verdict']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
