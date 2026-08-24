# Round 256 Audit — NC-05 Killed + Optimizer Repaired + All NC Collision + New-Hunt Redesigned

**Task ID:** R256-NC05-KILL-OPTIMIZER-COLLISION-NEWHUNT
**Agent:** main (CTO, Super Z)
**Date:** 2026-08-24

---

## 1. P0 — NC-05 Killed: NOVELTY_THREATENED

**5 prior-art patents directly cover the proposed mechanism.** The claim "No tool uses telemetry to predict failure" is NOT supportable.

| Patent | What it covers |
|---|---|
| US 12,386,345 (Siemens, Aug 2025) | Predicting failure of MRI modules including flexible coils, using sensors, remote evaluation, prediction models |
| US 2024/0241197 A1 | MRI coil with embedded diagnostic module, remote/cloud monitoring, AI tracking, predicting hard/soft failure |
| US 2025/0199104 A1 (June 2025) | MRI coil monitoring: resonant frequency, ring-down, coupling, temperature. Cloud aggregation + AI prediction |
| US 2026/0122134 A1 (Siemens, Apr 2026) | Cloud-enabled MRI abnormality prediction, including coils, telemetry trends, predictive warnings |
| US 2024/0103112 A1 | ML-based MRI coil fault detection, failure type/location, real-time automated detection |

**Verdict: NOVELTY_THREATENED.** No simulation. The mechanism is fully covered by prior art.

### Lesson

NC-05 had positive EV (+0.0047) but zero novelty. The optimizer must be `EV × novelty_confidence`, not raw EV. A cheap-to-test candidate with zero novelty has **negative effective value**.

---

## 2. P1 — Optimizer Repaired: Novelty-First Pipeline

### The fix

**Pipeline order: NOVELTY FIRST → COMMERCIAL EV SECOND**

A candidate cannot reach INVEST merely because EV > 0. Minimum INVEST condition:

> **Novelty confidence ≥ Level 2 + positive evidence-acquisition EV**

### States

| State | Condition | Action |
|---|---|---|
| INVEST | Novelty ≥ Level 2 AND EV > 0 | Proceed with §103 + killer experiment |
| WATCH | Novelty ≥ Level 1 AND EV ≥ -0.05 | Monitor; re-evaluate when new info arrives |
| NOVELTY_THREATENED | Prior art directly covers mechanism | Do NOT simulate. Preserve for resurrection only if genuinely different mechanism found |
| RESET | Novelty < Level 1 OR EV < -0.05 | Return to discovery queue |

### Novelty levels

| Level | Definition |
|---|---|
| 0 | Prior art directly covers the full mechanism → NOVELTY_THREATENED |
| 1 | Prior art covers components but not the specific combination → MARGINAL |
| 2 | Prior art covers adjacent domains but NOT the specific mechanism in this domain → SURVIVES |
| 3 | No prior art found after deep search → STRONG |

### Effective value formula

`effective_EV = raw_EV × novelty_confidence`

Example: NC-05 had raw_EV = +0.0047, novelty_confidence = 0.0 (5 patents). effective_EV = 0.0. NOT INVEST.

---

## 3. P2 — Collision Attack on NC-01..NC-04

All 4 remaining NC candidates collision-searched. **NONE survive to INVEST.**

| Candidate | Mechanism | Prior art | Novelty | Verdict |
|---|---|---|---|---|
| NC-01 | Sterilization dose optimization | ISO 11137 itself provides the method. Sterigenics/Steris use ISO 11137 software. Monte Carlo dose modeling (Geant4). | Level 1 (MARGINAL) | RESET |
| NC-02 | Implant fatigue from tolerances | Tolerance-based FEA (Abaqus, ANSYS, nCode). Monte Carlo tolerance propagation (SmartUQ, Isight). Implant fatigue (ASTM F1717, ISO 14801). | Level 1 (MARGINAL) | RESET |
| NC-03 | Bayesian futility boundaries | FDA adaptive design guidance (2015). Commercial tools (East/Cytel, PASS). Decades of literature. | Level 0 (THREATENED) | NOVELTY_THREATENED |
| NC-04 | IVD cross-reactivity prediction | Molecular similarity (RDKit, Open Babel, Schrödinger). Standard computational chemistry. | Level 1 (MARGINAL) | RESET |

### The pattern

The entire NC-01..NC-05 batch failed novelty collision. The R255 new-hunt engine generated candidates by asking "what domain has pain?" then proposing "apply AI to X." This produces prior-art-threatened candidates because "apply AI to X" is almost always already covered.

---

## 4. P3 — New-Hunt Redesigned: Information Bottleneck

### The new principle

Search for candidates using the structure:

> **hidden variable → inability to observe → existing expensive workaround → new measurement/inference mechanism → measurable technical effect → buyer economics**

This produces candidates with **genuine technical novelty** (new measurement capability), not commercial packaging of existing technology.

### 3 candidate structures generated (NOT yet candidates — must be collision-searched first)

#### Structure 1: Implant Micromotion Measurement
- **Hidden variable:** In-vivo implant micromotion (how much an implant moves under physiological load, non-invasively)
- **Inability to observe:** Current methods require X-ray (radiation, episodic) or CT (expensive). No continuous, non-invasive measurement.
- **Expensive workaround:** Surgeons use static imaging + clinical symptoms. Loosening detected late → revision surgery ($50K-$150K).
- **New mechanism:** Implant-integrated impedance sensor (implant itself becomes the sensor).
- **Technical effect:** Continuous, non-invasive micromotion with sub-micron resolution.
- **Novelty question:** Is implant-integrated impedance-based micromotion novel? (Related to CE-001 but applied to orthopedic implants.)

#### Structure 2: Tissue Drug Concentration
- **Hidden variable:** Real-time drug concentration at target tissue (not blood)
- **Inability to observe:** Blood draws measure systemic, not tissue. Biopsies are invasive/episodic.
- **Expensive workaround:** Dose adjustment based on blood levels + clinical response. Suboptimal dosing → toxicity or failure.
- **New mechanism:** Implantable microdialysis probe with continuous wireless measurement.
- **Technical effect:** Real-time tissue drug concentration curve.
- **Novelty question:** Is continuous tissue-level drug measurement via implantable microdialysis novel?

#### Structure 3: Vessel Wall Shear Stress
- **Hidden variable:** Local wall shear stress at implant-tissue interface
- **Inability to observe:** CFD estimates bulk flow, not local interface stress. Measurement requires invasive techniques.
- **Expensive workaround:** Implant design uses safety margins. Thrombosis risk assessed post-hoc.
- **New mechanism:** Implant-surface-integrated pressure sensors measuring local shear directly.
- **Technical effect:** Direct measurement of local hemodynamic stress at interface.
- **Novelty question:** Is implant-surface-integrated wall shear stress measurement novel?

### Key difference from R255

R255 asked "what domain has pain?" → proposed "apply AI to X" → got prior-art-threatened candidates.

R256 asks "what variable is expensive to observe?" → proposes "new measurement mechanism" → produces candidates with genuine technical novelty.

### Next steps

These 3 structures are NOT yet candidates. Each must be:
1. Collision-searched for prior art (novelty-first pipeline)
2. §103 attacked
3. Assessed for novelty level BEFORE any EV calculation or simulation

---

## 5. Updated Honest Scoreboard

| Metric | Value |
|---|---|
| Constitution | v1.5.0, 35 articles |
| Cemetery | 21 entries (CE-019 MSVED, CE-021 CC-08) |
| World-Class | 0/5 |
| Commercial tool candidate | 1 (CC-04, not sellable) |
| INVEST candidates | **0** (NC-05 downgraded, all others RESET/THREATENED) |
| NOVELTY_THREATENED | 3 (NC-05, NC-03) |
| RESET | 10 (CC-02, CC-03, CC-05, CC-06, CC-07, CC-09, CC-10, NC-01, NC-02, NC-04) |
| New candidate structures | 3 (information-bottleneck, not yet candidates) |
| Sellable | 0 |
| Transactions | $0 |

---

## 6. Key Insight

The entire NC-01..NC-05 batch failed novelty collision. This confirms the CEO's diagnosis: the new-hunt engine was backwards (commercial EV before novelty). The fix is the information-bottleneck structure: start from "what variable is expensive to observe?" not "what domain has pain?"

The 3 new candidate structures are promising because they propose **new measurement capabilities** (things that cannot currently be measured), not **automation of existing measurements** (which is almost always prior-art threatened).

### The frontier

> Find a technical capability that a buyer needs, that is materially difficult to build internally, that produces a measurable economic effect, and whose accumulated validation/know-how becomes increasingly difficult to reproduce.

The information-bottleneck structure finds this by identifying **hidden variables that buyers currently operate without** — the most defensible starting point for a genuinely novel mechanism.

---

## 7. Artifacts Produced (ALL VERIFIED ON DISK)

| Artifact | Path | Size |
|---|---|---|
| NC-05 kill + optimizer + collision + new-hunt | `CANONICAL_STATE/R256_NC05_KILL_OPTIMIZER_COLLISION_NEWHUNT.json` | 19,580 bytes |
| This Audit | `CANONICAL_STATE/ROUND_256_AUDIT.md` | (this file) |
| Script | `scripts/r256_nc05_kill_optimizer_collision_newhunt.py` | (in /home/z/my-project/scripts/) |
