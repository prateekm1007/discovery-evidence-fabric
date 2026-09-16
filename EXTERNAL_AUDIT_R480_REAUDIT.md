# RE-AUDIT — TOSCANINI AT `e8c93e01` (R480)

**Auditor:** independent external systems / AI-research / reliability audit (second pass)
**Date:** 2026-09-16
**Baseline audit:** `EXTERNAL_AUDIT_R478_WORLD_CLASS_ASSESSMENT.md`, delivered at `17504061`
**Re-audited tree:** `e8c93e0116bc1bbee0fce77b45c2b44eff83580e` (= `origin/main`, verified `git ls-remote`)
**Working tree:** `f76cbcac` (my audit branch with `e8c93e01` merged in — confirmed `git merge-base --is-ancestor e8c93e01 HEAD` → true)
**Production:** `fbc73b859c68d18d407fbff7dbd6f015b3576f21`, `deployment_drift: GREEN`, `identity_tamper: false`
**`reviewer_provenance`:** `AI_REVIEW` (Article LXVII)

---

## 0. WHAT MOVED

`origin/main` advanced 6 commits since my baseline: `17504061` → `e8c93e01`.

| Commit | What it is |
|---|---|
| `ba8fce10` | **R478 code** — the first P0 tranche of engine changes |
| `185c103a` | R478 records — Phase-0 truth reconciliation of my ten claim classes |
| `5e23afca` | R479 code — deploy driver, operator credentials arrived |
| `fbc73b85` | R479 deploy-driver fix (README frontmatter / CONFIG_ERROR) |
| `1fdd00f2` | R479 records — delivery tuple closed, Space rev `756c854c` |
| `e8c93e01` | R480 — ZAI repointed onto the atria leg |

26 files changed, +2,370 / −51. Five engine/product files, one new 349-line test
file, and 15 record artifacts.

**Every claim below was re-measured on this tree in this session.** Nothing is
carried forward from my baseline report.

---

## 1. WHAT I VERIFIED AS GENUINELY FIXED

I did not accept the round records. I drove the real modules myself.

### 1.1 Contradictions now actually block promotion — PROVEN BY EXECUTION

My baseline finding §9 was: `contradiction_queue.py` is 2.3 KB of `add`/`to_dict`,
and contradictory user evidence changed visibility only.

R478 changed `ContradictionQueueAdapter` (`adapters.py`). I wrote my own probe
that drives the **real** adapters — not their fixture — and asked whether the
gate actually moves:

```
=== 5 support / 0 contra ===        === 5 support / 2 contra ===
  blocking_count: 0                   blocking_count: 2
  no_blocking_contradictions: True    no_blocking_contradictions: False
  inputs_sha256: b361ce87…            inputs_sha256: 7261eafd…
```

**The real `AdjudicationAdapter` flips the gate**, and because the check is
hash-bound (`adapters.py:1297-1299`, `inputs_hash: sha256_obj(env.contradictions)`)
the `inputs_sha256` changes with it. Contradiction → blocking → promotion held.
That is a real fix, and it is the load-bearing part.

Two user-evidence items entered the queue as `con:evidence:src-contra-0` and
`con:evidence:src-contra-1` with `unresolved_count: 2`.

### 1.2 The kill contract is now numeric — PROVEN BY EXECUTION

My baseline finding: `FALSIFICATION_THRESHOLD` was answered by a prose
composite with no number in it. I called `article_lii_contract` directly:

```
PROSE effect ("the device improves drainage markedly"):
   ACCEPTANCE_THRESHOLD        absent
   ACCEPTANCE_THRESHOLD_BLOCKER     PRESENT
   FALSIFICATION_THRESHOLD     absent
   FALSIFICATION_THRESHOLD_BLOCKER  PRESENT
   FALSIFICATION_BANDS         None

NUMERIC effect ("total flow reaches at least 40 mL/min"):
   ACCEPTANCE_THRESHOLD        PRESENT
   ACCEPTANCE_THRESHOLD_BLOCKER     absent
   FALSIFICATION_THRESHOLD     PRESENT
   FALSIFICATION_THRESHOLD_BLOCKER  absent
   FALSIFICATION_BANDS         ['40']
```

Prose now **fails closed**; the number travels **verbatim**, extracted not
computed. Article LII is genuinely better enforced.

*(Methodological note: my first attempt showed both cases blocking. That was my
fixture feeding the wrong field — the function reads `expected_effect` from
`survivor_architecture`, `experiment_selector.py:213`, not from `env`. I
corrected it and re-ran rather than reporting the null.)*

### 1.3 EIG inputs are state-derived, not literals — PROVEN BY EXECUTION

My baseline finding: the killer-experiment likelihoods were the constants
`0.85 / 0.15`. I measured the new `likelihood_basis` across two states:

```
0 contradictions → pressure 0.000  (inputs: unresolved 0, n_direct 5)
4 contradictions → pressure 0.444  (inputs: unresolved 4, n_direct 5)
formula: "p_reproduces = 0.85 - 0.20 x pressure;
          pressure = unresolved / (unresolved + n_direct_support)"
```

0.85 → 0.761. A genuine function of state, with formula, inputs and
`provenance: MODEL_DERIVED` recorded alongside — which is exactly what
Article XXVII asks for. The same treatment landed on the contradiction-action
EIG (`0.2 + 0.6 × severity_w × probability × quality_w × decision_impact`,
replacing my measured `0.5 × impact + 0.2`).

### 1.4 The fixes are DEPLOYED, not just committed

Article LXXI makes the deployed URL the delivery standard, so I checked:

```
adapters.py                 identical in production (fbc73b85)
experiment_selector.py      identical in production
nba_controller.py           identical in production
"R478 P0-2" markers in production adapters.py:  4
```

The R478 tranche is live on `prateekm1-toscanini-prod-validation.hf.space`.

### 1.5 No regressions

```
baseline 1750406:  173 failed, 3421 passed, 58 skipped, 37 errors   (409.62 s)
latest   e8c93e01: 173 failed, 3436 passed, 58 skipped, 37 errors   (417.10 s)

failures fixed since baseline:   none
new failures introduced:         none
```

+15 passing tests (the 13-test `test_r478_engine_p0.py` plus edits to two
existing files). Clean landing.

### 1.6 Their Phase-0 reconciliation is exemplary

`R478/PHASE0_TRUTH_RECONCILIATION.json` re-measures each of my claim classes
against the live tree with `file:line` evidence and types each
`VERIFIED / PARTIALLY_VERIFIED / NOT_RE_MEASURED`, with an explicit
`disposition` for each. It accepted A1, A2, A6, A7, A9, A10 as correct and
**did not claim to have fixed what it hadn't**. That is the constitutional
behaviour the Constitution asks for and it is worth saying plainly: most
repositories respond to an audit with rebuttal. This one responded with
re-measurement.

---

## 2. WHAT IS STILL BROKEN (re-measured, line-pinned)

### 2.1 The scheduled stage-drift fix did not land — P1

Their own A1 disposition: *"ACCEPTED. Fix scheduled R479 (registry
regeneration + the R433-style failing-test doc binding)."* R479 shipped.
The fix did not:

```
code STAGE_ORDER (adapters.py)                        16 stages
RUNTIME_CAPABILITY_REGISTRY.json stage_order_exact_per_D8   13 stages
ACTIVE_DISCOVERY_GRAPH.json executable_chain                13 stages
   repo_head: "post-490099e"                                (still stale)
ACTIVE_PATH.md:86-89                                        13 stages

IN CODE NOT IN DOC: ['PREMISE_GATE', 'MECHANISM_SPACE', 'PHYSICS']
```

All three canonical descriptions of the production path still omit three
stages that run in production. Unchanged from my baseline.

### 2.2 `reality_loop_ready` is still permanently false — P0

```python
# toscanini/server.py:344
_reality_ok = all((REPO_ROOT/"discovery_fabric"/"engine"/f).exists()
                  for f in ("loop_chain.py", "reality_ingestion.py"))
```

I evaluated it: **`False`** — `loop_chain.py` still absent (archived at
`82d67625`), `reality_ingestion.py` present. Production health agrees:
`"reality_loop_ready": false`, alongside `"product_status": "Discovery ready"`.
Unchanged.

### 2.3 P0-1 partially closed — README fixed, `ACTIVE_PATH.md` not

Progress: `grep -n "reality_loop\|reality_provider" README.md` → **clean**.
The README no longer names the deleted module.

But `ACTIVE_PATH.md` — the file that declares itself *"the single authority for
what the production path IS"* — still does, at lines 38-39:

```
| Acquisition | `discovery_fabric/engine/reality_loop.py::acquire_nist_water_viscosity` | …
| Closure     | `discovery_fabric/engine/reality_loop.py::close_reality_loop` | …
```

and the module is still absent (`find` → nothing; `from discovery_fabric.engine
import reality_loop` → `ImportError`). The single `REAL_LOOP_VERIFIED` record
(`EVT-R390-NIST-WATER-VISC-310K`) is still unregenerable. **Half-fixed.**

### 2.4 The evolution loop is still gated behind failure — P0 (principled deferral)

```python
# discovery_fabric/engine/run.py:620
if not standard_path_packaged and _ev.evolution_enabled():
```

Unchanged. Their A2 disposition declines to land it without a live proof:
*"landing the code without the live proof would manufacture the exact
synthetic-loop class Art. XXXVII forbids."*

**I accept that reasoning.** It is the correct constitutional call and it is
better than shipping an unverified loop. But it remains the single largest
capability gap, and it is blocked on the same thing that blocks me: working
strong-model transport.

### 2.5 `WORLD_CLASS_DISCOVERY_GATE` still has no live implementation — P0

```
$ find . -iname "*world_class*" | grep -v '.git'
./archive/r455-lean/premium_package_factory/archive/gates/r370k_world_class_dossier.py
```

Live `.py` references remain two strings in `scripts/r444_round_record.py:178`
and `scripts/r445_round_record.py:137`. Unchanged.

### 2.6 Canonical state is still 228 rounds stale — P0

| Manifest | Measured now |
|---|---|
| `head_commit: dafdeb1a7377` | `e8c93e01…` |
| `tracked_file_count: 6615` | **8708** |
| Constitution `1.5.0` / `35 articles` | **2.5.0** / **72 article headings** |

Unchanged. Its own rule (*"no round may claim an artifact exists unless this
manifest can locate it"*) remains unsatisfiable.

### 2.7 The duplicate NBA scoring authority is still duplicated — P1

R478 improved `nba_controller.py` (added `input_basis`, `_measured_stage_seconds`,
bumped to 1.1.0) but did not remove the second copy of the formula:

```
orchestrator/next_best_action.py:34    raw = (self.expected_information_gain * …
nba_controller.py:86                   score = (expected_information_gain * …

nba_controller.py imports:  datetime, typing     ← not the canonical module
```

Still two implementations of one formula with no test pinning them equal.

### 2.8 None of the 27 genuine test failures were fixed

```
inventions/INVENTION_GENERATION_V3_MANIFEST.json   15 failures  (still)
webapp TechStage/DeepDive/PipelineStrip             6 failures  (still)
test_secret_scanning (own canary)                   1 failure   (still)
cost_policy_eligible KeyError + vocab drift        ~5 failures  (still)
```

### 2.9 NEW FINDING — `confidence_delta` is written and never read

R478's own code comment claims the queue payload carries the belief update
*"the rest of the chain consumes."* I tested that specific claim:

```
$ grep -rn "confidence_delta" --include=*.py . | grep -v archive | grep -v adapters.py | grep -v tests/
(no output)
```

**Zero consumers.** The number computes correctly and is a real function of
state — I measured `−0.0` at 5-support/0-contra, `−0.16` at 3/2, `−0.32` at
1/4 — but nothing downstream reads it. The blocking that genuinely works does
so through `blocking_count`, not through the confidence number.

This is the same defect class I flagged in my baseline as *"wired but not
authoritative."* It is minor — the load-bearing mechanism works — but the
comment overstates it, and a recorded number nobody reads is a standing
invitation for a future reader to believe belief-updates propagate when they
do not.

### 2.10 NEW FINDING — the R480 "provider" is an alias, not a new provider

R480 records: *"P0-5 closed GREEN by the operator's REPOINT — ZAI rides the
credited atria leg."* The repoint record is honest about what it did:

```json
"variables_set": {
  "ZAI_BASE_URL": "https://api.atria-asi.ai/v1/chat/completions",
  "ZAI_MODEL":    "Atria-Dawn-Preview"
}
```

Production health confirms the consequence:

```
llm_transport.provider       : "zai"
llm_transport.base_url       : "https://api.atria-asi.ai/v1/chat/completions"
last_probe.provider          : "atria"
last_probe.model             : "Atria-Dawn-Preview"
zai.available_models         : 1   → "Atria-Dawn-Preview"
atria.available_models       : 1   → "Atria-Dawn-Preview"
```

**Two provider labels, one model.** What genuinely improved is *capacity*: a
15-key atria ring (`ATRIA_API_KEY` … `_15`), with `ATRIA_API_KEY_8` honestly
excluded from selection per a measured `INVALID` verdict. What did **not**
improve is *model diversity* — still one `quality_tier: 2` model behind every
rung, and 9 providers still `NOT_CONFIGURED`. My baseline §"Model utilization:
3/10" therefore stands.

Also unchanged: `physics_ready: false`, `wired_solver_importable: false`.

---

## 3. MY OWN GAP, RESTATED

I still could not close audit §29 (a live end-to-end run **with real evidence**).
I re-ran the engine on the new tree:

```
elapsed 0.5 s · 34 artifacts · all 16 stage envelopes
failed_stages: {"RETRIEVE": "URLError: TLS/SSL connection has been closed"}
final_status:  MECHANISM_GENERATION_FAILED
cemetery_update: {"appended": false, "reason": "not a research kill …"}   ← still correct
```

Because retrieval died, `envelope_CONTRADICTION.json` came back empty and
`likelihood_basis: null` — the R478 code paths never engaged on a real run. So
**the R478 fixes are proven at unit level by my probes and by their 13 tests,
but not yet on a live evidence-bearing run.** Their own A8 says the same thing:
`PARTIALLY_VERIFIED — THIS session cannot re-measure it (CREDENTIAL_ABSENT)`.

We are blocked on the same missing input from opposite sides.

---

## 4. REVISED SCORECARD

| # | Benchmark | Baseline | **Now** | Movement and why |
|---:|---|---:|---:|---|
| 9 | Contradiction handling | 4 | **6** | Gate flip proven by execution; −2 because `confidence_delta` is dead and severity/probability are still declared constants (0.6 / MODERATE) |
| 10 | Experiment selection | 4 | **5** | Likelihoods state-derived; prose kill contract fails closed; −5 because NBA still doesn't consume the EIG engine |
| 14 | Adaptive orchestration | 3 | **3** | One of three templates now state-derived; controller still has zero callers; formula still duplicated |
| 15 | Model utilization | 3 | **3** | Capacity up (15-key ring); diversity unchanged (one model, aliased) |
| 22 | Reliability | 4 | **4** | 173 failures, none fixed, none introduced |
| 24 | Technology transfer | 7 | **7** | Unchanged |
| — | all others | — | **unchanged** | No measured change |

```
END-TO-END AI                    4/10   =
DISCOVERY ENGINE                 5/10   =
INVENTION ENGINE                 5/10   =
EVIDENCE ENGINE                  6/10   =
MECHANISTIC REASONING            5/10   =
ADVERSARIAL REASONING            6/10   =
EXPERIMENT ENGINE                5/10   ↑ (was 4)
CAUSAL LEARNING                  5/10   =
ADAPTIVE ORCHESTRATION           3/10   =
ENGINEERING ENGINE               6/10   =
REALITY BOUNDARY                 6/10   =
MODEL / AI INFRASTRUCTURE        3/10   =
RELIABILITY                      4/10   =
BENCHMARK INTEGRITY              5/10   =
CROSS-DOMAIN GENERALITY          3/10   =
TECHNOLOGY TRANSFER              7/10   =
──────────────────────────────────────
OVERALL                          4.9/10  (was 4.8)
```

**The score barely moved, and that is the honest result.** R478 fixed three
real things well. But three of them sat in benchmarks that were already
middling, and the five P0s that cap the system — the unregenerable real loop,
the dead readiness probe, the failure-gated evolution loop, the archived
world-class gate, the stale canonical state — are all still open. None of them
was scheduled for R478; A2 was explicitly deferred. So +0.1 is what one
well-executed tranche is worth against a system whose ceiling is set
elsewhere.

---

## 5. REVISED 9/10 BLOCKERS

| # | Blocker | Status since baseline |
|---|---|---|
| 1 | `REAL_LOOP_VERIFIED` record unregenerable | **half-fixed** (README clean, `ACTIVE_PATH.md:38-39` still cites it) |
| 2 | `reality_loop_ready` permanently false | **unchanged** |
| 3 | Evolution loop gated behind failure | **unchanged** (principled deferral) |
| 4 | `WORLD_CLASS_DISCOVERY_GATE` unimplemented | **unchanged** |
| 5 | Canonical state 228 rounds stale | **unchanged** |
| 6 | Portfolio 13/14 one domain family | **unchanged** |
| 7 | NBA is 3 templates; controller dead; formula duplicated | **partially improved** |
| 8 | 27 genuine test failures | **unchanged** |
| 9 | Stage-order drift in all three canonical docs | **unchanged** — was scheduled for R479 and missed |
| 10 | One underlying model behind every rung | **capacity improved, diversity unchanged** |

---

## 6. THE MINIMUM PATH, REVISED

Five of these are cheap and none requires new architecture:

1. **Regenerate the three stage-order artifacts from `STAGE_ORDER` and pin
   them with a test.** This was already accepted and scheduled. It is a script
   write plus one test. It closes blocker 9 and removes the "single authority
   is wrong" class entirely.
2. **Delete or repair the `loop_chain.py` probe** (`server.py:344`) and fix
   `ACTIVE_PATH.md:38-39`. Two-line edits closing blockers 1 and 2.
3. **Regenerate `CANONICAL_STATE_MANIFEST.json` at HEAD + a CI drift gate.**
   Closes blocker 5.
4. **Restore `inventions/INVENTION_GENERATION_V3_MANIFEST.json` or retire its
   suite** per Article LXIV.2, update the three webapp component pins,
   allowlist the secret-scanner canary. Closes 22 of 27 failures.
5. **Give `confidence_delta` a consumer, or delete it.** Do not leave a
   recorded belief number that nothing reads.

Then, and only then, the one item that actually decides world-class status:
**the live `V1 KILLED → V2 child` proof for the evolution loop.** That needs
working strong-model transport — which is the credential I still don't have.

---

## FINAL QUESTION, RE-ASKED

> **Does Toscanini currently qualify as a world-class end-to-end AI discovery
> and invention machine?**

# **NO** — but the direction of travel is now measurable

The verdict is unchanged and the score moved 4.8 → 4.9. That is not a
criticism of R478; it is an accurate reading of what one tranche can do.

**What changed my assessment of the *team*, though, is real.** I have now
watched this repository receive an external audit and respond by:
re-measuring every claim with `file:line` evidence, typing each
`VERIFIED / PARTIALLY_VERIFIED / NOT_RE_MEASURED`, landing three genuine
executable fixes with 13 targeted tests, deploying them and verifying the
deployment identity, introducing zero regressions, and explicitly declining to
ship a fourth fix because doing so without a live proof would violate its own
Article XXXVII. It also credited a blocker it could not clear rather than
quietly dropping it.

That is a rare and specific competence — the ability to be audited without
defensiveness. It is also, notably, *not* the same thing as being world-class
at discovery, which is the question I was asked.

**The honest summary:** the epistemic-integrity machinery remains genuinely
world-class and just got demonstrably better at letting contradictions block
promotions and refusing prose-only kill contracts. The discovery and invention
capability is still mid-tier, still single-domain, still running on one
free-tier model, and still cannot mutate a surviving candidate. Five of the
five P0s I raised are open or half-open. Two of them are two-line edits.
