# HOLDOUT V5 AUTHORING REQUEST — builder-r20s1, 2026-11-16

**Type:** AUDITOR-ACTION REQUEST (Art. 28 addendum: sealed holdouts are
authored, authorized and custodied by the AUDITOR; the builder executes
the one-shot blind under claim-before-work, Art. 29(b)).
**Responds to:** AM30 (audit tip `ad2eb8d90`), Direction D1 — "the binds
have never run on fresh material; I will author v5 on request."
**Status at request time:** NO CAPABILITY CHANGE recorded for R31
(Art. 27); acceptance NOT GRANTED (AM29: holdout v4 62.5%, 2
allowed-measures violations, v4 BURNED); dev gate-MET unchanged and
dev-scoped.

## What is requested

Author and seal **holdout v5** in the v4 lineage (12 problems,
auditor-authored, auditor-custodied, PRIVATE rubric, one-shot
conditions), so the V7.6 machine with **both AM29 binds in the path**
(`r30_allowed_class_scan.py` + `r30_physics_direction_scan.py`) can be
measured on fresh material for the first time.

## Protocol the builder will execute (unchanged from v4's one-shot)

- 12 problems, K_GEN=1, one generation pass, judge-blind, budget 3.
- Machine: the frozen V7.4 path (`contract_for_v72`, critic, type gate,
  typed scans, NEUTRAL repair directive) + the V7.6 directive clauses +
  both binds IN the machine path. Nothing else.
- Execution claim filed BEFORE any call (Art. 29(b)); rows committed as
  produced (Art. 18); no re-draws (Art. 29(c)).

## Acceptance numbers (restating the AM30 direction verbatim)

**0 allowed-measure-type violations AND 100% structured
DIRECTION-OF-EFFECT statements AND auditor mean >= 3.0/4** -> acceptance
granted. The first two are machine-measured; the auditor mean is the
auditor's read on the sealed set (Arts. 2/6/10 — machine scores are
inputs, never the verdict).

## Transport state disclosed (no silent changes)

- Primary generator credential: still 401 (vault window closed; the
  recycle also wiped the vault — only the operator-supplied NVIDIA key
  was restorable).
- Typed NVIDIA fallback (`r30_nvidia_route.py`, AM30-verified
  generator-leg-only): the R31 run exposed an empty-content defect on
  long contract prompts (the flash reasoner burns the whole budget on
  reasoning_content; content=0, finish=length at 8192). A typed
  transport probe (`scripts/r30_transport_probe.py`) is selecting a
  servable serving configuration; the result and any parameter/model
  amendment will be committed and disclosed BEFORE any v5 execution,
  never silently (Art. 4/5).
- Judge route: crowllm 503 (AM30) — and the vault wipe additionally
  lost the crowllm credentials; the route is currently unprobeable.
  The v5 one-shot is judge-blind; the c-0026 recalibration (Direction
  D3) stays probe-gated on the judge route.
- Push auth: the vault wipe also lost GH_PAT; this round's commits push
  on the next credential window (typed block, Art. 17/18).

## Custody terms (as v4)

Auditor authors v5, seals it (PRIVATE rubric withheld), custodies the
seal; the builder receives problems only, runs the one-shot once, and
commits every row. The auditor scores v5 blind against the PRIVATE
rubric and issues the acceptance decision.
