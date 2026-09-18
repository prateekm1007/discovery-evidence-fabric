# TOSCANINI / DISCOVERY-EVIDENCE-FABRIC — MASTER HANDOFF TO NEXT CHAT (R510 era)

**Date of handoff:** 2026-09-18 (UTC)
**Author:** Super Z coder line (the R509-C2-ZLINE line), at main `3c17b602`
**Verified:** every sha, endpoint, and path in this document was re-verified from live bytes at handoff time (see §10 verification log)
**Precedent:** this file follows the `HANDOFF_TO_NEXT_CHAT_R419_MASTER.md` convention. The R419 handoff's mission and authority-order sections remain valid; its STATE sections are superseded by this document.

**Purpose:** give the next coder/auditor chat the complete operative state so the operator never has to repaste old files. Everything the new chat needs is either (a) in this file, or (b) in a file this file points to, with the exact autocommand to read/verify it.

**OPERATING MODE — AUTOCOMMANDS ONLY:** the operator (CEO) does not run manual steps. Every machine action in this document is a copy-paste-ready shell command for the new chat to execute itself. The operator's only acts are WORDS in chat (ratifications, rulings, verbatim acts) and SUPPLIES (keys, funding, registrations). If you (new chat) find a step that seems to need a human at a keyboard — it doesn't; either it is an autocommand here, or it is one of the operator's word-acts, or it is forbidden until an operator act lands.

---

## 0. FIRST INSTRUCTION — THE BOOTSTRAP RITUAL (run these before ANY other action)

Do not start by coding. Do not start by planning. Establish the live baseline first. Run this block verbatim:

```bash
# ---------- 0.1 locale (the R507 UTF-8 lesson; run in EVERY new shell) ----------
export LANG=C.UTF-8 LC_ALL=C.UTF-8

# ---------- 0.2 LXXIII vault consult order (Art. LXXIII / R509-C2 recovery precedent) ----------
# Order: (1) canonical path, (2) /tmp survivor copy, (3) rebuild canonical from survivor.
for p in /home/z/my-project/.secrets.env /tmp/my-project/.secrets.env; do
  [ -f "$p" ] && echo "VAULT FOUND: $p"
done
if [ ! -f /home/z/my-project/.secrets.env ] && [ -f /tmp/my-project/.secrets.env ]; then
  cp /tmp/my-project/.secrets.env /home/z/my-project/.secrets.env && chmod 600 /home/z/my-project/.secrets.env
  echo "canonical vault rebuilt from /tmp survivor"
fi
# Load into session env (values NEVER go into files, logs, or commits — BS-021):
set -a; . /home/z/my-project/.secrets.env; set +a
# Verify fingerprints (expected: GITHUB_TOKEN sha256[:16]=f1ebca5f9b622f3e len 40; HF_TOKEN sha256[:16]=33bc7af22c628bc1 len 37):
python3 - <<'PY'
import hashlib, os
for n in ("GITHUB_TOKEN", "HF_TOKEN"):
    v = os.environ.get(n, "")
    print(n, "fp:", hashlib.sha256(v.encode()).hexdigest()[:16], "len:", len(v))
PY
# Expected output:
# GITHUB_TOKEN fp: f1ebca5f9b622f3e len: 40
# HF_TOKEN fp: 33bc7af22c628bc1 len: 37
# If fingerprints DIFFER: STOP. Do not rotate (LXXVI: rotation is a CEO act).
# Register the delta, ask the operator, and treat all push/Space acts as blocked.

# ---------- 0.3 repo baseline (fresh container? clone; existing? verify) ----------
cd /home/z/my-project/hf_space 2>/dev/null || {
  git clone https://github.com/prateekm1007/discovery-evidence-fabric.git /home/z/my-project/hf_space
  cd /home/z/my-project/hf_space
}
# Authenticated fetch via the standing credential-helper injection
# (token via env, NEVER in a URL, NEVER on disk — the R503/R506 push pattern):
git -c credential.helper='!f() { echo username=x; echo password='"$GITHUB_TOKEN"'; }; f' fetch origin
echo "local HEAD : $(git rev-parse HEAD)"
echo "origin/main: $(git rev-parse origin/main)"
# These two MUST be equal. If not: realign (git status first; never destroy local records):
#   git status --short   # records-only work is additive; stash/rebuild cleanly if dirty

# ---------- 0.4 durable branch tip ----------
git -c credential.helper='!f() { echo username=x; echo password='"$GITHUB_TOKEN"'; }; f' \
  ls-remote origin refs/heads/runtime-state-hf refs/heads/main
# Expected at handoff time: main=3c17b602..., runtime-state-hf=215251c9...

# ---------- 0.5 frozen chain verify (the R506 battery freeze; Art. XXVII: these bytes are law) ----------
sha256sum R506/BATTERY_PROBLEMS.json scripts/r506_harvest_rules.py scripts/r506_discovery_yield.py
# Expected (first 8 hex):
#   e9c72c58  R506/BATTERY_PROBLEMS.json        (the six-problem manifest)
#   40d728f8  scripts/r506_harvest_rules.py     (the frozen rules script)
#   831f1a0e  scripts/r506_discovery_yield.py   (the frozen yield instrument)

# ---------- 0.6 live production identity (read-only public GET; no token needed) ----------
curl -sS -m 20 "https://prateekm1-toscanini-prod-validation.hf.space/api/version"
# Expected: {"engine_commit": "d7520b9bc5d7f26a2ab40b28367501e916634513", ...,
#            "constitution_version": "2.8.0"}
# If engine_commit != d7520b9b...: STOP AND RE-BASELINE (Art. XXVII discipline:
# never silently measure a different build than the frozen battery measured).

# ---------- 0.7 in-flight check (did the sibling line move while you read?) ----------
git log --oneline -8
```

If every step returned the expected values, your baseline is green and you may proceed to §1.

If the vault is missing entirely (fresh container, /tmp wiped): the recovery order is
(1) session env → (2) `/tmp/my-project/.secrets.env` → (3) `/home/z/my-project/.secrets.env` →
(4) the HF Space secrets surface (32 names; needs the HF token — chicken-and-egg, so only
usable if the HF token came from 1–3) → (5) the operator re-supplies in one chat message
(the R503 precedent; zero shame, it is a typed custody event, not a failure).

---

## 1. MUST-READ BEFORE CODING (the no-break list, in this order)

The system has been broken before by chats that skipped this list. The ritual is not
ceremonial — it is the audit loop protocol (`GOVERNANCE/AUDIT_LOOP_PROTOCOL_v1.md`) and
it is enforced by the governance files. Read in this order, fully, before any code,
plan, or verdict:

| # | File | Size | Why it must be read |
|---|------|------|---------------------|
| 1 | `EPISTEMIC_CONSTITUTION.md` | 2,399 lines (v2.9.0, sha `6aab103c`…, IN TREE — production still serves 2.8.0) | The supreme authority. Especially: Art. XXI.3 (absence ≠ absence), XXV (silence-is-not-death; never convert UNKNOWN into REJECTED), XXVII (no invented thresholds), XXVIII (no silent semantic promotion), XXXI (memory artifacts), XXXVII/XXXVIII (reality boundary), XXXIX (release chain), XLIII (blind problems), LXI (typed failures), LXXIII (vault), LXXIV (durable checkpoints / mid-flight rule), LXXVI (credential custody; rotation is a CEO act), LXXVII (discovery performance ≠ pipeline completion), LXXVIII (survivor four-gates incl. `blocking_count==0`), LXXIX (fresh-problem generalization), the Four Layers, and the WORLD_CLASS_DISCOVERY_GATE checklist |
| 2 | `GOVERNANCE/README.md` then the other four | short | How auditing itself is governed; the blindspot register is where BS-021 (owner keys never land in durable bytes) lives |
| 3 | `ACTIVE_PATH.md` | 1,305 lines | The single authority for what the production path IS; read through the R509 addenda at the end |
| 4 | `worklog.md` (repo root) | 2,167 lines — AT MINIMUM read every entry from `R506` to the end | The canonical, append-only work record; the last five entries (R506, R509 act-1, R509-C2, R509-C2-POST, R509-C2-ZLINE) are the live campaign |
| 5 | `R506/R506_ROUND_RECORD.json` | json | The battery: what the six problems are, how the freeze works, why the manifest was pushed before terminals existed |
| 6 | `R508/R508_ROUND_RECORD.json` + commit `ed296772` message (R508-C1) | json | The typed infrastructure failure (6× `INCOMPLETE_INFRASTRUCTURE_FAILURE`) and the verification intake |
| 7 | `R509/R509_ROUND_RECORD.json` | json | Act 1 PRESERVE: the discovery that the six capabilities are durable bytes; the tail that rewrote the mechanism (no deaths — the push path went silent) |
| 8 | `R509/R509_C2_ROUND_RECORD.json` + `R509/POST_RESTART_OBSERVATION.json` | json | The sibling line's execution: the 10-min engine_checkpoint cadence fact, the 48h dry-run, the 11:36:15Z Space restart |
| 9 | `R509/R509_C2_ROUND_RECORD_ZLINE.json` | json | THIS line's execution: the race reconciliation block (§ `race_reconciliation`) tells you exactly what both lines measured and where they differ by design |
| 10 | `R509/RESPAWN_DESIGN.md` + `R509/SUPPORT_TRACKS_DESIGN_NOTES.md` | md | The post-harvest engine fixes (M1–M4) and the parallel support tracks — design only, code forbidden until harvest |
| 11 | `scripts/r509_preflight_gate.py` (docstring), `scripts/r509_kill_switch.py`, `scripts/r509_battery_watchdog.py` + `_zline.py` | py | The armed phase-3 instrumentation you will inherit; read before running |
| 12 | `HANDOFF_TO_NEXT_CHAT_R419_MASTER.md` | 1,474 lines | Background: mission, authority order, history of failure classes. Its state sections are superseded by this file |
| 13 | `R509/KEY_BUDGET_LEDGER_ZLINE.json` + `R509/KEY_BUDGET_LEDGER.json` | json | The key-budget law: the shared PatentBear bucket, the five-rule protocol, why you must not spend |

Reading discipline that has worked: read with the question "what would I have to
NEVER do to avoid breaking this?" after each file. If you finish the list without
three new "never do" entries, you skimmed; go back.

---

## 2. AUTHORITY ORDER AND MISSION (unchanged from R419, restated because it never bends)

Authority order when artifacts conflict:
1. `EPISTEMIC_CONSTITUTION.md` (v2.9.0 in tree; production serves 2.8.0 — see the act-2 gate in §6)
2. `GOVERNANCE/AUDITOR_SELF_GOVERNANCE_v1.md`
3. `GOVERNANCE/AUDITOR_BLINDSPOT_REGISTER.md` (BS-021: owner keys never land in durable bytes)
4. `GOVERNANCE/AUDIT_LOOP_PROTOCOL_v1.md`
5. `ACTIVE_PATH.md`
6. Current repository / deployment state (verified, not assumed)
7. Current worklog / directives
8. Screenshots, reports, handoffs (INCLUDING THIS ONE — this file is a continuity aid, never authority)
9. Remembered conversational context

Mission (settled, do not re-litigate): a **world-class AI discovery and invention
machine** that turns difficult user problems into credible technology packages a real
company can evaluate, license, and build. The current cycle goal (CEO, R506): **stop
proving the machine works; start measuring whether it discovers.** One instrument, one
battery, one survivor. Success for the current campaign is, verbatim from the CEO
directive: *"not activity — it is six terminals, then one bottleneck named by
measurement."*

Who is who:
- **The operator / CEO** = the human user. Speaks in directives. Owns all keys.
  Ratifies constitution amendments. Rules on (a)-vs-(b) decisions. Never runs commands.
- **Coder lines** = AI sessions (you). Execute phases, produce records, push records.
  Two lines may run the SAME directive in parallel — the race protocol in §11.6 handles it.
- **The sibling line** = the other AI session that executed R509-C2 before this line;
  its records are canonical (`R509/` without suffix), this line's landed additively
  (`_ZLINE` suffixes). Both seals stand (R498 precedent).

---

## 3. THE IRON LAWS — violate any of these and you break the system

1. **Repetition-only seal.** No new problem text, no gate/threshold/prompt tuning, no
   engine change touches the scored set while a battery is in flight or frozen. Tuning
   voids the battery (draft Art. LXXIX).
2. **Every measurement is typed.** A number without a type, a provenance, and a byte
   citation is not a measurement. Absence of evidence is typed (e.g.
   `ABSENT_FROM_DURABLE_LEDGER`, `UNOBSERVABLE_*`, `REGISTERED_ABSENT_VALUE_NOT_HELD`),
   never silently treated as zero or as failure.
3. **Never research-type a live artifact.** Read-only paths for observers; the
   durable worktree is read-only; `sessions.json` on the durable branch carries
   `owner_key` values — load in memory only, never write them anywhere, BS-021
   fail-closed scan before ANY write/commit.
4. **Art. XXVII — invent no threshold.** The only derived bound ever authorized is
   82 min = 2 × p90 (p90=41, n=98, measured). Everything else cites its source bytes.
5. **Art. XXV — silence is not death.** UNKNOWN stays UNKNOWN with a typed reason
   until bytes resolve it. R508 held this line and was vindicated by the preserved tail.
6. **Art. XV — disclose immediately.** Every mistake, every environment rollback,
   every rejected push, every correction of a sibling's imprecision. Disclosure has
   never once been punished; concealment has.
7. **Scope law (the CEO campaign directive, binding):** until harvest, the tree accepts
   ONLY observer-side scripts + records. Zero engine delta in
   `discovery_fabric/`, `toscanini/`, `orchestrator/`, `TOSCANINI_UI/`. Zero deploy.
   Zero resubmission outside phase 3. Touching the six sessions' durable history is
   forbidden entirely.
8. **Stop-list (binding, from the same directive):** no attacker tuning, no new
   providers/sources/UI/pruning/package work, no physics changes, no deploy, no
   resubmission outside phase 3, no touching the six sessions' durable history.
9. **BS-021 + LXXIII + LXXVI (credentials):** owner key VALUES never land in durable
   bytes (no repo file, no commit, no record, no log, no download). The vault file
   (`/home/z/my-project/.secrets.env`, 0600) and the HF Space secrets surface (32
   names, the custody vault of record) are the only resting places. **Rotation is a
   CEO act — never machine-judged, never machine-executed.**
10. **Art. X — `MODULE_INVENTORY.json`** is regenerated only by its own authority
    script and must be `--check` GREEN whenever engine files changed (they shouldn't
    have, per the scope law).
11. **Measure-before-integration / LXXIV durable checkpoints:** execution states live
    on the durable branch (`runtime-state-hf`), not in chat memory. A missing manifest
    means MID_FLIGHT, never terminal.
12. **The funnel is the boss (phase 4 law):** the harvest rules + instrument decide
    the bottleneck; exactly ONE cliff-fix gets built per cycle; everything else on the
    wish-list waits.

---

## 4. CURRENT STATE — verified facts with bytes (the situation you inherit)

### 4.1 The one-paragraph state

The R506 discovery-yield battery (six blind NHTSA problems, frozen manifest
`e9c72c58`) was submitted 2026-09-18 00:03–00:04Z to production (`d7520b9b` / 2.8.0).
All six workers reached terminal COMPLETE on the live Space between 00:12:05Z and
00:45:07Z — **no deaths** — but the engine's durable push path went silently silent
after the last snapshot 00:09:15Z (`0da7fe50`), so the durable terminal authority has
0/6 terminals and the round typed 6× `INCOMPLETE_INFRASTRUCTURE_FAILURE` (LXI). The
ephemeral forensics tail + six live terminal session views were PRESERVED read-only at
08:35Z (durable commit `215251c9`), three hours before a Space restart (11:36:15Z)
that would have destroyed them — the preservation also proved the live session store
SURVIVED the restart (the store persists; only the run dirs' survival is unknown, and
only the owner can check). The durable push path is now measured RESTART-INSENSITIVE
silent (this boot pushed nothing vs 120 historical boot-reason rows). Scorecard:
138/25 = 5.52 → OVERALL 6/10, NO — eighth consecutive NO, frozen until terminals
exist on the durable authority. Phase 3 (resubmit or recover) and phase 4 (harvest)
are fully armed and gated on the operator's two word-acts.

### 4.2 The six sessions (the campaign's subject matter)

| # | session_id | durable last row | last snapshot | live terminal (preserved) | bridge | verdict (both lines) |
|---|-----------|------------------|---------------|---------------------------|--------|----------------------|
| P1 | `ts_dbdf24c91535` | HEARTBEAT @ 00:09:08.897Z | problem_understanding_merged @ 00:04:02Z | COMPLETE / INVENTION_REQUIRES_EXPERIMENT @ 00:12:04Z | NO_SURVIVOR | PUSH-FAILURE-suspect |
| P2 | `ts_ca977637f50b` | PHASE_STARTED @ 00:09:12.284Z | clarification_answered @ 00:08:45Z | COMPLETE / INVENTION_REQUIRES_EXPERIMENT @ 00:22:56Z | COMPLETED | PUSH-FAILURE-suspect |
| P3 | `ts_66e23c67b511` | PHASE_STARTED @ 00:09:10.080Z | problem_understanding_merged @ 00:08:58Z | COMPLETE / INVENTION_REQUIRES_EXPERIMENT @ 00:22:49Z | COMPLETED | PUSH-FAILURE-suspect |
| P4 | `ts_84a8807b12dc` | PHASE_STARTED @ 00:09:04.823Z | clarification_answered @ 00:08:58Z | COMPLETE / INVENTION_REQUIRES_EXPERIMENT @ 00:23:55Z | COMPLETED | PUSH-FAILURE-suspect |
| P5 | `ts_6da1b9339ce5` | PHASE_STARTED @ 00:09:10.840Z | clarification_answered @ 00:09:09Z | COMPLETE / INVENTION_REQUIRES_EXPERIMENT @ 00:45:07Z | COMPLETED | PUSH-FAILURE-suspect |
| P6 | `ts_d9b7d3463583` | CLARIFICATION_ANSWERED @ 00:09:15.107Z | clarification_answered @ 00:09:15Z | COMPLETE / INVENTION_REQUIRES_EXPERIMENT @ 00:40:37Z | COMPLETED | PUSH-FAILURE-suspect |

Preserved terminal facts (pipeline facts only — LXXVII-inadmissible as discovery
evidence): #1 INSUFFICIENT_ADJUDICATION / EVALUATION_FAILED / rank 0.15; #2 #3 #6
CONTESTED / adv PASS / rank 0.5069–0.5145; #4 #5 CONTESTED / adv KILLED / rank
0.2691; all six evidence_verified=true, prior_art UNRESOLVED_INSUFFICIENT_EVIDENCE.

### 4.3 The measured mechanism (both lines converged)

- The silent stage is the **durable push path**: last successful snapshot 00:09:15Z
  (`0da7fe50`), then ZERO snapshots despite six terminal FINAL_SNAPSHOT phases — with
  `last_write_error=null`, `forensics_degraded=false`, shrink_guard ok. **Silent
  custody loss.**
- The sibling's narrowing fact: `engine_checkpoint` is a measured **10.0-min periodic
  timer** (n=17 gaps / 6 sessions; R487: 11 checkpoints at 10.0–10.2-min spacing) —
  the six RUNNING battery sessions received **zero** ticks. The checkpoint/push
  subsystem below the health surface dropped both the periodic ticks AND the six
  terminal pushes. WHICH internal stage: still UNKNOWN (owner-side bytes needed).
- Shared-hang hypothesis: **NOT supported** (xkiro `RATE_LIMITED` = exactly ONE row at
  23:37:47Z followed by 16 ok-rows; terminal spread 33.0 min = independent
  completions; heartbeat 00:40:41Z mid-run).
- Push-path silence is **RESTART-INSENSITIVE**: the 11:36:15Z boot pushed nothing
  (vs 120 historical boot/after_restore rows) — the defect survived a full restart.
- The routing ledger carries **1,176** durable rows (the directive's "1,107" was not
  re-derived exactly by either line — disclosed, non-consequential).
- Owner-side forensics of the push-path internals remains THE typed root-cause path.

### 4.4 What is armed and waiting (phase 3 instrumentation, all observer-side)

| Instrument | Script | State | Autocommand |
|-----------|--------|-------|-------------|
| Pre-flight gate (fail-closed; 6 checks: freeze shas / live identity / durable / watchdog / act-2 verbatim / CEO ruling) | `scripts/r509_preflight_gate.py` | ARMED, never executed against live; GO only in offline rehearsal so far | `python3 scripts/r509_preflight_gate.py --skip-live --operator-act2-verbatim "2.9.0 stands" --ceo-execution-ruling resubmit` (rehearsal) |
| Kill-switch (per-session STALLED > 82 min → typed declare + PRESERVE via the read-only owner-key path; never touches workers) | `scripts/r509_kill_switch.py` | ARMED, self-test 3/3 | `python3 scripts/r509_kill_switch.py --self-test` then `--loop 10` when a run is live |
| Watchdog (canonical: STALLED_OVER_2X_P90 82min / DURABLE_TIP_STALE 30min=3× cadence / HEARTLESS_WORKERS; 2-poll hysteresis) | `scripts/r509_battery_watchdog.py` | ACCEPTED: 48h dry-run 577 polls, exactly 3 alerts (the R508 signature), zero false fires on R484/R487 | `python3 scripts/r509_battery_watchdog.py --self-test`; live: `--live` or cron `--once` |
| Watchdog ZLINE variant (DURABLE_TIP_STALE rides 2×p90 = the only authorized derived bound; 3/3 hysteresis) | `scripts/r509_battery_watchdog_zline.py` | ACCEPTED: replay PASS vs REAL R508 evidence bytes, zero false fires | `python3 scripts/r509_battery_watchdog_zline.py --self-test` |
| Battery driver (preflight / submit / poll / harvest modes) | `scripts/r506_battery_driver.py` | FROZEN-adjacent: this is the submission + harvest path | `python3 scripts/r506_battery_driver.py preflight` |
| Yield instrument | `scripts/r506_discovery_yield.py` (`831f1a0e`) | FROZEN — never edit; divergence = broken freeze | (called by the driver's harvest mode) |

One live watchdog tick was recorded 11:48:03Z (container-lifetime limited, disclosed).
The 48h accumulation runs via `--live` — start it if no process is running (§10.3).

### 4.5 The two watchdog variants are BOTH valid — an owner decision is queued

Canonical (sibling): `DURABLE_TIP_STALE` fires at 30 min = 3 × the measured 10-min
checkpoint cadence, 2-poll hysteresis. ZLINE (this line): `DURABLE_TIP_STALE` rides
82 min = 2 × p90 (the directive's only authorized derived bound), 3/3 hysteresis.
Both are recorded for the owner to pick or merge. Until the owner picks, run the
canonical one and leave the variant in the tree. Disclosed limitation (do NOT fix
unilaterally): a 293.1-min healthy progression gap exists 2026-09-13→14 (outside the
R484/R487 acceptance corpus) — the 82-min bound would have fired there; a
heartbeat-aware suppression variant is an owner decision, recorded not adopted.

---

## 5. WHAT IS DONE (the compressed ledger — read with `git log` beside you)

Every entry below is a pushed commit on `origin/main` unless stated otherwise.
The worklog entries in `worklog.md` carry the full detail; this table is the map.

| Commit | Round | What landed (records-only unless noted) |
|--------|-------|------------------------------------------|
| `2b42e8b4` → `9d126769` | R506 | The yield instrument built + frozen (`831f1a0e`); LXXVII/LXXVIII/LXXIX drafted (pending operator); the six-problem battery selected mechanically from NHTSA ODI narratives, disjointness fail-closed, manifest `e9c72c58` PUSHED BEFORE any terminal existed; all 6 submitted through the real user path; 5 clarified mechanically with each run's own verbatim text; redacted custody pushed to `runtime-state-hf` (`691d8d3d`) |
| (R506 → R508 span) | R507 | Constitution 2.8.0 → **2.9.0** ratified in tree (LXXVII/LXXVIII/LXXIX enacted; tree sha `6aab103c`); production still serves 2.8.0 — the verbatim act-2 gate exists because of this gap |
| `ed296772` | R508 + R508-C1 | The infra loss typed honestly: 6× `INCOMPLETE_INFRASTRUCTURE_FAILURE` (LXI); score 138/25 = 5.52 → OVERALL 6/10, **NO** (eighth consecutive); every checkable claim re-derived; forbidden-until-acts list (restart/rebuild/redeploy/resubmit) established |
| `759891bf` | R509 (act 1) | **PRESERVE EXECUTED** — the measured discovery that `durable.py::_collect_payload` pushes `sessions.json` (with owner_keys) WHOLESALE to the durable branch made act 1 executable read-only; 12/12 HTTP 200 GETs, same-boot verified both sides, 16 evidence files + six terminal views pushed as `battery/forensics_preservation_2026-09-18T083509Z/` → durable commit **`215251c9`** (parent `691d8d3d`); BS-021 scans clean; capabilities in-memory only |
| `666b8228` | R509-C2 (sibling line) | Phase 1 autopsy (`RESIDUE_AUTOPSY.json`: 6× PUSH-FAILURE-suspect, checkpoint-cadence fact); phase 2 watchdog (`r509_battery_watchdog.py` + 4 replay artifacts + 48h dry-run 577 polls); phase 3 ARMED (`r509_preflight_gate.py`, `r509_kill_switch.py`); tracks 10 (R370G door rehearsal DOOR_PROVEN, real_event_count=0), 11 (KEY_BUDGET_LEDGER), 12 (RESPAWN_DESIGN.md M1–M4); environment-rollback recovery disclosed |
| `1b23f584` | R509-C2-POST (sibling) | The 11:36:15Z Space restart measured: session store PERSISTED (owner-key GET `ts_ca977637f50b` → COMPLETE, envelope `50a912dc0775` byte-consistent); run dirs UNKNOWN from observer domain (owner-verifiable in one look); push path RESTART-INSENSITIVE silent; production tuple unchanged |
| `3c17b602` | R509-C2-ZLINE (this line) | The independent parallel execution landed additively: `RESIDUE_AUTOPSY_ZLINE.json` (per-session routing attribution typed; the 23:37:47Z row is EXACTLY ONE; 33.0-min spread kills shared-hang), `r509_battery_watchdog_zline.py` + replay acceptance PASS vs REAL R508 evidence bytes, `KEY_BUDGET_LEDGER_ZLINE.json` (5-rule protocol), `SUPPORT_TRACKS_DESIGN_NOTES.md`, the full race_reconciliation block; four pre-rebase local commits preserved in reflog, zero remote objects overwritten |

Support tracks (directive tracks 10–12, all isolated, none deployed):
- **Track 10 — R370G door rehearsal:** DOOR_PROVEN end-to-end on a labeled rehearsal
  fixture; real_event_count=0, counts_as_learning=false, nothing promotes,
  REAL_LOOP_VERIFIED stays 0.
- **Track 11 — key-budget coordination ledger:** committed; the shared PatentBear
  bucket 19/20 FROZEN below floor 2; the R498 two-line blind-consumption incident is
  the named lesson; five rules (reserve-before-spend / measure-meter-first /
  reconcile-after-spend / floor-is-law / reservations-expire).
- **Track 12 — respawn design (post-harvest only, no code yet):** M1 durable-push
  custody acknowledgment (the piece execution #1 actually exposed), M2 periodic
  terminal reconciliation (would have recovered all six), M3 idempotent resume =
  push-not-rerun, M4 reaping last; regression gate = the R509 signature + closure
  no-ops.

---

## 6. WHAT IS LEFT — the gate tree (who owns each gate, in order)

```
GATE A (operator, WORD-ACT):   act 2 verbatim — the operator types exactly
                               "2.9.0 stands" (opens phase 3) or "revert"
                               (constitution adjudication first, phase 3 stays shut).
GATE B (operator, RULING):     (a) recover-first — owner recovers the ephemeral run
                               dirs into the durable branch (the ONE open input: do
                               the run dirs still exist owner-side? owner-verifiable
                               in one look; the session store survived the restart, so
                               (a) is NOT dead) → the frozen instrument then measures
                               execution #1 on its own input contract;
                            or (b) resubmit — execution #2, identical six problems,
                               same bytes/prefixes, R508 as attempt genealogy.
GATE C (autocommand):          pre-flight gate GO (fail-closed; it refuses by design
                               until A+B land) + kill-switch armed in parallel.
GATE D (autocommand):          the run itself — six terminals, or six typed failures
                               WITH death evidence (watchdog durable tail + alert log).
                               Only terminals enter the funnel.
GATE E (autocommand):          phase 4 harvest under the frozen rules → YIELD_MEASUREMENT
                               + funnel + bottleneck rank published.
GATE F (build, ONE only):      the single cliff-fix the funnel names:
                               diversity adapter (candidates starve) /
                               collision scale-out (mandatory_complete=false dominates) /
                               attacker v4.3 (over/under-kill dominates) /
                               ring-failover routing (substitution dominates).
                               Everything else on the wish-list is FORBIDDEN this cycle.
GATE G (post-harvest):         engine-side respawn design (M1–M4) lands as its own
                               measured change with regression proof (test cases = the
                               R508/R509 deaths + closure no-ops). Until then: forbidden.
PARALLEL (operator supplies):  fund-or-assign the strong ring (HF router);
                               fresh PatentBear key (bucket 19/20 FROZEN below floor 2);
                               Tier-1 registrations (EPO OPS / PatentsView).
```

Notes on the gates:
- **Do not execute GATE C/D until both word-acts (A + B) are in the chat transcript.**
  The pre-flight gate script encodes both and refuses otherwise — trust it, but also
  honor it even if you could bypass it.
- If the operator answers "2.9.0 stands" + "resubmit": the exact execution order is
  §10.4. If "recover-first": the owner pushes the run dirs; you then run the harvest
  path on execution #1's own input contract — read `R509/R509_ROUND_RECORD.json`
  "Owner decision now framed" again before acting.
- The kill-switch runs DURING any live execution (GATE D), not instead of it. It is
  observe-and-type only. If it fires `STALLED` per-session: preserve + root-cause from
  the NEW evidence; that is the pre-registered response, not a judgment call.
- **The operator's word-acts are the only manual things in this system, and they are
  words, not commands.** Everything under GATES C–G is autocommands in §10.

---

## 7. CREDENTIALS, VAULT, AND KEY BUDGET (read twice before touching any API)

### 7.1 The vault (Art. LXXIII + LXXVI)

- Canonical local vault: `/home/z/my-project/.secrets.env` (mode 0600).
  Current living copy: `/tmp/my-project/.secrets.env` (survivor of the last container
  recycle; 287 bytes; `GITHUB_TOKEN` + `HF_TOKEN`; fingerprints match the registered
  records — NOTHING rotated).
- The HF Space secrets surface is the **custody vault of record** (Art. LXXVI):
  32 names measured live at R503 (incl. `HF_TOKEN`, `GITHUB_TOKEN`, NVIDIA_API_KEY,
  OPENROUTER_API_KEY, ENGINE_OPERATOR_KEY; PATENTBEAR_API_KEY status = custody gap,
  value not held — §7.3).
- **Values live in exactly two places**: the local vault file and the HF secrets
  surface. Never in a repo file, a commit, a record JSON, a log, a chat paste-back,
  or `/home/z/my-project/download/`. Every emitted byte with potential key material
  gets the BS-021 fail-closed scan (grep the emitted files for value substrings
  BEFORE commit — see `scripts/r509_push_preservation.py` for the pattern).
- **Rotation is a CEO act.** If a key fails (401/403), you type the failure, register
  the fingerprint delta, and ask. You never rotate, never regenerate, never "helpfully"
  update a standing secret (the R503 disclosed incident is the cautionary tale — the
  write happened to be byte-identical, which is the ONLY reason it was survivable).

### 7.2 Registered fingerprints (verify, never assume)

| Credential | Fingerprint (sha256[:16]) | len | Registered at | Status at handoff |
|-----------|---------------------------|-----|---------------|-------------------|
| `GITHUB_TOKEN` (PAT, push/fetch) | `f1ebca5f9b622f3e` | 40 | R497 lift-in / R503 vault audit / R509-C2 recovery | HELD in vault; push intact |
| `HF_TOKEN` (HF API, prateekm1, fine-grained) | `33bc7af22c628bc1` | 37 | R463 probe / R468 set event / R503 whoami verify | HELD in vault; Space secrets surface readable with it |
| PATENTBEAR active key | `50fe7b3d569bb1fa` (prior `561b6e70f5b5ea7f`) | — | R505 / R509 ZLINE ledger | **VALUE NOT HELD anywhere machine-readable** (R504 custody gap); bucket 19/20 → spend FROZEN |

HF token autocommands (after §0.2 vault load):
```bash
# whoami verify (expect: name prateekm1, type fine-grained):
curl -sS -m 20 -H "Authorization: Bearer $HF_TOKEN" https://huggingface.co/api/whoami-v2 | head -c 300
# Space secrets surface LIST (names only in logs — never echo values):
curl -sS -m 30 -H "Authorization: Bearer $HF_TOKEN" \
  "https://huggingface.co/api/spaces/prateekm1/toscanini-prod-validation/secrets" \
  | head -c 2000   # endpoint shape may have changed — if so, read scripts/r503_vault_custody.py first
```
If you must fetch a VALUE from the secrets surface (LXXVI Section 3 allows
measure-before-write custody work): do it in-process (`python3` + requests, value
straight into the vault file write), never echo it, never put it in a command line,
never in a tool result you paste anywhere.

### 7.3 The key budget is LAW (track 11)

- The shared PatentBear bucket is **19/20 used, remaining 1, below the stewardship
  reserve floor of 2 → `POOL_EXHAUSTED_MEASURED`; spend_allowed=false. FROZEN.**
- Measured costs: probe=1 debit, seal-scale spend=6, full battery rerun=8. Nothing
  seal-scale is possible until the operator supplies a fresh rotated key.
- Before ANY metered spend: append a RESERVATION row to
  `R509/KEY_BUDGET_LEDGER_ZLINE.json` (append-only), re-measure the provider meter
  FIRST, and append the OUTCOME row after. Unexplained deltas type
  `CROSS_LINE_UNEXPECTED_DEBIT` and freeze the bucket.
- The R498 lesson (twice-recorded): two coder lines sharing one key pool consume each
  other's headroom blind unless the ledger is checked first. CHECK THE LEDGER FIRST.

### 7.4 The push pattern (autocommand; token never in URL or on disk)

```bash
git -c credential.helper='!f() { echo username=x; echo password='"$GITHUB_TOKEN"'; }; f' push origin main
# durable branch (records custody) — same pattern:
git -c credential.helper='!f() { echo username=x; echo password='"$GITHUB_TOKEN"'; }; f' push origin runtime-state-hf
# verify after every push:
git -c credential.helper='!f() { echo username=x; echo password='"$GITHUB_TOKEN"'; }; f' ls-remote origin refs/heads/main refs/heads/runtime-state-hf
```
Scripted equivalent: `scripts/r509_push_preservation.py::cred_env()` (the standing
R503/R506/R509 pattern — GIT_CONFIG_COUNT injection, GIT_ASKPASS=/bin/true). Copy that
function; do not invent a new mechanism.


## 8. FILE STRUCTURE MAP (anti-entropy — where things live, where new things go)

### 8.1 The workspace root (`/home/z/my-project/`)

```
/home/z/my-project/
├── .env                       # container tooling (DATABASE_URL) — NOT the vault, ignore
├── .secrets.env               # THE LXXIII VAULT (canonical, 0600) — rebuild from /tmp
│                              #   copy per §0.2; values never leave it
├── hf_space/                  # ★ THE CANONICAL REPO (main branch) — everything happens here
├── r509_durable/              # detached worktree of origin/runtime-state-hf @ 215251c9
│                              #   (runs/, sessions.json ← owner_keys INSIDE, BS-021,
│                              #   snapshot_log.jsonl, battery/, evidence/, model_routing/)
│                              #   READ-ONLY for observers. Never commit here directly.
├── hf_space.stale_09b44c5/    # stale R451-era checkout — quarantine reference ONLY.
│                              #   Named "stale" on purpose. Never work in it, never delete
│                              #   it mid-round (it is disclosed custody of the stale era).
├── r445_work/, r446_work/     # historical round work dirs (frozen, with node_modules gaps)
├── r446hf_negtest_409.json    # R446 negative-test artifact (frozen)
├── download/                  # user-facing deliverables only — NEVER put keys/records here
├── upload/, skills/, scripts/, tool-results/   # container scaffolding, not project state
└── worklog.md                 # STALE container-local legacy worklog (R441-era). The
                               #   canonical worklog is hf_space/worklog.md. Do not confuse them.
```

### 8.2 Inside the canonical repo (`/home/z/my-project/hf_space/`)

```
hf_space/
├── EPISTEMIC_CONSTITUTION.md      # v2.9.0 IN TREE (2,399 lines) — production serves 2.8.0
├── GOVERNANCE/                    # 5 auditor files (README, SELF_GOVERNANCE, BLINDSPOT_REGISTER,
│                                  #   REMEMBERED_STATE, LOOP_PROTOCOL) — read 5, live by them
├── ACTIVE_PATH.md                 # the single authority for the production path + addenda
├── worklog.md                     # ★ CANONICAL append-only worklog (2,167 lines; R441→R509-C2-ZLINE)
├── HANDOFF_TO_NEXT_CHAT_R419_MASTER.md   # prior handoff (background valid, state superseded)
├── HANDOFF_NEXT_CHAT_R510_MASTER.md      # THIS file
├── MODULE_INVENTORY.json          # Art. X authority — regen ONLY by its script, keep --check GREEN
├── CANONICAL_MODEL_FLOW.md, ENGINE_BLUEPRINT.md, PRODUCTION_ADVERSARIAL_CALL_GRAPH.md
├── R309/ … R509/                  # round records: ONE directory per round, records-only.
│   │                              #   Next round = R510/ (never reuse, never rename another
│   │                              #   line's files — race protocol §9.6)
│   ├── R506/                      # BATTERY_PROBLEMS.json (manifest, e9c72c58) ·
│   │                              #   HARVEST_RULES.json (bytes 8cec1cd3 / attest 70a83fe1) ·
│   │                              #   YIELD_INSTRUMENT.json (831f1a0e pre-registration) ·
│   │                              #   DURABLE_POPULATION_BASELINE.json (97-run pre-battery) ·
│   │                              #   BATTERY_RAW/ (verbatim NHTSA fetches) ·
│   │                              #   BATTERY_SESSIONS_REDACTED.json · 3 hermetic case files
│   └── R509/                      # THE LIVE CAMPAIGN EVIDENCE:
│       ├── RESIDUE_AUTOPSY.json / RESIDUE_AUTOPSY_ZLINE.json
│       ├── R509_ROUND_RECORD.json / R509_C2_ROUND_RECORD.json / R509_C2_ROUND_RECORD_ZLINE.json
│       ├── POST_RESTART_OBSERVATION.json
│       ├── PRESERVATION_2026-09-18T083509/   (the 08:35Z capture, byte shas)
│       ├── WATCHDOG_REPLAY_ACCEPTANCE.json / REPLAY_48H_DRYRUN.json /
│       │   REPLAY_R484_CONTROL.json / REPLAY_R487_CONTROL.json / REPLAY_R509_SIGNATURE.json
│       ├── WATCHDOG_LIVE_LOG.jsonl
│       ├── KEY_BUDGET_LEDGER.json / KEY_BUDGET_LEDGER_ZLINE.json
│       ├── R370G_REHEARSAL.json / r370g_rehearsal_ledger.json
│       ├── RESPAWN_DESIGN.md / SUPPORT_TRACKS_DESIGN_NOTES.md
│       └── (new alerts/watches append here: WATCHDOG_ALERTS.jsonl, KILL_SWITCH_*.jsonl)
├── scripts/                       # 478 round scripts, naming law: scripts/rNNN_<purpose>.py
│   │                              #   r506_* battery/instrument (FROZEN ones marked in §4.4)
│   │                              #   r507_* ratification/pins · r509_* campaign instruments
│   │                              #   Your new scripts: scripts/r510_*
├── discovery_fabric/              # ★ ENGINE — FROZEN under the scope law (zero delta until
├── toscanini/                     # ★ ENGINE (server.py = the job API) — same freeze
├── orchestrator/                  # ★ ENGINE — same freeze
├── TOSCANINI_UI/webapp/           # ★ frontend — same freeze
├── archive/, MECHANISM_CEMETERY/  # retired code — never delete, never import, never "clean up"
├── tests/                         # pin suites (R506 17+1s, R507+R505 22 passed) — run, don't touch
└── Dockerfile, requirements.txt   # deploy surfaces — deploy is forbidden outside its phase
```

### 8.3 Naming and placement law (this is how entropy was kept out for 200 rounds)

1. **One round = one directory**: new records go to `R510/` (then R511, …). Never write
   into another round's directory except APPEND-ONLY ledgers that declare it
   (KEY_BUDGET ledger rows, WATCHDOG alert logs).
2. **One script per instrument, name = round + purpose**: `scripts/r510_<thing>.py`.
   Frozen instruments (`831f1a0e` etc.) are never edited — a divergence is a broken
   freeze, the loudest possible failure, by design.
3. **Race protocol**: if two lines run the same directive, the second pusher lands
   ADDITIVELY with a suffix (`_ZLINE`, `_C1`, `_C2`) and a race_reconciliation block in
   its round record. Push rejections (non-fast-forward) are handled by fetch + realign +
   rename — NEVER force-push, NEVER overwrite remote objects (the R498/R509 precedents).
4. **The durable branch** (`runtime-state-hf`) is engine state + custody evidence. Its
   worktree is read-only for observers; writes happen through dedicated scripts that
   assert the tip before committing (see `r509_push_preservation.py`).
5. **`worklog.md` is append-only** — new entries at the end, format: `--- Task ID: …`,
   `Agent: …`, `Task: …`, `Work Log: …`, `Stage Summary: …`, `reviewer_provenance=AI_REVIEW`.
6. **Every round record JSON** carries: artifact_type, round, directive anchor,
   reviewer_provenance=AI_REVIEW, a `what_is_NOT_claimed` list, and byte citations for
   every claim. Copy the shape from `R509/R509_C2_ROUND_RECORD_ZLINE.json`.
7. **Active path changes** = an ACTIVE_PATH.md addendum at the end + worklog entry, never
   a rewrite of earlier sections.
8. Nothing project-related ever goes to `/home/z/my-project/download/` (that is for
   user deliverables) — records live in the repo and get PUSHED (durable beats local;
   the container has recycled twice and origin is what survived).

---

## 9. KNOWN TRAPS (each one already cost a round once — do not pay again)

1. **Container recycle / rollback** (happened ~Sep-11/16 and again before 11:01Z today):
   local worktrees, vaults, and worklogs vanish. Only origin survives. Therefore:
   commit + push records IMMEDIATELY when a gate closes; never leave the only copy of
   evidence local overnight; the vault consult order (§0.2) is the recovery path.
2. **Stale checkout**: the R451-era incident (`hf_space.stale_09b44c5`). Always
   `ls-remote` + compare HEAD == origin/main before acting (§0.3–0.4). Never assume a
   clone is fresh because it exists.
3. **Locale**: the sole Windows cp1252 failure class became a UTF-8 requirement
   (Correction 1, R507 era). `export LANG=C.UTF-8 LC_ALL=C.UTF-8` in every shell (§0.1).
4. **Unicode line-separator fragmentation** when reading JSONL ledgers (measured in the
   ZLINE autopsy): use the read discipline in `scripts/r509_residue_autopsy_zline.py`
   (b-`\n`-split, sha-pinned, fail-closed) instead of naive line iteration.
5. **Push command composition**: one mistaken `git push origin HEAD:runtime-state-hf`
   from the main worktree was rejected non-fast-forward (zero remote effect) and had to
   be disclosed (Art. XV). Compose push refspecs deliberately; verify with ls-remote.
6. **The race pattern**: R506/R507 and R509-C2 both had two lines converge on one
   directive. Expect it; land additively; reconcile in your round record (§8.3.3).
7. **Absence is not absence** (Art. XXI.3): `session_id=null` rows typed
   `ABSENT_FROM_DURABLE_LEDGER`, empty surfaces typed `REGISTERED_ABSENT_…`,
   unobservable inputs typed `UNOBSERVABLE_*`. A zero you did not measure is a lie.
8. **Secrets hygiene incidents** are one keystroke away: the R503 mis-parse rewrote a
   standing secret (survived only because byte-identical). Measure-before-write,
   fail-closed, values in two places only (§7.1).
9. **The 1,107-vs-1,176 class of imprecision**: when a directive states a figure, you
   still measure it from bytes and disclose the delta. Directives are orders, not
   measurements.
10. **The restart hazard**: a Space restart destroys ephemeral run dirs (the R508
    warning, vindicated by 3 hours on 2026-09-18). If a run is live and evidence is
    ephemeral-only, PRESERVE FIRST — preservation always outranks analysis.


## 10. AUTOCOMMAND PLAYBOOKS (every machine action you will need)

### 10.1 Baseline re-verify (run at session start, and any time you feel unsure)
= §0 verbatim. Fast form when the vault is already loaded:
```bash
export LANG=C.UTF-8 LC_ALL=C.UTF-8; cd /home/z/my-project/hf_space
set -a; . /home/z/my-project/.secrets.env; set +a
git -c credential.helper='!f() { echo username=x; echo password='"$GITHUB_TOKEN"'; }; f' fetch origin
git rev-parse HEAD origin/main
curl -sS -m 20 https://prateekm1-toscanini-prod-validation.hf.space/api/version
sha256sum R506/BATTERY_PROBLEMS.json scripts/r506_harvest_rules.py scripts/r506_discovery_yield.py
```

### 10.2 Watchdog operations (observer-only, always legal)
```bash
cd /home/z/my-project/hf_space
python3 scripts/r509_battery_watchdog.py --self-test          # canonical variant
python3 scripts/r509_battery_watchdog_zline.py --self-test    # ZLINE variant
# single poll right now (cron-friendly):
python3 scripts/r509_battery_watchdog.py --once --alert-log R509/WATCHDOG_ALERTS.jsonl
# continuous live leg (48h accumulation; run under nohup so the container survives you):
nohup python3 scripts/r509_battery_watchdog.py --live \
      --alert-log R509/WATCHDOG_ALERTS.jsonl >> R509/WATCHDOG_LIVE_LOG.jsonl 2>&1 &
# replay a historical window (acceptance re-run):
python3 scripts/r509_battery_watchdog.py --replay "2026-09-18T00:00Z" "2026-09-18T02:00Z" \
      --out R509/REPLAY_R509_SIGNATURE.json
```
Check if a watchdog is already running before starting another:
`ps aux | grep -E "r509_(battery_watchdog|kill_switch)" | grep -v grep`

### 10.3 Kill-switch (armed; runs only while a battery is live)
```bash
python3 scripts/r509_kill_switch.py --self-test                # 3/3 expected
# during GATE D only:
nohup python3 scripts/r509_kill_switch.py --loop 10 \
      --alert-log R509/KILL_SWITCH_ALERTS.jsonl >> R509/KILL_SWITCH_LIVE.log 2>&1 &
```
It declares per-session STALLED at >82 min without durable progression, PRESERVEs the
session tail via the read-only owner-key path, and never touches workers. Its firing
is the pre-registered response, not a decision point.

### 10.4 GATES C+D — pre-flight then execution #2 (ONLY after operator act 2 + ruling)
```bash
cd /home/z/my-project/hf_space
# (1) offline rehearsal of the gate (always safe, does not touch the Space):
python3 scripts/r509_preflight_gate.py --skip-live \
  --operator-act2-verbatim "2.9.0 stands" --ceo-execution-ruling resubmit
# (2) the real gate (live identity check against the Space):
python3 scripts/r509_preflight_gate.py \
  --operator-act2-verbatim "2.9.0 stands" --ceo-execution-ruling resubmit
# Exit codes: 0 GO | 3 IDENTITY_MOVED_REBASELINE | 4 GATE_REFUSED | 5 FREEZE_BROKEN | 6 WATCHDOG_UNARMED
# (3) ON GO: start the observers, then submit:
python3 scripts/r506_battery_driver.py preflight
python3 scripts/r506_battery_driver.py submit        # identical six problems, same bytes/prefixes
# (4) then §10.2 live watchdog + §10.3 kill-switch, and poll:
python3 scripts/r506_battery_driver.py poll
```
Read `scripts/r506_battery_driver.py` docstring + `r509_preflight_gate.py` docstring
BEFORE the first real invocation. If the gate exits 3 (identity moved): STOP and
re-baseline — never silently measure a new build; that refusal is the system working.

### 10.5 GATE E — harvest (only after terminals exist on the durable authority)
```bash
python3 scripts/r506_harvest_rules_validation.py     # frozen rules self-check
python3 scripts/r506_harvest_rules_rehearsal.py      # hermetic rehearsal first — always
python3 scripts/r506_battery_driver.py harvest       # → R506/YIELD_MEASUREMENT.json + funnel
```
Then publish the funnel + bottleneck rank in the round record. Build exactly ONE
cliff-fix (GATE F) — the funnel names it, not you.

### 10.6 Records commit + push (the routine every round ends with)
```bash
cd /home/z/my-project/hf_space
export LANG=C.UTF-8 LC_ALL=C.UTF-8
set -a; . /home/z/my-project/.secrets.env; set +a
# (a) BS-021 leak scan on EVERY file you are about to commit:
for f in $(git status --short | awk '{print $2}'); do
  python3 - "$f" <<'PY'
import sys, re
p = sys.argv[1]
b = open(p, 'rb').read()
import os
toks = []
vault = '/home/z/my-project/.secrets.env'
if os.path.exists(vault):
    for line in open(vault):
        if '=' in line and not line.strip().startswith('#'):
            v = line.split('=',1)[1].strip()
            if len(v) >= 12: toks.append(v)
hit = [t[:6] for t in toks if t.encode() in b]
print(p, 'LEAK' if hit else 'clean', hit or '')
PY
done
# If ANY file prints LEAK: do not commit; fix the file, not the scan.
# (b) commit records only (scope law) and push:
git add R510/ scripts/r510_*.py worklog.md ACTIVE_PATH.md HANDOFF_NEXT_CHAT_R510_MASTER.md 2>/dev/null || true
git commit -m "R510 — <one honest sentence>. Records-only; zero engine delta; no deploy. reviewer_provenance=AI_REVIEW"
git -c credential.helper='!f() { echo username=x; echo password='"$GITHUB_TOKEN"'; }; f' push origin main
git -c credential.helper='!f() { echo username=x; echo password='"$GITHUB_TOKEN"'; }; f' ls-remote origin refs/heads/main
# (c) append the worklog entry (append-only) and push again if the entry came after the commit.
```

### 10.7 Tests you must be able to pass at any moment
```bash
python3 -m pytest tests/ -k "r506 or r507 or r505" -q    # the pin suites: 39 passed + 1 skipped expected
python3 scripts/module_inventory.py --check 2>/dev/null || python3 - <<'PY'
# Art. X inventory check — locate the authority script first if this fails:
import subprocess; print(subprocess.run(['grep','-rl','MODULE_INVENTORY','scripts/'],capture_output=True,text=True).stdout)
PY
```
(The inventory regen authority is the Art. X script — find it via the grep if the
name differs at your tip; never hand-edit MODULE_INVENTORY.json.)

### 10.8 Vault rebuild after a container recycle
```bash
for p in /tmp/my-project/.secrets.env /home/z/my-project/.secrets.env; do [ -f "$p" ] && echo "survivor: $p"; done
cp /tmp/my-project/.secrets.env /home/z/my-project/.secrets.env 2>/dev/null && chmod 600 /home/z/my-project/.secrets.env
# verify fingerprints against §7.2 — if they differ: STOP, register the delta, ask the operator.
# If BOTH are gone: the HF token must be re-supplied by the operator in one chat message
# (the R503 precedent) — typed CUSTODY_GAP_VALUE_NOT_HELD, then rebuilt 0600, never rotated.
```

### 10.9 Rebuild everything on a brand-new container (the full cold start)
```bash
export LANG=C.UTF-8 LC_ALL=C.UTF-8
# vault (§10.8) → clone → baseline (§0.3–0.6) → read §1 list → worklog tail → git log -8
# durable worktree rebuild (read-only):
cd /home/z/my-project/hf_space
git -c credential.helper='!f() { echo username=x; echo password='"$GITHUB_TOKEN"'; }; f' fetch origin
git worktree add --detach /home/z/my-project/r509_durable 215251c9 || \
git -C /home/z/my-project/r509_durable checkout --detach 215251c9
```
Everything else (r445_work, stale checkout) is history — ignore it.

---

## 11. SCORECARD AND TRUE NUMBER (so you do not have to re-derive the standing verdict)

- **Standing score: 138/25 = 5.52 → OVERALL 6/10, NO — the eighth consecutive NO.**
  Frozen until terminals exist on the durable authority (recovery or execution #2).
  The infra loss measures nothing about capability (LXI + the LXXVII symmetry).
- Pre-battery durable baseline (97 runs): buyer_ready 0/86; experimentally_
  discriminated 0/86; mutated_survivors 2/86; drops 43× EVIDENCE_UNVERIFIED,
  27× NO_CANDIDATES, 11× ATTACK_KILLED. This is what "the machine does not yet
  discover" looks like in bytes.
- Decisive verifications still owed (the re-audit union): the R500 pure seal re-run
  (needs 6+ quiet debits — key-blocked); v4.2 attacker-computes deployed measurement
  (rides next deploy — deploy-gated); the funded strong ring (owner-gated); one REAL
  instrument packet → REAL_LOOP_VERIFIED; a fresh-problem survivor reaching a buyer
  ZIP; the Tier-1 registrations.
- What would move the number: terminals → harvest → a funnel with a named bottleneck
  → the ONE cliff-fix → a survivor through the four LXXVIII gates
  (`blocking_count==0` included). Nothing else moves it.

---

## 12. VERIFICATION LOG (what this handoff itself verified, at handoff time)

Run at 2026-09-18 by the outgoing line, all GREEN:
- local HEAD == origin/main == `3c17b602` (R509-C2-ZLINE); worktree clean.
- Vault present at `/tmp/my-project/.secrets.env`; GH fp `f1ebca5f9b622f3e` (len 40),
  HF fp `33bc7af22c628bc1` (len 37) — match registered records.
- Space live: `GET /api/version` → `d7520b9bc5d7f26a2ab40b28367501e916634513` / 2.8.0,
  web_build c0c934b4…, 102 files; space page HTTP 200.
- Frozen chain byte-verified: `R506/BATTERY_PROBLEMS.json` → `e9c72c58`;
  `scripts/r506_harvest_rules.py` → `40d728f8`; `scripts/r506_discovery_yield.py` →
  `831f1a0e`; rules internal sha `70a83fe1` embedded in the preflight gate;
  manifest/rules/instrument/production identities all as §4 states.
- Durable tip: `origin/runtime-state-hf` = `215251c9` (remote-tracking ref, pushed);
  durable worktree at `/home/z/my-project/r509_durable` detached at `215251c9`.
- Watchdog/kill-switch `--help` interfaces verified; one live watchdog tick on record
  (11:48:03Z); no watchdog process running at handoff (start one per §10.2 if you
  want the 48h leg accumulating).

If your re-run of §0 diverges from any expected value above, the divergence is the
news — measure it, type it, disclose it. This handoff is then stale and the bytes win.

---

## 13. YOUR FIRST TEN ACTIONS (the new chat, in order)

1. Run §0 (the bootstrap ritual) — every step, no skipping.
2. Read §1 files 1–5 (constitution in full, governance, ACTIVE_PATH, worklog R506→end).
3. Read §1 files 6–13 (the campaign records + instruments).
4. `git log --oneline -8` — check whether the sibling line moved while you read.
5. Start the watchdog live leg if none is running (§10.2) — the 48h accumulation should
   be growing, not waiting.
6. Verify the pin suites pass at tip (§10.7).
7. Rehearse the pre-flight gate offline (§10.4 step 1) so you have seen its GO and its
   refusals before the operator's acts arrive.
8. Append an intake entry to `worklog.md` (who you are, what you verified) —
   append-only, with reviewer_provenance=AI_REVIEW.
9. Commit + push the intake (§10.6). Your existence is now durable.
10. Then WAIT for the operator's word-acts (GATE A: "2.9.0 stands" / "revert";
    GATE B: recover-first / resubmit). While waiting, legal work is: observer watches,
    reading, rehearsal — nothing else. When the acts land, §10.4 is the path.

**The single sentence that matters:** six terminals, then one bottleneck named by
measurement — everything else is noise, and the constitution is how you tell the
difference.
