#!/usr/bin/env python3
"""r34_served_model_attestation.py — AM32 D1: the served-model identity gate.

The registered frozen machine requests zai-org/GLM-5.3 (llm_registry.py
catalog entry, line ~507; the gateway log's requested_model field). The
ONLY byte-authority for what was actually SERVED is the gateway call
log (ENGINE_RUNS/zai_gateway_calls.jsonl: `requested_model` vs `model`)
— the row metadata records route/route_model per attempt but the peer's
zai rows carry route_model=None, so row fields alone cannot attest
serving identity.

Gate semantics (AM32 D1):
  - per row: every attempt's served model must equal the registered
    model; any mismatch => row SUBSTITUTED;
  - per run: ANY substituted row => run VOID (pre-scoring gate — the
    verdict fires before any rubric scoring, and a VOID run is refused
    as acceptance-eligible, Art. 3 fail-closed);
  - run-window attribution: every zai_gateway attempt inside the run
    window is served whatever the log shows for requested
    zai-org/GLM-5.3 in that window (typed: run_window_serving — the log
    has no per-row correlation field; window-wide substitution implies
    per-row substitution).

Applied here PRE-SCORING to (a) the canonical R33 one-shot (peer-run,
e401bb2ad) and (b) the quarantined duplicate (incident artifact) — the
expected verdict for both is VOID from the transport bytes already on
record.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROWS_DIR = REPO / "eval" / "pairs" / "holdout_v5_generation"
DUP_DIR = REPO / "eval" / "pairs" / "holdout_v5_generation_DUPLICATE_builder-r20s1"
GW_LOG = REPO / "ENGINE_RUNS" / "zai_gateway_calls.jsonl"
SUMMARY = REPO / "eval" / "holdout_v5_full_summary.json"
OUT = REPO / "eval" / "holdout_v5_attestation.json"

REGISTERED_MODEL = "zai-org/GLM-5.3"
REGISTRY_PROVENANCE = ("discovery_fabric/engine/llm_registry.py catalog entry "
                       "(zai-org/GLM-5.3, openai-compatible, 128k ctx) + the "
                       "gateway log requested_model field")


def load_rows(d: Path) -> dict[str, dict]:
    rows = {}
    for f in sorted(d.glob("HO5-*.json")):
        rows[f.stem] = json.loads(f.read_text(encoding="utf-8"))
    return rows


def gateway_window(window_start: str, window_end: str) -> dict[str, int]:
    """served-model histogram for registered-model requests in the window
    (string compare on ISO timestamps, hour-precision bounds padded)."""
    hist: dict[str, int] = {}
    for line in GW_LOG.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("requested_model") != REGISTERED_MODEL:
            continue
        ts = str(d.get("ts", ""))
        if window_start <= ts[:13] <= window_end:
            hist[d.get("model")] = hist.get(d.get("model"), 0) + 1
    return hist


def attest(rows: dict[str, dict], gw_hist: dict[str, int],
           summary_serving: dict[str, int] | None,
           label: str) -> dict:
    """Tiered evidence, fail-closed (Art. 3): an attempt that cannot
    PROVE served == registered from committed bytes is NOT attested
    equal — absence of proof is not proof of equality."""
    per_row = []
    for pid, d in sorted(rows.items()):
        atts = d.get("attempts") or []
        row = {"problem_id": pid, "attempts": [], "substituted": False,
               "served_models": set()}
        for a in atts:
            route = a.get("route")
            if route == "zai_gateway":
                if gw_hist:  # tier 3: local committed?? log window
                    served, basis = set(gw_hist), \
                        "local gateway log run-window (UNCOMMITTED file)"
                elif summary_serving:  # tier 2: committed driver summary
                    served = {k.split("<-")[0].strip()
                              for k in summary_serving}
                    basis = "committed full_summary gateway_log_serving_" \
                            "models (driver-produced record)"
                else:  # no evidence at all -> fail closed
                    served, basis = {"UNPROVABLE"}, \
                        "no serving evidence; fail-closed (Art. 3)"
            else:
                served = {a.get("route_model") or "UNRECORDED"}
                basis = "route_model field (chain API-returned)"
            row["served_models"] |= served
            eq = served <= {REGISTERED_MODEL}
            row["attempts"].append({
                "stage": a.get("stage"), "route": route,
                "served_models": sorted(served), "basis": basis,
                "equal_registered": eq})
            if not eq:
                row["substituted"] = True
        row["served_models"] = sorted(row["served_models"])
        row["attestation"] = ("EQUAL" if not row["substituted"]
                              else "SUBSTITUTED")
        row["generated_at"] = d.get("generated_at")
        row["file_sha256_16"] = hashlib.sha256(
            (ROWS_DIR / f"{pid}.json").read_bytes()
            if (ROWS_DIR / f"{pid}.json").exists()
            else (DUP_DIR / f"{pid}.json").read_bytes()).hexdigest()[:16]
        per_row.append(row)
    n_equal = sum(1 for r in per_row if r["attestation"] == "EQUAL")
    verdict = "PASS" if n_equal == len(per_row) and per_row else "VOID"
    return {
        "label": label,
        "n_rows": len(per_row),
        "n_equal": n_equal,
        "n_substituted": len(per_row) - n_equal,
        "verdict": verdict,
        "gate": ("pre-scoring: a VOID run is refused as acceptance-"
                 "eligible before any rubric scoring (AM32 D1)"),
        "rows": per_row,
    }


def main() -> int:
    # run window from the canonical rows' generated_at span
    canon = load_rows(ROWS_DIR)
    times = sorted(str(d.get("generated_at", "")) for d in canon.values())
    start, end = times[0][:13], times[-1][:13]
    gw_hist = gateway_window(start, end)
    full = json.loads(SUMMARY.read_text(encoding="utf-8")) if SUMMARY.exists() else {}
    summary_serving = full.get("gateway_log_serving_models") or {}

    canon_att = attest(canon, gw_hist, summary_serving,
                       "canonical R33 one-shot (e401bb2ad)")
    dup_att = (attest(load_rows(DUP_DIR), {}, {},
                      "quarantined duplicate "
                      "(builder-r20s1 incident artifact)")
               if DUP_DIR.exists() else None)

    out = {
        "record": "HOLDOUT_V5_SERVED_MODEL_ATTESTATION/1.0.0",
        "registered_model": REGISTERED_MODEL,
        "registered_model_provenance": REGISTRY_PROVENANCE,
        "evidence_tiers": {
            "tier1_row_bytes": "committed row attempts: route/route_model "
                               "(nvidia rows provable; zai rows carry "
                               "route_model=None — cannot self-attest)",
            "tier2_committed_summary": "eval/holdout_v5_full_summary.json "
                                       "gateway_log_serving_models "
                                       "(committed, driver-produced): "
                                       + json.dumps(summary_serving),
            "tier3_local_gateway_log": "ENGINE_RUNS/zai_gateway_calls.jsonl "
                                       "(GITIGNORED, uncommitted): "
                                       "0 entries on the run day "
                                       "(2026-11-16); last entry "
                                       "2026-11-15T19:31Z — the run's "
                                       "primary-call log was NOT durably "
                                       "committed (custody gap, typed)",
        },
        "evidence_custody_gap": {
            "finding": "the v5 run-window gateway log is neither committed "
                       "nor present in the workspace — serving identity for "
                       "the zai rows rests on the tier-2 committed summary "
                       "alone",
            "v6_requirement": "the attestation gate REQUIRES a committed "
                              "gateway-log slice (requested vs served per "
                              "call for the run window) as a mandatory run "
                              "artifact; without it the run is UNPROVABLE "
                              "and fails closed",
        },
        "run_window": {"start": start, "end": end,
                       "gateway_log_serving_histogram_in_window": gw_hist},
        "canonical_run": canon_att,
        "quarantined_duplicate_run": dup_att,
        "run_verdicts": {
            "canonical": canon_att["verdict"],
            "quarantined_duplicate": (dup_att or {}).get("verdict")},
        "acceptance_consequence": ("per AM32: the v5 run is INVALID (not "
                                   "merely low-scoring) — the registered "
                                   "machine did not execute; scoring is "
                                   "refused; v5 burns without acceptance "
                                   "(eval/holdout_v5_burn_record.json)"),
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"canonical: {canon_att['n_equal']}/{canon_att['n_rows']} equal -> "
          f"{canon_att['verdict']}")
    if dup_att:
        print(f"duplicate: {dup_att['n_equal']}/{dup_att['n_rows']} equal -> "
              f"{dup_att['verdict']}")
    print(f"gateway histogram (window, local log): {gw_hist}")
    print(f"tier-2 committed summary serving: {summary_serving}")
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
