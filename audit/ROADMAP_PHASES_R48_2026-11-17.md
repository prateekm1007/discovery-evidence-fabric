# GOVERNING ROADMAP — Phases 0-5 (owner-authored, auditor-adopted R48, 2026-11-17)
Scores are estimates, not measurements. A phase is DONE only when its gate passes on data the builder did not tune on.
RULES: no rented compute (gateway + judge queue only); no new guard or claim kinds; >=30% of changed lines per round in engine code.
SCALE: 4=now (strong eval discipline, no holdout accepted, engine off measured path); 5=custody fixed+measured path decided+physics computed; 6=a sealed set accepted (mean>=3.0, 0 violations, CI excludes 3.0); 7=two consecutive sealed sets >=3.3 with engine on measured path; 8=non-obvious+viable by blind external rating within speed budget; 9=external ground truth (post-cutoff rediscovery + unattended end-to-end).
## Phase 0 custody+scope (4->4.5)
OWNER: move every *_PRIVATE.json rubric out of the public repo; encrypt with owner-only passphrase; treat every credential that touched public history as burned.
CODER: secret scan over ALL refs; ledger entry naming the measured path (engine mechanism_space vs wrapper r40_machine_v77).
GATE: no plaintext rubric or token reachable from any public ref; one ledger entry names the measured path.
## Phase 1 checkable claims (->5)
Computed physics: CoolProp+ht+fluids+thermo+chemicals+tespy+units lib; each intervention emits a running calculation; direction-of-effect from the SIGN of that calculation.
Structured output: schema enums for allowed measures + permitted signals; DELETE the prose regex scanners (F57/F58/F59).
GATE: >=80% numeric claims run with units checked; 0 allowed-measures violations + 0 false input-flags on labelled v6/v7; 0 inverted directions.
## Phase 2 generation quality (->6)
Typed operators: TRIZ matrix as OUR OWN JSON; K>=3 short candidates each a different principle; expand only the winner.
Cheap novelty gate: TF-IDF cosine first, LLM judge only borderline.
Schedule cap: schedule/duty-cycle family <=1 per 6 interventions.
Ablation: every addition ablated at matched budget on DEV (burned v1-v7; v8 now DEV-only); delete if it doesn't earn its place.
GATE: auditor scores a NEWLY SEALED set n>=30 at mean>=3.0, 0 violations, CI excluding 3.0.
## Phase 3 optimize+speed (->7)
GEPA: compile directive against DEV labels, held-out DEV slices.
Best-first search: AIDE-style ONLY now (computed checks give a trustworthy metric).
Conformal predictors: MAPIE+telemanom validated on C-MAPSS/XJTU-SY/CWRU with own loaders.
Speed: median <=2min, worst <=5min per problem, 429-safe backoff.
GATE: two consecutive sealed sets mean>=3.3; measured path through engine; pre-registered gain on a DEV slice the optimizer never saw.
## Phase 4 real novelty (->8) — AGENT-RUN (AM46 owner directive: AI agents replace human experts)
Prior-art distance: SPECTER2-class embeddings vs patents+papers (deterministic). Cross-domain retrieval: MOOSE-Chem inspiration pattern; failed-mechanism memory blocks repeats.
BLIND AI PANEL: >=3 judge agents, >=2 model families distinct from generator AND each other; every rung R-CAL qualified (accuracy>=0.8, answered_rate>=0.9) before service; blind + position-swapped; structured per-axis scores; judge!=generator (provider AND model).
PANEL CALIBRATION GATE: agreement>=0.7 (alpha>=0.6) on 10-item slice; AUC>=0.8 ranking known-novel over known-obvious controls; auditor cross-check>=20% (family disclosed); disagreement rule pre-registered.
GATE: >=50% viable+non-obvious by calibrated blind panel; >=0.2 cosine separation; 0 canary completions. LABEL: AI-rated, not physical efficacy.
## Phase 5 external proof (->9) — AGENT-RUN (AM46)
Rediscovery: >=30 granted patents/papers AFTER generator cutoff (canary-confirmed); engine sees only the problem; auditor agents score blind vs OFF-REPO rubrics. Human-produced artifacts = external ground truth; agent scoring against them is objective.
VALIDATION TIERS: T1 executable computed/simulated falsifier (unit-checked, sandboxed, evidence committed); T2 retrieval-agent cross-check, every citation resolves; T3 owner physical test OPTIONAL gold label. Externally confirmed = >=1 candidate passes T1+T2 (agent-validated).
Unattended: 30-batch end-to-end, 0 human interventions.
GATE: >=40% key mechanisms recovered (pre-registered); >=1 agent-validated candidate; unattended pass. LABEL: physical efficacy unclaimed unless T3.
LOOP: auditor agents author/seal -> builder agents generate -> verifier agents recompute -> calibrated panel rates -> retrieval agents check prior art -> burn -> next. Gateway+judge queue only. Only owner act remaining: P0 one-time custody+rotation.
