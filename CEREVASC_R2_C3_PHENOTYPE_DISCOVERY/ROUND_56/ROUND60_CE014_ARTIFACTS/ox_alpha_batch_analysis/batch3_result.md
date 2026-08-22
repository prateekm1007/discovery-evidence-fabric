# OX Alpha task: round60_batch3

- Timestamp: 2026-08-22T00:50:32.916792+00:00
- Model: stealth/ox-alpha
- Elapsed: 36.69s
- Finish reason: stop
- Usage: {"prompt_tokens": 5053, "completion_tokens": 1231, "total_tokens": 6284, "cost": 0, "is_byok": false, "prompt_tokens_details": {"cached_tokens": 576, "cache_write_tokens": 0, "audio_tokens": 0, "video_tokens": 0}, "cost_details": {"upstream_inference_cost": 0, "upstream_inference_prompt_cost": 0, "upstream_inference_completions_cost": 0}, "completion_tokens_details": {"reasoning_tokens": 0, "image_tokens": 0, "audio_tokens": 0}}

## User prompt

```
You are performing CE-014 prior art analysis for the CTO. This is BATCH 3 of 3. The CTO must decide whether to KILL or PROMOTE a Slot 5 candidate based on whether any of 9 fetched patents constitutes blocking prior art. This batch contains 3 patents.

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

Under KSR obviousness, a patent may ALSO be blocking if it would be obvious
to combine its teaching with another cited patent's teaching to produce all
three elements. Note this separately as "blocking-via-combination" if so.

THE 3 PATENTS IN THIS BATCH:

===== PATENT 1: WO2021108783A1 =====
Title: Methods and systems for assessing a vasculature
URL: https://patents.google.com/patent/WO2021108783A1/en
Original concern: HIGHEST — snippet says 'combines angiography and ML to quantitatively predict outcome at the time of treatment ... mechanical thrombectomy'. Direct timing match for candidate claim.
Abstract:
Abstract Methods and systems are provided for assessing a vasculature of an individual. In an embodiment of a method, one or more angiographic parametric imaging (API) maps of the vasculature are obtained, wherein each API map of the one or more API maps encodes a hemodynamic parameter. A state of the vasculature is determined using a machine-learning classifier applied to the one or more API maps.

Claims (extracted, may be truncated):
Claims What is claimed is: 1. A method for assessing a vasculature of an individual, comprising: obtaining one or more angiographic parametric imaging (API) maps of the vasculature, wherein each API map of the one or more API maps encodes a hemodynamic parameter; and determining a state of the vasculature using a machine-learning classifier applied to the one or more API maps. 2. The method of claim 1, wherein the machine-learning classifier is a convolutional neural network (CNN). 3. The method of claim 2, wherein the CNN comprises ensemble networks. 4. The method of claim 3, wherein a first network of the ensemble networks is trained using anterior-posterior API maps and a second network of the ensemble networks is trained using lateral API maps, and the state of the vasculature is determined using a combination of results from each network of the ensemble networks. 5. The method of claim 4, wherein the result of each network is weighted by a network coefficient. 6. The method of claim 1, wherein the machine-learning classifier is trained to determine an occlusion state of the vasculature. 7. The method of claim 1, wherein the machine-learning classifier is trained to determine a reperfusion state of the vasculature. 8. The method of claim 1, wherein the hemodynamic parameter is one or more of time to peak (TTP), mean transit time (MTT), time to arrival, peak height (PH), and/or area under the time- density curve (AUC). 9. The method of claim 1, further comprising normalizing the hemodynamic parameter to reduce injection variability. 10. The method of claim 1, further comprising correcting the one or more API maps to account for C-arm position to reduce foreshortening error. 11. The method of claim 1, wherein the received one or more API maps comprise a pre treatment API map and a post-treatment API map. 12. The method of claim 11, further comprising dividing the hemodynamic parameter of the post-treatment API map by the corresponding hemodynamic parameter of the pre-treatment normalized API map. 13. The method of claim 1, wherein the one or more API maps are obtained by generating each API map from a digital subtraction angiography (DSA) image sequence of the vasculature. 14. The method of claim 13, wherein generating each API map comprises temporally cropping the DSA image sequence to only include frames where contrast is shown in the capillary phase. 15. The method of claim 13, wherein generating each API map comprises spatially cropping the DSA image sequence to remove portions outside a region of interest. 16. The method of claim 13, wherein generating each API map comprises extracting a time density curve at each pixel of the DSA image sequence. 17. The method of claim 1, further comprising segmenting the one or more API maps using a CNN. 18. An image processing apparatus, comprising: a memory for storing one or more angiographic parameter imaging (API) maps of a vasculature, wherein each API map of the one or more API maps encodes a hemodynamic parameter; and a processor in electronic communication with the memory, and wherein the process is programmed to determine a state of the vasculature based on the one or more API maps stored in the memory, and wherein the processor determines the state of the vasculature using a machine-learning classifier. 19. The image processing apparatus of claim 18, wherein the processor is further programmed to obtain the one or more API maps and store the one or more API maps in the memory. 20. The image processing apparatus of claim 18, wherein the processor is further programmed to: obtain one or more digital subtraction angiography (DSA) image sequences; generate one or more API maps from the one or more DSA image sequences, wherein each API map corresponds to a DSA image sequence; and store the generated one or more API maps in the memory. 21. The image processing apparatus of claim 20, wherein the processor generates each API map by temporally cropping the DSA image sequence to only include frames where contrast is shown in a capillary phase. 22. The image processing apparatus of claim 20, wherein the processor generates each API map by spatially cropping each image of the DSA image sequence to remove portions outside a region of interest. 23. The image processing apparatus of claim 20, wherein the processor generates each API map by extracting a time density curve at each pixel of the DSA image sequence. 24. The image processing apparatus of claim 20, further comprising an imaging sensor in electronic communication with the processor, and wherein the processor is further programmed to generate the one or more DSA image sequences using the imaging sensor. 25. The image processing apparatus of claim 18, wherein the machine-learning classifier of the processor is trained to determine an occlusion state of a vasculature. 26. The image processing apparatus of claim 18, wherein the machine-learning classifier of the processor is trained to determine a reperfusion stat

------------------------------------------------------------

===== PATENT 2: WO2023133427A1 =====
Title: Stroke prediction multi-architecture stacked ensemble supermodel
URL: https://patents.google.com/patent/WO2023133427A1/en
Original concern: HIGH — RapidAI 'Stroke prediction multi-architecture stacked ensemble'.
Abstract:
Abstract Apparatus and associated methods relate to emergency stroke detection and classification. In an illustrative example, a stroke detection device may include an ensemble stroke classification model (ESCM). The ESCM may, for example, include class-specific model sets applicable for at least four classes of features, and a general model set applicable for all classes of features. Each model set, for example, may be stacked with multiple class-specific models for each of a corresponding group of architectures. The stroke detection device may, for example, extract predetermined features from a rolling window of a first predetermined duration of EEG data. The predetermined features are extracted and combined into a 1-D input vector. By applying the input vector, the stroke detection device may generate a binary stroke prediction result. Various embodiments may advantageously accurately predict whether a patient is experiencing a stroke within a finite time to assist an emergency serv

Claims (extracted, may be truncated):
Claims What is claimed is: 1. A stroke detection device (120) comprising: a data store (235) comprising a program of instructions, wherein the data store comprises: a feature extraction engine (130) configured to extract features from a rolling window of EEG data (125) to generate a 1-D input vector (135) of the extracted features (136); and, a classification engine (240) configured to apply the 1-D input vector to an ensemble stroke classification model (ESCM) (140); and, a processor (205) operably coupled to the data store such that, when the processor executes the program of instructions, the processor causes operations to be performed to automatically and accurately predict whether a patient is experiencing a stroke, the operations comprising: receive a finite time window of a first predetermined duration of EEG data from a monitoring device operably coupled to the patient; extract, by the feature extraction engine, at least four classes of features from the received EEG data; aggregate the extracted features into the 1-D input vector; apply the classification engine to the 1-D input vector such that the ESCM operates on the extracted features aggregated into the 1-D input vector; generate, by the ESCM, a binary stroke prediction (145); and, generate and transmit a prediction signal to a user interface device such that an indication of the binary stroke prediction is provided to a user, wherein: the ESCM comprises: a class-specific model set (165, 170, 175, 180) for each of the classes of features, each set comprising multiple class-specific models 28 for each of a corresponding group of architectures, each class-specific model configured to receive the 1-D input vector and operate on features of the corresponding class; and, a general model set (160) including multiple general models for each of a corresponding group of architectures, each general model configured to receive the 1-D input vector and operate on features of multiple of the classes; and, the binary stroke prediction is generated based on a predetermined weighted aggregation of an output of each of the class-specific models and each of the general models, such that a stroke prediction with an area under a receiver operating characteristic curve greater than 0.95 is determined in a finite time window of less than 10 minutes. 2. The stroke detection device of claim 1, further comprising the monitoring device, wherein the monitoring device comprises a headset configured to measure rolling windows of EEG data from the patient. 3. The stroke detection device of claim 2, wherein the headset further comprises a plurality of electrodes configured to measure EEG data from the patient, wherein a position of each of the plurality of electrodes correlates with a corresponding brain region. 4. The stroke detection device of claim 1, further comprising a feedback module configured to receive the prediction signal and transmit an alert when the binary stroke prediction indicates that a stroke is detected. 5. The stroke detection device of claim 1, wherein the binary stroke prediction comprises a prediction of a large vessel occlusion stroke, and wherein the SESCM is trained using historic large vessel occlusion stroke data. 6. The stroke detection device of claim 1, wherein each classification-specific model set is created by training N predetermined models until a predetermined criterion is reached, and selecting from the N models a predetermined M number of models (where M &lt; N) as the class-specific model set, wherein the M models having a closest result to a quality criterion. 7. The stroke detection device of claim 1, wherein the at least four classes comprise time series features, power spectrum density (PSD) features, quantitative EEG features, and brain symmetry features. 8. The stroke detection device of claim 1, wherein the corresponding group of architectures for each of the model sets comprise gradient boosted machine, deep neural network, and distributed random forest. The stroke detection device of claim 1, wherein the ESCM is trained by generating a training input set by randomly selecting a finite time window of the first predetermined duration from a training data of a second predetermined duration longer than first predetermined duration. The stroke detection device of claim 1, further comprising a user interface configured to receive a professional stroke prediction input indicating a human evaluation of a stroke prediction, wherein the binary stroke prediction is further generated based on the predetermined weighted aggregation including the professional stroke prediction input. 11. A computer program product (CPP) comprising a program of instructions tangibly embodied on a non-transitory computer readable medium wherein, when the instructions are executed on a processor (205), the processor causes stroke detection operations to be performed to automatically predict whether a patient is experiencing a stroke, the operations comprisi

------------------------------------------------------------

===== PATENT 3: WO2025017275A1 =====
Title: Determination of brain age using abnormality suppression
URL: https://patents.google.com/patent/WO2025017275A1/en
Original concern: MEDIUM — RapidAI 'Determination of brain age using abnormality suppression'.
Abstract:
Abstract A method and system that provides for the automated detection of abnormalities in subject brains from medical imagery of the subject brains, and then applies the known local brain age determination techniques to obtain a local brain age for different image blocks of the subject brain is described. The output from the automatic abnormality detection method and system is used to suppress or negate the output of the local brain age determination method and system, by causing the local brain ages that have been found for image blocks corresponding to subject brain regions for which an abnormality has been detected to be disregarded and/or discarded. Thus, by filtering the output of the local brain age detection method and system with the output of the method and system for automated detection of abnormalities, then only those local brain ages which relate to image blocks of the parts of the subject brain that are more structurally normal are output as local brain ages. Thus, using

Claims (extracted, may be truncated):
Claims Claims 1. A computer implemented method of determining brain age of brains with abnormalities using medical imaging, comprising: receiving medical imagery of a subject brain; detecting abnormal areas of the subject brain corresponding to disease or injury within the medical imagery; segmenting the medical imagery of the subject brain into a plurality of volumes; determining a separate brain age for at least a subset of the plurality of volumes; suppressing the brain age determination for a particular volume of the subject brain if the particular volume at least partially comprises detected abnormal areas; and providing for output the separate brain age determinations for those volumes for which the brain age determination has not been suppressed. 2. A method according to claim 1, wherein the brain age determination for a particular volume of the subject is suppressed if it comprises at least 90% of abnormal areas. 3. A method according to claim 1 or 2, wherein the brain age determination for a particular volume of the subject is suppressed if it comprises at least 50% of abnormal areas. 4. A method according to claims 1, 2, or 3, wherein the brain age determination for a particular volume of the subject is suppressed if it comprises at least 30% of abnormal areas. 5. A method according to any of claims 1 to 4, wherein the brain age determination for a particular volume of the subject is suppressed if it comprises at least 1 voxel of abnormal areas. 6. A method according to any of the preceding claims, and further comprising combining the separate brain age determinations for each volume that is not suppressed to give a unified brain age result; and providing the unified brain age result for output. 7. A method according to claim 6, wherein the combining comprises processing the separate brain age determinations into the unified brain age result using a statistical calculation. 8. A method according to claim 7, wherein the statistical calculation is one selected from the group comprising: i) an averaging calculation ; or ii) a clustering calculation. 9. A method according to any of the preceding claims, wherein the medical imaging comprises medical imaging obtained by any one of the following medical imaging modalities: i) Magnetic Resonance (MR) imaging; ii) Computerised Tomography (CT) imaging; and/or iii) ultrasound imaging. 10. A method according to any of the preceding claims, and further comprising outputting the separate non-suppressed brain age determinations, or the unified brain age result, as appropriate, by displaying the determinations or result on a display screen. 11. A computer program or suite of computer programs so arranged such that when executed by a computer system they cause the computer system to perform the method of any of the preceding claims. 12. A computer readable storage medium storing a computer program or at least one of the suite of computer programs according to claim 11. 13. A computer system, comprising: a processor; and a computer readable storage medium storing one or more computer readable programs which when executed by the processor cause the computer system to: receive medical imagery of a subject brain; detect abnormal areas of the subject brain corresponding to disease or injury within the medical imagery; segment the medical imagery of the subject brain into a plurality of volumes; determine a separate brain age for at least a subset of the plurality of volumes volume; suppress the brain age determination for a particular volume of the subject brain if the particular volume at least partially comprises detected abnormal areas; and provide for output the separate brain age determinations for those volumes for which the brain age determination has not been suppressed. 14. A system according to claim 13, wherein the brain age determination for a particular volume of the subject is suppressed if it comprises at least 1 voxel of abnormal areas. 15. A system according to any of claims 13 or 14, wherein the computer readable storage medium further stores one or more computer readable programs which when executed by the processor cause the computer system to combine the separate brain age determinations for each volume that is not suppressed to give a unified brain age result; and provide the unified brain age result for output. 16. A system according to claim 15, wherein the combining comprises processing the separate brain age determinations into the unified brain age result using a statistical calculation.

------------------------------------------------------------

YOUR ANALYSIS — for EACH of the 3 patents in this batch, produce this structured assessment:

PATENT: <id>
  ELEMENT (a) hit? YES / NO / PARTIAL — quote the claim language that supports this
  ELEMENT (b) hit? YES / NO / PARTIAL — quote the claim language that supports this
  ELEMENT (c) hit? YES / NO / PARTIAL — quote the claim language that supports this
  BLOCKING VERDICT: BLOCKING / NON-BLOCKING / BLOCKING-VIA-COMBINATION
  If BLOCKING or BLOCKING-VIA-COMBINATION: state the exact combination that produces all three elements
  If NON-BLOCKING: state which element(s) miss and why

CONSTRAINTS:
- Quote ACTUAL claim language from the patents above. Do NOT fabricate claim language.
- If the extracted claims are truncated or missing, state that explicitly and mark the assessment INCONCLUSIVE.
- Be adversarial: try to find a blocking interpretation. The CTO wants to KILL the candidate if any blocking prior art exists.
- Do NOT make the strategic KILL/PROMOTE decision — that is the CTO's role.

OUTPUT FORMAT: Plain text, no emojis, structured per patent. Target ~800-1200 words total for this batch.

```

## Response

PATENT: WO2021108783A1
  ELEMENT (a) hit? NO. The signal source is angiographic imaging of the vasculature, not a physical measurement of retrieved thrombus material. Claim 1: "obtaining one or more angiographic parametric imaging (API) maps of the vasculature, wherein each API map of the one or more API maps encodes a hemodynamic parameter." No claim language references a sensor integrated with a retrieval system or measurement of retrieved clot material. This is intra-procedural imaging of the vasculature — explicitly excluded by element (a)'s definition.
  ELEMENT (b) hit? PARTIAL. Claim 1: "determining a state of the vasculature using a machine-learning classifier applied to the one or more API maps"; claims 6-7 recite occlusion/reperfusion states; claim 11: "a pre treatment API map and a post-treatment API map" with claim 12 ratio computation. This computes a reperfusion state during/around treatment, but no claim language recites computing a calibrated risk score for sICH or 90-day functional outcome, and no procedural features (pass count, device trajectory) are inputs.
  ELEMENT (c) hit? NO. No claim language recites gating a continuation/escalation decision (additional passes, adjunct therapy). Claims are limited to "assessing a vasculature" / determining a state.
  BLOCKING VERDICT: NON-BLOCKING
  Misses: (a) entirely — signal source is vascular hemodynamic imaging, not retrieved-clot physical signature; (c) entirely — no continuation/escalation gating. Even under KSR combination, this patent supplies only an intra-procedural reperfusion-state computation; it does not teach retrieved-clot sensing or pass-continuation gating.

PATENT: WO2023133427A1
  ELEMENT (a) hit? NO. Signal source is EEG. Claim 1: "extract features from a rolling window of EEG data (125) to generate a 1-D input vector"; "receive a finite time window... of EEG data from a monitoring device operably coupled to the patient." No thrombus retrieval, no sensor on a retrieval system, no physical signature of clot material.
  ELEMENT (b) hit? NO. Output is stroke detection/classification, not sICH or functional outcome risk. Claim 1: "automatically and accurately predict whether a patient is experiencing a stroke"; claim 5: "prediction of a large vessel occlusion stroke."
  ELEMENT (c) hit? NO. Claim 4: "transmit an alert when the binary stroke prediction indicates that a stroke is detected" — a notification/workflow output, explicitly excluded from element (c).
  BLOCKING VERDICT: NON-BLOCKING
  Misses all three elements. No plausible KSR combination with the other two batch patents produces element (a): none of the three teaches measuring a physical signature of retrieved thrombus with a retrieval-system-integrated sensor.

PATENT: WO2025017275A1
  ELEMENT (a) hit? NO. Signal source is pre-/post-procedural medical imagery of the brain. Claim 1: "receiving medical imagery of a subject brain; detecting abnormal areas of the subject brain corresponding to disease or injury within the medical imagery." No retrieved thrombus, no integrated sensor, no intra-procedural timing tied to retrieval passes.
  ELEMENT (b) hit? NO. Output is brain age estimation. Claim 1: "determining a separate brain age for at least a subset of the plurality of volumes." Not an sICH or 90-day outcome risk score.
  ELEMENT (c) hit? NO. The only "gating" is suppression of brain-age outputs for abnormal volumes ("suppressing the brain age determination for a particular volume") — a computational filtering step, not a clinical continuation/escalation decision.
  BLOCKING VERDICT: NON-BLOCKING
  Misses all three elements.

BATCH SUMMARY:
- Zero patents in Batch 3 hit element (a). None measures a physical signature of retrieved thrombus via a retrieval-system-integrated sensor during the procedure.
- Zero patents hit element (c). None gates additional retrieval passes or adjunct therapy on a computed score.
- Blocking-via-combination: NOT FOUND within this batch. WO2021108783A1 is the closest (intra-procedural timing, ML-based state computation from procedural imaging), but combining it with the other two adds nothing toward retrieved-clot physical sensing or pass-gating. A combination would still require an unstated inventive step (clot-integrated sensing), so KSR obviousness does not close the gap on the record provided.

CAVEATS:
- Claims for all three patents were noted as possibly truncated. For WO2021108783A1, claims after 26 are cut off; dependent claims could theoretically add outcome-prediction or decision language, but independent claims 1 and 18 as extracted do not support elements (a) or (c), and dependent claims cannot broaden beyond them. Assessment stands as NON-BLOCKING on the extracted record; residual truncation risk is LOW but nonzero.
- Strongest alternative explanation for the original HIGH concern on WO2021108783A1: its marketing/description text about predicting outcome "at the time of treatment" may describe embodiments in the description rather than claims. If the CTO wants certainty, a description-level review of WO2021108783A1 is recommended before finalizing, since descriptions can serve as KSR-combination teaching even when claims miss. On claims alone, however, it is non-blocking.

Recommendation to CTO: no blocking prior art identified in Batch 3; decision on KILL/PROMOTE rests with the CTO, weighing this batch against Batches 1-2.
