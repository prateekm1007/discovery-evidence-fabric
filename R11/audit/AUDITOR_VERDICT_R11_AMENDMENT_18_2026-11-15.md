# R11 AUDITOR VERDICT — AMENDMENT 18 (2026-11-15): R18 @ fc8d6788a — v3.0.0 enforcement wiring + weight-bound r11
Auditor: session auditor (Claude). Preflight: audit/preflight/PREFLIGHT_2026-11-15_r18.md. Companion: eval/auditor_judgments_r11_r18.json. Builder OFF audit branch. Auditor Art. 13 (independent recompute) applied.

## VERDICT
**Gate: NOT_MET — feasibility RESOLVED-FAIL (1.367), improving; novelty RESOLVED-PASS (2.133).** The v3.0.0 enforcement wiring is real and caught a genuine decoder bug — but **F32 (HIGH): the new tests do not gate the builder's branch, and the queue-push CI is RED.** The "unenforced rules" problem the refactor targeted is not yet solved.

## 1. Art. 19/21/26 — verified, credited
- **Art. 19 decoder fix is REAL**: `majority_of` now strict plurality; I verified every tie case (['A','B','tie']→tie, ['A','B']→tie, ['tie','tie','A']→tie) and plurality cases. The old `max(pref_counts)` returned arbitrary winners on split ties — the exact ties→wins class. Zero impact on committed records. **Auditor Art. 13 independent recompute reproduces r11 exactly** (novelty 2.133, feasibility 1.367 from per-pair rows). 10 new tests compile (6+1+3).
- **Art. 21**: 5 real label-misuse findings (dev-fu-003, eval-new04, eval-new08) disclosed + pinned; judged bytes untouched (Art. 4); CI fails on new findings. Honest.
- **Art. 26**: judge crowllm/Qwen ≠ generator zai/GLM, k=3, green.

## 2. F32 HIGH — the enforcement does not gate the builder's branch
The new Art. 19/21/26 tests live in `tests/` and are picked up by `epistemic_certification.yml` — **which triggers on `main` only**. The builder works on `queue/dev12_r7`. The queue-push workflow (`r11_queue_surface.yml`) **does not include the new tests**, and its check-run is **FAILURE** (on fc8d6788a and d1cf5a129). So the coder's "Arts. 19/21/26 CI checks WIRED + GREEN on commit" overstates: the tests exist and pass locally, but they do not run on the builder's commits, and the queue CI is red. **This is precisely the unenforced-rules failure the owner's refactor was meant to fix.** Wire the new tests into the queue-push workflow and make the queue CI green.

## 3. Weight-bound battery r11 (F30 improving)
Overall: novelty **2.133** CI [1.426, 2.841] PASS; feasibility **1.367** CI [0.931, 1.802] FAIL (improved from r10's 1.9). Intervention subset: novelty 2.556 / feasibility 1.5 (from 2.389); predictor subset: 1.5 / 1.167. The weight-bound design improved feasibility (the binding axis) at some novelty cost. **Report-vs-bytes note:** the coder's headline "2.556 / 1.5" was the intervention subset, not the overall gate numbers (2.133 / 1.367); label subsets clearly (Art. 1/5). Gate NOT_MET; feasibility still >0.25.

## 4. Report-vs-bytes
"All green" vs queue surface CI FAILURE; headline numbers were the intervention subset. The Art. 27 "no capability change" report was honest for the CI work itself (the weight-bound r11 is a separate capability stream).

## 5. Gold-set self-check: 10/10; decoder tie cases verified.

## 6. Ledger delta
F32 HIGH opened (CI enforcement gap); F30 OPEN-IMPROVING (feasibility 1.9→1.367). V18 recorded. Progress 52–60% (feasibility improving; enforcement started but the CI gap is a setback on the enforcement goal).
