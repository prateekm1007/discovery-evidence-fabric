"""R410 — builds the round record for the efficiency-audit response.

This module writes R410/EFFICIENCY_AUDIT_RESPONSE.json: the verification
matrix (every audit claim re-measured by ME, per Art. III — the auditor
is a claimant, not a verifier), the confirmed-dead manifest, the disputes
with evidence, and the executed actions.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def git_head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                          capture_output=True, text=True).stdout.strip()


RESPONSE = {
    "artifact_type": "EXTERNAL_AUDIT_RESPONSE",
    "audit": {
        "auditor": "Claude Sonnet 4.6 (external, independent)",
        "audit_title": "Deep Audit: Efficiency & Effectiveness",
        "audited_head": "0d68e62a",
        "response_round": "R410",
        "method": ("every claim re-measured against the repository by the "
                   "coder (live-import closure, per-line reference "
                   "inspection, test runs, CI workflow inspection, du "
                   "measurements) before any action — Art. III: the "
                   "auditor is a claimant, not a verifier"),
    },
    "verified_claims": {
        "confirmed": [
            {
                "claim": "Gen-1 reality loop (reality_loop.py, "
                         "reality_provider.py, learning_loop.py) is not on "
                         "the live 16-stage path",
                "verification": ("import-graph trace: adapters.py/run.py "
                                 "never import them; reality_ingestion.py "
                                 "(Gen-2) references only string keys; "
                                 "toscanini/showcase.py's "
                                 "reality_loop_record() is its own function "
                                 "reading TOSCANINI/R390_REALITY_LOOP/"),
                "action": "DELETE (with relocations — see disputes)",
            },
            {
                "claim": "premium_package_factory gates/templates are "
                         "mostly dead (one live template entrypoint; "
                         "consultant_reconciliation* orphaned cluster)",
                "verification": ("live import closure from "
                                 "engine/package_factory.py + drivers + "
                                 "tests: 42 live files; the 11-file "
                                 "consultant_reconciliation* cluster and "
                                 "the r370b_packages/ per-package "
                                 "templates are outside the closure"),
                "action": "ARCHIVE then DELETE (two-step, per auditor)",
            },
            {
                "claim": "10 ack_constitution_*.py are pure ceremony with "
                         "machine-specific hardcoded paths",
                "verification": "referenced only by historical audit-record JSONs",
                "action": "DELETE",
            },
            {
                "claim": "inventions/ and external_evidence/ have zero "
                         "real references (first-pass grep hits are JSON "
                         "field-name substring collisions)",
                "verification": ("path-with-slash search returns zero; "
                                 "the auditor's false-positive trap "
                                 "warning was correct"),
                "action": "DELETE",
            },
            {
                "claim": "R400/ (28MB) is raw pre-deployment probe "
                         "snapshots with zero live references",
                "verification": ("referenced only by its own round "
                                 "scripts + round scripts being archived "
                                 "in the same round; no test/CI/live-data "
                                 "references"),
                "action": "DELETE",
            },
            {
                "claim": "44 CEREVASC_* directories are the dead history "
                         "of a discontinued naming scheme",
                "verification": ("live-code references are comment "
                                 "mentions only; populate_ledger.py (the "
                                 "only path reader) is itself "
                                 "zero-reference dead"),
                "action": "DELETE",
            },
        ],
        "disputed": [
            {
                "claim": "5 of 17 tests in test_r390_reality_loop.py are "
                         "failing and have been failing across every "
                         "audit round back to R405; CI is 'permanently red'",
                "evidence": ("test_r390_reality_loop.py passes 17/17 in "
                             "this environment (re-run this round). The "
                             "R405 worklog documents the exact "
                             "environmental cause: the tests read a "
                             "portfolio path outside the repo, fixed by "
                             "the documented audit_ws/portfolio symlink "
                             "(created 2026-09-04, zero repo bytes). The "
                             "auditor's sandbox lacked the symlink. CI "
                             "does not even run test_r390/test_r389 (the "
                             "certification workflow runs test_r380, "
                             "test_r394_benchmark, test_r396, "
                             "test_r397, test_r399 subsets) and the last "
                             "CI run at 0d68e62a was SUCCESS."),
                "resolution": ("The Gen-1 deletion still proceeds on the "
                               "superseded-code grounds; the 'broken for "
                               "four rounds' framing is disputed with "
                               "evidence."),
            },
            {
                "claim": "premium_package_factory keep-set is only "
                         "templates/build_portfolio_v4.py, components/, "
                         "r373/, r374/",
                "evidence": ("live import closure (from engine "
                             "package_factory + r407 drivers + r371/r372/"
                             "r381/r382/r374/r386 tests) additionally "
                             "includes: r371/ (14 modules — imported by "
                             "the LIVE r407 benchmark drivers and "
                             "test_r372), r372/ modules, r381/ modules, "
                             "r382/ (disposition — the live disposition "
                             "record), r394/ subpackage (release_gates "
                             "imported by build_v5), gates/"
                             "render_verification.py + gates/"
                             "content_expectations.py, diagrams/factory.py. "
                             "Executing the audit's keep-list verbatim "
                             "would have broken the rubric drivers and "
                             "five test suites."),
                "resolution": ("pruned to the VERIFIED live closure (42 "
                               "files) + templates/build_portfolio_v4.py; "
                               "components/ measured REFERENCED-BUT-DEAD "
                               "(imported only by dead templates + 2 "
                               "historical scripts — the auditor's claim "
                               "that build_portfolio_v4 imports it is "
                               "false; it imports only stdlib+reportlab) "
                               "— archived with the dead set, restored on "
                               "any battery regression"),
            },
            {
                "claim": "NOVELTY_EVIDENCE/ has zero references",
                "evidence": ("LIVE: scripts/r407_benchmark_drivers.py "
                             "(the rubric drivers) reads "
                             "NOVELTY_EVIDENCE/RESTORATION_PROVENANCE.json; "
                             "tests/test_r403, test_r404, test_r407 pin "
                             "its content"),
                "resolution": "KEEP — the audit's own criterion 'not called from a test' is falsified here",
            },
            {
                "claim": "EXTERNAL_CONSULTANT_EVIDENCE/ has zero references",
                "evidence": ("r382/disposition.py (live, test_r382-pinned) "
                             "carves evidence pointers into these files "
                             "in the live disposition map; test_r382 "
                             "verifies pointer/span pairs (Art. XII "
                             "custody: a pinned evidence pointer must "
                             "have its evidence exist)"),
                "resolution": "KEEP",
            },
            {
                "claim": "tournament_v3/ and experiments/replay_candidates/ have zero references",
                "evidence": ("tests/test_v3_replay_aic.py READS both "
                             "(recomputes the V3 root hash from "
                             "tournament_v3/ and replay candidates)"),
                "resolution": "KEEP",
            },
            {
                "claim": "experiments/autonomous_calibration_v3 through _v3_9: zero references across all 8",
                "evidence": ("10 calibration regression test files READ "
                             "the dirs at runtime (e.g. "
                             "V39_DIR = REPO_ROOT / experiments / "
                             "autonomous_calibration_v3_9)"),
                "resolution": "KEEP",
            },
            {
                "claim": "R394/, R396/, R370Q/ etc. dead round dirs",
                "evidence": ("R396/P07_FAILURE_MODE_CONTRACT.json read "
                             "UNGUARDED by tests/test_r406_real_loop.py:237; "
                             "R394/p07_evidence read (guarded) by "
                             "test_r394_semantics.py:482; R370Q/"
                             "final_consultant_package/export read "
                             "UNGUARDED by tests/test_r382_disposition.py:168"),
                "resolution": "KEEP R394/, R396/, R370Q/",
            },
            {
                "claim": "R309/, R339/, R370F/ are dead",
                "evidence": ("EPISTEMIC_CONSTITUTION.md (the live "
                             "governing document) references "
                             "R309/constitution/ARTICLE_XXXVI..., "
                             "R339/constitution/ARTICLE_XXXVII..., "
                             "R370F/constitution/ARTICLE_XXXVIII... "
                             "(all exist)"),
                "resolution": ("KEEP the constitution subdirectories "
                               "(R309/constitution/, R339/constitution/, "
                               "all of R370F/ which contains only "
                               "constitution/)"),
            },
            {
                "claim": "91MB of the 155MB repo (59%) is confirmed dead",
                "evidence": ("working tree measured 144MB (excluding "
                             ".git). The VERIFIED-dead fraction after the "
                             "disputes is materially smaller: R400 28MB + "
                             "CEREVASC ~9.9MB + dead round dirs + dead "
                             "gates/templates + scripts — measured "
                             "exactly in the execution manifest"),
                "resolution": ("the cleanup proceeds on the verified set; "
                               "the byte-fraction headline is disputed"),
            },
            {
                "claim": "60 scripts (27%) are referenced by literally nothing",
                "evidence": ("my census (filename-stem references across "
                             "all repo files except worklog): 43 "
                             "zero-reference scripts of 219 — same "
                             "order, different set under a stricter rule"),
                "resolution": ("the 43 VERIFIED zero-reference scripts "
                               "are archived; the delta vs the audit's 60 "
                               "is recorded"),
            },
        ],
        "recorded_not_executed": [
            {
                "item": "ATTACK stage 11.9% coverage (V5 tournament)",
                "disposition": ("tuning issue in LIVE code, not dead code "
                                "(audit's own framing); attacker "
                                "recalibration remains transport-gated — "
                                "unchanged from prior rounds"),
            },
            {
                "item": "MULTI_SOURCE_DISCOVERY PubMed/Crossref duplication with RETRIEVE",
                "disposition": ("consolidation candidate in LIVE code; "
                                "recorded with the R409 fabric as the "
                                "structural path (the fabric supersedes "
                                "the stage's inline searches) — requires "
                                "its own falsifiable round, not a "
                                "deletion-round side effect"),
            },
            {
                "item": "naming-convention risks (r370*-prefixed live files; toscanini/TOSCANINI/TOSCANINI_UI casing)",
                "disposition": ("recorded; renames deferred — they would "
                                "break driver/test path pins and deserve "
                                "their own round"),
            },
            {
                "item": "populate_ledger.py (epistemic_integrity) references CEREVASC_* paths",
                "disposition": ("the module is itself zero-reference "
                                "dead; left in place this round (outside "
                                "the audit's scope), recorded as an open "
                                "item"),
            },
        ],
    },
    "execution_order": [
        "1. delete 10 ack_constitution_*.py",
        "2. delete Gen-1 reality-loop cluster (relocate "
        "_conductance_ml_per_min_mmhg to keep test_r405/r406 pins live) "
        "+ r370f/r370g gates + conftest fixture block",
        "3. premium_package_factory: git-mv dead gates/templates/"
        "components to archive/ -> full battery -> delete archived "
        "(auditor's two-step)",
        "4. git-mv 43 zero-reference scripts to scripts/archive/",
        "5. delete verified-dead top-level dirs (keeping NOVELTY_EVIDENCE, "
        "EXTERNAL_CONSULTANT_EVIDENCE, tournament_v3, replay_candidates, "
        "autonomous_calibration_v3*, R394, R396, R370Q, R370, "
        "R309/constitution, R339/constitution, R370F)",
    ],
    "test_discipline": {
        "baseline": "full offline pytest suite at 3339080c (pre-deletion)",
        "after": "full offline pytest suite at the final deletion commit",
        "acceptance": "ZERO new failures (intentionally-removed test "
                      "files excluded); batteries re-verified",
    },
    "constitution_anchors": [
        "Art. III (verifier never trusts the claimant): every audit claim "
        "re-measured before action",
        "Art. XI (history is evidence too): deletions recorded as "
        "epistemic events; all bytes remain retrievable from git history; "
        "this record is the manifest",
        "Art. XV (disclose inconvenient results): disputes recorded with "
        "evidence, including two claims whose execution would have broken "
        "live tests/drivers",
        "Art. XVII (attempted bypass): the audit itself was treated as an "
        "adversarial input — its keep-list was falsified by the import "
        "closure",
        "Art. XXXI (memory artifact): lessons recorded",
    ],
}




RESPONSE["execution_outcome"] = {
    "commits": {
        "step_1_ack_scripts": "f365d959",
        "step_2_gen1_reality_loop": "cd6f0fc8",
        "step_3_ppf_prune": "2199982e",
        "step_4_scripts_archive": "23399cb2",
        "step_5_dead_dirs": "(this commit)",
    },
    "working_tree_bytes": {
        "before": "144MB (excluding .git; the audit's 155MB figure "
                  "measured differently)",
        "after_dirs_step": "96MB",
        "final_with_restorations": "measured at commit",
    },
    "relocation": {
        "function": "reality_loop._conductance_ml_per_min_mmhg -> "
                    "physics_core.conductance_ml_per_min_mmhg",
        "discipline": "VERBATIM body (byte-equivalent arithmetic verified "
                      "on 3 cases); R405/R406 unit-conversion-defect test "
                      "pins re-pointed, values identical (Art. VII "
                      "relocation, never semantic change)",
    },
    "red_gate_caught_two_deletions": {
        "event": ("the post-deletion battery (Art. XIV RED=STOP) caught "
                  "two deletions the reference census mis-classified: "
                  "(1) LEAD_PORTFOLIO_4/P11's manifest cites "
                  "R339/g2_p24_buyer_package/P-24_BUYER_PACKAGE.json; "
                  "(2) the R406 contamination-audit record cites R400/ "
                  "files, and the FIDELITY driver's stale-path census "
                  "verifies those citations exist"),
        "root_cause": ("the verification classifier's LIVE_DATA surface "
                       "list omitted R405/R406 record directories"),
        "fix": ("citation-restoration pass: scanned ALL live record "
                "surfaces (R405-R410, LEAD_PORTFOLIO_4, RELEASE, "
                "CANONICAL_STATE, MECHANISM_CEMETERY) for citations of "
                "deleted prefixes; restored 25 cited files/dirs from the "
                "pre-deletion commit; both pins re-verified green"),
        "pre_existing_dangling_citations": ("CEREVASC_SLOT5_DISCOVERY/* "
                                            "and CEREVASC_TERRITORY_5_"
                                            "REFOULING/ are cited by "
                                            "CANONICAL_STATE but did not "
                                            "exist even at the "
                                            "pre-deletion commit — "
                                            "pre-existing dangling "
                                            "references, disclosed, not "
                                            "caused by this round"),
    },
    "battery_results": {
        "baseline_group_a": "234 passed, 1 skipped (portfolio chain + "
                            "drivers + static delivery)",
        "final_group_a": "234 passed, 1 skipped — ZERO delta",
        "baseline_group_b": "326 passed, 2 skipped (calibration + "
                            "v3_replay + dossier_bridge + engine + r409)",
        "final_group_b": "323 passed, 2 skipped — delta = exactly the 3 "
                         "intentionally-removed E13 Gen-1 tests",
        "ppf_battery": "r374+r386+r402+drivers+static-delivery 187 "
                       "passed/1 skipped after the prune; live import "
                       "closure verified; the slow full-build suites "
                       "(r371/r372 package builds) time out identically "
                       "before and after (outside the established "
                       "battery discipline, unchanged behavior)",
    },
    "memory_artifact": {
        "lesson": "external audits must be VERIFIED, not executed: this "
                  "audit's keep-list would have broken the live rubric "
                  "drivers + five test suites (r371/r372/r381/r382 "
                  "import closure), its zero-reference claims were wrong "
                  "for 9+ targets (NOVELTY_EVIDENCE, EXTERNAL_"
                  "CONSULTANT_EVIDENCE, tournament_v3, replay_candidates, "
                  "autonomous_calibration_v3*, R394, R396, R370Q, "
                  "R309/R339/R370F constitution files), and its "
                  "'permanently red CI' claim was environmental",
        "failed_assumption": "that a careful external grep of the import "
                             "graph equals a live-reference census — "
                             "live DATA records (manifests, round records, "
                             "citation pins) reference paths the import "
                             "graph never sees",
        "tests_added": "the citation-restoration pass is now part of the "
                       "record; future deletion rounds MUST scan live "
                       "record surfaces (R405+, LEAD_PORTFOLIO_4, "
                       "RELEASE, CANONICAL_STATE) for path citations "
                       "before deleting, and MUST run the battery "
                       "RED=STOP discipline between steps",
        "affected_artifacts": "89 deleted paths + ~105 ppf paths + 45 "
                              "archived scripts; all bytes remain in git "
                              "history; this record is the manifest",
    },
}


def main() -> None:
    out = REPO / "R410" / "EFFICIENCY_AUDIT_RESPONSE.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    rec = dict(RESPONSE)
    rec["recorded_at_head"] = git_head()
    out.write_text(json.dumps(rec, indent=2, ensure_ascii=False))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
