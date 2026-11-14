# R11 AUDITOR VERDICT — deep audit of queue/dev12_r7 @ eff419506
**Auditor:** session auditor (Claude), 2026-11-14. Read-only audit of the remote via GitHub REST API; no coder bytes modified. Companion machine-readable judgments: `eval/auditor_judgments_r11.json`.

## 1. Verified claims (evidence-checked, not taken on trust)
- Remote `queue/dev12_r7` tip == `eff419506`; all 12 R11 commits present (2150c4a4f..eff419506). PUSH CLAIM VERIFIED.
- A1 arm: 12/12 COMPLETE, every record 3 LLM calls, e2e 33.3–58.1 s (mean 41.4 s) — within the <=5-call / <=60 s budget. Per-call provider/model/rung/status provenance present. VERIFIED.
- Novelty search: 12/12 MEASURED (lexical overlap vs a 16-record local prior-art pool — see F9). VERIFIED as typed, bounded.
- Triples: 12 committed; rubric summary + gate inputs present; gate correctly PENDING_AUDITOR_JUDGMENTS with owner-set thresholds (Art. LXXXVI). VERIFIED.
- Ablations: 3 variants x 12 typed records in versioned subdirs; minus_repair 0 COMPLETE vs 5 default — repair load-bearing. VERIFIED.
- Near-miss restoration: `eval/pairs/r11_a0plus/` blob SHAs byte-identical between 8364765b9 and eff419506 (14 files). Art. XXXIX held. VERIFIED.
- Judge parse failures: 0/38 (structured output instrument works). VERIFIED.
- Battery runner cascade fallback + judge incremental writes present in committed code. VERIFIED.

## 2. Findings (severity-ordered)
### F1 CRITICAL — judge tally bug inflates wins (scripts/r11_a0plus_compare.py ~line 240)
`picked = x if (prefer=="A")==(order=="a0plus_first") else (y if prefer in ("A","B") else "tie")` — when prefer=="TIE" AND order=="other_first", `(False)==(False)` is True, so a TIE is silently converted into a win for the x-arm. Recomputed from the 38 committed raw judgments with a correct decoder:
| pair | reported | corrected (judge's true preference) |
|---|---|---|
| A0+ vs baseline | 8W/2T/0L | **4W/6T/0L** |
| A0+ vs full | 6W/0T/2L | **5W/1T/2L** |
| A1 vs baseline | 5W/5L | 5W/5L (unchanged) |
| A1 vs A0+ | 5W/5L | **4W/5L/1T** |
The owner-facing "8W/2T/0L" claim is inflated by 4 phantom wins. Arts. XIX/XXX/XXIV. Fix the decoder, re-tally from committed raw judgments (no re-run needed), unit-test all prefer x order combinations incl. TIE, and re-check the 30/30 calibration scoring for the same decoder.
### F2 CRITICAL — judge is the A1 generator (independence violation)
All 36 A1 generation calls ran on **xkiro/mistralai/ministral-14b**; the judge is **xkiro/mistralai/ministral-14b**. `judge_independence: INDEPENDENT_PROVIDER` is false for every A1 comparison (self-preference risk). Arts. XXVI/LXVII. Enforce generator!=judge (provider AND model) at runtime; re-judge A1 pairs on a different provider/model.
### F3 HIGH — novelty gate input is circular by construction
Comparator = sentence coverage vs (standard reference UNION baseline answer) → baseline novelty == 0 always; `novelty_delta` == the arm's absolute lexical novelty. Any verbose synonym-rich answer clears +0.5. Machine delta +1.8 vs auditor-measured +0.6. Rename the quantity, add a semantic (embedding) comparator with symmetric treatment, keep lexical only as disclosed diagnostics. Arts. XIX/XXX.
### F4 HIGH — A1 substance defects (auditor read all 10 valid pairs)
Fabricated/irrelevant DOIs (>=5 answers), fabricated user-constraint labels (>=4), physics/unit errors (>=4: graphene-grid conductivity contradiction; "ripple std" at 1-min sampling; PEO-in-cathode inversion; 0.5 C/cm top-oil gradient), decade-long real-time "falsification" tests (>=5), false departure-from-standard claims (PRPD, spectral kurtosis are standard). A1 is format-complete, substance-unverified. Per-pair evidence in the judgments file.
### F5 HIGH — judge instrument saturation + trivial calibration
76% of all axis values are 5; 5/38 judgments all-identical; calibration corpus is obvious good-vs-bad pairs (30/30 measures parsing, not discrimination). No close-pair calibration, no position-swap double-read. Drop decorative axes or anchor them; calibrate on close pairs; swap-order consistency check.
### F6 MEDIUM — measurement provenance pins are dirty
Rubric/compare/novelty records carry `dirty_tree: true` and parent-commit SHAs. Re-run on the clean tree and pin the exact commit (Arts. LXII/LXXXV). Make rubric/triples writes incremental like the judge driver.
### F7 MEDIUM — full pipeline arm is hot-path dead weight
0 clean COMPLETE (8 NOT_SCORED, 3 CONTRACT_INVALID_MARKER, 1 other); A0+ 5 COMPLETE; audit/relabel ablations show zero COMPLETE delta. Either fix the composer or retire the full pipeline from the hot path with Art. LXIV accounting; decide audit/relabel on a QUALITY ablation (rubric axes), not COMPLETE counts alone.
### F8 MEDIUM — transport: single free provider, no quota ledger, serial execution
z.ai quota dead (429 since 02:17Z); cascade lands 100% on xkiro (single point of failure + F2 collision). 12 items serial ~8.3 min. Add quota/cost ledger, provider-health TTL cache, circuit breaker, per-provider concurrency, 4-way item parallelism (target <=3 min wall for the battery).
### F9 LOW — novelty search is not prior-art search
Lexical overlap vs 16 local records. Add live Crossref/arXiv/patent retrieval with dedup + relevance verification before any NOVELTY_CLAIMED (Art. XXI).
### F10 LOW — no CI, no direct instrument tests
0 check-runs on HEAD; no unit tests import the rubric/gate/decoder; order-dependent flake admitted; 6 typed skips. Add a push CI workflow running the touched-surface tests + new decoder/rubric unit tests.

## 3. Article LXXXVI gate — AUDITOR JUDGED (this is the verdict, not an input)
10 valid pairs (fu-004, sofc excluded: baseline bytes absent, Art. XXV). Order-blinded presentation; independence limits disclosed in the judgments file. Auditor means: A1 (n 1.9, f 1.7, t 2.0, c 1.8) vs baseline (n 1.3, f 2.7, t 3.0, c 2.3).
- Novelty clause: mean delta **+0.6 >= 0.5 → PASS**
- Feasibility clause: mean |gap| **1.2 > 0.25 → FAIL**
- **GATE STATE: NOT_MET.** Substance preference: baseline 6, A1 3, tie 1. Format wins excluded per the article.
A1's invention novelty is real but its feasibility/testability/honesty are below the standard-practice baseline. The machine inputs (+1.8 delta, 0.2 gap) were degenerate (F3) and the machine judge is conflicted (F2) — neither was used for this verdict.

## 4. What this means for the next round
The loop's plumbing (transport, contracts, provenance, ablations) is now solid. The binding constraint is **generation quality under physics/honesty checks** and **a trustworthy judge**. Close F1/F2 first (cheap, unblocks measurement), then F4 via a verify-before-compose leg (unit/sanity checks, DOI resolution, constraint-label audit, accelerated-test design), then F3/F5 instruments, then F7/F8 speed/pruning. No governance additions — every item above is a capability or measurement fix.
