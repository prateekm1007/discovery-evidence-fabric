# Round 272 Audit — Deep Collision on 5 INVEST Candidates: ALL DOWNGRADED

**Task ID:** R272-DEEP-COLLISION-5-INVEST
**Agent:** main (CTO, Super Z)
**Date:** 2026-08-24

---

## 1. Reclassification: INVEST → INVEST-PENDING-DEEP-COLLISION

INVEST means "spend the next evidence budget attacking this," NOT "this is probably patentable." The CEO found prior art for ALL 5 INVEST candidates. Each needs mechanism-specific deep collision.

---

## 2. Deep Collision Results: ALL 5 Downgraded or Blocked

### #1: NC-C (Predictive Occlusion-Isolation Controller) → WATCH

**CEO prior art:** US11291809B2 (powered obstruction-clearing shunt system)

**Mechanism-specific claim:** Dual safety invariant (global ICP preservation AND surviving-path overload prevention) for distributed CSF drainage.

**Gate P verdict:** WEAK — the control law is standard fault-tolerant control with dual safety invariants. Functionally equivalent to fault-tolerant flight control (mission + structural protection), smart water grids (demand + pipe pressure limits), nuclear safety (power + temperature limits).

**What survives:** The CSF-specific application. But the control law is standard. §103 risk: HIGH (motivated combination of known predictive maintenance + known flow redistribution).

### #2: SC-D (Bacteriophage Defense) → WATCH

**CEO prior art:** NIH tech transfer tab-3312 (phage tethered to hydrogel-coated catheters for shunts), EP4132552A2 (phage treatment of implant infections)

**What survives:** The specific closed-loop (biosensor → species selection → release → self-amplification) is not found as a single reference. BUT: each element individually known. The control law (sense pathogen → select treatment → release → confirm) is standard closed-loop therapeutic control (same architecture as artificial pancreas). Novelty is the PAYLOAD (phage), not the architecture.

### #3: SC-H (Enzymatic Clearance) → WATCH

**CEO prior art:** US20090131850A1 (CSF protein filtration/degradation), US11529443 (Aβ/tau molecular-recognition membrane in shunt)

**What survives:** Only the dynamic contact-time optimization (flow modulation for catalytic efficiency while maintaining drainage). BUT: this is standard chemical reaction engineering (residence time optimization). The dual constraint (clearance + drainage) is standard multi-objective control.

### #4: SC-F (Molecular ICP Signaling) → BLOCKED

**Cannot assess** — molecule is UNSPECIFIED. This is the SC-05 lesson: a concept without a specific mechanism cannot survive deep collision. Needs 8 specifications (molecule, release kinetics, concentration, transport, sensor, specificity, background, clearance) before any collision search is meaningful.

### #5: SC-A (Phase-Change Valve) → WATCH (downgraded from #1)

**CEO prior art:** PubMed 38145958 (2024 review — Ga-based liquid metals with body-temperature-tunable phase transitions for biomedical actuators/sensors/implants), US8231563B2 (electrokinetic actuation for CSF flow regulation)

**What survives:** Only the protein-regulated phase-transition shift (CSF protein → apoprotein → phase transition → hydraulic resistance). BUT: this element is UNSPECIFIED (which apoprotein? which conformational change? what sensitivity?). Liquid metal phase transitions are established biomedical technology. The specific protein-Ga-In interaction is not found but needs specification.

---

## 3. The Pattern

**ALL 5 INVEST candidates were downgraded or blocked.** The CEO found prior art the engine missed for EVERY candidate. The M4=NOT FOUND assessments were based on training knowledge, not live search. The CEO's live searches found prior art for:

| Candidate | CEO-found prior art | Engine missed it because |
|---|---|---|
| NC-C | US11291809B2 (powered shunt obstruction clearing) | Searched "predictive occlusion" not "powered shunt obstruction" |
| SC-D | NIH tab-3312 (phage on catheters), EP4132552A2 | Searched "phage implant" not "phage catheter hydrogel" |
| SC-H | US20090131850A1 (CSF protein filtration), US11529443 (Aβ/tau shunt) | Searched "enzymatic clearance" not "CSF protein removal apparatus" |
| SC-F | None (but molecule unspecified) | Cannot search without specific molecule |
| SC-A | PubMed 38145958 (liquid metal biomedical), US8231563B2 (electrokinetic CSF) | Searched "phase-change valve" not "liquid metal biomedical actuator" |

**The functional-equivalence search is still not exhaustive enough.** Each CEO-found source used different terminology than the engine searched. The engine's 15-term expansion was insufficient.

---

## 4. Updated Portfolio

| Status | Count | Candidates |
|---|---|---|
| INVEST | **0** | (all downgraded) |
| WATCH (need unexpected-effect proof) | 4 | NC-C, SC-D, SC-H, SC-A |
| BLOCKED (need mechanism specification) | 1 | SC-F |
| WATCH (from R271) | 9 | NC-B, NC-D, NC-E, SC-B, SC-C, SC-E, SC-G, SC-I, SC-J |
| KILL | 2 | NC-A, NC-F |
| Cemetery | 23 | (including CE-023 SC-05) |
| **Level 2 confirmed** | **0** | |
| **Sellable** | **0** | |
| **Transactions** | **$0** | |

---

## 5. What Each WATCH Candidate Needs to Survive

| Candidate | What's needed | Why |
|---|---|---|
| NC-C | Unexpected CSF-specific occlusion prediction result (non-greedy redistribution, counterintuitive optimal strategy) | Control law is standard; needs unexpected effect |
| SC-D | Unexpected pre-clinical benefit (>100x dose reduction vs antibiotics, microbiome preservation) | Architecture is standard closed-loop; needs unexpected payload effect |
| SC-H | Non-linear clearance improvement (10x contact time → 100x clearance) or new clinical indication | Optimization is standard; needs unexpected kinetic result |
| SC-A | Specific protein + Ga-In composition + unexpected hydraulic response (>10°C shift per protein unit) | Material class is known; needs specific interaction + unexpected effect |
| SC-F | 8 molecule specifications | Cannot assess without specific molecule |

---

## 6. The Hard Truth

After 272 rounds of discovery, collision, validation, and killing:

- **0 confirmed Level 2 candidates**
- **0 sellable technology assets**
- **0 transactions**
- **23 cemetery entries**
- **~14 candidates at WATCH/BLOCKED**
- **5 candidates that passed initial screening but failed deep collision**

The discovery engine is architecturally sound (governance, collision, synergy, gates) but has not yet produced a single invention that survives adversarial attack at the mechanism level. Every candidate that sounded novel at the concept level was threatened at the element-decomposition level.

The frontier remains: **a specific causal mechanism where two known elements interact to produce a quantitatively unexpected technical effect that no existing system achieves under comparable constraints, verified by live patent search and external review.**

---

## 7. Artifacts Produced

| Artifact | Path | Size |
|---|---|---|
| Deep collision 5 INVEST candidates | `CANONICAL_STATE/R272_DEEP_COLLISION_5_INVEST_CANDIDATES.json` | 28,099 bytes |
| This Audit | `CANONICAL_STATE/ROUND_272_AUDIT.md` | (this file) |
| Script | `scripts/r272_deep_collision_5_invest.py` | (in /home/z/my-project/scripts/) |
