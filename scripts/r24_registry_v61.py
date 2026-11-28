#!/usr/bin/env python3
"""r24_registry_v61.py — Art. 16/20 accounting for V6 ROUND 2: the
contract-bind lever (same arm, no clock reset) is strengthened with
the F36 constraint-awareness; claim c-0014 filed BEFORE any call."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

rf = REPO / "eval" / "ABLATION_REGISTRY.json"
reg = json.loads(rf.read_text(encoding="utf-8"))
v6 = next(e for e in reg["entries"]
          if e.get("status") == "ACTIVE"
          and "contract_bind" in str(e.get("stage", "")))
assert v6.get("rounds_without_beating") == 1
v6["notes"] = (
    "AM24 D1 = ROUND 2/2 of this arm (claim c-0014, work_id "
    "r24-v61-constraint-bind, executor builder-r20s1; pre-registration "
    "pushed BEFORE any LLM call). The lever is UNCHANGED in kind "
    "(contract-level bind at mechanism choice — no clock reset, Art. 20 "
    "anti-zombie); round 2 strengthens it with the F36 "
    "constraint-awareness fix the auditor demanded: the contract reads "
    "the problem's OWN constraint text (allowed-measures enumerations "
    "= hard lists; exclusion cues = hard exclusions; performance bounds "
    "= bill verification targets) and the machine repair loop carries a "
    "typed deterministic constraint-fit scan "
    "(scripts/r24_constraint_scan.py, findings disclosed). Round-1 "
    "evidence motivating round 2: the bind fixed the V5 failure modes "
    "(repairs 29->19, residuals 11->5) and produced 2/18 PERFECT-parity "
    "rows (fgap=0 with nd=4), but a heavy tail (7/18 at fgap=4) "
    "dominated the mean; the F36 evidence (HO2-03 zinc-anode collar and "
    "HO2-04 intake-humidity OUTSIDE the stated allowed measures) shows "
    "the machine reaches for out-of-scope measures — the round-2 bind "
    "targets exactly that. Round-2 rule: if not beating the incumbent "
    "on the primary metric, the contract-bind lever RETIRES at 2 (no "
    "round 3 under this lever kind). Driver: "
    "scripts/r24_feas_bind_v61.py; record: "
    "eval/battery_feas_bind_v61_r24.json; byte map identical to r23 "
    "(controlled comparison).")
rf.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n",
              encoding="utf-8")

p = REPO / "eval" / "work_claims.json"
d = json.loads(p.read_text(encoding="utf-8"))
d["claims"].append({
    "claim_id": "c-0014", "work_id": "r24-v61-constraint-bind",
    "session_id": "builder-r20s1", "role": "EXECUTOR",
    "kind": "measurement", "base_sha": "7f645e406",
    "claimed_at": "2026-11-15T20:05:00Z",
    "lease_expiry": "2026-11-15T22:20:00Z", "status": "OPEN",
    "takes_over": None,
    "artifact_paths": ["eval/pairs/r24_feas_bind_v61/",
                       "eval/battery_feas_bind_v61_r24.json",
                       "eval/battery_feas_bind_v61_r24.partial.json"],
    "notes": "AM24 D1 — V6 ROUND 2/2 (the binding-clause attempt, Art. "
             "20 clock): the contract-level feasibility bind is "
             "strengthened with the F36 constraint-awareness fix — "
             "SYS_A1_INT_V61 = V6 bind + CONSTRAINT BIND reading the "
             "problem's own constraint text (allowed-measures "
             "enumerations = hard lists; exclusion cues like 'without "
             "X'/'no change to X'/'retrofit only' = hard exclusions; "
             "performance bounds = bill verification targets; the bind "
             "outranks mechanism preference), plus SYS_A1F_V5 = "
             "SYS_A1F_V4 + PRIMARY-INDICATOR CONSTRAINT for the "
             "predictor side (affects holdout v3's one-shot only; this "
             "battery rides predictors byte-identical r11). Machine "
             "path byte-unchanged (critic + gate + NEUTRAL typed "
             "repairs, budget 2); the repair loop's typed scan now "
             "includes the deterministic constraint-fit scan "
             "(scripts/r24_constraint_scan.py — segment-based: "
             "exclusion cues searched anywhere, allowed-list segments "
             "classified before exclusion subtraction; CONSERVATIVE "
             "typed limit: purely-semantic violations without term "
             "overlap are NOT flagged — the authoritative constraint-"
             "fit read is the auditor's on holdout v3). Byte map "
             "IDENTICAL to r23 (18 fresh intervention + 12 predictor "
             "rides byte-identical r11, n=30 — controlled comparison "
             "against the same incumbent bytes). Pre-registration = "
             "scripts/r24_a1w_v61_contract.py + "
             "scripts/r24_constraint_scan.py + "
             "scripts/r24_feas_bind_v61.py committed in this push "
             "BEFORE any LLM call (Art. 29(b)). Canonical metric "
             "unchanged (Art. 16/19); judge crowllm/Qwen != generator "
             "zai/GLM; transport ladder identical; phases staggered. "
             "FAIL-CLOSED ARITHMETIC DISCLOSURE (unchanged, "
             "pre-registered): rides floor 14/30 ~= 0.467; the Art. 20 "
             "decision reads on the changed arm (summary_intervention_"
             "rows vs the r20 incumbent; V6 round 1 = 2.333 vs "
             "incumbent 1.5). Round-2 rule: not beating = the "
             "contract-bind lever RETIRES at 2 with full accounting. "
             "Acceptance verbatim AM24 D1. VERIFIER: the peer session "
             "is invited — recompute from committed bytes (Art. 13), "
             "NEVER re-run; flips to DONE only when the verifier "
             "record exists."})
p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
             encoding="utf-8")
print("registry: V6 round-2 note typed; claim c-0014 filed")
