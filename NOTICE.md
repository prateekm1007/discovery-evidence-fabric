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
- stanfordnlp/dspy GEPA (Apache-2.0) — `dspy/teleprompt/gepa/` offline prompt
  compilation against the labelled bind corpus (D3, planned).
- EnvCommons/PaperBench (MIT) — hierarchical rubric leaf-node schema (D6, planned;
  the PRIVATE rubric stays server-side).
- songquanpeng/one-api (MIT) — gateway logging/quota patterns (D8, planned;
  NOT new-api, which is AGPLv3).
- khundman/telemanom (Apache-2.0) — non-parametric dynamic thresholding baseline
  for the predictor (D5, planned).
- astroautomata/PySR (Apache-2.0) — symbolic regression for governing relations
  (D1 extension, planned).
- allenai/SPECTER2 (Apache-2.0) — paper-novelty embeddings (D4, planned).
- UKGovernmentBEIS/inspect_ai (MIT) — standard eval transcripts (D8, planned).
- SwanHubX/SwanLab (Apache-2.0) — experiment tracking ledger (D8, planned).
- google/BIG-bench (Apache-2.0) — canary GUID mechanism (D7, planned).

## Datasets (public; our own loaders, per AM43)

CWRU Bearing Data, XJTU-SY, NASA C-MAPSS, PHM-Vibench (ModelScope),
CHAOZHAO-1/Machine-Fault-Dataset, hustcxl/Rotating-machine-fault-data-set,
XiuzeZhou/RUL — used for predictor validation (D5) with loaders written in
this repository; no unlicensed repo code is copied.

## Excluded by license rule

- new-api — AGPLv3 (copyleft): not copied; one-api (MIT) is the reference instead.
- AutoTRIZ-DETC24 casebase.json — no license (textbook cases): not copied;
  TRIZ encoded from public-domain methodology in scripts/triz_principles.py.
- Gitee CWRU-1 and other unlicensed CN PHM repos — public data used, own loaders.
