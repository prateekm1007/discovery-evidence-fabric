# toscanini_bridge — Engine Integration Guide

## What this closes

**Diagnosed gap (2026-09-07, live acceptance run ts_fa94ec9fe6b4):** fresh
discovery runs end at `EVOLVED_INVENTION_CANDIDATE` with no ENGINEER stage —
inventions reach the user with `geometry.present: false`,
`engineering.parameters: []`, `downloads.package_zip: null` and the UI shows
"GEN 2 has no 3D model … honest absence" / "Invention, no package yet."
Engineering geometry + technology package only exist on the separately
certified released chain (P-01…P-24).

**This module is the canonical invention-to-3D-to-package path (P0):**

```
run state (JSON) + CIO (JSON)
   -> CLASSIFY  (measured visualizability: ENGINEERING_3D | SYSTEM_3D |
                 CONCEPTUAL_3D | PROCESS_3D | NOT_VISUALIZABLE)
   -> GEOMETRY  (CadQuery/OCCT authority; failure -> diagnose -> repair ->
                 rebuild; engineering failure demotes to conceptual, never
                 silent "No 3D")
   -> GENERATION_MODELS (one GLB per recorded generation — visual lineage)
   -> PACKAGE   (buyer-facing ZIP: essay PDF, engineering definition,
                 evidence, decisive experiment, manifest+hashes, provenance)
   -> CIO UPDATE (geometry.present/class/glb+sha, downloads.package_zip,
                 maturity basis — epistemic guards intact)
```

## Proven

- **Real run end-to-end**: the captured solar run (problem: "Make a solar
  panel which is the most efficient in the world.", GEN 2 AI+IoT+thermal
  architecture) now produces an 11-component SYSTEM_3D conceptual GLB (named
  nodes mirror the run's recorded subsystems), gen-1/gen-2 lineage GLBs, and a
  10-file technology package — honestly labeled `EARLY_TECHNICAL_EVALUATION`
  with the CONCEPTUAL_3D disclaimer ("no engineering dimensions").
- **Engineering path reproduces the released chain**: with the P-07 released
  parameters, the parametric dual-lumen-catheter build measures
  volume 583.550835 mm3 and exports a 75,884-byte STL — byte-for-byte the
  released P-07 figures — with G1 trimesh watertight + G9 regeneration gates.
- **29 tests pass** (`python3 tests/test_bridge.py`), including epistemic
  guards (conceptual artifacts can never carry mm dimensions; EXPERIMENTALLY
  VERIFIED requires a real reality-loop state; forbidden legal language
  raises), manifest hash verification, provenance chain, section-27 leak
  guard (raw JSON can never enter the essay), and failure demotion.

## Wiring into the engine repo

The bridge is a drop-in package. Integration points:

### 1. After survivor selection / run completion

```python
from toscanini_bridge import run_bridge

# once the run directory has final_state + engineering_specification and the
# CIO has been built (existing engine step), run:
result = run_bridge(
    run_result,            # the dict served by GET /api/run/{id}/result
    cio,                   # the dict served by GET /api/run/{id}/cio
    work_dir,              # per-run artifact directory
    glb_endpoint=f"/api/run/{run_id}/model",
    package_endpoint=f"/api/run/{run_id}/package",
)
# persist result["cio_updated"] as the run's CIO (it is the authority);
# persist result["report"] as geometry.cad_pipeline_status evidence.
```

Recommended placement: a new stage after RANK (the current fresh-run
pipeline's last recorded stage). It must run for EVERY completed run with a
survivor — package maturity is honest per run, but the artifact always exists
(§17/§30). NOT_VISUALIZABLE is a recorded, honest outcome (§18) — never fake
a model for an algorithmic invention.

### 2. Serve the artifacts

```
GET /api/run/{id}/model      -> the GLB bytes (geometry.glb from CIO)
GET /api/run/{id}/package    -> the ZIP bytes (downloads.package_zip)
GET /api/run/{id}/cio        -> the updated CIO (already exists in engine)
```

### 3. Frontend renders from the CIO only

The frontend already renders the CIO; it should read the new fields:

- `geometry.present` / `visualizability_class` -> the 3D panel renders the
  GLB; SYSTEM_3D/CONCEPTUAL_3D show the disclaimer chip ("conceptual
  architecture — no engineering dimensions") instead of engineering
  measurements.
- `geometry.components[]` -> the component-inspection panel (function /
  mechanism / evidence / unknowns per component, §24).
- `visualization.generation_models[]` -> the GEN 1 / GEN 2 switcher (§25).
- `downloads.package_zip` + `package_maturity` -> the Technology package (ZIP)
  button becomes active for every run with a survivor (§30 maturity block:
  INVENTION: GEN 2 GENERATED / 3D: CONCEPTUAL MODEL / BUYER READINESS: EARLY
  TECHNICAL EVALUATION).
- `maturity.maturity_ladder` -> the DESIGNED/SIMULATED/EVIDENCE-SUPPORTED/
  EXPERIMENTALLY VERIFIED chips (§29) — the UI never decides these.

### 4. Rebuild (P1, §31)

`engineering_geometry.FORM_LIBRARY` builders are pure functions of the
parameter dict; the engine's existing `/api/showcase/{slot}/evaluate`
convention (param_id + value inside envelope) extends to runs: validate ->
rebuild -> measure -> compare -> new GLB -> new hash + provenance entry. For
conceptual runs, rebuild is honestly unavailable (no engineering parameters)
and the UI should say so.

## Epistemic rules encoded (binding)

- invented architecture ≠ invented evidence: only recorded run-state values
  become parameters; every parameter carries value_class (MODELLED design
  proposal inside a declared envelope, or SOURCE_FACT).
- CONCEPTUAL_3D ≠ ENGINEERING_3D: conceptual artifacts are topology-only
  (component count, adjacency); `guard_no_engineering_dimensions` raises on
  any mm-family key. Conceptual packages contain no STEP/STL.
- EXPERIMENTALLY VERIFIED only from real reality-loop evidence
  (`guard_experimental_language`); this bridge never sets it.
- No patentability/FTO language anywhere (`guard_language`); counsel package
  remains a separate export ("Potential IP territory — formal legal review
  required").
- Geometry failure -> categorized diagnosis -> repair (envelope clamp) ->
  rebuild -> honest demotion to conceptual; never a silent "No 3D" while an
  invention exists (§17, §46).
- Deterministic builds: identical run state -> identical GLB hash; G9
  regeneration gate enforced on the engineering path.

## Files

```
toscanini_bridge/
├── __init__.py            run_bridge public API
├── bridge.py              orchestrator + failure-recovery loop
├── classifier.py          measured visualizability classification
├── epistemics.py          classes, labels, guards (the constitution of this path)
├── conceptual_geometry.py SYSTEM_3D / CONCEPTUAL_3D builders (abstract units)
├── engineering_geometry.py ENGINEERING_3D parametric forms + measure + gates
├── essay.py               §28 eight-section technical essay (+ leak guard)
├── package.py             buyer-facing technology package assembly (ZIP+manifest)
└── cio_update.py          CIO mutation with epistemic guards
tests/test_bridge.py       29 tests (§47 categories, scoped to this path)
```

Dependencies: cadquery 2.6.1 (OCCT), trimesh, reportlab — all standard in the
engine's existing stack (the released chain already uses the same gates).

## Remaining P0/P1 notes for the engine

1. The frontend's run-result panel should replace raw JSON blocks
   (HYPOTHESIS/DESIGN DECISION/NOVELTY HYPOTHESIS) with the essay sections —
   the essay builder here already produces prose from the same canonical
   state (§27).
2. The challenge dimension `obvious_combination` passed "AI + IoT + thermal
   modeling" on the solar run — the §14 drift is an engine-side attack
   calibration matter (P1: attacker calibration, second blind corpus).
3. Run-result 404 currently hangs the UI at "Loading run…" — add an error
   state; consider a share_id fallback so runs survive cookie loss (§8:
   "you can leave and come back").
4. `physics_ready: false` in health — conceptual artifacts do not depend on
   it; the engineering path should wire the existing physics stack after
   geometry (§35 registry decides which domain earns a solver).
