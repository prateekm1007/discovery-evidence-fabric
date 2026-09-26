import json
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "R537" / "R537_ROUND_RECORD.json"


def _sh(*a):
    return subprocess.run(list(a), capture_output=True, text=True,
                          cwd=str(REPO)).stdout.strip()


def main() -> int:
    head = _sh("git", "rev-parse", "HEAD")
    origin = _sh("git", "rev-parse", "origin/main")
    rec = {
        "artifact": "R537_ROUND_RECORD/1.0",
        "round": "R537",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "classification":
            "CORRECTNESS_AND_CONFORMANCE__LIVE_CHANNEL_PENDING",
        "audit_driven": True,
        "local_head": head,
        "origin_main": origin,
        "hermetic_deliverables": {
            "A_dependency_contract_proof":
                "R537/R537_DEPENDENCY_CONTRACT_PROOF.json (the "
                "repaired 4-case expected-vs-observed matrix; a "
                "missing stage-log entry is NOT_REACHED, never "
                "execution; every (dependency,case,consumer) triple "
                "asserted against its expected set; the cascade-vs-"
                "declaration-only two-authority divergence "
                "documented, not refactored)",
            "B_cemetery_fail_closed":
                "R537/R537_CEMETERY_FAIL_CLOSED_PROOF.json + "
                "tests/test_r537_cemetery_fail_closed.py (the P0: a "
                "forced cemetery exception -> UNRESOLVED / "
                "infrastructure failure -> no favorable cemetery PASS "
                "-> no ESTABLISHED_PROVISIONALLY -> no discovery "
                "credit, proven through the real EngineRun -> "
                "ADJUDICATION -> _CemeterySubCheck -> "
                "mechanism_cemetery path with the durable "
                "adjudication record inspected)",
            "C_domain_identity_battery":
                "R537/R537_CEMETERY_DOMAIN_IDENTITY_BATTERY.json "
                "(the 12 required adversarial cases: same-domain "
                "block, cross-domain no-block, generic-only no-"
                "block, structural signal, lexical signal, substring "
                "collision ('flow' inside 'workflow'), plural/"
                "inflection collision, candidate/problem vocab "
                "overlap, no mechanism graph, malformed graph, "
                "generic-only entry downgrade, the [:24] cutoff "
                "probe).  All cases closed after the hardenings: "
                "token-boundary lexical matching, independent "
                "candidate/problem vocabularies, alternatives-not-"
                "corroboration recorded, the [:24] alphabetic "
                "cutoff removed from the matching set, no-identity "
                "decisions durably returned",
            "D_real_path_controls":
                "tests/test_r537_cemetery_real_path.py (the real "
                "EngineRun -> ADJUDICATION -> _CemeterySubCheck -> "
                "mechanism_cemetery caller driven with a same-domain "
                "hard-block control + a cross-domain no-block-on-"
                "generic-vocabulary control; the durable adjudication "
                "record inspected, not just the immediate return)",
            "E_freeze_dataflow":
                "R537/R537_FREEZE_DATAFLOW_PROOF.json + the R537 "
                "§E lineage instrumentation in adapters.py (FREEZE "
                "verified-custody IDs/hashes; SYNTHESIZE + VERIFY "
                "input sets + consumed-verified-custody flags) + a "
                "live real-conductor machine-join; the exact-span "
                "custody semantics inspected (a hash-bound "
                "observation, not a substring-identity check).  The "
                "canonical downstream authority is env.evidence "
                "(the retrieval pool); FREEZE is a parallel custody "
                "observation, not the input — the boundary is "
                "recorded as the dataflow defect, no behavior "
                "changed to make it match",
            "F_artifact_namespace":
                "R537/R537_ARTIFACT_NAMESPACE_PROOF.json + "
                "scripts/validate_artifact_namespace.py wired into "
                "the pre-commit hook (scripts/pre_commit_"
                "artifact_namespace.py), both CI workflows "
                "(epistemic_lightweight + epistemic_certification), "
                "and this round-record generator.  No human "
                "reviewer is the enforcement mechanism",
            "G_production_identity":
                "R537/R537_PRODUCTION_IDENTITY_PROOF.json (a fresh "
                "live probe of the deployed Space: /api/version + "
                "/api/health, drift GREEN, tamper false; the Space "
                "currently serves the R534 build eaeba79d8 — R536/R537 "
                "source state is NOT yet deployment-proven, so the "
                "full 5-link chain is asserted only when the R537 "
                "build is deployed)",
            "J_attack_calibration":
                "R537/R537_ATTACK_CALIBRATION_PROOF.json + "
                "scripts/r537_attack_calibration_proof.py (the "
                "sealed R412 corpus verified byte-identical to its "
                "seal; the measured FPR compared to the sealed "
                "fpr_max 0.30 bar; the gate state DERIVED from the "
                "committed measurement record, never asserted; FPR "
                "> 0.30 or a non-CALIBRATED gate mechanically "
                "blocks terminal KILL — kills are escalated to "
                "ESCALATED_OBJECTION at consumption, never "
                "executed)",
        },
        "live_channel_pending": {
            "note": ("the following require the live HF Space + "
                     "HF_TOKEN + the NHTSA network and are NOT "
                     "completed in this hermetic environment.  They "
                     "are recorded PENDING-LIVE-CHANNEL, never "
                     "fabricated (Art. XXV):"),
            "H_blind_scored_battery":
                "a fresh LXXIX blind battery on the deployed R537 "
                "engine specifically exercising the repaired "
                "cemetery (the known R535 false-positive class -> no "
                "cross-domain hard-block; the same-domain control -> "
                "still hard-blocked); fresh results, not a "
                "historical reclassification, prove the intervention "
                "— do not claim '4/8 fixed' from the old artifact",
            "I_nonstarved_conformance":
                "a separate unscored non-starved production "
                "conformance battery forcing a path with >= 2 "
                "materially distinct mechanisms to exercise "
                "COLLISION / PHYSICS / ATTACK / CONTRADICTION / "
                "KILLER_EXPERIMENT / ADJUDICATION / CLASSIFY / "
                "NEXT_BEST_ACTION / RANK / the post-RANK gauntlet / "
                "IMPROVE + the technical-improvement package tail; "
                "record which branches actually execute (conformance "
                "evidence, not discovery yield)",
            "J_live_fpr_measurement":
                "the ATTACK FPR live measurement against the "
                "deployed Space's /api/ops/calibration-attack on the "
                "production provider ring (the hermetic proof above "
                "records the gate state; the live FPR is measured on "
                "the deployed ring, not inferred from old narrative "
                "state)",
        },
        "optimization_authorized": False,
        "next_optimization_round": ("SYNTHESIZE (the current "
                                    "measured runtime leader; only "
                                    "after the R537 "
                                    "correctness/conformance "
                                    "closure, per the directive §10 "
                                    "— do NOT optimize it during the "
                                    "correctness/conformance round)"),
        "constitution_ref": ("Art. XXV (UNKNOWN is first-class, "
                             "never fabricated), Art. XXVII "
                             "(thresholds carry provenance; the "
                             "sealed fpr_max 0.30 is reused, never "
                             "re-invented), Art. LI (a written-but-"
                             "never-read cemetery is a log, not a "
                             "memory), Art. LXI (infrastructure is "
                             "never a scientific verdict), Art. X "
                             "(one authority), Art. LXXXIII (one "
                             "cliff at a time), Art. LXXXIV "
                             "(starvation-skip is correct), Art. "
                             "LXXVII (pipeline completion is not "
                             "discovery credit), Art. LXXIX (fresh "
                             "blind problems), Art. XI (corrections "
                             "are append-only)"),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"local HEAD: {head}")
    print(f"origin/main: {origin}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
