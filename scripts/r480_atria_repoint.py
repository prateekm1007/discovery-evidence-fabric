#!/usr/bin/env python3
"""R480 — the Space repoint: ZAI -> atria (the operator's credited
provider directive), executed as variables + secrets + restart.

NO REBUILD: the ZAI_BASE_URL re-point is the R391 operator override
(gateway.py / llm_registry.url_for_call), ZAI_MODEL overrides per call
(llm_registry.model_for_call), and the keys are secrets — all three
are runtime surface, so identity stays fbc73b8 and the docker image is
untouched (restart only).

Wired this round (probe-before-wire passed: R480/ATRIA_LEDGER_LINE.json
LEDGER_LINE_GREEN):
  variables  ZAI_BASE_URL = https://api.atria-asi.ai/v1/chat/completions
             ZAI_MODEL    = Atria-Dawn-Preview  (the catalog's SOLE
             model — re-measured this round, 200)
  secrets    ZAI_API_KEY       = atria key 1 (the zai slot rides atria)
             ATRIA_API_KEY.._15 = the operator's re-supplied ring, all
             fifteen names on the surface (the R472 practice: the ring
             is the selection authority; slot 8 carries inertly — its
             measured INVALID verdict stands until re-measured CLEAR)

Left standing (write-only surface, values unknown, standing valid):
GITHUB_TOKEN (rotated R479), PORTFOLIO_COMMIT, the 8 router keys.

BS-021: this script records FINGERPRINTS only, never key values.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "R480" / "SPACE_REPOINT_RECORD.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def fingerprint(value: str) -> str:
    return ("fp_" + hashlib.sha256(value.encode()).hexdigest()[:12]
            + f"_len{len(value)}")


def load_vault() -> dict:
    vault = {}
    p = Path("/home/z/my-project/.secrets.env")
    for line in p.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            vault[k.strip()] = v.strip()
    return vault


def main() -> int:
    from huggingface_hub import HfApi
    vault = load_vault()
    hf_token = vault.get("HF_TOKEN", "")
    space = "prateekm1/toscanini-prod-validation"
    api = HfApi(token=hf_token)

    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO),
                            capture_output=True, text=True).stdout.strip()
    probe = json.loads((REPO / "R480" / "ATRIA_LEDGER_LINE.json").read_text())
    if probe.get("outcome") != "LEDGER_LINE_GREEN":
        print("FATAL: probe-before-wire did not answer GREEN — refusing "
              "to rewire on an unmeasured transport")
        return 2

    ring = {n: vault[n] for n in
            (["ATRIA_API_KEY"] + [f"ATRIA_API_KEY_{i}" for i in range(2, 16)])
            if vault.get(n)}
    if len(ring) != 15:
        print(f"FATAL: expected 15 ring keys in the vault, got {len(ring)}")
        return 2

    print("[r480-repoint] variables: ZAI_BASE_URL -> api.atria-asi.ai, "
          "ZAI_MODEL -> Atria-Dawn-Preview")
    api.add_space_variable(
        repo_id=space, key="ZAI_BASE_URL",
        value="https://api.atria-asi.ai/v1/chat/completions")
    api.add_space_variable(repo_id=space, key="ZAI_MODEL",
                           value="Atria-Dawn-Preview")

    wired = []
    print("[r480-repoint] secrets: ZAI_API_KEY = atria key 1; the "
          "15-name atria ring (slot 8 inert by its measured verdict)")
    api.add_space_secret(repo_id=space, key="ZAI_API_KEY",
                         value=ring["ATRIA_API_KEY"])
    wired.append("ZAI_API_KEY")
    for name, val in ring.items():
        api.add_space_secret(repo_id=space, key=name, value=val)
        wired.append(name)

    print("[r480-repoint] restarting the Space (variables + secrets "
          "apply on restart; NO rebuild — identity stays at "
          f"{commit[:12]})")
    api.restart_space(repo_id=space)

    rec = {
        "round": "R480",
        "space": space,
        "action": "ZAI re-pointed to atria (the operator's credited "
                  "provider directive) + the atria ring re-wired from "
                  "the operator's re-supplied set",
        "identity_unchanged": commit,
        "probe_before_wire": {"record": "R480/ATRIA_LEDGER_LINE.json",
                              "outcome": probe["outcome"]},
        "variables_set": {"ZAI_BASE_URL":
                          "https://api.atria-asi.ai/v1/chat/completions",
                          "ZAI_MODEL": "Atria-Dawn-Preview"},
        "secrets_wired": wired,
        "secrets_fingerprints": {
            "ZAI_API_KEY": fingerprint(ring["ATRIA_API_KEY"]),
            "ring_size": len(ring),
        },
        "left_standing": ["GITHUB_TOKEN (rotated R479)",
                          "PORTFOLIO_COMMIT",
                          "UNOROUTER_API_KEY", "XKIRO_API_KEY",
                          "APINEX_API_KEY", "BAI_API_KEY",
                          "BYNARA_API_KEY", "TOKENHARBOR_API_KEY",
                          "AEROLINK_API_KEY", "ATRIA_API_KEY (re-wired "
                          "this round; listed standing names are the "
                          "other 8 routers)"],
        "note_slot_8": ("ATRIA_API_KEY_8 carried inertly per the R472 "
                        "measured INVALID verdict (deterministic 401 "
                        "x3, flapping disclosed); the ring's selection "
                        "authority excludes it until a future probe "
                        "measures CLEAR"),
        "bs_021": "fingerprints only, never key values",
        "reviewer_provenance": "AI_REVIEW",
        "created_at_utc": utc_now(),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1))
    print(f"[r480-repoint] record -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
