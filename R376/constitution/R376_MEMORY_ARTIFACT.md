# R376 Memory Artifact — Prior-Art Differentiation Cycle Defects

**Article XXXI record.** Three defects were found by adversarial testing
during the R376 cycle and fixed with pinned regression tests. Each is
recorded so future sessions cannot reintroduce it silently.

## Defect 1 — Folded tokens in search queries

- **Lesson:** the term-overlap machinery folds plurals
  ('prosthesis' -> 'prosthesi') for MATCHING; those folded forms must
  never enter SEARCH strings. Lens measured 0 hits for
  `title:(prosthesi ...)` — the fold is an internal comparison key, not
  a word.
- **Failed assumption:** "one tokenizer everywhere is simpler" — true
  for adjudication, false for providers.
- **Affected artifacts:** the first `build_query_ladder` implementation
  (fixed pre-merge); no shipped artifact carried folded queries.
- **Test added:** `test_natural_word_forms_not_folded`.

## Defect 2 — Coverage-denominator dilution (false anticipation)

- **Lesson:** the anticipation coverage ratio must be measured against
  the candidate's FULL element set (uncapped), not the 6-8 term query
  core. A capped denominator ranked the DOMAIN terms (battery, thermal,
  runaway — entity-anchored +3) into the set and crowded out the TRUE
  differentiators (acoustic, multi-modal), so a domain-only patent
  measured 0.857 coverage and produced a FALSE RESOLVED_ANTICIPATED —
  a kill-state from diluted math.
- **Failed assumption:** "the query core approximates the claim." A
  patent claim has ALL its elements; the query is a retrieval key.
- **Affected artifacts:** `coverage_decision` (fixed pre-merge);
  the adversarial battery fixture caught it before any production run.
- **Test added:** `test_domain_only_patent_cannot_anticipate` +
  `test_full_cover_resolves_anticipated` (true anticipation still fires).

## Defect 3 — Tuple-unpack crash in the grid candidate path

- **Lesson:** a helper whose return contract is "2-tuple" must ALWAYS
  return a 2-tuple. `_collision_for_candidate` returned a bare dict on
  success; the caller unpacked it as `a, b = helper()` which split the
  dict's KEYS — every grid candidate crashed with
  `TypeError: string indices must be integers, not 'str'` and the grid
  recorded GRID_ERROR 0-candidates on the FIRST fresh medical run.
- **Failed assumption:** "both return paths are shaped alike" — they
  were not (success: dict; failure: tuple).
- **Affected artifacts:** `ENGINE_RUNS/t6_medical_infusion_occlusion`
  (two scrapped fresh runs, archived under
  ENGINE_RUNS_ARCHIVE_R376_BEFORE/t6_medical_*); traceback capture added
  to the GRID_ERROR record so this class of failure is always
  diagnosable from the artifact alone.
- **Tests added:** `test_run_py_wires_collision_rerun` extended
  (source-level); the fresh six-domain campaign is the end-to-end
  evidence (all six grids GRID_RUN with per-candidate collisions).

## Standing lesson for the next cycle

Adversarial fixtures that CONSTRUCT the failure (a patent text built
from the candidate's own words) are the cheapest way to catch
semantic-math defects (Defect 2) before they become production kills.
The CEO's "do not lower the bar" discipline means every new
decision-producing metric needs its own false-positive fixture.
