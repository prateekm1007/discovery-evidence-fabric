# Protocol Changelog

All changes to `INVENTION_PROTOCOL_V<N>.md` are recorded here. Each entry traces to an approved Protocol Change Proposal (PCP).

## V1 — 2026-08-17
- Initial frozen constitution.
- Established 5 hard/soft gates (Patent 35%/≥70 non-compensable; Evidence 25%/≥70 non-compensable; Technical 15%/≥65; Engineering 15%/≥60; Commercial 10%/≥65).
- Established 18-stage pipeline from COMPANY CORPUS to ADJUDICATION.
- Established mandatory artifact folder structure (00_MANIFEST through 23_LESSONS_LEARNED + SHA256SUMS).
- Established 12 hard CI/preflight checks (Sections 9.1 through 9.12).
- Established domain-specific simulation slot with SIMULATION_DOMAIN registry.
- Established lessons-learned immutability (lessons inform V2, do not silently modify V1).
- Established portfolio discipline: 15 companies × 10 moat positions = 150 inventions.
- Established three terminal statuses: WOULD_NOT_PAY / WOULD_CONSIDER_WITH_MILESTONES / LEVEL_4_BUYER_READY.
- Established constitutional invariants that cannot be weakened by future versions.

CereVasc Invention #1 (V2) is the first invention adjudicated under V1. It passes all 16 mechanical preflight checks; final status: `WOULD_CONSIDER_WITH_MILESTONES` with 6 explicit milestones (PMA base status confirmation, live AI30 motivation analysis, OOPD pre-submission, ISO 10993 CNS-contact testing, IDE submission, chronic in vivo fouling patency demonstration).

## V1 — 2026-08-17 (preflight enforcement update)
- Added Section X.0 constitution hash-pin check to `protocol/preflight_check.py`.
- Check verifies: (1) `CONSTITUTION_REGISTRY.json` exists and is parseable, (2) `current_canonical_path` field present, (3) canonical constitution file exists at the pinned path, (4) SHA-256 matches `current_sha256`.
- Runs FIRST in `main()` before any per-invention check; result appears as top-level `constitution_check` field in `preflight_report.json`.
- A hash mismatch is a hard CI failure — the constitution was modified outside the Protocol Evolution Workflow (§14).
- CereVasc Invention #1 (V2) now passes 17 checks (16 invention-level + 1 constitution hash-pin).
- No change to V1 constitution content (hash unchanged: `8d75ca8fc17f031ffa3b8d7ea4a272b5114592bdd0476c3d95d8220171a389f8`). This is an enforcement update, not a protocol amendment.


## V1.1 — 2026-08-17T16:24:11.272507+00:00 (PCP-001 APPROVED)
- BELOW_BUYER_THRESHOLD added as 4th terminal status
- 4-concept separation formalized (PATENT_STATUS, ENGINEERING_STATUS, BUYER_SENTIMENT, BUYER_READINESS)
- Deterministic state machine enforced
- 103 three-state evidence enforced
- Retroactive inflation scanner is permanent CI gate
- Approved by: CEO
