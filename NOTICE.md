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
| CoolProp | MIT | http://coolprop.org | fluid thermophysical properties (D2 ENGINE-NATIVE: `discovery_fabric/engine/physics_library_checks.py` `check_fluid_property_direction`, claim c-0128; suite `tests/test_physics_library_checks.py`) |
| ht (Caleb Bell) | MIT | https://github.com/CalebBell/ht | heat-transfer correlations (D2 ENGINE-NATIVE: `physics_library_checks.py` `check_convective_htc_direction` via `ht.conv_internal.Nu_conv_internal`; suite `tests/test_physics_library_checks.py`) |
| fluids | MIT | https://github.com/CalebBell/fluids | fluid mechanics (D2 ENGINE-NATIVE: `physics_library_checks.py` `check_pipe_pressure_drop` via `fluids.friction_factor`; suite `tests/test_physics_library_checks.py`) |
| Cantera | BSD-3-Clause | https://github.com/Cantera/cantera | computed chemical equilibrium (D2 ENGINE-NATIVE: `physics_library_checks.py` `check_equilibrium_direction` on gri30.yaml — the port of the `scripts/r80_chemistry_equilibrium.py` mechanism, c-0107; the r80 script stays imported by `engine/tool_grounded_critic.py`, so its Art. 16 retirement RIDES that module's migration — typed, not silent; suite `tests/test_physics_library_checks.py`) |
| detect-secrets (Yelp) | Apache-2.0 | https://github.com/Yelp/detect-secrets | secret scanning (D8; gitleaks binary substitution noted in the run record) |
| scikit-learn-contrib MAPIE | BSD-3-Clause | https://github.com/scikit-learn-contrib/MAPIE | conformal prediction intervals (D5; the fixture-stage conformal FA-control prototype `scripts/r80_conformal_fa.py` is in tree, claim c-0108 — computed coverage 0.915 walk-forward at confidence 0.90 on the synthetic fixture; the REAL-DATA legs are MEASURED on the P3 lane: `eval/r105s2_p3_stage1_record.json` … `stage3b`, claims c-0125 — CWRU detection 12/12 FA 0/4; C-MAPSS 0.94 stable / 0.50 drift; sliding+FM 0.887-0.9118) |
| scikit-learn | BSD-3-Clause | https://github.com/scikit-learn/scikit-learn | the Ridge one-step predictor of the conformal FA-control prototype (imported by `scripts/r80_conformal_fa.py`, the committed bytes the P3 lane runs verbatim) |
| AIDE (WecoAI/aideml) | MIT | https://github.com/WecoAI/aideml | the best-first candidate-population tree-search pattern — credited in the module header of `discovery_fabric/engine/aide_tree_search.py`; pattern copy only, zero upstream code bytes (the dedicated row the auditor's direction 3 asked for; the prose entries above remain) |
| pint | BSD-3-Clause | https://github.com/hgrecco/pint | unit discipline (imported by `discovery_fabric/engine/physics_checks.py` — bare dimensional floats are typed refusals) |
| numpy | BSD-3-Clause | https://github.com/numpy/numpy | array layer (engine + eval tooling) |
| scipy | BSD-3-Clause | https://github.com/scipy/scipy | sparse/linalg/stats (engine + eval tooling: `loadmat`, `spearmanr`, sparse scans) |
| pandas | BSD-3-Clause | https://github.com/pandas-dev/pandas | tabular corpus handling (score-9 corpus readers) |
| matplotlib | BSD-3-Clause | https://github.com/matplotlib/matplotlib | diagnostic figures (scripts; never a gate input) |
| pytest | MIT | https://github.com/pytest-dev/pytest | the CI test runner (every article CI check runs under it) |
| PyTorch | BSD-3-Clause | https://github.com/pytorch/pytorch | FM-eval tensor layer (the P3 lane FM arms, claims c-0125) |
| transformers | Apache-2.0 | https://github.com/huggingface/transformers | Time-MoE-50M loading (trust_remote_code; the cache-API compatibility shims are typed in `scripts/r105s2_p3_stage2.py`) |
| huggingface_hub | Apache-2.0 | https://github.com/huggingface/huggingface_hub | weight/dataset fetch via the vault token (digest-verified custody, Art. 17) |
| Chronos / Chronos-Bolt (amazon) | Apache-2.0 | https://github.com/amazon-science/chronos-forecasting | the FM arms of the P3 real-data conformal lane (`amazon/chronos-bolt-base`; `chronos 2.3.2` `predict_quantiles` returns (quantiles, mean) — typed in `scripts/r105s2_p3_stage2.py`; claims c-0125) |
| Sundial (thuml) | Apache-2.0 | https://github.com/thuml/Time-Series-Library | Tsinghua time-series FM (the D8 arm of the auditor verdict 2026-11-20; `thuml/sundial-base-128m`; measured under the same conformal protocol — see the P3 stage records) |
| cadquery | Apache-2.0 | https://github.com/CadQuery/CADQuery | parametric CAD geometry (the CAD gate layer) |
| OCP (OpenCascade) | Apache-2.0 (OCCT 7.8+; earlier releases LGPL-2.1-with-exception) | https://github.com/Open-Cascade-SAS/OCCT | the CAD kernel under cadquery |
| sfepy | BSD-3-Clause | https://github.com/sfepy/sfepy | FEM mechanics checks (script harnesses) |
| trimesh | MIT | https://github.com/mikedh/trimesh | mesh geometry handling |
| rdkit | BSD-3-Clause | https://github.com/rdkit/rdkit | cheminformatics (SMILES mining in `discovery_fabric/engine/patent_claim_extract.py`) |
| reportlab | BSD-3-Clause | https://hg.reportlab.com/hg-public/ | PDF rendering (tooling) |
| Pillow (PIL) | MIT-CMU | https://github.com/python-pillow/Pillow | image I/O (render/tooling paths) |
| pypdf | BSD-3-Clause | https://github.com/py-pdf/pypdf | PDF reading — the gate's page-text primary (package quality gate) |
| pdfplumber | MIT | https://github.com/jsvine/pdfplumber | PDF line/block rect geometry (the gate's collision/clipping legs; the R109 D6 AGPL-retirement successor) |
| poppler-utils (pdftotext/pdftoppm) | GPL-2.0 — SEPARATE PROCESS ONLY, EXCLUDED-BY-RULE waived as subprocess | https://poppler.freedesktop.org/ | CLI fallbacks invoked as external binaries (never imported, no linkage, no upstream bytes vendored): `pdftotext` text fallback + `pdftoppm` the gate's 36-dpi blank-render leg |

**Retired (Art. 16 accounting — the R109 D6 swap, eval/retirement_ledger.json):** PyMuPDF (fitz) — was the package_quality_gate's page-text + block-rect primary; retired on the AGPL-3.0-or-commercial license-rule conflict (the standing rule is MIT/Apache/BSD-only). Successors: pypdf (page text), pdfplumber (block geometry), pdftoppm (rendered ink coverage). Zero fitz imports remain in the tree (test-covered: `tests/test_notice_import_coverage.py`).

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
- China/global AI4Science scan continuation (live web read
  2026-11-19, the FM-eval leg):
  - FISHER — a foundation model for multi-modal industrial systems
    (2026; the RMIS benchmark, 19 sub-datasets across anomaly
    detection and diagnosis tasks) — scanned as an FM-eval candidate
    for the industrial multi-modal leg; no code adopted; license and
    weights availability re-verified at adoption time.
  - "Data-Layer Mismatch in Industrial Motor Fault Diagnosis"
    (IEEE, 2026) — an applicability study of time-series foundation
    models on industrial motor data; scanned for the conformal
    FA-control leg's external-validity framing (the data-layer
    mismatch caveat is the honest external-viability note for any
    TSFM adoption); no code adopted.
  - FISHER (`jianganbai/FISHER`, license verified 2026-11-19; the
    auditor-confirmed row) — a foundation model for multi-modal
    industrial signal compreHEnsive representation
    (sound/vibration/voltage, arbitrary sampling rates via sub-band
    concatenation); ships the RMIS benchmark (19 sub-datasets).
    Code MIT (LICENSE verified); weights on HuggingFace + Tsinghua
    Cloud + wisemodel (tiny/mini/small). Publication: IEEE Trans.
    Industrial Informatics DOI 10.1109/TII.2026.3698554; arXiv
    2507.16696. No NOTICE file in the repo. Scanned for the
    industrial-signal leg (the v13 domain family); no code adopted.
  - microsoft/Industrial-Foundation-Models (verified 2026-11-19) —
    Generative Tabular Learning models (healthcare/energy-storage/
    commerce/transportation/agriculture). Code repo MIT (LICENSE
    verified); weights distributed as GTL DELTA checkpoints
    (microsoft/LLaMA-2-13b-GTL-Delta on HuggingFace, model card
    `license: mit`) — the composite artifact depends on the LLaMA-2
    base weights under Meta's LLaMA-2 Community License, which
    downstream use inherits. Repo archived by the owner 2026-09-15.
    Reference-only row; no code adopted.
  - UniFault (`emadeldeen24/UniFault`, verified 2026-11-19) — a
    fault-diagnosis foundation model from bearing data (multivariate
    inputs unified into standardized univariate sequences; arXiv
    2504.01373, cited-by 24). Code MIT (LICENSE verified); a tiny
    checkpoint download is published in the README. No NOTICE file.
    Scanned for the industrial-signal leg alongside FISHER/RMIS; no
    code adopted.
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

## External model releases scanned (license-verified 2026-11-20, R105 scan lane; no code adopted — attribution + ecosystem tracking only)

- Hydrogen-1.0 (Deep Principle, Hangzhou; released 2026-11-02) — 753B
  science model post-trained on GLM-5.3 (Z.AI base). Weights MIT
  (`License: mit` tag, HF model card `deep-principle/Hydrogen-1.0`);
  independently authored code/docs Apache-2.0; BF16 + NVFP4 (Blackwell)
  + MXFP4 (Instinct MI350X) variants; distributed HF + ModelScope +
  NeuroSpark API. Publisher-reported evals (unreplicated, typed as
  such): FSR 38.3%, GPQA-Diamonds 93.0%. Module-attribution note: the
  z-ai/GLM family is being selected as a science post-training base by
  third parties — a data point for the score-8 family planning.
- structRFM (USTC; Nature, 2026-11-05) — structure-guided RNA sequence
  foundation model; MIT (GitHub `heqin-zhu/structRFM` LICENSE file).
  Releases pre-trained model (768d/12L/12H) + 21M sequence-structure
  pairs + fine-tuned checkpoints + full code. No code adopted.
- NASA-IBM Lunar Foundation Model (NASA-IBM AI4Science; paper
  2026-09-08, open release 2026-09-10) — ViT-B encoder-decoder trained
  on SomBench (~2M co-registered lunar tile bundles, 11 modalities);
  Apache-2.0 (`nasa-ibm-ai4science/NASA-IBM-Lunar-Foundation-Model`).
  Card states non-operational-use limitations (typed as-is; no
  field-of-use legal restriction under Apache-2.0). No code adopted.
- OpenMDW-1.1 license taxonomy event (Linux Foundation + PyTorch
  Foundation; v1.1 published 2026-05-28) — permissive model-first
  license covering weights + data + docs + model outputs; MOF-aligned.
  NVIDIA adopting across Cosmos / Isaac GR00T / Ising / Nemotron
  (verified on `nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16`:
  "Governing Download Terms: OpenMDW License Agreement, version 1.1").
  Taxonomy action: `openmdw-1.1` is tracked as a first-class permissive
  license class in the scan ledger. Sub-items scanned, license NOT yet
  byte-verified (stay provisional): Nemotron for Science + LitmusBench
  v0.2 (~50k chemistry RLVR questions, SC26 2026-11-16), Nemotron 3.5
  Transcribe, Bolt E4B. No code adopted.

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

## Score-9 payloads (claim c-0127, adopted 2026-11-19; license texts byte-verified per the c-0125 convention)

- MOOSE-Chem2 (Zonglin Yang et al., NeurIPS 2025) — GitHub
  `ZonglinY/MOOSE-Chem2` @ `5b289372fe7722df33bfc49c4c329671967f8822`;
  MIT (LICENSE byte-read: "MIT License, Copyright (c) 2025 Zonglin
  Yang"). The 2024 fine-grained chemistry corpus
  (`Data/chem_research_2024_finegrained.xlsx`, 276,676 bytes) supplies
  the post-cutoff rediscovery corpus (30 sampled items committed under
  `eval/r106_score9_corpus/` with attribution; the sampled rows carry
  their source commit). Our own protocol engine; upstream method code
  NOT copied.
- PatentChem (Kevin Greenman, learningmatter-mit; DOI
  10.5281/zenodo.7992427) — GitHub `learningmatter-mit/PatentChem`;
  MIT (LICENSE byte-read: "Copyright (c) 2022 Kevin Greenman"). The
  claim-extraction APPROACH (USPTO claims sections -> numbered-claim
  segmentation -> keyword query mining -> molecule SMILES mining) is
  re-expressed as this repository's engine rules
  (`discovery_fabric/engine/patent_claim_extract.py`); zero upstream
  bytes copied (the upstream is a USPTO bulk-download pipeline, ours
  is the rule set + real-bytes acceptance sample).
- PaECTER (Max Planck Institute of Innovation and Competition et al.;
  PLOS ONE 2025, doi 10.1371/journal.pone.0358188) — HF
  `mpi-inno-comp/paecter` (base `anferico/bert-for-patents`,
  1024-dim). USED FOR: the machine-score similarity input on the
  rediscovery lane (labelled INPUT_NOT_VERDICT). TYPED LICENSE
  DISCREPANCY: the R106 auditor verdict names PaECTER "CC-BY,
  attribution-only" but the canonical repo bytes carry
  "license: apache-2.0" (HF API tag + the model card "license:
  apache-2.0" line, both byte-read 2026-11-19); the NOTICE row cites
  the byte-verified repo license and the discrepancy rides the run
  record for auditor re-adjudication. Weights cached locally, not
  redistributed.
- Inspect AI (UK AI Security Institute) — `inspect-ai` v0.3.291; MIT
  (PyPI classifier byte-read). The unattended 30-batch harness driver
  (the Task/solver/scorer + the eval log). Typed deviations: this
  build's `@scorer` requires `metrics=` and `@solver` requires
  `name=` (signature regressions vs the public docstrings — worked
  around at call sites, the library is NOT patched).
- baber/uspto_raw (HF mirror of the Google-Patents-form USPTO grant
  dump) — the real-bytes claims sample (12 granted chemistry patents,
  `eval/r106_score9_patentchem/real_claims_sample.jsonl`). TYPED: the
  mirror carries no license tag; the underlying texts are USPTO grant
  publications; the Google Patents Public Data form is attributed;
  attribution-only usage (excerpts + derived rule outputs committed).
- big_patent subset b (HF `NortheasternUniversity/big_patent`,
  CC-BY-4.0 tag byte-read) — the FIRST real-corpus pick for the
  claims leg; the HF parquet carries only description+abstract (NO
  claims field) so it was NOT adopted for the leg (the typed
  correction in the extraction record); listed here for the
  attribution discipline (Art. 16 accounting: the miss is disclosed,
  not silent).

## Score-9 exclusions (typed)

- USPTO bulk downloads (bulkdata.uspto.gov / data.uspto.gov bulk /
  the PatentChem Zenodo 75GB mirror) — NOT fetched: sandbox-egress
  probes all failed (typed infra state, Art. 15) and the full-year
  bulk exceeds the rootfs; the claims leg accepted on the
  bounded real sample instead (Art. 22).
