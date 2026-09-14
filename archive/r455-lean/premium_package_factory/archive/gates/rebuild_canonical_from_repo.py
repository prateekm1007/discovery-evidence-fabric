"""
rebuild_canonical_from_repo.py — Rebuild the factory's canonical input
HONESTLY from the actual R332 repo file + conversation-summary deltas.

This replaces the previous reconstructed canonical_15_packages_R370.json
which had invented field values (e.g., P-01 mechanism had "(P_ICP <= 20 mmHg
AND F_i <= F_MAX for all segments)" appended that is NOT in R332).

Strategy:
  1. Load R332/g3_all13_canonical/CANONICAL_BUYER_PACKAGES.json (13 packages)
  2. For each R332 package, copy ALL fields VERBATIM (no additions)
  3. Add R335-R370 deltas from conversation summary, clearly marked:
     - KILL: P-10 (n-eicosane failed, n-octadecane repair in P-10... but P-10 is in R332 as alive)
       Actually per summary: P-10 was killed in R347. P-12, P-20 killed in R364.
     - ADD: P-24, P-26, P-27-R1, P-28, P-29 (from R347/R368)
     - REPAIR: P-15→P-15-R1, P-21→P-21-R1, P-22→P-22-R1, P-27→P-27-R1 (from R364)
  4. Each delta entry has provenance: "FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED"

The factory then uses this file as input, and Gate 1 verifies:
  - 13 R332 packages: 0 field mismatches with repo (VERIFIED)
  - 8 delta entries: flagged as UNVERIFIED (honest)
"""

import os
import json
import hashlib
from datetime import datetime, timezone

REPO_ROOT = "/home/z/my-project/discovery-evidence-fabric"
CANONICAL_R332 = os.path.join(REPO_ROOT, "R332/g3_all13_canonical/CANONICAL_BUYER_PACKAGES.json")
OUTPUT_PATH = "/home/z/my-project/canonical_data/canonical_15_packages_honest.json"


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def rebuild():
    """Rebuild canonical input honestly from R332 + conversation-summary deltas."""

    # Load R332 (the actual repo canonical)
    with open(CANONICAL_R332) as f:
        r332 = json.load(f)

    r332_authority = r332.get("authority", "")
    r332_constitution_hash = r332.get("constitution_hash", "")
    r332_timestamp = r332.get("timestamp", "")

    packages = {}
    package_provenance = {}

    # Copy all 13 R332 packages VERBATIM
    for key, value in r332.items():
        if key.startswith("P-"):
            packages[key] = dict(value)  # shallow copy is fine — values are strings/lists
            package_provenance[key] = {
                "source": "R332/g3_all13_canonical/CANONICAL_BUYER_PACKAGES.json",
                "source_hash": _sha256_file(CANONICAL_R332),
                "verification": "VERIFIED_AGAINST_REPO",
                "fields_copied_verbatim": list(value.keys())
            }

    # Mark packages that the conversation summary says were KILLED in R335-R370
    # but are still alive in R332. We keep them in the package list (for traceability)
    # but flag them with a "killed_in_later_round" field.
    # Per conversation summary:
    #   P-12: killed in R364 (0 design-around solutions)
    #   P-20: killed in R364 (0 design-around solutions)
    #   P-10: killed in R347 (n-eicosane FAILED, n-octadecane is repair candidate
    #         but per summary P-10 is NOT in the final 15; the summary lists
    #         P-10_PHASE_CHANGE_VALVE as having "n-eicosane FAILED at 5.04s"
    #         and n-octadecane as the repair — but the final 15 list does NOT
    #         include P-10. So P-10 was killed.)
    killed_in_later_round = {
        "P-10": {
            "kill_round": "R347",
            "kill_reason": "n-eicosane FAILED at 5.04s; n-octadecane repair candidate but not in final 15",
            "source": "FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED"
        },
        "P-12": {
            "kill_round": "R364",
            "kill_reason": "0 design-around solutions found; cannot evade existing CNS biotech patents",
            "source": "FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED"
        },
        "P-20": {
            "kill_round": "R364",
            "kill_reason": "0 design-around solutions found; CD47-mimetic glycan + IL-10 PLGA combination fully covered",
            "source": "FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED"
        }
    }

    for pkg_id, kill_info in killed_in_later_round.items():
        if pkg_id in packages:
            packages[pkg_id]["_killed_in_later_round"] = kill_info
            package_provenance[pkg_id]["killed_in_later_round"] = kill_info

    # Mark packages that were SUPERSEDED by R1 repairs (P-15→P-15-R1, etc.)
    # These are kept in the package list for traceability but flagged as superseded.
    # The factory should NOT generate buyer-facing PDFs for superseded packages.
    superseded_by_r1 = {
        "P-15": {
            "superseded_by": "P-15-R1",
            "supersede_round": "R364",
            "reason": "Original cardiac motion harvesting failed in shunt geometry; superseded by P-15-R1 (extracardiac harvesting)",
            "source": "FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED"
        },
        "P-21": {
            "superseded_by": "P-21-R1",
            "supersede_round": "R364",
            "reason": "Original UWB localization was MARGINAL (10mm vs 5mm); superseded by P-21-R1 (RFID)",
            "source": "FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED"
        },
        "P-22": {
            "superseded_by": "P-22-R1",
            "supersede_round": "R364",
            "reason": "Original SMP buckling FALSIFIED + tissue safety VIOLATED; superseded by P-22-R1 (hydraulic)",
            "source": "FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED"
        }
    }

    for pkg_id, sup_info in superseded_by_r1.items():
        if pkg_id in packages:
            packages[pkg_id]["_superseded_by_r1"] = sup_info
            package_provenance[pkg_id]["superseded_by_r1"] = sup_info

    # Add the R1 repair packages (P-15→P-15-R1, P-21→P-21-R1, P-22→P-22-R1)
    # Per conversation summary:
    #   P-15-R1: cardiac motion failed → extracardiac harvesting
    #   P-21-R1: UWB 10mm marginal → RFID localization
    #   P-22-R1: SMP buckling failed → hydraulic navigation
    #   P-27-R1: polymer substrate failed → metal tube
    # These are NEW package IDs that don't exist in R332.
    # We construct them by taking the R332 base and applying the documented R1 repair.

    r1_repairs = {
        "P-15-R1": {
            "base_package": "P-15",
            "repair_round": "R364",
            "original_failure": "Cardiac motion harvesting failed in shunt geometry (10 μW P50 not achievable)",
            "r1_mechanism_change": "Extracardiac harvesting (CSF pulsation + neck motion) instead of cardiac motion",
            "source": "FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED"
        },
        "P-21-R1": {
            "base_package": "P-21",
            "repair_round": "R364",
            "original_failure": "UWB localization accuracy MARGINAL (10mm vs 5mm clinical requirement)",
            "r1_mechanism_change": "RFID with passive tags instead of UWB",
            "source": "FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED"
        },
        "P-22-R1": {
            "base_package": "P-22",
            "repair_round": "R364",
            "original_failure": "SMP buckling FALSIFIED (82x exceedance) + tissue safety VIOLATED (0.039 N > 0.01 N)",
            "r1_mechanism_change": "Hydraulic pressure-driven navigation instead of shape-memory polymer",
            "source": "FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED"
        }
    }

    for r1_id, repair_info in r1_repairs.items():
        base_id = repair_info["base_package"]
        if base_id in packages:
            # Copy base package verbatim, then apply R1 changes
            # IMPORTANT: Do NOT copy the _superseded_by_r1 field from the base
            r1_pkg = {k: v for k, v in packages[base_id].items()
                      if k not in ["_superseded_by_r1", "_killed_in_later_round"]}
            r1_pkg["id"] = r1_id
            r1_pkg["_r1_repair"] = repair_info
            # Update mechanism to reflect R1 change (only the mechanism field)
            # We do NOT invent new values for other fields — they stay as R332 verbatim
            # The mechanism field is updated to reflect the R1 architecture
            if r1_id == "P-15-R1":
                r1_pkg["mechanism"] = (
                    "Extracardiac mechanical energy harvesting (CSF pulsation + neck motion) "
                    "+ 100μF capacitor + duty-cycled sensing "
                    "[R1 REPAIR: original P-15 cardiac motion harvesting failed in shunt geometry]"
                )
                r1_pkg["evidence_now"] = (
                    "R1 repair (R364). Cardiac motion harvesting FALSIFIED in shunt geometry "
                    "(10 μW P50 not achievable). Extracardiac harvesting modelled but unverified. "
                    "[FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED]"
                )
            elif r1_id == "P-21-R1":
                r1_pkg["mechanism"] = (
                    "Passive RFID tags at catheter tip + wearable external reader for 3D position tracking "
                    "[R1 REPAIR: original P-21 UWB localization was MARGINAL (10mm vs 5mm requirement)]"
                )
                r1_pkg["evidence_now"] = (
                    "R1 repair (R364). UWB localization was MARGINAL (10mm vs 5mm requirement). "
                    "RFID with passive tags modelled for higher accuracy + lower power. "
                    "[FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED]"
                )
            elif r1_id == "P-22-R1":
                r1_pkg["mechanism"] = (
                    "Hydraulic pressure-driven multi-segment catheter navigation "
                    "[R1 REPAIR: original P-22 SMP buckling FALSIFIED (82x exceedance) + "
                    "tissue safety VIOLATED (0.039 N > 0.01 N)]"
                )
                r1_pkg["evidence_now"] = (
                    "R1 repair (R364). P-22 original: SMP buckling FALSIFIED + tissue safety VIOLATED + "
                    "control stability NOT modeled. Hydraulic navigation modelled as alternative. "
                    "[FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED]"
                )
            packages[r1_id] = r1_pkg
            package_provenance[r1_id] = {
                "source": "FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED",
                "base_package": base_id,
                "base_source": "R332/g3_all13_canonical/CANONICAL_BUYER_PACKAGES.json",
                "base_source_hash": _sha256_file(CANONICAL_R332),
                "repair_round": repair_info["repair_round"],
                "verification": "R1_REPAIR_FROM_SUMMARY_BASE_VERIFIED",
                "fields_modified_from_base": ["id", "mechanism", "evidence_now"],
                "fields_copied_verbatim_from_base": [
                    f for f in packages[base_id].keys()
                    if f not in ["id", "mechanism", "evidence_now", "_r1_repair"]
                ]
            }

    # Add the entirely new packages from R347/R368 (P-24, P-26, P-27-R1, P-28, P-29)
    # These have NO base in R332. All fields are FROM_CONVERSATION_SUMMARY.
    new_packages = {
        "P-24": {
            "buyer_action_id": "P24-EXP-001",
            "problem": "Postural ICP excursions cause patient symptoms and possible complications. Existing valves cannot compensate passively.",
            "buyer": "Shunt OEM (valve manufacturer)",
            "mechanism": "Passive hydraulic damper using gravity head to compensate for postural ICP variations",
            "evidence_now": "T1 MODEL_PREDICTED. Computational model predicts 60% reduction in postural ICP excursion. [FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED]",
            "modelled_only": ["60% postural ICP excursion reduction (MODELLED)", "Damper dynamics idealized"],
            "known_failures": [],
            "strongest_alternative": "Fixed-pressure programmable valve (Medtronic Strata) — no postural compensation",
            "remaining_uncertainty": "Whether 60% reduction survives real patient postural dynamics",
            "decisive_experiment": "Bench: passive damper in mock CSF loop with 5 postural scenarios. Measure ICP excursion.",
            "pass_rule": "Damper reduces ICP excursion by >= 40% vs no-damper in >= 4 of 5 postural scenarios",
            "fail_rule": "Damper reduces ICP excursion by < 20% in >= 3 of 5 scenarios",
            "cost_estimate": "$8-15K (ESTIMATED)",
            "timeline_estimate": "3-5 weeks (ESTIMATED)",
            "integration_path": "LOW — passive mechanical feature, no new sensor",
            "regulatory_status": "510(k) possible (passive modification to existing valve)",
            "commercial_route": "License to valve manufacturer",
            "buyer_action": "COMMISSION TEST — build mock CSF loop, run 5 postural scenarios with/without damper",
            "provenance_manifest": "R347/p24_manufacturing/ [FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED]"
        },
        "P-26": {
            "buyer_action_id": "P26-EXP-001",
            "problem": "Fixed-pressure shunts cannot adapt to CSF composition changes that affect drainage dynamics. No self-regulating passive valve exists.",
            "buyer": "Shunt OEM (valve manufacturer)",
            "mechanism": "Passive osmotic-driven drainage valve responsive to CSF osmolarity changes",
            "evidence_now": "T1 MODEL_PREDICTED. Computational model predicts 35% improvement in drainage regulation. [FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED]",
            "modelled_only": ["35% drainage regulation improvement (MODELLED)", "Osmotic membrane dynamics idealized"],
            "known_failures": [],
            "strongest_alternative": "Fixed-pressure programmable valve (Medtronic Strata) — no self-regulation",
            "remaining_uncertainty": "Whether 35% improvement survives real CSF osmolarity variability",
            "decisive_experiment": "Bench: osmotic valve prototype in mock CSF loop with 3 osmolarity levels (280, 295, 310 mOsm/L).",
            "pass_rule": "Drainage rate adjusts >= 25% across osmolarity range AND response time < 30 minutes",
            "fail_rule": "Drainage rate adjusts < 10% OR response time > 2 hours",
            "cost_estimate": "$10-20K (ESTIMATED)",
            "timeline_estimate": "4-6 weeks (ESTIMATED)",
            "integration_path": "MEDIUM — osmotic membrane integration with valve",
            "regulatory_status": "510(k) possible (passive modification)",
            "commercial_route": "License to valve manufacturer",
            "buyer_action": "COMMISSION TEST — build osmotic valve prototype, measure flow response to osmolarity changes",
            "provenance_manifest": "R347/p26_manufacturing/ [FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED]"
        },
        "P-27-R1": {
            "buyer_action_id": "P27-EXP-001",
            "problem": "Implantable pressure sensors drift over time, requiring recalibration or replacement surgery. No self-referenced drift-free sensor exists.",
            "buyer": "Implantable sensor company / shunt OEM",
            "mechanism": "Self-referenced piezoresistive pressure sensor using metal tube substrate for drift compensation [R1 REPAIR: original P-27 polymer substrate failed]",
            "evidence_now": "R1 repair (R364). P-27 original: polymer substrate FALSIFIED (hysteresis 8%, drift 2%/day). Metal tube substrate modelled for <0.5%/day drift. [FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED]",
            "modelled_only": ["<0.5%/day drift target (MODELLED)", "Metal substrate thermal stability (MODELLED)"],
            "known_failures": ["P-27 original: Polymer substrate hysteresis 8% (vs <1% target)", "P-27 original: Polymer substrate drift 2%/day (vs <0.5%/day target)"],
            "strongest_alternative": "MEMS pressure sensors (drift 1-2%/day, require recalibration)",
            "remaining_uncertainty": "Whether metal substrate achieves <0.5%/day drift in vivo",
            "decisive_experiment": "Bench: metal substrate sensor in CSF-mimicking bath, 30 days. Measure drift + hysteresis.",
            "pass_rule": "Drift < 0.5%/day AND hysteresis < 1% over 30 days",
            "fail_rule": "Drift > 1%/day OR hysteresis > 2%",
            "cost_estimate": "$8-15K (ESTIMATED)",
            "timeline_estimate": "4-6 weeks (ESTIMATED)",
            "integration_path": "MEDIUM — sensor integration with catheter",
            "regulatory_status": "PMA (active implantable sensor)",
            "commercial_route": "License to implantable sensor company",
            "buyer_action": "COMMISSION TEST — build metal substrate sensor, measure drift over 30 days",
            "provenance_manifest": "R347/p27_manufacturing/ + R364/p27_r1_repair/ [FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED]"
        },
        "P-28": {
            "buyer_action_id": "P28-EXP-001",
            "problem": "Catheter obstruction causes 30-50% of shunt failures. Current detection requires CT/MRI or clinical symptoms. No non-invasive acoustic detection exists.",
            "buyer": "Shunt OEM / medical imaging company",
            "mechanism": "Acoustic resonance sensor detecting catheter obstruction via acoustic transmission change through CSF",
            "evidence_now": "T1 MODEL_PREDICTED. Computational model predicts >90% obstruction detection accuracy. [FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED]",
            "modelled_only": [">90% detection accuracy (MODELLED)", "Acoustic propagation model (MODELLED)"],
            "known_failures": [],
            "strongest_alternative": "CT/MRI (radiation, expensive, delayed) or clinical symptoms (late detection)",
            "remaining_uncertainty": "Whether acoustic detection achieves >90% accuracy in vivo with anatomical variability",
            "decisive_experiment": "Bench: acoustic transducer + catheter mock + obstruction states (0%, 30%, 70%, 100%). Measure detection accuracy across 100 trials.",
            "pass_rule": "Detection accuracy >= 85% AND false positive rate < 10%",
            "fail_rule": "Detection accuracy < 70% OR false positive rate > 20%",
            "cost_estimate": "$10-20K (ESTIMATED)",
            "timeline_estimate": "4-6 weeks (ESTIMATED)",
            "integration_path": "MEDIUM — external device, no implanted components",
            "regulatory_status": "510(k) possible (non-invasive diagnostic device)",
            "commercial_route": "License to shunt OEM or imaging company",
            "buyer_action": "COMMISSION TEST — build acoustic test rig, measure obstruction detection accuracy",
            "provenance_manifest": "R368/p28_alternative_candidate/ [FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED]"
        },
        "P-29": {
            "buyer_action_id": "P29-EXP-001",
            "problem": "CSF flow measurement is currently only possible via MRI (expensive, intermittent). No implantable flow sensor exists.",
            "buyer": "Implantable sensor company / shunt OEM",
            "mechanism": "Miniaturized NMR flow sensor measuring CSF flow velocity via proton spin phase shift",
            "evidence_now": "T1 MODEL_PREDICTED. Computational model predicts ±5% flow accuracy. Miniaturization architecture specified but unverified. [FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED]",
            "modelled_only": ["±5% flow accuracy (MODELLED)", "Miniaturization feasibility (MODELLED)"],
            "known_failures": [],
            "strongest_alternative": "External MRI flow measurement (expensive, intermittent, not real-time)",
            "remaining_uncertainty": "Whether miniaturized NMR is physically achievable in catheter-scale form factor",
            "decisive_experiment": "Bench: miniaturized NMR prototype in mock CSF flow loop. Measure flow accuracy across 0.01-1.0 mL/min range.",
            "pass_rule": "Flow accuracy ±10% OR BETTER across 0.01-1.0 mL/min range AND form factor < 5mm diameter",
            "fail_rule": "Flow accuracy > 25% OR form factor > 10mm diameter",
            "cost_estimate": "$30-60K (ESTIMATED)",
            "timeline_estimate": "8-12 weeks (ESTIMATED)",
            "integration_path": "VERY HIGH — NMR miniaturization is technically challenging",
            "regulatory_status": "PMA (active implantable with magnetic field)",
            "commercial_route": "License to implantable sensor company (HIGH RISK)",
            "buyer_action": "COMMISSION TEST — build miniaturized NMR prototype, measure flow accuracy",
            "provenance_manifest": "R368/p29_alternative_candidate/ [FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED]"
        }
    }

    for pkg_id, pkg_data in new_packages.items():
        pkg_data["id"] = pkg_id
        packages[pkg_id] = pkg_data
        package_provenance[pkg_id] = {
            "source": "FROM_CONVERSATION_SUMMARY_NOT_REPO_VERIFIED",
            "verification": "NOT_VERIFIED_AGAINST_REPO",
            "note": f"Package {pkg_id} is an R335-R370 addition. Not present in R332 (local repo latest). "
                    f"All fields derived from conversation summary, not repo canonical."
        }

    # Build the final honest canonical file
    honest_canonical = {
        "authority": "Honest canonical input for Premium Package Factory — R332 repo verbatim + conversation-summary deltas",
        "generated_at": _now_iso(),
        "constitution_sha256": r332_constitution_hash,
        "constitution_version": "v1.7.0 (per conversation summary; R332 file references v1.6.0-era hash)",

        "honest_disclosure": {
            "local_repo_latest_commit": "fb9d691 (Round 334, 2026-08-26)",
            "local_repo_latest_canonical_file": "R332/g3_all13_canonical/CANONICAL_BUYER_PACKAGES.json",
            "local_repo_canonical_hash": _sha256_file(CANONICAL_R332),
            "r335_r370_locally_available": False,
            "r335_r370_pull_blocked": "GitHub PAT redacted in CREDENTIALS_AND_MODELS.md",
            "packages_verified_against_repo": 13,
            "packages_from_conversation_summary_only": 8,
            "packages_from_conversation_summary": [
                "P-15-R1 (R1 repair of P-15, base verified)",
                "P-21-R1 (R1 repair of P-21, base verified)",
                "P-22-R1 (R1 repair of P-22, base verified)",
                "P-24 (entirely new, NOT verified)",
                "P-26 (entirely new, NOT verified)",
                "P-27-R1 (R1 repair of hypothetical P-27, NOT verified)",
                "P-28 (entirely new, NOT verified)",
                "P-29 (entirely new, NOT verified)"
            ],
            "packages_killed_in_later_round": ["P-10", "P-12", "P-20"]
        },

        "packages": packages,
        "package_provenance": package_provenance,

        "r332_authority": r332_authority,
        "r332_timestamp": r332_timestamp,
    }

    # Write
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(honest_canonical, f, indent=2, ensure_ascii=False)

    print(f"Honest canonical written to: {OUTPUT_PATH}")
    print(f"  Packages: {len(packages)}")
    print(f"  Verified against R332 repo: 13")
    print(f"  From conversation summary (R1 repairs with verified base): 3")
    print(f"  From conversation summary (entirely new, NOT verified): 5")
    print(f"  Killed in later round (kept for traceability): 3")

    return honest_canonical


if __name__ == "__main__":
    rebuild()
