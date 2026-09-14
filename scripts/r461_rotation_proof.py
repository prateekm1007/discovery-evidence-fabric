#!/usr/bin/env python3
"""R461 — the LIVE ROTATION PROOF: real generate() calls through the
engine's actual admission + cascade path (the R456-A3 acceptance
discipline), measuring the operator's rotation rule on the five-router
registration:

  "Use these to use free ai models like qwen 3.8, glm 5.3, deepseek,
   minimax etc. once tokens run out of one go to the next provider"
  "create a system if one system ends of of tokens, you automatically
   go to next. we should never run out of tokens this way."

Arms (all REAL calls, no faked state — the only state used is the
providers' own live gate/credit conditions, re-measured in the run):
  A. THE NEW RUNG SERVES — preferred [bynara]: a FAST-class generation
     must land on the measured free answerer (tencent-hy3-free) with
     cost_provenance FREE_TIER_API / OWNER_BYNARA_ACCOUNT /
     ZERO_PAID_COST.
  B. ROTATION MEASURED LIVE — preferred [bynara, unorouter] on a
     STRONG task: bynara's catalog-discovered STRONG rungs are
     credit/plan-gated on the account RIGHT NOW (glm-5.3-free 402/429,
     qwen3.8-flash-free/muse-spark 403 — re-measured this run), so the
     cascade must ADVANCE past the typed failures and land on the next
     account's STRONG rung (unorouter glm-5.3:free) — token exhaustion
     on one provider automatically going to the next, measured live.
  C. THE QUINTET'S NATURAL ROUTE — default policy, all five keys live:
     records whatever the availability/quality order actually serves.

Keys from ENV ONLY (BS-021). The artifact records routes, typed
failure classes, latencies, and cost provenance — never key values.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import llm_registry as reg  # noqa: E402

PROMPT_FAST = (
    "You are a mechanical engineering assistant. Reply with exactly "
    "one line in the form FIELD: value — FIELD: one sentence naming "
    "the single most important thermal design constraint for a "
    "sealed electronic enclosure.")
PROMPT_STRONG = (
    "You are a materials-science reasoning assistant. Produce exactly "
    "three lines, each in the form FIELD: value — "
    "FIELD mechanism: one plausible crevice-corrosion mechanism for "
    "aluminum alloy 5052 in chlorinated water; "
    "FIELD variable: the dominant electrochemical variable that "
    "mechanism acts on; "
    "FIELD falsifier: the cheapest observation that would refute it.")


def _cost_prov(rec):
    cp = rec.cost_provenance or {}
    return {"cost_basis": cp.get("cost_basis"),
            "account_domain": cp.get("account_domain"),
            "policy": cp.get("policy"),
            "model_id": cp.get("model_id"),
            "provider": cp.get("provider_id") or rec.provider_id}


def _route(rec):
    out = []
    for hop in rec.route or []:
        out.append({"provider": hop.get("provider_attempted")
                    or hop.get("provider"),
                    "model": hop.get("model"),
                    "status": hop.get("status"),
                    "failure_type": hop.get("failure_type"),
                    "latency_ms": hop.get("latency_ms"),
                    "detail": (hop.get("detail")
                               or hop.get("error") or "")[:160]})
    return out


def _run_arm(name, prompt, preferred, role):
    t0 = time.time()
    policy = reg.SelectionPolicy(preferred_providers=preferred,
                                 purpose="general")
    rec = reg.generate(prompt, policy=policy, role=role,
                       max_tokens=220, timeout=180)
    arm = {
        "preferred": preferred,
        "role": role,
        "status": rec.status,
        "provider": rec.provider_id,
        "model": rec.model,
        "latency_ms": rec.latency_ms,
        "wall_s": round(time.time() - t0, 2),
        "content_head": (rec.content or "")[:220],
        "cost_provenance": _cost_prov(rec),
        "route": _route(rec),
        "failure_type": rec.failure_type,
    }
    print(f"--- ARM {name} [{','.join(preferred) or 'default'} "
          f"role={role}] ---")
    print(f"    status={rec.status} provider={rec.provider_id} "
          f"model={rec.model} {arm['wall_s']}s")
    for hop in arm["route"]:
        print(f"    hop {str(hop['provider']):10s} "
              f"{str(hop['model'])[:34]:34s}"
              f" {str(hop['status']):10s} "
              f"{str(hop['failure_type']):16s}")
    cp = arm["cost_provenance"]
    print(f"    cost: basis={cp.get('cost_basis')} "
          f"account={cp.get('account_domain')} policy={cp.get('policy')}")
    return arm


def main() -> int:
    missing = [v for v in ("UNOROUTER_API_KEY", "BYNARA_API_KEY",
                           "XKIRO_API_KEY", "APINEX_API_KEY",
                           "BAI_API_KEY")
               if not os.environ.get(v, "").strip()]
    if missing:
        print(f"FATAL: router keys unset in env: {missing} (BS-021 — "
              f"env only)")
        return 2
    os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "ZERO_PAID_COST")
    # The R418 operator pin: {PROVIDER}_MODEL routes the provider's
    # VERY FIRST attempt to a model the operator has MEASURED working
    # ("an operator who has measured a working model routes the
    # engine's very first attempt there instead of burning the cascade
    # on models the account cannot serve"). tencent-hy3-free is the
    # measured bynara answerer (3 consecutive PROBE_OKs) — the pin is
    # evidence-backed, the documented mechanism, never a faked state.
    os.environ["BYNARA_MODEL"] = "tencent-hy3-free"

    arms = {}
    # Arm A: a CHEAP-class generation (role=extraction) — the pinned
    # measured rung must serve ON bynara with the free-tier cost
    # provenance.
    arms["A_new_rung_serves"] = _run_arm(
        "A", PROMPT_FAST, ["bynara"], role="extraction")
    # Arm B: a STRONG-class generation — bynara's STRONG-capable rungs
    # are the credit/plan-gated catalog ids RIGHT NOW, so the cascade
    # must ADVANCE on the typed failures and land on the next
    # account's STRONG rung.
    arms["B_rotation_live"] = _run_arm(
        "B", PROMPT_STRONG, ["bynara", "unorouter"], role="synthesis")
    # Arm C: the default policy, all five keys live — records the
    # natural quintet route.
    arms["C_quintet_default"] = _run_arm(
        "C", PROMPT_STRONG, [], role="synthesis")

    # verdict fields (computed from the records, never narrated)
    a, b, c = (arms["A_new_rung_serves"], arms["B_rotation_live"],
               arms["C_quintet_default"])
    verdict = {
        "new_rung_serves": (
            a["status"] == "OK" and a["provider"] == "bynara"
            and a["cost_provenance"]["cost_basis"] == "FREE_TIER_API"
            and a["cost_provenance"]["account_domain"] ==
            "OWNER_BYNARA_ACCOUNT"),
        "rotation_advanced_on_typed_failure": (
            b["status"] == "OK"
            and any(h["provider"] == "bynara" and h.get("failure_type")
                    in ("CREDIT_EXHAUSTED", "RATE_LIMITED",
                        "AUTH_FAILURE", "MODEL_NOT_FOUND", "TIMEOUT",
                        "INVALID_RESPONSE", "UNKNOWN")
                    for h in b["route"])
            and b["provider"] != "bynara"),
        "quintet_route_recorded": c["status"] in ("OK", "CALL_FAILED"),
    }
    out = {"round": "R461",
           "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
           "policy": "ZERO_PAID_COST (FREE_TIER_API eligible, "
                     "model_cost_policy v1.1.0)",
           "arms": arms, "verdict": verdict,
           "note": ("real generate() calls through admission+cascade; "
                    "no faked state — the only failure state used is "
                    "the providers' own live gate/credit conditions")}
    path = REPO / "R461" / "ROTATION_PROOF.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nartifact -> R461/ROTATION_PROOF.json")
    print(f"verdict: {json.dumps(verdict)}")
    ok = verdict["new_rung_serves"] and \
        verdict["rotation_advanced_on_typed_failure"]
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
