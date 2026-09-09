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

This directory is history, not live code. Do not import from here.
