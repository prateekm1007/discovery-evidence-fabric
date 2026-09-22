# Proposed Constitutional Amendments — External Auditor Draft

**Drafted:** 2026-09-22, against `EPISTEMIC_CONSTITUTION.md` v2.10.1 (`origin/main` @ `185a2d44`)
**Status of every article below:** PROPOSED — none of these are ratified. None should be treated as binding until the operator ratifies them, one at a time, the same way Article LXXI and Article LXXXV were.

**Update, same day (R519, prior to this doc landing):** the two specific incidents Article LXXXVII cites below have already been independently corrected — `R512/SPACE_DEPLOY_RECORD.json` has been reverted to the verified R516 state (`47e12a2d`), and `R518/R518_ROUND_RECORD.json` now exists with an honest `IMPLEMENTED_PERFORMANCE_HYPOTHESIS` / `NOT_RUN_CREDENTIAL_BLOCKED` classification instead of a silent gap. That's a good sign — it means the underlying discipline is sound even without these articles being ratified. It doesn't remove the case for ratifying LXXXVII, though: nothing currently *structurally* prevents the same class of corruption from happening again next round. The fix this time was a manual correction after the fact, not a rule that makes the corruption impossible to write in the first place.

**A note on process, before the articles themselves:** Article LXXXVI below (once ratified) would require exactly this — one cliff per round. Ratifying all four of these in a single commit would violate the discipline the first one establishes. Recommended order, each as its own round with its own record: **LXXXVI → LXXXVII → LXXXVIII → LXXXIX**, in that order, since LXXXVII and LXXXVIII cite incidents that LXXXVI's framing makes legible, and LXXXIX is the largest structural change and should land last, once the others are stable.

---

## Article LXXXVI — The One-Cliff Discipline Is Binding, Not Optional

**Status:** PROPOSED — pending operator ratification
**Would amend:** Constitution v2.10.1 → v2.10.2
**Sponsor:** External auditor draft, 2026-09-22 session, submitted for operator/coder review

### The rule

> Every optimization round follows exactly one sequence: **fresh controlled battery → durable funnel or latency measurement → name the single largest valid dropout → one fix, and only one → identical battery, re-run → publish before/after → name the next cliff.**

This is not new practice. R512's RETRIEVE parallelization (3-rep controlled A/B, -65.4%, deployed and verified live) followed it exactly. The round immediately after R511 named RETRIEVE as the measured latency sink and then spent its own optimization elsewhere (removing `MULTI_SOURCE_DISCOVERY`, saving ~16s against runs later measured at 12–84 minutes) — a real fix, but not the named cliff. R516's mechanism-generation comparison (2/6 → 0/6 across two different n=6 batteries) was written up as a before/after despite not being a controlled comparison; its own record says so, but nothing in the constitution stopped it from being read as a result.

Before this article, this discipline existed only as an unwritten operator convention in `GOVERNANCE/`. A coder instructed to "read your constitution" would not find it. It is now binding on both engineering-optimization rounds and discovery-funnel rounds alike.

### Section 1 — What "one fix" means

A round may act on exactly one named cliff. A round record proposing two independent fixes in the same push is non-compliant regardless of how small either fix is. A second opportunity found mid-round is recorded and deferred to the next round, never folded in.

### Section 2 — What "controlled" means

A before/after comparison is controlled only if: the same battery (identical problems, identical count) runs under both conditions, the only variable that changes is the fix itself, and the report states sample size and variance, not a bare delta. Two batteries run on different problem sets, at different times, are two independent measurements — they may inform a hypothesis, but must be labeled as uncontrolled and may not be reported as a before/after.

### Section 3 — Enforcement

A round record's evidence fields (per Article XVI's standard) must show one named cliff and, if a fix is claimed, a controlled comparison. A round record failing this is `NONCOMPLIANT`, not merely incomplete — the same severity Article LXXI already assigns to a deployment mismatch.

---

## Article LXXXVII — Deployment-Identity Records Are Singular, Append-Only, and Round-Record-Bound

**Status:** PROPOSED — pending operator ratification
**Would amend:** Constitution v2.10.2 → v2.10.3 (chained after Article LXXXVI)
**Extends:** Article LXXI (The Deployed Production URL Is the Delivery Standard)
**Sponsor:** External auditor draft, 2026-09-22 session — closes two gaps found auditing `R512/SPACE_DEPLOY_RECORD.json` and the R518 round

Article LXXI mandates that every round record carry a `production_deployment` tuple. It does not say what happens when code reaches `origin/main` with no round record at all, and it does not govern any deployment-tracking artifact that exists outside that tuple. Both gaps were exploited by the same commit: R518 pushed a provider-routing change to `origin/main` with no `R518_ROUND_RECORD.json` anywhere in the repository, and in that same commit overwrote `R512/SPACE_DEPLOY_RECORD.json` — a file with no constitutional status, no schema, and no `health_check_result`/`drift` fields — replacing a verified R516 deployment entry (`47e12a2d`, confirmed GREEN in R516's own close record) with content whose `ab_basis` text was reused, byte-for-byte, from an entry written a day earlier about a different commit. The result: the one file an auditor would check for "what's deployed" no longer agreed with the repository's own verified history, recoverable only by walking `git log`.

### Section 1 — No round record is itself a violation of Article LXXI

A commit reaching `origin/main` that changes engine, routing, or deployment-affecting code, with no corresponding `{ROUND}_ROUND_RECORD.json` in that commit or the one immediately following, is `ARTICLE_LXXI_NONCOMPLIANT` by omission. Silence does not exempt a round from the tuple requirement.

### Section 2 — Deployment-identity records are append-only

Any file whose purpose is to record "what commit is currently deployed" — whether or not it is the file named in Article LXXI — must be append-only: each deployment event is a new entry, never an in-place overwrite of a prior one. A file that has been overwritten in place loses standing as a deployment-history authority from that point forward and must be migrated to an append-only form (one entry per deploy event, keyed by timestamp and commit) before it may be cited again in any round record or audit.

### Section 3 — One canonical artifact

There is exactly one authority for "what is currently deployed": the `production_deployment` tuple in the most recent compliant round record (Article LXXI §2). Any other file that also claims to track deployment identity — including `R512/SPACE_DEPLOY_RECORD.json` in its current form — is informational only and may never be cited in an audit verdict as proof of production state unless it independently carries `health_check_result` and `drift` fields matching Article LXXI's schema.

---

## Article LXXXVIII — Latency and Wall-Clock Claims Must Be Attributed Before Use

**Status:** PROPOSED — pending operator ratification
**Would amend:** Constitution v2.10.3 → v2.10.4
**Sponsor:** External auditor draft, 2026-09-22 session — closes a gap that produced an incorrect auditor finding in this same session

### The rule

> No wall-clock duration may be used to support an optimization, regression, or reliability claim until it has been decomposed into named categories. An undecomposed total is not evidence of where the time went.

### Section 1 — The minimum decomposition

Any reported run duration must separate, at minimum:

```text
engine_compute_s   — summed latency of model/API calls actually made
harness_wait_s     — time spent waiting on a human or scripted operator action
                      (e.g. a clarification answer); not engine behavior
network_io_s       — retrieval/fan-out time outside the model_route call log
unattributed_s     — total_wall_s minus the above; must be reported, not hidden
```

A total that has not been broken down this way may be recorded as a raw observation but must not be characterized as "engine time" or "run time," and must not be used to compute a reliability spread between runs.

### Section 2 — Incident this closes

A review of R513's 5-case battery characterized case A's 83.8-minute total as engine behavior, producing a "12–84 minute, 7x spread" reliability finding. Checking clarification timestamps directly against the durable record showed 54.3 of those 83.8 minutes were `harness_wait_s` — a one-off delay answering a clarification prompt; cases B–E all answered in under a minute. The corrected engine-time spread across all five cases was 11.1–31.6 minutes (2.8x), not 7x. The smaller, real finding underneath it — a consistent ~9–16 minute `unattributed_s` per run — survived the correction and remains the open question. Had this decomposition been a standing requirement, the inflated finding would not have been written in the first place.

### Section 3 — Application

This applies equally to coder-produced performance claims and to auditor-produced ones. Neither is exempt, including any that predate this article.

---

## Article LXXXIX — Discovery-Fidelity Articles Are Gated Behind Funnel Maturity

**Status:** PROPOSED — pending operator ratification
**Would amend:** Constitution v2.10.4 → v2.11.0 (minor — restructures grading of the WORLD_CLASS_DISCOVERY_GATE section)
**Sponsor:** External auditor draft, 2026-09-22 session

### The problem

The WORLD_CLASS_DISCOVERY_GATE lists twenty checks spanning roughly Articles XLII through LXXIX — multi-domain discovery, attacker calibration, baseline supremacy, portfolio honesty, cross-domain reach, and more — with no stated prerequisite. Every one of those checks presumes candidates are reliably reaching the attack stage. As of the most recent measured funnel (R516), 0–2 of 6 fresh runs reach `mechanisms_found`, and no battery on record has ever produced a `buyer_ready` candidate. Auditing or building against calibration, portfolio diversity, or cross-domain reach right now answers a question the system cannot yet ask.

### The rule

> The WORLD_CLASS_DISCOVERY_GATE, and any article whose evidentiary bar presumes candidates routinely reach `attack_survivors` or later in the discovery-yield funnel (Article LXXVII), is **SUSPENDED from grading** — not repealed, not deleted — until a stated funnel-maturity threshold is met.

### Section 1 — The threshold

Suspension lifts when a controlled battery (Article LXXXVI's standard) shows candidates reaching `attack_survivors` at a rate the operator names as the maturity bar, sustained across at least two independent controlled batteries. Until the operator names that number, the working default is: any nonzero, reproducible `attack_survivors` rate on a fresh-problem battery.

### Section 2 — What stays fully active during suspension

Nothing about evidentiary rigor for the *earlier* funnel stages is relaxed by this article. Articles I–XX, Article XLI (mechanism representation), Article XLII (mechanism distinctness), and Article LXXVII (funnel as the only valid discovery-evidence signal) remain fully binding. A suspended article is one that presumes success *past* those stages — not one that governs them.

### Section 3 — What this changes for audits

An audit performed while the gate is suspended should not report a score or verdict against any suspended article. It should instead report funnel position: how far candidates get, and what the single largest measured dropout is (per Article LXXXVI). This is not a lowered bar — it is a refusal to grade against a bar nothing has reached yet, which is Article XXVII (No threshold invention) applied to the audit process itself.

---

*End of proposed amendments. Each is independently ratifiable — the operator may accept, reject, or send back for revision any subset without affecting the others, though the recommended order above should hold if more than one is accepted.*
