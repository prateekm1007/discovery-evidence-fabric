#!/usr/bin/env python3
"""R451-C1.3 — re-bind the CONSTITUTION_ACKNOWLEDGMENT to this session
(the standing pre-commit discipline; the acknowledgment is re-bound each
coding round to the round's actual intended change)."""
import json
import hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ACK = REPO / "epistemic_integrity" / "approved_provenance" / \
    "CONSTITUTION_ACKNOWLEDGMENT.json"
CONST = REPO / "EPISTEMIC_CONSTITUTION.md"

const_bytes = CONST.read_bytes()
const_hash = hashlib.sha256(const_bytes).hexdigest()
const_version = ""
for line in const_bytes.decode().splitlines():
    if line.startswith("**Version:**"):
        const_version = line.split("**Version:**")[1].strip()
        break

ack = {
    "constitution_version": const_version,
    "constitution_hash": const_hash,
    "acknowledged_at": "2026-09-13T08:30:00+00:00",
    "acknowledged_by": "Coder 1 (R451-C1.3 session)",
    "session": "r451-c13-transport-authority-provenance-closure",
    "intended_change": (
        "R451-C1.3 (operator directive, 2026-09-13): Production Transport "
        "Authority + Provenance Closure. (1) runtime_admission.py — the "
        "five-state measured route vocabulary (NOT_PROBED / PROBE_OK / "
        "PROBE_FAILED / PROBE_EXPIRED / POLICY_REFUSED) as the RUNTIME "
        "admission authority: llm_registry.generate() never treats "
        "credential_present=true as admissibility; probe-before-admit "
        "through the rung's REAL transport with the EXISTING TTL "
        "mechanism (no per-call probing); successful real calls refresh "
        "the window; real-call transport failures invalidate it; the "
        "LOCAL route uses the SAME rule (no bespoke local exception); "
        "transient probe failures absorbed by one bounded retry, "
        "permanent classes never retried. (2) call_context.py + run.py — "
        "run-level routing provenance: every run-owned engine call "
        "carries run_id/session_id/engine_stage (the conductor binds the "
        "run identity; run_owned_call => run_id != null fails CLOSED in "
        "the ledger; capability probes legitimately carry run_id=null as "
        "call_class=CAPABILITY_PROBE); ROUTING_LEDGER_RUN.json isolates "
        "one run's lines BY RUN ID — no time-window or ledger-tail "
        "inference. (3) C1.4 explicit task degradation (requested_task / "
        "actual_task_capability / task_capability_match / "
        "degraded_reason on every selected line and in the candidate's "
        "derivation trace — a CHEAP_EMERGENCY_FALLBACK candidate is never "
        "read as STRONG reasoning). (4) C1.5 catalog-discovered semantics "
        "(DISCOVERED -> only catalog-present models are candidates; "
        "UNDISCOVERED -> pinned defaults explicitly marked "
        "PINNED_DEFAULT; the family allowlist stays; the pinned-dead-"
        "identifier retention REMOVED). (5) C1.6 MODEL_NOT_FOUND recovery "
        "(a FRESH catalog relisting clears the known-dead mark and "
        "invalidates the stale capability record — deterministic, "
        "append-only recovery events). (6) C1.7 the ONE runtime-"
        "admission semantic shared by select_provider() and generate() "
        "(available AND cost_policy_eligible AND "
        "measured_capability_eligible — no legacy weaker selector). "
        "(7) C1.8 the canonical Space's OWN zero-paid route (llama.cpp "
        "llama-server built from the pinned tag + the sha-pinned "
        "Qwen3-1.7B Q4_K_M GGUF, env-gated entrypoint, probe-before-admit "
        "on the Space). (8) C1.9 ONE bounded ZeroGPU experiment (no "
        "model leaderboard; the single question: can a small open-weight "
        "reasoning model run inside the canonical Space's ZeroGPU "
        "allocation and satisfy the Toscanini transport contract). "
        "(9) C1.10 production deployment at the pushed SHA (/api/version "
        "== /api/health == ls-remote) + a fresh production run recording "
        "every call with run_id. Transport failures stay transport "
        "(Art. LXI); no verifier, gate, threshold, or epistemic "
        "semantics modified (Art. VII); no benchmark started; no "
        "candidate-generation heuristics added; the scientific engine "
        "unchanged. Constitution v2.4.0 read IN FULL at session start "
        "and re-read IN FULL before the final commit."
    ),
    "pre_session_warning": (
        "Never optimize for the gate. Do not manufacture provenance. Do "
        "not weaken verification to admit a desired claim. Do not use "
        "weaker fallback evidence. Do not convert uncertainty into "
        "certainty. If the gate is RED, research remains STOPPED. "
        "Unprovable history remains unproven."
    ),
}
ACK.write_text(json.dumps(ack, indent=1, ensure_ascii=False) + "\n")
print(f"re-bound: {const_version} {const_hash[:12]}")
print(f"-> {ACK}")
