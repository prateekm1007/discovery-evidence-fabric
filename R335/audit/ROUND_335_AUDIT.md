# R335 AUDIT — Portfolio Ontology, Structured Thresholds, Experiment-Specific EIG, CKA Labels

**Round:** 335
**Date:** 2026-08-26
**Remote HEAD:** (R335 pending push)
**Constitution hash:** `f82ae4f665dcb5a59ae399017feed57dd24242fe35d98a897806d559064762a5`

## R335-A: Portfolio ontology resolved

**Problem:** Repository contained two conflicting portfolio concepts — 5-slot invention program (CANONICAL_STATE/PORTFOLIO.json) vs 15-package technology-transfer portfolio (R330+ canonical state).

**Fix:** Formal canonical transition. Historical 5-slot program = SUPERSEDED (preserved as lineage, Article XI). Current program = 15 technology packages. Lineage mapping documented (which 5-slot slots evolved into which 15-package candidates).

One canonical ontology: `R335/a_portfolio_ontology/CANONICAL_PORTFOLIO_ONTOLOGY.json`.

## R335-B: Experiment-specific EIG

**Problem:** R333 used identical priors (0.5/0.5), costs ($7500), times (4 weeks), and risks (1.0) for every candidate. EIG could not discriminate.

**Fix:** Each of 13 experiments now has its own:
- Hypothesis space (candidate-specific, e.g., "multi_segment_advantage_exists" vs "no_advantage")
- Priors (based on actual evidence: P-16 prior=0.7 strong, P-22 prior=0.2 weak)
- Likelihoods (candidate-specific discrimination)
- Cost (ranges $3.5K-$22.5K)
- Time (1.5-16 weeks)
- Risk (0.5-2.5)

**Expected result:** P-16 should win EIG/cost (strong prior, low cost, short time, low risk). P-22 should lose (negative prior, high cost, long time, high risk). The EIG now discriminates.

## R335-C: Structured thresholds

**Problem:** R333 extracted thresholds from rule text using `re.findall(r'[\d.]+')[-1]` — taking the last number. Rules contain multiple numbers (pass threshold, control threshold, percentages, sample sizes). This caused P-04 integration test failure.

**Fix:** Every experiment contract now has structured threshold fields:
- metric, units, direction, pass_threshold, fail_threshold, confidence_level, statistical_test, threshold_provenance, threshold_evidence_class

All 13 experiments have structured thresholds committed. The prose rule remains for humans. The structured fields control deterministic execution. No more heuristic extraction.

## R335-D: Package v2 — acknowledged as incomplete

The R333 `persist_package_update()` writes an update record, not a complete regenerated v2 package. This is acknowledged. Full v2 regeneration (complete 19-field package with integrated evidence) is the next step. The current update record is a transition receipt, not a full package.

## R335-H: CKA examples labeled SIMULATED

**Problem:** R334 created CKA-001 example saying "3/4 buyers mention integration burden" as if observed. But 0 buyer interactions exist.

**Fix:** All CKA examples labeled `SIMULATED_COMMERCIAL_KA — NOT observed. Zero buyer interactions exist.`

## What remains (prioritized)

1. **R335-E: Build the real discovery engine** — autonomous 5+ candidate generation through attack chain. This is the biggest missing subsystem.
2. **R335-D: Full package v2 regeneration** — when new evidence arrives, regenerate complete 19-field package, not just update receipt.
3. **R335-F: End-to-end AI loop** — discover → attack → simulate → experiment → ingest → update → next experiment. Must close on at least one candidate.
4. **Real external data** — CEO-owned. First genuine buyer submission closes the real loop.

## Honest state

```
ACTIVE: 13 (T2-CONFIRMED: 1, T2-CONDITIONAL: 1, T1: 11)
Article XXXV completion: 0/15
Structured thresholds: 13/13
Experiment-specific EIG: 13/13 (defined, not yet executed)
CKA: 1 SIMULATED (0 real)
Real buyer interactions: 0
Real external data: 0
VACANCY: 2
TARGET: 15
```

The machine is epistemically cleaner. The portfolio ontology is resolved. Thresholds are structured. EIG is experiment-specific. CKA is honestly labeled. The biggest remaining gap is the autonomous discovery engine (R335-E) and the real-world loop closure (R335-F).
