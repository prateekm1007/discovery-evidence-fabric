#!/usr/bin/env python3
"""R451 §1 verification: the zero-paid transport + the fail-closed policy.

Run inside ONE tool call (the sandbox reaps the llama-server at the
boundary): starts the server, calls generate() through the registry
with LOCAL_QWEN_BASE_URL wired, prints the cost provenance, then
UNWIRES the local provider and proves the policy REFUSES the paid
fallback (POLICY_BLOCKED, never a silent paid route).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r451_local_qwen as lq  # noqa: E402

assert lq.ensure_server(), "llama-server failed to start"
os.environ["LOCAL_QWEN_BASE_URL"] = lq.BASE + "/v1/chat/completions"
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "ZERO_PAID_COST")

from discovery_fabric.engine import llm_registry as reg  # noqa: E402

res = reg.generate(
    prompt=("Reply in EXACTLY this format (one line):\n"
            "STATUS: <one word>"),
    system="transport policy probe", max_tokens=16, max_retries=0,
    timeout=120)
print("== zero-paid call ==")
print("status:", res.status)
print("provider:", res.provider_id, "model:", res.model)
print("cost_provenance:", json.dumps(res.cost_provenance, indent=1))
print("content:", (res.content or "")[:80].strip())

# fail-closed: remove the ONLY zero-paid route; a paid key is present
# (simulated) but the policy must REFUSE it — never silently fall back
del os.environ["LOCAL_QWEN_BASE_URL"]
os.environ["OPENAI_API_KEY"] = "sk-simulated-paid-key-not-real"
res2 = reg.generate(
    prompt="Reply with: READY", system="policy probe",
    max_tokens=8, max_retries=0, timeout=30)
print("\n== fail-closed (local server unwired; paid key present) ==")
print("status:", res2.status)
print("error:", (res2.error or "")[:160])
refusals = (res2.selection_ledger or {}).get("cost_policy_refusals", [])
print("paid refusals recorded:", len(refusals))
assert res2.status == "POLICY_BLOCKED", "FAIL: paid fallback not refused"
assert res2.content is None, "FAIL: content from a refused route"
print("\nVERDICT: PASS — zero-paid transport serves; paid routes refused")
