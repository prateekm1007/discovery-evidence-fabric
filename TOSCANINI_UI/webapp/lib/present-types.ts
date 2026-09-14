// R453-C2 — types for the canonical-state presentation layer.
// Canonical engine types are re-exported from ./types (the single mirror
// of the backend payloads); presentation-layer shapes are declared here.

import type {
  AskResponse,
  DossierBody,
  DossierTab,
  EventsBody,
  GauntletCard,
  RunStateObject,
  ScienceEvent,
  SessionDetail,
  UserStateView,
} from "./types";

export type {
  AskResponse,
  DossierBody,
  DossierTab,
  EventsBody,
  GauntletCard,
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
}

export interface NextAction {
  label: string;
  kind: "package" | "retry" | "new" | "surface";
  surface?: SurfaceId;
}

// one conversation message. `epi` carries the brief-§10 meta label.
export type Msg =
  | { kind: "user"; id: string; text: string }
  | { kind: "note"; id: string; text: string; epi?: EpistemicMeta | null }
  | { kind: "progress"; id: string; text: string; live: boolean }
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
  | {
      kind: "outcome";
      id: string;
      tone: "positive" | "development" | "rejected" | "unknown" | "blocked";
      label: string;
      body: string;
      next: NextAction | null;
    }
  | { kind: "ask"; id: string; question: string; response: AskResponse };
