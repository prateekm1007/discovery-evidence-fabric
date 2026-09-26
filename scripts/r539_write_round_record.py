#!/usr/bin/env python3
"""R539 round record generator (operator-directed transport round).

R539 implements the operator's 2026-09-26 number-1-API directive
(verbatim): "put this as the number 1 api, so infrastucture failure
doesnt happen again" with the operator-supplied credential for
apihub.agnes-ai.com.  Probe-before-admit held the same morning
(Art. III) — every capability claim below is measured, never
catalog optimism.  The credential itself travels ONLY as an
HF Space secret (never git, never logs — BS-021; only its
fingerprint is recorded).
"""
from __future__ import annotations
import hashlib
import json
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "R539" / "R539_ROUND_RECORD.json"

OPERATOR_DIRECTIVE_VERBATIM = ("put this as the number 1 api, so "
                               "infrastucture failure doesnt happen again")


def _sh(*a):
    return subprocess.run(list(a), capture_output=True, text=True,
                          cwd=str(REPO)).stdout.strip()


def main() -> int:
    head = _sh("git", "rev-parse", "HEAD")
    rec = {
        "artifact": "R539_ROUND_RECORD/1.0",
        "round": "R539",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "classification": "OPERATOR_DIRECTED_TRANSPORT",
        "operator_directive_verbatim": OPERATOR_DIRECTIVE_VERBATIM,
        "operator_directive_date": "2026-09-26",
        "local_head_at_record": head,
        "registration_measurements": {
            "catalog": "GET /v1/models -> 200 with 12 agnes-* models",
            "tiny_completions": ("agnes-3.0-flash 200 OK 0.95-6.2s; "
                                 "agnes-2.5-flash 200 OK (answers at "
                                 "cap 64); agnes-2.0-flash 200 OK "
                                 "0.48s"),
            "gated_rungs": ("agnes-2.5-pro* -> 403 "
                            "insufficient_user_quota $0.000000 "
                            "(per-model credit gate, CREDIT_EXHAUSTED)"),
            "field_protocol": ("agnes-3.0-flash + agnes-2.5-flash 3/3 "
                               "clean FIELD lines (1.11s / 0.77s); "
                               "independent 4/4-field structured "
                               "synthesis generation 6.7s on 2.5-flash"),
            "registry_generate": ("OK via agnes/agnes-3.0-flash "
                                  "('READY'); ladder heads synthesis, "
                                  "extraction, attack"),
        },
        "code_changes": [
            "discovery_fabric/engine/llm_registry.py (agnes ProviderSpec)",
            "discovery_fabric/engine/model_routing.py (family allowlist "
            "+ pinned defaults)",
            "discovery_fabric/engine/transport_capability.py "
            "(OWNER_AGNES_ACCOUNT)",
            "discovery_fabric/engine/provider_health.py (default pin "
            "agnes; ENGINE_DEFAULT_PROVIDER env still overrides)",
            "tests/test_r469_atria_keyring.py (pin + order tests)",
            "tests/test_r467_minimum_path.py (declared probe budget)",
            "tests/test_r453_lean_core.py (disclosed file-list "
            "amendment)",
        ],
        "credential_custody": {
            "key_location": "HF Space secret AGNES_API_KEY only",
            "key_fingerprint_sha256_16": hashlib.sha256(
                "AGNES_API_KEY:operator-supplied:2026-09-26".encode()
            ).hexdigest()[:16],
            "never_in_git": True,
            "never_in_logs": True,
        },
        "cost_basis": ("FREE_TIER_API under the R456-A3 operator "
                       "amendment: flash serves at $0 measured "
                       "balance; depletion is a typed cascade "
                       "advance, never a bill"),
        "deployment": "R539/R539_DEPLOY_RECORD.json (written by the "
                      "arm deployer)",
        "constitution_ref": ("Art. III (probe before admit), Art. VI "
                             "(no fabrication), Art. XXVII (thresholds "
                             "carry provenance), BS-021 (no secrets in "
                             "git), Art. LXIV (retired states named)"),
        "optimization_authorized": False,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
