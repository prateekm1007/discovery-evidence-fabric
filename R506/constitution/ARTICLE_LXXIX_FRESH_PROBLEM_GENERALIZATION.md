# Article LXXIX — Fresh-Problem Generalization

**Status:** DRAFT FOR OPERATOR RATIFICATION (R506) — not yet law
**Proposed amendment:** Constitution v2.8.0 → v2.9.0
**Sponsor:** Operator (CEO) directive, 2026-09-18, "Review of the external feedback + directive to coder", section 1, verbatim:

> "**LXXIX — FRESH-PROBLEM GENERALIZATION.** Capability claims require
> blind problems: not authored, tuned, or selected to match the pipeline;
> corpus-disjointness test-enforced against R446/R412/R458/R492-DEV/sealed
> corpora; family-declared at submission; single-shot or fixed-budget with
> *all* attempts recorded (zeros are data). Tuning between scored problems
> voids the battery."

### The correction this article makes

Article XLIX demands 10 problems across 6 domains for a behavioral discovery
claim — but nothing requires those problems to be **blind**. Every corpus the
machine has been scored on to date passed through machine or operator hands
that knew the pipeline: problems can be (even unintentionally) authored,
tuned, or selected to be pipeline-friendly — well-formed, span-friendly,
mechanism-space-friendly. The R489 cross-domain attempt additionally
disclosed the submission-path gap: the family can be absent from the run's
own record (`canonical_family null`), making family-level claims
unverifiable from the run bytes alone. A multi-problem claim over
pipeline-adjacent fixtures is generalization theater.

### The rule

> **A discovery-capability claim requires blind fresh problems.**

**Blind** means all of:

1. **Not authored, tuned, or selected to match the pipeline.** Problems come
   from sources outside the machine's own generation, and the selection rule
   is pre-registered (hash-frozen) before any problem is submitted. A problem
   whose wording, structure, or evidence surface was adjusted after seeing
   pipeline behavior is void.
2. **Corpus-disjointness is test-enforced** against every standing corpus:
   `R446`, `R412`, `R458` (incl. its DEV split), `R492-DEV`, and the sealed
   corpora. The disjointness check runs mechanically before submission and
   fails closed; a problem that overlaps a standing corpus is rejected by
   the check, not by judgment.
3. **Family-declared at submission.** The problem payload carries its domain
   family so the run's own bytes can prove the family claim (closing the R489
   submission-path gap by construction).
4. **Single-shot or fixed-budget, all attempts recorded.** Zeros are data.
   An attempt that produced nothing is published with the same fidelity as
   an attempt that produced a survivor. Selective publication of attempts is
   benchmark gaming (Art. LIX) at the attempt level.

**Tuning between scored problems voids the battery.** All tuning touches
DEV/frozen corpora only, never the scored set (Art. LIX discipline applied
to problem sets). A battery in which any gate, prompt, threshold, retrieval
form, or model selection changed between scored problems is VOID — the
measurements stand only as un-scored history.

### Relationship to existing articles

- Extends Article XLIX (multi-problem discovery) with the blind-source
  requirement it presupposes.
- Extends Article LIX (no benchmark gaming) from parameters to problems.
- Extends Article XXXIII/XXVII: pre-registration is the evidence ledger that
  makes the battery's irreversible scoring act lawful.
- The R489 cross-domain comparison note ("future cross-domain proofs should
  submit with the family carried in the problem payload") is hereby
  constitutionalized as clause 3.

### Machine-enforcement points

1. The battery driver records, per problem: the pre-registered selection-rule
   hash, the disjointness-check verdict, the declared family, and every
   attempt (including zeros) — all hash-pinned before the first submission.
2. The disjointness test is part of the battery's acceptance; a battery whose
   disjointness cannot be re-run by a second container is void (Art. LXII).
3. Mid-battery changes are prevented by the freeze rule: gates + instrument
   are frozen for the battery's duration; the drop-off table is the
   deliverable, not a to-do list for the battery's own run.
