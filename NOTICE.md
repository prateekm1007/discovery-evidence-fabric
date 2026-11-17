# NOTICE — third-party components and license attributions

This repository (discovery-evidence-fabric) uses or derives from the following
permissively-licensed third-party components, per the AM43 capability survey
(audit/CAPABILITY_SURVEY_R46_DEEP_2026-11-17.md). The LICENSE RULE is in force:
only MIT / Apache-2.0 / BSD code is copied or depended on, with attribution;
AGPL-licensed code (e.g. new-api) and unlicensed material (e.g. AutoTRIZ
casebase.json, Gitee CWRU-1) are NOT copied verbatim; the TRIZ methodology
(39 parameters, 40 principles, contradiction matrix, 76 standard solutions)
is public-domain factual knowledge and is encoded in our own files
(scripts/triz_principles.py).

## Python dependencies (pip; used by the computed-physics layer and eval tooling)

| Component | License | Upstream | Use here |
|---|---|---|---|
| CoolProp | MIT | http://coolprop.org | fluid thermophysical properties (D1 computed physics) |
| ht (Caleb Bell) | MIT | https://github.com/CalebBell/ht | heat-transfer correlations |
| fluids | MIT | https://github.com/CalebBell/fluids | fluid mechanics / pressure drop / NPSH |
| thermo | MIT | https://github.com/CalebBell/thermo | chemical thermodynamics |
| chemicals | MIT | https://github.com/CalebBell/chemicals | chemical property data |
| tespy | MIT | https://github.com/oemof/tespy | thermal engineering plant cycles |
| detect-secrets (Yelp) | Apache-2.0 | https://github.com/Yelp/detect-secrets | secret scanning (D8; gitleaks binary substitution noted in the run record) |
| scikit-learn-contrib MAPIE | BSD-3-Clause | https://github.com/scikit-learn-contrib/MAPIE | conformal prediction intervals (D5, planned) |

## Planned copies (AM43 directions D2–D8; attribution in-band at adoption)

- WecoAI/aideml (MIT) — `aide/agent.py`, `aide/journal.py`, `aide/interpreter.py`
  candidate-population tree search patterns (D2 direction; the current V8.1.1
  population search is our own implementation, informed by the AIDE architecture).
- stanfordnlp/dspy GEPA (MIT — corrected from Apache-2.0 by the R47
  byte verification; the standalone gepa-ai/gepa is also MIT) —
  `dspy/teleprompt/gepa/` offline prompt compilation against the
  labelled bind corpus (D5, planned; DEV-only, never touches v8).
- openai/preparedness PaperBench (MIT) — hierarchical rubric leaf-node
  schema (D6, planned; the PRIVATE rubric stays in owner-side private
  custody per F60 — EnvCommons/PaperBench itself carries no license
  file and is NOT the copy source).
- songquanpeng/one-api (MIT) — gateway logging/quota patterns (D8,
  planned; NOT new-api, which is AGPLv3).
- khundman/telemanom (BSD-3-Clause — corrected from Apache-2.0 by the
  R47 byte verification) — non-parametric dynamic thresholding
  baseline for the predictor (D6, planned).
- astroautomata/PySR (Apache-2.0) — symbolic regression for governing
  relations (D4 extension, planned).
- allenai/SPECTER2 (Apache-2.0) — paper-novelty embeddings (D4,
  planned; TF-IDF cosine gate first per AM44 D3).
- UKGovernmentBEIS/inspect_ai (MIT) — standard eval transcripts (D8,
  planned).
- SwanHubX/SwanLab (Apache-2.0) — experiment tracking ledger (D8,
  planned).
- google/BIG-bench (Apache-2.0) — canary GUID mechanism (D7, planned).
- SakanaAI/ShinkaEvolve (Apache-2.0; `shinka/core/novelty_judge.py`
  verified present) — TF-IDF novelty-gate pattern (D3, planned).
- triz-engine (MIT; `data/triz-matrix.json` 39x39 +
  `triz-knowledge-base.json` verified present) — candidate principle
  mapping for D2 typed population; our own self-encoded families in
  scripts/triz_principles.py remain the primary, the matrix JSON is
  the cross-check (attribution carried here).
- llnl/open-ai-co-scientist (MIT) — Elo-tournament / proximity-dedup
  pattern (D8, planned; NOT jataware/open-coscientist, which is
  MIT + Commons Clause).

Note: the "4x more medals" figure for AIDE tree search is the AIDE
project's own README claim (vendor-reported), not an independent
benchmark result; it is treated as motivation only, never as evidence.

## Datasets (public; our own loaders, per AM43)

CWRU Bearing Data, XJTU-SY, NASA C-MAPSS, PHM-Vibench (ModelScope),
CHAOZHAO-1/Machine-Fault-Dataset, hustcxl/Rotating-machine-fault-data-set,
XiuzeZhou/RUL — used for predictor validation (D5) with loaders written in
this repository; no unlicensed repo code is copied.

## Excluded by license rule

- new-api — AGPLv3 (copyleft): not copied; one-api (MIT) is the reference instead.
- AI-Scientist-v2 — restrictive custom "AI Scientist Source Code License":
  approach only, zero code copied; AIDE (MIT) is the copyable tree-search base.
- jataware/open-coscientist — MIT + Commons Clause: not copied; the clean-MIT
  llnl/open-ai-co-scientist is the tournament-pattern source instead.
- AutoTRIZ-DETC24 casebase.json — no license (textbook cases): not copied;
  TRIZ encoded from public-domain methodology in scripts/triz_principles.py.
- Gitee CWRU-1 and other unlicensed CN PHM repos — public data used, own loaders.
