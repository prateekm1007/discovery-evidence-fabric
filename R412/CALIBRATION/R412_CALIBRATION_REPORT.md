# R412 Attacker Calibration Report (P0-1)

**Run id:** `r412:attacker-calibration-v1`
**Date:** 2026-09-05
**Reviewer provenance:** `AI_REVIEW` (Art. LXVII — corpus authoring and attack
runs are both machine work; no human review is claimed)
**Verdict:** **NOT_CALIBRATED** — measured against the sealed,
pre-registered thresholds; nothing was tuned after the fact.

---

## 1. What was measured

The sealed 40-case corpus (`r412_attacker_calibration_corpus.json`,
sha-pinned by `r412_calibration_seal.json`, committed BEFORE any attack —
Art. VIII seal discipline) was attacked by the R411 attack instrument
(`discovery_fabric/r411/attack.py`, **unmodified**, exactly as it ran the
R411 campaign — Art. LIX):

| Cohort | n | Sealed expected outcome |
|---|---|---|
| KNOWN_GOOD | 10 | SURVIVED (related-but-non-colliding prior art by construction) |
| KNOWN_BAD | 10 | KILLED (Art. L minimum defect classes) |
| NEAR_MISS | 10 | KILLED (one specific defect: magnitude / regime / baseline inversion / service mismatch) |
| PRIOR_ART_COLLISION | 10 | KILLED on `prior_art` (the provided art teaches the same mechanism+intervention+effect) |

Three single-attacker passes were measured (NO ensemble, per the R412
directive):

| Pass | Model | Role | TPR | **FPR (false-kill on KNOWN_GOOD)** | Coverage | Parse | Verdict |
|---|---|---|---|---|---|---|---|
| minimax-m3 | `minimax/minimax-m3:free` (openrouter) | **primary** — the R411 campaign's operative attacker | 1.000 | **0.80** | 1.00 | 0.95 | NOT_CALIBRATED |
| glm-5.3-free | `z-ai/glm-5.3-free` (tokenrouter) | second-instrument ATTEMPT | — | — | 0.00 | — | transport failure (empty content at finish_reason=length — the same failure R411 recorded; the INCOMPLETE checkpoint line is kept as evidence) |
| glm-4-plus | `glm-4-plus` (zai local gateway) | second instrument — the R411 GENERATOR model measured as attacker | 0.967 | **1.00** | 1.00 | 0.98 | NOT_CALIBRATED |

Pre-registered thresholds (sealed before measurement): coverage >= 0.875,
parse >= 0.875, TPR >= 0.75, **FPR <= 0.30**.

Cross-model agreement (cases where BOTH passes were decisive):
**1.000 (37/37)** — the two instruments agree perfectly wherever both
deliver a verdict, and what they agree on is killing.

## 2. The finding

**Both instruments are universal killers on this corpus.**

- The primary (R411) attacker killed 30/30 defect cases AND 8/10
  known-good cases (the remaining 2 were non-decisive CONDITIONALs —
  one a kill-intent FINAL line with only WOUND-level surface verdicts,
  one an outright WOUNDED final).
- The generator-family model (glm-4-plus) killed 29/30 defect cases AND
  **10/10 known-good cases**.
- Agreement between them is perfect — the failure mode is
  **architectural, not model-specific**. The 8-surface
  "DESTROY this candidate" protocol reliably produces kills on any
  candidate constructed like a real (bounded, honestly-qualified)
  technology proposal.

The kills are NOT blanket skepticism: `expected_marker_in_basis_rate` is
**1.0 for both instruments** — every kill on a defect case cites the
sealed expected defect content in its basis. The instrument sees real
defects and real depth. It also sees "defects" in the known-good cases:
the false-kill bases cite Donnell–Mushtari shell theory vs 1D beam
idealization, salt mass balance in closed reservoirs, binary-vs-ternary
remixing in dividing-wall columns, and related-art-collision judgments
on the corpus's deliberately non-colliding prior art. These are
substantive objections an expert would have to adjudicate — which is
exactly the point of measuring specificity instead of assuming it.

## 3. What this re-contextualizes

1. **R411's 0/5 result (14/14 killed) is re-read as:** the attacker can
   say NO, and its NOs are substantively grounded — but an instrument
   that also kills 80–100% of known-good mechanisms cannot distinguish
   a bad campaign from a good one. R411's zero survivors is therefore
   NOT evidence that no good candidate existed; it is consistent with
   an instrument that would have killed a good candidate too.
   (The user's reframe — "a successful campaign with zero survivors" —
   stands, with this sharpened caveat: the campaign honestly reported
   what its instruments did; the instruments themselves are now
   measured to be non-selective.)
2. **The next discovery campaign must not run with this attacker as the
   final arbiter of quality.** Before any campaign, either (a) the
   attacker protocol is redesigned and re-measured on this corpus until
   FPR <= 0.30 at TPR >= 0.75, or (b) the attacker's kills are treated
   as *objections to answer* rather than terminal verdicts. Any such
   redesign is a new instrument version measured BEFORE the next
   campaign (Art. LIX: no tuning on this corpus — the corpus is now
   spent as a blind benchmark; a second sealed corpus is required for
   measuring instrument v2).
3. **Corpus honesty boundary:** the ground truth itself is
   `AI_REVIEW`-authored. The 8–10 known-good cases were built from
   textbook physics with honest bounds; the attackers' depth objections
   may be right that some cases are over-idealized. The per-case
   disagreement records (sealed ground-truth basis vs attacker basis,
   both verbatim, in `r412_attacker_measurement.json`) are precisely
   the material a human expert would adjudicate. Until then, both the
   "known-good" labels AND the kills remain AI claims.

## 4. Secondary measurements

- **Expected-surface citation:** kills cite the sealed
  `expected_kill_surface` only 46.7% (minimax) / 37.9% (glm-4-plus) of
  the time — kills happen via different routes than the ground truth
  predicts, even when the defect content is cited.
- **Bare-final defect (`KILLED: KILLED`):** 11/38 (minimax) and 18/39
  (glm-4-plus) kills had bare FINAL lines. The structured-death guard
  in the measurement harness backfills `specific_reason` from the
  kill-surface basis WITH DISCLOSURE (`fallback_used: true`); zero
  violations (no kill lacked both objection and basis). This pins the
  P1 directive: bare `KILLED` finals are a real, frequent instrument
  defect that future production artifacts must not inherit silently.
- **Instrument budget:** 40 cases x ~30 s (openrouter) / ~5 s (local
  gateway); 81 attack invocations total, 1 transport failure.

## 5. Artifacts

- `R412/CALIBRATION/r412_attacker_measurement.json` — the full
  measurement record (per-case verdicts, bases, hashes, confusion
  matrices, agreement, structured death records).
- `R412/CALIBRATION/runs/<pass>.jsonl` — per-case checkpoint evidence
  (append-only; every attempt, including the glm-5.3-free failure).
- `R412/CALIBRATION/calibration_metrics.py` — the measurement math
  (hermetically pinned by `tests/test_r412_attacker_measurement.py`).
- `R412/CALIBRATION/calibration_runner.py` — the live runner
  (preflight seal check, checkpointing, resumability, bounded retries).
- `scripts/r412_run_attacker_calibration.py` — the CLI driver.

## 6. Next steps (recorded, not executed)

1. **Attacker v2 protocol design** — the redesign goal is specificity:
  spare bounded, honestly-qualified mechanisms while still killing the
  30 defect cases. Candidate levers (to be designed on a DEVELOPMENT
  corpus, never this one): explicit decision rules distinguishing
  "defect that invalidates the claim" from "engineering objection the
  claim's bounds already absorb"; a related-art-vs-collision
  adjudication step; a kill-basis adequacy standard.
2. **A second sealed calibration corpus** for measuring v2 (this corpus
  is now spent as a blind instrument benchmark — Art. LIX).
3. Only after v2 measures FPR <= 0.30 at TPR >= 0.75: the re-run
   discovery campaign (the standing R412 stop condition remains: no new
   campaign until authorization green AND attacker calibrated).
