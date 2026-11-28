# dev_holdout_problems — burned holdout problem sets as DEV material

Provenance (Art. 7 — bytes over claims; sha256-verified at copy time):

- `holdout_v3_problems.burned_dev.json`
  sha256 = 38884e58524a3ffb4a8584501ccb4416197138fb314ff91b5dd73829a7ff1f77
  BYTE-IDENTICAL to the sealed set the c-0016 one-shot generated against
  (the one-shot record discloses problems sha256_16 = 38884e58524a3ffb).
  Scored 68.8% by the auditor's PRIVATE rubric and BURNED -> DEV
  (AM25 verdict sec. 2: "Burned -> DEV").

- `holdout_v2_problems.burned_dev.json`
  sha256 = 79db7868a0e7483daaa623f6aeb3da2da036533cc188623713cb55d6e67e6fee
  The v2 sealed problems (scored 62.5%, burned -> DEV, AM24/AM25).

Purpose: the AM25 D2 regression pins (tests/test_r26_catalog_scan.py)
run on the REAL violating bytes — HO2-03 (zinc anode), HO2-04
(intake-humidity control), HO3-05 (chelating-resin cartridge) — which
live in these burned sets. The auditor's PRIVATE rubrics are NOT in
this folder, were never opened by the builder, and must never be
copied to any builder-visible path (Art. 7 sealed instruments).

These sets are DEV: no sealed or holdout use. Fresh holdouts (v4+)
are authored by the AUDITOR (Art. 28 addendum) on new problems.
