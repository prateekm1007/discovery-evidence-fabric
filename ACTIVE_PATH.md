# ACTIVE_PATH.md — A2 Active Discovery Path

## The A2 Pipeline

```
PROBLEM (medical-device failure)
    ↓
STEP 1: RETRIEVE — search Europe PMC / OpenAlex for relevant evidence
    ↓
STEP 2: FREEZE — snapshot retrieved evidence with content hashes
    ↓
STEP 3: SYNTHESIZE — LLM generates candidate intervention from frozen evidence
    ↓
STEP 4: VERIFY EVIDENCE — every assertion must have source_id + source_hash + exact span
    ↓
STEP 5: PRIOR-ART SEARCH — search for existing solutions, never claim "nobody has done this"
    ↓
STEP 6: ADVERSARIAL CHALLENGE — attack mechanism, transfer, obviousness, feasibility
    ↓
STEP 7: EPISTEMIC CLASSIFICATION — assign state (OBSERVED → ... → INVENTION_CANDIDATE)
    ↓
OUTPUT: INVENTION_CANDIDATE | REJECTED | UNKNOWN
```

## What is NOT in the active path

- TEE mechanism extraction (QUARANTINED — Task 7 showed negative value)
- TEE mechanism abstraction (QUARANTINED)
- TEE cross-domain transfer engine (QUARANTINED)
- Knowledge graph construction (UNPROVEN — not implemented)
- Simulation (not yet authorized)
- Invention corpus generation (not yet authorized)

## Active Runtime Dependencies

1. `discovery_fabric/normalization/evidence_item_schema.json` — canonical evidence schema
2. `discovery_fabric/connectors/openalex/mapper.py` — OpenAlex → EvidenceItem mapper
3. `discovery_fabric/a2/run.py` — A2 runner (new)
4. `discovery_fabric/a2/retrieve.py` — Europe PMC retrieval (new)
5. `discovery_fabric/a2/synthesize.py` — LLM synthesis (new)
6. `discovery_fabric/a2/verify.py` — evidence verification (new)
7. `discovery_fabric/a2/prior_art.py` — prior-art search (new)
8. `discovery_fabric/a2/adversarial.py` — adversarial challenge (new)
9. `discovery_fabric/a2/classify.py` — epistemic classification (new)
