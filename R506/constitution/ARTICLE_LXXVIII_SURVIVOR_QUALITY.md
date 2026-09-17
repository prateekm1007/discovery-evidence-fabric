# Article LXXVIII — Survivor Quality: What Counts as a Surviving Invention

**Status:** DRAFT FOR OPERATOR RATIFICATION (R506) — not yet law
**Proposed amendment:** Constitution v2.8.0 → v2.9.0
**Sponsor:** Operator (CEO) directive, 2026-09-18, "Review of the external feedback + directive to coder", section 1, verbatim:

> "**LXXVIII — SURVIVOR QUALITY.** Discovery credit accrues only to
> candidates surviving the domain-appropriate adversarial + evidence +
> contradiction + technical gates, each mechanically recorded (attack
> record, verification verdict, `blocking_count==0`, physics/technical
> evaluation). Candidate count, survivor-at-synthesis, and grid-advanced
> counts are never invention counts."

### The correction this article makes

The durable-run population measured by the R506 yield instrument shows the
failure mode concretely: SURVIVOR_SELECTION files rank 11 candidates with
`killed: false` while the same run's SURVIVOR_GATE records that discovery-
level verification was NOT re-run per grid candidate, and the run's primary
candidate died at the adversarial gauntlet (`obvious_combination: KILLED`).
A reader of the selection file alone would count 11 survivors; the bytes
support zero. "Survivor" today means at least three different things —
gauntlet survivor, grid-advanced candidate, selected-synthesis candidate —
and the most flattering one wins whenever the numbers drift.

### The rule

> **Discovery credit accrues only to a candidate that has survived — with
> mechanically recorded evidence for each — the domain-appropriate:**

```text
1. adversarial gate          (attack record with per-dimension verdicts)
2. evidence gate             (verification verdict; Art. I–III discipline)
3. contradiction gate        (blocking_count == 0, the engine's own check)
4. technical gate            (physics/technical evaluation on record)
```

**Each gate's verdict must exist as a machine-checkable record attached to
that candidate.** A gate that did not run is not a gate passed: its absence
types the candidate `INCOMPLETE_*` (Art. LXI), never surviving.

### Never counted as inventions

```text
candidate count at any stage
survivor-at-synthesis counts
grid-advanced counts          (exploration-grid advancement is transport to
                               the engineering gauntlet, not survival of the
                               discovery gauntlet — the SURVIVOR_GATE
                               resolution is the standing record)
package-emitted counts        (emission is a pipeline signal — Art. LXXVII)
```

### Relationship to existing articles

- Extends Article XLVIII (diversity measured, not counted) by defining what
  a *survivor* is before diversity can be measured over survivors.
- Extends Article LX (the classification ladder never moves on generated
  reports) with the concrete gate-verdict checklist.
- Extends Article LXI (infrastructure failure is never scientific rejection)
  in the inverse direction: a skipped gate is also never a scientific pass.
- The yield instrument (`R506/YIELD_INSTRUMENT.json`) is the standing
  mechanical implementation: `attack_survivors` counts the primary
  candidate's gauntlet outcome; `grid_advanced_not_counted` is recorded but
  never counted; `mutated_survivors` requires `delta_real` + re-evaluation
  with nothing inherited.

### No threshold invented

This article defines **what counts**, not **how many must survive**. Bars
stay where the R412 seal put them; quotas stay search budgets (Art. LXVIII).
Nothing existing is weakened.
