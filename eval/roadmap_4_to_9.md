# ROADMAP 4 → 9 — where we are, where we're going

> Provenance (builder note, 2026-11-17): verbatim owner document,
> received 2026-11-17 with the R50 round-open instruction. The owner's
> message states the durable commit of this document + AM46 is queued
> for the next push-capable round (push tooling down that round); the
> plan is IN FORCE NOW. This file is that durable commit, staged by
> builder-r50s1. Nothing in this file is builder-authored except this
> header; the body is the owner's document as received.

## Where we are (verified, not claimed)

| Asset | State |
|---|---|
| Evaluation discipline | **Strong**: 7 holdouts sealed/burned; v6 VALID 2.583/4, v7 VALID 2.917/4 — both **wrapper** scores; power pre-registration, attestation, claim mutex, PRIVATE-rubric convention all working |
| The engine | `mechanism_space.py` **3,716 lines, 6 typed operators**, smoke 6/6 — **decided onto the measured path (ROUTE), not integrated**; accept/reject contract probe is weak |
| V8.0 binds | Verified (c-0060): structured extraction P/R 1.0 on labels, inferred-class cap (F58 closed), quantified pricing, 23 CI-wired tests |
| v8 packet | **DEV-only** — rubric public (F60: unauth HTTP 200), machine bumped mid-run + 23/30 rows (F62) |
| Custody | **Broken**: live PAT plaintext on `r448/visual-lab` (F45); rubrics public (F60). **Only remaining owner act** |
| CI | **RED at `a57972828`** — fix forward first |
| Judges | qwen-3.8-max **MET** (16/18 + 11/12); deepseek c-0043 re-calibration OPEN |
| Copy levers | License-verified: AIDE/triz-engine/GEPA/one-api/gitleaks/Inspect/CoolProp/ht/fluids/thermo/chemicals/tespy **MIT**; PySR/SPECTER2/SwanLab/PaddleScience/AgentScope **Apache-2.0**; MAPIE **BSD-3**; PaperBench from **openai/preparedness (MIT)**; telemanom NOASSERTION (read text before copying). **Never copy:** new-api (AGPL), EnvCommons (none), AutoTRIZ casebase (none), AI-Scientist-v2 (custom), jataware (Commons Clause) |

**Destination (9/10):** the engine rediscovers ≥40% of key mechanisms from ≥30 post-cutoff patents/papers, ≥1 candidate agent-validated (T1+T2), a 30-problem batch runs unattended with 0 human interventions — standing on two consecutive sealed sets ≥3.3 with the engine on the measured path.

---

## P0 — custody + scope (4 → 4.5) · 1–2 rounds · HARD PREREQUISITE for everything

**Gap:** rubrics + PAT public; CI red; all-refs scan not run.

1. **OWNER (one-time, parallel):** move/encrypt every `*_PRIVATE.json` to private custody (age/openssl, owner-held passphrase) + scrub public history; rotate the PAT and the 2 Aug-18 keys — treat every credential that touched public history as burned. After this, **auditor agents manage custody**; no further owner acts anywhere in the plan.
2. Fix the red CI at `a57972828` forward-only; quote the check-run API read in the round record (D2 rule).
3. **gitleaks over all 23 refs + full history** → committed enumeration report (exact branch+path set, F59 precision); detect-secrets pre-commit; wire both into CI. Do not baseline-away findings.
4. Measured-path ledger entry: **done** (`eval/measured_path_decision_r47.json`, ROUTE) — reference it from every future run ledger.

**Gate:** unauth probes + gitleaks find **0** plaintext rubrics/tokens on any public ref; measured path named; CI green API-read.

## P1 — make claims checkable (→ 5) · 3–5 rounds · the capability core

**Gap:** physics is LLM prose; scanners read prose; engine off the measured path.

1. **Computed physics layer** (engine code): add `pint` + CoolProp/ht/fluids/thermo/chemicals/tespy. Build `discovery_fabric/engine/physics_checks.py` — a registry of computable governing relations keyed by failure class (Arrhenius time-at-temperature integral, NPSH/surge margin, LSI scaling, frost psychrometrics, fouling U-degradation, Larson-Miller creep, COP/charge proxy…). Every intervention emits a **small typed calculation that actually runs in the sandbox**; **direction-of-effect = the sign of the computed result**, never prose.
2. **Structured output schema**: extend `mechanism_candidate/1.0.0` with enums — `measure_class` (problem's allowed measures), `signals_used` (permitted signals), `principle_id`, `mechanism_class`. Scanners read schema fields; **delete the prose-regex scanners** (F57/F58/F59) via the Art. 16 retirement ledger.
3. **Integrate the engine route** (F61 execution): `knowledge_first_item` anchors the problem → operator contracts → `assemble_candidate` → schema → `physics_checks` → binds. **Fix the weak C4 probe first**: real negative cases must be rejected by the contracts before any ablation claim.
4. Regression on labelled v6/v7 rows through the new path.

**Gate:** ≥80% of numeric claims run unit-checked; **0** allowed-measures violations, **0** false input-flags, **0** inverted directions on the labelled rows.

## P2 — generation quality (→ 6) · 3–5 rounds

**Gap:** single-chain generation defaults to duty-cycle templates; no novelty pressure; no accepted sealed set.

1. **TRIZ as our own JSON** (`discovery_fabric/engine/triz_matrix.json`): 39 parameters + 40 principles + contradiction matrix (reference triz-engine MIT data; NOTICE attribution). Problem → contradiction (improving vs worsening parameter) → candidate principles.
2. **Typed-operator population**: K≥3 short plans per intervention, each under a **different principle/operator**, plan-only schema; **expand only the winner**. Schedule family (dynamics/periodic/vibration) capped **1 per 6**. Diversity axes **computed, never LLM-judged** (QDAIF lesson).
3. **Cheap novelty gate**: TF-IDF cosine among candidates + vs accepted bills; reject above a pre-registered threshold; LLM judge only borderline (ShinkaEvolve pattern); SPECTER2 embeddings only if TF-IDF fails.
4. **Matched-budget DEV ablations** (burned v1–v8 are DEV): each addition vs V7.7 baseline at equal call budget; adopt only if schedule-share ≤17%, `ALLOWED_ROW_OUTSIDE`=0, mean no drop — **else delete it**.
5. **v9**: auditor authors a fresh n≥30 set **in the post-P0 private custody**, power-pre-registered; builder one-shot on the **frozen engine-route machine**; 30/30 served==registered attestation pre-scoring; auditor scores; burn.

**Gate:** mean ≥3.0, 0 violations, 0 inverted, 0 unavailable-input, **CI excluding 3.0** (n=30, SD≈0.7 → mean ≳3.25), run VALID.

## P3 — optimize + speed (→ 7) · 3–5 rounds

**Gap:** hand-tuned directive; no search; asserted FA-rates; no speed budget.

1. **GEPA (MIT)** compiles the generation directive offline against DEV labels with **held-out DEV slices**; metric = the now-trustworthy computed checks + scan battery; reflection on the strongest servable route; generation stays on the registered model. Pre-registered gain on a slice the optimizer never saw.
2. **AIDE-style best-first search — only now** (copy `agent.py`/`journal.py`, MIT + NOTICE): search over typed plans scored by computed checks. Searching earlier = searching noise.
3. **Conformal predictors**: MAPIE + telemanom (verify license text) with **our own loaders** for C-MAPSS/XJTU-SY/CWRU; conformal thresholds make FA ≤1/year a computed property (coverage ≥1−α).
4. **Speed**: per-problem wall-time in the events ledger; median ≤2 min, worst ≤5 min; 429-safe backoff; gateway + judge queue only.

**Gate:** **two consecutive sealed sets ≥3.3**; measured path through the engine; pre-registered DEV gain.

## P4 — real novelty (→ 8) · 3–4 rounds · AGENT-RUN (AM46)

1. **Prior-art distance**: SPECTER2-class embeddings vs patents+papers (deterministic); known-novel vs known-obvious controls separated ≥0.2 cosine.
2. **MOOSE-Chem inspiration retrieval** + failed-mechanism memory blocking repeats.
3. **Blind AI panel (R-PANEL)**: ≥3 agents, ≥2 families ≠ generator and ≠ each other; every rung R-CAL qualified (qwen eligible now; deepseek after c-0043; third from the queue); blind + position-swapped; agreement ≥0.7 (α≥0.6), **AUC ≥0.8 on controls**, auditor cross-check ≥20% (family disclosed); composition + disagreement rule pre-registered **before any rating**.
4. Canary strings + contamination probes on every sealed set.

**Gate:** ≥50% viable+non-obvious by the calibrated blind panel; ≥0.2 cosine separation; 0 canary completions; within speed budget. *Label: AI-rated, not physical efficacy.*

## P5 — external proof (→ 9) · 4–6 rounds · AGENT-RUN

1. **Rediscovery benchmark**: ≥30 granted patents/papers **after the generator's cutoff**, canary-confirmed; engine sees only the problem; auditor agents score blind vs **off-repo rubrics**; key mechanisms pre-registered per item.
2. **Validation tiers**: **T1** executable computed/simulated falsifier (reuses P1 physics + tespy); **T2** retrieval-agent cross-check where **every citation resolves**; ≥1 candidate passes T1+T2 = *agent-validated*. T3 physical test optional gold label, never required.
3. **Unattended operation**: 30-batch end-to-end, **0 human interventions** — automated claim mutex + verifier lane, durable events, backoff, speed budget.

**Gate:** ≥40% key mechanisms recovered; ≥1 agent-validated candidate; unattended run passes.

---

## Round protocol (every round, no exceptions)

FULL constitution reads → claim-before-work (push = mutex) → executor/verifier lanes → **≥30% of changed lines in engine code** → Art. 27 capability ledger + Art. 16 retirements → pushed CI green **API-read with quoted check-runs** → secret-grep staged diff → Session/Work-Id trailers. **No rented compute. No new guard/claim kinds.** DEV = burned v1–v8; acceptance = fresh confidential sealed sets only, frozen machine, one-shot, burn after. NOTICE attribution for every copied permissive file. Never pass a gate on a point estimate.

## Risk register

- **P0 slips → everything slips** (no valid acceptance without custody). Escalate to owner once per round until done.
- Engine integration is the P1 crux: contract negative-case tests before ablation, or the route repeats the wrapper's blind spots.
- Judge-queue 429/503 windows: backoff + c-0043 retry gates panel eligibility; never substitute a rung silently (R-JUDGE).
- Rediscovery cutoff assumptions: canary-probe every item; drop failures.
- ~17–27 rounds total at 1 executor + 1 verifier per round; delete any addition that fails its ablation.

## Checklist

- [ ] **P0:** owner custody+rotation ⬜ · CI fix ⬜ · all-refs gitleaks report ⬜ · measured path ✅
- [ ] **P1:** physics_checks + pint ⬜ · enum schema + scanners deleted ⬜ · engine route integrated (negative cases proven) ⬜ · gate ≥80%/0/0/0 ⬜
- [ ] **P2:** TRIZ JSON ⬜ · K≥3 population + cap 1/6 ⬜ · TF-IDF novelty ⬜ · matched-budget ablations ⬜ · **v9 accepted (≥3.0, CI>3.0)** ⬜
- [ ] **P3:** GEPA held-out gain ⬜ · best-first search ⬜ · conformal predictors ⬜ · speed budget ⬜ · **two sets ≥3.3, engine on path** ⬜
- [ ] **P4:** prior-art distance ⬜ · calibrated blind panel ⬜ · canaries ⬜ · **≥50% viable+non-obvious** ⬜
- [ ] **P5:** ≥30 post-cutoff rediscovery ⬜ · T1+T2 validated candidate ⬜ · **unattended 30-batch** ⬜
- [ ] Durable commit of this roadmap + AM46 (queued, next push-capable round)

**Next round (R50) starts at P0.2–P0.3 + P1.1:** fix the red CI, ship the all-refs scan report, and land the first `physics_checks.py` + pint slice (≥30% engine lines). Score **4/10** today; every point from here is earned by a gate passing on data nobody tuned on.
