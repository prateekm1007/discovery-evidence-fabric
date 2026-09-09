"""discovery_fabric.engine.visual_compiler — R441.

The Visual Compiler: the deterministic presentation pipeline that turns
the canonical GLB (CadQuery/OCCT — the engineering authority) into the
buyer-grade visual set (Hero, Turntable, Exploded, Section,
Orthographic, Dimension, Poster), guarded by the Visual Quality Gate.

Constitutional position (Article LXXII):

    A 3D artifact is not complete because geometry exists. It is
    complete only after the canonical geometry has been transformed by
    the Visual Compiler into a deterministic presentation set, passed
    the Visual Quality Gate, and the exact same approved render has
    been embedded in both the website and the technology package PDF.

Layer contract (operator directive R441):

    Layer 1 (KEEP):  CadQuery + OpenCascade — exact CAD, STEP,
                     engineering geometry. Never removed.
    Layer 2 (NEW):   headless Chromium + Three.js replaces Blender as
                     the hero-render path (same renderer family as the
                     website — WYSIWYG, deterministic, CPU/SwiftShader).
    Layer 3 (CANON): glTF is the canonical interchange; every package
                     emits STEP + GLB + the deterministic visual set.

Modules:
    scene_builder.py   GLB -> canonical scene spec (inventory, grounding)
    camera_solver.py   deterministic camera solve (hero/ortho/section)
    material_mapper.py semantic materials from component type (never
                       from a prompt)
    render_worker.py   headless renderer process boundary (Chrome
                       resolution, env allowlist, memory guard)
    visual_gate.py     independent pixel-level quality gate
    visual_compiler.py the orchestrator (typed records, one entry point)
"""

VISUAL_COMPILER_VERSION = "1.0.0"
RENDER_PIPELINE = "VISUAL_COMPILER_HEADLESS_THREE"
