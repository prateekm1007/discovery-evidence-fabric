# ROADMAP 4->9 DETAILED (auditor R50 plan, landed R52; governing with ROADMAP_PHASES_R48 as amended by AM46)
RULES EVERY ROUND: FULL constitution reads; claim-before-work (push=mutex); executor/verifier lanes; >=30% changed lines in discovery_fabric/ engine code (F63 watch); Art.27 capability ledger + Art.16 retirements; pushed CI green API-read with quoted check-runs; secret-grep staged diff; Session/Work-Id trailers; no rented compute; no new guard/claim kinds; DEV=burned v1-v8; acceptance=fresh confidential sealed sets only (frozen machine, one-shot, attestation pre-scoring, burn after); NOTICE attribution for copied permissive code; never pass a gate on a point estimate.
## P0 custody+scope (4->4.5, 1-2 rounds) HARD PREREQUISITE
OWNER one-time: move/encrypt *_PRIVATE.json to private custody + scrub public history; rotate PAT + Aug-18 keys (burned). Thereafter auditor agents manage custody.
CODER: [DONE R50] red CI fixed; all-refs prefix enumeration; detect-secrets pre-commit. [DONE R51] content-level verification (1 full-format token = F45 PAT, 2 paths r448/visual-lab; F60 unauth 200/8385). [R52] gitleaks GIT-MODE full history (commit messages carry the 2 Aug-18 keys — tree-blob scan misses them). Escalate owner act each round until landed.
GATE: 0 plaintext rubrics/tokens on any public ref (unauth probes + gitleaks); measured path named (DONE: ROUTE engine).
## P1 checkable claims (->5, 3-5 rounds)
[DONE R50] physics_checks.py slice (pint+CoolProp, 1 relation). [DONE R51] candidate_schema.py 1.1.0 wrap-only enums (measure_class/signals_used/principle_id/mechanism_class), 1.0.0 hash byte-stable, 7/7 CI-wired. [DONE R47-cont] contract negative-case probe 14/14.
[R52+] P1.3 INTEGRATE: migrate scripts/v82_typed_population.py + v82_novelty_gate.py INTO discovery_fabric/engine/ (F63); wire mechanism_space.assemble_candidate -> candidate_schema 1.1.0 -> physics_checks -> binds; measured DEV path runs through the engine. Expand physics registry to >=6 relations (Arrhenius integral, NPSH/surge margin, LSI, frost psychrometrics, fouling U-degradation, Larson-Miller); direction-of-effect = SIGN of computed result. P1.4 labelled v6/v7 regression through integrated path; then Art.16 DELETE prose scanners.
GATE: >=80% numeric claims run unit-checked; 0 allowed-measures violations; 0 false input-flags; 0 inverted directions.
## P2 generation quality (->6, 3-5 rounds)
TRIZ as OWN JSON (39 params/40 principles/matrix; triz-engine MIT reference + NOTICE). K>=3 distinct-principle plans, expand winner only (v82 semantics exist — migrate). Schedule family cap 1/6. TF-IDF novelty first, LLM borderline only (exists — migrate). Matched-budget DEV ablations vs V7.7 (adopt iff schedule-share<=17%, ALLOWED_ROW_OUTSIDE=0, mean no drop; else DELETE). v9: fresh n>=30 confidential set post-P0, frozen engine-route machine, 30/30 attestation, auditor scores, burn.
GATE: mean>=3.0, 0 violations, 0 inverted, 0 unavailable-input, CI excludes 3.0 (n=30, SD~0.7 -> mean>~3.25), VALID.
## P3 optimize+speed (->7, 3-5 rounds)
GEPA (MIT) offline compile vs DEV labels, held-out slices, pre-registered gain. AIDE best-first (MIT agent.py/journal.py + NOTICE) ONLY after computed metric trustworthy. MAPIE (BSD-3) + telemanom (verify license text) conformal predictors, own loaders C-MAPSS/XJTU-SY/CWRU, coverage>=1-alpha, FA<=1/yr computed. Speed median<=2min worst<=5min, 429-safe backoff.
GATE: two consecutive sealed sets >=3.3; engine on measured path; pre-registered DEV gain.
## P4 real novelty (->8, 3-4 rounds, AGENT-RUN AM46/R-PANEL)
SPECTER2-class prior-art distance (>=0.2 cosine control separation). MOOSE-Chem inspiration retrieval + failed-mechanism memory. Blind panel >=3 agents >=2 non-generator families, R-CAL qualified (qwen MET; deepseek post-c-0043; third from queue), agreement>=0.7/AUC>=0.8, auditor cross-check>=20%, pre-registered composition+disagreement rule. Canaries on every sealed set.
GATE: >=50% viable+non-obvious; >=0.2 separation; 0 canary completions; speed budget. LABEL: AI-rated.
## P5 external proof (->9, 4-6 rounds, AGENT-RUN)
>=30 post-cutoff patents/papers (canary-confirmed), engine sees problem only, off-repo rubrics, pre-registered key mechanisms. T1 computed/simulated falsifier + T2 citation-resolving retrieval; >=1 agent-validated (T1+T2); T3 optional. Unattended 30-batch, 0 human interventions.
GATE: >=40% mechanisms recovered; >=1 agent-validated; unattended pass. LABEL: physical efficacy unclaimed unless T3.
## RISKS
P0 slip blocks all acceptance (escalate). Engine integration crux: negative-case tests before ablation. Judge-queue 429/503: backoff + R-JUDGE (no silent rung substitution). Rediscovery cutoff: canary-probe every item. ~17-27 rounds total; delete failed ablations.


## COPYABLE WORLDWIDE TECHNIQUES (license-verified R92, 2026-11-18) — mapped to phases
Deep research of GitHub/global sources; licenses read via GitHub API. Copy only permissive (MIT/Apache/BSD) with attribution+NOTICE. Each item targets a measured gap. EXCLUSIONS: Moirai (CC BY-NC 4.0, non-commercial), AI-Scientist-v2 (restrictive custom), new-api (AGPL), EnvCommons/PaperBench (no license — use openai/preparedness MIT), AutoTRIZ casebase (no license — encode TRIZ ourselves), jataware open-coscientist (Commons Clause).

### Generation quality + repair convergence (P1/P2 — the current frontier, mean stuck ~3.1, 27/30 burn full repair budget)
- Reflexion (noahshinn/reflexion, MIT): verbal self-reflection MEMORY carrying error patterns across repair attempts. Copy the reflection-memory pattern into the repair loop so each attempt learns from the prior failure signature. Acceptance: >=50% of rows reach zero findings within budget on v11 (convergence gate).
- Self-Refine (madaan/self-refine, Apache-2.0): feedback->refine->stop loop structure. Copy the structured stop criterion (not fixed budget burn). Acceptance: same convergence gate.
- CRITIC (microsoft, tool-interactive critiquing, paper pattern): self-correct by CALLING external tools to verify+amend, not just flag. Wire the critic to call the physics/equilibrium tools to correct first-pass defects. Acceptance: first-pass defect incidence drops vs v10.
- AIDE (WecoAI/aideml, MIT): solution-space TREE SEARCH (best-first over diverse candidates, metric-pruned). Replace single-chain repair with population tree search scored by the binds. Acceptance: >=3 distinct candidates/intervention, best-first selection, schedule-family <=17%.
- DSPy + GEPA (stanfordnlp/dspy MIT, gepa-ai/gepa MIT): compile the generation directive OFFLINE against the labelled bind corpus (reflective prompt evolution, ~35x fewer rollouts than RL). Acceptance: >=10-point bind-pass gain on a held-out labelled slice; zero LLM in CI.
- TextGrad (zou-group/textgrad, MIT): text-as-gradient directive optimization (alternative/complement to GEPA).

### Physics/chemistry correctness (the HO10-03 inverted-equilibrium class)
- Cantera (Cantera/cantera, BSD-3-Clause; GitHub NOASSERTION — verify license text): equilibrate() COMPUTES chemical equilibrium composition. STRONGEST fix for the equilibrium-direction class: compute the equilibrium and check the claimed T/P/concentration direction against the computed result, instead of the LLM guessing. Acceptance: HO10-03-class claims verified against computed equilibrium; 0 inverted on computed rows.
- ChemCrow (ur-whitelab/chemcrow-public, MIT): LLM + 18 chemistry tools (RDKit/reaction/property). Copy the tool-integration pattern for chemistry reasoning. Acceptance: chemistry claims tool-verified.
- CoolProp (MIT) / thermo (CalebBell/thermo, MIT): extend the existing physics layer to equilibrium/phase checks.
- PySR (astroautomata/PySR, Apache-2.0): symbolic regression to DISCOVER governing relations from data (predictor feature laws). Acceptance: predictors carry discovered symbolic laws with units.

### Diversity (monoculture)
- pyribs (icaros-usc/pyribs, MIT): MAP-Elites/CMA-ME quality diversity — fill a grid of mechanism niches with the best candidate per cell (structural diversity vs our cap). Acceptance: mechanism-class grid coverage; schedule-family <=17%.

### P3 predictors + speed/efficiency
- TimesFM (google-research/timesfm, Apache-2.0 code+weights<=2.5) / Chronos (amazon-science/chronos-forecasting, Apache-2.0): time-series FOUNDATION models, zero-shot forecast/anomaly -> predictor lead-time + FA quality. Acceptance: validated on C-MAPSS/XJTU-SY/CWRU with conformal FA control. (Moirai EXCLUDED: CC BY-NC.)
- MAPIE (scikit-learn-contrib/MAPIE, BSD-3): conformal prediction intervals -> computed FA-rate control (<=1 FA/year). Acceptance: coverage >=1-alpha.
- vLLM (vllm-project/vllm, Apache-2.0) / SGLang (sgl-project/sglang, Apache-2.0): high-throughput serving if self-hosting a frontier model. Acceptance: speed median <=2min/worst <=5min.
- RouteLLM (lm-sys/RouteLLM, Apache-2.0): cost-aware strong/weak routing -> efficiency. Acceptance: cheap model for easy rows, frontier for hard; cost/row drops.
- LiteLLM (BerriAI/litellm, MIT core; GitHub NOASSERTION dual-license — verify): gateway requested-vs-served logging (R-REQID attestation). Beware the response-model alias-overwrite pitfall.

### P4 novelty/viability + P5 external proof
- SPECTER2 (allenai/SPECTER2, Apache-2.0): scientific document embeddings -> prior-art distance (novelty). Acceptance: separates known-novel/known-obvious >=0.2 cosine. PaECTER (patent embeddings, CC-BY per paper — verify) for patents.
- Inspect (UKGovernmentBEIS/inspect_ai, MIT): eval transcript + blind cross-family panel scoring + unattended batch harness (P5). Acceptance: panel agreement >=0.7; unattended 30-batch 0 interventions.

### Integration discipline
Every copied technique: (1) attribution+NOTICE; (2) a deterministic acceptance test wired into CI (exists-but-does-not-gate is a defect); (3) ablated at matched budget on DEV before adoption, deleted if it doesn't earn its place; (4) no frozen-file edits without a conscious CI-gated re-freeze; (5) generation-side improvement, not just another detection bind (AM78 P3).


## COPYABLE TECHNIQUES — UPDATE 2 (R93, worldwide incl. China; license-verified via GitHub API)
Continuing the worldwide search per owner directive. New license-verified copyable items mapped to current gaps:

### Time-series foundation models (P3 predictors — replace hand-rolled inference)
- Time-MoE (Time-MoE/Time-MoE, Apache-2.0, ICLR 2025 Spotlight): time-series foundation model scaled to 2.4B params, zero-shot forecast/anomaly. Acceptance: predictors validated on C-MAPSS/XJTU-SY/CWRU with conformal FA control (MAPIE).
- MOMENT (moment-timeseries-foundation-model/moment, MIT, ICML'24): open time-series foundation model family (forecast/anomaly/classification/imputation/embeddings); pre-trainable on own data. Acceptance: same predictor gate.
- (TimesFM/Chronos already in Update 1; Moirai EXCLUDED CC BY-NC.)

### Chemistry tool integration (the inverted-equilibrium / chemistry-correctness lever)
- ChemMCP (osu-nlp-group/chemmcp, Apache-2.0): MCP-compatible chemistry toolkit for LLM agents — wire equilibrium/property tools into the generation loop so chemistry claims are tool-verified, not guessed.
- CACTUS (pnnl/cactus, BSD-2-Clause): LLM agent + cheminformatics tools (PNNL). Complement to ChemCrow (MIT).
- Cantera (BSD-3, Update 1) remains the strongest fix: equilibrate() COMPUTES equilibrium composition; check the claimed direction against the computed result (kills the HO10-03/HO11-03 class at the source).

### Convergence / self-evolution (the repair-loop convergence gate, AM78 P2)
- Awesome-Self-Evolving-Agents (XMUDeepLIT, Xiamen U) — PAPER LIST only (no code license; use as a survey of self-evolving patterns, not copyable code). Reflexion (MIT) + Self-Refine (Apache-2.0) remain the copyable convergence patterns (already prototyped in scripts/r80_repair_convergence.py, c-0105 — DEV-stage, NOT yet wired into the frozen machine).

### Quality diversity (monoculture)
- qdpy (Map-Elites/CVT-Map-Elites/NSLC/SAIL) + VQ-Elites (unsupervised problem-agnostic QD) complement pyribs (MIT, Update 1).

### Frontier model class (AM78 P5 — acceptance runs need a serving frontier model)
- Intern-S1-Pro (Shanghai AI Lab, open-sourced Feb 2026, trillion-param science multimodal): POTENTIAL frontier-class generator, but GitHub license NONE/unverified — DO NOT copy until license confirmed; track as a candidate serving model for acceptance runs (the owner-funded-allowance path remains primary).

### Integration discipline (unchanged, AM79): attribution+NOTICE, CI-wired acceptance test, matched-budget DEV ablation before adoption, no frozen edits without CI-gated re-freeze, generation-side improvement not just detection binds.


## COPYABLE TECHNIQUES — UPDATE 3 (R93, worldwide incl. China; license-verified)
Addressing the convergence ablation's NOT_ADOPTED outcome: the prompt-refractory BILL_UNTAGGED class (27/30 rows) cannot be fixed by reflection alone (c-0106 ablation). The next leverage is **CRITIC tool-grounding** (generation-time tool calls that correct, not just flag) and **AIDE tree search** (population search over diverse candidates, metric-pruned).

### CRITIC tool-grounding (c-0107 Cantera + ChemMCP/CACTUS wired into the critic/generator)
- CRITIC pattern (microsoft, ICLR 2023; open-compass/CriticEval MIT benchmark): LLMs self-correct by CALLING external tools to verify and amend outputs, not just self-critique. Wire Cantera `equilibrate()` and ChemMCP/CACTUS chemistry tools into the generator so chemistry claims are tool-verified at generation time (kills the inversion class at the source; c-0107 is the mechanics).
- ChemAgent (paper, 137 chemical tools integrated): comprehensive tool pool for chemistry/materials — copy the tool-integration pattern.
- MatClaw (autonomous code-first LLM agent for materials, 2026): writes and executes Python directly in a sandboxed environment — the code-first execution pattern for chemistry claims.

### AIDE tree search (replace single-chain repair with population search)
- AIDE (WecoAI/aideml, MIT): tree-search agent that autonomously drafts, debugs, and benchmarks code until a user-defined metric is maximized. Copy the best-first tree-search pattern (diverse candidates, metric-pruned, refinement over attempts) to replace the single-chain repair loop that burns budget without converging on the prompt-refractory class.

### Scientific agent skills (P4/P5 novelty/viability)
- K-Dense-AI/scientific-agent-skills: 177 ready-to-use validated skills for AI agents (biology, chemistry, physics, engineering) — copy skill patterns for real-world validation.
- awesome-ai4s (HyperAI): 200+ AI4S papers/tools open source — survey for P4/P5.
- synthesis-agent (hspark1212): LLM agent for materials synthesis using Materials Project — copy the similarity-search-on-recipes pattern.

### Integration discipline (unchanged, AM79): attribution+NOTICE, CI-wired acceptance test, matched-budget DEV ablation before adoption, no frozen edits without CI-gated re-freeze, generation-side improvement not just detection binds.
