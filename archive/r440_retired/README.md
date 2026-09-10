# R440 Retired Subsystems (Art. LXIV disposition)

## package_factory.py — ARCHIVED (was discovery_fabric/engine/package_factory.py)

- **Disposition:** `ARCHIVED_TO archive/r440_retired/package_factory.py`
  (git mv preserves history; no rewrite — Art. XI).
- **Retired by:** R440.1 (the one-canonical-package-compiler round).
- **Why retired:** it was a COMPETING production package authority.
  `EngineRun._post_rank_pipeline()` and `_evolution_package_survivor()`
  invoked `generate_buyer_package` BEFORE/DURING invention evolution,
  violating the R440.2 order contract
  (DISCOVERY -> CHALLENGE -> DIAGNOSIS -> EVOLUTION -> FINAL INVENTION ->
  ENGINEERING -> EXPERIMENT -> PACKAGE) and producing stale-generation
  packages that could represent an earlier invention generation than the
  final canonical state.
- **Replacement:** `discovery_fabric/engine/package_compiler.py` — the
  ONE canonical package compiler, invoked post-evolution by the bridge
  gate (toscanini/worker.py phase 3.5), transactionally verified by the
  independent package quality gate
  (`discovery_fabric/engine/package_quality_gate/`, Gates A-V).
- **What also moved with it:** the E15-B dossier-quality gate and the
  E16-H holdout release gate as *production run-path* controls. Their
  checks are subsumed by the compiler validators (R440.7-.12) and the
  independent quality gate (identity/fidelity/evidence/engineering/
  experiment/artifact dimensions). The modules `dossier_quality.py` and
  `release_gate.py` remain importable for portfolio release paths.
- **Not deleted from history:** `git log --follow
  archive/r440_retired/package_factory.py` retrieves the full lineage.
