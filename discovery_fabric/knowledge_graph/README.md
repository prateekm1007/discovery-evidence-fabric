# Knowledge Graph

First-class entities (CEO database-layer directive, implemented):
DEVICE, DEVICE_FAMILY, PREDICATE, REGULATORY_ACTION, RECALL,
ADVERSE_EVENT, CLINICAL_TRIAL, PATENT_FAMILY, PATENT_CLAIM, MATERIAL,
MANUFACTURING_PROCESS, STANDARD.

## Implemented (this build cycle)

- `entities.py` — entity construction from normalized source records with
  identity discipline: DEVICE identity by exact identifier only
  (udi_di > k_number > pma_number > name-only). FDA numbering prefixes
  (K = 510(k), P = PMA) resolve the same clearance referenced by MAUDE's
  `pma_pmn_number` and the 510(k) endpoint to the SAME device node.
  Name-only nodes carry `identity_status=UNRESOLVED_NAME_ONLY` and are
  NEVER silently merged (Art. XXI.6).
- `edges.py` — typed, evidence-bound edges: an edge exists only if a
  retrieved record measurably establishes it; every edge carries the
  custody reference (source_id, record_id, raw_payload_sha256).
- `graph.py` — store enforcing: evidence-bound edges, typed edges only,
  real endpoints only (no phantom adjacency), append-only custody.
- `lifters.py` — MAUDE → ADVERSE_EVENT + DEVICE + edge; recall → RECALL +
  DEVICE (via measured k_numbers); 510(k)/PMA → REGULATORY_ACTION +
  DEVICE; GUDID → DEVICE; ClinicalTrials → CLINICAL_TRIAL + DEVICE edge
  ONLY on exact intervention-name match (no fuzzy adjacency, Art. XXI.4);
  patents → PATENT_FAMILY.

Measured live build (pacemaker slice): 202 entities / 144 evidence-bound
edges / 0 rejected; 52 devices resolved by exact identifier, 13
name-only — the distinction is preserved, not papered over.

## Not yet integrated (honest gaps)

- PREDICATE entities require structured predicate fields no live source
  currently returns (the 510(k) endpoint carries none — see registry
  known_gaps); created only when a measured field carries the linkage.
- MATERIAL / MANUFACTURING_PROCESS / STANDARD entity lifters await live
  sources in those roles (registry records the gaps).
- PATENT_CLAIM entities require a patent source with claims access
  (Lens/PatSnap/EPO/USPTO — all currently UNAVAILABLE without
  credentials).
