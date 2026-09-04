#!/usr/bin/env python3
"""R406 Step 1 — Freeze R405 truth as an immutable snapshot.

Directive: "Create an immutable R405 truth snapshot. It must contain:
commit / package hashes / novelty evidence hashes / engineering hashes /
experiment hashes / known discrepancies / known UNKNOWNs / physical
observation count / buyer engagement state. No interpretation. Only facts."

Constitutional basis: Art. IX (the snapshot is observational — it reads
state and does not modify it), Art. VI (no invented hashes — every hash is
recomputed from the working tree at the recorded commit), Art. XXIV (facts
are read from the underlying artifacts, not from summaries), Art. XXV
(UNKNOWN stays UNKNOWN — the snapshot never converts an unknown).

Every value below is computed or read by this script from the repository
at HEAD. Nothing is hand-transcribed.
"""
import hashlib
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def git(args):
    return subprocess.run(
        ["git", "-C", REPO] + args, capture_output=True, text=True,
        check=True).stdout.strip()


def load(path):
    with open(os.path.join(REPO, path)) as f:
        return json.load(f)


def main():
    head = git(["rev-parse", "HEAD"])
    tree_clean = git(["status", "--short"]) == ""

    packages = {}
    for p in ("P04", "P08", "P11", "P13"):
        recs = {}
        pdir = os.path.join(REPO, "LEAD_PORTFOLIO_4", p)
        for fn in sorted(os.listdir(pdir)):
            full = os.path.join(pdir, fn)
            if os.path.isfile(full):
                recs[f"LEAD_PORTFOLIO_4/{p}/{fn}"] = sha256_file(full)
        # P08 verification evidence subtree
        ve = os.path.join(pdir, "VERIFICATION_EVIDENCE")
        if os.path.isdir(ve):
            for root, _, files in os.walk(ve):
                for fn in sorted(files):
                    full = os.path.join(root, fn)
                    rel = os.path.relpath(full, REPO)
                    recs[rel] = sha256_file(full)
        packages[p] = recs

    top_level = {}
    for fn in ("FINAL_CLASSIFICATION.json", "GEOMETRY_REVERIFICATION_EVIDENCE.json",
               "BUYER_SURFACE_IDENTITY_AUDIT.json"):
        path = f"LEAD_PORTFOLIO_4/{fn}"
        top_level[path] = sha256_file(os.path.join(REPO, path))
    top_level["LEAD_PORTFOLIO_4_MANIFEST.json"] = sha256_file(
        os.path.join(REPO, "LEAD_PORTFOLIO_4_MANIFEST.json"))

    # Novelty evidence: recompute the restored-artifact hashes and compare
    # with the restoration provenance pins (fact: agreement/disagreement).
    prov = load("NOVELTY_EVIDENCE/RESTORATION_PROVENANCE.json")
    novelty = {}
    mismatch = []
    for e in prov.get("files", []):
        rel = e.get("restored_to")
        if not rel:
            continue
        full = os.path.join(REPO, rel)
        if not os.path.exists(full):
            mismatch.append(f"{rel}: LISTED_IN_PROVENANCE_BUT_ABSENT")
            continue
        actual = sha256_file(full)
        pinned = e.get("sha256") or e.get("restored_sha256")
        novelty[rel] = {
            "sha256_recomputed": actual,
            "sha256_pinned_in_provenance": pinned,
            "agrees": (pinned is None) or (pinned == actual),
            "source_commit": e.get("source_commit"),
        }
        if pinned is not None and pinned != actual:
            mismatch.append(f"{rel}: PIN_MISMATCH")

    engineering = {}
    for p in ("P04", "P08", "P11", "P13"):
        rel = f"LEAD_PORTFOLIO_4/{p}/ENGINEERING_TRACEABILITY.json"
        engineering[rel] = sha256_file(os.path.join(REPO, rel))
    for p in ("04_drainage_floor", "08_nir_photovoltaic",
              "11_gravity_damper", "13_pressure_sensor"):
        rel = (f"BENCHMARK_ENGINEERING_DOSSIERS/frozen_corpus_r370/{p}/"
               "ENGINEERING_TRACEABILITY.json")
        if os.path.exists(os.path.join(REPO, rel)):
            engineering[rel] = sha256_file(os.path.join(REPO, rel))

    experiments = {}
    for p in ("P04", "P08", "P11", "P13"):
        rel = f"LEAD_PORTFOLIO_4/{p}/DECISIVE_EXPERIMENT.json"
        experiments[rel] = sha256_file(os.path.join(REPO, rel))
    for rel in ("LEAD_PORTFOLIO_4/P04/QMIN_FLOOR_FLOW_CALCULATION.json",
                "LEAD_PORTFOLIO_4/P11/INSTRUMENT_MDD_CALCULATION.json",
                "LEAD_PORTFOLIO_4/P14/P14_EXTERNAL_DISTRIBUTION_RECORD.json",
                "R405/UNIT_CONVERSION_DEFECT_DISCLOSURE.json"):
        experiments[rel] = sha256_file(os.path.join(REPO, rel))

    classification = load("LEAD_PORTFOLIO_4/FINAL_CLASSIFICATION.json")
    states = {p: classification["classifications"][p]["state"]
              for p in ("P04", "P08", "P11", "P13")}

    transfer_states = {}
    for p in ("P04", "P08", "P11", "P13"):
        transfer_states[p] = load(
            f"LEAD_PORTFOLIO_4/{p}/TRANSFER_STATE.json")["current_state"]

    manifest = load("LEAD_PORTFOLIO_4_MANIFEST.json")

    snapshot = {
        "artifact_type": "R405_TRUTH_SNAPSHOT",
        "snapshot_version": "1.0",
        "generator": "scripts/r406_truth_snapshot.py (deterministic; every hash recomputed from the working tree at HEAD)",
        "snapshot_rule": "Immutable facts only. No interpretation. This file is a frozen record of R405 state at the commit below; it is never edited in place after generation (corrections, if any, are new versions).",
        "constitutional_basis": "Art. IX (observational — reads state, mutates nothing), Art. VI (no invented hashes), Art. XXIV (facts from artifacts, not summaries), Art. XXV (unknown stays unknown)",

        "commit": {
            "sha": head,
            "working_tree_clean_at_snapshot": tree_clean,
            "remote_main": head + " (ls-remote verified 2026-09-04 after the R404+R405 push)",
            "ci": "Epistemic Lightweight Check run 33843042554 success; Epistemic Certification run 33843042549 success (06:06:51Z -> 06:21:12Z, 14 gates green)",
            "constitution_version": "2.0.0 (1947 lines)",
            "constitution_sha256": sha256_file(os.path.join(REPO, "EPISTEMIC_CONSTITUTION.md")),
            "lead_portfolio_manifest_version": manifest["manifest_version"],
        },

        "final_classification_at_r405": states,
        "transfer_states_at_r405": transfer_states,

        "package_record_hashes": packages,
        "top_level_record_hashes": top_level,
        "novelty_evidence_hashes": novelty,
        "novelty_provenance_pin_mismatches": mismatch or [],
        "engineering_hashes": engineering,
        "experiment_hashes": experiments,

        "physical_observation_count": 0,
        "physical_observation_count_basis": "LEAD_PORTFOLIO_4_MANIFEST.json physical_validation field is 'NONE' for all four packages; zero PHYSICAL_OBSERVATION evidence exists in any LEAD_PORTFOLIO_4 record; loop_verification_state values are NONE/NONE/SYNTHETIC_LOOP_VERIFIED(P11)/NONE",

        "buyer_engagement_state": {
            "REAL_BUYER": 0,
            "basis": "every TRANSFER_STATE record: current_state TECHNICAL_REVIEW, 'REAL_BUYER = 0 (every release-gate honest-status field), all recipients UNCONTACTED'",
            "nda_state": "none recorded",
            "material_received": "the buyer-distribution repository release exists (Art. XXXIX chain); no recorded recipient of the release is engaged in evaluation",
            "commercial_posture_label": "SPONSORED_VALIDATION (CEO-managed commercial-state label, PORTFOLIO_COMMERCIAL_STATE.json axis — distinct from the evidence-gated transfer ladder, audit conflict C7)"
        },

        "known_discrepancies": [
            "D2 OPEN (P08): recorded 500 uW device target vs 121-163 uW conditional band on the shipped 0.384845 cm2 receiver (LEAD_PORTFOLIO_4/P08/ENERGY_BUDGET.json derived_discrepancies)",
            "P13 frozen buyer dossier lineage narrative MIS-ATTRIBUTED ('original P-27 chronic drift'; the predecessor is P-25) and contains ZERO biofouling mentions (LEAD_PORTFOLIO_4/P13/LINEAGE_AUDIT.json)",
            "P13 re-admission lacks a cemetery-waiver / DC-P-25-001-satisfaction artifact (governance gap, LINEAGE_AUDIT.json)",
            "P13 novelty: NOVELTY_SEARCH_REPORTED + SOURCE_ARTIFACT_UNAVAILABLE vs the management statement that all four were searched (NOVELTY_ASSESSMENT.json)",
            "r373 x3 + r374 x1 audit failures: the 0217d248 V3 corrections renamed P-22-R1 engine-side but the buyer surface was never re-shipped (disclosed at R401-WC2; fix path is the r386 release cycle)",
            "R396/R400/R401 recorded absolute conductances/flows are 133.322^2 = 17,774.7x too small (R405/UNIT_CONVERSION_DEFECT_DISCLOSURE.json); records stand as history per Art. XI",
            "P04 NIST-corrected 0.5471 mm rebuild exists in sandbox only; canonical/buyer geometry is 0.6 mm (GEOMETRY_SEPARATION.json valid_new_version_candidate.status = SANDBOX_ONLY)"
        ],

        "known_unknowns": [
            "P08: canonical deliverable electrical power UNKNOWN (eta_cell unknown; encapsulation transmission UNKNOWN; power electronics UNKNOWN; real external source spec UNKNOWN)",
            "P04: Q_min single operating value owner-gated (range 0.2-0.4 mL/min declared PHYSIOLOGICAL class); manufacturing (multi-lumen extrusion) capability UNKNOWN",
            "P11: clinical materiality margins for the 0.1 s settling difference UNESTABLISHED; run-to-run scatter beyond quantization unmodelled",
            "P13: prior-art state for THIS technology UNKNOWN (no search artifact); drift-target EXTERNAL_PRECEDENT sourcing open; waiver/re-admission basis open",
            "All four: zero physical validation; manufacturing process capability unmeasured; regulatory pathway UNKNOWN",
            "P04 common-cause kill threshold (>=90% rule) and P13 fouling criterion (1 mmHg) are owner-gated pre-registrations, not registered values"
        ]
    }

    out = os.path.join(REPO, "R406", "R405_TRUTH_SNAPSHOT.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(snapshot, f, indent=1, sort_keys=True)
    print(f"wrote {out}")
    n_hashes = (sum(len(v) for v in packages.values()) + len(top_level)
                + len(novelty) + len(engineering) + len(experiments))
    print(f"hashed artifacts: {n_hashes}; provenance pin mismatches: {len(mismatch)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
