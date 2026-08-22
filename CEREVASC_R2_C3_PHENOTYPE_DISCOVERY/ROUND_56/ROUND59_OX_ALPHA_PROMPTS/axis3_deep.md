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
