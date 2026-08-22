# OX Alpha task: round61_batch3

- Timestamp: 2026-08-22T01:09:25.584100+00:00
- Model: stealth/ox-alpha
- Elapsed: 30.55s
- Finish reason: stop
- Usage: {"prompt_tokens": 5343, "completion_tokens": 1079, "total_tokens": 6422, "cost": 0, "is_byok": false, "prompt_tokens_details": {"cached_tokens": 64, "cache_write_tokens": 0, "audio_tokens": 0, "video_tokens": 0}, "cost_details": {"upstream_inference_cost": 0, "upstream_inference_prompt_cost": 0, "upstream_inference_completions_cost": 0}, "completion_tokens_details": {"reasoning_tokens": 0, "image_tokens": 0, "audio_tokens": 0}}

## User prompt

```
You are performing CE-014 prior art analysis for the CTO. This is BATCH 3 of 3 for Round 61 (closure of residual uncertainty from Round 60). The CTO must decide whether the 11 unanalyzed patents from vectors E and F contain any blocking prior art.

CANDIDATE CLAIM UNDER TEST:
A method for guiding endovascular stroke treatment comprising:
(a) during the procedure, measuring a physical signature of thrombus material
    retrieved in a first retrieval pass using a sensor integrated with the
    retrieval system;
(b) computing, from said signature together with intra-procedural procedural
    features (reperfusion grade, pass count, device trajectory), a calibrated
    risk score for symptomatic intracranial hemorrhage and 90-day functional
    outcome available before procedure completion;
(c) and gating a continuation/escalation decision — whether to perform
    additional retrieval passes or adjunct therapy — on said score.

BLOCKING TEST: A prior art patent BLOCKS the candidate if and only if its
claims (independently or in combination with another cited prior art under
KSR-style obviousness reasoning) read on ALL THREE elements (a), (b), (c)
of the candidate claim:

(a) INTRA-PROCEDURAL retrieved-clot PHYSICAL signature measurement
    — signal source must be a physical measurement of retrieved thrombus
      (NOT pre-procedural imaging; NOT post-procedural histology; NOT
      intra-procedural imaging of the vasculature without retrieved clot)
    — timing must be DURING the procedure (before procedure completion)

(b) Computing a risk score from said signature + intra-procedural procedural
    features (reperfusion grade, pass count, device trajectory) — for sICH
    AND/OR 90-day functional outcome

(c) Gating a CONTINUATION/ESCALATION decision on said score
    — decision must be whether to perform additional retrieval passes or
      adjunct therapy (NOT a pre-procedural treatment-selection decision;
      NOT a post-procedural triage decision; NOT a notification/workflow
      decision)

If a patent hits (a) and (b) but NOT (c), it is NON-BLOCKING.
If a patent hits (b) and (c) but uses a different signal source than (a),
it is NON-BLOCKING.
If a patent hits (a) and (c) but uses a different score computation than (b),
it is NON-BLOCKING.
Only if a patent hits ALL THREE (a)+(b)+(c) is it BLOCKING.

THE 3 PATENTS IN THIS BATCH:

===== PATENT 1: US9844387B2 (vector F) =====
Title: Intravascular treatment of vascular occlusion and associated devices, systems, and methods
URL: https://patents.google.com/patent/US9844387B2/en
Concern: F — Intravascular treatment of vascular occlusion
Abstract:
Abstract Systems and methods for treating thrombosis and or emboli in a peripheral vasculature of a patient are disclosed herein. The method can include providing a thrombus extraction device including a proximal self-expanding coring portion formed of a unitary fenestrated structure and a distal expandable tubular portion formed of a braided filament mesh structure; advancing a catheter constraining the thrombus extraction device through a vascular thrombus in a vessel; deploying the thrombus extraction device from the catheter from a constrained configuration to an expanded configuration; retracting the thrombus extraction device proximally so that the coring portion cores and separates a portion of the vascular thrombus from the venous vessel wall while the mesh structure captures the vascular thrombus portion; and withdrawing the thrombus extraction device from the patient to remove the vascular thrombus portion from the vessel.

Claims (extracted, may be truncated):
Claims ( 28 ) What is claimed is: 1. A method of treating deep vein thrombosis in a peripheral vasculature of a patient, the method comprising: providing a thrombus extraction device comprising a proximal self-expanding coring portion and a distal expandable tubular portion formed of a filament mesh structure, wherein the mesh structure filaments are interwoven with the coring portion so that a proximal end of the mesh structure is attached to a distal end of the coring portion; advancing a catheter constraining the thrombus extraction device through a vascular thrombus in a venous vessel, wherein an intermediate shaft slidably extends through the catheter and a distal end thereof is coupled to a proximal end of the coring portion, and wherein an inner shaft slidably extends through the intermediate shaft and a distal end thereof is coupled to a distal end of the mesh structure; deploying the thrombus extraction device from the catheter from a constrained configuration to an expanded configuration, wherein the thrombus extraction device in an expanded state engages at least a wall of the vessel distally past a portion of the vascular thrombus; retracting the thrombus extraction device proximally so that the coring portion cores and separates a portion of the vascular thrombus from the venous vessel wall while the mesh structure captures the vascular thrombus portion; and withdrawing the thrombus extraction device from the patient to remove the vascular thrombus portion from the venous vessel. 2. The method of claim 1 , wherein advancing the catheter comprises inserting the catheter into the venous vessel until a radiopaque distal tip of the catheter is distally past the vascular thrombus portion. 3. The method of claim 1 , wherein deploying the thrombus extraction device from the catheter from the constrained configuration to the expanded configuration comprises advancing the intermediate shaft distally until the coring portion of the thrombus extraction device is beyond a distal end of the catheter. 4. The method of claim 3 , wherein deploying the thrombus extraction device further comprises: locking the intermediate shaft with respect to the catheter; retracting the inner shaft with respect to the catheter and the intermediate shaft until a stop feature fixed on the inner shaft engages a corresponding feature on the coring portion slidably connected to the inner shaft for expansion of the thrombus extraction device, wherein the coring portion has a coring angle in a range between about 30 degrees and about 45 degrees when the thrombus extraction device is in the expanded state, wherein the coring portion maintains sufficient radial force on the venous vessel wall to core and separate the vascular thrombus portion in the expanded state; and dynamically coupling the inner shaft with respect to the intermediate shaft. 5. The method of claim 3 , wherein deploying the thrombus extraction device further comprises determining a position of the thrombus extraction device with respect to the catheter via imaging of a first radiopaque marker located on the catheter and a second radiopaque marker located on at least one of the intermediate shaft, the inner shaft, coring portion, or mesh structure. 6. The method of claim 1 , wherein the vascular thrombus portion is captured into the mesh structure by entering the expandable tubular portion via at least one proximal opening or aperture located at the proximal end of the self-expanding coring portion. 7. The method of claim 1 , further comprising inserting the catheter into the venous vessel through an access site, wherein the access site comprises a popliteal access site, a femoral access site, or an internal jugular access site. 8. The method of claim 1 , wherein the venous vessel has a diameter of at least 5 millimeters and comprises at least one of a femoral vein, an iliac vein, a popliteal vein, a posterior tibial vein, an anterior tibial vein, or a peroneal vein. 9. The method of claim 1 , further comprising: percutaneously accessing the venous vessel of the patient with an introducer sheath through an access site into the venous vessel of the patient; advancing a distal end of the introducer sheath to a position proximal of the vascular thrombus; deploying a self-expanding funnel on the distal end of the introducer sheath; and inserting the catheter through a lumen of the introducer sheath so that a distal tip of the catheter is distally past the vascular thrombus portion. 10. The method of claim 9 , wherein deploying the self-expanding funnel comprises: advancing an obturator having a capture sheath feature on a distal end thereof to unsheathe the self-expanding funnel from a constrained configuration within the capture sheath feature to a deployed configuration free of the capture sheath feature; and removing the obturator from the introducer sheath by retracting the obturator through the deployed self-expanding funnel and through the lumen of the introducer sheath. 11. The method of claim 9 , wherein withdrawing the thrombus extraction device from the patient comprises: retracting the thrombus extraction device relative to the introducer sheath until a proximal opening of the self-expanding coring portion is within the self-expanding funnel; collapsing the coring portion and mesh structure so as to restrain and/or compress the vascular thrombus portion therein; retracting the coring portion and mesh structure into the introducer sheath; and removing

------------------------------------------------------------

===== PATENT 2: WO2018210860A1 (vector E) =====
Title: Methods and pharmaceutical compositions for the treatment of acute ischemic stroke
URL: https://patents.google.com/patent/WO2018210860A1/en
Concern: E — Methods/pharmaceutical compositions for [NETs in retrieved thrombi] — mentions retrieved thrombi, KEEP for analysis even though pharma-titled
Abstract:
Abstract An easily administrable drug treatment to increase the recanalization rate associated with intravenously t-PA would represent a major advance in the acute ischemic stroke (AIS) management. The inventors demonstrate the presence of NETs network in intracranial thrombus extracted during AIS reperfusion procedures. Thrombi are encapsulated by these NETs network, which confer t-PA resistance. In fact, in presence of DNAse 1, t-PA-induced thrombolysisis accelerated, whereas DNAse alone is inefficient. These results suggest that a co- therapy associating t-PA and DNAse 1 may potentialize t-PA efficacy. Accordingly, the present invention relates to a method of treating an acute ischemic stroke (AIS) in a patient in need thereof comprising administering to the patient a therapeutically effective combination of t-PA and DNAse, wherein administration of the combination results in enhanced therapeutic efficacy relative to the administration of t-PA alone.

Claims (extracted, may be truncated):
Claims CLAIMS: 1. A combination comprising t-PA and DNAse for use in the treatment of AIS in a patient in need thereof. 2. The combination according to claim 1, wherein the t-PA is recombinant t-PA. 3. The combination according to claim 1 or claim 2, wherein the t-PA is a modified form of native t-PA that retain the enzymatic or fibrinolytic activities of native t-PA. 4. The combination according to any one of claims 1 to 3 wherein the t-PA is a modified form of native t-PA wherein Thrl03 of wild-type tPA is changed to Asn (T103N), Asn 117 of wild-type tPA is changed to Gin (N117Q), and Lys-His-Arg-Arg 296-299 of wild-type tPA is changed to Ala- Ala- Ala- Ala. 5. The combination according to any one of claims 1 to 4 wherein the t-PA is alteplase or tenecteplase. 6. The combination according to any one of claims 1 to 5 wherein the DNAse is DNAse 1. 7. The combination according to any one of claims 1 to 6 wherein the DNAse is recombinant. 8. The combination according to any one of claims 1 to 7 wherein the DNAse is of human origin. 9. The combination according to any one of claims 1 to 8 wherein the DNAse is Dornase or Pulmozyme. 10. A method of treating an acute ischemic stroke (AIS) in a patient in need thereof comprising administering to the patient a therapeutically effective combination of t-PA and DNAse, wherein administration of the combination results in enhanced therapeutic efficacy relative to the administration of t-PA alone. 11. A method for enhancing the potency of t-PA administered to a patient suffering from an AIS as part of a treatment regimen, the method comprising administering to the patient a pharmaceutically effective amount of t-PA in combination with DNAse. 12. A method of achieving recanalization of occluded intracranial arteries in a patient suffering from an AIS comprising administering to the patient a therapeutically effective combination of t-PA and recombinant DNAse. 13. The method according to any one of claims 10 to 12, wherein the t-PA is recombinant t-PA. 14. The method according to any one of claims 10 to 13, wherein the t-PA is a modified form of native t-PA that retain the enzymatic or fibrinolytic activities of native t-PA. 15. The method according to any one of claims 10 to 14, wherein the t-PA is a modified form of native t-PA wherein Thrl03 of wild-type tPA is changed to Asn (T103N), Asn 117 of wild-type tPA is changed to Gin (N117Q), and Lys-His-Arg-Arg 296-299 of wild-type tPA is changed to Ala- Ala- Ala- Ala. 16. The method according to any one of claims 10 to 15, wherein the t-PA is alteplase or tenecteplase. 17. The method according to any one of claims 10 to 16, wherein the DNAse is DNAse 1. 18. The method according to any one of claims 10 to 17, wherein the DNAse is recombinant. 19. The method according to any one of claims 10 to 18, wherein the DNAse is of human origin. 20. The method according to any one of claims 10 to 19, wherein the DNAse is Dornase or Pulmozyme

------------------------------------------------------------

===== PATENT 3: WO2020099386A1 (vector E) =====
Title: A thrombectomy system and methods of extracting a thrombus from a thrombus site in a blood vessel of a patient
URL: https://patents.google.com/patent/WO2020099386A1/en
Concern: E — A thrombectomy system and methods of extracting a thrombus — device claim, HIGH priority
Abstract:
Abstract A thrombectomy system and method of extraction of thrombus are disclosed. The thrombectomy system comprises a delivery catheter; an aspiration catheter, comprising an aspiration funnel, configured to be movably disposed within the delivery catheter in a retracted position and at least partially outside the delivery catheter in an extended and expanded position, the funnel comprising a non-permeable covering, the funnel being configured to adapt its shape and length to a surrounding blood vessel such that the funnel reduces blood flow through the blood vessel and lengthens as it narrows to retain a thrombus within the funnel; a clot-capture element configured to capture the thrombus and to be at least partially withdrawn with the captured thrombus into the funnel; and a microcatheter adapted to carry the clot-capture element to the thrombus. The clot-capture element is movably disposed within the microcatheter in a retracted position. The microcatheter is movably disposed withi

Claims (extracted, may be truncated):
Claims Claims 1. A thrombectomy system, comprising: a delivery catheter configured to be advanced through vasculature of a patient to a thrombus site within a blood vessel; an aspiration catheter adapted to apply suction to an expandable aspiration funnel extending from a distal end of the aspiration catheter, the aspiration funnel being configured to be movably disposed within the delivery catheter in a retracted position in a compressed state and at least partially outside the delivery catheter in an extended and expanded position, the aspiration funnel comprising a non-permeable covering, a diameter of a distal end of the aspiration funnel being greater in the extended and expanded position than in the retracted position, the aspiration funnel being configured to adapt its shape and length to an inner wall of the blood vessel such that the aspiration funnel reduces blood flow through the blood vessel and lengthens as it narrows to retain a thrombus within the aspiration funnel; a clot-capture element configured to capture the thrombus and to be at least partially withdrawn with the captured thrombus into the aspiration funnel; and a microcatheter adapted to carry the clot-capture element to the thrombus site, wherein the clot-capture element is configured to be movably disposed within the microcatheter in a retracted position, and wherein the microcatheter is configured to be movably disposed within the aspiration catheter. 2. The thrombectomy system according to claim 1 , wherein the delivery catheter, the aspiration funnel, the microcatheter and the clot-capture element are oriented on a same axis, are coaxially configured and movable to each other. 3. The thrombectomy system according to any of claims 1 -2, wherein the aspiration funnel is self-expandable. 4. The thrombectomy system according any of claims 1 -3, wherein the clot-capture element is a stent retriever device. 5. The thrombectomy system according to claim 4, wherein the stent retriever device has closed cells and a continuous scaffold. 6. The thrombectomy system according to any of claims 1 -5, wherein the aspiration funnel comprises a segment defining a distal end and a proximal end, wherein: the segment is formed by a mesh of at least two sets of helicoidal filaments turning respectively in opposite directions and being intertwined; the mesh comprises two distinct tubular sections, a first section and a second section, wherein the second section, adjacent to the first section, provides a reduction of diameter; and said mesh of the first section has helicoidal filaments with a braiding angle configured to provide outward radial forces higher than in the second section, such that the first section becomes appositioned against the inner wall of the blood vessel. 7. The thrombectomy system according to claim 6, wherein: the first section comprises closed loops at the distal end configured to act as a spring, such that the radial forces in a first and second end portions of the first section are higher than in an intermediate portion thereof. 8. The thrombectomy system according to any of claims 6-7, wherein the second section is comprised of two sub-sections, a first sub-section having a shape with a progressive reduction of diameter configured to open and create a space for the thrombus and to stop a proximal blood flow during the removal of the thrombus, and a second sub-section of a tubular uniform diameter configured to provide a connection to the aspiration catheter. 9. The thrombectomy system according to claim 8, wherein said shape of the first sub section is cone-shaped. 10. The thrombectomy system according to any of claims 6-9, wherein the two sets of helicoidal filaments are adapted to become more longitudinally aligned as the aspiration funnel lengthens and narrows. 1 1. The thrombectomy system according to any of claims 6-10, wherein the helicoidal filaments of the mesh are made of a metal, a metal alloy or a composite including Nitinol or Nitinol/Platinum. 12. The thrombectomy system according to any of claims 6-1 1 , wherein: the helicoidal filaments comprise a number ranging between 24 and 48, said filaments having a cross section comprised in a range between 40 and 60 pm; and the angle of the helicoidal filaments with regard to a longitudinal axis of the segment (10) is comprised between 50 and 65 degrees for the first section (20), and between 15 and 50 for the second sub-section (32). 13. The thrombectomy system according to any of claims 8-12, wherein: the first section comprises a length ranging between 4 and 40 millimeters and the second sub-section comprises a length ranging between 1 and 10 millimeters; the first section comprises an outer diameter ranging between 3.5 and 6 millimeters and the second sub-section comprises an outer diameter ranging between 1 and 2 millimeters; and the shape of the first sub-section comprises a generatrix with an angle comprised between 15 and 45 degrees with regard to a longitudinal axis of the segment. 14. The thrombectomy system according to any of the preceding claims, wherein the covering comprises a polymer including silicone or polyurethane. 15. A method of extracting a thrombus from a thrombus site in a blood vessel of a patient, the method comprising: advancing a delivery catheter through vasculature toward the thrombus site; placing a distal end of the delivery catheter proximal to the thrombus in the blood vessel; advancing an aspiration catheter within the deliver

------------------------------------------------------------

YOUR ANALYSIS — for EACH of the 3 patents, produce:

PATENT: <id>
  ELEMENT (a) hit? YES / NO / PARTIAL — quote claim language
  ELEMENT (b) hit? YES / NO / PARTIAL — quote claim language
  ELEMENT (c) hit? YES / NO / PARTIAL — quote claim language
  BLOCKING VERDICT: BLOCKING / NON-BLOCKING / BLOCKING-VIA-COMBINATION
  Rationale (1-2 sentences)

CONSTRAINTS:
- Quote ACTUAL claim language. Do NOT fabricate.
- If claims are truncated, mark INCONCLUSIVE.
- Be adversarial: try to find a blocking interpretation.

BATCH SUMMARY:
- BLOCKING count: X
- BLOCKING-VIA-COMBINATION count: Y
- NON-BLOCKING count: Z
- If any BLOCKING, list patent IDs.

Target ~600-1000 words.

```

## Response

PATENT: US9844387B2
  ELEMENT (a) hit? NO — Claims recite mechanical thrombectomy steps only. Closest language: "withdrawing the thrombus extraction device from the patient to remove the vascular thrombus portion from the venous vessel" (claim 1); imaging is limited to radiopaque marker position ("determining a position of the thrombus extraction device with respect to the catheter via imaging of a first radiopaque marker..." claim 5). No sensor measurement of retrieved thrombus physical signature; no signal source measuring clot properties.
  ELEMENT (b) hit? NO — No claim language computing any risk score, calibrated score, or outcome prediction. No mention of sICH, mRS/90-day outcome, pass count, or reperfusion grade in claims.
  ELEMENT (c) hit? NO — Claims are directed to DVT in peripheral venous vasculature (claim 1: "A method of treating deep vein thrombosis in a peripheral vasculature"), not intracranial stroke; no continuation/escalation gating decision appears.
  BLOCKING VERDICT: NON-BLOCKING
  Rationale: Pure mechanical extraction-device/method patent for peripheral DVT; no sensing of retrieved thrombus, no risk-score computation, no decision gating on any element (a), (b), or (c). Even adversarially, the radiopaque-marker imaging in claim 5 measures device position, not thrombus material.

PATENT: WO2018210860A1
  ELEMENT (a) hit? PARTIAL — The specification demonstrates "the presence of NETs network in intracranial thrombus extracted during AIS reperfusion procedures," i.e., analysis of retrieved thrombi during AIS procedures. However, no claim requires any intra-procedural measurement; claims are purely pharmaceutical. Adversarial reading: the described NETs analysis of extracted thrombi could be argued as a retrieved-clot physical/biochemical signature during the procedure — but it is a research finding enabling drug selection, not a claimed measurement step.
  ELEMENT (b) hit? NO — No claim computes a risk score for sICH or functional outcome. Claims recite only therapeutic efficacy enhancement: "administration of the combination results in enhanced therapeutic efficacy relative to the administration of t-PA alone" (claims 10-12).
  ELEMENT (c) hit? NO — Claims gate nothing intra-procedurally; they direct administration of t-PA + DNAse as treatment. There is no continuation-pass or adjunct-therapy escalation decision tied to any measured signature.
  BLOCKING VERDICT: NON-BLOCKING
  Rationale: Pharmaceutical combination patent (t-PA + DNAse). While its description touches retrieved-thrombus composition (NETs), it neither claims an intra-procedural signature measurement nor any risk-score computation or escalation gating. At most it is relevant background for adjunct-therapy selection, not blocking under the three-element test.

PATENT: WO2020099386A1
  ELEMENT (a) hit? NO — Claims recite mechanical capture and retention hardware: "an aspiration funnel comprising a non-permeable covering... configured to adapt its shape and length to an inner wall of the blood vessel such that the aspiration funnel reduces blood flow... and lengthens as it narrows to retain a thrombus within the aspiration funnel" (claim 1). No sensor, no physical-signature measurement of retrieved thrombus material anywhere in the extracted claims.
  ELEMENT (b) hit? NO — No risk-score computation, no sICH or 90-day outcome prediction, no procedural-feature inputs (reperfusion grade, pass count, trajectory) appear in claims.
  ELEMENT (c) hit? NO — Claim 15 method covers extraction mechanics ("advancing a delivery catheter through vasculature toward the thrombus site; placing a distal end of the delivery catheter proximal to the thrombus..."); no continuation/escalation decision gated on any measured quantity.
  BLOCKING VERDICT: NON-BLOCKING
  Rationale: Device/hardware patent for a funnel-based aspiration thrombectomy system. Despite HIGH priority flagging, none of the three elements is present in the claims. Note: claims beyond claim 15 were truncated — if later method claims contain sensing or decision logic, this would need re-review, but nothing in the abstract or provided claims suggests it.

BATCH SUMMARY:
- BLOCKING count: 0
- BLOCKING-VIA-COMBINATION count: 0
- NON-BLOCKING count: 3

No blocking prior art found in Batch 3. Strongest alternative explanation for residual risk: WO2018210860A1's description of retrieved-thrombus NETs analysis establishes that analyzing retrieved clot composition during AIS procedures was known pre-filing; combined with a separate patent claiming intra-procedural risk scoring and escalation logic (none identified in Batches 1-3 per prior rounds), a KSR combination argument would still require a missing middle element (b). Recommend closing Round 61 with zero blockers, subject to confirmation that truncated dependent claims of WO2020099386A1 contain no sensing/decision features.
