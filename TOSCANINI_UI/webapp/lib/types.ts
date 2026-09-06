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
  | "ERROR_STUCK";

export interface SessionRow {
  session_id: string;
  title: string;
  status: SessionStatus;
  created_at: string;
  problem_id: string | null;
  final_status: string | null;
  origin: string;
  user_state_view?: UserStateView;
}

// R394/R395: the user-facing run state — derived backend-side from the
// session record's own fields. The UI renders THIS, never raw
// machine-state combinations (COMPLETE + REJECTED etc.).
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
  evidence_pack?: { retrieval?: { source?: string; title?: string }[] };
  cemetery_update?: Record<string, unknown>;
  user_state_view?: UserStateView;
  // R414: the canonical DiscoveryRun state (directive §4) — carried by
  // the result endpoint; the UI reads phases/outcomes from here
  run_state?: RunStateObject;
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
// The four terminal outcomes (directive §18) + the live PENDING state.
export type RunOutcome =
  | "PENDING"
  | "INVENTION_SURVIVED"
  | "INVENTION_REQUIRES_EXPERIMENT"
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
  phase_progression?: RunPhase[];
  schema_version?: string;
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
    glb?: string | null;
    step?: string[];
    stl?: string[];
    svg_views?: string[];
    parametric_model_present?: boolean;
    cad_pipeline_status?: string;
    authority?: string;
  };
  simulation?: {
    executed?: boolean;
    lifecycle_verdict?: string | null;
    baseline_outcome?: string | null;
    epistemic_class?: string | null;
    assumption?: string;
  };
  reality_loop?: { state?: string };
  downloads?: {
    package_zip?: string | null;
    package_maturity?: string | null;
    counsel_package?: string;
    note?: string;
  };
  experiment?: { decisive_experiment?: unknown; status?: string };
  language_guard?: { clean?: boolean; violations?: string[] };
  note?: string;
}
