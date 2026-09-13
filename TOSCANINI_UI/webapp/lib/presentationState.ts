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
  // R451-C2.1: the typed geometry/visual state — DERIVED BY THE BACKEND
  // (toscanini/dossier.py::_geometry_state) from canonical records; the
  // frontend consumes it verbatim and NEVER infers these states from a
  // missing file (the operator directive's central rule)
  geometry_state?: string;
  presentation_cause?: string | null;
  geometry_state_detail?: string | null;
  // R451-C2.2: the typed visual-join state (toscanini/visual_join.py —
  // the invocation→render→gate→hero chain) + the artifact contract's
  // recorded verdict; consumed verbatim, never re-derived
  visual_join_state?: string | null;
  visual_join_detail?: string | null;
  visual_join_cause?: string | null;
  pending_render_job?: string | null;
  // R451-C2.3 §1/§2: the contract's ENGINEERING authority verdict and
  // the two separated boundary states (consumed verbatim from the
  // backend's design tab — never re-derived here)
  engineering_authority?: "ENGINEERING" | "CONCEPTUAL" | "UNKNOWN" | null;
  engineering_geometry_ready?: boolean;
  visual_input_ready?: boolean;
  visual_input_basis?: string | null;
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

// R451-C2.1 — the six-value geometry/visual vocabulary (backend-owned;
// toscanini/dossier.py::GEOMETRY_STATES is the authority)
export const GEOMETRY_STATES = new Set([
  "upstream_not_reached",
  "geometry_not_applicable",
  "geometry_generation_failed",
  "geometry_available",
  "visual_render_failed",
  "visual_complete",
]);

// why the presentation is not approved (State C vs State D, R451-C2.2
// §1: every cause has its OWN sentence — a render that was never
// started is never worded as "renderer unavailable", and vice versa).
// R451-C2.3 §2/§5: the visual-input boundary and the fail-closed
// release chain get their OWN causes too — a missing canonical GLB is
// never worded as renderer absence, and an unverifiable release chain
// is never worded as a gate rejection or as visual readiness.
export type RenderBlockCause =
  | "renderer_unavailable"
  | "gate_not_passed"
  | "not_attempted"
  | "infrastructure"
  | "rendering_in_progress"
  | "visual_input_missing"
  | "release_unverified";

// the closed cause vocabulary — the source pin the test battery walks
export const RENDER_BLOCK_CAUSES: RenderBlockCause[] = [
  "renderer_unavailable",
  "gate_not_passed",
  "not_attempted",
  "infrastructure",
  "rendering_in_progress",
  "visual_input_missing",
  "release_unverified",
];

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
  /** case C/D: the canonical GLB exists and stays interactive */
  glbReadyButRenderBlocked?: boolean;
  /** case C vs D: WHY the presentation is not approved (backend-typed) */
  renderBlockCause?: RenderBlockCause;
  /** the recorded detail line for the render-blocked state, verbatim */
  renderBlockDetail?: string | null;
  /** R451-C2.3 §1: the contract's recorded ENGINEERING authority —
   * the ribbon title never claims engineering without it */
  engineeringAuthority?: "ENGINEERING" | "CONCEPTUAL" | "UNKNOWN" | null;
  /** case B: the invention exists but has no physical geometry */
  geometryAbsent?: {
    reason: "not_applicable" | "generation_failed";
    detail: string | null;
  };
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

// ---- the five hero states' exact copy (operator directive R451-C2.1) ----
// State B — invention exists, geometry absent:
export const GEOMETRY_ABSENT_COPY = {
  heading: "Technology visualization",
  line: "Engineering visualization not available on this invention.",
};

// States C/D — geometry exists, presentation not approved. R451-C2.2
// §1: the EXACT sentence per cause — five causes, five distinct
// sentences; the not_attempted join never reads as renderer absence.
// The canonical GLB stays interactive regardless.
export function renderBlockedCopy(cause?: RenderBlockCause): {
  title: string;
  line: string;
} {
  if (cause === "gate_not_passed") {
    // State D — the renderer produced pixels and the gate said no
    return {
      title: "PRESENTATION INTEGRITY GATE",
      line: "Model rendered but did not pass the presentation " +
        "integrity gate.",
    };
  }
  if (cause === "not_attempted") {
    // R451-C2.2 §1 — the explicit not_attempted sentence: the render
    // was never started. It is NOT "renderer unavailable".
    return {
      title: "ENGINEERING MODEL READY",
      line: "Engineering model ready. Presentation render not yet " +
        "started.",
    };
  }
  if (cause === "infrastructure") {
    // R451-C2.2 §1 — infrastructure caused the skip (capacity,
    // transport): distinct from renderer absence, Art. LXI vocabulary
    return {
      title: "ENGINEERING MODEL READY",
      line: "Engineering model ready. Presentation rendering paused " +
        "by infrastructure.",
    };
  }
  if (cause === "rendering_in_progress") {
    // R451-C2.2 §1 — the async render job is running right now
    return {
      title: "ENGINEERING MODEL READY",
      line: "Engineering model ready. Presentation render in progress.",
    };
  }
  if (cause === "visual_input_missing") {
    // R451-C2.3 §2 — the engineering geometry is ready but the
    // canonical GLB the Visual Compiler consumes was not produced:
    // a valid STEP alone never satisfies the visual boundary
    return {
      title: "ENGINEERING MODEL READY",
      line: "Engineering model ready. The canonical 3D model file " +
        "required for presentation rendering was not produced on " +
        "this run.",
    };
  }
  if (cause === "release_unverified") {
    // R451-C2.3 §5 — the gate passed but the release chain failed
    // closed (identity mismatch / missing release artifacts / hero
    // not the canonical GLB): never worded as visual readiness
    return {
      title: "ENGINEERING MODEL READY",
      line: "Engineering model ready. The presentation could not be " +
        "verified against the canonical geometry.",
    };
  }
  // State C — the renderer itself is unavailable in this environment
  return {
    title: "ENGINEERING MODEL READY",
    line: "Engineering model ready. Presentation renderer unavailable.",
  };
}

// R451-C2.3 §1 — the ribbon's title is authority-aware: the
// ENGINEERING MODEL READY claim exists ONLY when the artifact
// contract's recorded authority says ENGINEERING. A CONCEPTUAL
// artifact and an UNKNOWN-authority (legacy boolean-only) artifact
// stay readable but NEVER inherit the engineering claim.
export function renderBlockedTitle(
  authority?: "ENGINEERING" | "CONCEPTUAL" | "UNKNOWN" | null,
): string {
  if (authority === "ENGINEERING") return "ENGINEERING MODEL READY";
  if (authority === "CONCEPTUAL") return "CONCEPTUAL MODEL";
  return "GEOMETRY AUTHORITY UNVERIFIED";
}

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

  // ---- 4. the typed geometry/visual state (R451-C2.1) -----------------
  // THE ONE mapping consumes the backend-derived `geometry_state`
  // (toscanini/dossier.py::_geometry_state). The frontend NEVER infers
  // these states from a missing file — the operator directive's
  // central rule (geom.present == false collapses too much meaning;
  // upstream_not_reached / geometry_not_applicable /
  // geometry_generation_failed are DIFFERENT facts and the backend
  // records which one holds).
  const gstate = design?.geometry_state;
  const typedGeometry = gstate != null && GEOMETRY_STATES.has(gstate);

  if (typedGeometry) {
    if (gstate === "visual_complete") {
      // State E — render succeeded AND the gate passed: show the model
      return { state: "VISUAL_READY", infrastructurePaused: false };
    }
    if (gstate === "geometry_available" ||
        gstate === "visual_render_failed") {
      // States C/D — the canonical GLB exists and stays interactive;
      // `presentation_cause` (backend-typed) picks the exact copy;
      // R451-C2.3 §1: the ribbon title follows the contract's
      // recorded ENGINEERING authority (legacy/UNKNOWN authority
      // never claims ENGINEERING MODEL READY)
      return {
        state: "GEOMETRY_READY_RENDER_BLOCKED",
        infrastructurePaused: false,
        glbReadyButRenderBlocked: true,
        renderBlockCause: (design?.presentation_cause ??
          undefined) as RenderBlockCause | undefined,
        renderBlockDetail: design?.geometry_state_detail ?? null,
        engineeringAuthority: design?.engineering_authority ?? null,
      };
    }
    if (gstate === "geometry_not_applicable" ||
        gstate === "geometry_generation_failed") {
      // State B — the invention exists; the recorded outcome says why
      // there is no visualization (not applicable, or the build failed)
      return {
        state: "GEOMETRY_UNAVAILABLE",
        infrastructurePaused: false,
        geometryAbsent: {
          reason: gstate === "geometry_not_applicable"
            ? "not_applicable"
            : "generation_failed",
          detail: design?.geometry_state_detail ?? null,
        },
      };
    }
    // upstream_not_reached: falls through — the invention-existence
    // logic below resolves the honest absence state
  } else if (design?.availability === "AVAILABLE" && design.glb) {
    // pre-C2.1 projection fallback (documented): older dossier payloads
    // without the typed field — derive from the projection's OWN
    // renders fields (never from raw file existence)
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
    // case C/D: the engineering geometry EXISTS; the presentation render
    // did not run or did not pass — the canonical GLB stays available
    // through the interactive viewer (C2.6: geometry absent != renderer
    // unavailable). R451-C2.2 §1: an empty render status (no record at
    // all) is the not_attempted fact — never renderer absence.
    const cause: RenderBlockCause =
      renderRan && verdict != null ? "gate_not_passed"
      : renderStatus.includes("SKIPPED") || renderStatus === "INTERRUPTED"
        ? "infrastructure"
      : renderStatus === ""
        ? "not_attempted"
        : "renderer_unavailable";
    return {
      state: "GEOMETRY_READY_RENDER_BLOCKED",
      infrastructurePaused: false,
      glbReadyButRenderBlocked: true,
      renderBlockCause: cause,
      renderBlockDetail: design.renders?.note ?? null,
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
