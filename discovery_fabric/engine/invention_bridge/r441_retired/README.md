# r441_retired — Article LXIV retirement record

`blender_render.py` was RETIRED at R441 (operator directive: "Replace
Blender's role... Headless Three.js renders previews"). It is archived
here INTACT in the same commit that shipped its replacement
(`discovery_fabric/engine/visual_compiler/`), importable as history,
referenced by NOTHING live (verified by
`tests/test_r441_visual_compiler.py::TestBlenderRetirement`).

Disposition per Article LXIV operational rule 1: **ARCHIVED_TO**
`discovery_fabric/engine/invention_bridge/r441_retired/blender_render.py`.
The legacy dispatcher branch (`render.py::
render_invention_blender_legacy`) remains KEPT_BECAUSE the pinned
Blender build is still the stack's only USD/DAE/FBX conversion route
and the R441 swap carries one round of production A/B; deletion of the
legacy branch is scheduled R442 (the LXIV two-step discipline:
supersede -> battery -> delete).

**R452 RENEWAL (2026-09-13, external audit C4):** the "scheduled R442"
disposition above is STALE — the deletion is now roughly ten rounds
overdue, which the external audit flags as an Article LXIV violation.
Renewed dated reason for NOT deleting this round: the deletion's blast
radius spans the `artifact_identity.blender_scene_hash` schema field,
the pinned-build env contract (R423 allowlist battery), and the
R420/R441 test batteries — an owner-visible schema change that must not
ride an audit-response commit. STATUS: production renders measured 7/7
`three@0.175.0` (the legacy path never fired; it is a latent
second-truth-system risk, not an active one). ESCALATION (Art. LXV):
the deletion decision is OPEN with `escalation_count` incremented; the
cost of continued inaction is a standing second renderer selectable by
one environment variable, tested only by its label. Proof battery for
non-implicit selection:
`tests/test_r452_blender_retirement.py` (default = Visual Compiler;
unrecognized backend never falls through to legacy; explicit selection
stays labeled; this renewal record exists).

This directory is history, not live code. Do not import from here.
