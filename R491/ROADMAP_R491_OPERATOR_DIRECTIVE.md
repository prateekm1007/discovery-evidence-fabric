# ROADMAP — Operator Directive R491 (verbatim source)

**Provenance:** operator message, 2026-09-17 (R491 round opening), received together with two credentials (Lens API + Elsevier Developer Portal API — registered per Article LXXIII in `R491/SECRETS_R491.json`) and the instruction "Read your constitution."
**Status:** verbatim operator text. This file is a SOURCE artifact (quoted operator text, Art. LXX exception 3) — the adoption ruling and the constitution cross-check live in `R491/ROADMAP_ADOPTION.md`. Never edit the text below.

---

# Roadmap: Toscanini to 9/10 in every benchmark

Starting point: HEAD `8fc7bc47` (R490), overall 6/10. This roadmap covers all 25 dimensions, each with a concrete 9/10 bar, the exact change, and the acceptance test. No new registries, state machines, or provenance systems — every item reuses the canonical ledger, gate, cemetery, or chain (§39–41 constraints honored throughout).

## 0. What 9/10 means here (and what it doesn't)

9/10 = world-class and robust; only marginal improvement remains. Per the audit standard, every 9 requires **measured evidence from production or frozen benchmarks**, never architecture. What 9 does *not* require: solving every domain, replacing free-tier models with frontier ones, physical validation of every package, or human-level prose. Owner-gated items (money, labs, external reviewers) are marked **OWNER** — the roadmap stalls on those without operator action, and says so explicitly.

## 1. The full 25-dimension table

| # | Benchmark | Now | 9/10 requirement | Gap → root cause → exact change → acceptance test | Pri |
|---|---|---|---|---|---|
| 1 | End-to-end completion | 4 | ≥8/16 fresh problems reach buyer ZIP, zero manual repair | Gap: automation ends at HELD. Cause: no survivor has ever cleared every gate. Change: sequential unblock of #8, #4, #17, #24 then a 16-problem packaging campaign. Test: 8 ZIPs through XXXIX verifier from clean submissions. | P0 |
| 2 | Discovery quality | 5 | Support rate ≥0.8 across families + measured existence-refusals + multi-source custody (kept) | Gap: weak-domain retrieval (0.23), count-as-existence. Cause: retrieval-count proxy, no 5-question gate. Change: execute Art.XX measurement; refuse-to-build on UNESTABLISHED (typed, counted). Test: junk-record problems yield UNESTABLISHED; support ≥0.8. | P1 |
| 3 | Evidence quality | 5 | Verbatim-bound retrieval, contradiction detection ≥0.29, no count-as-existence | Gap: span 0 systematic, contradiction regression 0.29→0.14. Cause: synthesis never required to quote; adaptive path suppresses contradiction stage. Change: fix both, re-run R458. Test: instrument readings green on re-run. | P0 |
| 4 | Evidence binding | 4 | Proposer-emitted verbatim spans; verifier-rewrite ≈0; rebinds fail the binding stat | Gap: `repair_mechanism_span` + 80-char assist rewrites. Cause: repair path load-bearing for old lineage. Change (P1-8, accepted): proposer must emit verbatim or REJECT; grandfather old lineage explicitly. Test: non-verbatim fixtures REJECT, never repair-pass. | P0 |
| 5 | Mechanistic reasoning | 3 | Causal-density validator live; paraphrase fixtures fail; mechanisms carry bound causal graphs | Gap: 1–2 shared terms = VALID. Cause: term-overlap validator. Change: causal validator (extraction→graph→density threshold, calibrated on independent fixtures). Test: paraphrase-only mechanisms fail; live pass rate measured. | P0 |
| 6 | Candidate diversity | 5 | `n_distinct` counts physics families (human-audited sample agrees ≥0.8) | Gap: self-calibrated Jaccard bands + lexical grid. Change: independent-fixture calibration; retire or subordinate the lexical grid. Test: calibration report + audit sample. | P1 |
| 7 | Novelty/differentiation | 4 | Patent-leg complete, passages byte-verified, differentiation ladder on every survivor | Gap: EuropePMC-only, LLM-asserted passages, term-overlap relevance. Change: configure Lens or declare patent-blindness per run; byte-verify `exact_passage`; enforce ladder. Test: hallucinated-passage fixtures fail. | P1 |
| 8 | Adversarial attack | 5 | FPR≤0.30 + TPR≥0.75 **live** on sealed corpus; separate-provider attack on all survivors | Gap: FPR 1.0 live (v3 rules didn't fix selectivity). Cause: (rules × ring) — qwen served 20/22. Change: iterate attacker (model/ring/prompt) against sealed bars until bars met; ship measurement. Test: live sealed-corpus run green. **The critical path for the whole roadmap.** | P0 |
| 9 | Contradiction handling | 6 | Contradiction flips recorded decisions in production (confidence delta + dossier reflection + experiment-strategy change, each demonstrated) | Gap: blocking + belief-delta proven; dossier-reflection and strategy-change unproven. Change: wire contradiction into dossier builder + killer-experiment priority; demonstrate on 2 live runs. Test: B-evidence run shows all three movements. | P1 |
| 10 | Experiment selection | 4 | Numeric kill contracts + apparatus/sample/cost on every EXPERIMENT_READY; ≥1 physically executed | Gap: no apparatus/sample/cost, zero executed. Cause: no lab path, no cost ledgers. Change: require fields for READY; execute cheapest decisive experiment (P-07 WP-01). Test: one executed experiment ingested. | P0/P1 |
| 11 | Failure diagnosis | 6 | Cross-domain gap→mutation demos; gap taxonomy covers observed kill classes | Gap: single-class demos. Cause: kills concentrated in one family. Change: run 3 families, extend taxonomy from measured kills. Test: taxonomy covers ≥90% of observed kills. | P1 |
| 12 | Candidate mutation | 8 | Closures in ≥2 families (n≥5) + observed re-kill typings + selection wins | Gap: n=2, same class, child lost 11/11. Change: cross-domain closure campaign (mechanical run is the first attempt). Test: `CHILDREN_ADMITTED` outside thermal + one admitted child reaching selection top-half. | P0 |
| 13 | Causal learning | 4 | Cemetery steering measured (reproposal-block rate) + ≥1 REAL_LOOP spec update | Gap: prose causality, no persistent update. Change: measure blocked-reproposal rate on synthetic cemetery probes; close one REAL loop into a spec. Test: steering rate + REAL_LOOP_VERIFIED=1. | P1 |
| 14 | Adaptive orchestration | 4 | Cost-aware EIG with measured latencies; adaptive ≥ fixed quality; fidelity escalation live | Gap: literal costs, R458 regression. Change: measured cost/latency ledgers (close token-UNKNOWN too); fix contradiction suppression; demonstrate escalation. Test: R458 re-run green. | P1 |
| 15 | Model utilization | 5 | Strong-model serving with measured quality floor; weak-model STRONG always typed | Gap: free-tier substitution into STRONG (whole-loop). Cause: cost policy + flaky atria. Change: quality floor per task class; substitution typed + downgraded routing. Test: floor enforced in ledgers. | P1 |
| 16 | Model/provenance integrity | 6 | Revision pins, prompt/policy hashes, token accounting live | Gap: token cost UNKNOWN, no revision pins. Change: usage capture (v3 record already carries usage — extend to all calls) + model-revision + prompt-hash logging. Test: any ledger line re-priced and re-prompted. | P2 |
| 17 | Engineering representability | 5 | Baseline wins ≥6/16; UNKNOWN-excluded solving; tolerance/material binding enforced | Gap: 0/16 wins, honest-vs-broken unresolved. Change: baseline audit (fix or rule out), then campaign. Test: 6 wins with bound parameters. | P0 |
| 18 | Simulation/physics | 3 | Per-family solver matrix or explicit scoping; validation vs reference within tolerance | Gap: single 1D-hydraulics solver. Cause: by-design narrowness. Change: EITHER add validated solvers per represented family OR constitutionally scope claims per family (honest scoping = valid 9-path for this dimension). Test: matrix published; out-of-scope → honest terminal (already works). | P1 |
| 19 | Reality boundary | 6 | ≥1 REAL_LOOP_VERIFIED package + zero silent promotions under audit + rehearsal discipline kept | Gap: 1 DB lookup ever. Cause: no lab path (OWNER). Change: execute + ingest one attested experiment. Test: REAL_LOOP_VERIFIED=1 with full custody. | P0 (OWNER) |
| 20 | Benchmark integrity | 6 | R458 re-run green + holdout discipline + one externally replicated benchmark | Gap: re-run pending; AI-on-AI only. Change: re-run; publish replication kit; arrange one external replication. Test: green re-run + external repro. | P1 |
| 21 | Cross-domain generality | 4 | Closures ≥2 families + packages ≥3 domains | Gap: closures one class, packages zero. Change: closure campaign (mechanical → electrical → materials). Test: as stated. | P0 |
| 22 | Reliability | 6 | Zero orphan-deploy windows over 10 rounds; prune-safe shipments (proven); Windows-green suite | Gap: 8 race instances; case collision; stale-clone CRLF trap. Change: deploy-lease/queue (one writer), `.gitattributes` done + renormalize advisory (done), case rename. Test: 10 clean rounds + green Windows CI. | P2 |
| 23 | Reproducibility | 5 | Clean-clone rebuild **including buyer ZIP**; digests hold all platforms | Gap: rebuild proof excludes ZIP. Change: extend P1–P4 pattern to a shipped package. Test: fresh-clone ZIP rebuild, hash match. | P1 |
| 24 | Transfer package | 3 | ≥1 then ≥8/16 current-engine ZIPs, visual gate passing, zero manual repair | Gap: 0 current-engine packages. Cause: no survivor clears all gates. Change: downstream of #8/#17/visual-capacity; then campaign. Test: ZIPs through XXXIX verifier. | P0 |
| 25 | Overall | 6 | All of the above + external review concurring | See phasing. Test: independent re-run of all drivers (Phase 4). | — |

## 2. Minimum path — 12 changes in dependency order

1. **Calibrate the attacker live** (bars met on sealed corpus via committed transport). Unlocks #8 and unblocks every kill-dependent dimension. If FPR won't move: change the ring/model, not the bars.
2. **Verbatim-span synthesis** (proposer quotes or REJECTS). Unlocks #3/#4/#5.
3. **Baseline-win ruling** (fix evaluator or honestly certify candidates don't beat baselines — either is progress; only ambiguity is failure).
4. **R458 re-run** on the credited leg (validates #3, #14, #20 in one campaign).
5. **Cross-domain closures** (mechanical → one more family).
6. **A2 DEV-corpus calibration** (owned plan exists; closes the two-attacker gap).
7. **Visual capacity** (OWNER billing — single action unblocks #24's 3D path).
8. **First current-engine ZIP** through XXXIX (downstream of 1–3, 7).
9. **ZIP rebuild proof** (extend the proven P1–P4 pattern).
10. **One REAL experiment ingested** (OWNER lab/bench; cheapest decisive protocol first).
11. **Measured costs + floor enforcement** (token accounting, quality floors, escalation live).
12. **External review** (OWNER; the only cure for AI-on-AI).

## 3. Phasing with exit criteria

- **Phase 0 — Truth (done).** Scores above are the baseline; every claim byte-verified or labeled record-sourced.
- **Phase 1 — Instruments (coder, ~3–4 rounds).** Exit: attacker bars met live; span rate ≥0.8; baseline ruling published; R458 re-run green. *Without this phase, everything downstream is noise — a selective adversary is the load-bearing wall.*
- **Phase 2 — Generality (coder, ~2–3 rounds).** Exit: closures in ≥2 families; A2 calibrated; packages in ≥1 domain.
- **Phase 3 — Delivery (coder + OWNER billing).** Exit: visual COMPLETE_PASS in prod; ≥1 current-engine ZIP; ZIP rebuild proven.
- **Phase 4 — Reality (OWNER).** Exit: REAL_LOOP_VERIFIED = 1; external review on record.
- **Phase 5 — 9/10 verification (external).** Exit: independent clean-clone re-run of all drivers; ≥8/16 packaging; concurring verdict.

## 4. Honest risks

The plan fails if: the attacker can't pass bars on any affordable ring (then the architecture needs a non-LLM adversarial layer — the current design assumes calibration is achievable); candidates genuinely never beat baselines (then the discovery front-end, not the evaluator, is the problem); or owner-gated items (capacity, lab, review) stay open — in which case the reachable ceiling is ~7, and the report should say so rather than relabeling.
