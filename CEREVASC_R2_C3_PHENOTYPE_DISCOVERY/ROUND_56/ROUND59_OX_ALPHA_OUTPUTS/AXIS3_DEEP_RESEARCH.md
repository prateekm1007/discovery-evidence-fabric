# OX Alpha task: axis3_deep_research

- Timestamp: 2026-08-22T00:27:05.387313+00:00
- Model: stealth/ox-alpha
- Elapsed: 71.61s
- Finish reason: stop
- Usage: {"prompt_tokens": 2163, "completion_tokens": 3365, "total_tokens": 5528, "cost": 0, "is_byok": false, "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "audio_tokens": 0, "video_tokens": 0}, "cost_details": {"upstream_inference_cost": 0, "upstream_inference_prompt_cost": 0, "upstream_inference_completions_cost": 0}, "completion_tokens_details": {"reasoning_tokens": 0, "image_tokens": 0, "audio_tokens": 0}}

## User prompt

```
You are performing DEEP RESEARCH on AXIS-3 for the CTO. The CTO has chosen AXIS-3 (post-hoc outcome prediction via retrieved-clot characterization + intra-procedural features) for deep research. The scout phase is complete; this is the deep-dive that will determine whether AXIS-3 lives or dies.

CTO RATIONALE FOR CHOOSING AXIS-3:
- Lowest total kill-risk score (14/25) across the 4 axes.
- Eliminates the Layer A failure mode: no latent-quantity identifiability problem (identifiability risk = 2), no pause protocol (clinical safety risk = 1), no pre-procedural timing requirement.
- Highest risks are prior art occupation (4) and patentability (4) — these are exactly what deep research must attack.
- Survival condition from scout: "retrieved-clot features add statistically significant incremental AUC over established periprocedural predictors, AND identify a concrete actionable decision that the score gates."

YOUR DEEP RESEARCH TASK — produce a structured report with these mandatory sections:

============================================================
SECTION 1: CE-014 PRIOR ART SEARCH (REAL SEARCHES, NOT SELF-COINED TERMS)
============================================================

For EACH of the following assignees / inventors / CPC classes, propose the EXACT query strings the CTO should run against Google Patents, USPTO, and Espacenet. Do NOT invent patent numbers. Instead, for each search vector, state:
- The assignee / CPC / inventor vocabulary
- The expected search URL or query string
- What claim elements you would expect to find
- Whether you can pre-verify any specific patent number from memory (HIGH confidence only — else UNKNOWN)

Search vectors (use ALL of these — this is the CE-014 method):
(a) RapidAI / iSchemaView — CPC G06N 20/00, G16H 50/20, A61B 5/00; vocabulary "CT perfusion," "RAPID," "ICH," "LVO," "CTA analysis"
(b) Brainomix — CPC G16H 50/20, A61B 5/00; vocabulary "e-Stroke," "e-ASPECTS," "ASPECTS auto," "treatment effect"
(c) Viz.ai — CPC G16H 50/20, H04N 5/265; vocabulary "LVO detection," "stroke workflow," "notification"
(d) General ML outcome prediction — CPC G16H 50/30, G06N 20/00; vocabulary "outcome prediction," "mRS prediction," "sICH prediction," "nomogram"
(e) Retrieved-clot histology/composition — CPC A61B 10/02, G01N 33/48, A61B 5/145; vocabulary "retrieved clot," "thrombus histology," "fibrin-rich," "RBC-rich," "composition"
(f) Intra-procedural perfusion feedback — CPC A61B 5/026, A61B 8/06; vocabulary "intra-procedural perfusion," "Doppler thrombectomy," "real-time CTP"

============================================================
SECTION 2: NON-OBVIOUSNESS ATTACK (KSR-STYLE)
============================================================

Construct the STRONGEST possible obviousness attack against an AXIS-3 candidate claim of the form:
"A method comprising: (a) characterizing retrieved thrombus material by composition/mechanical signature during endovascular stroke treatment; (b) combining said characterization with intra-procedural procedural features; (c) outputting a calibrated post-procedural risk score for sICH and 90-day mRS at procedure completion."

Identify:
- Prior art A (closest imaging-only ML prognostic system) — cite a real reference or UNKNOWN
- Prior art B (closest published retrieved-clot-to-outcome association paper) — cite a real reference or UNKNOWN
- The motivation/rationale a POSITA would cite to combine A + B
- Whether the combination yields predictable results (KSR prong)
- One specific reason the combination might NOT be obvious (the survival hook)

============================================================
SECTION 3: UTILITY ATTACK ("SO WHAT" DEFENSE)
============================================================

AXIS-3's biggest risk per the scout is that a post-hoc score changes no intervention. Construct the strongest utility attack:
- What actionable clinical decisions could plausibly be gated by a post-procedural sICH/mRS risk score? List 3-5.
- For each, state whether the action is currently gated by an existing cheaper signal (NIHSS, age, ASPECTS, TICI grade, etc.).
- If the score merely duplicates existing triage signals, the axis fails on utility. State honestly whether this is likely.
- Identify the SINGLE most defensible actionable decision that could rescue utility.

============================================================
SECTION 4: IDENTIFIABILITY OF RETRIEVED-CLOT FEATURES
============================================================

The scout rated identifiability risk = 2 (low) because retrieved-clot features are directly measurable (no latent quantity). Validate or refute this:
- What retrieved-clot features are proposed as inputs? (composition, mechanical, imaging-derived)
- For each, is the feature directly measurable post-retrieval, or does it require an in-situ measurement that brings back Layer A's identifiability problem?
- If post-retrieval measurement is required, is there a standardized measurement protocol? If not, the feature is "measurable but unstandardized" — a different failure mode.
- State the strongest attack on the identifiability=2 rating.

============================================================
SECTION 5: CANDIDATE CLAIM REFINEMENT
============================================================

Based on Sections 1-4, propose the REFINED candidate claim for AXIS-3 that:
- Avoids the obviousness trap of Section 2
- Survives the utility attack of Section 3 by tying to a specific actionable decision
- Stays within the identifiability envelope of Section 4
- Is bounded enough to be patentable but broad enough to be valuable

Provide:
- The claim (2-3 sentences)
- The closest prior art (real citations or UNKNOWN with search vectors)
- The 3 strongest attacks on this refined claim
- The 3 survival conditions (what must be true for this claim to live)

============================================================
SECTION 6: KILL DECISION RECOMMENDATION (NON-BINDING — CTO DECIDES)
============================================================

Based on Sections 1-5, state your honest engineering assessment:
- KILL: the axis is fatally flawed and should be killed
- CONDITIONAL SURVIVAL: the axis has a narrow path forward under specific conditions (state them)
- PROMOTE: the axis is robust enough to advance to formal invention pipeline

Do NOT make the decision — the CTO will. But state the engineering case clearly.

CONSTRAINTS:
- Do NOT fabricate. Say UNKNOWN explicitly.
- Do NOT propose v2/AI/neural-network re-skins of killed Layer A.
- Cite REAL references only. If you cannot verify, mark UNKNOWN with a specific search vector.
- Be concise. Target ~1500-2000 words total. Do NOT spend tokens on extensive internal reasoning — produce the structured report directly.
- Per CE-017: if you propose any latent quantity to measure, state the identifiability survival conditions explicitly.

OUTPUT FORMAT: Plain text, no emojis. Start with "===== AXIS-3 DEEP RESEARCH =====".

```

## Response (content)

===== AXIS-3 DEEP RESEARCH =====

------------------------------------------------------------
SECTION 1: CE-014 PRIOR ART SEARCH (EXACT QUERY STRINGS)
------------------------------------------------------------

(a) RapidAI / iSchemaView
- Vectors: assignee "RapidAI" OR "iSchemaView"; CPC G06N 20/00, G16H 50/20, A61B 5/00; keywords "CT perfusion", "LVO detection", "hemorrhage", "core infarct", "mismatch"
- Google Patents: https://patents.google.com/?assignee=RapidAI&cpc=G16H50/20 ; also q="iSchemaView" AND "perfusion"
- Expected claim elements: automated image analysis of CTA/CTP; LVO detection; perfusion map generation; workflow notification; possibly outcome/treatment-selection scoring.
- Pre-verified numbers: UNKNOWN from memory at HIGH confidence. Expect a family around automated perfusion imaging (search will surface it).

(b) Brainomix
- Vectors: assignee "Brainomix"; CPC G16H 50/20, A61B 5/00; keywords "ASPECTS", "e-Stroke", "automated image analysis", "treatment effect", "functional outcome"
- Query: https://patents.google.com/?assignee=Brainomix ; Espacenet: ti=("ASPECTS" OR "stroke") AND pa("Brainomix")
- Expected claim elements: automated ASPECTS scoring; collateral assessment; prediction of treatment benefit from non-contrast CT.
- Pre-verified numbers: UNKNOWN.

(c) Viz.ai
- Vectors: assignee "Viz.ai"; CPC G16H 50/20, H04N 5/265 (image transmission); keywords "LVO", "notification", "workflow", "mobile", "alert"
- Query: https://patents.google.com/?assignee=Viz.ai
- Expected claim elements: LVO detection on CTA; automated notification to interventionalist; image routing. Outcome prediction less likely here.
- Pre-verified numbers: UNKNOWN.

(d) General ML outcome prediction
- Vectors: CPC G16H 50/30 (prediction of disease outcome), G06N 20/00; keywords "modified Rankin", "mRS prediction", "symptomatic intracranial hemorrhage", "nomogram", "thrombectomy outcome"
- Query: https://patents.google.com/?q=("mRS" OR "Rankin") AND ("thrombectomy" OR "stroke") AND cpc=G16H50/30
- Expected claim elements: feature vector (age, NIHSS, ASPECTS, glucose, TICI) -> calibrated probability of mRS/sICH.
- Pre-verified numbers: UNKNOWN. Note: the academic literature (not patents) is the dominant prior art here — see Section 2, Prior Art A.

(e) Retrieved-clot histology/composition
- Vectors: CPC A61B 10/02 (instruments for taking samples), G01N 33/48 (biological material analysis), A61B 5/145; keywords "retrieved thrombus", "clot histology", "fibrin", "red blood cell", "erythrocyte-rich", "thrombus composition", "stent retriever"
- Query: https://patents.google.com/?q=("retrieved" AND "thrombus") AND cpc=A61B10/02 ; Espacenet: ti=("thrombus" AND "composition")
- Expected claim elements: devices/methods for capturing, imaging, or analyzing retrieved clot; possibly correlation to etiology or device choice.
- Pre-verified numbers: UNKNOWN. Academic prior art is strong here (see Prior Art B).

(f) Intra-procedural perfusion feedback
- Vectors: CPC A61B 5/026 (blood-flow measurement), A61B 8/06 (Doppler); keywords "intra-procedural", "perfusion", "Doppler", "revascularization monitoring", "microcatheter"
- Query: https://patents.google.com/?q=("intra-procedural" AND "perfusion") AND cpc=A61B5/026
- Expected claim elements: real-time flow assessment during thrombectomy; confirmation of reperfusion; possibly clot-position sensing.
- Pre-verified numbers: UNKNOWN.

CE-014 compliance note: all vectors above use assignee vocabulary, CPC classes, and inventor-domain terminology ("fibrin-rich", "TICI", "ASPECTS"), not self-coined phrases. Every vector must be run; absence of hits on self-coined phrases would be a false negative.

------------------------------------------------------------
SECTION 2: NON-OBVIOUSNESS ATTACK (KSR)
------------------------------------------------------------

Prior Art A (imaging/clinical ML prognostic system): Nogueira RG et al., machine-learning prediction of functional outcome after thrombectomy using the HERMES dataset (published ~2019-2020; exact journal/volume UNKNOWN — verify via PubMed search "Nogueira machine learning thrombectomy outcome"). This model uses age, NIHSS, ASPECTS, glucose, and treatment variables to predict 90-day mRS. Additional real literature: the MR CLEAN and HERMES pooled analyses establishing TICI grade and baseline predictors of outcome (citations verifiable via PubMed; specific DOIs UNKNOWN).

Prior Art B (retrieved-clot-to-outcome association): Multiple published studies correlate retrieved-clot histology (RBC-rich vs fibrin-rich) with stroke etiology, recanalization success, and outcomes — e.g., work by Liebeskind and collaborators on clot composition and etiology, and Boeckh-Behrens et al. on thrombus histology (exact citations UNKNOWN at HIGH confidence; verify via PubMed "thrombus histology thrombectomy outcome"). Also Marder et al. on clot structure (2006, Stroke — verify).

Strongest KSR attack:
1. A POSITA knows (Prior Art B) that clot composition correlates with outcome, and knows (Prior Art A) that combining periprocedural features into an ML outcome score is standard practice.
2. Motivation to combine: both are published, both target the same endpoint (post-thrombectomy outcome), and combining a new measurable feature with an established predictive model is a routine "improve the feature set" optimization — exactly the predictable-result scenario KSR condemns.
3. Predictable results: adding a known outcome-correlated feature to a logistic/ML model predictably changes AUC; no unexpected property is required.
4. The claim as drafted ("characterize clot + combine with procedural features + output calibrated score") reads as an arithmetic aggregation of two known teachings.

Survival hook (why it might NOT be obvious): if the claim requires a specific, non-generic coupling — e.g., the clot feature is measured intra-procedurally in real time (not post-hoc histology) and the score gates a decision that occurs before the patient leaves the angiography suite (a timing constraint neither A nor B teaches) — then the combination requires more than routine optimization. Generic "add a feature" claims die; "intra-procedural measurement + gated decision" claims have a hook.

------------------------------------------------------------
SECTION 3: UTILITY ATTACK ("SO WHAT")
------------------------------------------------------------

Plausible gated decisions:
1. Intensity of post-procedural BP control (higher-risk patients -> tighter systolic targets). Currently gated by NIHSS, age, and TICI grade; several trials (e.g., ENCHANTED2/BP-target trials) address BP targets but do not use clot features. Partially duplicated signal.
2. Destination triage: ICU vs step-down vs discharge. Currently gated by NIHSS and TICI. Largely duplicated.
3. Antithrombotic timing (when to start antiplatelet/anticoagulation post-EVT). Currently gated by TICI, hemorrhage on immediate CT, and procedural factors. A calibrated sICH risk could add marginal value but existing CT at 24h dominates.
4. Aggressive rescue therapy intra-procedurally (continue vs stop after partial reperfusion) — but this requires the score DURING the procedure, which conflicts with post-hoc clot characterization.
5. Enrollment/stratification in post-procedural neuroprotectant trials (risk enrichment). Not gated by a cheaper signal — this is genuinely new.

Honest assessment: decisions 1-3 are substantially duplicated by NIHSS + TICI + immediate CT. Decision 4 is the most valuable but is temporally incompatible with post-retrieval characterization unless the clot feature is available mid-procedure (possible: first-pass retrieved clot informs whether to continue). Decision 5 (trial enrichment) is real but low commercial value.

Single most defensible actionable decision: intra-procedural continuation/escalation decision gated by first-pass retrieved-clot signature — i.e., the score must be computed before the procedure ends, which forces the claim to include real-time measurement and gives it a decision no existing signal gates.

------------------------------------------------------------
SECTION 4: IDENTIFIABILITY OF RETRIEVED-CLOT FEATURES
------------------------------------------------------------

Proposed inputs:
- Composition (RBC/fibrin ratio): directly measurable post-retrieval via histology — but histology takes hours-days, killing intra-procedural use. Faster proxies: optical (color/transmittance), impedance, or imaging of the clot in the retrieval device. These proxies are measurable but UNSTANDARDIZED — no accepted protocol maps proxy reading to histology-validated composition. This is the "measurable but unstandardized" failure mode.
- Mechanical signature (stiffness/adherence during retrieval): measurable via device force sensing, but no standard device reports this; requires new hardware or instrumented retrievers. Measurable in principle, unstandardized in practice.
- Imaging-derived clot features (clot density on CT, length on CTA): standardized and pre-procedural, but these are NOT retrieved-clot features — they collapse back toward Prior Art A territory and add no novelty.

Strongest attack on identifiability=2: the rating is correct that there is no latent-quantity problem (no inverse problem, no unobservable state). But it conflates "measurable" with "measurable under a validated protocol." The composition proxies that would enable intra-procedural use have no standardization, no reproducibility data, and no established mapping to the histology gold standard. Identifiability risk should be re-rated 2 for post-hoc histology use, 3-4 for intra-procedural proxy use. Per CE-017: the latent quantity here is "true clot composition" inferred from a proxy; identifiability survival conditions are (i) a validated proxy-to-histology calibration on >=50-100 retrieved clots, (ii) demonstrated inter-device reproducibility, (iii) demonstration that proxy measurement does not damage/alter the clot.

------------------------------------------------------------
SECTION 5: CANDIDATE CLAIM REFINEMENT
------------------------------------------------------------

Refined claim:
"A method for guiding endovascular stroke treatment comprising: during the procedure, measuring a physical signature of thrombus material retrieved in a first retrieval pass using a sensor integrated with the retrieval system; computing, from said signature together with intra-procedural procedural features (reperfusion grade, pass count, device trajectory), a calibrated risk score for symptomatic intracranial hemorrhage and 90-day functional outcome available before procedure completion; and gating a continuation/escalation decision — whether to perform additional retrieval passes or adjunct therapy — on said score."

Closest prior art: Prior Art A (Nogueira/HERMES ML outcome model — UNKNOWN exact citation, verify PubMed) and Prior Art B (clot histology-outcome association literature — UNKNOWN exact citations, verify PubMed "thrombus histology thrombectomy"). Patent vectors (a)-(f) of Section 1 all UNKNOWN pending execution.

Three strongest attacks:
1. Obviousness: combining a known outcome-correlated feature (clot composition) with a known ML outcome model is predictable (KSR).
2. Utility: if the gated decision (extra passes) is already made on TICI/fluoroscopy, the score adds nothing.
3. Standardization: the physical signature has no validated proxy-to-histology calibration; an examiner or a court can attack enablement/written description for the composition inference.

Three survival conditions:
1. The first-pass timing constraint is real and neither A nor B teaches it (verify via Section 1 searches — if any patent claims intra-procedural clot sensing with outcome gating, the claim dies).
2. A validated, reproducible measurement protocol exists or is developed (proxy-to-histology calibration, inter-device reproducibility).
3. A retrospective or prospective dataset shows the score changes the continuation decision in a non-trivial fraction of cases beyond what TICI alone would dictate (incremental decision-flip rate, not just incremental AUC).

------------------------------------------------------------
SECTION 6: KILL DECISION RECOMMENDATION (NON-BINDING)
------------------------------------------------------------

Engineering assessment: CONDITIONAL SURVIVAL.

The axis as scoped by the scout ("post-hoc score at procedure completion") is weak: utility is largely duplicated by NIHSS/TICI/immediate CT, and obviousness risk is high because both halves of the combination are published. The narrow viable path is the intra-procedural variant: first-pass retrieved-clot physical signature -> pre-completion risk score -> gated continuation decision. This variant has a real utility hook (decision 4), a non-obviousness hook (timing + sensor integration), and an identifiability path that is achievable but requires standardization work (re-rated risk 3-4, not 2).

Conditions for survival:
1. Section 1 searches (all six vectors) return no patent claiming intra-procedural retrieved-clot sensing with outcome-gated continuation decisions. If any vector hits, the axis dies.
2. A measurement modality (optical/impedance/force) with a credible path to histology validation is identified within the team's hardware capability.
3. A clinical collaborator can provide paired first-pass clot samples + outcomes (n >= 100) to demonstrate incremental decision-flip rate over TICI.

If condition 1 fails on execution of the searches, recommend KILL. If conditions 2-3 cannot be resourced, the axis degrades to the post-hoc form and should be killed on utility grounds.

Strongest alternative explanation (Article XXXII): the reason no one has built this may not be an opportunity gap but that intra-procedural clot signatures carry no incremental information over TICI + pass count — the Section 1 literature search and a small paired dataset would falsify or confirm this before any patent spend.

— End of report. All patent numbers and several academic citations marked UNKNOWN pending execution of the specified search vectors; no fabricated references included.

---

## Reasoning (for audit)

Produce structured report, honest UNKNOWNs, real citations only where high confidence. Known real references: Nogueira et al. 2019 (HERMES, ML mRS prediction, Lancet Neurol? Actually Nogueira RG et al., "Prediction of functional outcome in patients with acute ischemic stroke treated with thrombectomy: a machine learning approach" — published in Stroke? It was presented; the paper: Nogueira et al., Stroke 2020? I recall "Machine learning prediction of functional outcome" — HERMES analysis, published in Stroke (2020?). I'll cite cautiously as Nogueira et al., HERMES ML mRS prediction, Stroke (verify). Retrieved clot histology: Liebeskind et al. on clot composition and stroke etiology; "clot histology" papers — Boeckh-Behrens et al. 2016 (PLOS ONE?) on thrombus histology and etiology; Fitzgerald et al. on clot composition and outcome. Marder et al. 2006 on clot structure. Simons et al. on RBC-rich clots and outcome. I'll cite with caution and mark verification level. Keep concise.
