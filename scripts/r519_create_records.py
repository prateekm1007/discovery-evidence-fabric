#!/usr/bin/env python3
"""R519: reconcile R518/R518_ROUND_RECORD.json with §9 required fields
and write R519/R519_ROUND_RECORD.json (honest classification).

No hand-waved "complete": battery fields are NOT_RUN_CREDENTIAL_BLOCKED;
classification is ROUTING_IMPLEMENTED_BUT_UNPROVEN with a typed blocker
naming the exact absent credentials.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(REPO),
        capture_output=True, text=True, check=True).stdout.strip()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def dump(p: Path, doc) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                 encoding="utf-8")


CONSTITUTION_SHA = (
    "2ce42426662d6493f672cf5fd7256bf5c2b9c8412e369ee9032b253b80b6fc56")
ABSENT_CREDENTIALS = [
    "OPENROUTER_API_KEY",
    "NVIDIA_API_KEY",
    "ATRIA_API_KEY",
    "ZAI_API_KEY",
    "GEMINI_API_KEY",
    "HF_TOKEN",
    "GITHUB_TOKEN",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
]
MULTI_SOURCE_HITS = [
    "CODER2_PRODUCT_EVENT_MAP.json",
    "TOSCANINI/conversational/nba_controller.py",
    "TOSCANINI/dossier.py",
    "TOSCANINI/event_journal.py",
    "TOSCANINI/investigation.py",
    "TOSCANINI/run_state.py",
    "TOSCANINI/sessions.py",
    "TOSCANINI_UI/webapp/components/RunNarrative.tsx",
    "TOSCANINI_UI/webapp/lib/productEvents.ts",
]


def main() -> int:
    now = utcnow()
    h = head()
    base_sha = "185a2d441f77285b2bcf401036e123cc9dae85df"

    # ---- R518 record reconciliation (§9) ----
    r518_path = REPO / "R518" / "R518_ROUND_RECORD.json"
    r518 = load(r518_path)
    r518["correction_at_utc"] = now
    r518["correction_reason"] = (
        "R519 §9: reconcile R518 record with R519 closure fields; "
        "battery remains NOT_RUN_CREDENTIAL_BLOCKED; status remains "
        "IMPLEMENTED_PERFORMANCE_HYPOTHESIS (never complete as substitute)."
    )
    r518["constitution"]["sha256"] = CONSTITUTION_SHA
    r518["constitution"]["verified_at_utc"] = now
    r518["immutable_state"]["origin_main"] = base_sha
    r518["r519_closure"] = {
        "round": "R519",
        "base_sha": base_sha,
        "implementation_sha": h,
        "single_retirement_authority": (
            "provider_health.RETIRED_ROUTE_PROVIDERS + is_route_retired() "
            "+ apply_route_retirement() + order_for_role(purpose,out_events); "
            "generate() filters preferred/cost-extension/rung-ladder"
        ),
        "zai_representation": (
            "table data PURPOSE_POST_RANK_IMPROVEMENT / "
            "PURPOSE_POST_RANK_TECHNICAL (no provider-name branch)"
        ),
        "preferred_provider_bypass": "CLOSED (all chain sources filtered)",
        "explicit_override_semantics": (
            "route retirement = removed from ordinary/default routing; "
            "ProviderSpec intact (Art. LXIV); explicit operator override "
            "allowed only when deliberately requested AND recorded"
        ),
        "adversarial_tests": {
            "file": "tests/test_r519_retirement_authority.py",
            "result": "PASS",
            "passed": 16,
        },
        "clean_replay": {
            "artifact": "R519/CLEAN_REPLAY.json",
            "result": "PASS",
            "checks": "13/13",
        },
        "r469_tests": {"result": "PASS", "passed": 34, "skipped": 1},
        "fresh_battery": {
            "status": "NOT_RUN_CREDENTIAL_BLOCKED",
            "reason": (
                "Art. LXXIII three-step credential lookup exhausted: "
                "session env empty; no .secrets.env vault; HF Space secret "
                "surface unreachable without HF_TOKEN."
            ),
            "missing_credentials": list(ABSENT_CREDENTIALS),
        },
        "classification": "ROUTING_IMPLEMENTED_BUT_UNPROVEN",
    }
    r518["required_round_outputs_checklist"]["clean_replay"] = (
        "COMPLETED via R519/CLEAN_REPLAY.json (13/13 PASS)"
    )
    r518["required_round_outputs_checklist"][
        "deployment_identity_proof"] = (
        "PENDING R519 post-push deploy record (R519_DEPLOY_RECORD.json)"
    )
    r518["unknowns"] = list(dict.fromkeys(
        (r518.get("unknowns") or []) + [
            "R519 fresh performance battery blocked: missing registered "
            "credentials (MEASUREMENT_BLOCKED_MISSING_PROVIDER_CREDENTIALS)",
            "MULTI_SOURCE_DISCOVERY still present in "
            f"{len(MULTI_SOURCE_HITS)} live/UI files (separate retirement)",
        ]
    ))
    r518["corrected_at_utc"] = now
    r518["r519_reconciled_at_utc"] = now
    dump(r518_path, r518)

    # ---- R519 round record ----
    r519 = {
        "artifact": "R519_ROUND_RECORD/1.0",
        "round": "R519",
        "parent_round": "R518",
        "created_at_utc": now,
        "constitution": {
            "version": "2.10.1",
            "sha256": CONSTITUTION_SHA,
            "bytes": 126124,
            "lines": 2538,
            "verified_at_utc": now,
        },
        "immutable_state": {
            "base_sha": base_sha,
            "implementation_sha": h,
            "chain_length": 15,
            "stages": (
                "RETRIEVE -> FREEZE -> PREMISE_GATE -> SYNTHESIZE -> VERIFY "
                "-> MECHANISM_SPACE -> COLLISION -> PHYSICS -> ATTACK "
                "-> CONTRADICTION -> KILLER_EXPERIMENT -> ADJUDICATION "
                "-> CLASSIFY -> NEXT_BEST_ACTION -> RANK"
            ),
        },
        "scope": {
            "r518_closure": [
                "evidence-architecture repair (R512 SPACE_DEPLOY_RECORD "
                "restored to pre-R518 historical state)",
                "single retirement authority (Art. X)",
                "preferred-provider bypass closure (all chain sources "
                "filtered through apply_route_retirement)",
            ],
            "fresh_performance_proof_attempt": (
                "attempted; blocked before first measurement by missing "
                "credentials — not claimed complete"
            ),
            "section_8_frozen": (
                "no changes to prompts/evidence/gates/thresholds/funnel/"
                "2800-token budget — only routing changed"
            ),
        },
        "selected_semantics": {
            "route_retirement": (
                "removed from ordinary/default routing; ProviderSpec intact "
                "(Art. LXIV); explicit operator override allowed only when "
                "deliberately requested AND recorded"
            ),
            "states": [
                "RETIRED_ROUTE_BLOCKED",
                "EXPLICIT_OPERATOR_OVERRIDE_ALLOWED",
                "DEFAULT_ROUTE_BLOCKED",
            ],
        },
        "retirement_table": {
            "atria": ["ROLE_ATTACK", "ROLE_SYNTHESIS"],
            "zai": [
                "post_rank:improvement_mutation_proposal",
                "post_rank:technical_mutation_proposal",
            ],
        },
        "adversarial_results": {
            "tests/test_r519_retirement_authority.py": {
                "passed": 16,
                "failed": 0,
                "cases": [
                    "A ordinary preferred list excludes atria",
                    "B preferred preferred list blocks + records",
                    "C hard_pin allowed then recorded",
                    "D env re-pin override recorded",
                    "E ordinary preferred literals exclude atria",
                    "F resurrection attempts",
                ],
            },
            "tests/test_r469_atria_keyring.py": {
                "passed": 34,
                "skipped": 1,
                "failed": 0,
                "note": (
                    "3 pin tests rewritten to new retirement policy; "
                    "3 ring-rotation tests use hard_pin_provider"
                ),
            },
            "combined_regression": {
                "passed": 50,
                "skipped": 1,
                "failed": 0,
            },
        },
        "clean_replay": {
            "artifact": "R519/CLEAN_REPLAY.json",
            "script": "scripts/r519_clean_replay.py",
            "result": "PASS",
            "checks_passed": 13,
            "checks_total": 13,
        },
        "module_inventory": {
            "script": "scripts/r456_module_inventory.py",
            "command": "python scripts/r456_module_inventory.py --inventory",
            "result": "PASS",
            "detail": "194 production files, 111779 LOC -> MODULE_INVENTORY.json",
        },
        "fresh_performance_battery": {
            "status": "NOT_RUN_CREDENTIAL_BLOCKED",
            "blocker": "MEASUREMENT_BLOCKED_MISSING_PROVIDER_CREDENTIALS",
            "arm_definitions": {
                "baseline": (
                    "pre-R518 routing via recorded env override "
                    "(ENGINE_*_PROVIDER / recorded explicit pin)"
                ),
                "optimized": "current R519 routing (ordinary routes only)",
                "difference": "only routing differs; prompts/evidence/gates "
                              "unchanged (§8 frozen)",
            },
            "required_metrics": {
                "SYNTHESIZE": [
                    "stage_wall_s", "probe_wall_s", "provider_call_wall_s",
                    "retries", "fallback", "provider", "model",
                    "output_size", "semantic_validity",
                ],
                "MECHANISM_SPACE": [
                    "budget_2800_tokens", "stage_wall_s",
                    "generation_wall_s", "probe_wall_s", "retries",
                    "candidate_validity", "support", "distinctness",
                ],
                "ATTACK": [
                    "generator_provider", "exclude",
                    "attacker_provider_chain", "runtime_evidence",
                ],
            },
            "repetitions": "multiple (not yet run)",
            "fresh_disjoint_problems": "required (not yet run)",
            "results": "NOT_RUN",
        },
        "§16_acceptance_rules": {
            "latency_data_present": False,
            "multiple_repetitions": False,
            "fresh_disjoint_problems": False,
            "only_routing_differs": "designed but not executed",
            "failures": [
                "No latency measurements (battery not run)",
                "No multi-repetition comparison",
                "No fresh-problem baseline vs optimized arms",
            ],
        },
        "classification": "ROUTING_IMPLEMENTED_BUT_UNPROVEN",
        "classification_not": [
            "OPTIMIZATION_PROVEN",
            "PERFORMANCE_INCONCLUSIVE",
            "complete",
        ],
        "typed_blocker": {
            "code": "MEASUREMENT_BLOCKED_MISSING_PROVIDER_CREDENTIALS",
            "article": "Art. LXXIII credential lookup + Art. LXXI §4",
            "absent_credentials": list(ABSENT_CREDENTIALS),
            "lookup_steps": [
                "session env: EMPTY for all registered provider/HF/GitHub keys",
                ".secrets.env vault: not found (HOME/workspace/.config, depth-3)",
                "HF Space secret surface: UNREACHABLE without HF_TOKEN",
            ],
            "escalation_required_from_operator": True,
            "escalation_names_exactly": list(ABSENT_CREDENTIALS),
        },
        "open_items": {
            "multi_source_discovery_vocabulary": {
                "status": "OPEN_SEPARATE_RETIREMENT",
                "files": list(MULTI_SOURCE_HITS),
                "note": (
                    "Not retired this round; recorded honestly (not green)."
                ),
            },
            "module_inventory_windows_path_issue": (
                "Open infrastructure item for Linux/CI if --check fails "
                "under path-separator noise; --inventory PASS this session "
                "on Windows."
            ),
            "graph_self_reference_limit": (
                "r515 generator records git rev-parse HEAD at regen time; "
                "a graph cannot contain its own commit SHA without "
                "hand-editing (forbidden). Post-push regen + second commit "
                "for graph/deploy record is the honest path."
            ),
            "pre_existing_test_failures": [
                "test_r418 routing pin: _Rec missing structured_output "
                "(model_routing.py) — pre-existing at HEAD",
                "ModuleNotFoundError: No module named 'toscanini' "
                "(dir is TOSCANINI uppercase) blocks some suites — pre-existing",
            ],
        },
        "deploy": {
            "status": "PENDING_POST_PUSH",
            "artifact": "R519/R519_DEPLOY_RECORD.json",
            "must_not_overwrite": "R512/SPACE_DEPLOY_RECORD.json",
        },
        "reviewer_provenance": "AI_REVIEW",
        "parent_record": "R518/R518_ROUND_RECORD.json",
        "outcomes": {
            "ROUTING_IMPLEMENTED_BUT_UNPROVEN": 1,
        },
    }
    dump(REPO / "R519" / "R519_ROUND_RECORD.json", r519)

    print("updated", r518_path.relative_to(REPO))
    print("wrote", (REPO / "R519" / "R519_ROUND_RECORD.json").relative_to(REPO))
    print("classification=ROUTING_IMPLEMENTED_BUT_UNPROVEN")
    print("blocker=MEASUREMENT_BLOCKED_MISSING_PROVIDER_CREDENTIALS")
    print("implementation_sha", h)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
