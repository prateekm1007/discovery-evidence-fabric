# OX Alpha task: round61_batch1

- Timestamp: 2026-08-22T01:08:35.212620+00:00
- Model: stealth/ox-alpha
- Elapsed: 21.29s
- Finish reason: stop
- Usage: {"prompt_tokens": 6448, "completion_tokens": 1182, "total_tokens": 7630, "cost": 0, "is_byok": false, "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "audio_tokens": 0, "video_tokens": 0}, "cost_details": {"upstream_inference_cost": 0, "upstream_inference_prompt_cost": 0, "upstream_inference_completions_cost": 0}, "completion_tokens_details": {"reasoning_tokens": 0, "image_tokens": 0, "audio_tokens": 0}}

## User prompt

```
You are performing CE-014 prior art analysis for the CTO. This is BATCH 1 of 3 for Round 61 (closure of residual uncertainty from Round 60). The CTO must decide whether the 11 unanalyzed patents from vectors E and F contain any blocking prior art.

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

THE 4 PATENTS IN THIS BATCH:

===== PATENT 1: US10226263B2 (vector F) =====
Title: Aspiration monitoring system and method
URL: https://patents.google.com/patent/US10226263B2/en
Concern: F — Aspiration monitoring system and method — MONITORING + aspiration, HIGH priority (could hit element a)
Abstract:
Abstract A system for removal of blood or thrombus includes an aspiration catheter having an elongate shaft including an aspiration lumen having proximal end configured to couple to a vacuum source, and a distal end having an orifice, an elongate member configured for placement through the aspiration lumen and having a distal portion including a disruption element configured to disrupt thrombus within the aspiration lumen, and a monitoring device configured for removable connection in between the aspiration catheter and the vacuum source, and including a housing, a pressure sensor in fluid communication with an interior of the housing, a measurement device coupled to the pressure sensor and configured for measuring deviations in fluid pressure, and a communication device coupled to the measurement device and configured to generate an alert signal when a deviation in fluid pressure measured by the measurement device exceeds a pre-set threshold.

Claims (extracted, may be truncated):
Claims ( 22 ) What is claimed is: 1. A system for removal of blood or thrombus comprising: a vacuum source; an aspiration catheter having an elongate shaft including an aspiration lumen having a proximal end and a distal end, the proximal end configured to couple to the vacuum source, the distal end having an orifice; an elongate member configured for placement through the aspiration lumen, the elongate member having a proximal portion configured to extend from the proximal end of the aspiration lumen; a rotating device configured to couple to the proximal portion of the elongate member, the rotating device comprising a body and a rotation element, the body configured to be gripped by a user and the rotational element configured to rotate the elongate member when the rotating device is coupled to the elongate member; and a self-contained monitoring device for real time monitoring of catheter aspiration, configured for removable connection in between the aspiration catheter and the vacuum source, comprising: a housing having a first port adapted for detachable connection to the vacuum source and a second port adapted for detachable connection with the aspiration catheter; a pressure sensor in fluid communication with an interior of the housing; a measurement device coupled to the pressure sensor and configured for measuring deviations in fluid pressure; and a communication device coupled to the measurement device and configured to generate an alert signal when a deviation in fluid pressure measured by the measurement device exceeds a pre-set threshold. 2. The system of claim 1 , wherein the elongate member is configured to macerate thrombus such that it can be aspirated through the aspiration lumen. 3. The system of claim 1 , wherein the elongate member is straight or substantially straight. 4. The system of claim 1 , wherein the elongate member has a wavy or undulating form. 5. The system of claim 1 , wherein the elongate member has a helical or spiral form. 6. The system of claim 5 , wherein the elongate member comprises a coil having a central axis. 7. The system of claim 6 , wherein the elongate member comprises a substantially straight shaft having a longitudinal axis and a distal end coupled to a proximal end of the coil, and wherein the central axis of the coil and the longitudinal axis of the substantially straight shaft are not co-linear. 8. The system of claim 7 , wherein the coil has an outer diameter, and wherein the longitudinal axis of the substantially straight shaft extends along a line closer to a circular projection of the outer diameter of the coil than the central axis of the coil. 9. The system of claim 8 , wherein the longitudinal axis of the substantially straight shaft extends along a line within the circular projection of the outer diameter of the coil. 10. The system of claim 1 , wherein the communication device is configured to generate a first type of alert in response to a deviation measured by the measurement device comprising one or more increases and decreases of vacuum pressure. 11. The system of claim 10 , wherein the first type of alert comprises at least one of an audible alert, a visible alert, and a tactile alert. 12. The system of claim 10 , wherein the communication device is configured to generate a second type of alert in response to the deviation comprising one or more increases and decreases of vacuum pressure no longer being measured by the measurement device. 13. The system of claim 1 , further comprising a memory module, wherein the measurement device is configured to compare measured deviations in pressure with information contained in the memory module. 14. The system of claim 1 , wherein the measurement device comprises a microprocessor. 15. The system of claim 1 , wherein the alert signal is configured to indicate a clogged condition. 16. The system of claim 1 , wherein the alert signal is configured to indicate a system leak. 17. The system of claim 1 , wherein the alert signal is configured to indicate thrombus being aspirated. 18. The system of claim 1 , wherein the alert signal is configured to indicate thrombus no longer being aspirated. 19. The system of claim 1 , wherein the alert signal is configured to indicate at least two of the states selected from the group consisting of a clogged condition, a system leak, thrombus being aspirated, and thrombus no longer being aspirated. 20. The system of claim 1 , wherein the elongate member is configured to guide a catheter through a portion of the vascular system of a subject. 21. The system of claim 20 , where the elongate member is configured to guide the aspiration catheter through the portion of the vascular system of the subject. 22. The system of claim 1 , wherein the elongate member is a guidewire.

------------------------------------------------------------

===== PATENT 2: US10743893B2 (vector F) =====
Title: Methods and systems for treatment of acute ischemic stroke
URL: https://patents.google.com/patent/US10743893B2/en
Concern: F — Methods and systems for treatment of acute ischemic stroke — mentions distal perfusion, HIGH priority
Abstract:
Abstract Described are methods and systems for transcervical access of the cerebral arterial vasculature and treatment of cerebral occlusions, including ischemic stroke. The methods and devices may include methods and devices which may provide aspiration and passive flow reversal, those which protect the cerebral penumbra during the procedure to minimize injury to brain, as well as distal catheters and devices to remove an occlusion. The methods and devices that provide passive flow reversal may also offer to the user a degree of flow control. Devices and methods which provide a way to securely close the access site in the carotid artery to avoid the potentially devastating consequences of a transcervical hematoma are also described.

Claims (extracted, may be truncated):
Claims ( 12 ) The invention claimed is: 1. A system for intracranial access through a patient's vasculature to access an intracranial occlusion, the system comprising: an inner member for steering and advancing through the patient's vasculature, the inner member having a distal tip region, a tapered section and a proximal section, wherein an axis of the inner member passes centrally through the proximal section, the tapered section, and at least partially through the distal tip region, wherein the proximal section, proximal to the distal tip region, has a cylindrical surface having an outer diameter greater than the distal tip region, wherein the proximal section is configured to advance the inner member through the vasculature, and wherein the proximal section, the tapered section, and the distal tip region have a passage therethrough configured for passage and relative movement of a wire; and a distal access catheter operatively connected to the inner member and wherein the distal access catheter has a distal inner diameter substantially corresponding to the outer diameter of the cylindrical surface, wherein the cylindrical surface of the inner member is maintained at least partially distal of a distal end of the catheter during advancement through the patient's vasculature, and wherein the inner diameter of the distal access catheter and the outer diameter of the cylindrical surface are sized to prevent coaxial separation between the inner member and the distal edge of the distal access catheter while being advanced through the curved vasculature and the cylindrical surface has a length to allow torsional and coaxial movements of the inner member relative to the distal access catheter while being advanced through curved vasculature without causing separation of the inner member from the distal inner diameter of the distal access catheter. 2. The system of claim 1 , wherein the inner member is composed of a flexible material. 3. The system of claim 1 , wherein the distal tip region and the tapered section are integral with each other. 4. The system of claim 1 , wherein the inner member can move coaxially relative to the distal access catheter. 5. The system of claim 1 , wherein the passage has a diameter between about 0.020 inches and 0.024 inches. 6. The system of claim 1 , wherein the passage has a diameter between about 0.030 inches and 0.040 inches. 7. The system of claim 1 , wherein the passage has a diameter between about 0.042 inches and 0.044 inches. 8. The system of claim 1 , further comprising a stent retriever disposed in the passage of the distal tip region. 9. The system of claim 1 , further comprising a radiopaque marker disposed at a distal end of the distal tip region. 10. The system of claim 9 , wherein the radiopaque marker is fabricated from a material selected from the group consisting of: platinum/iridium, tungsten, platinum, and tantalum-impregnated polymer. 11. The system of claim 1 , wherein the inner member is constructed with variable stiffness, wherein a distal segment of the inner member is constructed of a softer material with successively stiffer materials towards a proximal end of the inner member. 12. A method of accessing an intracranial occlusion through a patient's vasculature, the method comprising: advancing an inner member through the patient's vasculature, the inner member having a distal tip region, a tapered section, and a proximal section, the inner member having an axis passing centrally through the proximal section, the tapered section, and at least partially through the distal tip region, wherein the proximal section, proximal to the distal tapering surface has a cylindrical surface having an outer diameter greater than a diameter of the distal tip region, wherein the proximal section is configured to advance the inner member through the vasculature, wherein the proximal section, the tapered section, and the distal tip region have a passage therethrough configured for passage and relative movement of a wire, and wherein the inner member is operatively connected to a distal access catheter having a distal inner diameter substantially corresponding to the outer diameter of the cylindrical surface and wherein the distal access catheter can move coaxially relative to the cylindrical surface; maintaining the distal tapering surface partially outside of a distal end of the distal access catheter while being advanced through a curved portion of the patient's vasculature and while causing torsional and coaxial movements of the inner member relative to the distal access catheter, the distal inner diameter of the distal access catheter and the outer diameter of the cylindrical surface being sized and having a length to prevent separation between the inner member and a distal edge of the distal access catheter; and manipulating the inner member and distal access catheter through the patient's vasculature by a combination of torsional movements of the inner member and coaxial movements of the inner member relative to the distal access catheter to move the distal access catheter through regions of the patient's vasculature having a high tortuosity and without causing coaxial separation of the cylindrical surface from the distal inner diameter of the distal access catheter.

------------------------------------------------------------

===== PATENT 3: US10842498B2 (vector F) =====
Title: Systems and methods of restoring perfusion to a vessel
URL: https://patents.google.com/patent/US10842498B2/en
Concern: F — Systems and methods of restoring perfusion to a vessel — perfusion restoration, HIGH priority
Abstract:
Abstract Method for using a clot retrieval device for treating a clot in a blood vessel for use in the treatment of ischemic stroke to reperfuse an obstructed vessel.

Claims (extracted, may be truncated):
Claims ( 12 ) What is claimed is: 1. A method of restoring blood flow in neurovasculature by removing thrombus in human patients experiencing ischemic stroke, the method comprising: delivering a revascularization device to a blood vessel of a respective human patient of a plurality of human patients for retrieving a thrombus; and restoring perfusion to the blood vessel by passing the revascularization device by, through, or about the thrombus and removing the revascularization device to achieve approximately a 93% final revascularization rate under the modified treatment in cerebral infarction score of equal to or greater than a grade of 2 b (mTICI&gt;2b) for the plurality of human patients with one or more cerebral occlusions within a predetermined time period of natural stroke symptom onset. 2. The method of claim 1 , the revascularization device having a collapsed delivery configuration and an expanded deployed configuration, the revascularization device comprising: a framework of struts forming a porous inner body flow channel and having a tubular main body portion and a distal end; and a framework of struts forming an outer tubular body radially surrounding the tubular main body portion of the inner body during both the collapsed delivery configuration and the expanded deployed configuration. 3. The method of claim 1 , the revascularization device comprising: a shaft extending between a proximal end and a distal end; and a self-expandable outer body coupled to the shaft, the expandable outer body comprising a plurality of longitudinally spaced clot scaffolding segments separated by voids forming one or more clot inlet mouths between the adjacent clot scaffolding segments. 4. The method of claim 1 , wherein the thrombus is located in one of the following locations: a carotid artery, a M1 middle cerebral artery, a M2 middle cerebral artery, a basilar artery, and a vertebral artery. 5. The method of claim 1 , wherein the plurality of human patients comprise an outcome of a modified Rankin Scale of less than or equal to 1, the method further comprising: achieving approximately a 51.5% final revascularization rate mTICI=3 in the blood vessel after three passes of the revascularization device by, through, or about the thrombus. 6. The method of claim 1 , further comprising: achieving approximately a 52% revascularization rate mTICI≥2b after one pass of the revascularization device by, through, or about the thrombus. 7. The method of claim 1 , further comprising: achieving approximately a 76% final revascularization rate mTICI≥2c in the blood vessel after procedure completion with the revascularization device by, through, or about the thrombus. 8. The method of claim 1 , further comprising: restoring perfusion to the blood vessel by passing the revascularization device by, through, or about a clot of the blood vessel with an outcome for the plurality of human patients with the one or more cerebral occlusions within approximately a predetermined time period of natural stroke symptom onset of approximately 67%, the outcome being a modified Rankin Scale (mRS) of 0-2. 9. The method of claim 8 , further comprising: measuring the outcome of approximately 67% at 90-days following restoring perfusion to the blood vessel. 10. The method of claim 8 , the revascularization device comprising: an inner tubular body having a plurality of openings, a collapsed delivery configuration, and an expanded deployed configuration; and an outer tubular body at least partially overlying the inner tubular body and having a plurality of closed cell. 11. The method according to claim 1 , further comprising: achieving a final complete revascularization rate mTICI=3 in the blood vessel after three passes of the clot retrieval device by, through, or about the clot resulting in approximately a 10% clinical improvement from closest comparable clinical data. 12. The method according to claim 1 , inclusion criteria for the human patients comprises being aged between 18 years and 85 years; prestroke modified Rankin Scale (mRS)≤2; baseline National Institutes of Health stroke scale (NIHSS) score≥8 and ≤25; Alberta Stroke Program early computed tomography (ASPECT) score≥6; core infarct volume&lt;50 mL on magnetic resonance imaging or computed tomography based imaging (for anterior circulation strokes); and angiographic confirmation of an occlusion of an Internal Carotid Artery, M1 or M2 Middle Cerebral Artery, vertebral artery, or basilar artery with mTICI flow of 0-1.

------------------------------------------------------------

===== PATENT 4: US11185664B2 (vector F) =====
Title: Rapid aspiration thrombectomy system and method
URL: https://patents.google.com/patent/US11185664B2/en
Concern: F — Rapid aspiration thrombectomy system and method
Abstract:
Abstract An intravascular access system for facilitation of intraluminal medical procedures within the neurovasculature through an access sheath. The system includes an aspiration or support catheter having a flexible, distal luminal portion having an inner diameter defining a lumen extending between a proximal opening at a proximal end of the luminal portion and a distal opening at a distal end of the luminal portion. The catheter has a rigid spine coupled to at least the proximal end of the luminal portion and extending proximally therefrom. The system includes a dilator having a flexible, distal dilator portion sized to be received within the lumen of the luminal portion. Associated systems, devices, and methods of use are also described.

Claims (extracted, may be truncated):
Claims ( 26 ) What is claimed is: 1. A method of performing a medical procedure at a treatment site in a cerebral vessel of a patient, the method comprising: assembling a coaxial system of devices, the coaxial system of devices comprising: a catheter having a catheter lumen and a distal end; and a flexible solid inner member extending through the catheter lumen, the inner member comprising a tapered distal end and at least one radiopaque marker, the solid inner member having no lumen, wherein the tapered distal end of the flexible solid inner member extends distal to the distal end of the catheter forming an assembled coaxial system of devices; and advancing the assembled coaxial system of devices together within a petrous portion of an internal carotid artery without a guidewire. 2. The method of claim 1 , further comprising removing the flexible solid inner member after the catheter is placed at or near the treatment site. 3. The method of claim 2 , further comprising advancing a treatment device into the catheter lumen so that the treatment device resides at or near the treatment site. 4. The method of claim 2 , further comprising removing occlusive material while applying a negative pressure to the catheter lumen to capture occlusive material at, within, or through the distal end of the catheter. 5. The method of claim 4 , wherein the step of removing occlusive material comprises: inserting a retrievable stent device through the catheter; capturing the occlusive material with the retrievable stent device; and removing the occlusive material and the retrievable stent device from the treatment site. 6. The method of claim 1 , wherein the cerebral vessel is an intracranial vessel and wherein the treatment site is an occlusion or a region near a face of an occlusion within the intracranial vessel. 7. The method of claim 1 , wherein the tapered distal end of the flexible solid inner member tapers distally from a first outer diameter to a second outer diameter that is smaller than the first outer diameter. 8. The method of claim 7 , wherein the tapered distal end of the flexible solid inner member tapers over a length between 1 cm and 3 cm. 9. The method of claim 7 , wherein a proximal portion extends proximally from the flexible solid inner member to outside the body of the patient. 10. The method of claim 9 , wherein the proximal portion has a third outer diameter that is smaller than the first outer diameter of the flexible solid inner member. 11. The method of claim 10 , wherein the proximal portion is a stiff wire or a hypotube. 12. The method of claim 10 , wherein the first outer diameter is between about 0.003″-about 0.010″ smaller than an inner diameter of the catheter lumen. 13. The method of claim 12 , wherein the inner diameter of the catheter lumen is between about 0.040″ to about 0.088″. 14. The method of claim 1 , wherein the catheter comprises a flexible distal portion and a proximal tether element extending proximally from a point of attachment near a proximal end of the flexible distal portion, the proximal tether element extending proximally to outside the body of the patient. 15. The method of claim 14 , wherein an outer diameter of the proximal tether element at the point of attachment is smaller than an outer diameter of the flexible distal portion at the point of attachment. 16. The method of claim 14 , wherein the proximal tether element has sufficient rigidity to push the catheter distally towards the treatment site. 17. The method of claim 14 , wherein the proximal tether element is solid or has a lumen. 18. The method of claim 14 , further comprising: introducing through an insertion site of the patient an arterial access device, the arterial access device comprising an elongate body sized and shaped to be introduced into a carotid artery, the elongate body defining an internal lumen and a distal end; and advancing the arterial access device into the carotid artery. 19. The method of claim 18 , wherein the step of advancing the assembled coaxial system of devices is performed after the arterial access device is advanced into the carotid artery and further comprises: inserting the assembled coaxial system of devices into the internal lumen of the elongate body; and advancing the assembled coaxial system of devices through the internal lumen until the distal end of the catheter is past the distal end of the arterial access device. 20. The method of claim 18 , wherein a length of the flexible distal portion is less than an insertable length of the arterial access device. 21. The method of claim 20 , wherein the insertable length of the arterial access device is between 80 cm and 120 cm and the length of the flexible distal portion is between 10 cm and 25 cm or between 25 cm and 50 cm. 22. The method of claim 1 , further comprising: locking the catheter and the flexible solid inner member into a fixed position relative to one another forming a locked assembly, wherein advancing the assembled coaxial system of devices comprises advancing the locked assembly. 23. The method of claim 22 , wherein locking the catheter and the flexible solid inner member comprises using a mechanical locking element or gripping the catheter and the flexible solid inner member by hand. 24. The method of claim 23 , wherein the mechanical locking element is configured to be placed in a locked configuration to maintain the fixed position and an unlocked configuration to allow for relative sliding. 25. Th

------------------------------------------------------------

YOUR ANALYSIS — for EACH of the 4 patents, produce:

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

## Response (content)

PATENT: US10226263B2 (Aspiration monitoring system and method)
  ELEMENT (a) hit? PARTIAL — Claim 1: "a pressure sensor in fluid communication with an interior of the housing; a measurement device coupled to the pressure sensor and configured for measuring deviations in fluid pressure"; Claim 17: "the alert signal is configured to indicate thrombus being aspirated." The pressure deviation is an indirect proxy for thrombus presence in the aspiration line, not a physical signature measurement of retrieved thrombus material itself (no compositional/mechanical property of the clot is measured). Timing is intra-procedural (real-time monitoring).
  ELEMENT (b) hit? NO — No claim language computes any risk score for sICH or 90-day functional outcome. Claims recite only threshold-based alert states ("exceeds a pre-set threshold"; "clogged condition, a system leak, thrombus being aspirated"). Claim 13 memory comparison is against stored reference data for state classification, not outcome prediction.
  ELEMENT (c) hit? NO — Output is an "alert signal" (audible/visible/tactile, claims 10-12). No claim gates additional retrieval passes or adjunct therapy on any score.
  BLOCKING VERDICT: NON-BLOCKING
  Rationale: Hits at most a weak version of (a) via indirect pressure proxy; fails (b) and (c) entirely. Even a KSR combination with a risk-scoring patent would need the scoring patent to supply both (b) and (c).

PATENT: US10743893B2 (Methods and systems for treatment of acute ischemic stroke)
  ELEMENT (a) hit? NO — Claims are purely mechanical access claims: "an inner member for steering and advancing through the patient's vasculature... a distal access catheter operatively connected to the inner member." No sensor, no thrombus measurement of any kind.
  ELEMENT (b) hit? NO — No claim language regarding risk scores, sICH, or 90-day outcomes.
  ELEMENT (c) hit? NO — Claims recite device advancement/manipulation only; no decision gating.
  BLOCKING VERDICT: NON-BLOCKING
  Rationale: Pure access-catheter hardware patent; zero overlap with any element of the candidate claim. The "distal perfusion" concern in the vector tag is not reflected in the extracted claims.

PATENT: US10842498B2 (Systems and methods of restoring perfusion to a vessel)
  ELEMENT (a) hit? NO — No measurement of retrieved thrombus. Claims recite "delivering a revascularization device... and restoring perfusion... by passing the revascularization device by, through, or about the thrombus." No sensor or physical signature.
  ELEMENT (b) hit? PARTIAL — Claims recite population-level outcome statistics: "achieving approximately a 67%... outcome being a modified Rankin Scale (mRS) of 0-2" (claim 8), "measuring the outcome of approximately 67% at 90-days" (claim 9), and pass-count/revascularization-rate correlations (claims 5-7). However, these are aggregate clinical-trial performance recitations for a cohort ("a plurality of human patients"), not computation of an individual patient's calibrated risk score from a measured signature plus intra-procedural features.
  ELEMENT (c) hit? NO — No claim gates a continuation/escalation decision (additional passes, adjunct therapy) on any score. Pass counts appear only as achieved performance statistics.
  BLOCKING VERDICT: NON-BLOCKING
  Rationale: The 90-day mRS and pass-count language superficially resembles element (b) vocabulary, but it is cohort-level device-performance claiming, not patient-specific risk computation, and element (c) is entirely absent.

PATENT: US11185664B2 (Rapid aspiration thrombectomy system and method)
  ELEMENT (a) hit? NO — Claims recite mechanical assembly and advancement: "assembling a coaxial system of devices... advancing the assembled coaxial system of devices together within a petrous portion of an internal carotid artery without a guidewire." No sensor or thrombus signature measurement. (Claims truncated at claim 25; remaining dependent claims are unlikely to introduce sensing given the independent claim scope, but strictly: INCONCLUSIVE for claims 26.)
  ELEMENT (b) hit? NO — No risk score, sICH, or functional outcome computation in extracted claims.
  ELEMENT (c) hit? NO — Claims recite thrombus removal steps (claims 4-5) but no decision gating on a score.
  BLOCKING VERDICT: NON-BLOCKING
  Rationale: Pure access/thrombectomy technique patent; no sensing, scoring, or decision-gating subject matter. Truncation caveat noted but immaterial to the verdict.

BATCH SUMMARY:
- BLOCKING count: 0
- BLOCKING-VIA-COMBINATION count: 0
- NON-BLOCKING count: 4

Note for the CTO: US10226263B2 is the only patent with any sensing content, and its pressure-deviation proxy is the closest thing to element (a) in this batch. It would only become relevant in a combination analysis if a separate prior art reference supplied both (b) and (c) — none in this batch does. Strongest alternative explanation for the vector-F flag: the abstract/keyword matching ("monitoring," "perfusion," "90-day") triggered on vocabulary that does not appear in the claims; the claims are device/mechanical in scope.

---

## Reasoning (for audit)

Straightforward analysis.
