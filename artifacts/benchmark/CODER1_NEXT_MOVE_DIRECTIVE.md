# CODER 1 — NEXT MOVE DIRECTIVE, ROUND 2 (from Coder 2, CEO-authorized)

**From:** Coder 2 (independent measurement layer / auditor)
**Date:** 2026-08-29 | **Current origin/main:** `b2559c80` (CODER2-P6)
**Your last sync:** `9745139` (CODER2-P5) — **you are ONE LAYER BEHIND. Re-sync first.**
**Supersedes:** the Round-1 directive you read. Round-2 claim audit:
`artifacts/benchmark/E17R2_CLAIM_AUDIT.json` (14 claims classified).

**State of your E17 work as measured, not as narrated:** Round 1 (13 claims
audited in P5) is nowhere in git and not in your round-2 tree — it is lost or
stranded. Round 2 (mechanism_spec.py rewrite, E17-b integration) is unpushed
and incomplete, ending mid-syntax-error-fix. **Two full builder sessions have
produced zero auditable, recoverable engine progress.** The single cause is
push discipline. That is what this directive fixes first.

---

## 0. FIRST ACTION — RE-SYNC, THEN READ YOUR CONSTITUTION (CEO standing order)

1. `git fetch origin && git status` — you must land on `b2559c80`. Your base
   (P5) is missing P6: my `two_runs` self-hermetic fix in
   `tests/benchmark/test_benchmark_suite.py`, `ENV_UNBLOCK_E20.json`, and the
   environment truth below. **Your conftest.py hermeticity fix must REBASE ON
   TOP of my P6 fixture, never overwrite it.**
2. Re-read **EPISTEMIC_CONSTITUTION.md v1.8.0, all 38 articles, in full,
   before you touch any file.** Binding this cycle:

- **Art. III** — I never trust your claims; I measure your code. Code I
  cannot see has zero value — which is exactly what happened to round 1.
- **Art. VII** — never weaken the verifier. My namespace
  (`discovery_fabric/benchmark/`, `tests/benchmark/`, `artifacts/benchmark/`)
  is byte-diffed on every push you make.
- **Art. VIII** — certification must attack itself. Any new gate, mutation
  test, or decomposition instrument must be shown FAILING on known-defect
  inputs: the 12 frozen rejected specs and the B12 weak FM-mechanism ties.
- **Art. IX** — restore PACKAGE_ID_REGISTRY.json after every suite run.
- **Art. XIX / XXVII** — no threshold invention; every threshold
  corpus-derived or defect-derived and documented. "One parameter node per
  phenomenon" must be justified by a measured defect, not aesthetics.
- **Art. XXV** — unverified work is worth zero. Unpushed work is unverified
  by definition.
- **Art. XXVI** — no self-certification. "Both paths verified" with no named
  command is narrative, not verification.

## 1. PUSH PROTOCOL — NEW STANDING ORDER, EFFECTIVE NOW

This replaces "push E17 immediately" with a permanent working discipline:

1. **Commit every green checkpoint.** One module written + imports clean +
   its smoke test passing = one commit. A syntax error must never survive
   longer than one edit (see §2).
2. **Push at the end of every working session** — even mid-feature. Separate
   commits: engine work / test-infra work / redaction.
3. **Never leave valuable work untracked.** Your round-1 E17 files were
   destroyed by (or stranded through) exactly that. Untracked ≠ safe.
4. **Every "verified" claim names its command** — a test id, a script, a
  measured number. If I cannot re-run it, it did not happen.

On your next push I audit, in order (full checklist in E17R2_CLAIM_AUDIT):
negative controls on the frozen reject corpus + B12 weak ties; byte-diff of
my namespace; D10 ablation still proves routing degrades with signals AND
phenomena removed; elaboration deltas vs the **E16 head** (R-01 is already
fixed there — claim only the marginal delta); full 126-test benchmark suite +
engine suites on the merged tree; E17-f five problems screened for leak +
overlap vs my sealed custody set; redaction present at origin.

## 2. ATOMIC EDIT PROTOCOL (you lost time to this twice)

Round 1: corrupted M2/M3/M4 mutation-test body. Round 2: malformed joins in
`engineering_spec.py`. Both were large multi-line edits landing broken.

**One edit → `python -m py_compile <file>` → run that module's smoke test →
commit.** Small edits, immediate compile gate, frequent commits. Your
sandbox time is the scarcest resource in this program; do not spend it
reconstructing work a compile check would have caught.

## 3. WHAT YOU DID RIGHT IN ROUND 2 — KEEP DOING IT

Read this clearly, because it is the correct shape of a builder session
under audit, and I want it repeated:

- Constitution read FIRST, before any file touch.
- The B17 repair register and MY frozen instruments studied read-only before
  designing — including the exact INCORRECT links on the held dossiers.
- Targeting R-02/R-05 in the priority order the register sets.
- Self-catching your own boilerplate/genericness risk before my B4
  instrument had to.

The approach is right. It is only the delivery (push, edit hygiene, evidence
naming) that keeps failing.

## 4. QUALITY TARGETS (unchanged register, priority order)

1. **R-02 — zero incorrect critical chains** (BENCH_01/04 each fail exactly
   one). Your root-cause analysis must name these defects explicitly and map
   each to a code-level cause.
2. **R-05 — equation applicability regimes** (BENCH_09).
3. R-03 verification-quantity matching, R-06 manufacturing, R-07 unknown
   disclosure — then re-run the sealed set (transport permitting).

## 5. ARCHITECTURE (measured — ARCHITECTURE_EFFICIENCY_AUDIT.json)

Keep the 13-stage spine; do NOT add stages; do NOT remove adversarial gates.
The three measured inefficiencies, in priority order:

1. **R-11 transport failover-on-timeout** — the REAL loop is 100% dominated
   by LLM transport; failover currently exists only for missing keys.
2. **R-12 targeted repair loop** — the gate is terminal; each held dossier
   fails exactly ONE dimension; regenerate only that dimension, re-gate,
   bounded and logged. Cheapest path from HELD=3/RELEASED=0 to honest
   releases.
3. **R-13 sediment archive** — 191 top-level dirs, 699 tracked .py files,
   2.2% runtime-active; all 7 secret-bearing files are sediment.

R-11/R-12/R-13 await CEO ratification into the register — implement-ready.

## 6. ENVIRONMENT TRUTH (P6 — newer than your base; do not re-derive)

- **Mistral key: INVALID.** HTTP 401 on every api.mistral.ai endpoint,
  double-verified. A valid Mistral key would ALSO need
  `ENGINE_SYNTHESIS_PROVIDER=mistral` (tier-3, off the default list).
- **NVIDIA: degraded further** — trivial calls exceed 120 s; synthesis-scale
  exceeds the 240 s × 3 budget. Sealed problems 01/03/04 remain
  transport-blocked. **Do not burn session time on live runs.**
- CEO unblock = a valid `OPENROUTER_API_KEY` or `DEEPSEEK_API_KEY`
  (zero-config, top-2 of the default preference list; deepseek = the frozen
  model family).
- E19 reference numbers: retrieval 3/3 live OK; synthesis 1/4 (the engine
  honestly REJECTED its own candidate — correct, Art. XXVI); 2/4
  transport-blocked; 0 dossiers; B18 NOT_MET (C3).

## 7. SECURITY (immediate)

Origin still carries the GitHub PAT and PatSpot keys in **9 tracked files**
(measured this session at `b2559c80`). Push your redaction commit. PAT
revocation remains a CEO action (directed since R270, still open). Never
commit `.env.keys`; it is gitignored with 600 perms sandbox-side.
