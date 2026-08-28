# Human Spot-Check Protocol (Coder 2 Phase 3, B11)

## Purpose

An external human technical reviewer audits a small random sample of the
generated dossiers' reasoning chains. This is the external counterweight
to the automated semantic audits (B3/B4/B9): where a machine verdict and
a human verdict disagree, the DISAGREEMENT is preserved — neither side
overwrites the other.

## What the reviewer inspects

Each queue item is one reasoning chain, presented as four links:

    claim  ->  source  ->  engineering interpretation  ->  design implication

* **claim** — what the dossier asserts (a governing relation, a physical
  failure mechanism).
* **source** — the evidentiary basis the dossier itself cites (the cited
  engineering principle, the input evidence record, the mechanism source
  span).
* **engineering interpretation** — how the dossier interprets that source
  (the equation model and its stated applicability/assumptions, or the
  failure trigger and detectability).
* **design implication** — what the dossier does with it (the design
  output that consumes the relation, or the design control and
  verification test for the failure).

## Verdict vocabulary (exactly one per item)

* `HUMAN_CONFIRMED` — the engineering interpretation follows from the
  cited source, and the design implication follows from the
  interpretation.
* `HUMAN_DISPUTED` — the interpretation does not follow from the source,
  the source does not support the claim, or the implication does not
  follow (rationale REQUIRED).
* `HUMAN_UNCERTAIN` — cannot be determined from the provided materials
  (say what additional evidence would settle it).

## Hard rules

1. Human review is **external evidence**. It is NEVER converted into an
   automated score, NEVER folded into any pass/fail verdict, and NEVER
   averaged into a metric. Aggregation is counts only.
2. Reviewer verdicts are recorded append-only
   (`HUMAN_SPOT_CHECK_RESULTS.json`). The queue is never mutated.
3. Disagreements with automated audit verdicts are preserved and fed to
   the B9 disagreement register.
4. No verdict is fabricated. Until a human reviews, items stay
   `PENDING_HUMAN_REVIEW`.

## How to submit

Fill, for each reviewed item, the four reviewer fields in the queue JSON:

```json
{
  "item_id": "HSC-001",
  "reviewer_verdict": "HUMAN_CONFIRMED | HUMAN_DISPUTED | HUMAN_UNCERTAIN",
  "reviewer_id": "<reviewer identity>",
  "reviewed_at": "<timestamp>",
  "reviewer_rationale": "<1-3 sentences; REQUIRED for HUMAN_DISPUTED>"
}
```

Return the filled rows (any format — JSON list, CSV, or inline text).
Coder 2 ingests them via `discovery_fabric.benchmark.human_spot_check.
ingest_verdicts`, which validates the vocabulary, refuses duplicates,
and reports counts only.

## Blind stratum

A second queue sampled from the blind dossiers exists in CEO custody
(`HUMAN_SPOT_CHECK_QUEUE_BLIND.json`, outside this repository). Its
content never enters the repository; verdicts for it are recorded in the
same results file with `HSC-BLIND-*` ids.
