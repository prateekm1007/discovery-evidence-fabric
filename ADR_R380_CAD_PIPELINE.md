# ADR R380 — 3D ENGINEERING DESIGN PIPELINE

**Status:** RATIFIED (CEO directive 2026-08-31)
**Scope:** `discovery_fabric/engine/cad_pipeline.py` + R379 mutation-loop integration + package THREE_D_DESIGN section + numerical-provenance audit extension
**Constitution:** v1.8.0 (Articles II, III, VI, XVIII, XXV, XXVII, XXVIII, XXXIV, XXXVIII)

## Context

R379 gave the engine a structured technical state, an evaluator contract, and
design-variable mutations. What it did not have was a *physical design*: the
mutation moved numbers in a state, and nothing ever built the geometry those
numbers describe. The CEO R380 directive closes exactly that gap:

> TECHNICAL STATE → PARAMETER MAP → PARAMETRIC 3D MODEL → STEP/STL/GLB
> DERIVATIVES → GEOMETRY VALIDATION → TECHNICAL EVALUATION → MUTATION →
> NEW 3D MODEL → RE-EVALUATION

with the constraint that the 3D layer stays **subordinate to the invention
engine** (evidence → mechanism → technical state → design → evaluation →
improvement), never a separate CAD product.

## Technology selection (measured, not assumed)

| Tool | Status in this environment | Decision |
|------|---------------------------|----------|
| **CadQuery 2.6.1 + OCP (OCCT)** | INSTALLED, verified live (solids, isValid, Volume, BBox, faces, STEP/STL/GLB/SVG export) | **PRIMARY** — engine kernel |
| build123d | NOT INSTALLED | evaluated (same OCCT kernel, alternative API — recorded; not required) |
| FreeCAD | NOT INSTALLED | secondary analysis path — future integration via its Python console protocol; not fabricated here |
| Blender | NOT INSTALLED | presentation only — out of engine scope by CEO directive |
| trimesh 4.11.1 | INSTALLED | **independent secondary verifier** (STL watertight) |

External research (web-searched, no architecture copied): CadQuery is the
parametric CAD scripting standard on OCCT with agent-friendly code generation
(arXiv 2505.06507 "Text-to-CadQuery"); gencad/STEP-LLM generate *parametric
command histories*, not meshes — confirming the source-of-truth principle.
The design here follows the constitution, not any external project.

## Decision 1 — the PARAMETRIC MODEL is the source of truth

A candidate's 3D design is a `parametric_model` spec section containing:

- `build_program` — a deterministic Python `build(p)` function producing
  named solids (the ONE authoritative definition)
- `parameter_map` — param_id → {value, unit, envelope, value_class,
  envelope_class} — every entry bound bidirectionally to the technical state
- carried context: objects, materials, operating conditions, constraints,
  measurable outputs, model_version, parent_candidate, mutation_provenance,
  source_evidence_provenance
- `model_id` = content hash of (program, params, template, version)

STEP/STL/GLB/SVG are **derived artifacts**: hashed (real sha256 of real
bytes), labeled `derivative_of: parametric_model:<id>`. Rebuilding with the
same definition reproduces the same model_id in any directory — exports
cannot change identity. G5b rejects any program that hardcodes a parameter
value (the parameter would silently stop driving the design).

## Decision 2 — the sandbox (Art. XVIII)

LLM-proposed build programs are **untrusted code**. Deterministic gates:

1. AST scan BEFORE execution: no imports, no dunder names, no
   `open/exec/eval/__import__/getattr/...`, no global/nonlocal
2. Restricted exec namespace: only `cq` (injected by trusted code), `math`,
   and a minimal builtin set
3. `build(p)` must return a non-empty dict of buildable solids

Engine-owned templates (version-controlled source, e.g. `dual_lumen_tube`)
run through the SAME gates — same trust boundary for every origin.

## Decision 3 — geometry validation MEASURES, never trusts (Art. II/III)

The validator never reads the parameter claims as geometry truth. It
measures the built solid through OCCT:

- **G1** isValid + positive volume + non-degenerate bbox
- **G1b** signed containment wall per nested cylinder face
  (`R − dist − r`); **negative = lumen breach** (discovered live: face
  face-distance cannot detect a breach because intersecting faces return 0
  and trimmed surfaces break the raw adaptor — fixed with
  `BRepAdaptor_Surface` + axis-position containment)
- **G2** STL watertight via **trimesh — an independent second verifier**
  (Art. III verifier separation; UNVERIFIABLE when no STL exists, never
  silently passed)
- **G3** impossible dimensions (finite, inside declared envelopes,
  non-degenerate envelope)
- **G4** declared constraints checked against MEASURED quantities
  (e.g. wall_thickness from `min_wall_thickness_mm`), UNVERIFIABLE where
  the geometry does not measure a matching quantity
- **G4b** measured-vs-claimed dimension agreement — catches a program that
  ignores a parameter; **both** cross-section sides checked (a breach
  shrinks one side only)
- **G5** parameter map ↔ program usage bidirectional (dangling + unused)
- **G5b** hardcoded literal scan (source-of-truth)
- **G6** every declared object built
- **G7** declared interference pairs measured (intersect volume)
- **G8** slenderness/assumption checks where detectable, else UNVERIFIABLE

`render_is_not_validation` is a structural field on every report: renders
can never set or imply technical validity (CEO: "a beautiful render is NOT
engineering validation"). All measurements are COMPUTATIONAL_RESULT (rank 4)
with computation logs naming the kernel calls.

## Decision 4 — the warrants gate (never forced 3D)

`GEOMETRY_WARRANTS_3D`: a candidate warrants a 3D model only when its
technical state declares objects AND bounded length-like geometry variables.
Everything else gets an honest `NOT_APPLICABLE` with measured reasons —
methods/compositions/protocols are never decorated with 3D.

## Decision 5 — mutation integration (the CEO's example, verbatim)

R379 gates extended (additive, nothing weakened):

- **T10** (validate): a PARAMETER/GEOMETRY mutation on a model-bound
  parameter must REBUILD into valid geometry (dry-run, no exports) BEFORE a
  child exists. Measured on the built solid; a numerically-legal mutation
  that produces an unbuildable design is not defensible.
- **apply**: the child's model is rebuilt from the definition with the new
  value (derivatives never inherited), exported when `cad_out_dir` is
  configured, re-validated, attached to the child spec; `cad_rebuild` block
  on the mutation record with before/after model ids.
- **K7** (keep gate): the child's OWN rebuilt model must pass geometry
  validation.
- **KILLED_GEOMETRY_INVALID** ledger outcome: every proposal in an
  iteration died at T10 — the improving directions are geometrically
  unbuildable at this design point.
- **K2 refinement**: UNVERIFIABLE→SATISFIED constraint transitions accept a
  second legitimate evidence form: the child's own **geometry-measured**
  value (valid child geometry + computation log). MODELLED-only
  satisfaction remains laundering (Art. XXV). State-only candidates are
  unaffected.

## Decision 6 — evaluator consumes measured geometry (the loop order)

`evaluate_candidate_technically` now reads the spec's validated parametric
model: constraint targets whose STATE value is UNKNOWN but whose quantity is
MEASURED on the built solid are checked against the measurement, declared
`value_source: GEOMETRY_MEASURED_ON_BUILT_SOLID`, evidence class
COMPUTATIONAL_RESULT, with a note that the state's own value stays UNKNOWN
(no write-back — Art. XXVIII). This implements the CEO loop order
(GEOMETRY VALIDATION → TECHNICAL EVALUATION) and unblocks the fail-closed
R379 constraint wall *only when the geometry actually measures the quantity*.

## Decision 7 — package requirement (10 items)

`build_three_d_section` emits `THREE_D_DESIGN/` only when the spec carries a
VALIDATED model: PARAMETRIC_MODEL_SOURCE.py, STEP/STL/GLB, view SVGs,
KEY_DIMENSIONS.json (measured + computation logs),
GEOMETRY_VALIDATION_REPORT.json, PARAMETER_MANIFEST.json,
DESIGN_LINEAGE.json (parent/child ids, mutation provenance, evidence
provenance), TECHNICAL_EVALUATION_RESULT.json, README.json with the
explicit COMPUTATIONAL_RESULT vs physical-evidence distinction (physical
evidence: NONE — Art. XXXVIII). The zip packs recursively.

## Decision 8 — the audit closes the laundering path

`numerical_provenance.py` audits the parametric_model section at the same
hardness as every other numeric site: section class must be
COMPUTATIONAL_RESULT; parameter values need EXTRACTED-span or MODELLED
class; measured quantities need computation logs (invented measurement =
NAKED_NUMBER); derived artifact sha256 re-verified on disk (SOURCE_MISMATCH
on drift).

## Measured results (live, R380_LIVE_DEMO)

- Dual-lumen CSF shunt: state admitted (6 params, 2 constraints, 1
  objective, 2 relations, 3 objects) → model built and validated
  (pm:2af07223f0732735, kernel cadquery-occt 2.6.1, measured wall 0.4 mm,
  volume 164.93 mm³, bbox 3.0×3.0×30.0)
- CEO loop live: lumen 1.0 → 1.2 KEEP (wall 0.4 → 0.2 measured ≥ 0.15),
  second improvement 1.2 → 1.24 KEEP (wall 0.16), provenance chain
  [1.0→1.2, 1.2→1.24]
- Adversarial: 1.7 mm rejected at T10 — measured breach (wall −0.3), caught
  independently by G1b, G4, G4b
- 46 new adversarial hermetic tests; R379 suite unchanged (51 passed)

## Honest limitations (recorded, not hidden)

- FreeCAD integration path NOT implemented (not installed) — secondary
  analysis deferred; Blender presentation out of scope by directive
- G7/G8 are UNVERIFIABLE for single-object models without declared
  pairs/assumptions — honest, never defaulted to pass
- One engine template family (dual-lumen tube) exists; other geometries
  enter via the LLM build-program path through the same gates
- Liveness: the demo uses the deterministic template path with mocked
  untrusted proposals; production LLM transport is exercised by the same
  gates (Art. XVIII: the gates, not the proposer, are the trust boundary)
- All geometry is COMPUTATIONAL_RESULT; no physical observation exists
  anywhere in this pipeline (Art. XXXVIII — manufacture and measurement are
  the buyer's next step)
