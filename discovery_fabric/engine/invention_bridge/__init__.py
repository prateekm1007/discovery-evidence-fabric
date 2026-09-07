"""discovery_fabric.engine.invention_bridge — R418.

The canonical invention-to-3D-to-package bridge, integrated into the
engine repository (ported from the toscanini-bridge proof module,
commit 932f464, E2E-proven on live run ts_fa94ec9fe6b4; 29 tests).

Contract (operator P0 product correction, 2026-09-07):

    run state (session detail) + CIO
        |
        v  classify (measured, recorded, deterministic)
    visualizability: ENGINEERING_3D | SYSTEM_3D | PROCESS_3D |
                     CONCEPTUAL_3D | NOT_VISUALIZABLE
        |
        v  geometry (CadQuery/OCCT; conceptual builders for non-
           parameterized inventions; failure -> diagnose -> repair ->
           rebuild; never a silent 'No 3D')
    MODEL/model-00N.glb (+ STEP/STL when engineering)
        |
        v  package (essay PDFs, engineering definition, evidence
           summary, decisive experiment, MODEL/, manifest, provenance)
        |
        v  CIO update (geometry.present, downloads, maturity basis)

This package __init__ is deliberately LIGHT (R420b): importing the
bridge pulls cadquery/OCP (~500 MB RSS — measured locally 2026-09-08,
497 MB), which OOM-killed the 512 MB production container when the
async artifact workers spawned at boot (deploy dep-dafjealg1s2s73eqnog0
update_failed; the container never reached its boot snapshot). Every
submodule is importable on its own:

    from discovery_fabric.engine.invention_bridge import render      # stdlib-only
    from discovery_fabric.engine.invention_bridge import bridge      # heavy (OCP)
    from discovery_fabric.engine.invention_bridge import classifier   # heavy
    ...

Importers that need the HEAVY modules (the run worker's bridge gate,
tests) import them explicitly; light consumers (the async render job,
the server's render routes) import only what they need. The render
orchestrator itself (render.py) is stdlib-only by design so the
detached artifact worker stays small next to Blender's own footprint.
"""
