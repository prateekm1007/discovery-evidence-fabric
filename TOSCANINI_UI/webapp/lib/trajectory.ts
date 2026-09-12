// R450-C2 — the trajectory layer's shared types and fail-closed client
// helpers. These mirror visual-lab/trajectory/schema.py (the canonical
// projection). The UI renders the projection VERBATIM; it never derives,
// upgrades, or interprets an epistemic badge client-side (the frontend
// claims must be traceable to backend truth — GOVERNANCE principle 7).

export type EpistemicBadge =
  | "MEASURED"
  | "SIMULATED"
  | "INFERRED"
  | "PROPOSED"
  | "UNVERIFIED";

export const EPISTEMIC_BADGES: EpistemicBadge[] = [
  "MEASURED",
  "SIMULATED",
  "INFERRED",
  "PROPOSED",
  "UNVERIFIED",
];

export type PredictionOutcome =
  | "HELD"
  | "REFUTED"
  | "INDETERMINATE"
  | "NOT_EVALUATED";

export const PREDICTION_OUTCOMES: PredictionOutcome[] = [
  "HELD",
  "REFUTED",
  "INDETERMINATE",
  "NOT_EVALUATED",
];

// Client-side fail-closed badge guard: an unknown badge renders as
// UNVERIFIED (never silently re-styled into something stronger). The
// canonical projection never emits unknown badges; this is the render
// path's second line of defense (Art. IV — no weaker fallback masquerading
// as the strong path: an unknown badge can only degrade, never upgrade).
export function safeBadge(badge: unknown): EpistemicBadge {
  return typeof badge === "string" &&
    (EPISTEMIC_BADGES as string[]).includes(badge)
    ? (badge as EpistemicBadge)
    : "UNVERIFIED";
}

export function safePredictionOutcome(outcome: unknown): PredictionOutcome {
  return typeof outcome === "string" &&
    (PREDICTION_OUTCOMES as string[]).includes(outcome)
    ? (outcome as PredictionOutcome)
    : "NOT_EVALUATED";
}

export interface TrajectorySource {
  kind?: string;
  lineage_schema?: string | null;
  lineage_sha256?: string | null;
  run_id?: string | null;
  authority?: string | null;
}

export interface TrajectoryState {
  kind?: string;
  gen: number;
  invention_id?: string | null;
  status: string; // verbatim INVENTION_* vocabulary
  maturity?: string | null;
  origin?: string | null;
  current: boolean;
  // the state's own recorded challenge context — the CURRENT state has no
  // following transition, so its uncertainty rides here (Art. XXV)
  challenge?: FailureElement | null;
  epistemic_badge: EpistemicBadge;
}

export interface FailureElement {
  kind?: string;
  killed: boolean;
  kill_reason?: string | null;
  attack_overall?: string | null;
  final_status?: string | null;
  evidence_verified?: boolean | null;
  uncertainties?: string | null;
  survived_with_uncertainties?: boolean;
  epistemic_badge: EpistemicBadge;
}

export interface CauseElement {
  kind?: string;
  cause?: string | null;
  basis?: string[] | string | null;
  infrastructure_class?: boolean;
  diagnosed_by?: string | null;
  epistemic_badge: EpistemicBadge;
}

export interface DirectionElement {
  kind?: string;
  failure_or_challenge?: string | null;
  diagnosed_cause?: string | null;
  causal_change?: string | null;
  transferred_capability?: string | null;
  epistemic_badge: EpistemicBadge;
}

export interface MutationField {
  field: string;
  before: string;
  after: string;
  changed: boolean;
}

export interface MutationElement {
  kind?: string;
  shape: "STRUCTURED" | "NARRATIVE";
  mutation_type?: string | null;
  mutation_id?: string | null;
  change_delta?: string | null;
  fields?: MutationField[];
  diagnostic_trigger?: Record<string, unknown> | null;
  epistemic_badge: EpistemicBadge;
}

export interface PredictionElement {
  kind?: string;
  expected_effect?: string | null;
  falsification_test?: string | null;
  prediction_outcome: PredictionOutcome;
  epistemic_badge: EpistemicBadge;
}

export interface ResultElement {
  gen: number;
  status: string;
  maturity?: string | null;
  epistemic_badge: EpistemicBadge;
}

export interface TrajectoryTransition {
  kind?: string;
  from_gen: number;
  to_gen: number;
  failure?: FailureElement | null;
  cause?: CauseElement | null;
  direction?: DirectionElement | null;
  mutation?: MutationElement | null;
  prediction?: PredictionElement | null;
  result: ResultElement;
  update?: {
    stop_reason?: string | null;
    survivor_reached?: boolean;
    superseded?: boolean;
  } | null;
}

export interface TrajectoryRecord {
  schema: string;
  trajectory_id: string;
  source: TrajectorySource;
  epistemic_boundary: string;
  badge_vocabulary: EpistemicBadge[];
  stop_reason?: string | null;
  n_generations: number;
  current_invention?: {
    gen?: number | null;
    invention_id?: string | null;
    status?: string | null;
    maturity?: string | null;
  } | null;
  states: TrajectoryState[];
  transitions: TrajectoryTransition[];
}

export interface SensitivityPoint {
  value: number | string;
  objective: number | string;
}

export interface SensitivityRecord {
  schema: string;
  parameter: string;
  objective?: string | null;
  basis: "MEASURED" | "SIMULATED" | "MODELLED";
  epistemic_badge: EpistemicBadge;
  points: SensitivityPoint[];
  note?: string | null;
}

export function isTrajectoryRecord(value: unknown): value is TrajectoryRecord {
  if (!value || typeof value !== "object") return false;
  const rec = value as TrajectoryRecord;
  return typeof rec.schema === "string" &&
    rec.schema.startsWith("TOSCANINI_TRAJECTORY/") &&
    Array.isArray(rec.states) &&
    Array.isArray(rec.transitions);
}

export function isSensitivityRecord(value: unknown): value is SensitivityRecord {
  if (!value || typeof value !== "object") return false;
  const rec = value as SensitivityRecord;
  return typeof rec.schema === "string" &&
    rec.schema.startsWith("TOSCANINI_SENSITIVITY/") &&
    Array.isArray(rec.points) &&
    rec.points.length >= 2;
}
