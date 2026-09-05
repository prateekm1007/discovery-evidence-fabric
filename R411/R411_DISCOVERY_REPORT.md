# R411 — Autonomous Discovery of 5 High-Value Non-Medical Technologies

**Run:** r411:1788584836 | **Engine commit:** `bf89f095192e` | **Fabric:** RETRIEVAL_FABRIC_V2 | **Campaign:** R411-CAMPAIGN-V1

The engine moved search -> discovery -> mechanism -> evidence -> differentiation -> engineering -> adversarial attack -> decisive experiment -> transfer package -> buyer dossier for each selected technology. Physical observations: **0**. This is an experiment-ready portfolio, not a validated one.

## Discovery funnel

```text
Raw evidence records        390
  across 26 domains, 10 sources, 7 source families
Candidate mechanisms         550
  medical-excluded           8
  collision-rejected         142
  dedup-merged               0
Technology opportunities     400
  shortlisted (EIG/cost)     14
  prior-art searched         14
  engineering-gated          28
  attacked                   14
  attacker-killed            14
FINAL                        0/5
```

## Honest outcome: 0/5 technologies qualified

The pre-registered rule (s14) governs: the machine never fabricates a fifth. Every shortlisted candidate that died in the tournament died to a CONCRETE, BASIS-CITED attack — physics kills (laws misapplied at stated operating points), evidence kills (records that do not support the mechanism claims), prior-art kills (retrieved records teaching the same mechanism+intervention+effect). The attacker was calibrated first (2/2 known defects killed as expected; false-kill rate on known-good mechanisms honestly NOT_MEASURED — no known-good corpus exists pre-campaign). Each kill enters the MECHANISM_CEMETERY with its lesson, so future search is measurably different (Art. LI). This is a recorded result, not a pipeline failure: an engine whose adversarial stage cannot say NO is the failure mode the constitution exists to prevent.

## Mid-run corrections and instrument disclosures

**Review provenance (Art. LXVII):** every attack verdict, calibration result, and adjudication in this run is `AI_REVIEW`. No human or external-organization review exists anywhere in this campaign — the volume of AI-on-AI review does not substitute for independent human or institutional review.

All corrections are transport- or defect-class, disclosed in the run record with their rationale; none lowered any frozen threshold, gate, or floor:

- **parser_fix_note:** F2 re-run: extraction parser could not find blocks without END CANDIDATE markers (infrastructure defect, not a scientific result — the two zero-candidate domains were reset and re-extracted after the fix)
- **evidence_subset_extension_reason:** the frozen 18-id subset (composite-ranked budget allocation) yielded an eligible set concentrated in 3 domain families while 14 domains received zero verification budget; the correction measures ALL candidates with the same instrument — the floor, anchors, and span gate are unchanged
- **llm_transport_pin:** pin=ENGINE_LLM_PROVIDER=openrouter; model_override=OPENROUTER_MODEL=minimax/minimax-m3:free; epistemic_class=transport_only; recorded_at=2026-09-05T11:25:28Z — reason: owner directive 2026-09-05 'try free models' (OpenRouter free-model collection, key via .env.keys); incumbent transports unhealthy at resume (zai shared-upstream rate-limit; tokenrouter empty-content 30s); minimax-m3 live-measured 2.9s avg, 4/4 claim lines, 8/10 reference bindings vs glm-4-plus proposer; inkling 403 agentic-harnes
- **attack_transport_budget:** attack.py max_tokens 900 -> 2600 (2026-09-05): every live model measured finish=length at 900 (zero parseable VERDICT blocks, FINAL never reached) — an infrastructure defect; without the fix, truncated attacks would parse as verdict=INCOMPLETE with status=OK, which selection treats as not-killed — candidates would have passed WITHOUT real adversarial adjudication (a silent semantic promotion, Art. XXVIII). The fix makes the tournament actually run; surfaces/verdicts/final semantics untouched.
- **prior_art_transport_parallelization:** per-perspective fabric calls issued concurrently (identical queries/caps/storage; custody log under its module lock); forced by 113 s/call measured upstream latency x 7 calls x 14 candidates vs the sandbox per-invocation process lifetime
- **incomplete_requeue:** evidence-resolution transport failures leave done_ids and are re-attempted on later invocations (Art. LXI: INCOMPLETE is never a completed measurement); final state 400/400 OK
- **evidence-resolution instrument:** deterministic verbatim-span containment gate (frozen; casefold + whitespace-normalized). Proposer transports (untrusted, recorded per call): glm-4-plus (136 candidates, 0.936 span admission); z-ai/glm-5.3-free (23 candidates, 0.958 span admission); minimax/minimax-m3:free (241 candidates, 0.982 span admission)

## Selected technologies (0/5)

## Rejected candidates — the strongest deaths

The machine's discarded ideas, recorded so future discovery improves (the cemetery now carries them):

- **Porous Media Enhanced Heat Transfer** (`C-heat_exchanger-1~4`): KILLED. The single most dangerous surviving objection is the physics kill: Darcy's law as cited is invalid at the stated Re > 4000 operating point, and the realistic ΔP penalty for any porous insert t
- **Neural Network Based MPPT Control** (`C-power_electronics-6~2`): KILLED. The most dangerous surviving objection is the self-defeating evidence: the candidate's own cited IEEE Access 2023 record (doi:10.1109/access.2023.3291339) already implements the exact proposed
- **Pre-misalignment Bearing System** (`C-wind-2`): KILLED
- **Electrical Signature Analysis** (`C-wind-2~2`): KILLED. The single most dangerous surviving objection is prior_art: doi:10.1109/eic63069.2025.11123235 and doi:10.1109/eic63069.2025.11123384 directly teach electrical signature analysis for wind turb
- **Discontinuous PWM Loss Reduction** (`C-power_electronics-1`): KILLED. The most dangerous surviving objection is that the candidate's own Esw equation shows the absolute switching-loss benefit of DPWM is smallest precisely at the light loads (0.3-0.6 pu) where th
- **Data-Driven Thermal Prediction Model** (`C-data_center_thermal-1~2`): KILLED. The single most dangerous surviving objection is prior-art self-cancellation: the candidate's own evidence record [doi:10.1016/j.applthermaleng.2026.132277] is identical in mechanism, interven
- **Acoustic-Actuated Honeycomb Battery Cooling** (`C-batteries_ev-1`): KILLED
- **Acoustic-Actuated Honeycomb Battery Cooling** (`C-batteries_ev-1~3`): KILLED. The single most dangerous surviving objection is that the killer experiment conflates thermal uniformity (a geometric/ballast effect) with acoustic-streaming-driven convection, making the prop
- **Stochastic MRR Modeling** (`C-semiconductor_fab-7~4`): KILLED. The single most dangerous surviving objection is prior-art anticipation — six independent CMP records (notably doi:10.31274/etd-180810-313 and doi:10.1016/b978-0-12-821791-7.00099-x) already t
- **Adaptive Control Reactor Optimization** (`C-chemical_process-1~3`): KILLED. The single most dangerous surviving objection is that the equations provide no controller dynamics, so the claimed 40–70% waste reduction is mathematically ungrounded — the candidate cannot be
- **Cryogenic Cooling Enhancement** (`C-machining-1~4`): KILLED. The single most dangerous surviving objection is the boundary-condition inversion (Surface 6): the candidate's own stated materials (SS304, Ti-6Al-4V) contradict its own stated effectiveness r
- **Amino Acid-Mediated CO2 Conversion** (`C-carbon_capture-2~3`): KILLED. The single most dangerous surviving objection is the prior-art overlap: doi:10.1021/acs.energyfuels.5c04026 already teaches amino-acid-mediated CO2 conversion to solid carbonate at industrial 

*(Killed candidates also enter `MECHANISM_CEMETERY` with reusable lessons; quota/diversity rejections stay here only — a quota rejection is not a mechanism death.)*

## Buyer packages


None created: no technology survived the adversarial tournament, so no dossier was placed (the honest 0/5; s15's automatic placement runs for every SELECTED technology — with zero selected, zero are placed).

## Search-space report

- **Source diversity:** {"oa_journal_registry": 18, "biomedical_pubmed_line": 104, "doi_registrant_datacite": 45, "doi_registrant_crossref": 145, "repository_aggregator_core": 62, "scholarly_graph_s2": 6, "repository_aggregator_openaire": 10}
- **Document-type diversity:** {"PEER_REVIEWED": 167, "THESIS": 104, "UNKNOWN": 100, "CONFERENCE": 16, "PREPRINT": 2, "REPORT": 1}
- **Domain diversity:** 26 domains across 0 distinct final-technology domains
- **Cross-domain transfers:** 392 candidates carry an explicit cross-domain transition
- **Mechanism diversity (label-level):** 370
- **Candidate collision rate:** 0.0
- **Terminology recovery (anti-lock-in, s7):** 692 records were found ONLY by the non-forward perspectives/registers — the direct attack on the R409 measured frontier

## Reality boundary

```text
physical observations = 0 / 0
independent physical replication = 0
real buyers = 0
commercial transactions = 0
```

An experiment-ready package is never confused with physically validated technology (Art. XXXVIII).

## Stop condition (s23)

The machine has stopped. The next action for each technology, presented for the human owner's funding decision:

