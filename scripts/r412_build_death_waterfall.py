#!/usr/bin/env python3
"""Build R412/R412_DEATH_CAUSE_WATERFALL.json — the Phase 2 deliverable.

Classifies all 14 R411 deaths by PRIMARY death cause per the R412
taxonomy, records per-candidate death evidence (candidate_id, operator,
domain, death_stage, death_reason, evidence_ids, attacker_basis), makes
the counts reconcile EXACTLY with the frozen R411 funnel, and explains
the engineering-gated=28 denominator (measured: 14 unique ids x 2
append sites in the resumable state machine).

Classification method (Art. II: exact evidence): for each candidate the
PRIMARY cause is read from the attacker's own recorded
final_objection ('the single most dangerous surviving objection') and,
where that block carried no narrative (three candidates — a recorded
attacker-output defect), from the first kill-surface basis. Every
classification carries the verbatim basis text it was made from.
"""
import json
from collections import Counter
from pathlib import Path

REPO = Path("/home/z/my-project/audit_ws/repo")
RUN = REPO / "R411" / "DISCOVERY_RUN"
EV = json.loads(Path(
    "/home/z/my-project/scripts/r412_death_evidence.json").read_text())

# Primary death-cause classification, each with the recorded basis.
# source: 'final_objection' = the attacker's own most-dangerous-objection
# text; 'kill_surface' = the named kill surface whose basis text carries
# the cause (used where the final_objection block was bare 'KILLED').
CLASSIFICATIONS = {
    "C-batteries_ev-1": {
        "death_cause": "physics",
        "death_reason":
            "Dimensionally invalid Nusselt correlation (RHS units "
            "m^-1.5 s^-1.5, not dimensionless) AND regime mismatch "
            "(20-100 kHz in 2-10 mm channels places the geometry in the "
            "incompressible-oscillation regime where streaming is "
            "confined to thin boundary layers — bulk convective "
            "enhancement cannot follow).",
        "source": "kill_surface:equations (final_objection block was "
                  "bare 'KILLED' — recorded attacker-output defect)",
        "secondary_causes": ["evidence", "prior_art", "mechanism",
                             "engineering"],
    },
    "C-batteries_ev-1~3": {
        "death_cause": "engineering",
        "death_reason":
            "Killer experiment conflates thermal uniformity (a "
            "geometric/ballast effect) with acoustic-streaming-driven "
            "convection — the proposed test cannot falsify the mechanism "
            "even if the apparatus were built (Art. LII violation).",
        "source": "final_objection",
        "secondary_causes": ["mechanism", "baseline"],
    },
    "C-carbon_capture-2~3": {
        "death_cause": "prior_art",
        "death_reason":
            "doi:10.1021/acs.energyfuels.5c04026 already teaches "
            "amino-acid-mediated CO2 conversion to solid carbonate at "
            "industrial scale — the candidate reduces to a routine "
            "glycine-for-generic-amine substitution.",
        "source": "final_objection",
        "secondary_causes": ["evidence"],
    },
    "C-carbon_capture-7~3": {
        "death_cause": "prior_art",
        "death_reason":
            "Killed by lack of novelty (the underlying heat-integration "
            "physics is real and partially effective — the attack "
            "explicitly concedes the physics), plus lack of primary "
            "evidence and unquantified prediction.",
        "source": "final_objection",
        "secondary_causes": ["evidence"],
    },
    "C-chemical_process-1~3": {
        "death_cause": "physics",
        "death_reason":
            "Equations provide no controller dynamics, so the claimed "
            "40-70% waste reduction is mathematically ungrounded — the "
            "candidate cannot be validated, falsified, or scaled from "
            "the stated mathematics.",
        "source": "final_objection",
        "secondary_causes": ["evidence", "prior_art"],
    },
    "C-chemical_process-5~3": {
        "death_cause": "evidence",
        "death_reason":
            "All three evidence records are Chulalongkorn University "
            "graduate theses (2006-2007), not peer-reviewed literature; "
            "no archival control-journal record supports the adaptive-"
            "control claim.",
        "source": "kill_surface:evidence (final_objection block was bare "
                  "'KILLED' — recorded attacker-output defect)",
        "secondary_causes": [],
    },
    "C-data_center_thermal-1~2": {
        "death_cause": "prior_art",
        "death_reason":
            "Prior-art self-cancellation: the candidate's own evidence "
            "record (doi:10.1016/j.applthermaleng.2026.132277) is "
            "identical in mechanism, intervention, application, and "
            "effect to what is being proposed.",
        "source": "final_objection",
        "secondary_causes": ["evidence"],
    },
    "C-heat_exchanger-1~4": {
        "death_cause": "physics",
        "death_reason":
            "The physics kill: Darcy's law as cited is invalid at the "
            "stated Re > 4000 operating point, and the realistic "
            "delta-P penalty for any porous insert that delivers "
            "meaningful Nu enhancement makes the technology "
            "thermodynamically inferior to the established alternatives.",
        "source": "final_objection",
        "secondary_causes": ["prior_art", "evidence"],
    },
    "C-machining-1~4": {
        "death_cause": "physics",
        "death_reason":
            "Boundary-condition inversion: the candidate's own stated "
            "materials (SS304, Ti-6Al-4V) contradict its own stated "
            "effectiveness rule — even if the underlying cryogenic-"
            "cooling effect were real, the stated rule fails for the "
            "stated materials.",
        "source": "final_objection",
        "secondary_causes": ["engineering"],
    },
    "C-power_electronics-1": {
        "death_cause": "baseline",
        "death_reason":
            "The candidate's own Esw equation shows the absolute "
            "switching-loss benefit of DPWM is smallest precisely at the "
            "light loads (0.3-0.6 pu) where the candidate claims it is "
            "most effective — the baseline-advantage claim inverts at "
            "its own claimed operating point.",
        "source": "final_objection",
        "secondary_causes": ["physics"],
    },
    "C-power_electronics-6~2": {
        "death_cause": "prior_art",
        "death_reason":
            "Self-defeating evidence: the candidate's own cited IEEE "
            "Access 2023 record (doi:10.1109/access.2023.3291339) "
            "already implements the exact proposed intervention, "
            "eliminating novelty; the residual 10-20% efficiency claim "
            "is physically impossible against the P_max = G*A*eta "
            "ceiling of any functioning MPPT baseline.",
        "source": "final_objection",
        "secondary_causes": ["physics", "evidence"],
    },
    "C-semiconductor_fab-7~4": {
        "death_cause": "prior_art",
        "death_reason":
            "Prior-art anticipation: six independent CMP records "
            "(notably doi:10.31274/etd-180810-313 and "
            "doi:10.1016/b978-0-12-821791-7.00099-x) already teach "
            "MRR-variation modeling for CMP process control with richer "
            "dynamics than the candidate's ARX proposal.",
        "source": "final_objection",
        "secondary_causes": ["mechanism"],
    },
    "C-wind-2": {
        "death_cause": "engineering",
        "death_reason":
            "Intervention not controllable in service: wind turbine main "
            "shaft deflections under operational loads exceed installed "
            "misalignment tolerances by 10-100x (mm-scale shaft sag vs "
            "micron-scale assembly alignment) — a static 'engineered' "
            "misalignment is not a maintainable state in service.",
        "source": "kill_surface:intervention (final_objection block was "
                  "bare 'KILLED' — recorded attacker-output defect)",
        "secondary_causes": ["evidence"],
    },
    "C-wind-2~2": {
        "death_cause": "prior_art",
        "death_reason":
            "doi:10.1109/eic63069.2025.11123235 and "
            "doi:10.1109/eic63069.2025.11123384 directly teach "
            "electrical signature analysis for wind turbine defect "
            "detection in 2025, destroying the novelty claim.",
        "source": "final_objection",
        "secondary_causes": ["evidence"],
    },
}

TAXONOMY = ["problem_premise", "evidence", "mechanism", "prior_art",
            "physics", "baseline", "engineering", "attack", "other"]


def main() -> int:
    state = json.loads((RUN / "STATE.json").read_text())
    run = json.loads((REPO / "R411" / "R411_DISCOVERY_RUN.json").read_text())
    funnel = json.loads((RUN / "funnel_collision.json").read_text())

    # ---- per-candidate entries ----
    entries = []
    for c in EV:
        cid = c["candidate_id"]
        cls = CLASSIFICATIONS[cid]
        xdom = c.get("cross_domain_transition") or "NONE"
        operator = ("CROSS_DOMAIN_ANALOGY" if xdom.strip().upper() != "NONE"
                    else "DIRECT_TRANSFER")
        # first kill surface basis = attacker_basis verbatim
        kb = c.get("kill_surface_bases") or {}
        first_kill = (c.get("kill_surfaces") or [None])[0]
        basis = kb.get(first_kill, "") or str(c.get("final_objection") or "")
        entries.append({
            "candidate_id": cid,
            "technology_name": c.get("technology_name"),
            "operator": operator,
            "operator_basis": {
                "r411_generation_call": c.get("pain_class"),
                "cross_domain_transition": xdom,
                "five_operator_mapping_rule":
                    "cross_domain_transition != NONE -> CROSS_DOMAIN_"
                    "ANALOGY; NONE -> DIRECT_TRANSFER (mapping over the "
                    "frozen extraction record's own fields; the R411 "
                    "campaign generated via pain-class extraction calls, "
                    "not the five mechanism_space operators — recorded "
                    "honestly, not retrofitted)",
            },
            "domain": c.get("domain_id"),
            "death_stage": "attack (F7 adversarial tournament)",
            "death_cause": cls["death_cause"],
            "death_reason": cls["death_reason"],
            "classification_source": cls["source"],
            "secondary_causes": cls["secondary_causes"],
            "kill_surfaces": c.get("kill_surfaces"),
            "evidence_ids": sorted(set(
                (c.get("evidence_refs") or []) +
                (c.get("attack_evidence_ids") or []))),
            "attacker_basis": basis[:600],
            "attacker_independence_mode": "SEPARATE_PROVIDER",
            "reviewer_provenance": "AI_REVIEW",
        })

    # ---- cause distribution (must sum to the funnel's 14 deaths) ----
    counts = Counter(e["death_cause"] for e in entries)
    distribution = {k: counts.get(k, 0) for k in TAXONOMY}

    # ---- funnel reconciliation (exact, from the frozen artifacts) ----
    n_extr_rej = run["candidate_rejections"]["extraction_gate_rejected"]
    raw = funnel["raw_accepted_from_extraction"]
    med = funnel["medical_excluded_count"]
    col = funnel["collision_rejected_count"]
    ded = funnel["dedup"]
    surv = funnel["survivor_count"]
    eng_list = state.get("engineering_done", [])
    eng_unique = sorted(set(eng_list))
    eng_dupes = {k: v for k, v in Counter(eng_list).items() if v > 1}

    shortlist = json.loads((RUN / "shortlist.json").read_text())
    scored = json.loads((RUN / "scored_pool.json").read_text())
    n_finalist = sum(1 for c in scored
                     if (c.get("scoring") or {}).get("finalist_eligible"))
    # recorded evidence_subset + shortlist from STATE
    n_subset = len(state.get("evidence_subset_ids", []))
    n_short = len(state.get("shortlist_ids", []))

    assert (raw - med - col - len(ded.get("merge_events") or [])) == surv, \
        "funnel arithmetic does not reconcile"

    waterfall = {
        "artifact_type": "R412_DEATH_CAUSE_WATERFALL",
        "run_id": "r412:death-cause-waterfall",
        "subject_run": run["run_id"],
        "subject_engine_commit": run["engine_commit"],
        "created_in": "R412",
        "reviewer_provenance": "AI_REVIEW",
        "taxonomy": TAXONOMY,
        "classification_method": (
            "primary cause read from the attacker's recorded "
            "final_objection ('the single most dangerous surviving "
            "objection'); where that block was bare 'KILLED' (three "
            "candidates — a recorded attacker-output defect), from the "
            "first kill-surface basis. Every classification carries its "
            "verbatim basis and its source. Secondary causes recorded "
            "where the tournament killed on multiple surfaces."),
        "n_deaths": len(entries),
        "death_cause_distribution": distribution,
        "distribution_sums_to_deaths": sum(distribution.values()) == 14,
        "zero_count_causes": [k for k, v in distribution.items() if v == 0],
        "zero_count_note": (
            "No problem_premise, mechanism, attack, or other deaths: the "
            "problem-premise framing was attacked on two candidates and "
            "HELD both times; every R411 death traces to a downstream "
            "technical cause. This is a property of THIS run's funnel, "
            "not a general property of the space (Art. XXV)."),
        "deaths": entries,
        "funnel_reconciliation": {
            "extraction_gate_rejected": n_extr_rej,
            "extraction_attempts": raw + n_extr_rej,
            "extraction_denominator_note":
                "extraction_gate_rejected is counted over extraction "
                f"ATTEMPTS ({raw + n_extr_rej}), not over accepted "
                f"candidates ({raw}) — it is NOT a subtraction term "
                "between raw_accepted and survivors",
            "raw_accepted_from_extraction": raw,
            "medical_excluded": med,
            "medical_denominator": raw,
            "collision_rejected": col,
            "collision_denominator": raw - med,
            "dedup_merged": len(ded.get("merge_events") or []),
            "dedup_indeterminate_pairs": len(
                ded.get("indeterminate_pairs") or []),
            "dedup_semantics_note":
                "dedup_indeterminate_pairs counts PAIRS referred to "
                "collision adjudication (recorded, never merged) — it "
                "removes ZERO candidates and is NOT a subtraction term; "
                "dedup_merged is the only subtraction term",
            "candidate_survivors": surv,
            "survivors_identity": (
                f"{raw} - {med} - {col} - "
                f"{len(ded.get('merge_events') or [])} = {surv}"),
            "evidence_resolved": len(state.get("evidence_resolution_done",
                                               [])),
            "finalist_eligible": n_finalist,
            "evidence_subset": n_subset,
            "shortlisted": n_short,
            "prior_art_searched": len(state.get("prior_art_done", [])),
            "engineering_gated_unique": len(eng_unique),
            "engineering_gated_as_recorded": len(eng_list),
            "engineering_gated_28_explanation": (
                f"the R411 run record reports engineering n_gated="
                f"{len(eng_list)} because the resumable state machine "
                f"APPENDS to engineering_done at TWO sites (the F6 "
                "pre-selection pass and run_selection's re-gate); the "
                f"list holds {len(eng_unique)} unique ids, each appended "
                f"exactly {max(Counter(eng_list).values())}x "
                f"(measured: {sorted(eng_dupes.items())[:2]}...; all 14 "
                "ids duplicated). The R412 fix: the report builder now "
                "counts UNIQUE ids and records the append sites "
                "(pinned by test); the frozen R411 record is NOT "
                "rewritten — this field is the authoritative "
                "explanation."),
            "attacked": len(state.get("attack_done", [])),
            "killed": sum(1 for e in entries),
            "selected": len(state.get("selected_ids", [])),
        },
        "funnel_arithmetic_verified": {
            "raw_minus_medical_minus_collision_minus_dedup_eq_survivors":
                (raw - med - col - len(ded.get("merge_events") or []))
                == surv,
            "deaths_eq_attacked": len(entries) == len(
                state.get("attack_done", [])),
            "deaths_eq_killed_verdicts": len(entries) == sum(
                1 for v in (run["attacker_results"]["verdicts"] or
                            {}).values() if v == "KILLED"),
            "engineering_unique_eq_shortlist": len(eng_unique) == n_short,
            "selected_eq_zero": len(state.get("selected_ids", [])) == 0,
        },
    }

    assert all(waterfall["funnel_arithmetic_verified"].values()), \
        "waterfall funnel arithmetic failed its own verification"

    out_dir = REPO / "R412"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "R412_DEATH_CAUSE_WATERFALL.json"
    out.write_text(json.dumps(waterfall, indent=1))
    print(f"written: {out}")
    print("distribution:", {k: v for k, v in distribution.items() if v})
    print("all funnel checks:",
          waterfall["funnel_arithmetic_verified"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
