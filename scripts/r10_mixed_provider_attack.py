#!/usr/bin/env python3
"""r10_mixed_provider_attack.py — R10 P1 item 9 (owner): the REAL
mixed-provider attack-batch independence verification.

The directive: a real mixed-provider generator batch must run through
the CANONICAL independent_attack_batch/2.0.0 and its independence
labels must be HONEST — when the attacker's cascade lands on a
provider INSIDE the generator set, the label is typed
SHARED_WITH_A_GENERATOR and provider independence is NEVER claimed
(Art. XLV: a separate conversation context is not independent
validation).

The probe:
  1. generates candidates for ONE problem from TWO real providers
     (zai/glm-4-plus and xkiro/mistralai/ministral-14b) — a genuinely
     MIXED generator set, each candidate carrying its own
     generator_provider identity;
  2. runs independent_attack_batch with generator_providers covering
     BOTH (the attacker is admitted excluding both — and when the
     cascade cannot serve from OUTSIDE the set, the fallback is typed);
  3. writes eval/attack_mixed_provider_r10.json with per-candidate
     independence, the transport records, and the honest batch-level
     verdict (attacker_excludes_every_generator may be FALSE — that is
     the honest answer when the only serving attacker is inside the
     set; it is recorded, never upgraded).

Serves: Arts. XLV, LXI, XXV, XXIX.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402

names = _load_key_vault()
print("[r10atk] vault loaded (names only):", sorted(names))
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
os.environ["ENGINE_LLM_TIMEOUT_S"] = "40"
os.environ["ENGINE_LLM_RETRY_SLEEP_S"] = "0"
os.environ["FABRIC_PROBLEM_CALL_CAP"] = "60"

gw = subprocess.run(["bash", "scripts/zai_gateway_env.sh"], cwd=str(REPO),
                    capture_output=True, text=True, timeout=90)
if gw.returncode == 0:
    for line in (gw.stdout or "").splitlines():
        line = line.strip()
        if line.startswith("export ") and "=" in line:
            k, v = line[len("export "):].split("=", 1)
            os.environ[k] = v
    print("[r10atk] zai gateway admitted")
else:
    print("[r10atk] TYPED: zai gateway unavailable this window")
    sys.exit(3)

from discovery_fabric.engine.mechanism_space import llm_generate  # noqa: E402
from discovery_fabric.engine.independent_attack import (  # noqa: E402
    independent_attack_batch)

DEV12 = REPO / "eval" / "problems_dev12.json"
PAIRS = REPO / "eval" / "pairs" / "dev12_fresh"

PID = sys.argv[1] if len(sys.argv) > 1 else "dev-fu-005-bridge-bearing"
prob = next(p for p in json.loads(
    DEV12.read_text(encoding="utf-8"))["problems"]
    if p["problem_id"] == PID)
pair = json.loads((PAIRS / f"{PID}.json").read_text(encoding="utf-8"))
evidence = [{"id": e, "text": "the served evidence record of the "
             "audited run is bound by the pair's evidence_ids"}
            for e in (pair.get("evidence_ids") or [])][:6] or \
    [{"id": "pair-bound-evidence", "text": "the pair's evidence_ids "
      "bind the frozen records"}]

# ---- mixed-provider candidate generation (REAL, two providers) ----
GEN_SPECS = [("zai", "glm-4-plus"), ("xkiro", "mistralai/ministral-14b")]
prompt = (
    f"Device: {prob.get('device', '')}. Failure: {prob.get('failure', '')}.\n"
    "Propose ONE concrete intervention mechanism for this failure. "
    "Output exactly:\nMECHANISM: <one sentence, the causal mechanism>\n"
    "INTERVENTION: <one sentence, the concrete change>\n")
candidates = []
gen_providers = []
for prov_id, model in GEN_SPECS:
    os.environ["ENGINE_LLM_PROVIDER"] = prov_id
    t0 = time.time()
    res = llm_generate(prompt, max_tokens=300, timeout=40,
                       max_retries=1, purpose="candidate_generation",
                       hard_pin_provider=prov_id)
    wall = round(time.time() - t0, 1)
    ok = bool(res.get("ok"))
    content = str(res.get("content") or "")
    print(f"[r10atk] generator {prov_id}/{model}: ok={ok} "
          f"({wall}s, {len(content)} chars)")
    if ok and "MECHANISM" in content:
        candidates.append({
            "candidate_id": f"cand:{prov_id[0]}{len(candidates)}",
            "mechanism": content.strip()[:600],
            "generator_provider": prov_id,
            "generator_model": model})
        gen_providers.append(prov_id)
os.environ.pop("ENGINE_LLM_PROVIDER", None)

if len(gen_providers) < 2:
    print("[r10atk] TYPED: fewer than 2 generator providers served — "
          "the mixed-provider batch cannot run honestly this window "
          "(the record carries what served)")
record = {
    "record": "r10_mixed_provider_attack/1.0.0",
    "problem_id": PID,
    "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "generator_providers_verified": sorted(set(gen_providers)),
    "n_candidates": len(candidates),
    "batch_attacker_independent_of_every_generator": None,
    "per_candidate": [],
    "transports": [],
}
if len(gen_providers) >= 2:
    t0 = time.time()
    res = independent_attack_batch(
        candidates, prob, evidence,
        generator_provider=candidates[0].get("generator_provider"),
        generator_providers=sorted(set(gen_providers)),
        llm_generate=llm_generate)
    wall = round(time.time() - t0, 1)
    # the v2 batch result carries per-candidate records under
    # `records` (keyed by candidate id); every record's independence
    # fields are the honest typed verdicts
    recs = res.get("records") or {}
    per = []
    for cid, c in (recs.items() if isinstance(recs, dict) else []):
        if isinstance(c, dict):
            per.append({
                "candidate_id": c.get("candidate_id") or cid,
                "generator_provider": c.get("generator_provider"),
                "generator_model": c.get("generator_model"),
                "independence_mode": c.get("independence_mode"),
                "attack_state": c.get("state") or c.get("attack_state"),
                "attack_overall": (c.get("attack_results") or {}).get(
                    "overall") or c.get("overall")})
    record["per_candidate"] = per
    record["batch_records_keys"] = sorted(recs.keys()) if isinstance(
        recs, dict) else None
    record["unparsed"] = res.get("unparsed") or []
    record["transports"] = res.get("transports") or []
    record["transport"] = res.get("transport")
    record["attack_overall"] = (res.get("attack_results") or {}).get(
        "overall") or res.get("overall")
    record["wall_s"] = wall
    # the honest batch-level verdict: the attacker is independent of
    # every generator ONLY when every group's served provider is
    # OUTSIDE the generator set
    served = [t.get("attacker_provider") for t in record["transports"]]
    genset = set(record["generator_providers_verified"])
    record["attacker_providers_served"] = sorted(
        {str(s) for s in served if s})
    record["attacker_excludes_every_generator"] = bool(
        record["attacker_providers_served"]) and not (
        set(record["attacker_providers_served"]) & genset)
    record["no_candidate_labeled_shared_unless_fallback"] = (
        "a SHARED_* mode can only arise from a cascade fallback onto "
        "a provider inside the generator set (typed, Art. XLV)")

out = REPO / "eval" / "attack_mixed_provider_r10.json"
out.write_text(json.dumps(record, indent=1, default=str) + "\n",
               encoding="utf-8")
print("[r10atk] wrote", out)
print(json.dumps({k: record[k] for k in
                  ("generator_providers_verified", "n_candidates",
                   "attacker_excludes_every_generator",
                   "attacker_providers_served") if k in record},
                 indent=1))
for c in record["per_candidate"][:6]:
    print("  ", json.dumps({k: c.get(k) for k in
                            ("candidate_id", "generator_provider",
                             "independence_mode", "attack_state",
                             "attack_overall") if k in c}))
