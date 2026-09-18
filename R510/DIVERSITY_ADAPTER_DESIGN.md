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

## Dry-run result, keyed run R510-C10 (measured — acceptance false, honestly)

`R510/DIVERSITY_DRYRUN.json` (overwrites the C9 infra-blocked record above, which
stands as history): grid GRID_RUN, usable 10/10/9 via operator-supplied ring
values (session-env only, cleared post-run; first-2-available xkiro,atria; no
exhaustion, no rung switch needed). n_distinct 1/1/1, rest INDETERMINATE, median
1 < 3 → acceptance FALSE.

Root cause (subagent-analyzed from code, falsifier named in
`R510/R510_C10_WORKLOG_ENTRY.md`): the adapter mapping omits `mechanism_graph`
(grid emits a MECHANISM field; mapping never converts it), so every pair takes
the `core_j None → INDETERMINATE` first branch; the first-kept baseline yields
exactly one DISTINCT deterministically. Verdict correct per XLII/XXV; adapter
defective for its purpose — it cannot pass its own bar without graph mapping.

Gated fix spec (code post-harvest/funnel only): parse grid MECHANISM text into
`mechanism_graph` nodes (causal variables + physics vocab as terms) and edge
signatures; then evidence-ground the grid so distinct papers supply disjoint
 vocab (richness in envelope fields alone has zero leverage on `core_j`).

## Gating

Adapter code executes iff the funnel names candidate starvation (Part 1.4).
Until then this design + the honest zero-record are the deliverable.
