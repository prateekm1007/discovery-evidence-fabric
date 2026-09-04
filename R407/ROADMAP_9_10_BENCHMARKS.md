# Roadmap: 9/10 in Every Benchmark — an End-to-End AI-Loop Operating Plan

**Prepared:** 2026-09-04, from the R407 external audit of `technology-transfer-portfolio-15` + the engine (`discovery-evidence-fabric`) state at HEAD `08c03dd`.
**Companion file:** `NEXT_CODER_DIRECTIVE_R407.md` (the immediate work order W1–W12). This roadmap is the strategic map; the directive is the next move.

---

## 0. How to read this

- **"Every benchmark" is not an aspiration; it is a defined namespace.** There is no 0–10 scale in the engine today. Phase P0 makes one machine contract (`R407/BENCHMARK_RUBRIC.json`) define the ten families and their scoring, so "9/10" means the same thing to every future session, every gate, and the next external auditor.
- **The roadmap is itself a loop, not a list.** Each phase is one pass of the Constitution's 16-step discovery loop (claim → falsifier → evidence → independent evaluator → implement → baseline → experiment → adversarial → replay → record → commit → gates). You do not exit a phase by declaring it done; you exit when the frozen benchmark for that phase reads ≥ 9 **and** the phase's own adversarial test passes.
- **The honest spine:** several benchmarks (physical validation, baseline strength, closed-loop maturity, commercial transfer) are at 1–2/10 today and **cannot be raised to 9 by code**. The only way this operating plan reaches 9/10 *in every benchmark* is for the reality half of the loop to start feeding the machine. Part E is therefore the joint operating plan (coder + CEO/institution); it is not optional.

---

## Part A — The 9/10 rubric (implemented as one contract in P0)

| Family | 10 = | 9 = (release bar) | Now (auditor est.) | Measured by | Reaches 9 in |
|---|---|---|---|---|---|
| DELIVERY | perfect + independent clean-clone replay | 924/924 pins, chain 25/25, byte-reproducible, zero stale hashes | 8 (D1/D2 defects) | release-chain driver | P0 |
| HONESTY | + no unsourced number ever shipped | numeric-assertion audit clean; unknown preserved; PASS rows classified+logged; no semantic promotion | 7 (P-11, P-16, "traced") | honesty drivers + PDF scan | P0/P1 |
| FIDELITY | frozen corpus pinned, hermetic | zero stale paths, zero NOT_MEASURABLE, frozen file hash guard on | 5 (C1/C2) | fidelity driver | P0 |
| MACHINERY | + full E/A/F green on clean clones | E15 A–J pass; E16 blind-holdout/causal/diversity pass; A2/A10/A12 pass | 7 (harnesses exist; some never run) | E15/E16/A/F suites | P1 (measured) |
| ADVERSARIAL | attacker calibration shows per-category sensitivity + clean controls survive | confusion matrix recorded, no arbitrary kill-rate target, negative-control suites green | 2 (corpus frozen, never run) | attacker-calibration driver | P2 |
| NOVELTY_PRACTICE | + adversarial prior-art hunt on every survivor | search neutrality (no hardcoded solution class), collision stage on, zero≠novelty enforced | 7 (R402 CB-2 done; custody gap on prior_art_v2) | novelty/retrieval drivers | P2 |
| INDEPENDENCE | stated reviewer kind + one human/org review in the chain | every external claim discloses reviewer provenance; no opaque "external consultant" | 3 | reviewer-provenance field audit | P1/P4 |
| DOSSIER_QUALITY (12 dims × /10) | per-dossier ≥9 on every dim | per-dossier ≥9 on definition-stage dims; reality dims at honest ceiling w/ decisive-experiment package | 4–8 by dim (see Part B) | dossier-quality driver (the R407 rubric) | P1–P3 |
| LOOP | one REAL_LOOP_VERIFIED package | controlled-rehearsal ingest proven; REALITY_EVENT interface live; loop ledger correct | 3 | loop-state ledger + rehearsal | P3 (rehearsal), P5 (first REAL) |
| REALITY-FED (physical validation, baseline strength, commercial transfer) | real observation + independent replication + buyer transaction | ≥1 decisive experiment executed per promoted dossier with attested provenance | 1–2 | REALITY_EVENT ledger + attestation checks | P5/P6 only |

Scoring rules (non-negotiable, in the contract): a score without a driver output is rejected; a missing instrument scores 0, never 9; reality-fed dims carry a recorded stage ceiling until a REALITY_EVENT of the right class lands; relabeling a ceiling as a defect (or vice versa) is itself a HONESTY failure.

---

## Part B — Current standing (from the R407 audit's dossier scoring, normalized to /10)

Per-dossier 12-dimension scores (audit, scale ×2): **mechanism clarity 6–8** (all dossiers have a named causal mechanism; none established novel); **evidence quality 2–6** (hashed problem-context sources only; P-16 has direct mechanism precedent = 6, P-13 = 2); **provenance 4–6** (excellent metadata discipline; computations lack shipped logs); **engineering correctness 6–8** (no unit/arithmetic errors found; dimensional state 0/66 proven — honest); **baseline strength 2** (no dossier measures an advantage over an incumbent); **reproducibility 2–6** (CAD regeneration perfect = 6; simulations not shippable = 2); **physical validation 2** (zero observations, zero prototypes — portfolio-wide); **novelty practice 8** (never claimed; NOT_ESTABLISHED everywhere); **manufacturing feasibility 2–6** (CAD only); **commercial transferability 2–6** (evaluable but not licensable); **decisive-experiment quality 6–8** (WP-01 + kill conditions well defined; P-13 = 2); **closed-loop maturity 2–4** (P-24 = 4 synthetic; rest 2).

Portfolio-level (from the audit): DELIVERY 8, HONESTY 7–9, physical reality 2, end-to-end loop = **Stage 2 (computational discovery system)**, honest ceiling recorded.

Verdict carry-over (kill/promotion from the audit — these set P4's experiment queue):
- **Promote to sponsored experiment:** P-07 drainage floor (cheapest decisive test), P-16 NIR-PV (strongest direct precedent), P-24 gravity damper (ASD predicate), P-27-R1 MEMS sensor (most mature base tech).
- **Disconfirmation-first:** P-29 implantable MR sensor, P-28 tissue detection, P-21-R1 deep-tissue, P-15-R1 PVDF — each WP-01 is likely negative; run them as designed kill tests, then redirect or kill.
- **Remove from buyer surface as a transfer item:** P-13 (data-conditional; repositioned; make it permanent).

---

## Part C — Phases (each phase = loop iterations; exit = frozen benchmark ≥ 9)

### P0 — Canonical truth + rubric + fidelity (R407 W1–W5, W10) — *≈ 2–4 sessions*
- Fix D1 (identity registry), D2 (LATEST_RELEASE), B1 (P-22-R1 V3 re-ship through Art. XXXIX chain), C1/C2 (stale paths, semantic-genericness restore), backfill worklog.
- Implement `R407/BENCHMARK_RUBRIC.json` + drivers for DELIVERY/HONESTY/FIDELITY.
- **Exit:** DELIVERY, HONESTY, FIDELITY ≥ 9 by the drivers; r373/r374 audits green; adversarial test on each fix passes; both remotes clean at HEAD==origin/main.

### P1 — Buyer-surface honesty + reproducibility evidence (R407 W6–W8) — *≈ 2–4 sessions*
- Fix P-11 numbers, P-16 V-002 classification + log, exec-brief "traced claims" wording, "external consultant" → AI adversarial review with reviewer provenance.
- Ship computation-log artifacts for referenced computations or downgrade them; add per-package `reviewer_provenance`.
- **Exit:** HONESTY ≥ 9; DOSSIER_QUALITY `reproducibility` ≥ 9 on ≥ 6 packages; INDEPENDENCE ≥ 6 with the provenance field everywhere; no PASS row without log+class.

### P2 — Run the frozen measurements (R407 W9) — *transport-gated, as soon as a healthy model transport exists*
- Orchestrator: attacker calibration (16 cases) → model contest → 12-problem cross-domain frozen benchmark → operator proofs. Raw records only.
- Close the prior-art custody gap (direct searchers must write custody entries).
- **Exit:** ADVERSARIAL ≥ 9 (confusion matrix, clean controls survive); NOVELTY_PRACTICE ≥ 9; MACHINERY fully measured; every deferred measurement has a raw record — or an honest `BLOCKED` state with the reason, never a silent pass.

### P3 — Decisive-experiment acquisition layer + rehearsal (R407 W11) — *≈ 2–3 sessions*
- Per promoted/priority dossier: `DECISIVE_EXPERIMENT_PACKAGE` (WP-01 protocol, measurement schema, acceptance, kill; what a bench partner/buyer must return as a REALITY_EVENT).
- Run a controlled rehearsal through the REALITY_EVENT ingest; record `SYNTHETIC_REHEARSAL=TRUE / REAL_LOOP_VERIFIED=FALSE`.
- Harden CB-7 (killer-experiment falsification schema) now that the acquisition layer exists (deferred from R402).
- **Exit:** LOOP ≥ 6 (machinery proven by rehearsal); DOSSIER_QUALITY `decisive-experiment quality` ≥ 9 on ≥ 6 dossiers; rehearsal certificate present.

### P4 — First real external evaluation (JOINT: coder + institution) — *institution-gated*
- Sponsor the promoted decisive experiments (P-07 first — cheapest; P-16; P-24; P-27 if budget allows) and the four disconfirmation tests.
- Obtain **one genuinely independent human (or external-organization) technical review** of the portfolio — the first non-AI independence event in the chain.
- **Exit:** INDEPENDENCE ≥ 9 (human/org review on record); ≥ 1 REALITY_EVENT (bench result) attested with custody chain and ingested through the SAME code path as the rehearsal.

### P5 — First closed real loop (JOINT) — *institution-gated*
- A bench result changes a dossier: evidence class, model update, V2 mutation, package re-ship through Art. XXXIX.
- **Exit:** one package reaches `REAL_LOOP_VERIFIED`; LOOP ≥ 9; physical-validation dim for that package ≥ 9; portfolio maturity moves to **Stage 3** (evidence-backed transfer for that dossier) or **Stage 4**.

### P6 — Repeat, diversify, buyer cycle (JOINT)
- Second and third domains/packages through the real loop; ≥ 2 independent labs or one buyer evaluation; commercial evidence (cost/effort) from real quotes.
- **Exit:** DOSSIER_QUALITY reality-fed dims ≥ 9 for the closed packages; a buyer-facing evaluation artifact exists; portfolio maturity **Stage 4–5**.

### P7 — Full 9/10 + next external audit (R408)
- Re-run every family driver from clean clones; every benchmark ≥ 9 (or at honest stage ceiling with the ceiling recorded and the reason cited).
- Self-audit against this roadmap's own axes before R408.

---

## Part D — The end-to-end loop, and where each node is measured

```
 OBSERVE (real) ──► EVIDENCE ──► MECHANISM ──► HYPOTHESIS ──► PREDICTION ──► EXPERIMENT ──► MEASUREMENT ──► MODEL UPDATE ──► SEARCH UPDATE ──► DISCOVERY ──► DOSSIER ──► BUYER
      ▲                                                                                                                 │                    measured by
      │                                                                                                                 ▼                    MACHINERY/E15/F-series
      └────────────── REALITY_EVENT (attested, custody chain, SAME code path as rehearsal) ◄── decisive experiment ◄── DECISIVE_EXPERIMENT_PACKAGE
                          measured by LOOP ledger & REALITY-FED dims                        run by institution/lab/buyer (P4–P6)
```

Where 9/10 is blocked today:
1. **Nodes left of EVIDENCE are empty** — no observation exists; that is the whole physical-validation gap. P4–P6 fill them.
2. **The left-to-right chain is proven only to DOSSIER** (E15/A/F series). EVIDENCE→MEASUREMENT→UPDATE (the bottom-right arc) has machinery but no real input; P3 rehearses it, P5 closes it for real.
3. **SEARCH UPDATE ← failure learning** is engine-internal and was not demonstrated portfolio-side; P2 (cemetery consumption + prior-art custody) and P5 (a real failure changing a dossier) close it.

---

## Part E — Joint operating plan (who must do what — the "end to end" part)

The coder alone cannot reach 9/10 in every benchmark. Split responsibilities, recorded in the rubric so scores never attribute institution actions to the coder:

| Owner | Responsibility | Evidence they must produce |
|---|---|---|
| CODER (AI agent) | W1–W12, all rubric drivers, reproduction/rehearsal machinery, protocol packages, honest ceilings | machine scores, adversarial tests, rehearsal cert, clean-clone replays |
| CEO / principal | issue directives; approve kill/promotion; fund decisive experiments (P-07 first); **obtain ≥1 human/org independent review**; run at least one lab/bench cycle; arrange buyer evaluation | REALITY_EVENT submissions w/ attestation + custody; review report; experiment invoice/quotes |
| Independent evaluators | the frozen drivers + the next external audit (R408) — never the coder | scored benchmarks; audit report |

Rule: a benchmark counts as met only when scored by an evaluator that is not the claimant (Art. XXVI). The coder may run drivers; the *certification* is the clean-clone replay and the R408 external pass.

---

## Part F — Measurement schedule and exit criteria

- **After P0/P1:** DELIVERY/HONESTY/FIDELITY ≥ 9 (drivers). **After P2:** ADVERSARIAL/NOVELTY/MACHINERY ≥ 9. **After P3:** LOOP ≥ 6, decisive-experiment quality ≥ 9. **After P5:** first package REAL_LOOP_VERIFIED, physical validation ≥ 9 for that package. **After P7:** every family ≥ 9, maturity Stage 4–5, R408 audit pass.
- **The benchmark for the benchmarks:** FIDELITY stays ≥ 9 through the whole plan — frozen corpus hash guard, zero stale paths, zero NOT_MEASURABLE, hermetic tests — or every other score is suspect.
- **Definition of done for the whole plan:** an R408 external auditor re-runs every check in this roadmap from clean clones, reproduces the scores, confirms at least one package went around the real loop (observation → dossier change → re-ship), and the honest ceilings that remain are ceilings the roadmap names, not defects it hides.

*End of roadmap — companion directive `NEXT_CODER_DIRECTIVE_R407.md` is the W1–W12 action list that starts P0.*
