"""
R374 — final engineering evidence hardening (CEO directive).

Modules:
  equation_status.py    R374-2 three-level equation validation status +
                        R374-3 per-symbol source-backed unit status
  traceability_truth.py R374-1 traceability truth model (four states per
                        chain + reasons + UNKNOWN-is-not-verified
                        declaration + over-claim language scan)
  diagram_proof.py      R374-4 per-element diagram proofs (mechanism 5,
                        experiment 7)
  pathway.py            R374-6 failed-candidate pathway (six elements,
                        honest legacy migration, append-only enforcement)
  acceptance_r374.py    the seven-condition R374 acceptance gate
  run_r374_audit.py     runner: R374 audit artifact + release candidate +
                        repo-rule application (R374-7)

No R371/R372/R373 gate is lowered; the frozen benchmark is untouched.
"""
