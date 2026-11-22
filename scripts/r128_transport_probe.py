#!/usr/bin/env python3
"""R128 dir-4 probe: both new transports, typed refusals first, then the
funded call with usage bytes appended to eval/r128_transport_probe.json.
Idempotent: re-run whenever the owner adds a key; the record is updated
in place (the funded-call clause filled), never rewritten."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
from discovery_fabric.engine import route_adapter as ra

REC = REPO / "eval" / "r128_transport_probe.json"
out = json.loads(REC.read_text())
updates = []

# --- Bedrock: dry-run typed refusal (always safe) -------------------------
try:
    ra.bedrock_converse([{"role": "user", "content": "x"}],
                        "anthropic/claude-3-haiku", max_tokens=8)
    updates.append("bedrock: NO refusal on a keyless dry run — typed-refusal REGRESSION")
except ra.RouteRefused as e:
    out["bedrock"]["dry_run"]["typed_refusal"] = str(e)
    out["bedrock"]["dry_run"]["test"] = "PASS"
    updates.append(f"bedrock dry run typed refusal: {e}")

# --- Bedrock: funded call (only when the key exists) ----------------------
try:
    r = ra.bedrock_converse(
        [{"role": "user", "content": "Reply with the single word OK."}],
        "anthropic/claude-3-haiku-v1" if False else out.get(
            "bedrock", {}).get("model_id_override",
                               "anthropic.claude-3-haiku-v1:0"),
        max_tokens=8, timeout_s=60)
    out["bedrock"]["funded_call"] = {
        "model": r["model"], "content": r["content"][:80],
        "usage_bytes": r["usage"], "raw_envelope_keys":
            sorted((r["raw"] or {}).keys())}
    updates.append(f"bedrock FUNDED call recorded: {r['usage']}")
except ra.RouteRefused as e:
    updates.append(f"bedrock funded call still refused (typed): {e}")

# --- HF router: funded call -----------------------------------------------
try:
    r = ra.hf_router_chat(
        [{"role": "user", "content": "Reply with the single word OK."}],
        "meta-llama/Llama-3.1-8B-Instruct", max_tokens=8, timeout_s=60)
    out["hf_router"]["first_funded_call"] = {
        "model": r["model"], "content": r["content"][:80],
        "usage_bytes": r["usage"]}
    updates.append(f"hf funded call recorded: {r['usage']}")
except ra.RouteRefused as e:
    updates.append(f"hf funded call refused (typed): {e}")

out["probe_runs"] = (out.get("probe_runs") or 0) + 1
out["last_probe_updates"] = updates
REC.write_text(json.dumps(out, indent=1) + "\n")
for u in updates:
    print(u)
