# TOSCANINI — Database Coverage Audit (Founding Artifact)

**Directive:** CEO 2026-08-30 — "we are converting our pipeline into a general purpose Discovery and Invention engine. Its name is Toscanini."
**Constitutional basis:** Epistemic Constitution v1.8.0, re-read in full before this audit (Articles I–XXXVIII). Art. XXXIV explicitly sanctions this direction: *"Data acquisition (retrieve missing records, query new databases)"* is the mandated next action once computation has extracted all decisive information — the data layer is now the bottleneck, and this audit is the honest map of it.
**Scope:** Audit steps 1–5 (inventory, class coverage, blind spots, scoring, minimum set) + design assessment of steps 6–10 (normalized interface, provenance, reliability, dedup, contradiction). **No API integration work was performed** — per the directive, the audit comes first.
**Machine-readable companion:** `TOSCANINI/TOSCANINI_SOURCE_SCORECARD.json` (every score, status, and unblock path).

---

## 0. The True Numbers (Art. XV: whatever they are)

Measured, not claimed. Health re-probe run live during this audit session (2026-08-30) via the standard custody path.

| Number | Value | Basis |
|---|---|---|
| Sources registered in the custody registry | **41** | `source_registry/registry.py` |
| …with connectors implemented | **35** | registry `connector` field |
| Measured **LIVE** today | **28** | health report 2026-08-29 + live re-probe 2026-08-30 (europepmc recovered: UNAVAILABLE→LIVE, verified) |
| Measured **DEGRADED** | **2** | openalex (credit-budget 429, re-probed today — still failing), semantic_scholar |
| Measured **UNAVAILABLE** | **5** | epo_ops, uspto_odp, google_bigquery_patents (credentials); patsnap_eureka (subscription); materials_project (ASN block + no key) |
| Registered-only, **NOT_INTEGRATED** | **6** | astm_standards, iso_catalogue, eudamed, fda_denovo, who_ictrp, wipo_patentscope |
| Registry authority roles with ≥1 LIVE source | **13 / 13** | coverage matrix (role = COVERED iff ≥1 LIVE measured) |
| Custody retrieval-log entries | **969** | `retrieval_log.jsonl`, chain_valid = true |
| Usage concentration (top-5 sources) | **81% of all retrievals** | europepmc 366, lens_patent 155, google_patents 96, fda_recall 86, fda_maude 81 |
| Second, older provider layer (weak custody) | **~12 adapters** | `orchestrator/` (incl. NASA NTRS, OSTI, NIH RePORTER, Patentscope) — see §3 |
| Non-medical failure databases | **0** | grep-verified: no NTSB / NHTSA / EASA / industrial-incident source anywhere |
| Standards full-text sources | **0** | (metadata-only: eCFR + FDA-recognized-standards are LIVE; ISO/ASTM text paywalled) |
| Government technical reports in custody layer | **0** | NASA/OSTI exist only in the non-custody orchestrator layer |

**Of the CEO's 15 priority sources: 6 are already LIVE** (Lens, PubChem, NIST WebBook, ClinicalTrials.gov, the FDA set incl. MAUDE, AccessGUDID), **4 are built-but-blocked** (OpenAlex — budget; Materials Project — ASN+key; USPTO-ODP/EPO — credentials), **5 are absent from the custody layer** (NASA NTRS, DOE OSTI, ISO/ASTM full text, non-medical failure DBs, and — partially — EU regulatory via EUDAMED).

The honest one-sentence summary: **the medical vertical is world-class; the horizontal is not yet.** Calling Toscanini "general-purpose" today would violate Art. I (assertion ahead of evidence) — the class-coverage table below shows exactly which cells are empty.

---

## 1. Inventory (Audit step 1)

Two retrieval layers exist. Only the first is custody-grade.

**Layer 1 — the source registry (CEO database-layer directive, custody-grade).** 41 sources, 35 connectors, health-instrumented (`health.py` 7-step chain: connector → live request → parse → normalize → provenance store → retrieval-log store → health verdict), every retrieval logged with `raw_payload_sha256`, per-record `limitations[]`, 13 authority roles. This is the layer the SOURCE_HEALTH_REPORT measures. Full per-source status and score: see the scorecard JSON.

**Layer 2 — orchestrator adapters (older, partial custody).** `orchestrator/multi_source_discovery.py` (PubMed, ClinicalTrials, openFDA, NIH RePORTER, Crossref, NASA NTRS — the NTRS adapter is implemented but **unwired** into the four-search attack), `orchestrator/triangulation_engine.py` (adds OSTI, WIPO Patentscope scrape), `orchestrator/provider_capability_registry.py`, plus `prior_art_v2/` patent machinery with failover. NIH RePORTER and NASA/OSTI produce evidence only through this layer — which is exactly the architectural smell the audit must flag: **evidence that bypasses the custody registry violates the spirit of Art. XXI.9** (every search result must enter provenance custody). The R375 campaign envelopes show layer-2 sources (NIH RePORTER, openFDA raw calls) being cited per-run, logged more thinly than registry sources.

**Toscanini design consequence (step 6 preview):** unify on Layer 1's interface. Layer 2 adapters must either be promoted into registry connectors with full custody or retired. No third layer may be created.

---

## 2. Evidence-class coverage (Audit step 2)

Against the CEO's six classes:

| Class | LIVE custody sources | Verdict |
|---|---|---|
| **SCIENCE** — what people know | europepmc, pubmed, crossref, lens_scholarly, elsevier_scopus (openalex degraded, semantic_scholar degraded) | **COVERED** — but OpenAlex (CEO #1) is the strongest semantic-concept source and is budget-blocked |
| **TECHNOLOGY / patents** — what people claimed | lens_patent, google_patents, patentbear (metered) | **PARTIAL** — bibliographic breadth is fine; **claims text** hangs on a single metered source; USPTO-primary/EPO blocked on free credentials |
| **REAL-WORLD failures** — what breaks | fda_maude, fda_recall | **MEDICAL-ONLY** — the CEO's framing is exactly right: failure DBs are gold for discovering *unmet problems*; aviation/automotive/industrial/chemical = **0 sources** |
| **PHYSICAL TRUTH** — what is possible | nist_webbook, pubchem, cod_optimade, uniprot, chembl, rcsb_pdb | **COVERED for chem/bio**; DFT-computed materials (Materials Project) blocked |
| **STANDARDS** — what must be satisfied | fda_recognized_standards, ecfr_title21 | **PARTIAL** — which standards apply is LIVE; what they *require* (ISO/ASTM/IEC text) is paywalled and absent |
| **COMMERCIAL / REGULATORY reality** — what survived | fda_510k, fda_pma, fda_pma_supplements, fda_udi, fda_classification, fda_registrationlisting, gudid_commercial, gudid_sterilization | **US-ONLY, otherwise excellent** — EUDAMED (free API) not yet integrated |

---

## 3. Blind spots (Audit step 3)

Ranked by invention-value damage:

1. **Non-medical failure evidence = ZERO.** Toscanini's problem→mechanism pipeline starts from documented failure. Outside medicine it is blind. This is the single largest gap and the CEO's priority #14. (NHTSA recalls API and NTSB are both free.)
2. **Government technical reports = ZERO custody sources.** NASA NTRS + DOE OSTI hold decades of R&D including negative findings commercial literature under-reports. Adapters exist in layer 2 (NTRS even unwired) — the failure was custody, not code.
3. **Standards full text = ZERO.** The R375 campaign's decisive depth gaps were `engineering_specificity` and `manufacturing_reasoning`; standards requirement-text and manufacturing-change records (PMA supplements — already LIVE) are precisely the evidence class that feeds those floors. Free partial answer: NIST SP-series + FDA recognition lists; full answer needs a licensing decision.
4. **OpenAlex degraded.** The only semantic-concept engine in the fabric — finds prior art across terminology boundaries. Unblock is budget discipline/mailto registration, not code.
5. **Patent claims-text single-threaded.** PatentBear (metered) is the only claims source; Lens search results carry no claim text (measured). USPTO-ODP + EPO OPS keys are free registrations awaiting a CEO decision.
6. **EU commercial reality = ZERO.** EUDAMED is free and unconnected.
7. **Cross-source factual contradiction detection = machinery gap** (§6, step 10) — the queue exists, the comparator does not.

---

## 4. Scoring (Audit step 4)

Every current and proposed source scored **coverage × authority × machine-accessibility × licensing × freshness × invention-value** (1–5 per axis, totals in the JSON scorecard). Tier outcome:

- **T0 KEEP/RESTORE (30 sources):** everything LIVE today + openalex (restore) — the medical spine stays.
- **T1 ADD NOW (7, all free):** nasa_ntrs (promote existing adapter into custody), doe_osti, arxiv, nhtsa_recalls, ntsb, eudamed, fda_denovo.
- **T2 CEO DECISION (4):** uspto_odp key, epo_ops OAuth (both free registrations), materials_project key + unblocked egress (infrastructure), ISO/ASTM licensing (paid).
- **T3 DEFER (4):** bigquery-patents, patsnap, patentscope, who_ictrp — each redundant with a LIVE source; adding them now would be coverage theater (Art. XIX anti-gaming applies to infrastructure too: sources must earn their place by *invention value*, not count).

## 5. Minimum world-class set (Audit step 5)

Rule: **every class ≥2 independent LIVE custody sources; no single points of failure; nothing added that merely duplicates.** The set that satisfies it: the 28 LIVE + openalex restored + the 7 T1 adds + the 4 T2 decisions (3 of which are free). Result per class: SCIENCE 7, PATENTS 3→5, FAILURES 2→4, PHYSICAL 6→7, STANDARDS 2→3(+licensing), COMMERCIAL 7→9 (adds EU). Twelve of those actions are free; two are restorations needing zero code.

---

## 6. Machinery assessment (Audit steps 6–10, design — not yet built)

| CEO step | Exists today | Gap Toscanini must close |
|---|---|---|
| 6. One normalized evidence interface | EvidenceItem schema (27 fields, provenance required) + 35 connectors → SourceRecord | **Unify the two layers** — orchestrator curl-adapters must route through the registry or die; no third layer |
| 7. Provenance source→record→passage→claim→component | retrieval log (969 entries, chain-valid) + raw sha256 + span-exact a2 binding + dossier claim IDs | uniform component-level chain as a queryable index (pieces exist in dossier builders only) |
| 8. Source-specific reliability rules | MAUDE limitations constitutionally codified (Art. XXI.5) and on every record; per-connector `limitations[]` | a uniform **evidence-quality weight table per source class** (peer-reviewed ≠ preprint ≠ regulatory record ≠ user-submitted report) |
| 9. Dedup across databases | patent-number merge (federated_evidence) + typed identity dedup (evidence_identity: paper/patent/trial/fda_device/fda_event) | the two dedup engines are ununified; build ONE canonical-index (DOI / patent-number / K-number / NCT-id) in front of both |
| 10. Contradiction detection | ContradictionQueue preserves attack/verify/collision contradictions in every candidate envelope (never silently dropped) | **no cross-source factual comparator** (A says property X=5, B says X=8). Depends on step 9 entity resolution first. Largest machinery gap. |

**On MAUDE:** the CEO's warning — *"MAUDE is not ground truth; FDA itself warns reports can be incomplete, inaccurate, untimely, unverified, biased"* — is **already the constitution's Article XXI.5** with structured per-record metadata (`REPORT_COUNT` vs `MALFUNCTION/INJURY/DEATH`, `CAUSALITY_UNVERIFIED`, `INCIDENCE_UNKNOWN`) enforced on every MAUDE-derived result since the V16.1 violation was retracted. The evidence-quality-weighting request extends this principle to every source class; that is the right generalization and it will be implemented as machinery, not per-record prose.

---

## 7. Boundary with R376 (honest state disclosure)

The R376 release-path work from the previous session exists **uncommitted and incomplete**: its audit instrument FAILs against the shipped portfolio (defines a `RELEASE_GATE_CERTIFICATE` the current builder does not yet emit) and it breaks 3 test floors (`buyer_decision_completeness` 5/26, `section_coverage` 5/26) plus a ~25× slowdown of the a10 benchmark path. Per Art. XV/XXIV it has been **preserved, not destroyed and not merged**: branch `r376-wip-2026-08-30` (commit 264ec050, defects enumerated in the commit message). Main is back at clean, green `66376d37`. Completing R376 remains queued behind this audit; nothing in the Toscanini plan touches the release path until R376 is finished properly.

## 8. What Toscanini is NOT allowed to become

Per the constitution this audit inherits rather than overrides: adding a database is not adding evidence (Art. XXI.1); zero hits is not novelty (XXI.2); provider failure is not absence (XXI.3, enforced since R375); relevance is adjudicated per record (XXI.4); triangulation requires genuine independence (XXI.7); signals are hypotheses, not conclusions (XXI.8); and every retrieved record enters custody or it is noise (XXI.9). The federated-evidence-fabric diagram in the CEO directive maps cleanly onto this: it is the registry's role system made horizontal. The name **Toscanini** is hereby recorded as the engine's identity for the general-purpose conversion; renaming code namespaces is deferred until the minimum set (§5) is in, so that naming churn never races evidence work.
