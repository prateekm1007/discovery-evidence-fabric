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
