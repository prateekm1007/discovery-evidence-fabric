# Prior-Art Landscape — P-01

**Candidate:** P-01 — Predictive Occlusion-Isolation Controller
**Authority:** Article XXXVI §2 C16, C18
**Status:** PARTIAL — based on R274/R277 prior-art searches; full provenance in source artifacts

---

## 1. Closest published art

### Reference 1: Multi-segment / multi-catheter CSF drainage
- **Citation:** CN103491862A (Chinese patent, multi-point CSF drainage catheter)
- **What it teaches:** A multi-lumen catheter with multiple drainage points along its length, intended to provide redundancy against localized obstruction.
- **Why it is close:** Same physical architecture concept (multiple drainage paths). However, CN103491862A is a passive multi-lumen design with no per-segment flow control or predictive algorithm.
- **Source provenance:**
  - Search query: "multi-segment CSF shunt drainage catheter"
  - Database: Google Patents
  - Date of search: R277 (2026-08-25)
  - Result rank: top 5

### Reference 2: Active shunt control with pressure feedback
- **Citation:** US20180000421A1 (smart shunt with telemetry and pressure-based control)
- **What it teaches:** An implantable shunt with pressure sensing and telemetry, allowing clinician adjustment of valve settings based on measured ICP.
- **Why it is close:** Uses sensor feedback for shunt management. However, US20180000421A1 adjusts a single valve based on global ICP — it does not predict obstruction or redistribute flow across segments.
- **Source provenance:** R277 search

### Reference 3: Predictive maintenance for medical devices
- **Citation:** General literature on predictive maintenance for implantable devices (multiple)
- **What it teaches:** Statistical/machine-learning prediction of device failure from sensor trends.
- **Why it is close:** Same predictive-maintenance concept. However, applied generally to implants (pacemakers, etc.), not specifically to multi-segment CSF shunt drainage with the dual-invariant control law.
- **Source provenance:** R277 search

### Reference 4: Distributed micro-shunt mesh (R268 internal candidate SC-10)
- **Citation:** Internal R268 candidate, downgraded R269 (architecture occupied, control law unspecified)
- **What it teaches:** Distributed micro-shunts as a redundant drainage architecture.
- **Why it is close:** Same architectural concept (multiple drainage paths). However, SC-10 had no specified control law; P-01's contribution IS the control law.
- **Source provenance:** R268-R269 internal portfolio

## 2. Known third-party claims / patents that could matter (THREATS)

### Threat 1: US12636471B2 (CSF metering shunt, May 2026)
- **What it claims:** A CSF metering shunt with active flow control.
- **Why it could matter:** If the claims cover active per-segment flow control in CSF shunts, P-01 could be threatened.
- **Our assessment:** WATCH. Need full claim analysis. The patent appears to focus on global metering, not per-segment predictive redistribution. But this is not yet definitively established.
- **Source provenance:** R274 negative-search provenance

### Threat 2: WO2011146757A2 (active perturbation for shunt diagnosis)
- **What it claims:** Active perturbation (vibration, pressure pulse) for shunt state estimation.
- **Why it could matter:** If P-01's predictive algorithm uses active perturbation, this patent could read on it.
- **Our assessment:** LIKELY IMMATERIAL. P-01 uses passive observation (flow/pressure trends), not active perturbation. But counsel should confirm.
- **Source provenance:** R258 (IB-03 deep search found this)

### Threat 3: Osmotic valve US20020087111A1 (functional equivalent for valve mechanism)
- **What it claims:** Osmotically-driven valve for shunt flow control.
- **Why it could matter:** If P-01's variable orifice is implemented as an osmotic valve, this could read on the actuator.
- **Our assessment:** LIKELY IMMATERIAL. P-01's variable orifice is electromechanical (MEMS), not osmotic. But counsel should confirm.
- **Source provenance:** R274 (CM-01 downgrade)

## 3. Search saturation evidence

- Total queries executed across R274 + R277: ~50+
- Databases covered: USPTO, EPO, Google Patents, PubMed, OpenAlex, PatSnap, PatentBear
- Result saturation: yes — after ~30 queries, new results plateaued
- Negative-search provenance: per R274, queries → databases → results → exclusions all logged

## 4. Honest summary

The prior-art landscape for P-01 has three relevant categories:

1. **Multi-segment/multi-lumen catheters** (CN103491862A, SC-10) — these cover the physical architecture but NOT the predictive control law.
2. **Active shunt control with sensor feedback** (US20180000421A1) — these cover single-valve sensor-driven adjustment but NOT multi-segment predictive redistribution.
3. **Predictive maintenance for implants** (general literature) — these cover the prediction concept but NOT the specific application to CSF shunt obstruction with the dual-invariant control law.

P-01's specific contribution — the dual-invariant (INV-1 + INV-2) predictive redistribution control law applied to multi-segment CSF drainage — does not appear to be directly taught in any single reference. However, the threats (US12636471B2, WO2011146757A2) require full claim analysis by buyer counsel.

**This is NOT a patentability opinion.** Buyer counsel should examine the specific claims of the cited patents in light of the buyer's intended use.
