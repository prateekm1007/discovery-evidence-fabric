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
// the deterministic steering router (presentation-level, no semantics)
//
// R463 (independent audit P0-1, "roadmap to 9/10"): the FIRST router's
// ~9 rigid phrasings were a measured product defect — any natural-
// language paraphrase of a steering intent ("make it cheaper", "use a
// different material", "optimize for manufacturability") silently
// demoted to a read-only question, and a demanding user concluded the
// conversation does not change the discovery. The table below keeps
// the SAME contract shape (ordered pattern rules → canonical verbs,
// ASK as the fallback) with a real steering lexicon: objective/
// constraint steering, alternative-material/mechanism shapes,
// politeness-prefixed imperatives, and per-verb paraphrase families.
// Deliberately still DETERMINISTIC and MODEL-FREE: it can only route
// to the engine's action endpoint or leave the message as a question
// (Ask ≠ Act is untouched; the settled R458 route-table guarantees —
// including "questions about the record stay ASK" — are pinned by
// adversarial_r458 and adversarial_r463 suites).
// ---------------------------------------------------------------------------

interface PhraseRule {
  verb: Exclude<ActionVerb, "ASK">;
  patterns: RegExp[];
}

/** Ordered — the FIRST match wins. */
const PHRASE_RULES: PhraseRule[] = [
  {
    // explicit document references — most specific first
    verb: "UPLOAD_EVIDENCE",
    patterns: [
      /\buse (this|that|the) (manufacturer'?s?|supplier'?s?|vendor'?s?)?\s?(paper|pdf|document|file|datasheet|data sheet|spec|specification|publication|drawing|report)\b/i,
      /\b(add|attach|include) (this|that|the|my) (paper|pdf|document|file|datasheet|data sheet|spec|specification|publication|drawing|report)\b/i,
      /\bbased on (this|that|the) (attached )?(paper|pdf|document|datasheet|data sheet|spec)\b/i,
      /\b(consult|consider) (this|that|the) (attached |uploaded )?(paper|pdf|document|datasheet|spec|publication)\b/i,
    ],
  },
  {
    verb: "ATTACK",
    patterns: [
      /\bchallenge (candidate|invention|architecture|this|the)\b/i,
      /\btry to disprove\b/i,
      /\battack (candidate|invention|architecture|this|the)\b/i,
      /\b(disprove|falsify) (candidate|invention|this|it|the)\b/i,
      /\bi'?m not convinced\b/i,
      /\b(i (doubt|question|disagree with)) (this|it|that|the)\b/i,
      /\b(look|poke) (for weaknesses|holes)\b/i,
      /\bfind (the|a) (flaw|weakness|hole|failure mode) (in|of)\b/i,
      /\bweakness(es)? (in|of) (this|it|the candidate|the design)\b/i,
      /\bstress[- ]?test (this|it|the)\b/i,
      /\b(red[- ]team|adversarially (review|test)) (this|it|the)\b/i,
      /\b(poke|punch) holes in\b/i,
      /\bplay( the)? devil'?s advocate\b/i,
    ],
  },
  {
    verb: "COMPARE_MECHANISMS",
    patterns: [
      /\bcompare (the |the two |all )?(mechanisms|candidates|hypotheses|explanations|designs|options|approaches)\b/i,
      /\bwhich (mechanism|candidate|explanation|design|option) is (stronger|better|more likely|best|strongest)\b/i,
      /\bstack(ed)? up against\b/i,
      /\btrade[- ]?offs? (between|of|among)\b/i,
      /\b(what|which) (are the )?trade[- ]?offs?\b/i,
      /\bhead[- ]to[- ]head\b/i,
      /\bside[- ]by[- ]side (comparison|of)\b/i,
      /\brank (the )?(candidates|mechanisms|options|designs)\b/i,
      /\b(candidate|mechanism|design) [12ab] (vs\.?|versus) (candidate|mechanism|design) [12ab]\b/i,
    ],
  },
  {
    verb: "FIND_EVIDENCE",
    patterns: [
      /\b(look|find|search) for (contradicting|contradictory|supporting|more|additional) (evidence|sources|data)\b/i,
      /\bsearch for (contradicting|contradictory|supporting|more) (evidence|sources)\b/i,
      /\b(find|look for|search for|pull|gather|check|get) (the )?(prior art|literature|publications|related work|state of the art|standards|clinical data|adverse[- ]event (data|reports)|patents?)\b/i,
      /\bany (evidence|sources|data|publications) (for|against|on|about)\b/i,
      /\b(evidence|sources) (against|contradicting|supporting) (this|it|that|the candidate|the mechanism)\b/i,
      /\bis there (evidence|literature|any study|any source)\b/i,
      /\bvalidate (this|it|the claim) against (the )?(literature|evidence|data|sources)\b/i,
    ],
  },
  {
    verb: "REQUEST_EXPERIMENT",
    patterns: [
      /\bdesign (a|an|the) (decisive )?(experiment|test)\b/i,
      /\bpropose (a|an|the) (decisive )?(experiment|test)\b/i,
      /\b(a|an|the) (decisive|killer) (experiment|test)\b/i,
      /\bdesign (a|an|the)? ?(bench|benchtop|physical|validation|verification) (test|experiment|trial|protocol)\b/i,
      /\bpropose (a|an|the)? ?(physical|bench|validation) (test|protocol|trial)\b/i,
      /\b(test|experiment) (plan|protocol) (for|to verify|to validate)\b/i,
      /\bhow (would|do) we (test|verify|validate) (this|it|that)\b/i,
    ],
  },
  {
    verb: "REQUEST_ENGINEERING",
    patterns: [
      /\bwork out the engineering\b/i,
      /\bestablish the (engineering|geometry|dimensions)\b/i,
      /\bbuild (a|the) (3d|three[- ]dimensional|cad) (model|design)\b/i,
      /\boptimi[sz]e (it|this|that|the design|the candidate)? ?for\b/i,
      /\b(manufacturing|production|fabrication) (approach|process|route|method|plan|steps?)\b/i,
      /\bwork (out|up) (the )?(manufacturing|production|fabrication)\b/i,
      /\bwork out how to (actually |best )?(manufacture|produce|fabricate|build|make) (this|it|that|them)\b/i,
      /\b(engineering|dimensional) (specification|realization|package)\b/i,
      /\bspec(ify| out) (the )?(geometry|dimensions|materials|tolerances?)\b/i,
    ],
  },
  {
    verb: "REVIEW_PACKAGE",
    patterns: [
      /\b(review|open|show|see) (me )?(the )?(technology )?package\b/i,
      /\b(download|export|generate|get|build|produce) (the )?(package|zip|dossier|bundle|deliverable)\b/i,
      /\bi(’|')?d (like|want) (the|a) (technology )?package\b/i,
      /\bshow (me )?the deliverable\b/i,
    ],
  },
  {
    verb: "RESEARCH",
    patterns: [
      /\bresearch (this|it|that|further)\b/i,
      /\binvestigate (this|it|that) further\b/i,
      /\bkeep (investigating|looking|going|digging|pushing|exploring)\b/i,
      /\b(dig|dive|go) deeper\b/i,
      /\bgo (further|broader|wider)\b/i,
      /\bmore (detail|depth|analysis|investigation)\b/i,
      /\bcontinue (the )?(investigation|research|search|exploration)\b/i,
      /\bexpand (the )?(search|investigation|evidence|scope)\b/i,
      /\belaborate on (this|it|that)\b/i,
    ],
  },
  {
    // the broadest family LAST: alternative/destination steering and
    // objective/constraint steering ("make it cheaper", "use a
    // different material", "reduce the pressure loss")
    verb: "CHANGE_MECHANISM",
    patterns: [
      /\btry (another|a different|an alternative|a second|one more) (mechanism|approach|explanation|hypothesis|concept|route|principle|configuration|material|design)\b/i,
      /\bchange the mechanism\b/i,
      /\b(keep|hold|preserve) (the|that) .*(constraint|requirement).* (but|and) change\b/i,
      /\bwhat else could (cause|explain) (this|it)\b/i,
      /\b(use|try|switch to|go with|move to|swap (to|for)) (a different|another|an alternative|some other) (material|polymer|elastomer|mechanism|approach|geometry|configuration|concept|actuator|design|coating|adhesive|spring|valve)\b/i,
      /\b(make|get|design|build|redesign|rework|turn) (it|this|them|the design|the candidate|the concept|the invention|the mechanism) (cheaper|smaller|lighter|safer|stronger|faster|simpler|stiffer|thinner|longer|shorter|more (compact|durable|efficient|affordable|reliable|biocompatible|manufacturable|robust|flexible|rigid))\b/i,
      /\b(reduce|lower|minimi[sz]e|cut|shrink|bring down|decrease) (the |its |their )?(cost|pressure (loss|drop)|weight|size|profile|complexity|friction|leakage|risk)\b/i,
      /\b(improve|increase|boost|maximi[sz]e) (the |its |their )?(reliability|efficiency|flow|durability|strength|safety margin)\b/i,
      /\b(cheaper|less expensive|more affordable) (design|approach|mechanism|solution|way|version|option)\b/i,
      /\b(avoid|eliminate|get rid of|prevent|design out) (the )?(kink|kinking|fatigue|leak|leakage|failure|obstruction|debris)\b/i,
      /\bwhat if (we|you) (used|tried|changed|made|replaced|swapped)\b/i,
      /\b(different|other|alternative) (way|route|path) (to|of|for)\b/i,
      /\binstead of (this|that|the current)\b/i,
      /\btake (a|another) (different|new) (direction|angle|approach)\b/i,
    ],
  },
];

export type MessageRoute =
  | { kind: "ask" }
  | { kind: "action"; verb: Exclude<ActionVerb, "ASK"> };

// ---------------------------------------------------------------------------
// R461 (independent audit P0-2): the user's words ride the action.
//
// The audit measured the deployed UI passing `{}` to sendAction — the
// engine forked a child round whose directive was only "[CHANGE_MECHANISM]",
// the typed instruction discarded. The R458 contract defines exactly where
// the words go: params.direction is "the user's own words" (verbatim),
// FIND_EVIDENCE carries a mode, ATTACK may carry a target. This builder is
// DETERMINISTIC presentation logic: it copies the user's text byte-for-byte
// and derives NOTHING scientific (Art. X / §27 — no frontend epistemology).
// ---------------------------------------------------------------------------

export function findEvidenceMode(text: string): "contradictory" | "supporting" | "general" {
  const t = String(text ?? "").toLowerCase();
  if (/\bcontradict(ing|ory)\b/.test(t) || /\bdisprov/.test(t)) {
    return "contradictory";
  }
  if (/\bsupporting\b/.test(t)) return "supporting";
  return "general";
}

export function buildActionParams(
  verb: Exclude<ActionVerb, "ASK">,
  text: string
): Record<string, unknown> {
  const t = String(text ?? "").trim();
  const params: Record<string, unknown> = {};
  if (t) params.direction = t; // the user's exact words — never paraphrased
  if (verb === "FIND_EVIDENCE") params.mode = findEvidenceMode(t);
  return params;
}

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
