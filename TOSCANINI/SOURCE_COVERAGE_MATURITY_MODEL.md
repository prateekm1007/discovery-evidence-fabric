# SOURCE COVERAGE MATURITY MODEL — Toscanini

**Version:** 1.0.0
**Directive:** CEO 2026-08-30 — "First create a SOURCE COVERAGE MATURITY MODEL … Every source must be graded across those dimensions."
**Status:** RATIFIED INSTRUMENT (grades regenerate mechanically via `python3 -m discovery_fabric.source_registry.maturity`)
**Machine output:** `TOSCANINI/SOURCE_MATURITY_GRADES.json`
**Implementation:** `discovery_fabric/source_registry/maturity.py`

---

## 1. Why this model exists (the inconsistency it resolves)

The 2026-08-30 audit reported simultaneously:

- "13/13 evidence roles covered" — **true** (every authority role has ≥1 measured-LIVE source)
- "Toscanini is not general-purpose" — **also true**

The CEO correctly identified that these two statements can mislead unless the
audit distinguishes **role coverage** from **depth / quality / availability**.
A single weak source can technically "cover" a role while providing nothing
like world-class coverage. Binary coverage collapses eleven independent
properties of a source into one bit; this model refuses that collapse.

**Role coverage is now ONE dimension among ELEVEN.** A role is only as strong
as its live sources' depth vectors, and the engine is only as general as its
weakest cross-cutting dimension (geographic breadth, failure-domain breadth,
temporal span, relevance quality).

---

## 2. The eleven dimensions (CEO-specified)

| # | Dimension | Measures | Basis |
|---|-----------|----------|-------|
| 1 | `ROLE_COVERAGE` | Does the source demonstrably fulfill its declared authority roles (measured 7-step chain + real records)? | MEASURED |
| 2 | `SOURCE_DIVERSITY` | Structural independence of the underlying corpus vs other registered sources (overlap groups; aggregator status) | DECLARED |
| 3 | `LIVE_AVAILABILITY` | Measured health: LIVE / DEGRADED / UNAVAILABLE / NOT_INTEGRATED | MEASURED |
| 4 | `RECORD_VOLUME` | OK records in the hash-chained custody log | MEASURED |
| 5 | `FRESHNESS` | min(provider-declared cadence, pipeline last-success date) | MEASURED+DECLARED |
| 6 | `PRIMARY_SOURCE_AUTHORITY` | PRIMARY (issuer) / SECONDARY (repackager) | DECLARED |
| 7 | `QUERY_RELEVANCE` | Per-source relevance-adjudication quality | **UNMEASURED engine-wide (honest)** |
| 8 | `PROVENANCE_COMPLETENESS` | Custody fields (entry hash, payload hash, chain link) present on logged retrievals | MEASURED |
| 9 | `FAILURE_NEGATIVE_EVIDENCE_COVERAGE` | Failure-native / attempt-outcomes / mixed-undersampled / not-a-failure-source | DECLARED |
| 10 | `GEOGRAPHIC_COVERAGE` | Corpus reach: global / multi-region / single jurisdiction | DECLARED |
| 11 | `TEMPORAL_COVERAGE` | Declared historical span of the corpus | DECLARED |

### Scale

```
0            ABSENT_OR_BLOCKED
1            WEAK
2            ADEQUATE
3            STRONG
UNMEASURED   explicit unknown (Art. XXV) — never numeric, never averaged as 0
```

Every grade carries `{grade, basis, evidence, rationale}` — the basis tag
(`MEASURED` / `DECLARED` / `MEASURED+DECLARED` / `UNMEASURED`) is mandatory.
A `DECLARED` grade is a fact about the provider's stated policy or corpus
nature; a `MEASURED` grade is computed from the health report or the custody
log. **No grade is ever asserted without one of these bases.**

---

## 3. Band rules and their rationale (Art. XXVII — no invented thresholds)

### RECORD_VOLUME
```
0        zero OK records logged
1        1–19      probe-scale   (health checks only — never exercised at query scale)
2        20–199    query-scale   (used in real retrievals)
3        ≥200      campaign-scale (sustained multi-query use, e.g. L8 15-territory run)
```
*Rationale:* anchored on the measured usage distribution in the 969-entry
custody log — probe-scale, query-scale and campaign-scale are the three usage
patterns the engine has actually exhibited. Metered sources (PatentBear,
Lens) carry an explicit `metered_note`: their volume is **policy-capped, not
availability-capped** — the numeric grade stands (it is weak volume) with the
reason disclosed.

### FRESHNESS
`min(declared_cadence, measured_last_success)` where declared cadence
{daily|weekly|continuous}=3, {periodic|monthly|quarterly}=2, {annual|static}=1,
and pipeline last-success ≤7d=3 / ≤30d=2 / older=1. *Rationale:* a provider
that updates daily is unusable if our pipeline last pulled a month ago —
usable freshness is the minimum of the two.

### PROVENANCE_COMPLETENESS
3 = custody fields on **every** logged retrieval + health-chain
`provenance_stores`/`retrieval_log_stores` pass; 2 = ≥95%; 1 = below.
*Rationale:* Art. XII requires the chain to hold on every entry, not the
average entry. (Provider-error entries that log an error payload with no
records still degrade the grade — strictness is intentional.)

### LIVE_AVAILABILITY
LIVE=3, DEGRADED=1, UNAVAILABLE=0, NOT_INTEGRATED=0.
*Rationale:* DEGRADED=1 (not 2) because a rate/budget-limited source cannot
support campaign runs **today** — the CEO's OpenAlex-429 concern is exactly
this: a source that is nominally present but operationally unusable.

### SOURCE_DIVERSITY
3 = sole registered provider of its corpus; 2 = shares a corpus with other
registered sources (overlap group); 1 = aggregator repackaging upstream
corpora already reachable via primaries.
*Rationale:* the scientific layer leaning on five overlapping literature
aggregates is breadth-on-paper, not evidence independence (Art. XXI.7).
Overlap groups are declared in `maturity.py::OVERLAP_GROUPS`.

### ROLE_COVERAGE
3 = LIVE chain 7/7 **with real records**; 2 = LIVE chain 7/7 with a
definitive-zero probe (connector proven, role not yet exercised);
1 = DEGRADED; 0 = UNAVAILABLE/NOT_INTEGRATED.
*Rationale:* a connector that has never returned a record has not proven the
role — it has proven a route to the role.

### PRIMARY_SOURCE_AUTHORITY
PRIMARY=3 (issuer of record), SECONDARY=2. *Rationale:* engineering
credibility chains terminate at issuers (FDA, NIST, EPO), not repackagers.

### FAILURE_NEGATIVE_EVIDENCE_COVERAGE
3 = failure-native (exists to record failures: MAUDE, recalls);
2 = attempt-outcomes (records attempts incl. terminated/failed: trial registries);
1 = mixed-undersampled (literature/patents: publication & grant bias);
0 = no failure semantics (identity, standards, property data).
*Rationale:* the CEO's negative-evidence directive — "what was tried and
failed" — needs sources whose *purpose* is failure recording.

### GEOGRAPHIC_COVERAGE
3 = global corpus or universal reference data; 2 = multi-region; 1 = single
jurisdiction. *Rationale:* FDA corpora are authoritative **for the US
market** — they cannot evidence EU reality; the audit showed EU regulatory
reality has zero live coverage.

### TEMPORAL_COVERAGE
3 = declared span ≥40y (e.g. MAUDE 1976–present); 2 = ≥20y; 1 = <20y;
UNMEASURED where the registry declares no span. *Rationale:* invention-grade
prior-art reasoning needs decades of lookback; the number is only graded
where the provider itself declares the span — never guessed.

### QUERY_RELEVANCE
**UNMEASURED for every source today.** Per-record relevance adjudication
(RELEVANT / IRRELEVANT_FILTERED with recorded basis) exists inside the
discovery pipeline (`discovery_modes/device_failure.py`), but nothing
aggregates those decisions per-source. Until that aggregation is built, no
relevance-quality claim is admissible. This is a declared machinery gap,
listed in §6.

---

## 4. Rollups

### Per-role depth (the CEO's central demand)
For each of the 13 authority roles:
```
covered_binary      — ≥1 measured-LIVE source serves the role (the old "13/13" bit)
live_sources        — which sources, with depth vectors
live_depth_mean     — mean numeric depth across serving live sources
depth_label         — WORLD_CLASS (≥2.5) / ADEQUATE (≥2.0) / WEAK (<2.0) / GAP_NO_LIVE_SOURCE
limiting_dimensions — the specific dimensions holding each live source below 3
```
*Band rationale:* a WORLD_CLASS role requires a primary, live,
provenance-complete source exercised at campaign scale on an independent
corpus — depth ≥2.5 means at most one non-3 dimension. The label bands are
assessment vocabulary (not kill criteria); they make "13/13 covered but not
world-class" mechanically visible.

### Engine-level cross-cutting findings
The model does not average away inconvenient structure (Art. XV). It states:
- **GEOGRAPHIC** distribution of live sources (12/27 single-jurisdiction;
  EU regulatory reality: zero live sources)
- **FAILURE domain breadth** — all failure-native live sources are
  MEDICAL-ONLY; non-medical failure evidence has zero live coverage
- **QUERY_RELEVANCE** — unmeasured engine-wide (machinery gap)
- **CONCENTRATION** — top-5 sources carry 81% of usage; the scientific layer
  leans on overlapping literature corpora

---

## 5. First graded output (2026-08-30, health run 2026-08-29T09:42Z)

41 sources graded; custody chain re-verified intact (969/969 recomputed).

| Role | Binary | Depth label | Live | Limiting fact |
|------|--------|-------------|------|---------------|
| ADVERSE_EVENT | ✅ | WORLD_CLASS | 1 (fda_maude) | US-only, medical-only, relevance unmeasured |
| RECALL | ✅ | WORLD_CLASS | 1 (fda_recall) | US-only, medical-only |
| CLINICAL | ✅ | WORLD_CLASS | 1 (clinicaltrials_gov) | US-run registry; failed-trial outcomes not yet mined |
| SCIENTIFIC | ✅ | ADEQUATE | 4 | openalex DEGRADED; overlap concentration; relevance unmeasured |
| PATENT | ✅ | ADEQUATE | 3 | uspto_odp parse bug; epo/wipo/bigquery blocked; metered quota |
| REGULATORY | ✅ | ADEQUATE | 4 | US-jurisdiction only (eudamed NOT_INTEGRATED) |
| MATERIALS | ✅ | ADEQUATE | 2 | materials_project UNAVAILABLE (403/IP); no calculated-properties depth |
| STANDARDS | ✅ | ADEQUATE | 2 | catalogue/summary metadata only — no full text |
| DEVICE_IDENTITY / COMMERCIAL | ✅ | ADEQUATE | 1 each | single-source, US-only |
| MANUFACTURING / BIOLOGY | ✅ | ADEQUATE | 3 each | derived/literature-based |
| CHEMISTRY | ✅ | ADEQUATE | 1 | pubchem probe-scale volume |

**The inconsistency is resolved, not papered over:** 13/13 binary coverage is
real, AND the depth vectors show why Toscanini is still not general-purpose —
single-jurisdiction regulatory reality, medical-only failure evidence,
unmeasured relevance quality, and degraded/overlapping scientific breadth.

---

## 6. What this model now demands (the to-do list it generates)

1. Close QUERY_RELEVANCE: persist per-source relevance-adjudication
   aggregation in the custody log → then measure it. (STILL OPEN.)
2. Rescue DEGRADED sources (OpenAlex 429, Semantic Scholar 429) before
   adding replacements (CEO directive 3). (DONE 2026-08-30: backoff +
   Retry-After policy, metered-protected; S2 recovered LIVE in isolation;
   OpenAlex honestly DEGRADED — provider daily-budget window.)
3. Resolve NOT_INTEGRATED/UNAVAILABLE with real retrievals — no integration
   claim without usable evidence (CEO directive 1). (DONE 2026-08-30:
   europepmc zero-hit parse bug fixed → LIVE; uspto_odp endpoint-retirement
   unmasked → honest credential-block; 32 LIVE now.)
4. Integrate free/open priority sources (NASA NTRS, DOE OSTI, arXiv, NHTSA,
   NTSB, EUDAMED, FDA De Novo) → their first graded act is their probe
   (CEO directive 2). (DONE 2026-08-30 for NTRS/OSTI/arXiv/NHTSA — LIVE;
   NTSB/EUDAMED/De Novo measured-blocked, honestly recorded.)
5. Cross-source identity/dedup + contradiction detection + negative-evidence
   architecture (CEO directives 4-5). (DONE 2026-08-30:
   entity_resolution.py + negative_evidence.py; live anchor verification
   EuropePMC+Crossref → one canonical entity; 146 negative-evidence records
   across medical+transport in the live demonstration.)
6. Re-run the model after every health run; the grades file is generated,
   never hand-edited (Art. X: registry + measurement are the authority).

---

## 7. Constitutional compliance

- **Art. XXV** — UNMEASURED is a first-class grade; never converted to 0.
- **Art. XXI** — coverage graded from measured retrieval, never registration.
- **Art. XXVII** — every band documented with rationale above.
- **Art. XV** — engine findings state the negative results verbatim.
- **Art. XII/XVI** — the custody chain is recomputed as part of grading
  (969/969 links verified), not assumed.
