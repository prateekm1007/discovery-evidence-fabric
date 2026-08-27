# COMPREHENSIVE HANDOFF DOCUMENT — CereVascular eShunt Discovery System

**Date:** 2026-08-27
**From:** Previous chat session (R370 through R370Z)
**To:** New chat session
**Purpose:** Enable the new chat to continue work without needing old conversation context

---

## 1. SYSTEM OVERVIEW

### What this system is

An AI-driven autonomous discovery engine that generates, validates, and distributes engineering technology-transfer dossiers for 15 CSF (cerebrospinal fluid) shunt improvement technologies. The system has progressed from pure AI discovery through engineering documentation, external consultant audit, AI learning, V2 mutation, and buyer-ready distribution.

### The two GitHub repositories

| Repository | Role | URL | Current HEAD |
|-----------|------|-----|-------------|
| **discovery-evidence-fabric** | Development/intelligence repo — contains all source code, engineering dossiers, audit scripts, external evidence | `https://github.com/prateekm1007/discovery-evidence-fabric` | `bf97cdfde4fa8dd0b9f6c4d6b67e3f5669089e1b` |
| **technology-transfer-portfolio-15** | Buyer-facing distribution repo — contains 15 complete buyer packages, PDFs, ZIPs, manifests | `https://github.com/prateekm1007/technology-transfer-portfolio-15` | `2e96b2778d9388bcbf4172281567dec6fe3d58d6` (FROZEN — terminal commit) |

### Critical: GitHub authentication

The GitHub token is stored in the dev repo's git config (redacted as `[REDACTED:github_token]`). To extract it:

```bash
cd /home/z/my-project/discovery-evidence-fabric
TOKEN=$(git config --get remote.origin.url | sed -n 's|.*://prateekm1007:\([^@]*\)@.*|\1|p')
echo "$TOKEN" > /tmp/gh_token.txt
```

Use this token for all GitHub API calls and git operations on the portfolio repo.

---

## 2. FILE STRUCTURE — DO NOT BREAK THIS

### Development repo: `/home/z/my-project/discovery-evidence-fabric/`

```
discovery-evidence-fabric/
├── EPISTEMIC_CONSTITUTION.md                    ← v1.8.0, 38 articles. READ FIRST.
├── .gitignore                                   ← Allows only specific manifest files in output/
├── premium_package_factory/
│   ├── gates/                                   ← All audit/gate scripts (R370S, R370T, etc.)
│   │   ├── r370s_final_engineering_audit.py
│   │   ├── r370t_source_of_truth.py
│   │   └── ... (20+ gate scripts)
│   ├── templates/                               ← Dossier generation templates
│   │   ├── engineering_dossier_artifact_rich.py ← P-01/P-13/P-16 inline templates
│   │   ├── r370b_packages/                      ← P-02 through P-29 package templates
│   │   ├── build_portfolio_v4.py               ← Portfolio builder (defines 15 packages)
│   │   └── ...
│   └── output/
│       └── engineering_dossiers_artifact_rich/  ← .gitignored EXCEPT:
│           ├── FINAL_ENGINEERING_RELEASE_MANIFEST.json  ← COMMITTED (allowed by .gitignore)
│           ├── CROSS_REPOSITORY_RELEASE_INTEGRITY.json  ← COMMITTED
│           ├── DESIGN_INPUT_MIGRATION_REGISTER.json     ← COMMITTED
│           ├── FINAL_RELEASE_OBJECT.json                ← COMMITTED
│           ├── FINAL_RELEASE_ANCHOR_REPORT.json         ← COMMITTED
│           ├── R370U_FINAL_FREEZE_CERTIFICATE.json      ← COMMITTED
│           ├── P-01_ArtifactRichDossier.json            ← .gitignored (source data)
│           ├── P-02_ArtifactRichDossier.json            ← .gitignored
│           └── ... (15 dossier JSONs, all .gitignored)
├── EXTERNAL_CONSULTANT_EVIDENCE/                ← R370W external evidence layer
│   ├── EXTERNAL_CONSULTANT_REPORT_2026-08-27.md ← Frozen consultant report (IMMUTABLE)
│   ├── CONSULTANT_FINDING_REGISTRY.json         ← 31 findings, canonical P-ID bound
│   ├── CONSULTANT_RECONCILIATION_REPORT.json    ← 11 confirmed, 13 partial, 2 contested, 2 unsupported
│   ├── PACKAGE_MUTATION_DECISION_REGISTER.json  ← 8 mutations authorized, 5 not
│   ├── AI_LEARNING_TO_PACKAGE_CERTIFICATE.json  ← 8 end-to-end V1→V2 chains
│   ├── NEGATIVE_LEARNING_KNOWLEDGE_ATOMS.json   ← 4 "AI was wrong" atoms
│   ├── EXTERNAL_AUDIT_LEARNING_REPORT.json      ← 15 packages belief changes
│   ├── ENHANCED_INDEPENDENT_CALCULATIONS.json   ← 6 physics calc reviews
│   ├── FINAL_AI_LOOP_STATE.json                 ← Experiment priorities (4 tiers)
│   └── ... (12 total evidence artifacts)
├── external_evidence/                           ← Published literature references
├── CANONICAL_STATE/                             ← Source registry
└── ... (historical directories: CEREVASC_*, R332/, R354/, etc.)
```

### Portfolio repo: `/home/z/my-project/technology-transfer-portfolio-15/`

**WARNING:** This directory is part of the `/home/z/my-project` git repo (which has NO remote). The portfolio GitHub repo is a SEPARATE entity. To work with it:

```bash
# Clone the portfolio repo to a temp location for git operations
TOKEN=$(cat /tmp/gh_token.txt)
git clone https://prateekm1007:${TOKEN}@github.com/prateekm1007/technology-transfer-portfolio-15.git /tmp/portfolio-work
# Make changes in /tmp/portfolio-work
# Push back
```

**Portfolio repo structure (on GitHub):**

```
technology-transfer-portfolio-15/
├── README.md                                    ← Buyer instructions (explicit hierarchy)
├── PORTFOLIO_INDEX.pdf
├── PORTFOLIO_MANIFEST.json                      ← v2.0, 15 packages, 8 V2 + 7 V1
├── PORTFOLIO_RELEASE_REPORT.pdf
├── FINAL_RELEASE_OBJECT.json                    ← State-based release object (no PENDING)
├── FINAL_RELEASE_ANCHOR_REPORT.json
├── FINAL_DISTRIBUTION_VERIFICATION_CERTIFICATE.json ← State-hash verified
├── FINAL_BUYER_RELEASE_ID.json                  ← Buyer-facing release identity
├── BUYER_DISTRIBUTION_RELEASE_CERTIFICATE.json
├── AI_LEARNING_TO_PACKAGE_CERTIFICATE.json
├── SOURCE_RELEASE_MANIFEST.json                 ← Cryptographic bridge to dev repo
├── DISTRIBUTION_CANONICAL_MANIFEST.json
│
├── DOWNLOAD/                                    ← AUTHORITATIVE buyer distribution layer
│   ├── 01_multisegment_flow_control.zip         ← Complete package (11 files, V2)
│   ├── 02_adaptive_valve.zip                    ← Complete package (9 files, V1)
│   ├── ... (all 15 package ZIPs)
│   ├── 15_mr_flow_sensor.zip
│   ├── 01_multisegment_flow_control/            ← Complete package folder (matches ZIP)
│   ├── 02_adaptive_valve/
│   ├── ... (all 15 package folders)
│   ├── 15_mr_flow_sensor/
│   └── technology-transfer-portfolio-15.zip     ← Master ZIP (15 package ZIPs + index + README + manifest)
│
├── FULL_DOSSIERS/                               ← Source for DOWNLOAD/ (identical content)
│   ├── 01_multisegment_flow_control/
│   │   ├── 00_PACKAGE_README.pdf
│   │   ├── 01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf
│   │   ├── 02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf  ← THE FULL DOSSIER
│   │   ├── 03_BUYER_DECISION_CARD.pdf
│   │   ├── 04_EVIDENCE_SUMMARY.pdf
│   │   ├── 05_TRANSFER_MANIFEST.pdf
│   │   ├── PACKAGE_MANIFEST.json                ← v2.0 for V2 packages
│   │   ├── ENGINEERING_TRACEABILITY.json
│   │   ├── MATURITY_BASIS.json
│   │   ├── V2_MUTATION_ADDENDUM.json            ← V2 packages only
│   │   └── PACKAGE_MUTATION_CERTIFICATE_P-01_V2.json  ← V2 packages only
│   └── ... (all 15)
│
├── BUYER_OUTREACH/                              ← Individual buyer cards (01-15)
│   ├── 01_BUYER_CARD.pdf
│   └── ... (15 cards)
│
├── INTERNAL_QA/                                 ← Internal QA artifacts (not for buyers)
│   ├── FINAL_ENGINEERING_DOSSIER_RELEASE_CERTIFICATE.json
│   ├── CROSS_REPOSITORY_RELEASE_INTEGRITY.json
│   ├── DESIGN_INPUT_MIGRATION_REGISTER.json
│   ├── R370R_ENGINEERING_CONSISTENCY.json
│   └── PORTFOLIO_RELEASE_CERTIFICATE.json
│
└── RELEASE/
    └── BUYER_DISTRIBUTION_RELEASE_CERTIFICATE.json
```

---

## 3. THE 15 TECHNOLOGIES

| # | Package ID | Short Name | Technology | Version | Key Notes |
|---|-----------|------------|------------|---------|-----------|
| 01 | P-01 | multisegment_flow_control | Multi-Segment Flow Control with Bayesian Occlusion Prediction | V2 | Obstruction rate corrected; 16% error context added |
| 02 | P-02 | adaptive_valve | Adaptive Valve Profile for Postural ICP Regulation | V1 | Competitive gap noted (ASDs) |
| 03 | P-04 | catalytic_clearance | Catalytic Contact Time Lock for Amyloid Beta Clearance | V1 | Combination product; repositioned |
| 04 | P-07 | drainage_floor | Passive Drainage Priority Safety Floor | V2 | Obstruction rate corrected |
| 05 | P-11 | phage_antibiofilm | Phage Anti-Biofilm Coating for Shunt Infection Prevention | V1 | Combination product; repositioned |
| 06 | P-13 | failure_predictor | ML-based Shunt Failure Predictor (was "Neuromorphic") | V2 | Terminology corrected; repositioned as long-term research |
| 07 | P-15-R1 | self_powered_sensing | Self-Powered Sensing via Piezoelectric Energy Harvesting | V2 | HIGH FEASIBILITY RISK added |
| 08 | P-16 | nir_photovoltaic | NIR Photovoltaic Power Delivery | V1 | Consultant was WRONG about 500mW — dossier already says 500µW |
| 09 | P-21-R1 | uwb_localization | UWB Catheter Position Mapping with SAR-Bounded Accuracy | V2 | HIGH FEASIBILITY RISK added |
| 10 | P-22-R1 | catheter_navigation | Autonomous Catheter Navigation | V1 | Competitive landscape absent |
| 11 | P-24 | gravity_damper | Gravity Compensation Hydraulic Damper | V1 | Clear predicate (ASD) |
| 12 | P-26 | osmotic_valve | Osmotic Pressure Regulating Drainage Valve | V1 | Membrane fouling concern |
| 13 | P-27-R1 | pressure_sensor | Self-Referencing Piezoresistive Pressure Sensor | V2 | Regulatory terminology corrected |
| 14 | P-28 | acoustic_detection | Acoustic Obstruction Detection | V2 | HIGH FEASIBILITY RISK added |
| 15 | P-29 | mr_flow_sensor | MR Flow Quantification Sensor | V2 | HIGH FEASIBILITY RISK added |

---

## 4. CURRENT HONEST STATE

```
DOCUMENT_COMPLETE_FOR_STAGE:   15/15
ENGINEERING_EVALUABLE:         15/15
TRANSFER_EVALUABLE:            15/15
EXTERNALLY_VALIDATED:           0/15
PHYSICALLY_VALIDATED:           0/15
TRANSFER_READY:                 0/15

EXTERNAL_CONSULTANT_ASSESSMENT = INGESTED
AI_LEARNING = VERIFIED
PACKAGE_V2 = GENERATED WHERE WARRANTED (8 V2, 7 V1)

REAL_BUYER = 0
REAL_EXPERIMENT = 0
REAL_DATA = 0
REAL_LOOP_VERIFIED = FALSE
```

### What "frozen" means

- **Portfolio repo (`technology-transfer-portfolio-15`)** is FROZEN at commit `2e96b27`. The `FINAL_DISTRIBUTION_VERIFICATION_CERTIFICATE.json` uses a **state hash** (not a commit SHA) to avoid the chicken-and-egg problem. The certificate is verified by recomputing the state hash from actual files at HEAD.
- **Dev repo (`discovery-evidence-fabric`)** is at `bf97cdf` but is NOT frozen — it can receive new commits (e.g., for V3 work after real buyer feedback).

---

## 5. WHAT'S DONE (complete list)

### Engineering infrastructure
- ✅ Constitution v1.8.0 (38 articles including Article XXXVIII — The Reality Boundary)
- ✅ 15 artifact-rich engineering dossiers (package-specific, not generic)
- ✅ 161 design inputs across 15 packages (all classified)
- ✅ 66 governing equations (all validated)
- ✅ Engineering traceability (explicit ID-based, not keyword-inferred)
- ✅ 0 material engineering value truncations

### Buyer distribution
- ✅ 15 complete buyer packages (6 PDFs + 3 JSONs + V2 artifacts)
- ✅ 15 individual ZIPs (each contains complete package)
- ✅ 1 master ZIP (contains 15 package ZIPs + index + README + manifest)
- ✅ ZIP-folder equivalence verified (15/15, all hashes match)
- ✅ README with explicit buyer hierarchy

### External consultant evidence
- ✅ Consultant report frozen (SHA-256 recorded)
- ✅ 31 findings registered (canonical P-ID bound)
- ✅ Numeric assertions audited (CONFIRMED/PARTIALLY_CONFIRMED/CONTESTED/UNSUPPORTED)
- ✅ Regulatory reconciliation against FDA sources (JXG Class II, GWM Class II, PMOA)
- ✅ Independent physics calculations reviewed (P-15-R1, P-16, P-21-R1, P-28, P-29)
- ✅ 4 negative learning Knowledge Atoms (AI acknowledged errors)

### V1 → V2 mutation
- ✅ 8 packages mutated to V2 (P-01, P-07, P-13, P-27-R1, P-15-R1, P-21-R1, P-28, P-29)
- ✅ 7 packages correctly remain V1 (P-02, P-04, P-11, P-16, P-22-R1, P-24, P-26)
- ✅ Mutation certificates for all 8 V2 packages
- ✅ End-to-end chains: consultant finding → reconciliation → belief update → V1 → V2

### Release integrity
- ✅ FINAL_RELEASE_OBJECT (state-based, no PENDING)
- ✅ FINAL_DISTRIBUTION_VERIFICATION_CERTIFICATE (state hash verified)
- ✅ FINAL_BUYER_RELEASE_ID (buyer-facing release identity)
- ✅ Cross-repository cryptographic bridge (SOURCE_RELEASE_MANIFEST)
- ✅ Fresh-clone verification: 15/15 PASS, 0 drift, 0 post-freeze commits

---

## 6. WHAT'S LEFT (the real loop)

The CEO has explicitly stated: **STOP CODING.** The next phase is no longer repository engineering. It is:

```
V2 BUYER PACKAGES (DONE)
    ↓
REAL BUYER (send packages to actual technical decision-makers)
    ↓
OBJECTION (record their actual technical objections)
    ↓
ENGINEERING ENGAGEMENT (buyer commissions a bench test)
    ↓
REAL EXPERIMENT (physical prototype tested in lab)
    ↓
REAL DATA (experimental results — not simulation)
    ↓
AI UPDATE (belief update from real experimental evidence)
    ↓
DOSSIER V3 (packages revised based on real data)
```

### Experiment priorities (from external consultant reconciliation)

**Priority 1 (immediate bench tests, $5K each):**
- P-07 (Passive Drainage Floor) — multi-lumen extrusion + differential obstruction test
- P-16 (NIR Photovoltaic) — NIR source + PV cell + tissue phantom (resolve unit error first)
- P-24 (Gravity Damper) — damper element prototypes + c_h vs flow rate

**Priority 2 (after precondition):**
- P-15-R1 — measure in-vivo catheter-wall strain (precondition: source strain data)
- P-21-R1 — complete link budget at tissue depths >3cm
- P-28 — frequency-dependent phantom acoustic test
- P-29 — SNR feasibility test at 0.5T and 1.0T (expect negative)

**Priority 3 (reposition):**
- P-13 — remove from buyer-facing portfolio (data-conditional)
- P-04 — reposition as research collaboration
- P-11 — reposition for phage therapy company

**Priority 4 (requires analysis):**
- P-01, P-02, P-22-R1, P-26, P-27-R1 — competitive analysis, corrections

---

## 7. FILES THE NEW CHAT MUST READ BEFORE CODING

**If the new chat touches ANY code, it MUST read these files first:**

### Mandatory reads (in order)

1. **`/home/z/my-project/discovery-evidence-fabric/EPISTEMIC_CONSTITUTION.md`**
   - v1.8.0, 38 articles
   - Article I: evidence precedes assertion
   - Article XXV: unknown stays unknown
   - Article XXVII: threshold provenance
   - Article XXVIII: precedent ≠ validation
   - Article XXXVIII: The Reality Boundary (AI cannot create PHYSICAL_OBSERVATION)

2. **`/home/z/my-project/worklog.md`**
   - 5400+ lines, complete history from R370 through R370Z
   - Read the last 200 lines for the most recent state

3. **`/home/z/my-project/technology-transfer-portfolio-15/PORTFOLIO_MANIFEST.json`**
   - 15 packages, V2/V1 state, hashes, next actions, kill conditions

4. **`/home/z/my-project/technology-transfer-portfolio-15/FINAL_DISTRIBUTION_VERIFICATION_CERTIFICATE.json`**
   - State hash, package verification results, buyer distribution rule

5. **`/home/z/my-project/discovery-evidence-fabric/EXTERNAL_CONSULTANT_EVIDENCE/CONSULTANT_RECONCILIATION_REPORT.json`**
   - 31 findings: 11 confirmed, 13 partial, 2 contested, 2 unsupported

6. **`/home/z/my-project/discovery-evidence-fabric/EXTERNAL_CONSULTANT_EVIDENCE/PACKAGE_MUTATION_DECISION_REGISTER.json`**
   - 8 mutations authorized, 5 not — the decision basis for each

### Read if touching specific packages

7. **`/home/z/my-project/discovery-evidence-fabric/premium_package_factory/templates/build_portfolio_v4.py`**
   - Lines 47-61: defines all 15 packages with `kill_if` conditions, buyer types, mechanisms

8. **`/home/z/my-project/discovery-evidence-fabric/premium_package_factory/templates/engineering_dossier_artifact_rich.py`**
   - P-01, P-13, P-16 inline templates (P-13 has 9 DIs including DI-008 and DI-009 restored in R370U)

9. **`/home/z/my-project/discovery-evidence-fabric/premium_package_factory/gates/r370s_final_engineering_audit.py`**
   - The engineering audit script (di_value[:100] was removed in R370U)

### Read if touching release integrity

10. **`/home/z/my-project/scripts/r370z_final_cleanroom_verification.py`**
    - The final verification script — run this to confirm the system is still frozen

11. **`/home/z/my-project/scripts/r370y_terminal_freeze.py`**
    - The terminal freeze script — explains the state-hash approach

---

## 8. CRITICAL RULES — DO NOT VIOLATE

### Rule 1: Everything must be autocommands

**No manual git operations.** All git operations must be scripted:

```python
import subprocess
result = subprocess.run(["git", "add", "-A"], cwd=repo_path, check=True)
result = subprocess.run(["git", "commit", "-m", "message"], cwd=repo_path, check=True)
result = subprocess.run(["git", "push", "origin", "main"], cwd=repo_path, check=True)
```

**No manual file copies.** All file operations must be scripted in Python.

**No manual PDF editing.** PDFs are generated from source data via scripts.

### Rule 2: Do not modify frozen release

The portfolio repo at `2e96b27` is FROZEN. Do NOT:
- Add commits to `technology-transfer-portfolio-15` unless creating V3 after real experimental data
- Modify the 15 buyer packages without a new mutation certificate
- Change `FINAL_DISTRIBUTION_VERIFICATION_CERTIFICATE.json` without recomputing the state hash

### Rule 3: Do not create another audit framework

The CEO has explicitly said: **No R370Z. No more self-generated audits. No more packaging layers.** The system is done. The next evidence must come from real buyers/engineers/experiments.

### Rule 4: Preserve the reality boundary

Per Article XXXVIII:
- AI can propose, compute, interpret
- AI CANNOT create PHYSICAL_OBSERVATION evidence
- `REAL_LOOP_VERIFIED` remains FALSE until a real experiment produces real data
- An external consultant is "real human evidence" but NOT "physical experimental evidence"

### Rule 5: Do not silently fix external claims

If a consultant says something wrong (like the P-16 "500 mW" claim), do NOT:
- Silently correct the consultant
- Silently mutate the dossier to match the consultant
- Auto-replace one number with another

Instead:
- Record the consultant finding as CONTESTED
- Record the AI reconciliation separately
- Preserve the original finding immutably

### Rule 6: The portfolio repo is NOT the local directory

`/home/z/my-project/technology-transfer-portfolio-15/` is part of the root `/home/z/my-project` git repo (which has no remote). The actual GitHub portfolio repo must be cloned separately:

```bash
TOKEN=$(cat /tmp/gh_token.txt)
git clone https://prateekm1007:${TOKEN}@github.com/prateekm1007/technology-transfer-portfolio-15.git /tmp/portfolio-work
```

### Rule 7: Use the state-hash pattern for certificates

The chicken-and-egg problem (a certificate cannot reference its own commit SHA) was solved by using a **state hash** instead of a commit SHA. The certificate records:
- `portfolio_state_hash` = SHA-256 of all package file hashes + master ZIP hash
- `self_hash` = SHA-256 of the certificate (excluding self_hash field)

Verification: recompute state hash from actual files at HEAD and confirm it matches.

---

## 9. SCRIPT INVENTORY

All R370 scripts are in `/home/z/my-project/scripts/`:

| Script | Purpose | Status |
|--------|---------|--------|
| `r370u_cleanroom_verification.py` | Fresh-clone verification of cross-repo integrity | ✅ Complete |
| `r370u_final_release_reconciliation.py` | U1-U10: manifest creation, migration register | ✅ Complete |
| `r370u_scan_truncation.py` | U6: lossy transformation scanner (v1) | ✅ Complete |
| `r370u_scan_truncation_v2.py` | U6: refined scanner (distinguishes MATERIAL from display) | ✅ Complete |
| `r370v_final_release_anchor.py` | V1-V6: HEAD-to-release anchor verification | ✅ Complete |
| `r370w_external_consultant_reconciliation.py` | W1-W12: consultant evidence ingestion | ✅ Complete |
| `r370w_final_release_object.py` | Final release object builder | ✅ Complete |
| `r370w_final_reproducibility_test.py` | Fresh-clone reproducibility test | ✅ Complete |
| `r370w_learning_loop.py` | Enhanced learning loop with negative atoms | ✅ Complete |
| `r370w_v2_mutation.py` | V1→V2 mutation of buyer dossiers | ✅ Complete |
| `r370x_buyer_distribution_fix.py` | Download folder/ZIP equivalence fix | ✅ Complete |
| `r370x_final_distribution_gate.py` | Final distribution verification gate | ✅ Complete |
| `r370x_final_v2_release.py` | X1-X10: final V2 release anchor | ✅ Complete |
| `r370y_terminal_freeze.py` | Y1-Y6: terminal-head freeze (state hash) | ✅ Complete |
| `r370z_final_cleanroom_verification.py` | FINAL verification from fresh GitHub clone | ✅ Complete |

---

## 10. HOW TO VERIFY THE SYSTEM IS STILL FROZEN

Run this single command to confirm the system hasn't drifted:

```bash
cd /home/z/my-project && python3 scripts/r370z_final_cleanroom_verification.py
```

Expected output:
```
FINAL BUYER RELEASE VERIFIED
15/15 COMPLETE
15/15 DOWNLOADABLE
15/15 ZIP-VALID
15/15 HASH-VALID
0 DRIFT
0 POST-FREEZE COMMITS
```

If this fails, something has changed and must be investigated.

---

## 11. WHAT TO DO IF A REAL BUYER PROVIDES FEEDBACK

This is the expected next step. When a real buyer/engineer provides feedback:

1. **Freeze the feedback** as `EXTERNAL_BUYER_FEEDBACK_<date>.md` with SHA-256
2. **Register findings** in a `BUYER_FINDING_REGISTRY.json` (similar to consultant registry)
3. **Reconcile** each finding (CONFIRMED/PARTIALLY_CONFIRMED/CONTESTED/UNSUPPORTED)
4. **Generate belief updates** and **knowledge atoms**
5. **Make mutation decisions** (only CONFIRMED or PARTIALLY_CONFIRMED + MATERIAL)
6. **Create V3 packages** with mutation certificates
7. **Update the portfolio repo** (new commit, new state hash)
8. **Record the learning chain**: buyer finding → reconciliation → belief update → V2 → V3

**When a real experiment produces real data:**
1. Record as `PHYSICAL_OBSERVATION` in the observation ledger (Article XXXVIII)
2. This is the first event that can set `REAL_LOOP_VERIFIED = TRUE`
3. Update dossiers to V3 based on experimental evidence
4. The AI has now completed the end-to-end reality loop

---

## 12. ANTI-ENTROPY PRINCIPLES

To prevent entropy in the file structure:

1. **Never create duplicate directories.** `FULL_DOSSIERS/` and `DOWNLOAD/` folders contain identical content — `DOWNLOAD/` is the authoritative buyer layer, `FULL_DOSSIERS/` is the source.

2. **Never commit .gitignored files.** The `.gitignore` in the dev repo allows ONLY these files in `output/engineering_dossiers_artifact_rich/`:
   - `FINAL_ENGINEERING_RELEASE_MANIFEST.json`
   - `CROSS_REPOSITORY_RELEASE_INTEGRITY.json`
   - `DESIGN_INPUT_MIGRATION_REGISTER.json`
   - `R370U_FINAL_FREEZE_CERTIFICATE.json`
   - `FINAL_RELEASE_ANCHOR_REPORT.json`
   - `FINAL_RELEASE_OBJECT.json`

3. **Never modify the constitution without formal amendment.** The constitution is at v1.8.0 with 38 articles. Any change requires a new article and version bump.

4. **Never create a new audit round without CEO authorization.** The CEO has said STOP. R370Z was the final verification.

5. **Always use canonical P-IDs.** Package 01 = P-01, Package 03 = P-04 (NOT P-03). The mapping is:
   - 01→P-01, 02→P-02, 03→P-04, 04→P-07, 05→P-11, 06→P-13, 07→P-15-R1, 08→P-16, 09→P-21-R1, 10→P-22-R1, 11→P-24, 12→P-26, 13→P-27-R1, 14→P-28, 15→P-29

6. **Always preserve original findings immutably.** The consultant report is frozen. AI reconciliation is separate. Never modify the original.

---

## 13. QUICK START FOR THE NEW CHAT

If the user asks you to continue work:

1. **First:** Read this handoff document completely
2. **Second:** Read `/home/z/my-project/worklog.md` (last 200 lines)
3. **Third:** Run `python3 /home/z/my-project/scripts/r370z_final_cleanroom_verification.py` to confirm the system is still frozen
4. **Fourth:** Ask the user what specific task they want — do NOT start coding without explicit direction

If the user asks about:
- **Buyer distribution** → Point them to `DOWNLOAD/NN_folder_name.zip`
- **Engineering content** → Point them to `02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf` inside the ZIP
- **External consultant** → Point them to `EXTERNAL_CONSULTANT_EVIDENCE/`
- **V2 mutations** → Point them to `PACKAGE_MUTATION_DECISION_REGISTER.json`
- **Release integrity** → Point them to `FINAL_DISTRIBUTION_VERIFICATION_CERTIFICATE.json`
- **Real-world loop** → This is the next phase: buyer → experiment → data → V3

**DO NOT** create new audit frameworks, new maturity scores, or new self-certification schemes. The system is done. The next evidence must come from reality.

---

## 14. CONTACT POINTS

- **Dev repo:** `https://github.com/prateekm1007/discovery-evidence-fabric` (HEAD: `bf97cdf`)
- **Portfolio repo:** `https://github.com/prateekm1007/technology-transfer-portfolio-15` (HEAD: `2e96b27`, FROZEN)
- **Worklog:** `/home/z/my-project/worklog.md` (5400+ lines, complete history)
- **Constitution:** `/home/z/my-project/discovery-evidence-fabric/EPISTEMIC_CONSTITUTION.md` (v1.8.0, 38 articles)
- **Final verification script:** `/home/z/my-project/scripts/r370z_final_cleanroom_verification.py`

---

*This handoff document is the single source of truth for the new chat. Read it completely before any action.*
