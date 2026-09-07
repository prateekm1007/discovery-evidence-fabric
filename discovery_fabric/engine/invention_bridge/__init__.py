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
           summary, decisive experiment, manifest sha256, provenance)
    TECHNOLOGY_PACKAGE/ + zip
        |
        v  CIO update (epistemic guards intact)

Epistemic law (Constitution v2.1.0):
- CONCEPTUAL_3D / SYSTEM_3D / PROCESS_3D never claim ENGINEERING_3D
  (Art. XXVIII — no silent semantic promotion).
- Conceptual artifacts carry NO engineering dimensions; topology only.
- Modelled parameters are labeled ENGINE-DECLARED MODELLED proposals
  (Art. XXVII).
- EXPERIMENTALLY_VERIFIED is never set by this bridge (Art. LIII).
- The buyer-package quality gate and release gate are untouched — the
  bridge package is a distinct honest artifact class (technology
  package for early technical evaluation), never a weakened buyer
  release (Art. IV/VII).
- reviewer_provenance=AI_REVIEW on every artifact (Art. LXVII).
"""
from .bridge import bridge, BRIDGE_VERSION  # noqa: F401
