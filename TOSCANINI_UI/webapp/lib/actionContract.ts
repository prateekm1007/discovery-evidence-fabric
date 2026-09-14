// R458-C2 — THE CONVERSATIONAL ACTION CONTRACT (client side).
//
// Directive §4/§5/§18: the conversation must be able to CHANGE the
// discovery, and "Ask" must be distinct from "Act".
//
//   ASK  — a read-only question over the run's own canonical record.
//          Executed today by POST /api/run/{id}/ask (R395). The answer
//          never changes the investigation.
//   ACT  — a canonical action request that asks the engine to produce
//          a NEW canonical state (POST /api/run/{id}/actions).
//
// OWNERSHIP (§18): Coder 1 owns execution semantics — what the engine
// does with an accepted action. Coder 2 owns presentation and
// invocation — this module is the invocation path, nothing more.
// The frontend NEVER implements scientific logic, NEVER creates a new
// canonical state client-side, and NEVER claims an action happened
// because the user typed it (Art. X: the UI is a projection; §27: no
// frontend-side epistemology, no duplicate backend authority).
//
// The phrase table below is a DETERMINISTIC presentation-level router:
// fixed patterns → canonical action names. It is not an interpreter,
// it holds no model, and it can only ever do two things: route a
// message to the engine's action endpoint, or leave it as a question.
// The full contract (wire shapes, verbs, error semantics, Coder-1
// obligations) is R458/CODER2_CONVERSATIONAL_ACTION_CONTRACT.json.
//
// Zero dependencies, React-free — the adversarial Node suite runs this
// module directly (Art. XVI: executable evidence, not prose).

// ---------------------------------------------------------------------------
// the canonical action vocabulary (§18 — exact 11)
// ---------------------------------------------------------------------------

export type ActionVerb =
  | "ASK"
  | "CLARIFY"
  | "RESEARCH"
  | "FIND_EVIDENCE"
  | "COMPARE_MECHANISMS"
  | "ATTACK"
  | "CHANGE_MECHANISM"
  | "REQUEST_ENGINEERING"
  | "REQUEST_EXPERIMENT"
  | "UPLOAD_EVIDENCE"
  | "REVIEW_PACKAGE";

/** The one-line user-facing phrasing per action — the composer's chip
 * label and the conversation's confirmation line. Human language only;
 * never a stage name, never an enum (BS-009). */
export const ACTION_LABEL: Record<Exclude<ActionVerb, "ASK">, string> = {
  CLARIFY: "Answer Toscanini's question",
  RESEARCH: "Research this further",
  FIND_EVIDENCE: "Look for evidence",
  COMPARE_MECHANISMS: "Compare the mechanisms",
  ATTACK: "Challenge this candidate",
  CHANGE_MECHANISM: "Try another mechanism",
  REQUEST_ENGINEERING: "Work out the engineering",
  REQUEST_EXPERIMENT: "Design the decisive experiment",
  UPLOAD_EVIDENCE: "Use this document in the investigation",
  REVIEW_PACKAGE: "Review the technology package",
};

/** What the conversation may HONESTLY say when the engine cannot
 * execute the action. Never a fake success; never a scientific claim
 * (Art. LXI vocabulary — an unavailable capability is an infrastructure
 * state, not a verdict). R459 (P1-1 complexity hiding): internal
 * protocol names and round numbers stay out of user-facing copy. */
export const ACTION_NOT_AVAILABLE_COPY =
  "I can't change the investigation from the conversation yet — that " +
  "capability isn't available right now. Nothing was changed by that " +
  "message, and the investigation's record is unaffected. Your message " +
  "is preserved here; asking about the record still works.";

// ---------------------------------------------------------------------------
// the deterministic phrase router (presentation-level, no semantics)
// ---------------------------------------------------------------------------

interface PhraseRule {
  verb: Exclude<ActionVerb, "ASK">;
  patterns: RegExp[];
}

/** Ordered — the FIRST match wins. Deliberately narrow: ambiguity
 * routes to ASK (a question is always safe; a wrong action is not). */
const PHRASE_RULES: PhraseRule[] = [
  {
    verb: "CHANGE_MECHANISM",
    patterns: [
      /\btry (another|a different|an alternative) (mechanism|approach|explanation|hypothesis)\b/i,
      /\bchange the mechanism\b/i,
      /\bkeep the .*(constraint|requirement).* (but|and) change\b/i,
      /\bwhat else could (cause|explain) (this|it)\b/i,
    ],
  },
  {
    verb: "ATTACK",
    patterns: [
      /\bchallenge (candidate|invention|architecture|this)\b/i,
      /\btry to disprove\b/i,
      /\battack (candidate|invention|architecture|this)\b/i,
      /\b(disprove|falsify) (candidate|invention|this|it)\b/i,
    ],
  },
  {
    verb: "FIND_EVIDENCE",
    patterns: [
      /\blook for (contradicting|contradictory|supporting|more) evidence\b/i,
      /\bfind (contradicting|contradictory|supporting|more) evidence\b/i,
      /\bsearch for (contradicting|contradictory|supporting|more) (evidence|sources)\b/i,
    ],
  },
  {
    verb: "UPLOAD_EVIDENCE",
    patterns: [
      /\buse (this|that|the) (paper|pdf|document|file|datasheet|spec|publication)\b/i,
      /\b(add|attach|include) (this|that|the) (paper|pdf|document|file|datasheet|spec)\b/i,
    ],
  },
  {
    verb: "COMPARE_MECHANISMS",
    patterns: [
      /\bcompare (the |the two |all )?(mechanisms|candidates|hypotheses|explanations)\b/i,
      /\bwhich (mechanism|candidate|explanation) is (stronger|better|more likely)\b/i,
    ],
  },
  {
    verb: "REQUEST_EXPERIMENT",
    patterns: [
      /\bdesign (a|an|the) (decisive )?(experiment|test)\b/i,
      /\bpropose (a|an|the) (decisive )?(experiment|test)\b/i,
    ],
  },
  {
    verb: "REQUEST_ENGINEERING",
    patterns: [
      /\bwork out the engineering\b/i,
      /\bestablish the (engineering|geometry|dimensions)\b/i,
      /\bbuild (a|the) (3d|three[- ]dimensional|cad) (model|design)\b/i,
    ],
  },
  {
    verb: "RESEARCH",
    patterns: [
      /\bresearch (this|it|that|further)\b/i,
      /\binvestigate (this|it|that) further\b/i,
      /\bkeep (investigating|looking)\b/i,
    ],
  },
  {
    verb: "REVIEW_PACKAGE",
    patterns: [
      /\b(review|open|show) (the )?(technology )?package\b/i,
    ],
  },
];

export type MessageRoute =
  | { kind: "ask" }
  | { kind: "action"; verb: Exclude<ActionVerb, "ASK"> };

/** Route one user message. ASK is the default — a message only becomes
 * an action when a pattern matches exactly. */
export function classifyMessage(text: string): MessageRoute {
  const t = String(text ?? "");
  for (const rule of PHRASE_RULES) {
    if (rule.patterns.some((re) => re.test(t))) {
      return { kind: "action", verb: rule.verb };
    }
  }
  return { kind: "ask" };
}

// ---------------------------------------------------------------------------
// the invocation path (Coder 2 owns THIS; Coder 1 owns the engine side)
// ---------------------------------------------------------------------------

export interface ActionResult {
  /** accepted — the engine accepted the action request for execution
   * (202). accepted:false + reason — the engine refused. */
  accepted: boolean;
  /** not_available — the engine does not implement the action endpoint
   * yet (the contract is defined; the capability is honestly absent). */
  not_available: boolean;
  /** R459: the engine opened a NEW investigation round carrying the
   * user's directive — the UI navigates to it. */
  new_run_id?: string;
  /** R459: a typed engine refusal (e.g. the run is still running) —
   * rendered verbatim, never guessed. */
  refusal?: string;
  action_id?: string;
  detail?: string;
}

const JSON_HEADERS = { "Content-Type": "application/json" };

export async function sendAction(
  runId: string,
  verb: Exclude<ActionVerb, "ASK">,
  params: Record<string, unknown> = {},
  post: (path: string, init: RequestInit) => Promise<Response> = (p, i) =>
    fetch(p, i),
): Promise<ActionResult> {
  let res: Response;
  try {
    res = await post(`/api/run/${runId}/actions`, {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify({
        action: verb,
        params,
        requested_via: "conversation",
      }),
    });
  } catch (e) {
    // transport-level failure — distinct from "not implemented"
    return {
      accepted: false,
      not_available: false,
      detail: e instanceof Error ? e.message : "request failed",
    };
  }
  if (res.status === 404 || res.status === 501) {
    // the contract's honest-absence state: the engine has not adopted
    // the action endpoint yet
    return { accepted: false, not_available: true };
  }
  if (res.status === 409) {
    // a typed engine refusal — render the engine's own words
    let reason = "";
    try {
      const b = (await res.json()) as Record<string, unknown>;
      reason = typeof b.reason === "string" ? b.reason : "";
    } catch {
      /* non-json error body */
    }
    return { accepted: false, not_available: false, refusal: reason };
  }
  if (res.ok) {
    let body: Record<string, unknown> = {};
    try {
      body = (await res.json()) as Record<string, unknown>;
    } catch {
      /* 202 with an empty body stays accepted */
    }
    return {
      accepted: true,
      not_available: false,
      new_run_id:
        typeof body.run_id === "string" ? body.run_id : undefined,
      action_id:
        typeof body.action_id === "string" ? body.action_id : undefined,
    };
  }
  let detail = "";
  try {
    detail = JSON.stringify(await res.json());
  } catch {
    /* non-json error body */
  }
  return { accepted: false, not_available: false, detail };
}
