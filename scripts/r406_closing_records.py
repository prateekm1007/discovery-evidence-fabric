#!/usr/bin/env python3
"""R406 closing records: FINAL_CLASSIFICATION r406 extensions, manifest
v4.0, and the acceptance checklist mapping the directive's 16 items to
their evidence.

Classification: UNCHANGED in class for all four packages (P04
READY_FOR_TECHNICAL_EVALUATION, P08 REQUIRES_ENGINEERING_REPAIR, P11
READY_FOR_SPONSORED_VALIDATION, P13 REQUIRES_EVIDENCE_REPAIR; P14
separate). What changed is the BASIS: P13's prior gap (no search
artifact) is repaired and replaced by a stronger one (novelty CONTESTED
by located art); P08 gains a fluence reproducibility contest that
reinforces REQUIRES_ENGINEERING_REPAIR; P04's canonical NIST state is
resolved (RETAIN); P11's kill conditions are now registered.
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(rel):
    with open(os.path.join(REPO, rel)) as f:
        return json.load(f)


def write(rel, obj):
    out = os.path.join(REPO, rel)
    with open(out, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
    print(f"wrote {rel}")


def main():
    # ---- 1. FINAL_CLASSIFICATION r406 extension (additive) ----
    fc_rel = "LEAD_PORTFOLIO_4/FINAL_CLASSIFICATION.json"
    fc = load(fc_rel)
    fc["r406_extensions"] = {
        "directive_basis": "R406 (real technology-transfer loop): the classification states are UNCHANGED — nothing this round is a class-changing fact; the BASIS of each is updated honestly below",
        "P04": {
            "state": "READY_FOR_TECHNICAL_EVALUATION (unchanged)",
            "basis_updates": [
                "canonical NIST state RESOLVED: RETAIN 0.6 mm with technical justification (R406/R406_P04_NIST_DECISION.json) — one canonical truth per quantity",
                "contamination audit: the R396/R400/R401 meets_required_min verdict flip (false -> true under the corrected conductance) is disclosed and REQUIRES_REASSESSMENT-classified with zero propagation to the canonical records (R406/R406_CONDUCTANCE_CONTAMINATION_AUDIT.json)",
                "the decisive experiment is now FULLY PRE-REGISTERED (Q_min 0.4/0.2, common-cause 90% rule, false-pass rule, repeatability, sample size, decision rule — EXPERIMENT_PREREGISTRATION.json): a technical evaluator can price and run it",
            ],
        },
        "P08": {
            "state": "REQUIRES_ENGINEERING_REPAIR (unchanged, reinforced)",
            "basis_updates": [
                "the energy model is now REPRODUCIBLE FROM CLEAN CHECKOUT (R406/P08_ENERGY_PIPELINE/PIPELINE_RUN.json: 7-stage chain, committed inputs/seed/outputs/plots/hashes/environment) — the R406 directive's reproducibility requirement is satisfied",
                "NEW: the independent reproduction CONTESTS the anchor fluence at the ~40% level (0.705 vs 1.049-1.416 mW/cm2) and records that the R310 anchor pair was same-hand implemented (its 0.11% agreement is not independent confirmation) — the D2 decision now has two quantitative bases (121-163 uW anchor band vs 81 uW independent GaAs-conditional), BOTH below the 500 uW target: the REQUIRES_ENGINEERING_REPAIR direction is unchanged and strengthened",
            ],
        },
        "P11": {
            "state": "READY_FOR_SPONSORED_VALIDATION (unchanged, strengthened)",
            "basis_updates": [
                "the experimental contract is now BUYER-EXECUTABLE with every element registered: blinded analysis, primary endpoints, predefined MDD 0.0253 s, quantitative kill conditions A/B, manufacturing tolerance, SAP (Wilcoxon signed-rank, alpha 0.05, no peeking), cost $15K/8wk RECORDED (EXPERIMENT_PREREGISTRATION.json)",
                "the experiment is capable of SUPPORTED or KILLED — not merely an interesting graph (the directive's Step 5 requirement)",
            ],
        },
        "P13": {
            "state": "REQUIRES_EVIDENCE_REPAIR (unchanged in class; the basis STRENGTHENED)",
            "basis_updates": [
                "the prior gap 'no search artifact exists' is REPAIRED: a specific search now exists with committed provenance custody (LEAD_PORTFOLIO_4/P13/NOVELTY_SEARCH_R406/) — verdict CONTESTED at the architecture level by located prior art (Seaver 2018 dual matched-die implantable ICP sensor dissertation; US4320664 1982 dummy-element bridge; WO2014076620A2 implanted-sensor drift compensation; US11701504B2 shunt-mounted ICP sensing; US11422051B2 sealed-cavity reference)",
                "the replacement gap is stronger than the old one: claim-differentiation review (owner patent counsel) is now the gating evidence action, and large engineering spend stays gated per the directive's hard-gate rule",
                "the KA-014 kill experiment is registered with the predecessor failure built in (5 arms; recalibration explicitly not a mechanism fix)",
            ],
        },
        "P14": {"state": "NOT_IN_FOUR_LEAD_PORTFOLIO (unchanged; records untouched this round)"},
    }
    write(fc_rel, fc)

    # ---- 2. Manifest v4.0 ----
    mf_rel = "LEAD_PORTFOLIO_4_MANIFEST.json"
    mf = load(mf_rel)
    mf["manifest_version"] = "4.0"
    for lp in mf["lead_packages"]:
        p = lp["company_designation"]
        add = [
            f"LEAD_PORTFOLIO_4/{p}/LOOP_CHAIN.json",
            f"LEAD_PORTFOLIO_4/{p}/MODEL_UPDATE_LEDGER.json",
            f"LEAD_PORTFOLIO_4/{p}/BUYER_EVALUATION_STATE.json",
            f"LEAD_PORTFOLIO_4/{p}/KILLABILITY_ASSESSMENT.json",
        ]
        if p in ("P04", "P11", "P13"):  # the directive's Steps 4/5/8 packages
            add.append(f"LEAD_PORTFOLIO_4/{p}/EXPERIMENT_PREREGISTRATION.json")
        if p == "P08":  # Step 6's artifact is the reproducible pipeline
            add.append("R406/P08_ENERGY_PIPELINE/PIPELINE_RUN.json")
        if p == "P13":
            add.append("LEAD_PORTFOLIO_4/P13/NOVELTY_SEARCH_R406/"
                       "NOVELTY_SEARCH_RESULT.json")
        lp["canonical_records"] = sorted(set(lp["canonical_records"] + add))
        # defensive: P08 never had an EXPERIMENT_PREREGISTRATION (its R406
        # artifact is the pipeline) — remove any stale entry so reruns stay
        # idempotent
        if p == "P08":
            lp["canonical_records"] = [
                r for r in lp["canonical_records"]
                if r != "LEAD_PORTFOLIO_4/P08/EXPERIMENT_PREREGISTRATION.json"]
        if p == "P13":
            lp["novelty_state"] = ("SEARCHED_AND_CONTESTED — a specific search artifact now exists "
                                   "(NOVELTY_SEARCH_R406, committed provenance custody); verdict CONTESTED at the "
                                   "architecture level by located prior art (Seaver 2018 dual-die dissertation, "
                                   "US4320664, WO2014076620A2, US11701504B2, US11422051B2); formal determination "
                                   "requires owner patent counsel")
        lp["loop_verification_state"] = (
            "NONE (derived: chain at PREDICTION, promotion blocked NO_PHYSICAL_DATA — "
            "the R406 14-state loop chain with machine-readable events; P11's legacy "
            "SYNTHETIC_LOOP_VERIFIED from R339 is recorded in its LOOP_CHAIN legacy field)")
    mf["r406_real_loop_round"] = {
        "date": "2026-09-04",
        "directive": "R406 — PHASE REAL TECHNOLOGY-TRANSFER LOOP: freeze R405 truth, contamination-audit the conductance defect, resolve the P04 canonical state, pre-register the physical experiments (P04 common-cause / P11 baseline / P13 KA-014), reproduce the P08 energy model from clean checkout, search P13 novelty, record buyer states, build the closed-loop schema + model-vs-measurement machinery, and assess killability",
        "new_artifacts": [
            "R406/R405_TRUTH_SNAPSHOT.json (immutable facts: 82 hashed artifacts, physical observation count 0, REAL_BUYER 0)",
            "R406/R406_CONDUCTANCE_CONTAMINATION_AUDIT.json (10 artifact entries, ratio survival PROVEN by recomputation, the meets_required_min verdict-flip discovered and disclosed, the R400 UI artifact the R405 inventory missed)",
            "R406/R406_P04_NIST_DECISION.json (RETAIN 0.6 mm with four-ground technical justification; single canonical truth; adoption path recorded)",
            "LEAD_PORTFOLIO_4/P{04,11,13}/EXPERIMENT_PREREGISTRATION.json (frozen pre-registrations, no post-hoc thresholds)",
            "R406/P08_ENERGY_PIPELINE/ (PIPELINE_RUN.json + PIPELINE_PROFILES.png: deterministic seeded MC, 7-stage chain, automatic budget comparison, the anchor-reproducibility contest)",
            "LEAD_PORTFOLIO_4/P13/NOVELTY_SEARCH_R406/ (search record + 11 custody files: 7 queries, 4 claim-section extracts, verdict CONTESTED)",
            "LEAD_PORTFOLIO_4/P{04,08,11,13}/LOOP_CHAIN.json + MODEL_UPDATE_LEDGER.json + BUYER_EVALUATION_STATE.json + KILLABILITY_ASSESSMENT.json",
            "discovery_fabric/engine/loop_chain.py (the 14-state machine-enforced chain: REALITY_EVENT-required promotion, Art. XXXVIII schema enforcement)",
            "discovery_fabric/engine/model_measurement.py (model-vs-measurement verdicts: MODEL_IMPROVED / MODEL_NOT_IMPROVED / INSUFFICIENT_DATA)",
            "R406/R406_ACCEPTANCE_CHECKLIST.json (the 16 directive items mapped to evidence)",
            "tests/test_r406_real_loop.py (adversarial pins)",
        ],
        "generators": [
            "scripts/r406_truth_snapshot.py", "scripts/r406_contamination_audit.py",
            "scripts/r406_p04_nist_decision.py", "scripts/r406_preregistrations.py",
            "scripts/r406_p08_energy_pipeline.py", "scripts/r406_p13_novelty_search.py",
            "scripts/r406_loop_and_buyer_records.py", "scripts/r406_closing_records.py",
        ],
        "final_classification": "UNCHANGED (P04 / P08 / P11 / P13 as R404-R405; basis updated per FINAL_CLASSIFICATION r406_extensions)",
        "honest_limits": [
            "physical_observation_count remains 0 — the entire round is machinery + records; the next material milestone is the FIRST REAL PHYSICAL OBSERVATION entering the loop and changing a technology decision (the directive's own closing requirement)",
            "REAL_BUYER = 0; no buyer engagement fabricated",
            "the P08 independent-run fluence contest is recorded, NOT resolved (canonical anchors stand; owner adjudication open)",
            "P13's CONTESTED verdict is a search-backed position, not a novelty determination (Art. XXVIII)",
        ],
    }
    write(mf_rel, mf)

    # ---- 3. acceptance checklist ----
    checklist = {
        "artifact_type": "R406_ACCEPTANCE_CHECKLIST",
        "directive_quotation": "Do not report 'R406 complete' unless all of the following are true",
        "items": [
            {"item": "Constitution reread", "state": "TRUE", "evidence": "EPISTEMIC_CONSTITUTION.md v2.0.0 read in full (1,947 lines) at session start AND re-read in full before R406 work; CONSTITUTION_READ_FULLY: YES; byte-identical verified (sha256 b7db5e57..., clean tree at 67792862)"},
            {"item": "Conductance contamination audit complete", "state": "TRUE", "evidence": "R406/R406_CONDUCTANCE_CONTAMINATION_AUDIT.json — 10 entries, 5-class vocabulary used, ratio survival recomputed (not assumed), two new Art. XV findings vs the R405 disclosure (missed R400 UI artifact; meets_required_min flip)"},
            {"item": "P04 canonical state resolved", "state": "TRUE", "evidence": "R406/R406_P04_NIST_DECISION.json — RETAIN with 4-ground justification; one canonical truth per quantity; auditor conflict resolved by recorded decision, not silence"},
            {"item": "P04 decisive experiment executable", "state": "TRUE", "evidence": "LEAD_PORTFOLIO_4/P04/EXPERIMENT_PREREGISTRATION.json — 3 obstruction conditions + single-lumen control, 5 measured quantities, registered Q_min/kill/false-pass/repeatability/sample-size/decision rules; cost $11-25K REPORTED"},
            {"item": "P08 model reproducible", "state": "TRUE", "evidence": "R406/P08_ENERGY_PIPELINE/PIPELINE_RUN.json — rerun: python3 scripts/r406_p08_energy_pipeline.py (deterministic seed 20260904); committed inputs/versions/config/outputs/plots/hashes/environment"},
            {"item": "P08 arithmetic reconciled", "state": "TRUE (with a new open contest)", "evidence": "the 7-stage chain auto-computes fluence -> incident power -> conversion; the R404 D1 reconciliation stands; the R406 independent run CONTESTS the anchor magnitude (~40%) — recorded, canonical unchanged, owner adjudication open"},
            {"item": "P11 baseline experiment executable", "state": "TRUE", "evidence": "LEAD_PORTFOLIO_4/P11/EXPERIMENT_PREREGISTRATION.json — 3 arms vs REAL ASD, blinded, registered kill conditions A/B, manufacturing tolerance, cost $15K/8wk RECORDED, SAP frozen"},
            {"item": "P11 MDD and kill rule fixed", "state": "TRUE", "evidence": "MDD 0.0253 s (INSTRUMENT_MDD_CALCULATION) + registered conditions A (>= 20% faster at all 4 pressures) and B (target-flow accuracy) — frozen before any run"},
            {"item": "P13 specific novelty search completed", "state": "TRUE", "evidence": "LEAD_PORTFOLIO_4/P13/NOVELTY_SEARCH_R406/NOVELTY_SEARCH_RESULT.json — 7 queries incl. both R405 Patent-Bear strings; 6 located art records with verbatim claim spans; 11 custody files; verdict CONTESTED (never inferred from zero hits)"},
            {"item": "P13 KA-014 experimentally addressed", "state": "TRUE (protocol-level: registered, not executed — zero physical data exists by record)", "evidence": "LEAD_PORTFOLIO_4/P13/EXPERIMENT_PREREGISTRATION.json — 5 arms incl. combined fouling+thermal; KA-014 kill criterion 1 mmHg registered; periodic recalibration explicitly NOT a mechanism fix"},
            {"item": "Four buyer states accurate", "state": "TRUE", "evidence": "LEAD_PORTFOLIO_4/Pnn/BUYER_EVALUATION_STATE.json — REAL_BUYER = 0, every engagement field NONE/null with the fabrication guard"},
            {"item": "Four package hashes/manifests coherent", "state": "TRUE", "evidence": "R406/R405_TRUTH_SNAPSHOT.json (82 recomputed hashes, 0 provenance mismatches) + LEAD_PORTFOLIO_4_MANIFEST.json v4.0 (every new record enumerated per package)"},
            {"item": "Clean clone replay", "state": "PENDING_AT_WRITE — executed at commit time (see the worklog and commit message for the recorded result)", "evidence": "the replay procedure: fresh clone -> test_r406_real_loop.py + the R402-R405 regression battery -> pipeline rerun byte-check"},
            {"item": "Full regression", "state": "PENDING_AT_WRITE — executed at commit time", "evidence": "r406 + r405 + r404 + r403 + r402 + r386 + r390 + r396 + r397 + r394 batteries"},
            {"item": "No unsupported claims", "state": "TRUE", "evidence": "every claim this round cites a committed artifact; physical validation claimed nowhere; world-class claimed nowhere; the P13 CONTESTED verdict and the P08 fluence contest are recorded as open, not resolved"},
            {"item": "End-to-end loop schema implemented", "state": "TRUE", "evidence": "discovery_fabric/engine/loop_chain.py (14 canonical states, machine-readable transition events, REALITY_EVENT-gated promotion — the absence of physical data blocks promotion, proven by adversarial tests) + model_measurement.py (Step 11 verdicts) + per-package LOOP_CHAIN/MODEL_UPDATE_LEDGER records"},
        ],
        "the_final_requirement": {
            "directive": "Do not optimize this round for another impressive test count. The next material milestone is the first real physical observation entering the loop and changing a technology decision.",
            "state": "HONORED: physical_observation_count = 0 is recorded as the headline fact of the truth snapshot; every chain is capped at PREDICTION with promotion_blocked_reason NO_PHYSICAL_DATA; the machine is armed end-to-end and waits on reality",
        },
    }
    write("R406/R406_ACCEPTANCE_CHECKLIST.json", checklist)
    print("closing records complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
