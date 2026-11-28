# Article LXXXVI — The Invention Gate (Holdout)

**Ratified:** 2026-11-14 (Round R11)
**Amends:** Constitution v2.10.1 -> v2.11.0
**Full text:** `R11/constitution/ARTICLE_LXXXVI_THE_INVENTION_GATE.md`
**Sponsor:** Operator audit directive, 2026-11-14, item 9 ("NEW GATE
FOR THE HOLDOUT: an arm must beat the baseline on invention-rubric
NOVELTY by >=0.5 with feasibility within 0.25 of the baseline,
auditor-judged on >=10 pairs. Beating the baseline on format does not
count.")

### The correction this article makes

The previous holdout gate — wins+ties vs baseline >= 50% with >= 1
win — is PASSABLE BY A BASELINE CLONE. The owner's audit measured it:
the A0+ arm's body was the baseline text verbatim with a header and
relabels, and it cleared the old gate on format. A gate that a copy
of the baseline can pass measures nothing about invention.

### The rule

> **The holdout gate is an INVENTION gate: an arm must beat the
> baseline on invention-rubric NOVELTY by >= 0.5 (mean over the
> judged pairs) with FEASIBILITY within 0.25 of the baseline,
> auditor-judged on >= 10 pairs. Beating the baseline on format does
> not count.**

1. The invention rubric is the four-axis 0-4 instrument (novelty vs
   the standard solution / feasibility / testability / constraint
   compliance — `discovery_fabric/engine/invention_rubric.py`).
   Correctness scoring stays separate and keeps its own gates.
2. The gate is AUDITOR-JUDGED. Machine judgments (the calibrated
   judge, the coder-deterministic rubric scores) are INPUTS and ride
   every record disclosed; they never constitute the gate verdict
   (Article XXVI: no self-certification).
3. Threshold provenance (Article XXVII): both thresholds are the
   owner's directive (2026-11-14, item 9), class BUYER_DEFINED,
   disclosed with uncertainty (mean over >= 10 pairs).
4. Until >= 10 auditor-judged pairs exist, the gate state is
   PENDING_AUDITOR_JUDGMENTS — never MET, never inferred
   (Article XXV).

### Deletion accounting (Article LXIV)

The replaced gate (wins+ties >= 50% with >= 1 win) is RETIRED, not
silently dropped: its definition, its replacement, and the audited
defect that retired it are recorded here and in
`discovery_fabric/engine/holdout_gate.py` (the `replaced_gate` block
rides every gate evaluation).
