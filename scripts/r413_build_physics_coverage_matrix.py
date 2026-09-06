#!/usr/bin/env python3
"""r413_build_physics_coverage_matrix.py — the Phase 2 coverage matrix
(operator directive V2).

WHAT THIS MEASURES (the operator's four required outputs, over the
currently dead R411/R412 mechanisms):
  1. candidate count by physics domain
  2. percentage currently simulatable
  3. percentage currently terminating as MECHANISM_NOT_SIMULATABLE
  4. expected candidates unlocked by each missing domain

POPULATION (disclosed, no silent scope choice — Art. XXVII):
  - ALL_DEAD (400): every candidate in the R411 scored pool. The R411
    campaign ended with 0 survivors; all 400 are currently dead
    (386 killed pre-shortlist + 14 with final technical adjudication).
  - ADJUDICATED (14): the shortlist deaths, whose primary cause is
    recorded in R412/R412_DEATH_CAUSE_WATERFALL.json.
  - R412_SEEDS (10): the gradient-arm seeds re-attempted 10 of the 14
    (same candidate_ids, verified live from ga3.jsonl) and died AGAIN
    at the upstream retrieval-evidence gate (DEAD_AT_TVM_QUERY). These
    are NOT an additional population — they are re-attempts of R411
    dead candidates whose blocker is retrieval evidence (the
    retrieval-resilience round's domain), NOT physics coverage. No
    physics-domain unlock is attributed to them.

DEATH ATTRIBUTION for "expected candidates unlocked": a dead candidate
is unlock-attributable only if its recorded death cause is technical
in the sense that computational validation could plausibly change the
outcome: physics, engineering, or baseline. prior_art and evidence
deaths are NOT unlockable by physics (novelty and evidence gaps are
not solver problems). This attribution rule is declared here, before
the computation.

CALIBRATION LOG (instrument honesty, Art. XV): the classifier's term
vocabulary was calibrated ONCE against the corpus BEFORE this matrix
was frozen, fixing seven disclosed false-positive families (power
flow, electrical load, harmonic distortion, unit-lookalike K,
light-load, unqualified efficiency, loss-reduction-as-chemistry,
acoustic-absorption-as-sorption). The classification RULE
(>=2 distinct terms = mechanism-level evidence) was fixed before any
corpus run and was NOT revised.

Determinism: identical inputs -> byte-identical artifact (Art. LXII).
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.physics_stack.mechanism_physics import (  # noqa: E402
    classify_mechanism, PHYSICS_DOMAINS, MULTIPHYSICS, UNKNOWN,
    MECHANISM_TEXT_FIELDS, STRONG_EVIDENCE_MIN_DISTINCT_TERMS,
)
from discovery_fabric.physics_stack.coverage import (  # noqa: E402
    load_coverage_registry, simulatable_phenomena,
)

OUT_PATH = (REPO / "R413" / "PHYSICS_STACK_V1"
            / "PHYSICS_COVERAGE_MATRIX_V1.json")
BUILD_DATE = "2026-09-06"

#: death causes under which computational validation could plausibly
#: change the outcome (declared before the computation).
UNLOCKABLE_DEATH_CAUSES = ("physics", "engineering", "baseline")

SCORED_POOL = REPO / "R411" / "DISCOVERY_RUN" / "scored_pool.json"
WATERFALL = REPO / "R412" / "R412_DEATH_CAUSE_WATERFALL.json"
GA3 = REPO / "R412" / "GRADIENT_V2" / "RUN" / "ga3.jsonl"


def main() -> None:
    pool = json.loads(SCORED_POOL.read_text())
    waterfall = json.loads(WATERFALL.read_text())
    ga3 = [json.loads(l) for l in GA3.read_text().splitlines() if l.strip()]

    deaths = {d["candidate_id"]: d for d in waterfall["deaths"]}
    shortlist_ids = set(deaths)
    pool_ids = {c["candidate_id"] for c in pool}
    seed_ids = {g["candidate_id"] for g in ga3}

    # population cross-checks (fail closed on surprises)
    assert shortlist_ids <= pool_ids, "shortlist not subset of pool"
    assert seed_ids <= pool_ids, "R412 seeds not subset of R411 pool"
    assert all(g["verdict"] == "DEAD_AT_TVM_QUERY" for g in ga3), \
        "unexpected R412 seed verdict"

    registry = load_coverage_registry()
    sim = simulatable_phenomena(registry)
    simulatable_phenomenon_set = set(sim["simulatable"])

    classifications = []
    for c in sorted(pool, key=lambda x: x["candidate_id"]):
        cls = classify_mechanism(c)
        pheno = list(cls["phenomenon_evidence"])
        sim_now = (bool(pheno)
                   and all(p in simulatable_phenomenon_set
                           for p in pheno))
        missing = sorted(p for p in pheno
                         if p not in simulatable_phenomenon_set)
        d = deaths.get(c["candidate_id"])
        classifications.append({
            "candidate_id": c["candidate_id"],
            "technology_name": c.get("technology_name"),
            "domain_id": c.get("domain_id"),
            "pain_class": c.get("pain_class"),
            "physics_domain": cls["domain"],
            "strongly_evidenced": cls["strongly_evidenced"],
            "weakly_evidenced": cls["weakly_evidenced"],
            "phenomena_evidenced": pheno,
            "simulatable_now": sim_now,
            "missing_phenomena": missing,
            "death": None if d is None else {
                "cause": d["death_cause"],
                "stage": d.get("death_stage"),
                "secondary_causes": d.get("secondary_causes", []),
                "kill_surfaces": d.get("kill_surfaces", []),
            },
            "unlock_attribution": None if d is None else (
                "PHYSICS_RELEVANT" if d["death_cause"]
                in UNLOCKABLE_DEATH_CAUSES else "NOT_PHYSICS_RELEVANT"),
            "r412_seed_reattempt": c["candidate_id"] in seed_ids,
        })

    n = len(classifications)
    n_adjudicated = sum(1 for r in classifications if r["death"])
    n_sim_now = sum(1 for r in classifications if r["simulatable_now"])
    n_not_sim = n - n_sim_now
    # untyped physics: no phenomenon evidence at all
    n_untyped = sum(1 for r in classifications
                    if not r["phenomena_evidenced"])

    domain_counts = Counter(r["physics_domain"]
                            for r in classifications)
    adjudicated_domain_counts = Counter(
        r["physics_domain"] for r in classifications if r["death"])

    # ---- expected candidates unlocked by each missing domain -------
    # full unlock: single-domain mechanism whose domain is X
    # partial unlock: multiphysics mechanism evidencing X among its
    # strong domains (a combination is needed; X alone insufficient)
    unlock = {}
    for dom in PHYSICS_DOMAINS:
        full_all = [r["candidate_id"] for r in classifications
                    if r["physics_domain"] == dom]
        full_adj = [r["candidate_id"] for r in classifications
                    if r["physics_domain"] == dom
                    and r["unlock_attribution"] == "PHYSICS_RELEVANT"]
        partial_all = [r["candidate_id"] for r in classifications
                       if r["physics_domain"] == MULTIPHYSICS
                       and dom in r["strongly_evidenced"]]
        partial_adj = [r["candidate_id"] for r in classifications
                       if r["physics_domain"] == MULTIPHYSICS
                       and dom in r["strongly_evidenced"]
                       and r["unlock_attribution"] == "PHYSICS_RELEVANT"]
        unlock[dom] = {
            "full_unlock_all_dead": len(full_all),
            "full_unlock_adjudicated": len(full_adj),
            "full_unlock_adjudicated_ids": full_adj,
            "partial_unlock_multiphysics_all_dead": len(partial_all),
            "partial_unlock_multiphysics_adjudicated": len(partial_adj),
            "partial_unlock_adjudicated_ids": partial_adj,
            "note": "full unlock = single-domain mechanisms whose "
                    "domain is X (the mechanism becomes simulatable "
                    "once domain X has a validated solver); partial = "
                    "multiphysics mechanisms needing X among others "
                    "(X alone is insufficient — a combination is "
                    "required, priced per-solver by the opportunity "
                    "score)",
        }

    # phenomenon-level gap counts (what the router actually hits)
    phenomenon_gap = Counter()
    for r in classifications:
        for p in r["missing_phenomena"]:
            phenomenon_gap[p] += 1

    # unknowns stay unknown, listed (Art. XXV)
    unknown_ids = [r["candidate_id"] for r in classifications
                   if r["physics_domain"] == UNKNOWN]

    doc = {
        "artifact_type": "R413_PHYSICS_COVERAGE_MATRIX_V1",
        "version": "1.0.0",
        "directive": "operator directive V2 (OPERATOR_DIRECTIVE_V2.json) "
                     "Phase 2: the coverage matrix that determines which "
                     "solver gets built next",
        "population": {
            "all_dead": {
                "n": n,
                "source": "R411/DISCOVERY_RUN/scored_pool.json",
                "definition": "every candidate of the R411 cross-domain "
                              "campaign (0 survivors; 386 pre-shortlist "
                              "rejections + 14 final adjudicated deaths)",
            },
            "adjudicated": {
                "n": n_adjudicated,
                "source": "R412/R412_DEATH_CAUSE_WATERFALL.json",
                "definition": "deaths with recorded final technical "
                              "adjudication (the shortlist)",
            },
            "r412_seeds": {
                "n": len(seed_ids),
                "source": "R412/GRADIENT_V2/RUN/ga3.jsonl",
                "definition": "re-attempts of 10 of the 14 dead "
                              "candidates (same candidate_ids, verified "
                              "live); ALL died DEAD_AT_TVM_QUERY at the "
                              "upstream retrieval-evidence gate — a "
                              "pre-physics blocker owned by the "
                              "retrieval-resilience round; NO physics "
                              "unlock is attributed to them",
            },
            "unlock_attribution_rule": {
                "physics_relevant_causes": list(
                    UNLOCKABLE_DEATH_CAUSES),
                "rationale": "computational validation could plausibly "
                             "change the outcome for physics/engineering/"
                             "baseline deaths; prior_art and evidence "
                             "deaths are not solver problems",
                "declared_before_computation": True,
            },
        },
        "classifier": {
            "module": "discovery_fabric/physics_stack/"
                      "mechanism_physics.py",
            "deterministic": True,
            "llm_calls": 0,
            "classification_rule": {
                "strong_evidence_min_distinct_terms":
                    STRONG_EVIDENCE_MIN_DISTINCT_TERMS,
                "multiphysics_rule": ">=2 strongly-evidenced domains",
                "unknown_rule": "no domain evidence",
                "fixed_before_corpus_run": True,
            },
            "mechanism_fields_read": list(MECHANISM_TEXT_FIELDS),
            "calibration_log": [
                "disclosed instrument calibration BEFORE this matrix "
                "freeze (Art. XV): seven false-positive families fixed "
                "in the term vocabulary — (1) 'power flow' (electrical) "
                "as hydraulic flow [negative lookbehinds]; (2) bare "
                "'load'/'load current' (electrical) as structural load "
                "[mechanical-context qualifier]; (3) 'harmonic "
                "distortion' (electrical) as structural vibration "
                "[harmonic removed]; (4) unit-lookalike K in "
                "'W/m^2*K' as permeability [lookalike removed]; (5) "
                "'light load' as optical light [contextual pattern]; "
                "(6) unqualified 'efficiency limitations' / bare eta as "
                "thermal efficiency [thermal qualifier required]; (7) "
                "'loss reduction' (engineering) and 'acoustic "
                "absorption' as chemistry/sorption [reduction/absorpt "
                "restricted to electrochemical/adsorptive contexts]. "
                "The classification RULE was fixed before any corpus "
                "run and NOT revised.",
                "POST-FREEZE INSTRUMENT DEFECT FOUND BY THE ADVERSARIAL "
                "TEST BATTERY (disclosed, Art. XV/XVI): bare "
                "'concentration' matched the chemical rule — 'stress "
                "concentration' (structural language) was leaking "
                "chemical_quantity evidence. Fixed (concentration now "
                "requires molar/gradient/chemical context) and the "
                "matrix RE-MEASURED in the same round (the artifact "
                "enters git once, in its final measured state, with "
                "the full calibration history disclosed; the "
                "classification rule itself was never revised).",
            ],
        },
        "the_four_operator_outputs": {
            "candidate_count_by_physics_domain": {
                "all_dead_400": dict(domain_counts),
                "adjudicated_14": dict(adjudicated_domain_counts),
            },
            "percentage_currently_simulatable": {
                "phenomenon_level": round(100.0 * n_sim_now / n, 2),
                "n_simulatable": n_sim_now,
                "n_total": n,
                "basis": "a mechanism is simulatable iff it has "
                         "phenomenon evidence AND every evidenced "
                         "phenomenon is simulatable today (registry "
                         "validated + solver installed); the registry's "
                         "only validated phenomenon is "
                         "laminar_incompressible_network_flow",
                "domain_level_note": "hydraulic-domain mechanisms "
                                     "(45/400) are domain-covered in "
                                     "principle but only those whose "
                                     "evidenced phenomena bind to the "
                                     "validated V0 phenomenon count "
                                     "here — the router routes "
                                     "phenomena, not domains",
            },
            "percentage_terminating_as_MECHANISM_NOT_SIMULATABLE": {
                "phenomenon_level": round(100.0 * n_not_sim / n, 2),
                "n_not_simulatable": n_not_sim,
                "of_which_untyped_phenomena": n_untyped,
                "basis": "the deterministic router fails closed on any "
                         "missing phenomenon (MECHANISM_NOT_SIMULATABLE "
                         "with the domain/phenomenon named); this is a "
                         "forward-looking deterministic property of the "
                         "current registry — the R411 funnel itself "
                         "never routed through solver validation (the "
                         "V0 hydraulic solver was built for the "
                         "medical-device domain)",
            },
            "expected_candidates_unlocked_by_each_missing_domain":
                unlock,
        },
        "phenomenon_level_gap_counts": dict(phenomenon_gap),
        "unknown_mechanisms": {
            "n": len(unknown_ids),
            "ids": unknown_ids,
            "note": "UNKNOWN is a first-class honest output (Art. XXV); "
                    "these mechanisms' physics could not be read from "
                    "their own recorded fields and are NOT forced onto "
                    "neighboring domains",
        },
        "registry_state_at_measurement": {
            "simulatable": sim["simulatable"],
            "declared_not_validated": sim["declared_not_validated"],
            "n_solver_not_installed": len(sim["solver_not_installed"]),
            "registry_sha256_note": "PHYSICS_COVERAGE_REGISTRY_V1.json "
                                    "(built this round, 18 phenomena, "
                                    "1 validated regime)",
        },
        "per_candidate": classifications,
        "provenance": {
            "inputs": [
                str(SCORED_POOL.relative_to(REPO)),
                str(WATERFALL.relative_to(REPO)),
                str(GA3.relative_to(REPO)),
            ],
            "builder": "scripts/r413_build_physics_coverage_matrix.py",
            "build_date": BUILD_DATE,
            "determinism": "byte-identical on re-run from identical "
                           "inputs",
        },
        "reviewer_provenance": "AI_REVIEW",
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(doc, indent=1, ensure_ascii=False)
                        + "\n")
    digest = hashlib.sha256(OUT_PATH.read_bytes()).hexdigest()

    print(f"wrote {OUT_PATH}")
    print(f"sha256: {digest}")
    print(f"all_dead={n} adjudicated={n_adjudicated} "
          f"simulatable_now={n_sim_now} ({100.0*n_sim_now/n:.1f}%) "
          f"not_simulatable={n_not_sim} ({100.0*n_not_sim/n:.1f}%)")
    print("domain counts (all 400):", dict(domain_counts))
    print("domain counts (adjudicated 14):",
          dict(adjudicated_domain_counts))
    print("phenomenon gaps (top):",
          phenomenon_gap.most_common(8))
    print("unlock (adjudicated, full+partial):")
    for dom in PHYSICS_DOMAINS:
        u = unlock[dom]
        print(f"  {dom:16s} full={u['full_unlock_adjudicated']:2d} "
              f"partial={u['partial_unlock_multiphysics_adjudicated']:2d}")


if __name__ == "__main__":
    main()
