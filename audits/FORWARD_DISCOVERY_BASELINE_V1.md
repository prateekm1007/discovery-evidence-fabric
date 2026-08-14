# FORWARD DISCOVERY BASELINE V1 — Forensic Audit

## Date: 2026-08-15
## Commit: bff798cb3f5b96e88b91cae4b03dc93982895f1e

## Audit Summary

### discovery_fabric/a2/ — A2 Pipeline Modules

| Component | Path | Status | Assessment |
|-----------|------|--------|------------|
| retrieve.py | discovery_fabric/a2/retrieve.py | **KEEP** | Europe PMC search — functional, used in all prior A2 runs |
| synthesize.py | discovery_fabric/a2/synthesize.py | **KEEP (MODIFY)** | Uses OpenRouter/deepseek — needs update to use NVIDIA API for DeepSeek. Key is hardcoded — must move to env var. |
| verify.py | discovery_fabric/a2/verify.py | **KEEP** | Evidence verification — functional, span checking works |
| prior_art.py | discovery_fabric/a2/prior_art.py | **KEEP (MODIFY)** | Uses EuropePMC search — needs integration with frozen evaluator (mistral-large-latest) |
| adversarial.py | discovery_fabric/a2/adversarial.py | **KEEP (MODIFY)** | 8-dimension adversarial — needs update to 7 dimensions per spec, with dimension-specific evidence requirement |
| classify.py | discovery_fabric/a2/classify.py | **KEEP** | Prior-art state machine — frozen, 6/6 regression PASS |
| run.py | discovery_fabric/a2/run.py | **KEEP (MODIFY)** | Runner with 10-problem manifest — needs expansion to 100 problems |

### discovery_fabric/connectors/

| Component | Path | Status | Assessment |
|-----------|------|--------|------------|
| openalex/mapper.py | discovery_fabric/connectors/openalex/mapper.py | **KEEP** | OpenAlex → EvidenceItem mapper — functional |
| README.md | discovery_fabric/connectors/README.md | **KEEP** | Lists USPTO, EPO, WIPO as TODO — not yet implemented |

### discovery_fabric/quarantine/

| Component | Path | Status | Assessment |
|-----------|------|--------|------------|
| QUARANTINE_MANIFEST.json | discovery_fabric/quarantine/QUARANTINE_MANIFEST.json | **QUARANTINE** | TEE components — must not be reopened |

### discovery_fabric/normalization/

| Component | Path | Status | Assessment |
|-----------|------|--------|------------|
| evidence_item_schema.json | discovery_fabric/normalization/evidence_item_schema.json | **KEEP** | Canonical evidence schema |

### discovery_fabric/ (other)

| Component | Path | Status | Assessment |
|-----------|------|--------|------------|
| knowledge_graph/ | discovery_fabric/knowledge_graph/ | **UNPROVEN** | Scaffolding only, not implemented |
| mechanisms/ | discovery_fabric/mechanisms/ | **QUARANTINE** | TEE-style mechanism extraction |
| discovery_modes/ | discovery_fabric/discovery_modes/ | **QUARANTINE** | TEE-style discovery operators |
| adversarial_review/ | discovery_fabric/adversarial_review/ | **KEEP** | Scaffolding for adversarial review |
| prior_art/ | discovery_fabric/prior_art/ | **KEEP** | Scaffolding for prior-art search |
| reports/ | discovery_fabric/reports/ | **KEEP** | Historical reports |

### prior_art_forensic/ — Frozen Evaluator & Calibration Artifacts

| Component | Status | Assessment |
|-----------|--------|------------|
| evaluator_v1_frozen_strict.py (in scripts/) | **FROZEN** | mistral-large-latest, prompt_hash=70bb690572d1fec1, ontology=c8ae93b52fb2c09d |
| SEARCH_UNIVERSE_V1.json | **FROZEN** | Search universe for prior-art |
| PATENT_ORACLE_V3.json | **FROZEN** | Oracle for calibration |
| CALIBRATION_FINAL.json | **FROZEN** | CALIBRATION_PASS |
| HISTORICAL_RECOVERY_V1_1.json | **FROZEN** | Historical recovery complete |

### Tests

| Component | Status | Assessment |
|-----------|--------|------------|
| tests/test_a2_migration.py | **KEEP** | 11/11 tests PASS — must remain green |

## API Key Status

| Provider | Key Available | Status |
|----------|--------------|--------|
| NVIDIA API (DeepSeek) | nvapi-Eilsj... | **AVAILABLE** — deepseek-v4-flash-0731 verified working |
| Mistral API | UsFQXJw... | **AVAILABLE** — for frozen prior-art evaluator |
| OpenRouter | sk-or-v1-897... | **DEPLETED** (402) — not usable |
| z-ai CLI | (environment) | **AVAILABLE** — glm-4-plus for secondary |

## Required Modifications

1. **synthesize.py**: Switch from OpenRouter to NVIDIA API for DeepSeek. Move API key to environment variable.
2. **prior_art.py**: Integrate with frozen evaluator (mistral-large-latest via Mistral API).
3. **adversarial.py**: Update to 7 dimensions with dimension-specific evidence requirement.
4. **run.py**: Expand problem manifest from 10 to 100 problems.
5. **New**: Add simulation-readiness assessment module.

## Components to NOT Create (Reuse Existing)

- Evidence verification → use existing verify.py
- Prior-art state machine → use existing classify.py (frozen)
- Evidence schema → use existing evidence_item_schema.json
- OpenAlex connector → use existing mapper.py
