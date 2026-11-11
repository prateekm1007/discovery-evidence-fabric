# R6 AUDIT — OWNER REPORT (2026-11-11)

Scope: every R6 audit P0/P1 code direction is now committed and pushed. What
remains is quota-dependent measurement and the auditor's holdout gate — no
code is outstanding on that side of the line.

## 1. Pushed chain (verified `git ls-remote origin main`)

Base: `b5ea85e9` (parallel-session work: run1 call-budget artifacts, suite
reconciliation, suite tally = 209 green / 44 red at `17872b168`, all 44
classified pre-existing). My chain on top, in order:

```
0a3194c6  fresh-run-2 measurement artifacts (983cad20404f, clean tree, workers=3)
0e125fbe  audit fixes: certification restored (live CAD kernel suite) + intervention instruments hardened
f85c05e0  P0-5/P0-6: composer subordination + answer-contract claim-level provenance
f9bdb0cc  P0-8/P0-9: run-identity isolation + ledger-anchored call-budget instrument
634fddfe  P1-11/P1-12/G: ablation judge binding, gateway atomic pacing, seeded-sweep strictness
074c0e1a  G-hygiene: two no-op ("or True") assertions replaced with real checks
2df5a9df  r401 shared-mechanism fixture vs hardened anchor gate (Art. VII resolution)
= origin/main  2df5a9df62d84ef418065ef03552a92471ec2374   (ls-remote verified)
```

The 7 commits were rebased onto `b5ea85e9` after a push race; local
pre-rebase hashes `f61b24a6`/`4ba5aced`/`19f251d5` were rewritten — the
pushed chain above is canonical.

## 2. Per-audit-item → article mapping

| Audit item | What was done | Commit | Constitution article served |
|---|---|---|---|
| A — certification | Certification workflow restored on the LIVE CAD kernel: `tests/test_r6_cad_kernel.py` (10 hermetic tests; G1 watertight asserted at its MEASURED value — OCCT duplicate-vertex disclosure, never recolored) | `0e125fbe` | Art. X (one authority, deterministic); Art. XXV (measured, never recolored) |
| B — intervention gates | Hardened: bare-phrase kill, 3-tier metric match, mandate-span overlap, unit-mismatch → typed UNCERTAIN, restates-kill veto, 3-token anchor domain; 21/21 gate tests green | `0e125fbe` | Art. X (deterministic instruments); Art. XIX (no threshold tuning to pass — the gate got stricter) |
| C — composer subordination | Composer can no longer answer before discovery eligibility: killed/rejected attacks → NO_ADMISSIBLE_CANDIDATES (zero LLM spend), typed COMPOSE status, answer_source labels on pairs; adversarial tests added | `f85c05e0` | Art. X; Art. XIX |
| D — answer contract | Claim-level provenance: per-parameter labels, lexical source support, digit-boundary user-citation checks; calibration rule = window+statistic+method; 29 contract + 10 adversarial tests | `f85c05e0` | Art. XXXVIII (every claim carries its evidence site) |
| F — call budget undercount | `scripts/r6_call_budget.py` v2: ledger-anchored distinct attempts by `generate_call_id` (retries, transport failures, provider fallbacks INCLUDED); missing stage evidence = NOT_MEASURED never zero; RETRIEVE measured from ledger; any NOT_MEASURED stage blocks the total; 11 tests; fresh2 artifact regenerated | `f9bdb0cc` | Art. XXV (unknown stays unknown); Art. LXI |
| P0-8 — run identity | Unique run root per measured attempt `RUNS_ROOT/<commit>/r{repeat}-{arms}-{utc19}`; children inherit via `--run-id` at both spawn sites; route probes stay commit-level; judge records carry `bound_inputs` (answer sha256s, evidence hash, judge route, `RUBRIC_VERSION "0-4-rubric/1"`); scoring gates usable/full_scoreable on BOUND_OK, counts INCOMPLETE_INPUT_MISMATCH / UNBOUND_LEGACY in the table; `_run_meta.json` run-scoped; 10 hermetic tests; runbook protocol | `f9bdb0cc` | Art. LXI (fresh-run discipline); Art. XXV |
| P1-11 — ablation grounding (H) | Every ablation judgment carries `judge_binding` (route, commit, rubric, calibration state+source, independence label, actionable=False); shared-family LABELLED, never silent; verdicts typed `..._PENDING_AUDITOR` or `DIAGNOSTIC_*` — nothing actionable in-harness until the auditor adjudicates | `634fddfe` | Art. XVII (calibration evidence); Art. XXV |
| P1-12 — gateway pacing (J) | Pacing is now an atomic FIFO slot queue: a slot's start is computed against the previous slot's reserved start; `lastStartMs` written AT SCHEDULE TIME (never at timer fire); 429 doubling applies from the next slot; `reservePacingSlot`/`_withPacingIntervalForTest` exported; concurrent test added (node-bound) | `634fddfe` | Art. X (one authority per rule) |
| G — sweep strictness | NEVER-READ denylist ENFORCED fail-closed (`BLOCKED_FORBIDDEN_FIELD_PRESENT`; field name reported, value never echoed); "unknown"/"" removed from clean classes (typed unknown bucket, excluded from BOTH metrics); "legit_intervention" added to clean set; incomplete rows typed (`INCOMPLETE_*`, run outcome `PARTIAL_WITH_INCOMPLETE_ROWS`); per-instrument catch/FPR over complete rows only; prefix-match carries explicit weaker-than-full disclosure; pre-existing `anchor_domain_check` arity bug fixed (3-arg, verdict key `ok`, unmeasurable without problem-domain context) | `634fddfe` | Art. XXV (unknown ≠ clean control); Art. XXV/LXIV |
| G hygiene — no-op tests | Two `or True` no-op assertions removed: sweep prefix test now asserts the typed BLOCKED outcome; stale-run test now asserts no stale-content leak | `634fddfe`, `074c0e1a` | Art. XXV |
| Item 1 — fresh re-run | Fresh DEV7 run 2 executed on `983cad20404f` (clean tree, workers=3); artifacts committed (4 pairs, SCORE_TABLE, CALL_BUDGET v2) | `0a3194c6` | Art. LXI |
| Rebase conflict — r401 | Rebased-in r401 fixture states an explicit resuspension mechanism the hardened lexicon didn't cover. Art. VII: the CLAIM (fixture behavior) stands, the VERIFIER CLASS is corrected — `_PHYSICS_LEXEMES` += resuspension/erosion/wear/entrainment/abrasion (disclosed in code); bare-phrase kill unchanged; 21 gate tests stay green | `2df5a9df` | Art. VII |

## 3. Disclosed numbers (evidence sites in-repo)

**Call budget — target NOT met (disclosed).** The four COMPLETED fresh2
problems measure 31–40 LLM attempts each vs the 12-call target:
bench-p05 = 32, eval-new06 = 31, eval-new09 = 32, eval-new02 = 40
(`eval/score/CALL_BUDGET_FRESH2_983cad20404f.json`). The window's ATTACK
retry storm carries it: 15–18 distinct ATTACK attempts incl. 12–18
retries/fallbacks (ledger cross_check per problem). The three timed-out
problems (p02/p09/sofc) have no routing ledger → NOT_MEASURED totals,
never zeroed. `within_target: false` on all four measured — the
twelve-call target is NOT met on this run.

**Fresh2 speed — median target NOT met (disclosed).** 4/7 DONE,
p50 = 298.3 s, p95 = 300.0 s, max = 300.0 s, mean = 255.9 s, 3 timeouts
typed INCOMPLETE_INFRASTRUCTURE with stage_times preserved
(`eval/score/SCORE_TABLE.json` `speed` + `wall_time` at commit
`983cad20404f`). Owner budget is median ~120 s — not met this window.

**Judge-dependent measurement — NOT_MEASURED (not fabricated).** Judge
route probe in the 429 window: NO_ROUTE (xkiro probes failed at 20.3/20.4 s);
4 completed problems' judge attempts = JUDGE_TRANSPORT_FAILED (×4), 0 usable
pairs, `system_score = None`, `BLIND_PAIRWISE_WIN_RATE = NOT_MEASURED`.
No score exists for this run and none is reported.

**Two-turn records (unchanged, pre-existing).** dev-fu-001 TIMEOUT;
003/004/005 complete; 002/006 incomplete; all JUDGE_TRANSPORT_FAILED at
commit time → P0-14 (≥4/6 valid improvement) not measurable yet.

**Regression.** 194 tests green across every suite this round touched
(incl. the rebased-in r401/r5xx files), measured on this host at
`2df5a9df`. Two host-environmental reds disclosed:
- `tests/test_r491_key_wiring.py` / `test_r492_key_wiring_completion.py`
  need `sh` (key materialization) — red on this Windows host AND verified
  red at origin/main `b5ea85e9` in an isolated worktree: pre-existing
  no-vault/host environment class, not an R6 regression.
- `tests/test_gateway_pacing.py` (both tests) is node-bound: no node
  runtime on this host. The new concurrent test's pump logic was verified
  here by exact event simulation of the mjs state machine (3 slots @
  200 ms interval fire spaced ≈ interval, no overlapping starts); the
  node authority confirms in the sandbox.

## 4. What still needs a provider/capability window (no code outstanding)

1. **Judge calibration** (24/30 gate) — the 429 window blocks it.
2. **P0-10 speed repeats** — 1-worker × ≥3 and 3-worker × ≥3 as separate
   invocations (unique run roots automatic under P0-8; runbook blocks A/C).
   Fresh2 counts as 3-worker repeat 1.
3. **P0-14** — six-case two-turn loop, gate ≥4/6 valid improvement.
4. **P0-15** — one closed experiment loop, labelled synthetic.
5. **Fresh DEV7 rerun on the post-audit code** — quota permitting.
6. **Sealed holdout** `57be8218…b107` n=24 — remains gated on the auditor
   clearing items 1, 2, 6, with the pre-registered ≥50% wins+ties on
   ≥10-pairs gate. The holdout files have never been opened, run,
   inspected, or tuned by me; the harness reads them only via
   `--holdout <path>` when that gate is invoked.

Max-2-scored-runs limit: 0 scored runs consumed this round (no judge
scoring ran); both slots are open for the capability window.

## 5. Standing disclosures

- Circular seeded sweep RETIRED (Art. LXIV), not repaired: replaced by
  `scripts/r6_seeded_sweep.py` consuming OWNER-HELD
  `seeded_specimens_v1.json` (integrity prefix `c0aeb715`, fail-closed).
- Constitution v2.10.1 SHA `ac128b1c83ee01035deda2ba7592db77b84182ce`
  verified by the auditor; OCCT watertight disclosure (G1) stands —
  asserted at measured value, never recolored.
- LOG.md carries the post-audit round entry (≤10 lines/round discipline).
