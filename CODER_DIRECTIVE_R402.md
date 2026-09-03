# CODER DIRECTIVE R402 — The Discovery Constitution

**Issued:** 2026-09-04, coder session following the R401-WC external audit + addendum (re-verified at remote HEAD `c8aa7757`).
**CEO decision on record:** a **substantial constitutional upgrade**, not 20 more procedural rules. The Constitution's center of gravity moves from *"do not lie about knowledge"* to *"do not mistake plausible generation for knowledge creation."*
**Constitution amended in this round:** v1.9.0 → v2.0.0 (`EPISTEMIC_CONSTITUTION.md` — Articles XL–LXIII, THE DISCOVERY IMPERATIVE, the 16-step discovery coding loop, the four-layer hierarchy, `WORLD_CLASS_DISCOVERY_GATE`).

---

## 0. Why this round exists (measured, not narrative)

The audit's single sentence: *this repository contains a first-rate epistemic operating system, four well-built measurement harnesses that have never been run, a verified buyer-delivery chain, and a discovery core that has not yet discovered anything it can prove.*

The re-verified adversarial probes (unchanged at `c8aa7757`, byte-identical to `78817a26`):

```
A. identical causal graph (Jaccard 1.0), renamed design knob      -> kept 2/2  GENUINE_MECHANISM_DIFFERENCE
B. identical causal graph (Jaccard 1.0), PURE SYNONYM rename      -> kept 2/2  GENUINE_MECHANISM_DIFFERENCE
C. identical causal graph (Jaccard 1.0), added specificity        -> kept 2/2  GENUINE_MECHANISM_DIFFERENCE
```

Plus: the generator's own retrieval hardcodes one solution class (`f"{failure} prevention coating flow"`, `mechanism_space.py:1503-1504`) across every domain; live retrieval is unioned into generation evidence after FREEZE; a `PROVEN_INVARIANT` can only hard-block in 3 legacy domains (hardcoded `elif` branches, `mechanism_cemetery.py:336-341`); the mechanism generator has **zero references to the cemetery** (failures are archived, not learned); and disabling the VERIFY stage converts "never ran" into `REJECTED`/`"evidence verification failed"` (Art. XXV violation, terminal decision field).

These are not procedural bugs. They are **the discovery core mistaking generation for discovery**. This round fixes them at the constitutional + instrument level, so the class of bug becomes impossible to mistake for a discovery metric.

---

## 1. Sequenced work order

Each item carries the constitutional article it enforces, the acceptance criterion, and the falsification test. **No item is done until its adversarial test exists and passes.** Order matters: the Constitution first (it defines what "done" means), then the three P0 instruments (they are the bottleneck — everything else measures through them), then the P1 correctness fixes, then the P2 hygiene.

| # | Item | Enforces | Acceptance criterion |
|---|------|----------|---------------------|
| W1 | Constitution v2.0: THE DISCOVERY IMPERATIVE + Articles XL–LXIII + 16-step coding loop + four-layer hierarchy + WORLD_CLASS_DISCOVERY_GATE | CEO directive | Full text present in `EPISTEMIC_CONSTITUTION.md`; Articles I–XXXIX preserved verbatim (historical foundation, per CEO: "I would not delete the existing Articles"); constitution loader + CI still validate |
| W2 | **CB-1 (P0)** distinctness instrument v2: structural comparison, three-verdict vocabulary `DISTINCT / EQUIVALENT / INDETERMINATE`; knob-rename/synonym/parameter-rename CANNOT independently create an invention; `material_distinctness_rate` counts only `DISTINCT` | Art. XLII, XLVIII | Audit probes A/B/C reproduce as **pinned tests** and return `EQUIVALENT`/`INDETERMINATE` (never `DISTINCT`); a genuinely different causal graph still returns `DISTINCT` (no universal merger — Art. V); every verdict records its basis |
| W3 | **CB-2 (P0)** search-space neutrality: the hardcoded `"prevention coating flow"` solution class is removed; mechanism query derived from problem facts + failure mechanism + constraint + frozen evidence vocabulary; every injected solution-class term carries `DERIVED_FROM_EVIDENCE` or `EXPLORATORY_HYPOTHESIS` provenance | Art. XLIII | Query-neutrality test across the 8 audit domains (thermal runaway, DC arc fault, rag clogging, aseptic loosening, humidity drift, surface pickup, blade erosion, catheter obstruction): zero hardcoded mechanism words in any query unless derived from frozen evidence/problem terms; the derivation is recorded per query |
| W4 | **CB-3 (P0)** evidence boundary: post-freeze expansion retrieval creates a NEW evidence snapshot + NEW freeze + NEW epistemic version; never a silent union | Art. XLIV | Freeze-boundary test: a frozen snapshot's hash set and the generation plane's hash set are disjoint by construction; every candidate's evidence bundle records `evidence_snapshot_id`, `evidence_hash`, `retrieval_role`, `retrieval_version`, `retrieval_sources`, `retrieval_timestamp`; the expansion state carries its own snapshot hash |
| W5 | **NF-2 (P1)** disabled/skipped stage yields `NOT_EVALUATED`/`UNRESOLVED` + final `UNKNOWN`, never `REJECTED` | Art. XXV, LXI | Disabled-stage test: VERIFY+SYNTHESIZE disabled → final_status `UNKNOWN`, reason states the stage never ran, epistemic state stays `OBSERVED`; a real `verified:false` with issues still rejects with the issue list |
| W6 | **CB-6 (P1)** terminal rejection reason carries the kill dimensions (never an empty trailing colon) | Art. LXIII (buyer-facing honesty) | Unit test: adversarial kill with empty `reason` but populated `attacks` → reason enumerates the killed dimensions |
| W7 | **NF-1 + CB-9 (P1/P2)** the declared stage-dependency graph resolves: `depends_on` uses stage names (the same namespace as `STAGE_ORDER`); `CEMETERY_CHECK`'s dead registration is resolved (removed from ADAPTERS with the recorded reason, or wired — never registered-but-unreachable) | Art. X (one authority), audit NF-1 | Resolution test: every `depends_on` entry of every adapter in `ADAPTERS` resolves to a stage in `STAGE_ORDER` (or the entry is removed); `len(ADAPTERS) == len(STAGE_ORDER)` or the asymmetry is a recorded, tested contract |
| W8 | **CB-5 (P1)** cemetery: `domain_terms` derived from the entry's own `physical_constraint`/`mechanism` vocabulary (deterministic term extraction — no hardcoded domain `elif` ladder); and the mechanism space CONSUMES the cemetery (Article LI: negative knowledge changes future search) | Art. LI | (a) Unit test: a PROVEN_INVARIANT written in NEW domain vocabulary (no csf/jacobian/stiffness terms) hard-blocks a matching candidate; (b) mechanism-space test: with a cemetery entry covering the candidate's causal core, the candidate is blocked/penalized and the block is recorded with the entry id — the cemetery state is an input to generation, not an archive |
| W9 | **CB-10 (P2)** TLS verification: retrieval honors `ENGINE_TLS_VERIFY` (default ON); the disabled state is a recorded configuration, never a silent global | security | Config test: default context verifies; explicit opt-out records the state in the item provenance |
| W10 | **CB-12 (P2)** the operator item cap that produced any headline distinctness number is recorded in the artifact that carries the number | provenance | The space record already carries `per_operator_item_cap` + `item_cap_source` — verify and pin in test |
| W11 | Run the frozen measurement harnesses **once the LLM transport is healthy** (attacker calibration corpus, model contest, 12-problem cross-domain benchmark) | Art. XLIX, L, LVIII | Deferred until transport; recorded as deferred, never claimed |

**Deliberately out of scope this round** (recorded, not forgotten): CB-7 killer-experiment falsification contract (needs its own round — it is a contract redesign, not a patch); CB-8 machine-bound paths (256 files — needs a portability sweep round); NF-4 seed/model-version capture in the run record; NF-5 cost metering; NF-6 authorization-gate path derivation; NF-7 short-abstract discard count; OB-1..5 operator/CEO actions. Each is listed in `COMPLETION_CHECKLIST.md` with its owner.

---

## 2. The coding loop for this round (constitutional, 16 steps)

```
1. READ CONSTITUTION
2. RECORD STATE
3. STATE THE SCIENTIFIC CLAIM BEING CHANGED
4. STATE THE MEASUREMENT THAT CAN FALSIFY IT
5. IDENTIFY THE CURRENT EVIDENCE
6. IDENTIFY THE INDEPENDENT EVALUATOR
7. IMPLEMENT
8. RUN BASELINE
9. RUN EXPERIMENT
10. RUN ADVERSARIAL TEST
11. REPLAY FROM CLEAN STATE
12. CLASSIFY RESULT
13. RECORD UNKNOWNS
14. UPDATE LEARNING MEMORY
15. COMMIT
16. RE-RUN CONSTITUTIONAL GATES
```

For each work item above, steps 3–6 are answered **in the commit message** (the repo's standing pattern). Step 10 is non-negotiable for W2/W3/W4: the audit's probes become tests; the attack that found the defect must be the test that pins the fix.

---

## 3. What this round may NOT do

- **No threshold tuning to make numbers look better.** The distinctness thresholds below were chosen from the *structure of the representation* (node-role term sets, edge signatures), not fitted to a desired output count (Art. XXVII: MODEL_DERIVED class, declared).
- **No green-gate optimization.** If the new instrument collapses the R401-WC2 headline to fewer distinct mechanisms, that is the *measurement becoming honest*, not a regression. The old `1.0` rate measured vocabulary entropy of a coating-biased generator; the new rate measures mechanism families. They are not comparable numbers and will not be presented as such.
- **No constitution-driven model lock-in.** The Constitution specifies invariants and evidentiary standards; models, matchers, and thresholds live in versioned technical policies (the four-layer hierarchy, Art. LIX discipline).
- **No silent worktree drift.** The audit's own contamination (cemetery + retrieval log) was restored to HEAD before any work; recorded in the worklog.

---

## 4. Session log contract

Every commit answers: what scientific claim changed, what falsifies it, what evidence exists, who the independent evaluator is. The worklog at `/home/z/my-project/worklog.md` carries the session record. The repository's own commit-message standard (measured root cause → fix → adversarial evidence) is unchanged.
