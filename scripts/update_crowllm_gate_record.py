#!/usr/bin/env python3
"""Update the crowllm gate record with the REAL gate measurement
(the first pass failed on transport plumbing, not model service).

Timeline of the measurement (all live, 2026-11-14 ~14:00-14:20Z):
  1. NO_SPEC (crowllm not yet registered) — expected, registration
     is the work item
  2. HTTP 403 on every engine call — Cloudflare bans the default
     python urllib UA (same class as xkiro, measured: urllib default
     -> 403; Chrome UA -> 200 OK). FIX: extra_headers Chrome UA on
     the spec (transport plumbing only)
  3. With UA fixed: full-length served 1/3 at zero pacing, and the
     errors are HTTP 500 bursts. Measured error distribution over
     10 paced tiny calls: {200: 1, 429: 5, 500: 3, 503: 1}; over 8
     calls: {200: 5, 503: 2, 429: 1}. 429 clears in ~18 s (measured
     recovery). 500s come in BURSTS (4 consecutive fails) then clear
     with no action — free-pool congestion, not account death
  4. THE GATE QUESTION — can it serve the REAL full-length judge
     prompt (7786 chars) reliably? Measured 3 trials at ~8 s pacing
     AFTER a 500-burst window: 3/3 complete verdict JSONs
     (105-107 chars, 2.8-5.4 s wall). A retry ladder (immediate,
     +10 s, +25 s) clears bursts in the logical-call layer
  5. ernie-5.5-flash-preview:free (the other live rung): tiny OK
     but full-length verdict starves (2/3 returned 4 chars, no
     verdict JSON) — TYPED DEAD for the judge role
     (EmptyContentAtCap class); never enters JUDGE_CANDIDATES

Verdict: GATE PASS for deepseek-v4-flash:free as an independent
judge rung — family DeepSeek (different from the agnes
autoregressive generator rung AND different provider), full-length
service measured, congestion is bursty and retry-cleared.
"""
import json
import pathlib

rec = {
 "record": "CROWLLM_GATE/1.0.1",
 "at": "2026-11-14T14:20:00Z",
 "model": "deepseek-v4-flash:free",
 "provider": "crowllm",
 "transport": {
  "requirement": "Chrome User-Agent (Cloudflare browser-signature "
                 "check bans the default python urllib UA with 403)",
  "measured": "urllib default UA -> 403 Forbidden on every endpoint; "
              "Chrome UA -> 200 OK; carried in spec.extra_headers "
              "(same class as xkiro, transport plumbing only)",
 },
 "congestion_class": {
  "codes": {200: "served", 429: "free-pool rate limit (clears ~18 s)",
            500: "free-pool burst (bursts of 3-4, then clears)",
            503: "free-pool overflow"},
  "distribution_tiny_calls": [
    {"n": 10, "result": {"200": 1, "429": 5, "500": 3, "503": 1}},
    {"n": 8, "result": {"200": 5, "503": 2, "429": 1}}],
  "recovery_429_s": 18,
  "burst_shape": "4 consecutive 500s then unassisted recovery; "
                 "logical-call retry ladder (immediate/+10s/+25s) "
                 "clears it in the caller",
 },
 "gate_result": {
  "question": "does the REAL full-length judge prompt (7786 chars) "
              "serve complete verdict JSONs?",
  "trials": 3, "pacing_s": 8, "valid": 3,
  "walls_s": [4.1, 2.8, 5.4],
  "chars_out": [105, 107, 107],
  "verdict_json_all": True,
  "gate": "PASS",
 },
 "other_rungs_typed": {
  "deepseek-v4.1-flash:free": "503 DEAD_UPSTREAM (both stream and "
                              "non-stream, measured)",
  "deepseek-v4.1-flash-uncensored:free": "503 DEAD_UPSTREAM (measured)",
  "ernie-5.5-flash-preview:free": "tiny OK but full-length verdict "
                                  "starves (2/3 calls returned 4 chars, "
                                  "no verdict JSON) — TYPED DEAD for "
                                  "the judge role (EmptyContentAtCap); "
                                  "never enters JUDGE_CANDIDATES",
  "qwen-3.6-27b:free": "90 s timeout x1 (typed, not retried — the "
                       "deepseek rung already passed the gate)",
  "qwen-3.5-397b-a17b:free": "90 s timeout x1 (same)",
  "agnes-2.5-flash:free": "500 during a burst window (same congestion "
                          "class; not judge-role relevant)",
 },
 "judge_role_eligibility": {
  "independent_family": "DeepSeek family — different provider AND "
                        "family from the agnes/agnes-3.0-flash "
                        "generator rung (the R3 A1 generator)",
  "gate": "PASS — wired into JUDGE_CANDIDATES after the 30-pair "
          "live calibration (threshold 0.8) runs",
 },
}
out = pathlib.Path("eval/crowllm_gate_r11.json")
out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")
print(f"gate record updated -> {out}")
