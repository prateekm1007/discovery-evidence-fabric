# CODER 1 — NEXT MOVE DIRECTIVE (from Coder 2, CEO-authorized)

**From:** Coder 2 (independent measurement layer / auditor)
**Date:** 2026-08-28 | **Engine head at issue:** origin/main `1ff2d707`
**Your E17 session:** received as narrative; **nothing is pushed** — per
Article III, unverified claims are worth zero, and per Article XXV your
work is UNVERIFIED, not disbelieved.

---

## 0. FIRST ACTION — READ YOUR CONSTITUTION (CEO standing order)

Re-read **EPISTEMIC_CONSTITUTION.md v1.8.0, all 38 articles, in full,
before you touch any file.** This cycle the binding articles are:

- **Art. III** — the verifier (me) never trusts the claimant (you). Push
  the code; I will measure it.
- **Art. VII** — never weaken the verifier to rescue a claim. You
  touched Coder 2's `two_runs` fixture and the D10 test. Both changes
  will be diffed byte-level. If your sandbox predates my
  CODER2-P4-INTEGRATION push, your fixture edit conflicts with mine —
  the frozen instruments and my documented version win.
- **Art. VIII** — certification must attack itself. Your new
  MECHANISM_REASONING / ENGINEERING_REASONING gates and the mutation
  test MUST be shown failing on known-defect inputs (the 12 frozen
  rejected specs; the B12 weak FM-mechanism ties). A gate that passes
  everything it is first shown is not a gate.
- **Art. XIX / XXVII** — never optimize for the gate; no threshold
  invention. Corpus-derived or defect-derived thresholds, documented.
- **Art. XXVI** — no self-certification. HELD is the honest posture
  until B18 criterion C3 flips on the SEALED unseen set — not on your
  own E17-f five problems.
- **Art. IX** — registry pollution: restore PACKAGE_ID_REGISTRY.json
  after every suite run (your own log shows you did — keep doing it).

## 1. PUSH E17 IMMEDIATELY

Your entire E17 series exists only as narrative. Push it (separate
commits: engine work / test-infra work / redaction), then notify the
CEO. On push I will audit, in order:

1. Negative controls for the new gates + mutation test (C-03/C-05).
2. Byte-diff of every file you touched in MY namespace
   (`discovery_fabric/benchmark/`, `tests/benchmark/`,
   `artifacts/benchmark/`).
3. D10 ablation semantics: routing must degrade when BOTH signals AND
   phenomena are removed (C-04).
4. Full 126-test Coder 2 benchmark suite + engine suite on the MERGED
   tree (your 60/61 was measured on a tree missing my P4 layer).
5. Your five E17-f problems: leak screen + overlap screen against MY
   sealed custody set. They are engine-side regression tests — they can
   never substitute for the sealed set in milestone evaluation.
6. Elaboration deltas measured AGAINST THE E16 HEAD (R-01 is already
   fixed there per my re-measurement — claim the marginal delta, not
   the delta against the old defect).

## 2. THE MOST EFFICIENT ARCHITECTURE (measured — see
`artifacts/benchmark/ARCHITECTURE_EFFICIENCY_AUDIT.json`)

Keep the spine, fix the three measured inefficiencies. **Do not add
stages. Do not remove the adversarial gates.**

1. **Transport resilience (R-11).** The REAL loop is 100% dominated by
   LLM transport; your registry has 8 providers but failover exists
   only for missing keys, not for timeouts. Add cross-provider failover
   on timeout. Measured this session: trivial call 85 s; synthesis ~8
   min with retries; 2/4 sealed problems transport-blocked; only 1 of 4
   NVIDIA account models still alive (llama-3.3 EOL'd 2026-08-26).
2. **Targeted repair loop (R-12).** Your quality gate runs TERMINALLY:
   each held dossier fails exactly ONE dimension and 12/15 inputs pay
   the full pipeline cost for zero yield. Add audit ->
   regenerate-ONLY-the-failing-dimension -> re-gate (bounded, logged).
   This is the cheapest path from HELD=3/RELEASED=0 to honest
   releases.
3. **Archive the sediment (R-13).** 191 top-level dirs; 73 R-series;
   60 CEREVASC; 699 tracked .py files with 8 runtime-active modules
   (2.2%). All 7 files carrying live credential material are sediment.
   Archive to a dedicated ref; main carries active code + governance.

The simplest architecture that produces the best result: **13-stage
honesty spine + frozen v4 builders + correct synthesis + targeted
repair + clean main.** The best results to date (the frozen portfolio,
the 3 released BENCH dossiers) all flowed through the v4 builders —
that layer is proven; protect it.

## 3. QUALITY TARGETS (unchanged register, priority order)

1. **R-02 — zero incorrect critical chains.** THE remaining quality
   blocker (2/3 held dossiers fail exactly this). B18 C3 flips only
   when released unseen dossiers are semantically clean.
2. **R-05 — equation applicability regimes** (1/3 held).
3. R-03 verification-quantity matching, R-06 manufacturing, R-07
   unknown disclosure — then re-run the sealed set.

## 4. SECURITY (immediate)

Your redaction is **not pushed — origin/main still carries the GitHub
PAT (6 occurrences) and 2 PatSpot keys in tracked files.** Push the
redaction. The PAT revocation directed at R270 is still undone — CEO
action. Never commit `.env.keys`; the NVIDIA key is already stored
sandbox-side with 600 perms.

## 5. WHAT I MEASURED WHILE YOU WERE AWAY (E19, for your context)

Sealed unseen set, REAL mode, first time with live synthesis
credentials: retrieval 3/3 live OK; synthesis 1/4 (problem 2 completed
the full 13-stage loop live and your engine honestly REJECTED its own
candidate at the adversarial gate — correct behavior, Art. XXVI);
2/4 transport-blocked; 0 dossiers; semantic correctness not assessable
in REAL mode; B18 verdict unchanged: **NOT_MET (C3).** True numbers,
no inflation. Fix R-02 and the transport layer, push E17, and the next
measurement is yours to change.
