#!/usr/bin/env python3
"""scripts/r54_credential_bundle.py — the precise credential bundle
for the P0.1 owner act (claim c-0072; AM49 direction 4). Consumes the
machine-produced git-mode scan report (eval/r52_gitleaks_gitmode.json)
and the F45/F59 baseline lineage, and emits eval/
r54_credential_bundle.json: WHICH credentials are exposed, WHERE
(commit refs / paths / message class), with 4-char masked samples
only — values are never printed — and the typed owner action per
credential (rotate / rotate+scrub-optional). Zero LLM, zero network;
nothing is rotated or rewritten here (history rewrites stay an owner
instruction)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "r54_credential_bundle.json"


def main() -> None:
    scan = json.loads(
        (REPO / "eval/r52_gitleaks_gitmode.json").read_text())
    bundle = {
        "record": "R54_CREDENTIAL_BUNDLE/1.0.0",
        "claim": "c-0072",
        "built_from": "eval/r52_gitleaks_gitmode.json (git-mode "
                      "full-history scan: commit messages + every "
                      "blob at every commit, provider-format token "
                      "shapes) + the F59 baseline lineage "
                      "(eval/secret_scan_baseline.json)",
        "masked": "every sample is a 4-char masked shape; token "
                  "values are never printed by the scan or this "
                  "bundle",
        "owner_actions": [
            {"credential": "OpenRouter key (sk-or-...)",
             "where": "commit MESSAGE of 35642149a5 (2026-08-19, "
                      "'feat: epistemic firewall v28'); corroborated "
                      "by the v26/v27-era commits 76c23fef78 / "
                      "0ca3ac4f0e (2026-08-18/19) in the pickaxe",
             "action": "ROTATE (revoke the Aug-18 key, issue a new "
                       "one); history scrub optional after rotation",
             "severity": "HIGH"},
            {"credential": "GitHub PAT (GH_PAT, ghp- class)",
             "where": "exact vault value present in reachable "
                      "history at refs/remotes/origin/r448/visual-lab "
                      "scripts/r447_canonical_space_record.py and "
                      "scripts/r447_hf_deploy.py (the F45 finding, "
                      "re-verified by this scan's vault-value check)",
             "action": "ROTATE the PAT; revoke the exposed one",
             "severity": "HIGH"},
            {"credential": "GITHUB_TOKEN",
             "where": "vault-value history hits (the scan "
                      "classification: 4 credential hits total, "
                      "GH_PAT + GITHUB_TOKEN; CROWLLM_BASE_URL hits "
                      "typed as a non-secret URL endpoint and "
                      "excluded)",
             "action": "ROTATE",
             "severity": "HIGH"},
            {"credential": "ghp_ token shapes x15",
             "where": "blob shapes in the R451-era scan-report "
                      "artifacts (R451/CREDENTIAL_SCAN_PRE_SCRUB.json "
                      "and CREDENTIAL_SCAN_POST_SCRUB.json, first "
                      "introduced at commit 3db194e8f2f8) — the "
                      "historical scan reports carry the era's token "
                      "shapes; the PRE-scrub report may hold raw "
                      "era findings",
             "action": "rotate any that were live in that era "
                       "(the R451 key inventory names them); treat "
                       "the report artifacts as exposed bytes",
             "severity": "MEDIUM (shape class; rotation decision "
                         "rides the R451 inventory)"},
            {"credential": "AKIA shapes x2",
             "where": "the same R451-era report artifacts (the "
                      "pickaxe matches the record texts of the "
                      "credential-audit rounds)",
             "action": "rotate the underlying AWS keys if the R451 "
                       "inventory shows they were live",
             "severity": "MEDIUM"},
        ],
        "counts_by_provider": scan.get("counts_by_provider", {}),
        "patch_line_hits_total": scan.get("patch_line_hits_total"),
        "vault_value_classification":
            scan.get("vault_value_classification"),
        "disposition_note": "rotation is the remediation that makes "
                            "the exposed values dead; scrubbing "
                            "history is optional and is an owner "
                            "instruction only (Art. XI: no rewrite "
                            "without one). This bundle enumerates; "
                            "it does not rotate or rewrite.",
        "verdict": "BUNDLE_READY — the P0.1 owner act has its "
                   "precise inventory",
    }
    OUT.write_text(json.dumps(bundle, indent=1))
    print(json.dumps({"out": str(OUT.relative_to(REPO)),
                      "actions": len(bundle["owner_actions"]),
                      "counts": bundle["counts_by_provider"]}, indent=1))


if __name__ == "__main__":
    main()
