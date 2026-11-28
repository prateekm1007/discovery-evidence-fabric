#!/usr/bin/env python3
"""r64s2_provider_census.py — OWNER-DIRECTIVE lane (claim c-0088).

The owner directive: (1) on z-ai failure use xiro (xkiro) or agnes;
(2) retire glm-4-plus ("too low level a model").

This script produces the EVIDENCE BASE for the lawful response:

  A. ROSTER CENSUS of the two alternates already qualified in the
     engine's ROUTE_REGISTRY (c-0078 end-to-end, R58 custody probe,
     keys vaulted): one GET {base_url}/models per route. No chat
     burns, no z-ai contact (the 429 window stays dark; these are
     XKIRO/AGNES custody probes, the R58 precedent), no engine
     modification (route_adapter is READ, never imported into any
     changed path).

  B. THE RE-REGISTRATION PROPOSAL: the R36 collision (glm-4-plus is
     the only servable id; zai-org/GLM-5.3 was falsified at zero
     reachable paths), the attestation constraint (the alternates'
     rosters carry no glm family — a failover call can never satisfy
     served==registered), the prereg pin (MANDATORY_RUN_ARTIFACTS[1]
     requires a 30/30 served_model==registered glm-4-plus
     attestation), the freeze-impact manifest, and the gated
     execution chain. The registered id is NOT changed here — the
     re-freeze act is gated on an auditor amendment superseding R36.

Keys are resolved BY NAME via route_adapter.resolve_vault_key and are
never printed, logged, or written to any artifact.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from discovery_fabric.engine.route_adapter import (  # noqa: E402
    BROWSER_UA, ROUTE_REGISTRY, RouteRefused, resolve_vault_key)

CENSUS_OUT = REPO / "eval" / "r64_provider_census.json"
PROPOSAL_OUT = REPO / "eval" / "r64_model_reregistration_proposal.json"

# families whose id NAMING conventionally marks a frontier/flagship
# tier — NAMING INFERENCE ONLY, never a strength measurement; the
# strength call belongs to the owner
FLAGSHIP_HINTS = ("gpt-5", "gpt-4.1", "gpt-4-turbo", "o3", "o4",
                  "claude-opus", "claude-sonnet-4", "claude-3.7",
                  "gemini-2.5-pro", "gemini-2.0", "deepseek-r",
                  "deepseek-v3", "qwen3", "qwen-max", "kimi",
                  "moonshot", "grok-3", "grok-4", "glm-4.5", "glm-5",
                  "glm-4-plus")


def roster(base_url: str, key: str, ua: str, route: str) -> dict:
    """One GET {base_url}/models. Typed outcome, never a bare crash."""
    url = base_url.rstrip("/") + "/models"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {key}", "User-Agent": ua,
        "Accept": "application/json"}, method="GET")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            body = json.loads(r.read())
        models = body.get("data") or body.get("models") or []
        ids = sorted({str(m.get("id") if isinstance(m, dict) else m)
                      for m in models if m})
        return {"route": route, "reachable": True,
                "latency_s": round(time.time() - t0, 2),
                "roster_n": len(ids), "model_ids": ids,
                "glm_family_present": any("glm" in i.lower()
                                          for i in ids),
                "flagship_hint_ids": [i for i in ids if any(
                    h in i.lower() for h in FLAGSHIP_HINTS)]}
    except urllib.error.HTTPError as e:
        return {"route": route, "reachable": False,
                "typed_error": f"HTTP {e.code} "
                               f"({(e.reason or '')[:80]})",
                "latency_s": round(time.time() - t0, 2)}
    except Exception as e:  # noqa: BLE001 — typed, Art. 15 class
        return {"route": route, "reachable": False,
                "typed_error": f"{type(e).__name__}: {str(e)[:120]}",
                "latency_s": round(time.time() - t0, 2)}


def census() -> dict:
    alts = ROUTE_REGISTRY["alternates"]
    ua_by_route = {"xkiro": BROWSER_UA, "agnes":
                   "agnes-route-adapter/1.0"}
    key_by_route = {"xkiro": "XKIRO_API_KEY",
                    "agnes": "AGNES_API_KEY"}
    results = []
    for alt in alts:
        name = alt["name"]
        key = resolve_vault_key(key_by_route[name])
        if key is None:
            results.append({"route": name, "reachable": False,
                            "typed_error": "vault_key_absent "
                                           "(owner-side custody)"})
            continue
        results.append(roster(alt["base_url"], key,
                              ua_by_route[name], name))
    return results


def build_proposal(census_rows: list) -> dict:
    return {
        "record": "R64_MODEL_REREGISTRATION_PROPOSAL/1.0.0",
        "session": "builder-r64s2",
        "claim": "c-0088",
        "owner_directive": (
            "if zai doesnt work use xiro or agnes; the provider "
            "should not be blocking us; glm 4 too low level a model "
            "to use; retire it"),
        "directive_analysis": {
            "failover_machinery_already_exists": (
                "ROUTE_REGISTRY (discovery_fabric/engine/"
                "route_adapter.py) carries two alternates "
                "c-0078-qualified end-to-end and R58 custody-probed: "
                "xkiro (api.xkiro.com, browser-UA transport contract) "
                "and agnes (apihub.agnes-ai.com, reasoning-first "
                "budgeting). Both vault keys are present. The census "
                "below re-verifies reachability + rosters today"),
            "failover_cannot_serve_the_registered_route": (
                "typed in the registry: xkiro carries NO glm family "
                "('alternate family, never the registered id') and "
                "the served==registered attestation is per-call "
                "against the registered id (R36: a silent model swap "
                "is forbidden). Alternates therefore cannot back the "
                "v9 one-shot or any registered-route work — using "
                "them there would fail the attestation BY DESIGN, "
                "not by accident"),
            "model_retirement_is_a_registration_act": (
                "R36 (the auditor's registration ruling) corrected "
                "the generator id to the exact servable id glm-4-plus "
                "after zai-org/GLM-5.3 proved servable on zero "
                "reachable paths. Retiring glm-4-plus = a NEW "
                "registration ruling superseding R36, an amended "
                "preregistration (MANDATORY_RUN_ARTIFACTS[1] pins "
                "'30/30 served_model==registered glm-4-plus'), a "
                "conscious re-freeze, and THEN the claim+run chain"),
        },
        "census": census_rows,
        "candidate_models_for_re_registration": [
            {"route": r.get("route"),
             "candidates": r.get("flagship_hint_ids", []),
             "caveat": ("naming-inference only (id conventions); the "
                        "stronger-than-glm-4 judgment is the owner's; "
                        "reachability of the chosen id must be "
                        "probed before registration (R36 lesson: "
                        "registration without a reachable path is "
                        "falsified)")}
            for r in census_rows if r.get("reachable")],
        "freeze_impact_manifest": {
            "scripts/r40_machine_v77.py:84": (
                "V77_REQUEST_MODEL = \"glm-4-plus\" — the frozen "
                "loop's registered-id constant (frozen file)"),
            "scripts/r60_v9_one_shot.py:580": (
                "assert m.V77_REQUEST_MODEL == \"glm-4-plus\" — the "
                "frozen instrument's byte-reuse check (frozen file)"),
            "eval/r64_v9_preflight.json": (
                "the freeze byte-baselines for both files (re-record "
                "in the same re-freeze commit)"),
            "tests/test_r64_v9_preflight.py": (
                "the guard tests asserting the constants (update in "
                "the same commit — the guards exist to force the "
                "act to be conscious)"),
        },
        "prereg_amendment_required": (
            "audit/holdout_v9/PREREGISTRATION.json is auditor-owned "
            "(Art. 28): MANDATORY_RUN_ARTIFACTS[1] pins the "
            "glm-4-plus attestation by name — the builder cannot "
            "amend it; the amendment must precede c-0082"),
        "gated_execution_chain": [
            "1. owner names the target model (or ratifies a census "
            "candidate); reachability of that exact id is probed "
            "(R36 lesson)",
            "2. auditor AM: re-registration ruling superseding R36 "
            "+ prereg amendment naming the new registered id",
            "3. builder conscious re-freeze (one commit: the two "
            "frozen lines + baselines + guards; CI red otherwise by "
            "design)",
            "4. c-0082 claim (holdout-v9-generation) after the "
            "adoption verdict, per Finding 2 sequencing",
            "5. the frozen v9 one-shot run against the new "
            "registration",
        ],
        "not_done_here": (
            "NO constant flipped, NO freeze touched, NO z-ai probe; "
            "the failover lanes stay qualified-but-non-registered "
            "until the re-registration lands"),
    }


if __name__ == "__main__":
    rows = census()
    out = {"record": "R64_PROVIDER_CENSUS/1.0.0",
           "session": "builder-r64s2",
           "claim": "c-0088",
           "zero_zai_probes": True,
           "method": "GET /models per qualified alternate; keys "
                     "resolved by name, never persisted",
           "routes": rows}
    CENSUS_OUT.write_text(json.dumps(out, indent=1,
                                     ensure_ascii=False) + "\n",
                          encoding="utf-8")
    PROPOSAL_OUT.write_text(json.dumps(build_proposal(rows), indent=1,
                                       ensure_ascii=False) + "\n",
                            encoding="utf-8")
    for r in rows:
        if r.get("reachable"):
            print(f"{r['route']}: reachable, roster_n={r['roster_n']}, "
                  f"glm_family={r['glm_family_present']}, "
                  f"flagship_hints={len(r['flagship_hint_ids'])}")
        else:
            print(f"{r['route']}: UNREACHABLE — "
                  f"{r.get('typed_error')}")
    ok = any(r.get("reachable") for r in rows)
    print("census:", "at least one alternate live" if ok
          else "NO alternate reachable (typed)")
