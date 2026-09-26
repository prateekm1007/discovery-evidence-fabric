// Types for the engine job API — mirrors toscanini/server.py payloads.

export type SessionStatus =
  | "BUILDING_PROBLEM"
  | "PENDING"
  | "RUNNING"
  | "COMPLETE"
  | "INTERRUPTED" // R392: worker died without a verdict (recoverable)
  | "ERROR_TRANSPORT"
  | "ERROR_BUILD"
  | "ERROR_RUN"
  | "ERROR_STUCK"
  | "RUN_BLOCKED_TRANSPORT" // R415: infrastructure-blocked, resumable — never a verdict
  // R446-C1 §4 (consumed by the UI from R458-C2 §4): the one-question
  // pause — the engine asked ONE material question; POST /answer resumes
  | "AWAITING_CLARIFICATION";

export interface SessionRow {
  session_id: string;
  title: string;
  status: SessionStatus;
  created_at: string;
  problem_id: string | null;
  final_status: string | null;
  origin: string;
  user_state_view?: UserStateView;
  // R463 (audit P1-2): steering continuity — the parent row marks a
  // thread that forked a new round
  has_fork?: boolean;
  // R464 (audit P1-2): a round opened by a steering action carries its
  // parent's id — the rail groups rounds under the investigation they
  // continue (the field already rides every /api/sessions row; the type
  // now says so).
  parent_session_id?: string | null;
}

// R394/R395: the user-facing run state — derived backend-side from the
// session record's own fields. The UI renders THIS, never raw
// machine-state combinations (COMPLETE + REJECTED etc.).
// R472 (audit P0-4): the no-survivor learning card — the terminal
// refusal that TEACHES: what was tested, the strongest failed
// hypothesis, the key missing evidence, and ranked next actions.
// Backend-derived from recorded fields only (toscanini/run_state.py
// learning_card); None for every non-no-survivor terminal.
export interface LearningCardAction {
  rank: number;
  action_kind: "ADD_EVIDENCE" | "REFINE_PROBLEM" | "NEW_TERRITORY";
  action: string;
  why: string;
}

export interface LearningCard {
  kind: "no_survivor_learning_card";
  what_was_tested: string;
  strongest_failed_hypothesis: string;
  key_missing_evidence: string;
  ranked_next_actions: LearningCardAction[];
  basis: string;
}

export interface UserStateView {
  user_state: string;
  label: string;
  meaning: string;
  decision: string;
  finished: boolean;
  found_something: boolean;
  rejected: boolean;
  package_available: boolean;
  machine_status?: string;
  // R414 (directive §18): the four terminal outcome states
  outcome?: RunOutcome;
  outcome_label?: string;
  // R472 (audit P0-4): the no-survivor learning card
  learning_card?: LearningCard | null;
}

export interface StageDigest {
  stage: string;
  status: string;
  records_found?: number;
  sources?: string[];
  sample_titles?: string[];
  mechanism?: string;
  intervention?: string;
  expected_effect?: string;
  falsification_test?: string;
  prior_art_count?: number;
  prior_art_titles?: string[];
  collisions?: { universe?: string; verdict?: string; result_count?: number }[];
  overall?: string;
  challenges?: { challenge?: string; verdict?: string; response?: string }[];
  count?: number;
  contradictions?: string[];
  experiment?: Record<string, unknown>;
  verdict?: string;
  reason?: string;
  epistemic_state?: Record<string, unknown>;
  action?: Record<string, unknown>;
  score?: number;
  breakdown?: Record<string, number>;
  // R397 physics stage (R401-WC2 fix: the PHYSICS digest carries the
  // lifecycle verdict + baseline outcome; typed explicitly so the
  // build's strict cast check passes without an unknown-cast)
  lifecycle_verdict?: string;
  baseline_outcome?: string;
}

export interface SessionDetail {
  session_id: string;
  title: string;
  user_text: string;
  status: SessionStatus;
  created_at: string;
  run_dir: string | null;
  problem_id: string | null;
  final_status: string | null;
  error?: string | null;
  stages?: StageDigest[];
  final_state?: Record<string, unknown> | null;
  package?: PackageInfo | null;
  invention_specification?: Record<string, unknown>;
  engineering_specification?: Record<string, unknown>;
  decisive_experiment?: Record<string, unknown>;
  // R540: the ranked result set — the contract's "ranked technology
  // packages" shape. One entry per admissible ranked survivor, each
  // carrying the six components (evidence, mechanism + kill, adversarial
  // disposition, engineering + model, decisive experiment, package) and a
  // mechanically traceable rank basis. The UI moves from a ranked result
  // directly to its package.
  ranked_results?: RankedDiscoveryResult | null;
  ranked_packages?: RankedPackage[] | null;
  // R541: per-rank candidate-bound package download routes — the UI's
  // "Download technology package #N" CTA resolves to a candidate-
  // specific route (?candidate=<id>), not one shared /package surface.
  ranked_package_downloads?: RankedPackageDownload[] | null;
  // R540: the three distinct completion states — never collapsed into a
  // single COMPLETE word (pipeline vs discovery vs technology-package).
  completion_states?: CompletionStates | null;
  evidence_pack?: { retrieval?: { source?: string; title?: string }[] };
  cemetery_update?: Record<string, unknown>;
  user_state_view?: UserStateView;
  // R414: the canonical DiscoveryRun state (directive §4) — carried by
  // the result endpoint; the UI reads phases/outcomes from here
  run_state?: RunStateObject;
  // R459 (audit P1-2): queue visibility — a queued run SAYS it is
  // waiting for a run slot (R459-reaudit: the engine holds a slot
  // pool) instead of spinning.
  queue_state?: { queued: boolean; reason: string; position?: number };
  // R459: the investigation thread — set on rounds opened by a
  // conversational action (the parent run's record stays untouched).
  parent_session_id?: string | null;
  // R461 (audit P0-2): the steering directive of an action-opened
  // round — recorded by the engine (toscanini/actions.py) and surfaced
  // through public_session_view; the conversation renders the user's
  // words from this record, never from a client-side guess.
  user_directive?: {
    action_id?: string;
    verb?: string;
    directive?: string;
    parent_session_id?: string;
  } | null;
  // R466 (reaudit residual friction): the round's DURABLE conversation
  // context — the engine appends the steering directive here at round
  // creation (an append-only guarded field, never cleared), while
  // user_directive is consumed and emptied by the worker at spawn.
  // The directive's words outlive the run start from THIS record.
  conversation?: {
    role?: string;
    text?: string;
    classification?: string;
    affects_canonical_state?: boolean;
  }[];
  // R459 (audit P0-3): attachments bound to this run (engine-side
  // custody; the conversation references them, never absorbs them)
  attachment_ids?: string[];
  // R458-C2 (§4): the one-question clarification pause — the engine set
  // status AWAITING_CLARIFICATION and asks exactly one material question
  // (C1's R446 §4 contract). The conversation renders it and the answer
  // resumes the SAME run via POST /api/run/{id}/answer.
  clarification?: {
    field?: string;
    question?: string;
    decision_changed?: string;
    score?: number;
    asked_at?: string;
  } | null;
  // R467 (audit P0-5): the typed "what changed because of your
  // direction" record — computed by the worker from the PARENT and
  // CHILD runs' own records (envelope_SYNTHESIZE.mechanism_map
  // identity comparison), never asserted. No-change is recorded
  // honestly as no-change.
  directive_outcome?: {
    parent_session_id?: string;
    directive?: string | null;
    parent_mechanism?: string | null;
    child_mechanism?: string | null;
    child_intervention?: string | null;
    mechanism_changed?: boolean;
    // R470 (audit P0-5): the typed compliance verdict — the card's
    // prose carries the honest semantics; the token rides as data.
    compliance_verdict?: string;
    territory?: {
      violation?: boolean;
      overlap_ratio?: number;
      overlapping_terms?: string[];
      checked_terms?: number;
    } | null;
    summary?: string;
    computed_at?: string;
    method?: string;
  } | null;
  // R471 (audit P1-2): the direction the user asked for while the run
  // was live — the engine refused the mid-flight mutation (typed 409,
  // never a false application) but RECORDED the words durably; the
  // terminal surface offers it as the next action through the same
  // canonical action endpoint.
  queued_directive?: {
    verb?: string;
    params?: Record<string, string>;
    directive?: string;
    queued_at?: string;
    queued_from_status?: string;
  } | null;
  // R471 (audit P0-5): the durable clarification answer — present
  // after reload, restart, and retry (field/answer + USER_STATED
  // provenance; the question is never repeated once answered).
  clarification_answer?: {
    field?: string;
    answer?: string;
    answered_at?: string;
    applied_at?: string;
    provenance?: string;
  } | null;
}

// R471 (audit P2-1): the MEASURED duration block — p50/p90 minutes
// from the deployment's own completed runs (n disclosed; null until
// enough completed runs exist — never an invented estimate).
export interface RunDurationStats {
  n: number;
  p50_minutes: number;
  p90_minutes: number;
  basis: string;
}

// R395: conversational Q&A over a run's / invention's own artifacts.
// status: ANSWERED (answer present) / NOT_IN_RECORD (honest refusal) /
// REFUSED_OVERCLAIM (reality-boundary guard) / REFUSED (run not
// finished) / TRANSPORT_ERROR / BAD_QUESTION.
export interface AskResponse {
  status: string;
  answer?: string;
  reason?: string;
  epistemic_class?: string;
  basis?: string;
  transport?: { provider?: string; model?: string };
}

// R395: the honest engine health, for the workspace status dot.
// R414: extended with the per-provider surface (directive §10) — the
// UI reduces this to something calm ("Discovery ready" / "one
// provider degraded"), never technical panic.
export interface HealthSummary {
  // R467 (the R466 P2 cold-start item): the server's top-level ok —
  // the warm marker the run-not-found grading reads (a 404 from an
  // engine never proven healthy this session is a cold-start window,
  // never evidence the run is absent).
  ok?: boolean;
  llm_transport_ready?: boolean;
  portfolio_ready?: boolean;
  engine_commit?: string;
  // R415 (P0 directive §13): the operational top-level block — the UI's
  // status wording is generated from these, never hand-written.
  showcase_ready?: boolean;
  discovery_ready?: boolean;
  retrieval_ready?: boolean;
  physics_ready?: boolean;
  reality_loop_ready?: boolean;
  product_status?: string;
  providers?: Record<
    string,
    { status?: string; available_models?: number }
  >;
  // R471 (audit P2-1): the measured p50/p90 duration block (null until
  // enough completed runs exist on this deployment)
  run_duration_stats?: RunDurationStats | null;
  durable?: { last_snapshot?: { at?: string; pushed?: boolean } };
  readiness?: {
    discovery_ready?: boolean;
    llm_ready?: boolean;
    showcase_ready?: boolean;
    physics_ready?: boolean;
    reality_loop_ready?: boolean;
    retrieval_ready?: { connectors_importable?: boolean };
    provider_count?: number;
    providers?: {
      provider: string;
      status: string;
      available: boolean;
      model?: string;
      last_success?: string | null;
      latency_ms?: number | null;
      rate_limit_state?: string;
    }[];
  };
}

export interface PackageInfo {
  complete?: boolean;
  maturity?: string;
  posture?: string;
  zip_name?: string | null;
  // R422 (directive 3): the honest document count from the package's own
  // manifest — rendered in the run-inspector Downloads block, never
  // hardcoded.
  document_count?: number | null;
  package_kind?: string | null;
  package_origin?: string | null;
}

export interface ShowcaseRow {
  slot: string;
  package_id: string;
  title: string;
  blurb: string;
  domain: string;
  demo_focus: boolean;
  parameter_count: number;
  glb: string;
}

export interface ShowcaseParam {
  param_id: string;
  value: number | string;
  unit?: string;
  envelope?: [number, number] | null;
  value_class?: string;
  category?: string;
  design_basis?: string;
}

export interface BriefSections {
  what_it_does?: string | null;
  why_it_matters?: string | null;
  established?: string | null;
  not_established?: string | null;
  decisive_experiment?: string | null;
  kill_condition?: string | null;
  source?: string;
}

export interface ShowcaseDetail {
  kind: "SHOWCASE";
  slot: string;
  package_id: string;
  title: string;
  blurb: string;
  domain?: string;
  demo_focus?: boolean;
  brief?: BriefSections;
  maturity?: string | null;
  maturity_basis?: string | null;
  known_blockers?: string[];
  evidence_class_counts?: Record<string, number>;
  first_decisive_work_package?: {
    work_package?: string | null;
    recorded_effort?: string | null;
  };
  mechanism_summary?: string;
  equations: { id?: string; expression?: string; caption?: string }[];
  parameters: ShowcaseParam[];
  key_dimensions: Record<string, Record<string, unknown>>;
  loop_verification_state?: string;
  model: {
    glb: string;
    glb_path: string | null;
    step?: string[];
    stl?: string[];
    svg_views?: string[];
    downloads?: { step?: string; stl?: string; glb?: string };
  };
  dossier: { pdfs: string[]; download: string };
  provenance_note?: string;
}

export interface EvalResult {
  status?: string;
  slot: string;
  param_id: string;
  new_value: number;
  unit?: string;
  value_class?: string;
  evidence_class: string;
  mutation_id: string;
  model_id?: string;
  measurements?: { objects?: Record<string, Record<string, unknown>> } | null;
  geometry_validation?: {
    valid?: boolean;
    checks?: Record<string, string>;
  };
  preview_glb?: {
    path: string;
    sha256: string;
    bytes: number;
    serve: string;
  };
  honesty?: string;
  record?: Record<string, unknown>;
}

export interface Refusal {
  status: string;
  reason: string;
}

// R390: the reality-loop closure (CEO directive #6 — the proof that an
// observation changes a technical decision). Mirrors
// toscanini/showcase.py::reality_loop_record().
export interface ConductanceRow {
  basis?: string;
  d_mm?: number;
  eta_mPa_s?: number;
  L_mm?: number;
  G_ml_min_mmHg?: number;
}

export interface RealityLoopRecord {
  kind: "REALITY_LOOP";
  slot: string;
  status?: string;
  loop_verification_state?: string;
  real_event?: boolean;
  observation?: {
    event_id?: string;
    origin?: string;
    origin_caveat?: string;
    quantity?: string;
    design_value?: number;
    measured_value?: number;
    relative_delta?: number;
    declared_uncertainty?: number;
    status?: string;
    design_declared_basis?: string;
  };
  causal_hypothesis?: {
    statement?: string;
    equation_basis?: string;
    residual_unknown?: string;
    deterministic?: boolean;
    llm_used?: boolean;
  };
  decision_change?: {
    question?: string;
    answer?: boolean;
    before?: string;
    after?: string;
    technical_result?: string;
    mutation?: {
      parameter?: string;
      from?: number;
      to?: number;
      envelope?: number[] | null;
      applied_to_canonical_package?: boolean;
    };
  };
  re_evaluation?: {
    evaluator?: string;
    before?: ConductanceRow;
    as_built?: ConductanceRow;
    after?: ConductanceRow;
    restored_ratio?: number;
  };
  causal_chain?: {
    stages?: string[];
    recorded_in_canonical_ledger?: boolean;
  };
  preview_glb?: string | null;
  honesty?: string;
}

// ---------------------------------------------------------------------------
// R414 product-integration types: the canonical DiscoveryRun state and
// the Canonical Invention Object (mirrors toscanini/run_state.py and
// toscanini/cio.py — the frontend READS these; it never re-derives
// states client-side and never infers an invention from a GLB).
// ---------------------------------------------------------------------------
// R416: the terminal outcomes — NO_DEFENSIBLE_INVENTION is a legacy
// key (pre-R416 records map onto UNDER_DEVELOPMENT server-side); the
// current invention is always presented, never a dead end.
export type RunOutcome =
  | "PENDING"
  | "INVENTION_SURVIVED"
  | "INVENTION_REQUIRES_EXPERIMENT"
  | "INVENTION_UNDER_DEVELOPMENT"
  | "INVENTION_KILLED_BY_CHALLENGE" // run_state.OUTCOME_KILLED_BY_CHALLENGE — the machine killed it, no verified survivor (R458-C2: consumed by isKilledByChallenge)
  | "FALSE_PREMISE_INCOHERENT"
  | "NO_DEFENSIBLE_INVENTION"
  | "RUN_BLOCKED";

export interface RunPhase {
  phase: string;
  label: string;
  state: "NOT_STARTED" | "IN_PROGRESS" | "DONE" | "FAILED";
  stages?: Record<string, string | undefined>;
}

export interface ProviderRouteHop {
  provider?: string;
  failure_type?: string;
  fallback_provider?: string;
}

export interface RunStateObject {
  run_id: string;
  user_problem: string | null;
  created_at: string | null;
  status: string;
  model_route: {
    calls?: {
      role?: string;
      provider?: string;
      model?: string;
      status?: string;
      failure_type?: string;
    }[];
    call_count?: number;
    note?: string;
  };
  retrieval_route?: string;
  evidence_state?: {
    state?: string;
    records_found?: number;
    sources?: string[];
  };
  mechanism_state?: {
    state?: string;
    mechanism?: string | null;
    intervention?: string | null;
  };
  invention_state?: {
    state?: string;
    final_status?: string | null;
    package_built?: boolean;
  };
  physics_state?: {
    state?: string;
    lifecycle_verdict?: string | null;
    baseline_outcome?: string | null;
  };
  novelty_state?: {
    state?: string;
    prior_art_count?: number;
    language_rule?: string;
  };
  attack_state?: { state?: string; overall?: string | null };
  experiment_state?: { state?: string; decisive_experiment_present?: boolean };
  package_state?: { state?: string; maturity?: string | null };
  failure_state?: {
    state?: string;
    error?: string | null;
    failed_stages?: Record<string, string>;
  };
  outcome: RunOutcome;
  outcome_label: string;
  outcome_basis: string;
  // R472 (audit P0-4): the no-survivor learning card rides the run
  // state object too (the backend projection attaches it wherever the
  // user_state_view is served)
  learning_card?: LearningCard | null;
  phase_progression?: RunPhase[];
  // R416: the invention generations (INVENTION 01, 02, ...) with
  // lineage, causal deltas, maturity labels and per-generation
  // geometry availability — the UI's generation navigation renders
  // THIS, never client-side inference.
  generations?: GenerationsProjection | null;
  evolution_state?: EvolutionLivePhase | null;
  // R510 dry-run cliff: canonical ranked portfolio projection (see
  // CanonicalPortfolioProjection). Served by the backend when the
  // run persisted CANDIDATE_PORTFOLIO.json; absent otherwise.
  portfolio?: CanonicalPortfolioProjection | null;
  schema_version?: string;
}

// R416: one architecture generation in the invention lineage.
export interface GenerationRecord {
  gen: number;
  label?: string | null;
  invention_id?: string | null;
  parent_id?: string | null;
  origin?: string | null;
  state?: string | null;
  maturity?: string | null;
  architecture?: {
    mechanism?: string | null;
    intervention?: string | null;
    expected_effect?: string | null;
    falsification_test?: string | null;
  };
  what_changed?: string | null;
  reason_for_change?: string | null;
  causal_delta?: {
    causal_change?: string | null;
    new_capability?: string | null;
    new_interaction?: string | null;
    new_operating_regime?: string | null;
    predicted_effect?: string | null;
    frontier_capability?: string | null;
    thirty_year_engine?: Record<string, string> | null;
    diagnosed_cause?: string | null;
  } | null;
  challenge?: {
    killed?: boolean;
    kill_stage?: string | null;
    kill_reason?: string | null;
    attack_overall?: string | null;
    independent_attack?: string | null;
    physics_lifecycle?: string | null;
    survived?: boolean;
    evidence_verified?: boolean;
    escalated_objection?: {
      preserved_objections?: { attack_class?: string | null; basis?: string | null }[];
      calibration_state?: string | null;
      measured?: {
        tpr_scoped?: number | null;
        fpr_known_good?: number | null;
        n_cases_attacked?: number | null;
      } | null;
      note?: string | null;
    } | null;
  };
  diagnosis?: { cause?: string | null; basis?: string[] } | null;
  fresh_evidence?: {
    n_items?: number | null;
    query?: string | null;
    status?: string | null;
    snapshot_version?: number | null;
  } | null;
  model_available?: boolean;
  stop_note?: string | null;
}

export interface GenerationsProjection {
  generations: GenerationRecord[];
  n_generations?: number;
  n_evolution_generations?: number | null;
  current_invention?: {
    gen?: number | null;
    invention_id?: string | null;
    state?: string | null;
    maturity?: string | null;
  } | null;
  survivor_reached?: boolean;
  survivor_gen?: number | null;
  stop_reason?: string | null;
  status?: string | null;
  honesty_contract?: string | null;
}

export interface EvolutionLivePhase {
  current_gen: number;
  phase: string;
  label: string;
  subline: string;
  note?: string;
}

// R510 dry-run cliff: the canonical ranked candidate portfolio as the
// backend serves it (projected verbatim from the run's
// CANDIDATE_PORTFOLIO.json — the UI reads rank, identity,
// distinctness and ranking basis from THESE fields and derives
// nothing: no client-side sort, no client-side scoring, no order
// inference. Null/absent when the backend has no portfolio record.)
export interface CanonicalPortfolioItem {
  candidate_id?: string | null;
  rank?: number | null;
  mechanism?: string | null;
  intervention?: string | null;
  predicted_effect?: string | null;
  falsification_test?: string | null;
  distinctness?: string | null;
  ranking_basis?: Record<string, number> | null;
  ranking_rule?: string | null;
  state?: string | null;
  origin?: string | null;
  provenance?: string | null;
}

export interface CanonicalPortfolioProjection {
  candidates: CanonicalPortfolioItem[];
  candidate_count_ranked?: number | null;
  mode?: string | null;
  r506_eligible?: boolean | null;
}

export interface CIOMaturity {
  design: boolean;
  simulation: boolean;
  evidence_supported: boolean;
  experimentally_verified: boolean;
  maturity_ladder: (string | null)[];
  reality_loop_state?: string;
  maturity_basis?: Record<string, string>;
}

// R540: the ranked result set — the contract's "ranked technology
// packages". The engine persists RANKED_DISCOVERY_RESULTS.json (the
// authority); the UI reads it verbatim and never re-sorts, re-scores, or
// infers a rank client-side.
export interface RankedResultComponents {
  evidence?: {
    records?: { id?: string | null; source?: string | null; frozen?: boolean }[];
    mechanism_source_span?: string;
    evidence_status?: string;
  };
  mechanism?: {
    mechanism?: string;
    intervention?: string;
    expected_effect?: string;
    falsification_test?: string;
    competing_considered?: string[];
  };
  adversarial?: {
    overall?: string | null;
    disposition?: "SURVIVED" | "KILLED" | "UNRESOLVED" | string;
    survived?: boolean;
    killed?: boolean;
    unresolved?: boolean;
    quality_verdict?: string | null;
    deficient_areas?: number | null;
  };
  engineering?: {
    geometry_present?: boolean;
    geometry?: Record<string, unknown>;
    engineering_core?: Record<string, unknown>;
    model_class?: string | null;
    limitations?: string;
  };
  decisive_experiment?: {
    experiment?: string;
    predicted_discriminator?: string;
    decision_rule?: string;
    execution_status?: string;
  };
  package?: {
    kind?: string;
    package_id?: string;
    rank?: number;
    note?: string;
    // R541: the candidate-bound package identity (each survivor's OWN
    // package, never a reused #1).
    zip_name?: string | null;
    maturity?: string | null;
    complete?: boolean;
    candidate_id?: string | null;
    zip_sha256?: string | null;
    zip_sha256_measured?: string | null;
    zip_sha256_matches?: boolean;
    manifest?: unknown;
  };
}

export interface RankedResultRecord {
  rank?: number;
  candidate_id?: string | null;
  key?: string | null;
  origin?: string | null;
  admissible?: boolean;
  selected?: boolean;
  components?: RankedResultComponents;
  rank_basis?: Record<string, unknown>;
  // R541: the candidate-bound package record (each survivor's OWN
  // package, never a reused #1)
  package?: {
    kind?: string;
    zip_name?: string | null;
    maturity?: string | null;
    complete?: boolean;
    candidate_id?: string | null;
    rank?: number;
    package_id?: string | null;
    zip_sha256?: string | null;
    zip_sha256_measured?: string | null;
    zip_sha256_matches?: boolean;
    manifest?: unknown;
  };
  discovery_completed?: boolean;
}

export interface RankedDiscoveryResult {
  schema?: string;
  run_id?: string;
  final_status?: string | null;
  ranked_results?: RankedResultRecord[];
  selected_candidate?: string | null;
  n_admissible?: number;
  n_killed?: number;
  n_ranked?: number;
  n_complete_packages?: number;
  completion?: CompletionStates;
  diagnostic_only?: boolean;
  derivation_error?: string;
}

// R541: a per-rank candidate-bound package download route (the UI's
// "Download technology package #N" CTA target).
export interface RankedPackageDownload {
  rank?: number;
  candidate_id?: string | null;
  package_zip?: string | null;
  package_sha256?: string | null;
  complete?: boolean;
  download_url?: string | null;
}

// R540: a ranked survivor with its attached technology package (the
// session-served shape — one entry per admissible ranked survivor).
export interface RankedPackage {
  rank?: number;
  candidate_id?: string | null;
  key?: string | null;
  origin?: string | null;
  admissible?: boolean;
  selected?: boolean;
  components?: RankedResultComponents;
  rank_basis?: Record<string, unknown>;
  package?: {
    kind?: string;
    zip_name?: string | null;
    maturity?: string | null;
    complete?: boolean;
    candidate_id?: string | null;
    rank?: number;
    package_id?: string | null;
    zip_sha256?: string | null;
    zip_sha256_measured?: string | null;
    zip_sha256_matches?: boolean;
    manifest?: unknown;
  };
  discovery_completed?: boolean;
}

// R540: the three distinct completion states — the contract's
// success-state semantics. Never collapsed into one COMPLETE word:
// a pipeline that ran, an admissible discovery, and a compiled package
// are three separate, explicitly recorded states.
export interface CompletionStates {
  PIPELINE_COMPLETED?: boolean;
  DISCOVERY_COMPLETED?: boolean;
  TECHNOLOGY_PACKAGE_COMPLETED?: boolean;
  FINISHED_DISCOVERY?: boolean;
  invariant?: string;
}

export interface CIO {
  present: boolean;
  kind?: string;
  schema_version?: string;
  legal_position?: string;
  novelty_language?: string;
  identity?: {
    invention_id?: string | null;
    problem?: string | null;
    mechanism?: string | null;
    novelty_hypothesis?: string | null;
    survivor?: boolean;
    final_status?: string | null;
  };
  maturity?: CIOMaturity;
  evidence?: {
    records?: {
      title?: string;
      source?: string;
      evidence_class?: string;
    }[];
    record_count?: number;
    prior_art?: { searched?: boolean; note?: string };
  };
  engineering?: {
    specification_present?: boolean;
    parameters?: {
      param_id?: string;
      value?: number | string;
      unit?: string;
      category?: string;
      value_class?: string;
      envelope?: [number, number] | null;
    }[];
  };
  geometry?: {
    present: boolean;
    class?: string | null;
    conceptual?: boolean;
    glb?: string | null;
    glb_sha256?: string | null;
    step?: string[];
    stl?: string[];
    svg_views?: string[];
    parametric_model_present?: boolean;
    cad_pipeline_status?: string;
    bridge_outcome?: string | null;
    bridge_why?: string | null;
    authority?: string;
    // R419 section 12: the named components from the bridge report —
    // the inspection panel renders these; click = viewer highlight
    components?: (
      | string
      | { name?: string; role?: string; type?: string }
    )[];
  };
  simulation?: {
    executed?: boolean;
    lifecycle_verdict?: string | null;
    baseline_outcome?: string | null;
    epistemic_class?: string | null;
    assumption?: string;
  };
  // R419: the render gallery contract — pointers the UI renders ONLY
  // from the CIO (the frontend never invents render availability).
  // R420: status may be "RENDERING" while the async render job finishes
  // the presentation artifacts automatically (calm pending state —
  // never a maturity statement); samples/resolution disclose the
  // achieved quality of a possibly degraded async-ladder attempt.
  visualization?: {
    renders?: {
      status?: string;
      pipeline?: string;
      pinned_blender?: string;
      renderer_stack?: Record<string, unknown>;
      is_conceptual?: boolean;
      hero_png?: string | null;
      hero_glb?: string | null;
      section_png?: string | null;
      section_glb?: string | null;
      exploded_png?: string | null;
      exploded_glb?: string | null;
      poster_png?: string | null;
      dimension_png?: string | null;
      orthographic?: Record<string, string>;
      turntable_frame_count?: number;
      turntable_first?: string | null;
      visual_gate?: {
        verdict?: string;
        hero_suppressed?: boolean;
        failed_rules?: string[];
      };
      missing?: string[];
      presentation_rule?: string;
      note?: string;
      enqueued_by?: string;
      samples?: number;
      resolution?: number[];
    };
    viewer_required?: string[];
  };
  reality_loop?: { state?: string };
  downloads?: {
    package_zip?: string | null;
    package_maturity?: string | null;
    package_kind?: string | null;
    package_origin?: string | null;
    package_kind_note?: string;
    document_count?: number | null;
  };
  experiment?: { decisive_experiment?: unknown; status?: string };
  language_guard?: { clean?: boolean; violations?: string[] };
  note?: string;
}

// R419 section 11: the 8-section technical essay (the package PDF's
// narrative, served as structured JSON from the same canonical state).
export interface EssayBody {
  section_order: string[];
  sections: Record<string, string>;
  structure?: string;
}

// ---------------------------------------------------------------------------
// R430.1 — the Scientific Technology Artifact Workspace
// ---------------------------------------------------------------------------

// Section 7: structured scientific events (closed vocabularies server-side;
// the frontend RENDERS these and never upgrades a status or class).
export type EventStatus =
  | "QUEUED"
  | "ACTIVE"
  | "COMPLETED"
  | "BLOCKED"
  | "FAILED_INFRASTRUCTURE"
  | "FAILED_SCIENTIFIC"
  | "UNKNOWN";

export type EpistemicClass =
  | "RETRIEVED"
  | "INFERRED"
  | "HYPOTHESIZED"
  | "COMPUTED"
  | "SIMULATED"
  | "ENGINEERING_DEFINED"
  | "PHYSICALLY_OBSERVED"
  | "UNKNOWN";

export interface ScienceEvent {
  event_id: string;
  investigation_id: string;
  seq: number;
  stage: string;
  kind: string;
  status: EventStatus;
  summary: string;
  epistemic_class: EpistemicClass;
  basis_ref: string;
  timestamp?: string | null;
  generation?: number | null;
  [k: string]: unknown;
}

export interface GauntletCard {
  stage: string;
  label: string;
  mark: string;
  state: string;
  summary?: string;
  events: string[];
}

export interface EventsBody {
  investigation_id: string;
  status: string;
  event_count: number;
  events: ScienceEvent[];
  gauntlet: GauntletCard[];
}

export type TabAvailability =
  | "AVAILABLE"
  | "PENDING"
  | "UNAVAILABLE"
  | "NOT_ESTABLISHED";

export interface EvidenceLedgerItem {
  id: string;
  title: string;
  source?: string | null;
  source_uri?: string | null;
  doi?: string | null;
  publication_date?: string | null;
  retrieval_timestamp?: string | null;
  evidence_class?: string | null;
  provenance_id?: string | null;
  used_in_design: boolean;
}

export interface DossierTab {
  availability: TabAvailability;
  epistemic_class: EpistemicClass;
  note: string;
  [k: string]: unknown;
  // tab-specific fields (kept loose like CIO — the backend is the
  // authority; the frontend renders, never re-derives)
  items?: EvidenceLedgerItem[];
  retrieved_count?: number;
  used_count?: number;
  reason?: string | null;
  glb?: string | null;
  geometry_class?: string | null;
  conceptual?: boolean;
  download?: string | null;
  primary_action?: string;
  zip_name?: string | null;
  package_maturity?: string | null;
  document_count?: number | null;
  key_unknowns?: { statement?: string; priority?: string | null }[];
  status_line?: string;
  problem?: string | null;
  mechanism?: string | null;
  strongest_evidence?: EvidenceLedgerItem | null;
  strongest_challenge?: string | null;
  decisive_experiment?: string | null;
  epistemic_status?: string;
  contract?: Record<string, { status?: string; value?: unknown }> | null;
  recorded?: unknown;
  execution_note?: string;
  // R451-C2.1: the typed geometry/visual state — the UI consumes THIS
  // (backend-derived), never a missing-file inference
  geometry_state?: string;
  presentation_cause?: string | null;
  geometry_state_detail?: string | null;
  // R451-C2.2: the typed visual-join state + the artifact contract
  // (both backend-derived; consumed verbatim, never re-derived)
  visual_join_state?: string | null;
  visual_join_detail?: string | null;
  visual_join_cause?: string | null;
  pending_render_job?: string | null;
  geometry_contract?: Record<string, unknown> | null;
  // R451-C2.3 §1/§2: the contract's ENGINEERING authority verdict and
  // the two separated boundary states — ENGINEERING_GEOMETRY_READY
  // (verified artifact + explicit engineering authority) and
  // VISUAL_INPUT_READY (the canonical GLB contract the Visual
  // Compiler consumes; a valid STEP never satisfies it by itself)
  engineering_authority?: "ENGINEERING" | "CONCEPTUAL" | "UNKNOWN" | null;
  engineering_geometry_ready?: boolean;
  visual_input_ready?: boolean;
  visual_input_basis?: string | null;
}

export interface FalsificationRecord {
  kind: "FALSIFICATION_DOSSIER" | "VALIDATION_INCOMPLETE" | "DEVELOPMENT_RECORD";
  cause?: string;
  detail?: string;
  scientific_conclusions?: string;
  note?: string;
  stop_reason?: string | null;
  initial_candidate?: string | null;
  challenge_condition?: string;
  observed_failure?: string | null;
  rejected_mechanism?: string | null;
  why_it_failed?: string | null;
  what_remains_unknown?: string | null;
  epistemic_class?: string;
  basis?: string;
}

export interface DossierBody {
  kind: "TECHNOLOGY_DOSSIER";
  schema_version: string;
  investigation_id: string;
  derived_from: string;
  running: boolean;
  tabs: Record<
    "overview" | "design" | "evidence" | "engineering" | "experiment" | "transfer",
    DossierTab
  >;
  falsification?: FalsificationRecord | null;
  // R451-C2.1: the DISCOVERY PIPELINE strip projection (backend-derived)
  pipeline?: PipelineStage[];
}

// R451-C2.1 — one row of the DISCOVERY PIPELINE strip. The status
// vocabulary is backend-owned (toscanini/dossier.py::pipeline_projection);
// the frontend renders it verbatim.
// R451-C2.2 — `blocked_class` carries the typed blocked reason class
// (VISUAL_GATE / PACKAGE_INTEGRITY / SCIENTIFIC / INFRASTRUCTURE /
// JOIN_FAILURE / NOT_ATTEMPTED / RENDERER_UNAVAILABLE /
// RELEASE_UNVERIFIED / VISUAL_INPUT) when the row is
// stopped or paused — the directive's blocked-status disambiguation,
// backend-owned and rendered verbatim.
export interface PipelineStage {
  key: string;
  label: string;
  status: "RECEIVED" | "IN_PROGRESS" | "NOT_REACHED" | "STOPPED" |
    "PAUSED_INFRASTRUCTURE";
  detail?: string | null;
  blocked_class?: string | null;
}
