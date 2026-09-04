# R405 — External Audit Response (Lead Portfolio 4)

**Responding auditor:** the repository's implementation agent (this session)
**External audit under review:** "Lead Portfolio 4 — External Audit & Elite Package Roadmap" (Claude Sonnet 4.6, external, independent; audit SHA 135fd74f, dated 2026-09-04), received as CEO input with the one-word directive **"audit"**.
**Repository state at response time:** local HEAD `f9aa4ab4` (R404, buyer-grade verification round — **not yet pushed**; the external audit audited `135fd74f` and therefore did not see R404).
**Constitution:** read in full before this response (CONSTITUTION_READ_FULLY: YES; v2.0.0, Articles I–LXIII).

---

## Part 0 — How to read this response

The external audit was performed at `135fd74f` (R403). One commit of work (R404, `f9aa4ab4`) landed after that audit's snapshot. This response therefore classifies every material claim of the external audit into exactly one of:

- **CONFIRMED** — verified against repository evidence this session.
- **ADDRESSED_BY_R404** — true at `135fd74f`, already resolved/extended by R404 (the audit's roadmap item is stale, not wrong).
- **DISPUTED** — the audit's claim does not match repository evidence (evidence cited below).
- **EXECUTED_THIS_ROUND** — a $0 roadmap item this round completed.
- **OWNER_GATED** — a roadmap item that is an owner/CEO action by record (release chain, patent search meter, engineering decisions), recorded here with the exact executable path.

The external audit's headline — "None of these packages are elite today... the gap is almost entirely documentation, arithmetic, and declaration" — is **CONFIRMED in structure**: the top-priority items are all $0 record work. This round executed the executable ones and found, in the process, that the audit's own demand for explicit arithmetic exposed a real unit-conversion defect in the repository's conductance machinery (Part 3).

---

## Part 1 — Findings the audit got right (CONFIRMED)

1. **REAL_BUYER = 0, PHYSICAL_OBSERVATION = 0, traceability unlinked, costs NOT_ESTABLISHED (except P11).** Verified: all four packages' TRANSFER_STATE/maturity records; the buyer repo's R394 truth model records EXPLICIT 0 / PARTIAL 0 / UNKNOWN 9–11 chains per package (engine-side corroboration: `premium_package_factory/r394/traceability.py` chain-state logic; the frozen corpus' r372-era `linked:true` flags are the superseded semantic-association standard). P11 is the only costed protocol ($15K/8wk, R339). CONFIRMED.
2. **PatentBear verdicts.** P04 CONDITIONAL (MEDIUM) / P08 PASS (VERY HIGH, zero specific-mechanism hits, US20190111255A1 element map) / P11 PASS refined to CONDITIONAL — all present in the restored R359/R361/R365 artifacts and the R403 NOVELTY_ASSESSMENT records. CONFIRMED.
3. **P13 has no novelty search for this technology.** CONFIRMED (R404's re-verification: REPORTED_BUT_UNLOCATED across the entire reachable history; the R403 lineage finding stands).
4. **PatSnap attempted-never-executed for all four** (error 67200203, balance exhausted). CONFIRMED in every NOVELTY_ASSESSMENT.
5. **"2 PatentBear queries remain."** CONFIRMED — the P13 record's meter note (2/20 remaining at last recorded state; the R359 artifacts show the meter's historical values, 11/20 remaining at R359, decreasing thereafter).
6. **P04 NIST correction not applied to the canonical package.** CONFIRMED — `applied_to_canonical_package: false` in the R390 loop closure; the valid rebuild (`pm:115852de5865efc8`) is recorded as a `valid_new_version_candidate` in GEOMETRY_SEPARATION.json. (Disposition: Part 4, item 1.)
7. **P11's two differentiators are UNESTABLISHED with materiality evidence NONE.** CONFIRMED verbatim from DIFFERENTIATION_AND_CAUSAL_CHAIN.json.
8. **P13's KA-014 (biofouling non-common-mode drift) is the kill channel and the recorded mitigations do not solve it.** CONFIRMED — the R404 LINEAGE_AUDIT records the P-25 failure (67.8% in-model cancellation, 3.45 mmHg > 2.0 threshold) and carries the mitigations as labels, not demonstrated repairs.
9. **P14's V2 addendum understates severity by presenting pressure reflection (1.9–3.5%) where intensity reflection is the acoustic-energy-relevant quantity.** CONFIRMED — and arithmetically exact: intensity = pressure², so 0.019²–0.035² = 0.036–0.123% ≈ the audit's 0.04–0.12%. The dominant obstruction classes (tissue 1.039, fibrous 1.072 Z-ratio) remain below the 1.1 kill threshold in the package record.
10. **System-level facts** (16-stage conductor, R401 behavioral validation, OpenAlex second lane, Semantic Scholar 429, PatentsView no key, WC2 corpus built but unmeasured, lexical F1 0.695 vs tested cross-encoder 0.857, end-to-end REJECTED). CONFIRMED — all carried in the R401/R401-WC2 records and re-verified in the R402 round.

---

## Part 2 — Errors in the external audit (DISPUTED)

1. **"R310/R311/R312 execution artifacts... do not exist in the repository or its history" (P08, and repeated in the roadmap's T2_ASSERTED item).** **DISPUTED — this is the R403 audit's own error, repeated.** R404 located the artifacts in git history (`e3b6adfd` — R310 4-model disagreement map, 200k photons, converged 1.049054 mW/cm²; `35514d0a` — R311 ACTUAL PyTissueOptics v2.0.1 run, 1.415645 mW/cm²; `f01ae2d1` — R312 convergence ladder, CI-overlap verdict), restored them byte-identically under `LEAD_PORTFOLIO_4/P08/VERIFICATION_EVIDENCE/` with sha256 + blob-sha1 custody, and verified the preregistration-hash binding. The audit's own open action ("independent execution of PyTissueOptics... required before this field can be upgraded") remains a valid recommendation, but the statement that the artifacts never existed in history is false, and the correct provenance class is **RECOVERED_EXECUTION_ARTIFACT** (restored with custody), not "consultant reconstruction."
2. **P04 Q_min: "The literature suggests 0.3–0.4 mL/hr as the physiological CSF production baseline."** **DISPUTED — unit error.** CSF production is 0.2–0.4 mL/**min** (≈ 12–24 mL/hr ≈ 500 mL/day). Verified this session by live web search: Tariq et al. 2023 (PMC10409822: "CSF production rate between 0.2 to 0.4 ml/min... estimated to be 18–24 ml/h"); Silverberg et al. 2002, J Neurosurg 97(6):1271 (0.4 ± 0.13 mL/min acute; 0.25 ± 0.08 chronic). The audit's threshold as written would be **60x too lenient** — a floor draining 0.3 mL/hr against ~20 mL/hr production is physiologically negligible (ICP would rise continuously). The corrected declaration is recorded at `LEAD_PORTFOLIO_4/P04/QMIN_FLOOR_FLOW_CALCULATION.json` with the audit error flagged and never adopted (Art. XXVII).
3. **"~125,000 CSF shunts implanted annually in the US (Isaacs et al. 2016)."** **DISPUTED — unverified, and the open-literature anchor differs.** The Hydrocephalus Association states "over 36,000 shunt surgeries are performed each year (one every 15 minutes)"; revision/diversion surgeries are "nearly one third of all neurosurgical procedures annually." No open source for 125,000 implants/year was found this session. Recorded as a divergent-sources note in the P04 commercial anchor (the revision-rate class 30–50%+ IS confirmed by multiple studies: 35.9%/1yr and 54.3% overall (pediatric PMC 2025); 17.7% (adults, ScienceDirect 2024); 81% ≥1 revision (Longeviti 2021)).
4. **ANSI Z136.1 numeric limits (1.8 J/cm² pulsed / 0.73 W/cm² continuous at 940 nm).** **NOT VERIFIABLE in open literature** (the standard is paywalled; open pages confirm ANSI Z136.1 governs skin MPE but do not publish the table values). Per Art. XXVII these figures are recorded as REPORTED-BY-EXTERNAL-AUDIT with owner-extraction-from-the-standard required before pre-registration. The audit's structural demand (pre-registered thermal kill boundary) is adopted; its numbers are not.
5. **Score inflation vs. R404 state.** The audit's per-package scores (P04 6.8, P08 5.8, P11 6.2, P13 5.1) score `135fd74f`. At `f9aa4ab4`: P08's D1 is resolved and the evidence layer restored (the audit's P08 "weakest physical evidence" premise is half-stale — the evidence layer is now the strongest of the four; what remains open is the D2 engineering decision); P04's geometry was independently re-verified by re-execution; P13's lineage is audited. The scores' orderings are not contested; their bases are superseded.
6. **Minor internal inconsistency:** Part 2 retires P14 without a score; Part 6 lists P14 at "6.1/10." Noted, not load-bearing.

---

## Part 3 — The defect the audit's arithmetic demand exposed (NEW THIS ROUND)

Executing the audit's Q_min item ("compute the theoretical floor lumen flow... if it's below, the package has a physics problem") required computing the floor conductance independently. That computation exposed a real defect:

**Both conductance functions divided by 133.322 where per-mmHg requires multiplying** (`reality_loop._conductance_ml_per_min_mmhg`, `physics_core.poiseuille_conductance`), making every recorded absolute conductance and flow **133.322² = 17,774.7x too small**. The R390 loop records' "declared floor conductance 1.432e-05 mL/(min·mmHg)" is actually **0.254 mL/(min·mmHg)**. Physical sanity: a 0.6 mm × 100 mm water column at 10 mmHg passes ~2.5 mL/min, not 1.4e-4 mL/min. The existing test pin did not catch it because its "hand computation" re-used the implementation's own conversion direction.

**Unaffected:** every ratio-based verdict (NIST diameter compensation, restoration ratio 0.999984, BEATS_BASELINE margins, KEEP/KILL decisions) — the constant cancels. **Fixed:** both functions, with adversarial magnitude guards and an independent-unit-path pin (a verification that re-derives through a different conversion route, so direction errors cannot cancel). **Disclosed:** `R405/UNIT_CONVERSION_DEFECT_DISCLOSURE.json` (affected-artifact inventory, Art. XXXI memory artifact, Art. XI history-preservation dispositions). No recorded verdict changes.

Consequence for P04: the floor lumen is **not** the flow-limiting element (6–12x production at minimum head); the experiment's discriminating power sits in partial common-cause obstruction, now quantified (~47% effective-diameter reduction tolerance).

---

## Part 4 — Roadmap disposition (every $0 item)

| # | Audit item (package) | Disposition |
|---|---|---|
| 1 | Apply NIST correction to canonical package (P04) | **OWNER_GATED — auditor conflict recorded, not silently resolved.** The R403 record holds application as "an owner release-chain decision (Art. XXXIX protocol), NOT a hardening edit"; the external audit says apply it now ("not a new engineering decision"). Both positions are recorded; the release protocol itself cannot run today (Art. XXXIX §5 requires both repos clean and PUSHED before the build — R404/R405 are unpushed pending the PAT). The executable path is recorded in GEOMETRY_SEPARATION.json: templates.py `floor_lumen_diameter_mm` 0.6→0.5471 + physics envelope + r397 pin coordination + rebuild (deterministic, machinery proven by R404) + buyer release through r386 chain. Q_min flows are computed for BOTH geometries so the decision is number-informed. |
| 2 | Declare Q_min (P04) | **EXECUTED** — `QMIN_FLOOR_FLOW_CALCULATION.json`: range 0.2–0.4 mL/min (PHYSIOLOGICAL class, web-verified citations), corrected floor flows, ~47% common-cause tolerance margin, audit's unit error flagged. Single-value pre-registration remains owner-gated (Art. XXVII). |
| 3 | Common-cause explicit kill + protocol (P04) | **EXECUTED** — quantified arm added to DECISIVE_EXPERIMENT.json: simultaneous obstruction upstream of both openings, floor flow measured independently, kill at ≥90% of tested pressure/flow cases (threshold provenance: external-audit proposal, ENGINEERING class, owner pre-registration required — never silently promoted). |
| 4 | Resolve D1/D2 (P08) | D1 **ADDRESSED_BY_R404** (see Part 2.1). D2: **PARTIALLY EXECUTED** — the audit's explicit arithmetic is now recorded side-by-side with the recorded fluence anchors in ENERGY_BUDGET.json, showing the exact point of divergence (source-power assumption 100 mW/cm² is the audit's reconstruction, not recorded data; µ_eff 1.5 cm⁻¹ is a literature-class assumption). The D2 decision itself (500 µW target vs 121–163 µW band vs area) remains OWNER-GATED as R404 classified it. |
| 5 | Downgrade T2_ASSERTED → MODELLED (P08) | **ADDRESSED_BY_R404 in stronger form** — artifacts restored with custody (RECOVERED_EXECUTION_ARTIFACT class, not MODELLED); re-execution remains the open owner action; buyer-surface relabeling is a release-chain operation. |
| 6 | Thermal kill condition (P08) | **EXECUTED (structure) / OWNER-GATED (numbers)** — pre-registered kill-boundary comparison added to DECISIVE_EXPERIMENT.json; ANSI figures recorded as REPORTED-unverified pending owner extraction from the paywalled standard text. |
| 7 | Source GaAs low-irradiance efficiency (P08) | **EXECUTED (sourcing status)** — Moon et al. 2020, "Dual-Junction GaAs Photovoltaics for Low Irradiance Wireless Powering of Subcutaneous Implants" (found via live search; snippet: "NIR light provides a means for high power conversion efficiency (>30%) in mm-scale subcutaneous implantable devices") recorded as the citable anchor for the ~30% class at low irradiance; Zhao et al. 2023 (18.6% at 8.6 mW/cm²) recorded as the conservative datapoint. Full-text verification open (Art. II — snippet-level evidence, honestly labeled). |
| 8 | Power-target framing (P08) | **EXECUTED** — "what 100–160 µW powers" recorded with the µW-scale implant literature anchor (Amar et al. 2015, "Power Approaches for Implantable Medical Devices"); the audit's specific device figures (SynchroMed 150 µW etc.) remain REPORTED-unverified. |
| 9 | Quantitative kill condition + MDD (P11) | **EXECUTED** — proposed quantified kill conditions A/B added (provenance: external-audit proposal, MODEL_DERIVED, owner pre-registration gate); instrument MDD computed: quantization σ 0.0289 s → MDD(p<0.05) 0.0253 s vs the claimed 0.1 s difference → DETECTABLE (3.95x margin), with the resolution-limited worst case disclosed (at 0.1 mL/min steady flow the 10% settling band equals the ±0.01 mL/min resolution). `INSTRUMENT_MDD_CALCULATION.json`. |
| 10 | Cost estimates (P04/P08/P13) | **EXECUTED (as REPORTED estimates)** — the audit's itemized ranges recorded in each DECISIVE_EXPERIMENT cost_basis with provenance = external auditor's itemization, class ENGINEERING_ESTIMATE (REPORTED), owner confirmation required. P11's recorded $15K/8wk stands (the audit's wider $15–38K range recorded as context). P13's $95–265K recorded with the audit's own 5–10x disclosure. |
| 11 | Claim maps (P04 US20240207499A1, P11 US20250242099A1) | **EXECUTED** — 3-sentence differentiations grounded in recorded evidence + live-searched patent text. P04: the closest prior (granted as US11865241B2, "Sensor monitoring system for in-dwelling catheter based treatments") is sensor-anchored per its own dependent-claim language ("flow sensor coupled to...", "limited-use sensor configured to releasably engage..."); the floor lumen is a passive geometric conductance split with no sensing elements. P11: US20250242099A1 (Goldsmith, "Vascular valves and servovalves — and prosthetic disorder response systems") is a vascular valving/servovalve publication, not a passive inline CSF damper. Both recorded in the NOVELTY_ASSESSMENT files with source URLs and retrieval method; final claim charts remain owner/counsel work (not legal opinions). |
| 12 | Traceability: link 3 DI chains per package | **EXECUTED (engine-side)** — new `ENGINEERING_TRACEABILITY.json` per package, R394-style identifier bindings (DI→DO→V→DECISIVE_EXPERIMENT), evidence classes per link, remaining chains left UNKNOWN (never silently linked). The BUYER-side traceability files are frozen (owner release-chain). |
| 13 | Commercial anchors (all four) | **EXECUTED (as REPORTED anchors)** — recorded in each BUYER_SEQUENCE with divergent sources disclosed, the audit's unverified figures flagged (125k/yr shunt figure DISPUTED; ICP market $450–600M vs search-found range $251M–$2.06B depending on scope), revision-rate class confirmed, prevention-economics framing recorded as the audit's proposal. Class ROUGH_ESTIMATE/REPORTED; verification before buyer presentation is an owner action. |
| 14 | Run PatentBear for P13 (2 queries) | **OWNER_GATED** — the audit's exact query strings are recorded in P13's NOVELTY_ASSESSMENT as the proposed plan; the meter (2/20 remaining) and free alternatives (EPO/Lens) are already recorded there. |
| 15 | KA-014 design mitigation (P13) | **EXECUTED (option c, the audit's honest-acknowledgment path)** — KA-014 promoted to the package summary's most prominent risk sentence; the specific BSA accelerated-fouling protocol recorded as PROPOSED spec (37 °C, physiological concentration, 4-week soak, weekly bridge-offset measurement, >1 mmHg differential drift = the P-25 channel recurring). The design-level mitigations (coating/shield options) recorded as owner choices with the audit's evidence-class requirements. |
| 16 | Drift target to EXTERNAL_PRECEDENT (P13) | **OWNER_GATED** — the audit's candidate sources (Silmeco/Kistler/Romain) were not verifiable this session; the sourcing action is recorded with the required citation form. |
| 17 | Formal KILL record for P14 to cemetery | **OWNER_GATED — not executed unilaterally.** The CEO disposition (R382) exists and the audit recommends executing it; killing a portfolio item is a CEO action (the R404 classification pinned P14's records byte-unchanged; that pin is re-verified this round). The audit's physics basis is CONFIRMED (Part 1.9); the recommendation is recorded in P14's owner-action list via this response (the P14 record itself stays sha-pinned). |
| 18 | Run WC2 attacker calibration (system) | **OWNER/TRANSPORT_GATED** — blocked on LLM transport (z.ai 429 / NVIDIA 410), unchanged since R402; the frozen harness and single orchestrator exist (R401-WC2 phase 7). |
| 19 | Deploy cross-encoder reranker (system) | **NOT EXECUTED THIS ROUND** — a pipeline code change outside the portfolio-documentation scope of this round ("no more infrastructure" standing instruction); the measured comparison (0.695 vs 0.857, tested-not-deployed) stands in the R401 record. Recorded as open. |
| 20 | Run decisive experiments (P04/P11 first) | **OWNER/BUDGET_GATED** — lab access and $15–40K budgets are owner actions; the records are now decision-grade for that conversation (this round's cost/kill/Q_min/MDD work closes the audit's declared precondition: "a buyer can evaluate whether to commission the decisive experiment"). |

---

## Part 5 — Final classification check (no forced changes)

R404's FINAL_CLASSIFICATION is re-verified and **unchanged** by this round's work, because nothing that changed is a classification-deciding fact:

- **P04 READY_FOR_TECHNICAL_EVALUATION** — the Q_min/kill/cost/anchor/traceability work strengthens the evaluation surface; the NIST canonical application remains owner-gated (and does not block technical evaluation; both geometries' physics is now computed).
- **P08 REQUIRES_ENGINEERING_REPAIR** — D2 remains the decisive owner engineering decision; the arithmetic display and thermal/efficiency sourcing sharpen it but do not resolve it.
- **P11 READY_FOR_SPONSORED_VALIDATION** — still the only costed recorded protocol; the kill conditions and MDD make it more sponsorable, not less.
- **P13 REQUIRES_EVIDENCE_REPAIR** — the fresh patent search remains the gating owner action; KA-014 acknowledgment and the fouling protocol spec are recorded.
- **P14 NOT_IN_FOUR_LEAD_PORTFOLIO** — record byte-unchanged (pin re-verified); KILL-record recommendation forwarded to owner.

The audit's own projected classifications ("after roadmap: ENGINEERING_VALIDATED 8.5–8.9/10") are roadmap projections, not current states, and are not adopted as claims.

---

## Part 6 — What the buyer gets from this round (and what it does not)

**Gets:** corrected absolute hydraulics with adversarial magnitude guards; a Q_min declaration with real physiological units and cited sources; quantified kill conditions on P04/P11; instrument detectability numbers for P11; explicit D2 arithmetic; claim maps grounded in recorded + searched patent text; cost ranges with provenance; commercial anchors with divergent sources disclosed rather than laundered; three linked traceability chains per package; an honest error ledger (two audit errors, one repo defect, all with evidence).

**Does not get:** physical validation (PHYSICAL_OBSERVATION remains 0 for all four packages — Art. LIII); a novelty opinion, patentability opinion, or FTO (the claim maps are differentiation arguments, not legal opinions — Art. XXVIII); unverified numbers presented as facts (every audit figure that failed verification is labeled REPORTED/DISPUTED with its verification status); a pushed release (the PAT is still required — operator reminder issued).

---

*Committed as part of the R405 round. Zero buyer-repository bytes touched; zero historical artifacts renamed, rewritten, or deleted; P14 records byte-unchanged; the R401 frozen baseline untouched (its contaminated absolute values are disclosed, not rewritten — Art. XI/LIX).*
