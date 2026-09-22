# Proposed Constitutional Amendments — External Auditor Draft (Revision 2)

**Drafted:** 2026-09-22, against `EPISTEMIC_CONSTITUTION.md` v2.10.1 (`origin/main` @ `185a2d44`)
**Revised:** 2026-09-22, incorporating corrections from a peer review of Revision 1
**Status of every article below:** PROPOSED — none are ratified. None should be treated as binding until the operator ratifies them, one at a time, the way Article LXXI and Article LXXXV were ratified.

---

## What changed between Revision 1 and Revision 2

A peer audit of Revision 1 was conducted independently and returned four concrete findings. All four were validated against the actual repository bytes before incorporation:

| Finding | Verified against | Valid? | Action |
|---|---|---|---|
| My "working default: any nonzero attack_survivors" in LXXXIX directly conflicts with Article XXVII | `EPISTEMIC_CONSTITUTION.md` line 857 ("A threshold that appears because 'it seems reasonable' is forbidden") | ✓ Confirmed | LXXXIX rewritten — default removed entirely |
| LXXXVI's prohibition should target the **behavioral claim**, not every commit, to avoid making record-only corrections noncompliant | LXXXVI's own Section 3 wording | ✓ Valid | Section 3 reworded |
| `engine_compute_s` is ambiguous — includes provider queueing, transport, inference; categories must be mutually exclusive with a provable sum identity | LXXXVIII's own definitions | ✓ Valid | Categories renamed and sum invariant made explicit |
| `ACTIVE_DISCOVERY_GRAPH.json repo_head = 5416bb4f` vs `origin/main = c02535fe` — stale; needs an architecture-provenance validation rule | `git show origin/main:ACTIVE_DISCOVERY_GRAPH.json` | ✓ Confirmed stale (9 commits behind); delta is records/governance/scripts only — no engine changes — so graph is stale on SHA but not wrong about architecture | New Article XC added |

The R516 "NO SPEED CLAIM / underpowered" language cited by the peer review was also confirmed verbatim in `R516/R516_ROUND_RECORD.json`: *"NO SPEED CLAIM: paired means flat within noise; served generations vary widely live (26-213 s); one transport stall confounds run #3-after."* That language supports LXXXVI's motivation and is now cited explicitly.

---

## Recommended ratification sequence

**LXXXVI → LXXXVII → LXXXVIII → LXXXIX → XC**, one round each, in order.

LXXXVI first because its mechanical validator is the enforcement surface that makes every later article auditable by more than prose. Do not ratify LXXXVII–XC before LXXXVI's validator exists. Ratifying all five in one commit would itself violate the discipline LXXXVI establishes.

**Before ratifying each article**, the operator must supply — for LXXXIX specifically — the ratified funnel-maturity threshold (see Section 1). No default is implied and none may be invented. The article cannot be activated without that operator input.

---

## Article LXXXVI — The One-Cliff Discipline Is Binding, Not Optional

**Status:** PROPOSED — pending operator ratification
**Would amend:** Constitution v2.10.1 → v2.10.2
**Sponsor:** External auditor draft, 2026-09-22, Revision 2

### Motivation

Before this article, the one-cliff discipline existed only as an unwritten operator convention in `GOVERNANCE/`. A coder instructed to "read your constitution" would not find it. Two incidents demonstrate why that is insufficient:

1. R511 measured RETRIEVE as the dominant latency sink and explicitly authorized one optimization against it. R513 — the immediately following round — fixed a different, much smaller bottleneck instead (~16s saved against 12–84 minute runs). The authorized cliff was deferred without explanation.

2. R516's before/after comparison used two different n=6 batteries under different conditions. The round record itself states this explicitly: *"NO SPEED CLAIM: paired means flat within noise... wall reduction is NOT demonstrated in this window"* and characterises the comparison as "underpowered vs ~100 s live variance." Nothing in the constitution stopped the comparison from being filed at all, only from being overclaimed.

### The rule

> Every optimization round follows exactly one sequence: **fresh controlled battery → durable funnel or latency measurement → name the single largest valid dropout → one fix, and only one → identical battery, re-run → publish before/after → name the next cliff.**

### Section 1 — What "one fix" means

A round may act on exactly one named behavioral cliff. A second opportunity found mid-round is recorded in the round record and deferred to the next round; it may never be folded into the current push. 

"One fix" applies to behavioral changes. Record-only corrections, generated-artifact regeneration, CI-only changes, and administrative maintenance may accompany a behavioral round in the same commit provided they do not change the measured variable and are explicitly labeled as non-behavioral in the round record. The round record must name both the behavioral change and any accompanying non-behavioral commits, so the line between them is auditable.

### Section 2 — What "controlled" means

A before/after comparison is controlled only if:
- the same battery (identical problems, identical count, pre-registered under Article XXXIII) runs under both conditions
- the only variable that changes between arms is the fix itself
- the report states sample size and variance explicitly, not a bare delta

Two batteries run on different problem sets, at different times, or with different counts are two independent measurements. They may inform a hypothesis but must be labeled `UNCONTROLLED_COMPARISON` and may not be reported or cited as a before/after result.

### Section 3 — What is noncompliant

The enforcement target is the **behavioral claim**, not Git commit topology. A round record is `NONCOMPLIANT` when:

```text
named_cliff is absent
OR controlled_comparison is absent when a fix is claimed
OR battery is absent
OR before/after is absent when a fix is claimed
OR sample_size and variance are absent
```

Administrative commits accompanying a compliant round record are not noncompliant by their presence. A behavioral round with no round record at all is noncompliant by omission (see Article LXXXVII Section 1).

### Section 4 — Mechanical enforcement requirement

This article must not be ratified without a mechanical round-record validator being created in the same ratification round. The validator is the enforcement surface for this article and for every later amendment that cites `NONCOMPLIANT` as a sanction. Prose-only governance is insufficient.

The validator rejects a round record before merge when any field listed in Section 3 is missing. Its own implementation must satisfy Article XVI: the validator code is a hypothesis; its test suite is the evidence.

---

## Article LXXXVII — Deployment-Identity Records Are Round-Record-Bound and Append-Only

**Status:** PROPOSED — pending operator ratification
**Would amend:** Constitution v2.10.2 → v2.10.3
**Extends:** Article LXXI (The Deployed Production URL Is the Delivery Standard)
**Sponsor:** External auditor draft, 2026-09-22, Revision 2

### Motivation

Article LXXI mandates that every code-producing round carry a `production_deployment` tuple with `target_sha`, `deployed_sha`, `health_check_result`, and `drift`. It does not say what happens when a behavior-bearing round reaches `origin/main` with no round record at all, and it does not govern deployment-tracking artifacts that exist outside that tuple.

Both gaps were exploited by the same commit: R518 pushed a provider-routing change with no `R518_ROUND_RECORD.json`, and in the same commit overwrote `R512/SPACE_DEPLOY_RECORD.json` — a file with no constitutional status, no schema, and no `health_check_result`/`drift` fields — replacing the verified R516 deployment entry (`47e12a2d`, confirmed GREEN in R516's own close record) with content whose `ab_basis` text was reused byte-for-byte from an entry about a different commit. R519 independently caught and corrected this before this article was drafted. The article is proposed as a structural safeguard against recurrence, not because the incident is still open.

### Section 1 — Silence is noncompliance

A behavior-bearing coder round — a commit or commit sequence that changes engine, routing, or deployment-affecting code — that reaches `origin/main` without a corresponding compliant `{ROUND}_ROUND_RECORD.json` is `ARTICLE_LXXI_NONCOMPLIANT` by omission. 

The constitutional unit is the **round**, not the commit. Mechanical follow-up commits, merge/reconciliation commits, generated-artifact regeneration, CI-only corrections, and record-only corrections may reach `origin/main` without their own round records, provided they are labeled as non-behavioral and accompany or follow a compliant round record for the round they belong to.

### Section 2 — Deployment-identity records are append-only

Any file whose stated purpose is to record deployment history must be append-only: each deployment event is a distinct entry, never an in-place overwrite of a prior one. A file that has been overwritten in place loses standing as a deployment-history authority from that point forward. It must be migrated to an append-only form (one entry per deployment event, keyed by timestamp and commit) before it may be cited in any round record or audit verdict.

### Section 3 — One canonical authority

The single authority for "what commit is currently deployed" is the `production_deployment` tuple in the most recent compliant round record (Article LXXI §2). Any other file that also claims to track deployment identity is informational only and may not be cited in an audit verdict as proof of production state unless it independently carries `health_check_result` and `drift` fields that match Article LXXI's schema.

---

## Article LXXXVIII — Latency and Wall-Clock Claims Must Be Attributed Before Use

**Status:** PROPOSED — pending operator ratification
**Would amend:** Constitution v2.10.3 → v2.10.4
**Sponsor:** External auditor draft, 2026-09-22, Revision 2

### Motivation

This article closes a gap that produced an incorrect auditor finding during the same session that proposed these amendments, and is cited here rather than hidden.

A review of R513's 5-case battery reported "12–84 minutes, a 7x spread" as an engine-reliability finding. Checking clarification timestamps directly against the durable record showed 54.3 of case A's 83.8 minutes were `harness_wait_s` — the human operator had not yet answered a clarification prompt. The remaining cases cleared clarification in under a minute. The corrected engine-time spread across all five cases was 11.1–31.6 minutes (2.8x). Had the decomposition this article requires been in place, the inflated finding would not have been written.

The categories below incorporate a refinement from the peer review of Revision 1: `engine_compute_s` was renamed to `model_call_wall_s` because API call elapsed time includes provider queueing, transport, inference, and response transfer — calling it "engine compute" is ambiguous and overstates what is actually measured.

### The rule

> No wall-clock duration may be used to support an optimization, regression, or reliability claim until it has been decomposed into the named categories below. An undecomposed total is a raw observation; it may be recorded but must not be characterised as "engine time," "run time," or any other category until the decomposition is performed.

### Section 1 — The required decomposition

Any reported run duration must separate, at minimum, the following **mutually exclusive, exhaustive** categories:

```text
model_call_wall_s    — elapsed wall time of all LLM/model/API calls made,
                       from request dispatch to response receipt, inclusive
                       of provider queueing, transport, inference, and
                       response transfer; does NOT include harness setup
                       before the call or processing after it

harness_wait_s       — time spent waiting on a human or scripted operator
                       action (e.g. a clarification answer, a manual
                       approval step); no engine code runs during this time

retrieval_network_s  — wall time of evidence-retrieval fan-out (web
                       searches, database queries, external fetches)
                       outside the model_route call log

internal_engine_s    — all remaining in-process engine time not covered
                       above: parsing, state machine transitions, gate
                       evaluation, record writes, serialisation

unattributed_s       — the residual after all above are accounted for;
                       must be reported explicitly, never omitted
```

### Section 2 — The sum invariant

The following must hold, within a stated timing tolerance:

```text
total_wall_s == model_call_wall_s
             + harness_wait_s
             + retrieval_network_s
             + internal_engine_s
             + unattributed_s
```

`unattributed_s` is not a vague residual — it is a mechanically testable accounting balance. A battery result whose categories do not satisfy this invariant (within tolerance) is labeled `ATTRIBUTION_INCOMPLETE` and may not be used to support a performance claim until the gap is closed.

### Section 3 — Scope

This applies equally to coder-produced performance claims and to auditor-produced ones. Neither is exempt, including any that predate this article. Prior performance claims not accompanied by a valid decomposition must be re-labeled `UNDECOMPOSED_OBSERVATION` rather than treated as settled performance evidence.

---

## Article LXXXIX — Discovery-Fidelity Grading Is Gated Behind a Ratified Funnel-Maturity Threshold

**Status:** PROPOSED — pending operator ratification — **requires operator to supply the funnel-maturity threshold before activation**
**Would amend:** Constitution v2.10.4 → v2.11.0
**Sponsor:** External auditor draft, 2026-09-22, Revision 2 (substantially rewritten from Revision 1 to remove an invented default threshold that violated Article XXVII)

### What changed from Revision 1

Revision 1 contained this sentence:

> "Until the operator names that number, the working default is: any nonzero, reproducible `attack_survivors` rate on a fresh-problem battery."

That sentence violates Article XXVII ("A threshold that appears because 'it seems reasonable' is forbidden"). The peer review of Revision 1 identified the conflict precisely and correctly. The sentence has been removed entirely. No default threshold exists. The operator must supply one before this article can activate downstream grading.

### The rule

The WORLD_CLASS_DISCOVERY_GATE remains fully binding as constitutional law. However, **the grading and scoring of discovery-fidelity requirements whose evidentiary bar presumes candidates routinely reach `attack_survivors` or later in the Article LXXVII funnel is deferred until an operator-ratified funnel-maturity threshold has been met.**

This is a grading deferral. It is not a repeal, weakening, or suspension of the underlying constitutional requirements. The requirements remain binding. Only their grading against the current funnel state is deferred.

### Section 1 — The funnel-maturity threshold

The operator must explicitly ratify the quantitative or categorical funnel-maturity threshold before downstream fidelity grading is permitted. **No default threshold is implied.** The machine, coder, and auditor must not invent a temporary threshold to permit downstream scoring. Article XXVII remains fully controlling.

The ratified threshold must specify:

1. the required funnel transition(s) (e.g. "at least N candidates reach `attack_survivors`")
2. the minimum acceptable rate or categorical condition
3. the minimum number of fresh controlled batteries over which it must hold
4. explicit provenance and rationale for the threshold — why this threshold and not another

Until the operator supplies and ratifies those four elements, this article's grading deferral remains permanently active.

### Section 2 — What remains fully active before the threshold is met

Nothing in this article weakens requirements governing the earlier funnel stages. The following remain fully binding at all times:

Articles I–XX (evidence grounding, mechanism representation, epistemic hygiene), Article XLI (mechanism representation), Article XLII (mechanism distinctness), Article XXVII (no threshold invention), Article XXXIII (battery pre-registration), Article LXXVII (funnel as the only valid discovery-evidence signal), Article LXXVIII (survivor credit only via mechanically recorded gate survivals), Article LXXIX (blind fresh-problem generalization for capability claims).

### Section 3 — Audit behavior before the threshold is met

Before the ratified funnel-maturity threshold is met, an audit reports:

```text
current funnel position (per Article LXXVII instrument)
largest measured dropout and its classification
measured attacker calibration state
fresh-problem reproducibility
unresolved evidence gaps
```

The audit does not assign a downstream discovery-fidelity score. A downstream requirement may be reported as:

```
MATURITY_GATED — INSUFFICIENT_FUNNEL_REACH
```

rather than as failed, passed, or partially scored. The gate itself is never reported as passing on the basis of narrative assertion.

### Section 4 — Activation

Once the operator-ratified maturity threshold is met and sustained for the required number of controlled batteries, downstream WORLD_CLASS_DISCOVERY_GATE grading becomes active. Activation must be derived from durable funnel measurements against the ratified threshold — not from a narrative claim that the threshold has been reached.

---

## Article XC — Architecture Records Must Match the Commit That Produced Them

**Status:** PROPOSED — pending operator ratification
**Would amend:** Constitution v2.11.0 → v2.11.1
**Sponsor:** External auditor draft, 2026-09-22, Revision 2 — this article was not in Revision 1; it was added after the peer review identified a stale `repo_head` in `ACTIVE_DISCOVERY_GRAPH.json`

### Motivation

`ACTIVE_DISCOVERY_GRAPH.json` currently records `repo_head = 5416bb4f` while `origin/main` is `c02535fe` — 9 commits behind. Verification against `git diff 5416bb4f c02535fe` confirms the 9-commit delta is records, governance docs, and scripts only; no engine or UI files changed, so the graph accurately reflects the current architecture despite the stale SHA. That means the risk is not a wrong graph today — it is that this is an undetected and undetectable gap unless someone checks manually. The `scripts/r515_regenerate_architecture.py` regeneration mechanism exists exactly to prevent this, but there is no rule requiring it to be run when the graph would diverge.

This is distinct from deployment identity (Article LXXI) and from audit authority (Article LXXXV). It is **architecture provenance** — the graph records what the system's stage chain and adapter structure actually is, and a stale SHA means the record cannot be verified as current without checking the diff manually every time.

### The rule

Any committed file that records architecture state (stage chain, adapter ordering, module graph, dependency structure) and carries a `repo_head` field is invalid as an architecture-provenance artifact when:

```text
record.repo_head != origin/main HEAD at the time the record is read
AND
the delta (git diff record.repo_head origin/main) touches any file in the architecture's scope (engine, UI, stage ordering, adapters)
```

A stale `repo_head` combined with a scope-clean diff is labeled `ARCHITECTURE_STALE_BENIGN`: the graph is accurate but the provenance is unverified. It may be cited as current architecture but must be regenerated before the next round closes.

A stale `repo_head` combined with any scope-affecting diff is labeled `ARCHITECTURE_STALE_INVALID`: the record may not be cited as current architecture until regenerated.

### Section 1 — Regeneration requirement

When the round-record validator (Article LXXXVI Section 4) runs and finds `ARCHITECTURE_STALE_INVALID`, the round record is `NONCOMPLIANT` until regeneration is complete. `ARCHITECTURE_STALE_BENIGN` generates a warning but does not block the round.

The regeneration must use the project's own executable regeneration script rather than hand-editing the `repo_head` field or any other field in the architecture record.

---

*End of proposed amendments. Each is independently ratifiable. None modify `EPISTEMIC_CONSTITUTION.md` directly. All are explicitly marked PROPOSED. The operator may accept, reject, or return for revision any subset without affecting the others, subject to the sequencing note: LXXXVI's mechanical validator must exist before the later articles' `NONCOMPLIANT` sanctions are meaningful.*
