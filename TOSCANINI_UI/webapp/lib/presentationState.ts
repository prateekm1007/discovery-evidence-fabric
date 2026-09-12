// R451-C2 — THE ONE PRESENTATION-STATE MAPPING (directive C2.2).
//
// The visual layer consumes the canonical user-state projection
// (`user_state_view`, the dossier tabs) and maps it onto exactly one
// of seven presentation states. It NEVER invents its own scientific
// truth, NEVER re-derives state from raw machine combinations, and
// NEVER interprets "why" — it renders what the backend recorded
// (Art. X: one canonical authority; auditor governance 7: frontend
// claims trace to backend truth).
//
// The constitutional core of this mapping (Art. LXI):
//
//   INFRASTRUCTURE_PAUSED  !=  SCIENTIFIC_REJECTION
//   TECHNOLOGY_NOT_ESTABLISHED != GEOMETRY_READY_RENDER_BLOCKED
//
// An infrastructure stop is never rendered as scientific absence
// ("Not established"), and geometry-present-but-render-blocked is
// never rendered as technology-absent.

// ---- structural views of the backend projections (no inference) ----

export interface UserStateProjection {
  user_state?: string;
  label?: string;
  meaning?: string;
  decision?: string;
  finished?: boolean;
  found_something?: boolean;
  rejected?: boolean;
  package_available?: boolean;
  outcome?: string;
  outcome_label?: string;
}

export interface DesignTabProjection {
  availability?: string;
  glb?: string | null;
  geometry_class?: string | null;
  hero_eligibility?: { eligible?: boolean; reason?: string | null };
  renders?: {
    status?: string;
    visual_gate?: { verdict?: string; hero_suppressed?: boolean };
    note?: string;
  } | null;
}

export interface EvidenceTabProjection {
  availability?: string;
  retrieval_state?: string; // NOT_REACHED | PENDING | FAILED | RETRIEVED
  retrieval_note?: string | null;
  retrieved_count?: number;
  used_count?: number;
}

// The terminal-status classification of the backend machine taxonomy —
// canonical HERE (the lib layer, dependency-free so the state mapping
// is deterministically testable outside the browser); RunNarrative
// re-exports it for the component callers (one definition, Art. X).
export function isTerminal(status: string): boolean {
  return (
    status === "COMPLETE" ||
    status === "INTERRUPTED" ||
    status.startsWith("ERROR") ||
    status.startsWith("RUN_BLOCKED") // R415: RUN_BLOCKED_TRANSPORT —
    // infrastructure-blocked terminal, distinct from every verdict
  );
}

export interface PresentationDetail {
  status: string;
  final_status?: string | null;
  user_state_view?: UserStateProjection;
  run_state?: {
    invention_state?: { state?: string } | null;
  } | null;
}

export interface PresentationDossier {
  tabs?: {
    design?: DesignTabProjection;
    evidence?: EvidenceTabProjection;
  } | null;
}

// ---- the seven presentation states (directive C2.2) ----

export type PresentationState =
  | "INVESTIGATING"
  | "INFRASTRUCTURE_PAUSED"
  | "TECHNOLOGY_NOT_ESTABLISHED"
  | "GEOMETRY_UNAVAILABLE"
  | "GEOMETRY_READY_RENDER_BLOCKED"
  | "VISUAL_READY"
  | "SCIENTIFIC_REJECTION";

// the backend user-state keys that are INFRASTRUCTURE states (Art. LXI)
// — the user-state projection is authoritative; a stale scientific-
// looking field never overrides it (adversarial attack C)
export const INFRASTRUCTURE_USER_STATES = new Set([
  "BLOCKED_TRANSPORT",
  "INTERRUPTED",
  "FAILED_TRANSPORT",
  "FAILED_ENGINE",
]);

// the visual-gate verdicts that mean the presentation render is approved
export const GATE_PASS_VERDICTS = new Set(["PASS", "COMPLETE_PASS"]);

export interface BlockedCopy {
  headline: "DISCOVERY PAUSED";
  subline: string;
  verdictLine: string;
  savedLine: string;
  whatHappened: string;
  whatWasEstablished: string;
  whatRemainsUnknown: string;
  journalBanner: string[];
}

export interface PresentationView {
  state: PresentationState;
  /** true for every state the blocked/infrastructure treatment covers */
  infrastructurePaused: boolean;
  /** the blocked-state copy (present only when infrastructurePaused) */
  blocked?: BlockedCopy;
  /** case D: the canonical GLB exists and stays interactive */
  glbReadyButRenderBlocked?: boolean;
}

const BLOCKED_COPY: BlockedCopy = {
  headline: "DISCOVERY PAUSED",
  subline: "Infrastructure temporarily unavailable.",
  verdictLine: "No scientific conclusion was reached.",
  savedLine: "Your problem is saved and ready to resume.",
  whatHappened:
    "Infrastructure stopped the investigation before the next stage " +
    "could execute.",
  whatWasEstablished: "Nothing beyond the recorded infrastructure state.",
  whatRemainsUnknown: "Everything downstream of the interruption.",
  journalBanner: [
    "PAUSED AT INFRASTRUCTURE",
    "The investigation has not produced a scientific verdict.",
    "Earlier recorded events remain valid.",
    "Downstream stages were not evaluated.",
  ],
};

export function resolvePresentationState(
  detail: PresentationDetail,
  dossier?: PresentationDossier | null,
): PresentationView {
  const usv = detail.user_state_view ?? {};
  const design = dossier?.tabs?.design;
  const evidence = dossier?.tabs?.evidence;
  void evidence; // the evidence card reads the tab directly in place

  // ---- 1. still running -> INVESTIGATING ------------------------------
  if (!isTerminal(detail.status)) {
    return { state: "INVESTIGATING", infrastructurePaused: false };
  }

  // ---- 2. infrastructure stops -> INFRASTRUCTURE_PAUSED ----------------
  // The backend user-state projection decides (Attack C: an unrelated
  // stale `rejected`/scientific field NEVER reconciles this away —
  // the canonical user-state authority wins, no silent frontend
  // reconciliation).
  if (INFRASTRUCTURE_USER_STATES.has(usv.user_state ?? "")) {
    return {
      state: "INFRASTRUCTURE_PAUSED",
      infrastructurePaused: true,
      blocked: BLOCKED_COPY,
    };
  }

  // ---- 3. terminal scientific rejection (a REAL scientific verdict) ----
  // false premise is the honest scientific terminal; challenge-killed
  // architectures are presented as under-development generations, never
  // as this state (R416 discipline, unchanged)
  if (usv.user_state === "COMPLETED_FALSE_PREMISE") {
    return { state: "SCIENTIFIC_REJECTION", infrastructurePaused: false };
  }

  // ---- 4. geometry present --------------------------------------------
  if (design?.availability === "AVAILABLE" && design.glb) {
    const verdict = design.renders?.visual_gate?.verdict;
    const renderStatus = design.renders?.status ?? "";
    const renderRan = !(
      renderStatus.startsWith("RENDER_SKIPPED") ||
      renderStatus === "RENDER_FAILED" ||
      renderStatus === "RENDER_TIMEOUT" ||
      renderStatus === ""
    );
    if (renderRan && verdict != null && GATE_PASS_VERDICTS.has(verdict)) {
      return { state: "VISUAL_READY", infrastructurePaused: false };
    }
    // case D: the engineering geometry EXISTS; the presentation render
    // did not run or did not pass — the canonical GLB stays available
    // through the interactive viewer, and the UI says exactly that
    // (C2.6: geometry absent != renderer unavailable)
    return {
      state: "GEOMETRY_READY_RENDER_BLOCKED",
      infrastructurePaused: false,
      glbReadyButRenderBlocked: true,
    };
  }

  // ---- 5. no geometry: honest absence, two distinct meanings ----------
  // a technology/invention exists but has no physical geometry to show
  // (e.g. a software or process invention) -> GEOMETRY_UNAVAILABLE
  const inventionExists =
    usv.found_something === true ||
    usv.package_available === true ||
    (detail.run_state?.invention_state?.state ?? "") === "EXISTS";
  if (inventionExists) {
    return { state: "GEOMETRY_UNAVAILABLE", infrastructurePaused: false };
  }
  // the run completed without establishing a technology — honest
  // scientific absence (NEVER shown for an infrastructure stop: rule 2
  // already returned above, which is the exact contradiction this
  // round removes)
  return { state: "TECHNOLOGY_NOT_ESTABLISHED", infrastructurePaused: false };
}

// ---- the blocked-state insight cards (directive section 3) ------------
// Dedicated treatment: "not evaluated because execution stopped", never
// ordinary incompleteness ("still being investigated"), never scientific
// absence ("none" / "nothing found").

export interface BlockedInsightCard {
  title: string;
  headline: string;
  body: string;
}

export function blockedInsightCards(
  evidence?: EvidenceTabProjection | null,
): BlockedInsightCard[] {
  // C2.5: distinguish "searched and measured zero" from "never reached
  // retrieval" — the numeric zero exists ONLY in the RETRIEVED state
  const retrieval = evidence?.retrieval_state;
  let supports: BlockedInsightCard;
  if (retrieval === "RETRIEVED" && evidence?.retrieved_count === 0) {
    supports = {
      title: "What supports it",
      headline: "0 sources retrieved",
      body: "Retrieval executed and measured zero records — the measured " +
        "zero, not an unavailable source.",
    };
  } else if (retrieval === "FAILED") {
    supports = {
      title: "What supports it",
      headline: "Evidence retrieval failed",
      body: "Retrieval ran into an infrastructure failure before " +
        "records could be acquired — not a measured zero.",
    };
  } else {
    supports = {
      title: "What supports it",
      headline: "Evidence retrieval not reached",
      body: "The run stopped at infrastructure before evidence could " +
        "be acquired.",
    };
  }
  return [
    {
      title: "What changed",
      headline: "Not evaluated",
      body: "Discovery paused before a technology state was established.",
    },
    {
      title: "Why it works",
      headline: "Not evaluated",
      body: "The investigation did not reach mechanism evaluation.",
    },
    supports,
    {
      title: "What could kill it",
      headline: "Not evaluated",
      body: "No candidate reached the attack stage.",
    },
  ];
}
