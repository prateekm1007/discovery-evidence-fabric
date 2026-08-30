"""toscanini — the orchestration boundary in front of the discovery engine.

Toscanini MVP (CEO directive 2026-08-30): a local web application that puts
the existing discovery-evidence-fabric engine behind a usable interface.

    Toscanini UI (Next.js, :3000)
        |
    toscaniu.server (HTTP+SSE, :8788)   <-- this package
        |
    discovery_fabric.engine.run.EngineRun  (UNCHANGED engine)
        |
    canonical package factory (UNCHANGED, QA-gated)

Constitutional constraints honored here:
  Art. IV/VI  — no fabricated progress; every stage event streamed to the
                UI comes from a persisted engine artifact on disk.
  Art. X      — the engine run directory IS the authoritative state; the
                session store is a projection/index, never a second truth.
  Art. XVIII  — LLM output is labeled MODEL_DERIVED; retrieval is
                EXTERNAL_EVIDENCE; nothing is promoted silently.
  Art. XX/XXI — problems built from free text are evidence-bound: live
                retrieval precedes the run; limitations stamped inline.
  Art. XXV    — infrastructure failures are shown as failures, never as
                kills or as absence.
  Art. XXXVIII — epistemic classes surface end-to-end in the UI.
"""
