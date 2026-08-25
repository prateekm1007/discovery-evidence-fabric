# Questions for Buyer Counsel — P-01

**Candidate:** P-01 — Predictive Occlusion-Isolation Controller
**Authority:** Article XXXVI §2 C20

---

## 1. Recommended diligence questions

### Q1. Does US12636471B2 (CSF metering shunt, May 2026) read on P-01's per-segment flow control?
- **Context:** US12636471B2 is a recent (May 2026) patent on CSF metering shunts with active flow control. P-01 uses per-segment variable orifice flow control. If US12636471B2's claims cover per-segment active flow control in CSF shunts, P-01 could be threatened.
- **Specific question:** Do the independent claims of US12636471B2 cover multi-segment (per-catheter-segment) active flow control, or only global (single-valve) metering?
- **Why we are asking:** This is the most recent and most directly relevant reference. We have not performed full claim analysis.
- **Possible answers and implications:**
  - If claims cover only global metering: P-01's per-segment approach likely does not infringe.
  - If claims cover per-segment flow control: P-01 may need design-around or license.

### Q2. Does WO2011146757A2 (active perturbation for shunt diagnosis) read on P-01's predictive algorithm?
- **Context:** WO2011146757A2 covers active perturbation (vibration, pressure pulse) for shunt state estimation. P-01 uses passive observation (flow/pressure trends), not active perturbation.
- **Specific question:** Does WO2011146757A2's claims extend to passive observation-based prediction, or only to active perturbation-based diagnosis?
- **Why we are asking:** We believe P-01 does not infringe because it uses passive observation. But counsel should confirm the claim scope.
- **Possible answers and implications:**
  - If claims limited to active perturbation: P-01 likely does not infringe.
  - If claims extend to passive observation: P-01 may need design-around.

### Q3. Is the dual-invariant control law (INV-1 + INV-2 simultaneously) patentable subject matter?
- **Context:** P-01's core contribution is the dual-invariant control law. Control laws can face §101 subject matter eligibility challenges in the US.
- **Specific question:** Does the dual-invariant control law, as applied to a multi-segment CSF shunt with specific sensors and actuators, constitute patent-eligible subject matter under §101?
- **Why we are asking:** We are not rendering a patentability opinion. Counsel should assess.
- **Possible answers and implications:**
  - If eligible: P-01 can be patented, strengthening the IP position.
  - If ineligible: P-01's value depends on trade-secret (know-how) and design-around protection.

### Q4. Does CN103491862A (multi-lumen CSF drainage catheter) cover P-01's physical architecture?
- **Context:** CN103491862A is a Chinese patent on multi-lumen CSF drainage. P-01 uses a multi-segment catheter with per-segment flow control.
- **Specific question:** Do CN103491862A's claims cover a multi-segment catheter with active per-segment flow control, or only passive multi-lumen drainage?
- **Why we are asking:** CN103491862A appears to be passive multi-lumen, but counsel should confirm whether the claims extend to active per-segment control.
- **Possible answers and implications:**
  - If passive only: P-01's active per-segment control likely does not infringe.
  - If extends to active: P-01 may need design-around or license (China-specific).

### Q5. Is the 30% revision rate reduction claim supportable in buyer's specific market?
- **Context:** P-01's economic model assumes a 30% reduction in shunt revision rate. This is MODELLED, not measured.
- **Specific question:** Based on the buyer's actual revision rate data (under NDA), is a 30% reduction plausible? What reduction would the buyer need to justify adoption?
- **Why we are asking:** The 30% assumption is the central economic claim. Buyer-specific data will either validate or challenge it.
- **Possible answers and implications:**
  - If buyer's data supports 30%: economic model is validated for that buyer.
  - If buyer's data suggests lower reduction: economic model needs adjustment; price tier may need renegotiation.

### Q6. What is the buyer's regulatory pathway assessment?
- **Context:** P-01 is a software-driven medical device with active control. Regulatory pathway (PMA vs 510(k) vs De Novo) affects timeline and cost.
- **Specific question:** Based on the buyer's regulatory expertise, what pathway does the buyer recommend for P-01? What is the expected timeline and cost?
- **Why we are asking:** Our estimate ($22-53M, 5-10 years) is based on PMA pathway. Buyer may have a more efficient pathway.
- **Possible answers and implications:**
  - If PMA required: our estimate stands.
  - If 510(k) viable: timeline and cost could be significantly lower.

### Q7. What is the buyer's freedom-to-operate assessment for the implantable flow sensor?
- **Context:** P-01 requires an implantable CSF flow sensor. No commercial option exists. The buyer may have internal IP or know of relevant patents.
- **Specific question:** Does the buyer have freedom-to-operate for an implantable CSF flow sensor (ultrasonic, thermal, or pressure-differential-based)?
- **Why we are asking:** The flow sensor is the largest engineering risk. Buyer's FTO assessment affects V1 implantable development path.
- **Possible answers and implications:**
  - If buyer has FTO: V1 development can proceed.
  - If buyer lacks FTO: joint development or license needed.

### Q8. What exclusivity scope does the buyer require?
- **Context:** P-01 is offered with rights differentiated by price (R275). The buyer's intended use affects the appropriate scope.
- **Specific question:** Does the buyer require exclusivity in hydrocephalus shunts, in all CSF management, or in a specific patient population?
- **Why we are asking:** The transaction scope depends on the buyer's intended use.
- **Possible answers and implications:**
  - Hydrocephalus-exclusive: highest price tier.
  - All CSF management: higher price tier + cross-licensing considerations.
  - Specific patient population: lower price tier + field-of-use restriction.

## 2. Open uncertainties we have NOT resolved

- Whether the strict dual-invariant claim can be salvaged with a V2 controller redesign (simulator falsified V1)
- Whether the 24h survival failure is a fundamental limitation or a tunable parameter issue
- Whether the implantable flow sensor can be developed for <$200K (our estimate)
- Whether the 30% revision rate reduction will hold in clinical trials

## 3. What we are NOT asking counsel to do

- We are not asking counsel to render a patentability verdict on P-01.
- We are not asking counsel to opine on whether the dual-invariant control law is novel as a general principle (it is not — predictive maintenance is established).
- We are not asking counsel to guarantee the 30% revision rate reduction.
- We are asking counsel to examine the specific questions above, in the context of the buyer's intended use.
