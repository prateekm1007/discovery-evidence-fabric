# AUDIT.md — Discovery Evidence Fabric Forensic Audit

## Phase 0: Deep Forensic Audit

### Repository State
- **Repo:** prateekm1007/discovery-evidence-fabric
- **Files:** 10 source files (excluding .git)
- **Executable code:** 1 Python file (openalex/mapper.py)
- **Schemas:** 1 JSON schema (evidence_item_schema.json)
- **READMEs:** 7 (root + 6 subdirectories)

### Component Classification

| Component | Path | EXISTS | EXECUTABLE | USED | TESTED | VALIDATED | Classification |
|-----------|------|--------|------------|------|--------|-----------|----------------|
| EvidenceItem Schema | normalization/evidence_item_schema.json | YES | YES | YES | NO | NO | **KEEP** — canonical schema, needed for A2 |
| OpenAlex Mapper | connectors/openalex/mapper.py | YES | YES | YES | NO | NO | **KEEP** — working connector, needed for A2 retrieval |
| Connectors README | connectors/README.md | YES | N/A | N/A | N/A | N/A | **KEEP** — documentation |
| Knowledge Graph | knowledge_graph/README.md | YES (scaffolding only) | NO | NO | NO | NO | **UNPROVEN** — scaffolding, not implemented |
| Mechanism Extraction | mechanisms/README.md | YES (scaffolding only) | NO | NO | NO | NO | **QUARANTINE** — TEE-style mechanism extraction, negative signal from Task 7 |
| Discovery Modes | discovery_modes/README.md | YES (scaffolding only) | NO | NO | NO | NO | **QUARANTINE** — TEE-style discovery operators, not validated |
| Adversarial Review | adversarial_review/README.md | YES (scaffolding only) | NO | NO | NO | NO | **KEEP** — needed for A2 adversarial challenge step |
| Prior Art | prior_art/README.md | YES (scaffolding only) | NO | NO | NO | NO | **KEEP** — needed for A2 prior-art search step |
| Reports | reports/MILESTONE_10K_EVIDENCE_OBJECTS.md | YES | N/A | N/A | N/A | N/A | **KEEP** — historical record |

### Summary

| Classification | Count | Components |
|----------------|-------|------------|
| KEEP | 5 | EvidenceItem Schema, OpenAlex Mapper, Adversarial Review (scaffolding→implement), Prior Art (scaffolding→implement), Reports |
| QUARANTINE | 2 | Mechanism Extraction (TEE, negative signal), Discovery Modes (TEE operators) |
| UNPROVEN | 1 | Knowledge Graph (scaffolding, not implemented) |
| REMOVE | 0 | Nothing to remove — repo is minimal |
