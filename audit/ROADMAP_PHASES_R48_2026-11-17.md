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
## Phase 4 real novelty (->8)
Prior-art distance: SPECTER2-class embeddings vs patents+papers.
Cross-domain retrieval: MOOSE-Chem inspiration pattern; failed-mechanism memory blocks repeats.
Blind rating: >=3 domain experts OR cross-family judge panel calibrated to them.
GATE: >=50% interventions viable+non-obvious; novelty distance separates known-novel from known-obvious by >=0.2 cosine; 0 canary completions.
## Phase 5 external proof (->9)
Rediscovery: >=30 granted patents/papers published after generator training cutoff (canary-confirmed); engine sees only the problem; auditor scores blind vs rubrics stored OFF-REPO.
Real-world validation: >=3 generated candidates/quarter to external validation.
Unattended: a 30-batch completes end-to-end with 0 human interventions.
GATE: >=40% key mechanisms recovered (pre-registered); >=1 externally confirmed candidate; unattended run passes.
NOTE: P4/P5 depend on owner-provided domain experts + real-world tests; without them the ceiling is ~7.
