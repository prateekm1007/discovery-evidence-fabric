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
| Cantera | BSD-3-Clause | https://github.com/Cantera/cantera | computed chemical equilibrium (AM80 direction 3: `equilibrate()` verifies claimed chemistry directions at generation time — the computed complement to the registry equilibrium-direction scan; suite `tests/test_r80_chemistry_equilibrium.py`, c-0107) |
| detect-secrets (Yelp) | Apache-2.0 | https://github.com/Yelp/detect-secrets | secret scanning (D8; gitleaks binary substitution noted in the run record) |
| scikit-learn-contrib MAPIE | BSD-3-Clause | https://github.com/scikit-learn-contrib/MAPIE | conformal prediction intervals (D5; the fixture-stage conformal FA-control prototype `scripts/r80_conformal_fa.py` is in tree, claim c-0108 — computed coverage 0.915 walk-forward at confidence 0.90 on the synthetic fixture, immediate typed FA on an injected level shift; the Time-MoE/MOMENT FM evals + the real C-MAPSS/XJTU-SY/CWRU runs are the typed next steps) |

## Planned copies (AM43 directions D2–D8; attribution in-band at adoption)

- microsoft CRITIC / CriticEval (ICLR23 pattern; CriticEval MIT;
  license-verified AM82 worldwide update 3) — the tool-grounding critic
  pattern (the critic CALLS external tools to verify/correct claims
  instead of iterating prompts) copied into
  `discovery_fabric/engine/tool_grounded_critic.py` (claim c-0109): the
  deterministic bill-tagger + computed-chemistry corrector surfaces, the
  machine's own base_scan as the CI oracle, adoption-gated (no frozen
  bytes; the machine-side wiring + live ablation are the typed next
  steps). Our own code, no upstream bytes.
- WecoAI/aideml (MIT) — `aide/agent.py`, `aide/journal.py`, `aide/interpreter.py`
  candidate-population tree search patterns (D2 direction; the current V8.1.1
  population search is our own implementation, informed by the AIDE architecture;
  R95 claim c-0110 lands the engine-native repair-slot controller
  `discovery_fabric/engine/aide_tree_search.py` — best-first parent selection on
  the machine's own finding surface, metric-pruned frontier, diverse
  process-only angle roster, incumbent-parity mode; pattern copy only, zero
  upstream code bytes).
- noahshinn/reflexion (MIT) — the verbal self-reflection MEMORY pattern
  (failure signature + lesson carried across repair attempts, quoted back
  neutrally); copied as a pattern into `scripts/r80_repair_convergence.py`
  (AM79 roadmap P2 convergence lane; our own code, no upstream bytes; the
  frozen-side wiring is a typed next step under the CI-gated re-freeze
  discipline).
- madaan/self-refine (Apache-2.0) — the structured feedback→refine→STOP
  criterion pattern (stop on a provably non-improving repair — exact
  failure-signature repeat — instead of fixed budget burn); copied as a
  pattern into `scripts/r80_repair_convergence.py` (AM79 roadmap P2
  convergence lane; our own code, no upstream bytes).
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
  R99 RUNTIME REALITY (AM85 direction 3): the weights ARE now fetched
  and served from the vault HF token (allenai/specter2_base +
  allenai/specter2 proximity adapter, loaded via the adapter stack
  per the model card; zero generation). The live calibration typed a
  METHOD FINDING: SPECTER2's within-industrial-text scale is
  domain-cohesive (faithful paraphrases 0.039-0.050; extremal
  cross-domain anchors 0.13-0.15 from a textbook control; the burned
  v13 corpus 0/30 at an absolute 0.2 gate, distances 0.049-0.062) —
  the AM85 0.2 ABSOLUTE gate is scale-invalid for SPECTER2 on
  within-domain texts; the semantic novelty gate is typed
  DISTRIBUTION-CALIBRATED (min-distance > the prior corpus's own
  pairwise p95) with the absolute numbers disclosed verbatim
  (eval/r99_p4_specter2_calibration.json). TF-IDF remains the AM85
  absolute-gate leg; SPECTER2 corroborates semantically.
- CoRector/cohere + z-ai SDK — BLIND PANEL VENDORS (R99, AM85
  direction 4): the blind cross-family rating panel serves
  cohere/command-a and cohere/command-a-plus over the xkiro
  transport (browser UA per the R58 contract) and the z-ai SDK chat
  model; each vendor is used per its own API terms; no vendor sees
  generator identity, other agents' ratings, or any rubric
  (scripts/r99_blind_panel.py, the typed blindness contract).
- China/global AI4Science scan (AM85 direction 6; license-verified
  via live web read 2026-11-19):
  - Time-MoE (github.com/Time-MoE/Time-MoE, ICLR'25 Spotlight,
    Apache-2.0) — billion-scale MoE time-series FM; the FM-eval leg
    candidate for the conformal FA-control real-data runs (typed
    next step in the MAPIE row above).
  - MOMENT (github.com/moment-timeseries-foundation-model/moment,
    Auton Lab CMU, MIT) — open time-series FM family; second FM-eval
    candidate, same typed next step.
  - Intern-S1 (github.com/InternLM/Intern-S1, Shanghai AI Lab,
    Apache-2.0) — scientific multimodal FM; scanned for the
    novelty/viability legs (no code adopted this round; the panel
    and FM-eval lanes are the typed adoption surfaces).
- FM-eval REAL-DATA candidates (the conformal FA-control leg's typed
  next step; license-verified via live web read 2026-11-19):
  - C-MAPSS turbofan degradation (data.nasa.gov, NASA open data —
    US-government public class; classic multivariate run-to-failure
    series) — the conformal FA-control real-data candidate 1.
  - XJTU-SY bearing run-to-failure (github.com/WangBiaoXJTU/
    xjtu-sy-bearing-datasets; the repo states no license — the
    Mendeley deposit of the same dataset is CC BY 4.0, Biao Wang;
    adoption attributes the Mendeley CC BY 4.0 deposit) — candidate 2.
  - CWRU bearing data (Case Western Reserve University) — candidate
    3, standard academic attribution, license re-verified at
    adoption time before any bytes are pulled.
- pyribs (BSD-3-Clause) — NOT ADOPTED, typed: no pyribs import
  exists anywhere in the tree; the quality-diversity mechanics are
  the c-0110 AIDE controller + the histogram caps (our own
  implementation). No attribution obligations arise; the row exists
  so the AM85 worldwide-module check is honest about non-use.
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

## Pattern copies in tree (R92 roadmap, license-verified 2026-11-18; ADOPTION gated on the matched-budget live ablation)

- noahshinn/reflexion (MIT) — the verbal self-reflection MEMORY
  pattern: per-row attempt history (persisted / resolved / new
  finding keys) composed into a reflection addendum on the repair
  directive from the second repair onward. Two independent
  implementations of the pattern are in tree: the fixture-stage
  prototype `scripts/r80_repair_convergence.py` (R80, claim c-0105,
  zero LLM) and the engine-native controller
  `discovery_fabric/engine/repair_convergence.py` (R93, claim
  c-0106, the live-ablation instrument). PATTERN copies only — zero
  upstream code bytes (the upstream implementation is an agent
  framework); both are re-implemented against the frozen V7.7 loop's
  own finding surface. On adoption, Art. 16 accounting retires the
  scripts-side prototype (superseded by the engine module).
- madaan/self-refine (Apache-2.0) — the structured STOP criterion
  pattern: stop refining when the feedback signature stops changing
  (here: identical finding signature across the stagnation window
  AFTER a reflection-augmented repair), instead of burning the fixed
  repair budget on non-improving repairs. Same two implementations
  and same pattern-copy-only terms as above.
- WecoAI/aideml (MIT; AM82 direction 2) — the best-first tree-search
  pattern over diverse candidates, metric-pruned: copied into
  `discovery_fabric/engine/aide_tree_search.py` (claim c-0110) — the
  single-chain repair loop becomes a best-first population search over
  distinct structural repair angles, scored ONLY by the machine's own
  finding surface (scan battery + critic + type gate), budget-matched
  (the controller adds zero LLM calls), incumbent-parity mode
  (population=False reduces exactly to the frozen single chain).
  Pattern copy only — zero upstream code bytes.
- ChemMCP (Apache-2.0; license-verified AM81/R93) — chemistry-tool
  integration pattern (LLM calls chemistry tools instead of guessing
  chemistries; planned P2 generation-side complement, AM81).
- CACTUS (BSD-2-Clause; license-verified AM81/R93) — chemistry
  toolkit (retro/forward reaction prediction) pattern (planned P2
  generation-side complement, AM81).

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

## triz-engine data (MIT)

The classical TRIZ contradiction matrix and the 39 engineering-parameter
descriptions in `discovery_fabric/engine/data/triz_classical_matrix.json`
are derived from the [triz-engine](https://github.com/SharathSPhD/triz-engine)
project and are included under the MIT License. The full license text is
preserved verbatim in [NOTICE-triz-engine](NOTICE-triz-engine).
