import json, sys
from pathlib import Path

p = Path("R519/R519_ROUND_RECORD.json")
d = json.loads(p.read_text(encoding="utf-8"))   # fail-closed on invalid JSON

b = d["fresh_performance_battery"]
b["credential_blocker_status"] = "RESOLVED_MID_ROUND"
b["credential_blocker_resolution"] = (
    "operator supplied HF_TOKEN + GITHUB_PAT in-session (fingerprints match "
    "the standing vault: 33bc7af22c628bc1 / f1ebca5f9b62 — no rotation, Art. "
    "LXXVI §2). Art. LXXIII step 3 (the HF Space secret surface) is now "
    "reachable; the deployed engine at 968e1d74 reports provider credentials "
    "CONFIGURED (atria HEALTHY; openrouter, nvidia, apinex, xkiro, unorouter, "
    "zai, bai, bynara configured). The recorded blocker "
    "MEASUREMENT_BLOCKED_MISSING_PROVIDER_CREDENTIALS no longer holds.")
b["new_constraint_for_AB"] = (
    "SYNTHESIZE and MECHANISM_SPACE have NO per-request provider-arm lever: "
    "require_provider is wired only to the attack/calibration endpoints "
    "(TOSCANINI/server.py). A same-instrument two-arm A/B (Art. XLVII) for "
    "those stages therefore requires TWO production Space deployments — "
    "baseline (pre-R518 routing: ENGINE_DEFAULT_PROVIDER=atria pin + old "
    "retirement table) and optimized (R519 ordinary routing) — across fresh "
    "disjoint problems with repetitions. That mutates deployed production "
    "identity and spends live provider budget. Scope decision escalated to "
    "the operator (Art. LXV / LXXI §4); NOT undertaken unilaterally.")
b["status"] = "READY_PENDING_OPERATOR_SCOPE_DECISION"

tb = d["typed_blocker"]
tb["code"] = "BATTERY_AWAITING_OPERATOR_SCOPE_DECISION"
tb["previous_code"] = "MEASUREMENT_BLOCKED_MISSING_PROVIDER_CREDENTIALS"
tb["note"] = (
    "Credential blocker RESOLVED this round (see "
    "fresh_performance_battery.credential_blocker_resolution). The remaining "
    "gate for an OPTIMIZATION_PROVEN classification is the operator's "
    "scope/cost decision on the two-deployment fresh-problem A/B.")
tb["escalation_required_from_operator"] = True
tb["escalation_question"] = (
    "Run the full two-deployment fresh-problem performance A/B now (spends "
    "live provider budget, temporarily changes deployed production identity "
    "to the pre-R518 baseline build), or accept "
    "ROUTING_IMPLEMENTED_BUT_UNPROVEN + deploy-GREEN for this round and "
    "schedule the A/B as a dedicated later round?")

d["classification"] = "ROUTING_IMPLEMENTED_BUT_UNPROVEN"

p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n",
             encoding="utf-8")
print("OK: reloaded + rewrote valid JSON")
print("classification:", d["classification"])
print("blocker:", tb["code"])
print("battery:", b["status"])
