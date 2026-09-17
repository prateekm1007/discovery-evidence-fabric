# Article LXXVII — Discovery Performance Is Distinct From Pipeline Completion

**Status:** DRAFT FOR OPERATOR RATIFICATION (R506) — not yet law
**Proposed amendment:** Constitution v2.8.0 → v2.9.0
**Sponsor:** Operator (CEO) directive, 2026-09-18, "Review of the external feedback + directive to coder", section 1, verbatim:

> "**LXXVII — DISCOVERY PERFORMANCE IS DISTINCT FROM PIPELINE COMPLETION.**
> Completed execution, stage-completion rate, package emission, test
> passage, search/model-call counts, orchestration success are
> inadmissible as discovery evidence. Discovery claims require the yield
> instrument on fresh problems. Promotion on pipeline signals alone is a
> constitutional violation (cite XLVIII/LIX as basis, extend to metrics)."

### The correction this article makes

Six consecutive audit rounds converged on the same split: delivery and
integrity measure ≈8/10 while invention capability measures ≈4/10. The
machine reliably completes 17-stage pipelines; the modal fresh run ends
with the candidate killed pre-loop (`NO_CANDIDATES`, `DEFERRED_TO_KILL_POINT`,
`good_discoveries=[]`), yet every completed run produces stage-green bytes
that can be — and repeatedly have been — read as progress. The Discovery
Imperative already states the principle (candidate count ≠ invention count);
Articles XLVIII and LIX already forbid specific gamed counts and benchmark
tuning. What is missing is the **metric-level firewall**: nothing in the
constitution makes a *pipeline signal* inadmissible as *discovery evidence*
when it is dressed up as a different number.

### The rule

> **A completed execution is not a discovery. Pipeline completion signals
> are inadmissible as discovery evidence, whatever number they are carried
> in.**

The following are **inadmissible** as evidence that the machine discovered
anything:

```text
completed execution / all-stages-green
stage-completion rate
package emission (ZIP/PDF/3D artifact existence)
test passage / battery green counts
search-call, model-call, or token counts
orchestration success / transport health
candidate counts at any stage (already Art. XLVIII)
```

Discovery claims require **the yield instrument** (`R506/YIELD_INSTRUMENT.json`,
`scripts/r506_discovery_yield.py` — the frozen DISCOVERY YIELD funnel) run on
**fresh problems** satisfying Article LXXIX. The funnel's
`candidates_generated_distinct → attack_survivors → contradiction_survivors
→ experimentally_discriminated → mutated_survivors → buyer_ready` transitions
are the admissible chain; its per-transition drop attribution is the
admissible bottleneck evidence.

**Promotion on pipeline signals alone is a constitutional violation.** A
candidate, a capability, or a round may not be promoted, classified upward
(Art. LX ladder), or described as discovering/inventing on the strength of
pipeline signals alone.

### Constitutional basis

Extends the Discovery Imperative and Article XLVIII (invention diversity
measured, not counted) and Article LIX (no benchmark gaming) from candidate
counts and benchmark procedure to **every metric the pipeline emits**. This is
Article XXI (search count is not evidence) applied to the machine's own
production statistics: an internally emitted number is exactly as untrusted
as an externally emitted one.

### What this article does NOT do

- It does not forbid *measuring* pipeline health — delivery and integrity
  remain legitimate engineering dimensions (the audit itself scores them).
  It forbids those measurements **wearing discovery's clothes**.
- It does not ratify a survival threshold: no "N survivors = success" bar is
  introduced (Art. XXVII; quotas are search budgets, never bars — Art.
  LXVIII). The yield instrument measures; the owner judges.
- It does not touch any existing article. It adds a metric-admissibility rule.

### Machine-enforcement points

1. Any record, dashboard, dossier, or round summary that states a discovery
   or invention claim must cite a yield-instrument record (funnel rows on
   fresh problems), not pipeline counters.
2. The frozen instrument's hash is pinned in `R506/YIELD_INSTRUMENT.json`;
   any edit mints a new version, old measurements stand.
3. The WORLD_CLASS_DISCOVERY_GATE's "multi-domain discovery" and "mechanism
   distinctness" evidence must be yield-instrument evidence from the moment
   this article is ratified.
