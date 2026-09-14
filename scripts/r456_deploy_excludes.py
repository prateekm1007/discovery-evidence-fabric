"""R456-LEAN-2 — the ONE canonical deploy-upload exclusion list.

The production Space build carries ONLY what the runtime reads and
serves. This list names the round-evidence trees, CI-instrument
directories, and archived history that the deploy drivers exclude from
the staged upload (the R455-LEAN-1-DELETIONS round proved the
production import closure is 168 files / 90,817 LOC and touches none
of these; the .dockerignore R-digit rule mirrors it for local builds).

Every excluded byte stays in git history and on the engine repo's
round records (Art. XI) — this is a transport exclusion, not a
disposition change.

Measured at R456 on the round branch: ~520 MB of tracked bytes
excluded; the staged Space upload drops to the runtime + records core.
"""

#: directories excluded from the Space upload (glob-free, exact names)
EXCLUDE_DIRS = [
    # R4xx round-evidence trees (the big measured ones; the small record
    # dirs R446-R455 stay: they carry the deployment + acceptance records)
    "R452", "R451", "R450", "R449", "R445", "R444", "R412", "R411",
    "R401-WC2", "R401",
    # CI instrumentation corpora (the Space runs no pytest)
    "tests", "experiments", "tournament_v3", "visual-lab",
    ".github",
    # archived history (importable in the engine repo; a hyphen dir the
    # runtime never imports)
    "archive",
    # superseded evidence snapshots (zero runtime reads, measured)
    "patentability", "CEREVASC_TERRITORY_2_FINAL_ADJUDICATION",
    "CEREVASC_TERRITORY_8_V4_SC3_HEAD_TO_HEAD",
    "CEREVASC_TERRITORY_9_CNS_THERAPY_PLATFORM",
    "CEREVASC_TERRITORY_10_LIFECYCLE_INTELLIGENCE",
    "BENCHMARK_ENGINEERING_DOSSIERS", "LEAD_PORTFOLIO_4",
    "CANONICAL_STATE", "EXTERNAL_CONSULTANT_EVIDENCE",
]

#: root files excluded from the Space upload
EXCLUDE_FILES = [
    "MODULE_INVENTORY.json",     # engine-side audit view (R456)
    "A_SERIES_ACCEPTANCE.json", "E15_ACCEPTANCE.json",
    "E16_ACCEPTANCE.json", "F_SERIES_ACCEPTANCE.json",
    "worklog.md",
]
