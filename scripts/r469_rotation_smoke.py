#!/usr/bin/env python3
"""R469 — the LIVE key-ring rotation smoke: the operator's keep-going
directive measured end-to-end through the REAL Atria API.

Operator instruction (2026-09-16, verbatim, key bodies redacted BS-021):
  "From Now on atira is out default API for discovery engine. Keep
   going to a new key of atira if one is exhausted. Wire it in the
   discovery engine."

Method (the R463/R467/R468 bogus-key differential — NO real budget is
spent on failures): a BOGUS head key fails auth exactly like an
exhausted/revoked one (401 -> AUTH_FAILURE, a KEY_ROTATION class), so
substituting it measures the rotation machinery against the live
endpoint without exhausting anything. Four arms:

  ARM 1 (control)     — all three REAL keys, fresh probe: the call
                        serves on slot 0 (the healthy baseline; also
                        proves the DEFAULT-PROVIDER pin puts atria at
                        the head of the live chain, and exercises the
                        probe's small-cap starvation recovery when the
                        reasoning model spends the 16-token probe cap).
  ARM 2 (probe-path   — key 1 bogus, fresh probe: the PROBE itself
         rotation)      rotates past the dead slot (an exhausted head
                        key must not PROBE_FAILED the rung) and the
                        call serves on the first REAL key.
  ARM 3 (call-loop    — key 1 bogus, capability record still fresh
         rotation)      (no re-probe): the CALL LOOP rotates past the
                        dead slot — the generate()-level rotation hop.
  ARM 4 (two-hop      — keys 1+2 bogus, fresh probe: the walk rotates
         walk)          past BOTH dead slots and serves on key 3.

Each arm is a REAL llm_registry.generate() call (the engine's single
entry point — availability -> pinned chain -> ladder -> runtime
admission probe -> call loop), so the artifact measures the exact
production path.

Keys come from the ENVIRONMENT ONLY (BS-021). The artifact records
measurements and FINGERPRINTS, never values.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import llm_registry as lr  # noqa: E402
from discovery_fabric.engine import runtime_admission as ra  # noqa: E402

OUT = REPO / "R469" / "ROTATION_SMOKE.json"
BOGUS1 = "atr_bogus ring-slot-1 differential 0000000001"
BOGUS2 = "atr_bogus ring-slot-2 differential 0000000002"
MODEL = "Atria-Dawn-Preview"

SCHEMA = ["FIELD_MECHANISM", "FIELD_KEY_VARIABLE", "FIELD_FALSIFIER"]
PROMPT = (
    "Propose ONE physical mechanism for reducing scaling deposits in a "
    "hot-water heat exchanger. Output EXACTLY three lines:\n"
    "FIELD_MECHANISM: <one sentence>\n"
    "FIELD_KEY_VARIABLE: <the single measurable quantity>\n"
    "FIELD_FALSIFIER: <the observation that would kill it>")


def fp(val: str) -> str:
    return f"{val[:6]}...{val[-4:]} (len {len(val)})" if val else "(unset)"


def run_arm(name: str, k1: str, k2: str, k3: str,
            fresh_probe: bool) -> dict:
    """One live generate() walk with the given ring values."""
    lr._reset_key_ring("atria")                     # fresh walk per arm
    os.environ["ATRIA_API_KEY"] = k1
    os.environ["ATRIA_API_KEY_2"] = k2
    os.environ["ATRIA_API_KEY_3"] = k3
    if fresh_probe:
        # the standing invalidation API (the post-failure re-probe
        # discipline) — forces the arm to walk the admission probe too
        try:
            ra.invalidate_capability(
                "atria", MODEL, reason="R469 smoke arm isolation")
        except Exception:  # noqa: BLE001 — best-effort isolation
            pass
    t0 = time.time()
    res = lr.generate(PROMPT, schema=SCHEMA, role="synthesis",
                      max_tokens=2000)
    dt = round(time.time() - t0, 2)
    hops = (res.route or [])
    ok_hop = next((h for h in hops if h.get("status") == "OK"), None)
    rot_hops = [h for h in hops if h.get("action") == "KEY_ROTATED"]
    probe_ev = (res.selection_ledger.get("ladder", {})
                .get("capability_evidence", [])
                if res.selection_ledger else [])
    chain = (res.selection_ledger or {}).get("chain", [])
    arm = {
        "arm": name,
        "fresh_probe": fresh_probe,
        "ring_fingerprints": [fp(k1), fp(k2), fp(k3)],
        "status": res.status,
        "ok": res.ok,
        "provider": res.provider_id,
        "model": res.model,
        "seconds": dt,
        "chain_head": chain[0] if chain else None,
        "chain": chain,
        "serving_key_slot": ok_hop.get("key_slot") if ok_hop else None,
        "serving_key_env_var": (ok_hop.get("key_env_var")
                                if ok_hop else None),
        "key_rotations_in_call": (ok_hop or {}).get("key_rotations"),
        "rotation_hops": [
            {"from_slot": h.get("key_slot_exhausted"),
             "to_slot": h.get("key_slot"),
             "to_env_var": h.get("key_env_var"),
             "failure_type": h.get("failure_type"),
             "status": h.get("status")}
            for h in rot_hops],
        "skipped_or_failed_hops": [
            {"provider": h.get("provider_attempted"),
             "status": h.get("status"),
             "failure_type": h.get("failure_type")}
            for h in hops if h.get("status") not in ("OK", None)],
        "probe_evidence_states": [
            {"provider": e.get("provider"),
             "capability_state": e.get("capability_state")}
            for e in (probe_ev or []) if e.get("provider") == "atria"],
        "task_degradation": res.task_degradation,
        "retry_notes": list(res.retry_notes or []),
        "fields_present": (
            [f for f in SCHEMA
             if f.lower() in (res.content or "").lower()]
            if res.content else []),
        "error": (res.error or None),
    }
    print(f"[{name}] status={res.status} in {dt}s "
          f"serving_slot={arm['serving_key_slot']} "
          f"env={arm['serving_key_env_var']} "
          f"rot_hops={len(rot_hops)} chain_head={arm['chain_head']}")
    return arm


def main() -> int:
    real1 = os.environ.get("ATRIA_API_KEY", "").strip()
    real2 = os.environ.get("ATRIA_API_KEY_2", "").strip()
    real3 = os.environ.get("ATRIA_API_KEY_3", "").strip()
    missing = [n for n, v in (("ATRIA_API_KEY", real1),
                              ("ATRIA_API_KEY_2", real2),
                              ("ATRIA_API_KEY_3", real3)) if not v]
    if missing:
        print(f"FATAL: real keys unset in session env (BS-021): {missing}")
        return 2

    out = {"round": "R469", "provider": "atria",
           "subject": "the LIVE key-ring rotation smoke — the keep-going "
                      "directive measured through the real API via the "
                      "bogus-key differential (no real budget spent on "
                      "failures)",
           "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
           "arms": []}

    # ARM 1: control — all real keys, fresh probe
    out["arms"].append(run_arm("control_all_real", real1, real2, real3,
                               fresh_probe=True))
    # ARM 2: key 1 dead (bogus differential), fresh probe -> the PROBE
    # rotates past the dead slot
    out["arms"].append(run_arm("probe_rotation_key1_dead", BOGUS1,
                               real2, real3, fresh_probe=True))
    # ARM 3: key 1 dead, capability fresh from ARM 2 -> no re-probe ->
    # the CALL LOOP rotates past the dead slot
    out["arms"].append(run_arm("callloop_rotation_key1_dead", BOGUS1,
                               real2, real3, fresh_probe=False))
    # ARM 4: keys 1+2 dead — only key 3 real, fresh probe
    out["arms"].append(run_arm("two_hop_keys12_dead", BOGUS1, BOGUS2,
                               real3, fresh_probe=True))

    a1, a2, a3, a4 = out["arms"]
    served_not_bogus = lambda a: (  # noqa: E731
        a["ok"] and a["provider"] == "atria"
        and a["serving_key_env_var"] in ("ATRIA_API_KEY",
                                         "ATRIA_API_KEY_2",
                                         "ATRIA_API_KEY_3"))
    verdict = {
        "control_served_on_slot_0": (
            a1["ok"] and a1["serving_key_slot"] == 0
            and a1["serving_key_env_var"] == "ATRIA_API_KEY"),
        "control_chain_head_is_atria": a1["chain_head"] == "atria",
        "probe_rotation_served_on_real_key": (
            served_not_bogus(a2)
            and a2["serving_key_env_var"] != "ATRIA_API_KEY"
            and a2["serving_key_slot"] in (1, 2)),
        "callloop_rotation_recorded": (
            served_not_bogus(a3)
            and a3["serving_key_env_var"] != "ATRIA_API_KEY"
            and len(a3["rotation_hops"]) >= 1
            and a3["rotation_hops"][0]["failure_type"] == "AUTH_FAILURE"
            and a3["rotation_hops"][0]["status"]
            == "FAILED_KEY_EXHAUSTED"),
        "two_hop_walk_served_on_key3": (
            a4["ok"] and a4["provider"] == "atria"
            and a4["serving_key_env_var"] == "ATRIA_API_KEY_3"
            and a4["serving_key_slot"] == 2),
        "all_arms_served_by_atria": all(
            a["ok"] and a["provider"] == "atria"
            for a in (a1, a2, a3, a4)),
        "no_arm_fell_off_the_ring": all(
            a["provider"] == "atria" for a in (a1, a2, a3, a4)),
    }
    verdict["ALL_GREEN"] = all(verdict.values())
    out["verdict"] = verdict

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"artifact -> R469/ROTATION_SMOKE.json (fingerprints only)")
    print(json.dumps(verdict, indent=2))
    return 0 if verdict["ALL_GREEN"] else 1


if __name__ == "__main__":
    sys.exit(main())
