// R453-C2 — types for the canonical-state presentation layer.
// Canonical engine types are re-exported from ./types (the single mirror
// of the backend payloads); presentation-layer shapes are declared here.

import type {
  AskResponse,
  CompletionStates,
  DossierBody,
  DossierTab,
  EventsBody,
  GauntletCard,
  RankedPackage,
  RunStateObject,
  ScienceEvent,
  SessionDetail,
  UserStateView,
} from "./types";

export type {
  AskResponse,
  CompletionStates,
  DossierBody,
  DossierTab,
  EventsBody,
  GauntletCard,
  RankedPackage,
  RunStateObject,
  ScienceEvent,
  SessionDetail,
  UserStateView,
};

// the five canonical retrieval states (run_state.py::_evidence_state —
// GATHERED+count splits into RETRIEVED_POSITIVE / RETRIEVED_ZERO)
export type RetrievalState =
  | "NOT_REACHED"
  | "PENDING"
  | "RETRIEVED_ZERO"
  | "RETRIEVED_POSITIVE"
  | "FAILED";

// geometry/model presentation states. UNKNOWN (nothing established) is
// deliberately distinct from UNAVAILABLE (established; presentation path
// down) and UNEARNED (exists; did not earn the primary surface — R436).
export type GeometryState =
  | "ENGINEERING"
  | "CONCEPTUAL"
  | "UNEARNED"
  | "UNAVAILABLE"
  | "PENDING"
  | "UNKNOWN";

// adversarial-test states — NOT_RUN is its own state and never defaults
// to SURVIVED (Test F)
export type AttackState =
  | "NOT_RUN"
  | "IN_PROGRESS"
  | "SURVIVED"
  | "CONTESTED"
  | "FAILED"
  | "UNRESOLVED";

// brief §10 vocabulary — the meta label a message may carry, derived
// ONLY from the record's epistemic class, never upgraded client-side
export type EpistemicMeta =
  | "FOUND"
  | "INFERRED"
  | "HYPOTHESIS"
  | "TESTED"
  | "SURVIVED_ATTACK"
  | "UNKNOWN"
  | "BLOCKED"
  | "REJECTED";

export type SurfaceId =
  | "overview"
  | "model"
  | "evidence"
  | "engineering"
  | "experiment"
  | "package"
  | "journal";

// the design tab shape the presentation layer reads (structural subset
// of DossierSections' DesignTabData — keeps this module React-free)
export interface DesignTabShape {
  availability?: string;
  note?: string;
  conceptual?: boolean;
  fallback_basis?: string | null;
  hero_eligibility?: {
    eligible?: boolean;
    reason?: string | null;
    rule?: string | null;
    not_visualized?: string[];
  } | null;
  [k: string]: unknown;
}

export interface CandidateView {
  label: string;
  intervention: string | null;
  mechanism: string | null;
  why: string | null;
  whatChanged: string | null;
  risk: string | null;
  attack: AttackState;
  maturity: string | null;
  current: boolean;
  killed: boolean;
  // R510 dry-run cliff: canonical portfolio fields, passed through
  // VERBATIM from the backend's portfolio projection (never derived
  // in React — no client-side rank, distinctness, or ordering).
  // Null when the backend served no portfolio record.
  candidateId: string | null;
  rank: number | null;
  distinctness: string | null;
  rankingBasis: string | null;
}

// R540: one ranked survivor + its attached technology package (the
// contract's "ranked technology packages"). Rendered verbatim from the
// engine's ranked result record — no client-side re-sort, re-score, or
// rank inference. The package CTA is the move from a ranked result to
// its downloadable package.
// R543-2: one materially investigated competing candidate — its own
// candidate, mechanism, what would kill it, and the recorded
// disposition. Carried on the ranked projection so the conversation
// exposes the competing-mechanism answer shape literally, not just a
// list of competing candidate IDs the user has to reconstruct.
export interface CompetingCandidateView {
  candidateId: string | null;
  mechanism: string | null;
  intervention: string | null;
  whatWouldKillIt: string | null;
  disposition: string | null;
}

export interface RankedPackageView {
  rank: number | null;
  candidateId: string | null;
  admissible: boolean;
  selected: boolean;
  // the six components (each honest — a missing component says so, it
  // never fabricates a value).
  evidence: {
    count: number | null;
    span: string | null;
    status: string | null;
    // R543-2: the evidence answer shape is the actual source
    // provenance, not just a count — the supporting recorded span plus
    // the source identity / provenance the record carries.
    sources: string[];
    sourceIdentity: string | null;
  };
  mechanism: {
    mechanism: string | null;
    intervention: string | null;
    expectedEffect: string | null;
    falsificationTest: string | null;
    competing: string[];
    // R543-2: the complete competing-candidate summaries (candidate +
    // mechanism + kill condition + disposition), never only IDs.
    competingCandidates: CompetingCandidateView[];
  };
  adversarial: {
    overall: string | null;
    disposition: string;
    survived: boolean;
    killed: boolean;
    unresolved: boolean;
  };
  engineering: {
    geometryPresent: boolean;
    modelClass: string | null;
    limitations: string | null;
  };
  experiment: {
    experiment: string | null;
    discriminator: string | null;
    decisionRule: string | null;
    executionStatus: string | null;
  };
  package: {
    kind: string | null;
    complete: boolean;
    zipName: string | null;
    maturity: string | null;
    // R541: the candidate-bound package identity — each ranked survivor
    // carries ITS OWN package (candidate_id + rank + zip + hash +
    // manifest), never a reused #1 package.
    candidateId: string | null;
    rank: number | null;
    packageId: string | null;
    zipSha256: string | null;
    zipSha256Matches: boolean;
    // R541: the candidate-specific download route ("Download technology
    // package #N" resolves to THIS candidate's package, not a shared
    // /package surface for every ranked card).
    downloadUrl: string | null;
  };
  rankBasis: string | null;
}

export interface NextAction {
  label: string;
  kind:
    | "package"
    | "retry"
    | "new"
    | "surface"
    | "diagnostic"
    | "run_queued"
    // R477 (audit P0-4): the engine-recorded next action executed
    // through the ONE canonical action endpoint (the same path the
    // conversation's steering uses).
    | "act";
  surface?: SurfaceId;
  verb?: string;
  /** R477 (audit P0-4): ONE decision trace — "engine-record" means the
   * label came from the run contract's next_action (the NBA controller
   * record / the NEXT_BEST_ACTION stage output, read via
   * GET /api/run/{id}/contract); "presentation" means the UI derived it
   * from canonical state because no engine record existed. Never two
   * authorities displayed at once. */
  source?: "engine-record" | "presentation";
  /** the engine record's own reason, when the label is engine-derived. */
  basis?: string | null;
}

// R477 (audit P0-4): the shape of GET /api/run/{id}/contract's
// next_action — the runtime NBA controller's preferred_action or the
// persisted NEXT_BEST_ACTION stage record (run_contract._next_action).
// Deliberately loose: the UI maps the closed action vocabulary and
// invents nothing for an unknown action (it falls back honestly).
export interface EngineNextAction {
  action?: string;
  reason?: string | null;
  target_uncertainty?: string | null;
  authority?: string;
  [k: string]: unknown;
}

// one conversation message. `epi` carries the brief-§10 meta label.
export type Msg =
  | { kind: "user"; id: string; text: string }
  | { kind: "note"; id: string; text: string; epi?: EpistemicMeta | null }
  | { kind: "progress"; id: string; text: string; live: boolean }
  // R458-C2 (§4): the engine's one material question — the conversation
  // can change the discovery. The composer becomes the answer box while
  // this message is the newest thing on the record.
  | {
      kind: "clarification";
      id: string;
      question: string;
      decisionChanged: string | null;
    }
  | {
      kind: "evidence";
      id: string;
      state: RetrievalState;
      retrieved: number | null;
      used: number | null;
      domains: string[];
      body: string;
      openSurface: SurfaceId;
    }
  | { kind: "candidates"; id: string; items: CandidateView[] }
  // R540: the ranked result set — one card per admissible ranked
  // survivor, each with its six components + rank basis + attached
  // technology package (the contract's "ranked technology packages").
  // Rendered verbatim from the engine record; the UI moves from a ranked
  // result directly to its package.
  | {
      kind: "ranked";
      id: string;
      items: RankedPackageView[];
      completion: CompletionStates | null;
      finished: boolean;
    }
  | {
      kind: "attack";
      id: string;
      state: AttackState;
      challenge: string | null;
      body: string;
    }
  | {
      kind: "artifact";
      id: string;
      surface: SurfaceId;
      title: string;
      body: string | null;
      cta: string;
    }
  // R477 (audit P0-1): the directive-outcome card — a direction the
  // user asked for while the run was live, saved by the engine and
  // never applied mid-flight. The conversation carries the receipt
  // verbatim; the one-click execution rides the run_queued next action.
  | { kind: "queued"; id: string; text: string }
  | {
      kind: "outcome";
      id: string;
      tone: "positive" | "development" | "rejected" | "unknown" | "blocked";
      label: string;
      body: string;
      next: NextAction | null;
    }
  | { kind: "ask"; id: string; question: string; response: AskResponse };
