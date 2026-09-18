# B4 Diversity-Adapter Design (R510) — records-only; code gated on funnel

## Promotion design (`candidate_diversity.py` 1.1.0 → adapter)

- Keep the 5 recorded angles (`cross_industry_transfer`, `mechanism_inversion`,
  `simplification`, `multi_physics_hybrid`, `constraint_first`); angle injection
  stays explicit and logged (no solution-class smuggling — Art. XLIII).
- Grid stays angle × provider with one pinned path per provider and
  `max_preference_fallback=0` (independence is structural, Art. XLV).
- Counting switches to the R506 rule verbatim: DISTINCT-only from
  `mechanism_space.deduplicate_candidates` (`mechanism_distinctness/2.0.0`,
  Jaccard merge 0.8 / distinct floor 0.45); INDETERMINATE retained visibly,
  never counted (Art. XLVIII/XXV); grid-advanced never counted (Art. LXXVIII).
- Mechanical entry mapping (no invented content): intervention,
  predicted_effect, novel_design_variable, known_failure_modes,
  constraint_set.boundary_conditions ← grid `fields`; empty dims stay empty so
  thin pairs type INDETERMINATE honestly.
- Adapter bars (from `evaluate_diversity`, unchanged): ≥10 usable, ≥3 clusters,
  mean distance ≥0.6, rewrites < n//2. Dry-run acceptance: median DISTINCT ≥3
  over 3 R458-DEV problems (B1/E1/F1; never the scored battery).

## Dry-run result (measured, infra-blocked — Art. LXI)

`R510/DIVERSITY_DRYRUN.json`: all three problems `PROVIDER_UNAVAILABLE`,
usable 0, DISTINCT 0, acceptance false. Cause, typed: this container holds no
`XKIRO_API_KEY` (the grid's local transport needs a ring key in env), and the
only held model credential (`HF_TOKEN`) is 402-blocked by standing measurement
(R463/R495). No production diversity endpoint exists (server.py carries only
`/api/ops/calibration-attack` and `/api/ops/a2-attack`), so server-side keys
cannot serve the grid either. This is a measurement gap, not an adapter defect:
the mapping + adjudicator path is code-complete and import-clean; the generator
leg needs a holding container with a credited ring key (owner ask stands, Part 3).

## Gating

Adapter code executes iff the funnel names candidate starvation (Part 1.4).
Until then this design + the honest zero-record are the deliverable.
