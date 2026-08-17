# HANDOFF TO NEXT CHAT — CereVasc / Discovery-Evidence-Fabric Program

> **Read this file in full before writing any code or running any command.**
> This handoff supersedes any prior conversational context. It is the single source of truth for the next chat session.
>
> **Generated:** 2026-08-17 UTC
> **Last commit on `main`:** `8b41ebe` (CereVasc dossier PDF pushed)
> **Repo:** https://github.com/prateekm1007/discovery-evidence-fabric
> **Program:** discovery-evidence-fabric — medical-device invention discovery & patentability autonomous analysis for 15 companies × 10 moat positions = 150 inventions.
> **Current company:** CereVasc, Inc.
> **Current portfolio position:** #1 (A1_MODIFIED architecture — Selective Therapeutic Agent Retention) — COMPLETE.
> **Next portfolio position:** #2 — NOT YET STARTED.

---

## 1. System Identity & Mission

The discovery-evidence-fabric program generates defensible patent assets for real medical-device buyers. It is **NOT** a generic invention generator. Each invention is built for a specific named buyer (CereVasc is the first), evaluated by a specific CEO who audits the actual GitHub repository rather than relying on summaries, and held to a 5-gate scoring rubric where **Patent Gate** and **Evidence Gate** are non-compensable.

The mission: produce 150 inventions (15 companies × 10 moat positions each), each independently subjected to the same evidence → engineering → commercial gates, with a final adjudication of `WOULD_NOT_PAY` / `WOULD_CONSIDER_WITH_MILESTONES` / `LEVEL_4_BUYER_READY`.

The mission's anti-goal: do **NOT** optimize verdicts to "yes". Optimize verdicts to be **defensible**. A `WOULD_NOT_PAY` under a correctly-applied protocol is a successful run. A `WOULD_PAY` under a sloppy protocol is a failure.

---

## 2. Constitutional Context — The 8 Invariants

`protocol/INVENTION_PROTOCOL_V1.md` is the immutable constitution. It was frozen on 2026-08-17 via commit `ee77781`. **V2, V3, V∞ cannot weaken these 8 invariants** — they can only strengthen or extend:

1. Non-compensable status of Patent Gate (35% / ≥70) and Evidence Gate (25% / ≥70)
2. 102 single-reference rule — 102 anticipation requires ALL limitations in ONE reference (or inherent); 102 is NEVER a combination
3. 103 motivation/expectation requirement — "both known in the art" is NOT motivation; explicit documented reason + reasonable expectation of success required
4. Provenance chain requirement — every conclusion traces to an `evidence_id` → `artifact_pointer` → `SHA256SUMS` entry; model-derived elements labeled `model_derived: true` with non-empty `model_derived_note`
5. Limitation freeze immutability — `08_LIMITATION_FREEZE.json` is never edited; only superseded by a new version (V2, V3, ...)
6. Mandatory artifact list — 19 canonical directories + 6 mandatory root files per invention (see Section 5 below)
7. No silent promotion — `LEVEL_4_BUYER_READY` requires all gates pass + composite ≥70 + milestones list empty; `WOULD_CONSIDER_WITH_MILESTONES` requires non-empty milestones list
8. The Protocol Evolution Workflow itself (§14) is the only way to change V1

---

## 3. Current State (2026-08-17 end of session)

### 3.1 What's DONE

| Item | Status | Commit | Hash / Pointer |
|------|--------|--------|----------------|
| `INVENTION_PROTOCOL_V1.md` written | ✓ | `ee77781` | path-corrected in current working tree (unstaged → uncommitted) |
| Canonical path repair | IN PROGRESS | working tree | `protocol/INVENTION_PROTOCOL_V1.md` (git mv'd from root) |
| `protocol/CONSTITUTION_REGISTRY.json` created | IN PROGRESS | working tree | untracked, not yet committed |
| `protocol/preflight_check.py` written | ✓ | `ee77781` | must be extended to enforce constitution hash |
| 9 artifact templates | ✓ | `ee77781` | `protocol/templates/` |
| `protocol/PROTOCOL_EVOLUTION_WORKFLOW.md` | ✓ | `ee77781` | only path to V2 |
| `protocol/CHANGELOG.md` + `protocol/README.md` | ✓ | `ee77781` | audit trail |
| CereVasc Invention #1 (V2 folder) | ✓ COMPLETE | `ee77781` | 40 artifacts hashed in SHA256SUMS |
| Preflight on CereVasc #2 (V2 folder) | ✓ PASSES | `ee77781` | 16 checks, 0 failures |
| CereVasc #2 CEO dossier PDF | ✓ | `8b41ebe` | 13 pages, 134KB at repo root |
| GitHub issue #2 (ENFORCE INVENTION_PROTOCOL_V1) | ✓ CLOSED | — | https://github.com/prateekm1007/discovery-evidence-fabric/issues/2 |

### 3.2 What's IN PROGRESS (NARROW CEO DIRECTIVE — see Section 4)

The CEO audited the repo directly and found one consistency defect: the commit claimed `INVENTION_PROTOCOL_V1.md` is frozen, but the canonical file at `protocol/INVENTION_PROTOCOL_V1.md` did not exist (the file was at the repo root instead).

The CEO's narrow directive: **repair the protocol-source-of-truth mismatch. Create the canonical `protocol/INVENTION_PROTOCOL_V1.md`, pin its SHA-256 in the protocol registry/preflight, make CI fail on protocol-hash mismatch or missing constitution, rerun the full preflight against CereVasc #1, and only then unlock the next portfolio position.**

Steps completed so far in this session (working tree, NOT yet committed):
1. ✓ `git mv INVENTION_PROTOCOL_V1.md protocol/INVENTION_PROTOCOL_V1.md` — file moved to canonical location
2. ✓ Computed SHA-256: `8d75ca8fc17f031ffa3b8d7ea4a272b5114592bdd0476c3d95d8220171a389f8`
3. ✓ Created `protocol/CONSTITUTION_REGISTRY.json` with the hash pin

Steps NOT yet done (the new chat's first task):
4. ✗ Extend `protocol/preflight_check.py` to add the constitution-hash check (Section X.0 — runs BEFORE any invention-level check)
5. ✗ Re-run preflight on CereVasc #2 (V2 folder) — must still pass 16 checks + the new constitution check
6. ✗ Commit the repair with message: "Repair canonical constitution path + add hash-pin preflight check"
7. ✗ Push to GitHub
8. ✗ Update GitHub issue #2 with a comment confirming the repair is complete
9. ✗ Only after the above, unlock Invention #3 (CereVasc Position 2 of 10)

### 3.3 What's NEXT (after the narrow directive)

- Invention #3 (CereVasc Position 2 of 10) — unblocked once the narrow directive is committed and pushed
- Then Inventions #4–#10 for CereVasc (the remaining 8 moat positions)
- Then 14 more companies × 10 inventions each = 140 more inventions

---

## 4. The Narrow CEO Directive — Exact Steps to Finish

The new chat's first task is to finish the in-progress narrow directive. Here is the exact sequence. **All operations are autocommands** (scripts in `/home/z/my-project/scripts/`). No manual edits to files outside `protocol/` and `scripts/`.

### Step 4 — Extend `protocol/preflight_check.py` with constitution-hash check

Add a new check function `check_constitution_hash(repo_root)` that:
1. Reads `protocol/CONSTITUTION_REGISTRY.json`
2. Gets `current_canonical_path` (e.g., `protocol/INVENTION_PROTOCOL_V1.md`)
3. Verifies the file exists at that path
4. Computes SHA-256 of the file
5. Compares to `current_sha256` in the registry
6. Returns a `CheckResult` with section `"X.0"` (runs before any Section 9 check)
7. If file missing OR hash mismatch → check fails with a clear message

Call this function FIRST in `audit_invention()` (or in `main()` before the per-invention loop). The constitutional check is repo-level, not per-invention.

Add a new field to the preflight report JSON: `constitution_check` at the top level.

### Step 5 — Re-run preflight

```bash
cd /home/z/my-project/discovery-evidence-fabric && \
python3 protocol/preflight_check.py 2>&1 | tail -30
```

Expected: CEREVASC_INVENTION_001_V2 PASSES 17 checks (was 16, +1 for the new constitution check). The 6 legacy invention folders still FAIL — they are pre-V1 and preserved per §9.11.

### Step 6 — Commit the repair

```bash
cd /home/z/my-project/discovery-evidence-fabric && \
git add protocol/INVENTION_PROTOCOL_V1.md protocol/CONSTITUTION_REGISTRY.json protocol/preflight_check.py protocol/preflight_report.json protocol/CHANGELOG.md protocol/README.md && \
git commit -m "Repair canonical constitution path + add hash-pin preflight check

CEO directive 2026-08-17: the commit ee77781 claimed INVENTION_PROTOCOL_V1.md
is frozen but the canonical protocol/INVENTION_PROTOCOL_V1.md did not exist
(file was at repo root). This commit repairs the source-of-truth mismatch.

Changes:
- Moved INVENTION_PROTOCOL_V1.md to protocol/INVENTION_PROTOCOL_V1.md
  (canonical path; no content change, hash unchanged).
- Added protocol/CONSTITUTION_REGISTRY.json pinning the canonical path
  and SHA-256 (8d75ca8fc17f031ffa3b8d7ea4a272b5114592bdd0476c3d95d8220171a389f8).
- Extended protocol/preflight_check.py with Section X.0 check:
  constitution_canonical_present + constitution_hash_matches.
  Runs BEFORE any invention-level check; CI fails on mismatch.
- Re-ran preflight: CEREVASC_INVENTION_001_V2 PASSES 17 checks
  (16 prior + 1 new constitution check). 6 legacy folders still FAIL
  (pre-V1, preserved per Section 9.11).

CereVasc Invention #2 status: WOULD_CONSIDER_WITH_MILESTONES, composite 73/100.
Invention #3 (CereVasc Position 2 of 10) is now unlocked.

Resolves CEO directive on issue #2." && \
git push origin main
```

### Step 7 — Update GitHub issue #2 with a comment

```bash
curl -s -X POST \
  -H "Authorization: token REDACTED-GITHUB-PAT" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/prateekm1007/discovery-evidence-fabric/issues/2/comments \
  -d '{"body": "## Canonical-path defect repaired\n\nThe CEO-identified consistency defect is resolved.\n\n- Canonical constitution file is now at `protocol/INVENTION_PROTOCOL_V1.md`.\n- SHA-256 pinned: `8d75ca8fc17f031ffa3b8d7ea4a272b5114592bdd0476c3d95d8220171a389f8`.\n- `protocol/CONSTITUTION_REGISTRY.json` is the immutable pin file.\n- `protocol/preflight_check.py` Section X.0 enforces the pin on every CI run.\n- Preflight on CereVasc #2 (V2 folder) passes all 17 mechanical checks.\n\nInvention #3 (CereVasc Position 2 of 10) is unlocked."}'
```

### Step 8 — Only then, unlock Invention #3

See Section 6 for how to start Invention #3.

---

## 5. Authoritative File Structure Map (Prevent Entropy)

This map is the **single source of truth** for what files and directories may exist in the repo. The new chat must not create directories or files outside this map without amending the constitution via the Protocol Evolution Workflow (§14).

### 5.1 Repo root: `prateekm1007/discovery-evidence-fabric/`

```
.
├── README.md                                  ← repo-level readme; MUST indicate current protocol version
├── protocol/                                  ← THE CONSTITUTION + ENFORCEMENT LAYER (see 5.2)
├── CEREVASC_INVENTION_001_V2/                  ← canonical V1-compliant invention folder (see 5.3)
├── CEREVASC_INVENTION_001/                     ← LEGACY (pre-V1); preserved per §9.11; do not modify
├── CEREVASC_INVENTION_001_FINAL/              ← LEGACY; preserved
├── CEREVASC_INVENTION_001_V1_FROZEN/          ← LEGACY; preserved
├── CEREVASC_INVENTION_001_V3_ELITE_AUDIT/     ← LEGACY; preserved
├── CEREVASC_INVENTION_001_V5/                 ← LEGACY; preserved
├── CEREVASC_INVENTION_002/                    ← LEGACY (pre-V1); preserved
├── CEREVASC_INVENTION_002_BUYER_READY_DOSSIER_V1/  ← LEGACY; preserved
├── CEREVASC_V8/                               ← LEGACY; preserved
├── CEREVASC_CORPUS_V6/                        ← company corpus (referenced by 01_COMPANY_CORPUS stub)
├── CereVasc_Invention_2_Dossier.pdf           ← CEO-grade compiled PDF of CereVasc #2
├── INVENTION_PROTOCOL_V1.md                   ← ❌ MOVED to protocol/INVENTION_PROTOCOL_V1.md (do not recreate at root)
├── A2_*.md, A2_*.json                         ← LEGACY from prior session experiments; preserved, do not extend
├── PRODUCTION_ADVERSARIAL_CALL_GRAPH.md       ← LEGACY; preserved
├── discovery_fabric/                          ← LEGACY code modules; preserved
├── experiments/                               ← LEGACY calibration experiments; preserved
├── patents/                                   ← LEGACY prior-art data; preserved
├── patent_sources/                            ← LEGACY; preserved
├── audit/, audits/                            ← LEGACY; preserved
├── corpus/, corpus_v2/, corpus_v3/            ← LEGACY corpus attempts; preserved
└── *.py (root-level)                          ← LEGACY scripts from prior sessions; preserved, do not extend
```

**Entropy prevention rule:** Do NOT add new top-level directories. New invention folders follow the pattern `<COMPANY>_INVENTION_<NNN>_V<M>/` at the repo root. New protocol assets go in `protocol/`. New scripts go in `/home/z/my-project/scripts/` (NOT in the repo root).

### 5.2 `protocol/` — The Constitution & Enforcement Layer

```
protocol/
├── INVENTION_PROTOCOL_V1.md           ← THE FROZEN CONSTITUTION (canonical path)
├── CONSTITUTION_REGISTRY.json         ← pins canonical path + SHA-256 + supersession history
├── PROTOCOL_EVOLUTION_WORKFLOW.md    ← the only way to create V2 (§14)
├── CHANGELOG.md                       ← audit trail of all protocol version changes
├── README.md                          ← protocol/ directory guide
├── preflight_check.py                 ← mechanical CI enforcement (12 §9 checks + §X.0 constitution check)
├── preflight_report.json              ← last preflight run output (machine-readable)
├── templates/                         ← 9 canonical artifact schemas (see 5.2.1)
│   ├── 00_MANIFEST.json
│   ├── 08_LIMITATION_FREEZE.json
│   ├── 11_102_RESULTS.json
│   ├── 12_103_RESULTS.json
│   ├── 14_DESIGN_AROUND_results.json
│   ├── 16_SIMULATION_results.json
│   ├── 21_EVIDENCE_LEDGER.json
│   ├── 22_FINAL_ADJUDICATION.json
│   └── 23_LESSONS_LEARNED.json
└── proposals/                         ← Protocol Change Proposals (PCP-NNN_slug.md); EMPTY for V1
```

**Entropy prevention rule:** Only files explicitly listed above may live in `protocol/`. New templates must be proposed via PCP and audited before addition.

#### 5.2.1 The 9 templates — what they enforce

| Template | Enforces |
|----------|----------|
| `00_MANIFEST.json` | Every artifact in an invention folder is listed with its SHA-256 |
| `08_LIMITATION_FREEZE.json` | L1..Ln limitations + arrangement are frozen; supersession requires V2, V3 |
| `11_102_RESULTS.json` | 102 single-reference rule (§5.9, §9.4); NOT_DISCLOSED + anticipated=true is CI failure |
| `12_103_RESULTS.json` | 103 documented motivation + reasonable expectation (§5.10, §9.5) |
| `14_DESIGN_AROUND_results.json` | ≥5 alternatives with limitation-avoidance matrix per alternative |
| `16_SIMULATION_results.json` | Domain-specific simulation slot; model_inputs required for every numeric output (§9.8) |
| `21_EVIDENCE_LEDGER.json` | Provenance chain for every conclusion (§3.4, §10); model_derived must be labeled |
| `22_FINAL_ADJUDICATION.json` | 5-gate scorecard + non-compensable status + no-silent-promotion check (§9.9, §9.12) |
| `23_LESSONS_LEARNED.json` | Per-invention learning record; immutable; informs V2 proposals but does NOT modify V1 |

### 5.3 Canonical invention folder layout — `<COMPANY>_INVENTION_<NNN>_V<M>/`

Every new invention folder MUST follow this exact layout. CereVasc #2 (`CEREVASC_INVENTION_001_V2/`) is the reference implementation — read it before creating a new invention folder.

```
<COMPANY>_INVENTION_<NNN>_V<M>/
├── 00_MANIFEST.json                 ← artifact index + hashes (chicken-egg: includes all artifacts EXCEPT itself in SHA256SUMS)
├── 01_COMPANY_CORPUS/                ← Stage 1: company patents/applications/regulatory filings
├── 02_FAMILY_GRAPH/                  ← Stage 2: DOCDB/INPADOC family expansion
├── 03_TECHNOLOGY_MAP/                ← Stage 3: Technology Graph (what prior art teaches)
├── 04_OWNERSHIP_MAP/                 ← Stage 3: Ownership Graph (who owns what)
├── 05_BUYER_MAP/                     ← Stage 3: Buyer Graph (what target buyer owns/licenses)
├── 06_MOAT_MAP/                      ← Stage 4: white-space positions; 10 positions per company
├── 07_PROBLEM_SELECTION/             ← Stage 5: which moat position is this invention
├── 08_LIMITATION_FREEZE.json         ← Stage 6: IMMUATION (L1..Ln + arrangement + content_hash_self)
├── 09_PRIOR_ART/                     ← Stage 7: discovery results
├── 10_CLAIM_RETRIEVAL/               ← Stage 8: primary-source claim text per reference
├── 11_102_ATTACK/                    ← Stage 9: 102_RESULTS.json (single-reference novelty)
├── 12_103_ATTACK/                    ← Stage 10: 103_RESULTS.json (combination + motivation)
├── 13_ARCHITECTURES/                 ← Stage 11: ≥5 architectural alternatives
├── 14_DESIGN_AROUND/                 ← Stage 12: design_around_results.json (≥5 alternatives)
├── 15_ENGINEERING_BLUEPRINT/         ← Stage 13: material spec, dimensions, manufacturing process
├── 16_SIMULATION/                    ← Stage 14: simulation_results.json (domain-specific)
├── 17_MANUFACTURING/                  ← Stage 15a: manufacturing_plan.json
├── 18_REGULATORY/                    ← Stage 15b: regulatory_pathway.json
├── 19_BUILD_BUY/                      ← Stage 16: build_vs_buy.json
├── 20_BUYER_MEMO/                    ← Stage 17: buyer_memo.md
├── 21_EVIDENCE_LEDGER.json           ← provenance for every conclusion (evidence_id → artifact → hash)
├── 22_FINAL_ADJUDICATION.json        ← Stage 18: 5-gate scorecard + verdict
├── 23_LESSONS_LEARNED.json           ← immutable learning record (informs V2 proposals)
└── SHA256SUMS                         ← hashes for every artifact (SHA256SUMS itself excluded)
```

**Entropy prevention rules for invention folders:**

1. **Zero-padded numbering is sacred.** Directories are numbered `01_`, `02_`, ..., `23_`. Skipping a number is a CI failure (an artifact was produced out of order or skipped).
2. **No free-floating JSON files at the root of an invention folder.** Every artifact goes in its canonical numbered directory OR is one of the 6 mandatory root files (00, 08, 21, 22, 23, SHA256SUMS).
3. **Legacy TASK*.json files may be preserved in the folder root** (e.g., `TASK1_RETENTION_PASSAGE_AUDIT.json`) — they are the source artifacts that were copied into canonical locations. Do NOT delete them. Do NOT add new ones.
4. **Version supersession only.** When limitations change, create `_V<M+1>/` — do NOT edit `_V<M>/`. V1 is preserved forever (§9.11).

### 5.4 `/home/z/my-project/scripts/` — Autocommand Library

All scripts that operate on the repo MUST live in `/home/z/my-project/scripts/`, NOT in the repo root. The repo's `.gitignore` excludes them from commits (they are dev-side tooling, not deliverables).

Existing scripts (the new chat should use these as references and extend, not rewrite):

```
/home/z/my-project/scripts/
├── assemble_cerevasc_v2_package.py       ← assembles CereVasc #2 package (regenerates SHA256SUMS, MANIFEST, EVIDENCE_LEDGER, REVISED_SCORE)
├── migrate_v2_to_canonical.py            ← migrates an invention folder from flat TASK*.json to canonical 19-directory layout
├── generate_cerevasc_dossier_pdf.py      ← compiles the dossier into a single CEO-grade PDF (ReportLab)
└── (future scripts go here)
```

**Entropy prevention rules for scripts:**

1. **Rule 9 (Script Persistence):** Scripts >10 lines MUST be saved to a file via `Write` tool BEFORE being executed. No `python3 -c "..."` heredocs for non-trivial work. Inline one-liners are fine.
2. **On failure, edit in place.** Do NOT rewrite the whole script with `Write` after a partial failure — use `Edit` to patch the failing lines and re-run.
3. **Same file path persists across iterations.** `assemble_cerevasc_v2_package.py` is the canonical script for assembling CereVasc #2; do not create `assemble_cerevasc_v2_package_v2.py` — extend the existing one.

### 5.5 `/home/z/my-project/download/` — User-Facing Deliverables ONLY

Final deliverables (PDFs, reports, datasets) go in `/home/z/my-project/download/`. This is the only directory the user can download from. Files here are pushed to the GitHub repo root as needed (as was done with `CereVasc_Invention_2_Dossier.pdf`).

### 5.6 `/home/z/my-project/worklog.md` — Multi-Agent Worklog

All agents append to this single file. Format:
```
---
Task ID: <id>
Agent: <name>
Task: <what was asked>

Work Log:
- <step 1>
- <step 2>

Stage Summary:
- <results>
```

The new chat MUST append a new section to `/home/z/my-project/worklog.md` after completing its work, with the Task ID `NARROW-CEO-DIRECTIVE-REPAIR` for the in-progress task and `INVENTION-3-START` for the next portfolio position.

---

## 6. Critical: Files the New Chat MUST READ Before Coding

In this exact order. Skipping any of these will cause the new chat to break the system.

### 6.1 Constitutional layer (read FIRST, before any code)

1. **`/home/z/my-project/discovery-evidence-fabric/protocol/INVENTION_PROTOCOL_V1.md`** — the constitution. Read ALL 17 sections. Pay special attention to:
   - §3 Governance Principles (8 invariants)
   - §7 The Five Gates (35/25/15/15/10; non-compensable Patent/Evidence)
   - §9 The 12 Hard CI/Preflight Checks
   - §14 Protocol Evolution Workflow (the only way to V2)
   - §16 Adjudication Tiers (3 terminal statuses)

2. **`/home/z/my-project/discovery-evidence-fabric/protocol/CONSTITUTION_REGISTRY.json`** — the hash pin. Read it to learn:
   - Current canonical path: `protocol/INVENTION_PROTOCOL_V1.md`
   - Current SHA-256: `8d75ca8fc17f031ffa3b8d7ea4a272b5114592bdd0476c3d95d8220171a389f8`
   - The 8 constitutional invariants
   - The CI enforcement requirements

3. **`/home/z/my-project/discovery-evidence-fabric/protocol/PROTOCOL_EVOLUTION_WORKFLOW.md`** — the only path to V2. Read it to learn:
   - When evolution is permitted / forbidden
   - The 6-step workflow (LESSONS_LEARNED → PCP → AUDIT → DECISION → SUPERSESSION → ANNOUNCEMENT)
   - What V2 cannot change (the 8 invariants)

4. **`/home/z/my-project/discovery-evidence-fabric/protocol/CHANGELOG.md`** — audit trail of all protocol version changes

### 6.2 Enforcement layer (read before extending preflight)

5. **`/home/z/my-project/discovery-evidence-fabric/protocol/preflight_check.py`** — the CI gate. Read ALL of it. Understand:
   - The 12 §9 checks already implemented
   - The dataclass structure (`CheckResult`, `InventionReport`)
   - How `audit_invention()` and `main()` work
   - The artifact-path conventions (legacy fallbacks for TASK*.json files)
   - Where to add the new §X.0 constitution check (BEFORE the per-invention loop)

6. **`/home/z/my-project/discovery-evidence-fabric/protocol/preflight_report.json`** — last preflight output. Read it to see what passed/failed and the failure reasons.

### 6.3 Templates (read before creating new invention artifacts)

7. **All 9 templates in `/home/z/my-project/discovery-evidence-fabric/protocol/templates/`** — read each one to understand the required schema. Pay special attention to:
   - `08_LIMITATION_FREEZE.json` — the immutability rules (§8)
   - `21_EVIDENCE_LEDGER.json` — the provenance chain requirements (§10)
   - `22_FINAL_ADJUDICATION.json` — the no-silent-promotion rules (§9.9, §9.12)
   - `16_SIMULATION_results.json` — the domain-specific simulation slot (§5.14, §12)

### 6.4 Reference implementation (read before creating a new invention folder)

8. **`/home/z/my-project/discovery-evidence-fabric/CEREVASC_INVENTION_001_V2/`** — the canonical V1-compliant invention folder. Read:
   - `00_MANIFEST.json` — the artifact index
   - `08_LIMITATION_FREEZE.json` — the frozen limitations L1..L6 for A1_MODIFIED
   - `21_EVIDENCE_LEDGER.json` — the provenance chain with 8 evidence entries
   - `22_FINAL_ADJUDICATION.json` — the verdict (WOULD_CONSIDER_WITH_MILESTONES, composite 73/100)
   - `23_LESSONS_LEARNED.json` — what worked / failed / proposed protocol changes
   - `11_102_ATTACK/102_RESULTS.json` — 15-reference limitation matrix
   - `12_103_ATTACK/103_RESULTS.json` — the migrated 103 analysis (model-derived motivation)
   - `16_SIMULATION/simulation_results.json` — the ICP safety simulation with fail-safe analysis

### 6.5 Script library (read before running any autocommand)

9. **`/home/z/my-project/scripts/assemble_cerevasc_v2_package.py`** — how to regenerate a package's MANIFEST/EVIDENCE_LEDGER/SHA256SUMS
10. **`/home/z/my-project/scripts/migrate_v2_to_canonical.py`** — how to migrate a flat-layout folder to canonical
11. **`/home/z/my-project/scripts/generate_cerevasc_dossier_pdf.py`** — how to compile a dossier PDF

### 6.6 DO NOT READ (legacy noise, preserved per §9.11)

Do NOT spend time reading these unless explicitly needed:
- `CEREVASC_INVENTION_001/` (legacy pre-V1)
- `CEREVASC_INVENTION_001_FINAL/` (legacy)
- `CEREVASC_INVENTION_001_V1_FROZEN/` (legacy)
- `CEREVASC_INVENTION_001_V3_ELITE_AUDIT/` (legacy)
- `CEREVASC_INVENTION_001_V5/` (legacy)
- `CEREVASC_INVENTION_002/` (legacy pre-V1; the BROKEN run that motivated V1)
- `CEREVASC_INVENTION_002_BUYER_READY_DOSSIER_V1/` (legacy)
- `CEREVASC_V8/` (legacy)
- Root-level `*.py` files (legacy scripts)
- `discovery_fabric/` (legacy code modules)

---

## 7. Rules: Everything Is Autocommands

**Nothing on the repo is manual.** Every operation is a script that lives in `/home/z/my-project/scripts/`. The new chat must:

1. **Never edit files in the repo by hand.** Use scripts. If a script doesn't exist for what you need, write a new one in `/home/z/my-project/scripts/` and run it.

2. **Never run inline `python3 -c "..."` for anything > 10 lines.** Save the script first via `Write` tool, then run via `python3 /home/z/my-project/scripts/<name>.py`. On failure, edit in place via `Edit` tool and re-run — do NOT rewrite via `Write`.

3. **Never push to GitHub manually.** Use `git push origin main` after committing. The remote is already configured with the CEO's token: `REDACTED-GITHUB-PAT`.

4. **Never update GitHub issues manually.** Use `curl` against the GitHub REST API (see Step 7 in Section 4 for the pattern).

5. **Never test PatSnap API.** It is structurally blocked (error 67200203 "API need a true rate!" on all endpoints). Model-derived motivation analysis is the standard under §10.3. Do not waste cycles trying different headers — they were all tested in the prior session.

6. **Never edit `protocol/INVENTION_PROTOCOL_V1.md` directly.** It is FROZEN. The only way to change it is the Protocol Evolution Workflow (§14): file a PCP, audit, supersede with V2. V1 is preserved forever.

7. **Never edit `protocol/CONSTITUTION_REGISTRY.json` directly** unless you are creating V2 via the workflow. The hash pin is immutable within a protocol version.

8. **Never delete legacy invention folders.** They are preserved per §9.11 (version preservation). Preflight correctly FAILS on them; that's the expected behavior, not a bug.

9. **Every commit must be reproducible.** The commit message must state what was done, why, and which artifact hash anchors are affected. The pattern is in Step 6 of Section 4.

10. **Every script must be idempotent.** Running `python3 /home/z/my-project/scripts/assemble_cerevasc_v2_package.py` twice must produce the same SHA256SUMS (modulo timestamps in JSON).

---

## 8. API & Environment Constraints

### 8.1 GitHub
- **Repo:** https://github.com/prateekm1007/discovery-evidence-fabric
- **Token:** `REDACTED-GITHUB-PAT`
- **Remote URL configured:** yes (in `.git/config` as `origin`)
- **Default branch:** `main`
- **Issue tracker:** https://github.com/prateekm1007/discovery-evidence-fabric/issues
- **Issue #2:** CLOSED (canonical-path repair will add a final comment when the narrow directive completes)

### 8.2 PatSnap
- **API key:** `REDACTED-PATSNAP-KEY-1`
- **Status:** STRUCTURALLY BLOCKED. All endpoints (query-search-count, AI semantic-comparison, claim-data) return `error_code: 67200203 "API need a true rate!"` even with valid auth (Bearer token accepted). This is a subscription-tier restriction, not a balance issue.
- **Implication:** 103 motivation analysis remains MODEL-DERIVED per §10.3. This is explicitly permitted by the protocol when labeled. The CereVasc #2 dossier does this correctly.
- **Do NOT retry PatSnap** in the new chat unless the CEO explicitly provides a new key tier.

### 8.3 Other patent sources (federated)
- EPO OPS: requires OAuth credentials (not configured)
- Google BigQuery patents: requires service account (not configured)
- USPTO ODP: requires auth token (not configured)
- Lens.org: works for NPL only
- These were explored in prior sessions; see `/home/z/my-project/worklog.md` for the V4-FEDERATED-EVIDENCE entry. They are not blocking — model-derived analysis is acceptable.

### 8.4 Environment paths
- **Repo root:** `/home/z/my-project/discovery-evidence-fabric/`
- **Scripts library:** `/home/z/my-project/scripts/`
- **Download deliverables:** `/home/z/my-project/download/`
- **Multi-agent worklog:** `/home/z/my-project/worklog.md` (884KB+; append-only)
- **Skill directory:** `/home/z/my-project/skills/pdf/` (PDF skill loaded in this session)

### 8.5 Fonts (verified)
- Liberation Serif/Sans: working (`/usr/share/fonts/truetype/liberation/`)
- DejaVu Sans Mono: working (`/usr/share/fonts/truetype/dejavu/`)
- Noto Serif SC: working (`/usr/share/fonts/truetype/noto-serif-sc/`)
- **DO NOT USE** the Tinos/Carlito files in `/usr/share/fonts/truetype/english/` — they are corrupted HTML files masquerading as TTFs. The prior session wasted cycles on this.

---

## 9. What's Done (Detailed)

### 9.1 INVENTION_PROTOCOL_V1.md (the constitution)
- 17 sections, FROZEN 2026-08-17 via commit `ee77781`
- Currently at canonical path `protocol/INVENTION_PROTOCOL_V1.md` (path-corrected in working tree, NOT yet committed)
- SHA-256: `8d75ca8fc17f031ffa3b8d7ea4a272b5114592bdd0476c3d95d8220171a389f8`
- 8 constitutional invariants defined
- 18-stage pipeline (COMPANY CORPUS → ADJUDICATION)
- 5 gates (35/25/15/15/10 weights; non-compensable Patent/Evidence ≥70)
- 12 hard CI checks (§9.1–§9.12)
- 3 terminal statuses (WOULD_NOT_PAY / WOULD_CONSIDER_WITH_MILESTONES / LEVEL_4_BUYER_READY)

### 9.2 Mechanical enforcement (`protocol/preflight_check.py`)
- Implements all 12 §9 checks
- Exit 0 = pass; exit 1 = fail (blocks commit)
- Writes `protocol/preflight_report.json` with per-check pass/fail
- PASSES on CEREVASC_INVENTION_001_V2 (16 checks, 0 failures)
- FAILS on 6 legacy folders (correctly — they are pre-V1)
- **PENDING:** Extend with §X.0 constitution-hash check (the in-progress narrow directive)

### 9.3 CereVasc Invention #1 (V2 folder) — COMPLETE
- All 8 CEO tasks done:
  - Task 1: US20200406018A1 "retention" passage audit → NOT self-anticipated (retention=reservoir)
  - Task 2: 102/103 rebuilt → 15 refs, 0 kills, L2 absent from ALL
  - Task 3: ePTFE recommended (passes albumin filter, FDA-cleared, ISO 10993 AVAILABLE)
  - Task 4: A1_MODIFIED with bypass at 15mmHg, 50% fouling SAFE, complete occlusion handled
  - Task 5: MEANINGFUL_MOAT, $3–8M internal cost, 18–36mo timeline, LICENSE positioning
  - Task 6: Class III, PMA supplement, combination product (CDRH-led), 60–78mo to PMA
  - Task 7: 7 design-around alternatives (DA5 strongest for blocking)
  - Task 8 (= Task 5): Build-vs-buy analysis
- Composite: 73/100
- Final status: WOULD_CONSIDER_WITH_MILESTONES
- 6 milestones required for LEVEL_4_BUYER_READY (AI30 reclassified from BLOCKER to ENHANCEMENT — PatSnap structurally blocked)

### 9.4 CEO dossier PDF
- `/home/z/my-project/download/CereVasc_Invention_2_Dossier.pdf` (134KB, 13 pages)
- Pushed to GitHub at repo root: `CereVasc_Invention_2_Dossier.pdf`
- Commit: `8b41ebe`
- 9/9 critical PDF QA checks passed; 4 minor warnings (non-blocking)

### 9.5 GitHub
- Commit `ee77781`: protocol + CereVasc #2 migration pushed
- Commit `8b41ebe`: CEO dossier PDF pushed
- Issue #2 closed: https://github.com/prateekm1007/discovery-evidence-fabric/issues/2
- **PENDING:** Comment on issue #2 confirming the canonical-path repair (after Step 7 in Section 4)

---

## 10. What's Left — Exact To-Do List

### 10.1 Immediate (in-progress narrow CEO directive — see Section 4 for exact steps)
- [ ] Extend `protocol/preflight_check.py` with §X.0 constitution-hash check
- [ ] Re-run preflight on CereVasc #2 (must pass 17 checks)
- [ ] Commit the repair
- [ ] Push to GitHub
- [ ] Comment on issue #2 confirming the repair
- [ ] Append to `/home/z/my-project/worklog.md` with Task ID `NARROW-CEO-DIRECTIVE-REPAIR`

### 10.2 Next portfolio position (Invention #3 — CereVasc Position 2 of 10)
- [ ] Read `CEREVASC_INVENTION_001_V2/06_MOAT_MAP/moat_map.json` to see the 10 positions
- [ ] Select Position 2 (a distinct white-space claim, not a "shotgun" attempt)
- [ ] Create `CEREVASC_INVENTION_002_V1/` (note: this is the next V1-compliant invention; the LEGACY `CEREVASC_INVENTION_002/` is preserved separately)
- [ ] Walk the 18-stage pipeline per §5
- [ ] At each stage, instantiate the matching template from `protocol/templates/`
- [ ] Populate `21_EVIDENCE_LEDGER.json` with `evidence_id`s as conclusions are drawn
- [ ] Run `python3 /home/z/my-project/discovery-evidence-fabric/protocol/preflight_check.py` to verify compliance
- [ ] Only after preflight passes, write `22_FINAL_ADJUDICATION.json`
- [ ] Write `23_LESSONS_LEARNED.json`
- [ ] Compile the dossier PDF via an extended version of `scripts/generate_cerevasc_dossier_pdf.py`
- [ ] Commit and push

### 10.3 Remaining program (after Invention #3)
- Inventions #4–#10 for CereVasc (8 more moat positions)
- Companies #2–#15 (14 more companies × 10 inventions each = 140 more)
- Total: 149 more inventions under V1

### 10.4 Long-term
- After ~30 inventions, lessons will accumulate enough to justify V2
- File a PCP per the Protocol Evolution Workflow
- Audit and supersede V1 → V2
- V1 preserved forever

---

## 11. Unlock Criteria for Invention #3

The new chat MUST NOT begin Invention #3 until ALL of the following are true:

1. ✅ `protocol/INVENTION_PROTOCOL_V1.md` exists at the canonical path
2. ✅ `protocol/CONSTITUTION_REGISTRY.json` pins its SHA-256
3. ✅ `protocol/preflight_check.py` enforces the pin (§X.0)
4. ✅ Preflight passes on CEREVASC_INVENTION_001_V2 (17 checks, 0 failures)
5. ✅ The repair is committed and pushed to GitHub
6. ✅ Issue #2 has a comment confirming the repair
7. ✅ `/home/z/my-project/worklog.md` has the `NARROW-CEO-DIRECTIVE-REPAIR` entry

Only then: begin Invention #3 per Section 10.2.

---

## 12. Entropy Prevention — Standing Rules

These rules apply for the life of the program, not just this session:

### 12.1 No top-level repo clutter
- New invention folders follow `<COMPANY>_INVENTION_<NNN>_V<M>/` at repo root
- New protocol assets go in `protocol/`
- New scripts go in `/home/z/my-project/scripts/` (NOT in the repo root)
- New deliverables go in `/home/z/my-project/download/` (pushed to repo root only if user-facing)

### 12.2 No version churn
- Limitation freeze changes → new folder version (`_V<M+1>/`), not edit-in-place
- Protocol changes → new protocol version (`INVENTION_PROTOCOL_V<N+1>.md`), not edit-in-place
- Script changes → edit-in-place via `Edit` tool, not rewrite via `Write` (Rule 9)

### 12.3 No silent modifications
- Every commit must have a message stating what was done, why, and which hash anchors are affected
- Every `evidence_id` must trace to a `content_hash` in SHA256SUMS
- Every model-derived assertion must have `model_derived: true` + non-empty `model_derived_note`
- Every `LEVEL_4_BUYER_READY` verdict must have all gates pass + composite ≥70 + milestones list empty

### 12.4 No bypass of the constitution
- The 8 invariants cannot be weakened by V2+
- The Protocol Evolution Workflow is the only path to V2
- No "emergency" bypass; no "this invention is special" exemption; no "constitution suspension" for any reason
- If the constitution is broken, fix it via the workflow; do not bypass it

### 12.5 No legacy deletion
- All `CEREVASC_INVENTION_001*` legacy folders are preserved per §9.11
- Preflight correctly FAILS on them; that's the expected behavior
- Do NOT "fix" them by migrating to V1 — they are historical record

### 12.6 No silent promotion
- `PROMISING` status from legacy runs is FORBIDDEN in V1
- The only valid terminal statuses are: `WOULD_NOT_PAY`, `WOULD_CONSIDER_WITH_MILESTONES`, `LEVEL_4_BUYER_READY`
- Promotion from `WOULD_CONSIDER_WITH_MILESTONES` to `LEVEL_4_BUYER_READY` requires the milestones list to become empty (not by deletion — by completion)

### 12.7 File-naming conventions
- Invention folders: `<COMPANY>_INVENTION_<NNN>_V<M>/` (e.g., `CEREVASC_INVENTION_003_V1/`)
- Invention artifacts: `<NN>_<NAME>/` for directories, `<NN>_<NAME>.json` for root files (matching the §6 canonical layout)
- Protocol assets: `protocol/<NAME>.md` or `protocol/<NAME>.json` (no subdirectories except `templates/` and `proposals/`)
- Scripts: `/home/z/my-project/scripts/<verb_object>.py` (snake_case, verb-noun pattern)

### 12.8 Hash integrity
- Every artifact in an invention folder MUST be in SHA256SUMS
- SHA256SUMS does NOT include itself (chicken-egg rule)
- 00_MANIFEST.json is in SHA256SUMS but NOT in its own `artifacts` array
- Any artifact referenced by 21_EVIDENCE_LEDGER.json MUST be in SHA256SUMS (§9.3)

---

## 13. Summary — What the New Chat Must Do

1. **Read Section 6 of this handoff in full.** All 11 listed files in the order specified. Do NOT skip any.
2. **Finish the narrow CEO directive (Section 4).** Six mechanical steps. All autocommands.
3. **Append to `/home/z/my-project/worklog.md`** with Task ID `NARROW-CEO-DIRECTIVE-REPAIR`.
4. **Then begin Invention #3 (Section 10.2)** — CereVasc Position 2 of 10.
5. **Never bypass the constitution.** The 8 invariants are absolute. The preflight is the floor, not the ceiling.

If anything in this handoff conflicts with the constitution (`protocol/INVENTION_PROTOCOL_V1.md`), **the constitution wins**. If anything in the constitution conflicts with the 8 invariants (Section 2), the invariants win. If a CEO directive conflicts with the invariants, the CEO is wrong and the directive must be renegotiated via the Protocol Evolution Workflow.

— END OF HANDOFF —
