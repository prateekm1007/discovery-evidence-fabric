#!/usr/bin/env python3
"""r23_registry_v6.py — Art. 16/20 accounting for the AM23 D2 round-2
lever: V5 (post-generation repair leg) RETIRED at round 1 in the same
change that ships its successor V6 (contract-level bind), which enters
as PENDING_MEASUREMENT; claim c-0012 filed BEFORE any generation call.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

rf = REPO / "eval" / "ABLATION_REGISTRY.json"
reg = json.loads(rf.read_text(encoding="utf-8"))
v5 = next(e for e in reg["entries"]
          if "repair" in str(e.get("stage", ""))
          and e.get("status") == "ACTIVE")
assert v5.get("beats_incumbent") is False
v5["status"] = "RETIRED"
v5["successor"] = ("SYS_A1_INT_V6 (V4 + feasibility bind at mechanism "
                   "choice; work_id r23-feas-bind-v6, claim c-0012, "
                   "executor builder-r20s1)")
v5["reason"] = (
    "Art. 20 + typed lesson from the round-1 measurement (c-0006): the "
    "POST-generation lever is falsified — the repair directive neither "
    "binds the bill format (11/18 residuals) nor reroutes an "
    "already-chosen mechanism, and the audit block plausibly read as "
    "added burden (changed-arm 2.222 vs incumbent 1.5). The successor "
    "moves the bind UP to mechanism CHOICE in the draft contract — the "
    "level the V4 pilot proved responsive (hard-7 fgap 3.0 -> 1.857) — "
    "shipping in the same change (Art. 16 accounting). All draft/"
    "repair/scan bytes stay committed under eval/pairs/r22_feas_repair_v5/.")
reg["entries"].append({
    "stage": "generator_arm_contract_bind",
    "variant": "SYS_A1_INT_V6 = SYS_A1_INT_V4 + FEASIBILITY BIND at "
               "mechanism choice (procurable classes only; bill format "
               "mandated at draft; MINIMAL bill; novelty lives in the "
               "CHANGE; the bind outranks mechanism preference) + "
               "byte-unchanged machine path (critic/gate/neutral typed "
               "repairs, budget 2); no selection",
    "incumbent": "SYS_A1_INT_V4 single-draw (the r20 bytes; "
                 "eval/battery_a1w2_full_r20.json)",
    "incumbent_numbers": {"n_valid": 18, "novelty_delta_mean": 2.333,
                          "feasibility_abs_gap_mean": 1.5},
    "variant_numbers": None,
    "metric_citation": "eval/battery_feas_bind_v6_r23.json:"
                       "summary_intervention_rows",
    "beats_incumbent": None,
    "rounds_without_beating": 0,
    "gate_pass": None,
    "status": "PENDING_MEASUREMENT",
    "gate_carrier": False,
    "notes": "AM23 D2 round-2 lever (claim c-0012 filed BEFORE any "
             "call); numbers land from the measured record at finalize "
             "(the CI recomputes them from the cited record — PENDING "
             "carries no invented numbers); the repair pass is NEUTRAL "
             "(typed findings only) so the arm under test is the "
             "CONTRACT BIND"})
rf.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n",
              encoding="utf-8")

p = REPO / "eval" / "work_claims.json"
d = json.loads(p.read_text(encoding="utf-8"))
d["claims"].append({
    "claim_id": "c-0012", "work_id": "r23-feas-bind-v6",
    "session_id": "builder-r20s1", "role": "EXECUTOR", "kind": "measurement",
    "base_sha": "91870128d", "claimed_at": "2026-11-15T18:58:00Z",
    "lease_expiry": "2026-11-15T21:10:00Z", "status": "OPEN",
    "takes_over": None,
    "artifact_paths": ["eval/pairs/r23_feas_bind_v6/",
                       "eval/battery_feas_bind_v6_r23.json",
                       "eval/battery_feas_bind_v6_r23.partial.json"],
    "notes": "AM23 D2 round-2 — the feasibility lever moves INTO the "
             "draft contract: SYS_A1_INT_V6 = V4 + FEASIBILITY BIND at "
             "MECHANISM CHOICE (procurable classes only; bill format "
             "mandated at draft — the V5 lesson; MINIMAL bill; novelty "
             "lives in the CHANGE; the bind outranks mechanism "
             "preference — choose a different mechanism if the first "
             "cannot meet it). Machine path byte-unchanged (critic + "
             "gate + NEUTRAL typed machine repairs, budget 2, findings "
             "disclosed — the r20/r21/holdout code path); repair pass "
             "is neutral so the arm under test is the CONTRACT BIND. "
             "Byte map: 18 fresh intervention (K_GEN=1, no selection) + "
             "12 predictor rides byte-identical r11 (n=30). "
             "Pre-registration = scripts/r23_a1w_v6_contract.py + "
             "scripts/r23_feas_bind_v6.py committed in this push BEFORE "
             "any LLM call (Art. 29(b)). Canonical metric unchanged "
             "(Art. 16/19); judge crowllm/Qwen != generator zai/GLM; "
             "transport ladder identical; phases staggered. FAIL-CLOSED "
             "ARITHMETIC DISCLOSURE (pre-registered): predictor rides "
             "carry r11 fgap sum 14 -> overall <=0.25 floor 14/30 ~= "
             "0.467 by construction; this battery decides the LEVER "
             "(Art. 20 ablation vs the single-draw incumbent; V5 "
             "retired at round 1 with this successor shipping in the "
             "same change, Art. 16). VERIFIER: the peer session is "
             "invited — recompute from committed bytes (Art. 13), "
             "NEVER re-run; flips to DONE only when the verifier record "
             "exists."})
p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
             encoding="utf-8")
print("registry: V5 RETIRED (successor typed) + V6 PENDING; c-0012 filed")
