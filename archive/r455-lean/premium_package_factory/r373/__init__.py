"""R373 — Independent engineering-artifact adequacy audit.

CEO R373 directive. This package is an AUDIT LAYER, not a builder:
  - it recomputes every verdict from canonical data (Constitution Art. III:
    the verifier must never trust the claimant — shipped artifacts are
    treated as claims, never as evidence of their own adequacy);
  - it reuses only NEUTRAL instrumentation (the diagram recording harness
    and the renderer itself — the artifact under audit), never the R372
    verdict logic;
  - it is observational (Art. IX): it writes ONLY its own audit artifacts;
    adversarial injections run on in-memory copies, never on shipped files;
  - it is builder-run tooling (Art. XXVI): its results are submitted FOR
    CEO AUDIT and are labelled as such — they are not independent
    certification.
"""
