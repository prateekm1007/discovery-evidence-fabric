// R454-C2 — THE PRODUCT EVENT MAP (brief §22 "conversation event
// rendering" + §25 "loading states").
//
// Backend science events (toscanini/event_journal.py vocabulary: kind,
// stage, status, epistemic_class) become first-person human sentences in
// the conversation. This is the ONE mapping — the conversation never
// shows raw machine vocabulary (BS-009: "engine stage SYNTHESIZE
// recorded at …" is a journal line, not conversation), never animates
// fake reasoning (§23: sentences describe recorded work, never hidden
// chain-of-thought), and never converts an infrastructure failure into
// a scientific verdict (Art. LXI: "the technical test could not be
// completed" — never "the candidate failed").
//
// The backend's own event summary is PRESERVED (§15): it stays in the
// technical record (journal surface, per-event provenance) and as the
// title attribute on conversation lines. This module only decides what
// the CONVERSATION says.
//
// Ground truth for every kind/status: toscanini/event_journal.py
// (kinds: problem.extract, evidence.retrieval_started, evidence.retrieved,
// evidence.retrieval_failed, evidence.bound, stage.{STAGE},
// geometry.created, package.completed, investigation.terminal;
// statuses: QUEUED | ACTIVE | COMPLETED | BLOCKED |
// FAILED_INFRASTRUCTURE | FAILED_SCIENTIFIC | UNKNOWN).
//
// Zero dependencies, React-free — the adversarial Node suite runs this
// module directly, so the honesty contracts are executable evidence
// (Art. XVI).

// ---------------------------------------------------------------------------
// types (structural subset of lib/types ScienceEvent — keeps this module
// dependency-free while matching the wire payload)
// ---------------------------------------------------------------------------

export interface ProductEventInput {
  kind?: string | null;
  stage?: string | null;
  status?: string | null;
  summary?: string | null;
  [k: string]: unknown;
}

export interface ProductEventSentence {
  /** The sentence the conversation renders. Empty string = render nothing. */
  text: string;
  /** True when this is a meaningful in-progress action line (brief §25). */
  loading: boolean;
  /** True when the state behind this event is infrastructure, not science. */
  infrastructure: boolean;
}

// ---------------------------------------------------------------------------
// the map
// ---------------------------------------------------------------------------

const INFRA_STATUSES = new Set([
  "FAILED_INFRASTRUCTURE",
  "BLOCKED",
  "TRANSPORT_ERROR",
]);

function isInfra(status: string): boolean {
  return INFRA_STATUSES.has(status);
}

// stage.{STAGE} → human phase sentences. ACTIVE = the meaningful action
// (§25's exact register); COMPLETED = a neutral record-completed sentence
// that NEVER announces a verdict (an ATTACK stage completing is not a
// candidate surviving — Test F; a SYNTHESIZE stage completing is not "the
// answer" — Art. XXVIII: hypotheses stay hypotheses until attacked).
const STAGE_SENTENCES: Record<string, { active: string; completed: string }> = {
  RETRIEVE: {
    active: "Investigating evidence — I'm searching the indexed sources now.",
    completed: "The evidence search for this problem is in.",
  },
  FREEZE: {
    active: "Freezing the evidence base so every claim traces to a hashed record.",
    completed: "The evidence base is frozen — every record carries its content hash.",
  },
  PREMISE_GATE: {
    active: "Checking that the problem itself holds up before building on it.",
    completed: "The problem's premise has been checked.",
  },
  SYNTHESIZE: {
    active: "Comparing mechanisms — I'm working out what could actually cause this effect.",
    completed: "Candidate mechanisms are formed. They are hypotheses to be tested, not conclusions.",
  },
  VERIFY: {
    active: "Verifying that the evidence actually says what it is claimed to say.",
    completed: "The evidence verification pass is recorded.",
  },
  MULTI_SOURCE_DISCOVERY: {
    active: "Searching beyond the obvious sources for supporting and contradicting work.",
    completed: "The wider source sweep is recorded.",
  },
  COLLISION: {
    active: "Checking the emerging ideas against prior art.",
    completed: "The prior-art collision check is recorded.",
  },
  PHYSICS: {
    active: "Checking the physics of the emerging candidates.",
    completed: "The physics check is recorded.",
  },
  ATTACK: {
    active: "Challenging the leading candidate — I'm trying to disprove it.",
    completed: "The adversarial challenge has run. Its outcome is in the record, stated exactly as recorded.",
  },
  CONTRADICTION: {
    active: "Cross-checking the evidence for contradictions.",
    completed: "The contradiction check is recorded.",
  },
  KILLER_EXPERIMENT: {
    active: "Designing the decisive experiment — the one that could kill the candidate.",
    completed: "The decisive experiment is specified, with its falsification condition.",
  },
  ADJUDICATION: {
    active: "Weighing what survived the challenges.",
    completed: "The adjudication is recorded.",
  },
  CLASSIFY: {
    active: "Classifying what the investigation actually established.",
    completed: "The investigation's classification is recorded.",
  },
  NEXT_BEST_ACTION: {
    active: "Deciding what comes next.",
    completed: "The next step has been chosen.",
  },
  RANK: {
    active: "Ranking the remaining candidates by evidence and risk.",
    completed: "The candidate ranking is recorded.",
  },
  GEOMETRY: {
    active: "Working on the technology model.",
    completed: "The technology model step is recorded.",
  },
  TRANSFER: {
    active: "Assembling the technology package.",
    completed: "The technology package step is recorded.",
  },
};

// the stage-agnostic evidence/geometry/terminal kinds the journal emits
// outside stage.{STAGE}
function kindSentence(kind: string, status: string, evt: ProductEventInput): ProductEventSentence | null {
  const infra = isInfra(status);
  switch (kind) {
    case "problem.extract":
      if (status === "ACTIVE")
        return { text: "I'm reading your problem — extracting what it claims, what it assumes, and what would count as success.", loading: true, infrastructure: false };
      if (status === "COMPLETED")
        return { text: "The problem is framed — the investigation works from your own words.", loading: false, infrastructure: false };
      return null;
    case "evidence.retrieval_started":
      return { text: "Investigating evidence — I'm searching the indexed sources now.", loading: true, infrastructure: false };
    case "evidence.retrieved": {
      const src = typeof evt.source === "string" ? evt.source : null;
      const count = typeof evt.count === "number" ? evt.count : null;
      let text = "Evidence came in";
      if (src) text += ` from ${src}`;
      if (count != null) text += ` — ${count} record${count === 1 ? "" : "s"}`;
      text += ".";
      return { text, loading: false, infrastructure: false };
    }
    case "evidence.retrieval_failed":
      return {
        text: "One of the evidence sources could not be reached. That is an infrastructure state — absence is never concluded from a failed source, and the investigation continues.",
        loading: false,
        infrastructure: true,
      };
    case "evidence.bound":
      return { text: "The evidence base is bound to the problem — every record is custody-tracked.", loading: false, infrastructure: false };
    case "geometry.created":
      return { text: "The technology model is ready to inspect.", loading: false, infrastructure: false };
    case "package.completed":
      return { text: "The technology package is assembled and ready.", loading: false, infrastructure: false };
    case "investigation.terminal":
      if (status === "COMPLETED")
        return { text: "The investigation reached its outcome — stated below exactly as recorded.", loading: false, infrastructure: false };
      if (infra)
        return {
          text: "The technical work hit an infrastructure wall. The test could not be completed — nothing has been rejected because of it, and the run can resume where it stopped.",
          loading: false,
          infrastructure: true,
        };
      return {
        text: "The investigation ended without a supported candidate. That is a recorded scientific outcome, not an infrastructure failure.",
        loading: false,
        infrastructure: false,
      };
    default:
      return null;
  }
}

// ---------------------------------------------------------------------------
// THE entry point
// ---------------------------------------------------------------------------

export function productEventSentence(evt: ProductEventInput | null | undefined): ProductEventSentence {
  if (!evt) return { text: "", loading: false, infrastructure: false };
  const kind = String(evt.kind ?? "");
  const status = String(evt.status ?? "UNKNOWN").toUpperCase();
  const infra = isInfra(status);

  // 1 — the named non-stage kinds
  const byKind = kindSentence(kind, status, evt);
  if (byKind) return byKind;

  // 2 — stage.{STAGE} events
  if (kind.startsWith("stage.")) {
    const stage = kind.slice("stage.".length).toUpperCase();
    const s = STAGE_SENTENCES[stage];
    if (s) {
      if (status === "ACTIVE") return { text: s.active, loading: true, infrastructure: false };
      if (status === "COMPLETED") return { text: s.completed, loading: false, infrastructure: false };
      if (infra)
        return {
          text: "A technical step could not complete — that is infrastructure, not a verdict about the idea.",
          loading: false,
          infrastructure: true,
        };
      if (status === "FAILED_SCIENTIFIC")
        return {
          text: "A step of the investigation recorded a scientific failure — kept as a finding, stated in the record.",
          loading: false,
          infrastructure: false,
        };
      if (status === "QUEUED") return { text: "", loading: false, infrastructure: false };
      return { text: "", loading: false, infrastructure: false };
    }
    // an unknown stage: honest, calm, never machinery
    if (status === "ACTIVE") return { text: "Still working — the investigation is progressing.", loading: true, infrastructure: false };
    if (status === "COMPLETED") return { text: "A step of the investigation is recorded.", loading: false, infrastructure: false };
    if (infra) return { text: "A technical step paused — infrastructure, not a verdict.", loading: false, infrastructure: true };
    return { text: "", loading: false, infrastructure: false };
  }

  // 3 — unknown kind entirely: status-based fallback only
  if (status === "ACTIVE") return { text: "Still working — the investigation is progressing.", loading: true, infrastructure: false };
  if (status === "COMPLETED") return { text: "A step of the investigation is recorded.", loading: false, infrastructure: false };
  if (infra) return { text: "A technical step paused — infrastructure, not a verdict.", loading: false, infrastructure: true };
  return { text: "", loading: false, infrastructure: false };
}

// ---------------------------------------------------------------------------
// helpers for the conversation live line
// ---------------------------------------------------------------------------

/** The most informative live line: the newest ACTIVE event, else the
 * newest infrastructure event (a pause is its own honest state — never
 * rendered as active work, R436 §5B). */
export function pickLiveEvent(events: ProductEventInput[]): ProductEventInput | null {
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i];
    if (String(e?.status ?? "") === "ACTIVE") return e;
  }
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i];
    if (isInfra(String(e?.status ?? "").toUpperCase())) return e;
  }
  return null;
}
