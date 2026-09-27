// R453-C2 — THE CANONICAL-STATE PRESENTATION LAYER.
//
// ONE pure module that translates canonical scientific/engineering state
// into user-facing conversation. Every sentence the product speaks about
// state flows through HERE — never re-derived inside a component, never
// upgraded client-side (Art. X: the UI is a projection of canonical
// state, not another epistemic authority; Art. XXVIII: no silent
// semantic promotion; Art. LXI: infrastructure failure is never a
// scientific rejection).
//
// State-honesty contracts pinned by tests/webapp/adversarial tests:
//   Test A  rejected candidate            -> "Rejected", never success
//   Test B  RUN_BLOCKED_TRANSPORT + stale COMPLETED_CANDIDATE +
//           visual_complete + ENGINEERING -> current run blocked; stale
//           positive interpretation SUPPRESSED from the conversation
//   Test C  retrieval = PENDING           -> "Evidence retrieval in
//                                           progress", never "not found"
//   Test D  retrieval = FAILED            -> "Evidence retrieval failed",
//                                           never "no evidence exists"
//   Test E  geometry = UNKNOWN            -> "Engineering geometry not
//                                           established", never
//                                           "engineering unavailable"
//                                           (unless canonical state says
//                                           unavailable)
//   Test F  attack = NOT_RUN              -> "The adversarial test has
//                                           not been completed", never
//                                           "survived attack"
//
// The zero-dependency, React-free core is deliberate: the adversarial
// fixture suite runs it in plain Node, so the honesty contracts are
// executable evidence, not prose (Art. XVI).

import type {
  AskResponse,
  CompletionStates,
  DossierBody,
  DesignTabShape,
  EpistemicMeta,
  Msg,
  RankedPackage,
  RankedPackageView,
  RetrievalState,
  GeometryState,
  AttackState,
  CandidateView,
  NextAction,
  SurfaceId,
  SessionDetail,
  UserStateView,
  EngineNextAction,
} from "./present-types";
// R453-C2 merge: the canonical single definitions live in the two pure
// sibling libs — isTerminal in lib/presentationState.ts (one definition,
// never two) and the render-availability notice in lib/renderAvailability.ts
// (the R452 B2/B3/C7 authority-derived, null-safe version). present.ts
// composes them; every component renders, never re-derives.
import { isTerminal } from "./presentationState";
import { renderAvailabilityNotice } from "./renderAvailability";

export type {
  AskResponse,
  DesignTabShape,
  EpistemicMeta,
  Msg,
  RetrievalState,
  GeometryState,
  AttackState,
  CandidateView,
  NextAction,
  SurfaceId,
  EngineNextAction,
};

// ---------------------------------------------------------------------------
// run-status classification — RE-EXPORT (R453-C2 merge): the canonical
// isTerminal lives in lib/presentationState.ts (RunNarrative re-exports it
// from there; one definition, never two). Ground truth unchanged:
// toscanini/user_state.py + run status vocabulary.
// ---------------------------------------------------------------------------

export { isTerminal };

// Infrastructure-blocked / dead-without-verdict statuses. Art. LXI: these
// are NOT scientific verdicts and must never be presented as one.
export function isBlockedStatus(status: string): boolean {
  return (
    status === "RUN_BLOCKED_TRANSPORT" ||
    status === "INTERRUPTED" ||
    status.startsWith("ERROR")
  );
}

// Test B gate: when the CURRENT canonical run is infrastructure-blocked,
// every stale positive artifact on the record (an older COMPLETED
// candidate snapshot, visual_complete flags, engineering=true) is
// suppressed from the conversational interpretation. The full record
// stays available in the technical view; the conversation refuses to
// read it as a present-tense positive result.
export function suppressStalePositives(detail: SessionDetail): boolean {
  if (isBlockedStatus(detail.status)) return true;
  const outcome =
    detail.run_state?.outcome ?? detail.user_state_view?.outcome;
  return outcome === "RUN_BLOCKED";
}

// R458-C2 (§24: one canonical state → exactly ONE honest word): the
// rejection verdict is read from the canonical user_state KEY — never
// from the raw `rejected` boolean, which is the stale field the R452-B1
// audit corrected at the key layer (the challenge-killed case is
// COMPLETED_UNDER_DEVELOPMENT with the killed-by-challenge decision
// text, never a bare "Rejected"). A false premise remains the one
// honest scientific rejection (R451-C2 resolvePresentationState
// vocabulary: SCIENTIFIC_REJECTION == COMPLETED_FALSE_PREMISE only).
export function isRejectedOutcome(detail: SessionDetail): boolean {
  if (suppressStalePositives(detail)) return false;
  const usv = detail.user_state_view;
  const outcome =
    detail.run_state?.outcome ?? detail.user_state_view?.outcome;
  return (
    usv?.user_state === "COMPLETED_FALSE_PREMISE" ||
    outcome === "FALSE_PREMISE_INCOHERENT"
  );
}

// R458-C2 (§6): the machine killed its own invention and no verified
// survivor replaced it. The run is terminal — nothing more happens
// without the user, so the next-best action is a fresh, better-aimed
// formulation. The generation records (what was killed and why) stay
// one click away in the workspace.
export function isKilledByChallenge(detail: SessionDetail): boolean {
  if (suppressStalePositives(detail)) return false;
  const usv = detail.user_state_view;
  return (
    usv?.user_state === "COMPLETED_UNDER_DEVELOPMENT" &&
    (usv?.outcome ?? "") === "INVENTION_KILLED_BY_CHALLENGE"
  );
}

// ---------------------------------------------------------------------------
// retrieval state — the five canonical retrieval states, verbatim
// (grounded in toscanini/run_state.py::_evidence_state: FAILED / GATHERED
// + records_found / PENDING / NOT_REACHED; zero results = GATHERED with
// records_found == 0. Article XXI: zero results is not novelty, provider
// failure is not absence.)
// ---------------------------------------------------------------------------

export function deriveRetrievalState(
  detail: SessionDetail,
  dossier: DossierBody | null | undefined
): RetrievalState {
  const ev = detail.run_state?.evidence_state;
  const evTab = dossier?.tabs?.evidence;
  const terminal = isTerminal(detail.status);
  const running = !terminal;

  // server-declared failure first (a failed retrieval is NOT zero results)
  const st = String(ev?.state ?? "").toUpperCase();
  if (st === "FAILED") return "FAILED";
  const stageRetrieve = (detail.stages ?? []).find((s) => s.stage === "RETRIEVE");
  if (stageRetrieve?.status && /FAIL/i.test(stageRetrieve.status)) {
    return "FAILED";
  }

  // positive: the server counted real records into the evidence pool
  if ((ev?.records_found ?? 0) > 0) return "RETRIEVED_POSITIVE";
  if ((evTab?.retrieved_count ?? 0) > 0 || (evTab?.items?.length ?? 0) > 0) {
    return "RETRIEVED_POSITIVE";
  }

  // explicit zero: retrieval COMPLETED and matched nothing (Art. XXI.2 —
  // a statement about the queries, never proof of novelty/absence)
  if (st === "GATHERED" && (ev?.records_found ?? 0) === 0 && ev) {
    return "RETRIEVED_ZERO";
  }

  if (st === "PENDING" || (!st && running)) {
    return running ? "PENDING" : "NOT_REACHED";
  }
  if (st === "NOT_REACHED") return "NOT_REACHED";

  // terminal with no retrieval state recorded at all: the stage never ran
  return terminal ? "NOT_REACHED" : "PENDING";
}

export function retrievalSentence(state: RetrievalState, detail: SessionDetail, dossier: DossierBody | null | undefined): string {
  const ev = detail.run_state?.evidence_state;
  const evTab = dossier?.tabs?.evidence;
  const n = ev?.records_found ?? evTab?.retrieved_count ?? null;
  const sources = ev?.sources ?? [];
  switch (state) {
    case "RETRIEVED_POSITIVE":
      return (
        `I found ${n ?? "the relevant"} sources in the evidence base` +
        (sources.length
          ? ` (${sources.slice(0, 3).join(", ")}${sources.length > 3 ? ", …" : ""})`
          : "") +
        ". Each one is custody-frozen with a content hash."
      );
    case "RETRIEVED_ZERO":
      return "The searches completed and returned no matching records. That is a statement about these queries in these databases — it is not evidence that the concept is novel or that no relevant work exists.";
    case "PENDING":
      return "Evidence retrieval is in progress — I'm searching the indexed sources now.";
    case "FAILED":
      return "Evidence retrieval failed — the sources could not be reached. This is an infrastructure state, not evidence of absence. Nothing was concluded from it, and the run can resume where it stopped.";
    case "NOT_REACHED":
      return "The evidence stage was not reached on this run — retrieval never began, so there is nothing to report from the sources yet. That is not a finding about the problem.";
  }
}

// ---------------------------------------------------------------------------
// geometry / model state (Test E). Grounded in the design tab's
// availability vocabulary (AVAILABLE / PENDING / UNAVAILABLE /
// NOT_ESTABLISHED), the CIO geometry class, and the R436 hero-eligibility
// projection. UNKNOWN (nothing established) is distinct from UNAVAILABLE
// (established but the presentation/render path is down) — conflating
// them was the identified presentation defect.
// ---------------------------------------------------------------------------

export function deriveGeometryState(
  detail: SessionDetail,
  dossier: DossierBody | null | undefined
): GeometryState {
  const design = dossier?.tabs?.design as DesignTabShape | undefined;
  const running = !isTerminal(detail.status);
  const avail = String(design?.availability ?? "").toUpperCase();

  if (design?.availability === "AVAILABLE") {
    // the canonical record distinguishes conceptual architecture from
    // engineering geometry (BS-025: a render never validates physics)
    if (design?.hero_eligibility?.eligible === false) return "UNEARNED";
    return design?.conceptual || design?.fallback_basis
      ? "CONCEPTUAL"
      : "ENGINEERING";
  }
  if (avail === "UNAVAILABLE") return "UNAVAILABLE";
  if (avail === "NOT_ESTABLISHED") return "UNKNOWN";
  if (running) return "PENDING";
  // terminal, no design tab record at all
  return "UNKNOWN";
}

export function geometrySentence(
  state: GeometryState,
  dossier: DossierBody | null | undefined
): string {
  const design = dossier?.tabs?.design as DesignTabShape | undefined;
  switch (state) {
    case "ENGINEERING":
      return "The technology model is the run's canonical engineering geometry — the same geometry the record carries, not an illustration.";
    case "CONCEPTUAL":
      return "A conceptual architecture model is shown. It presents the hypothesis so you can inspect it — it is not validated engineering geometry, and it never implies a physical result.";
    case "UNEARNED":
      return "The investigation recorded an architecture, but the system could not produce a visual model that faithfully represents it — so no model is shown. A substitute object would misrepresent the engineering state.";
    case "UNAVAILABLE":
      return (
        "Engineering geometry exists on this run; the visual rendering is " +
        "unavailable right now — an infrastructure state, and the geometry " +
        "itself is unaffected." +
        (design?.note ? ` ${design.note}` : "")
      );
    case "PENDING":
      return "The technology model will appear here as the design solidifies.";
    case "UNKNOWN":
      return "Engineering geometry is not established on this run. Nothing is rendered because nothing was established — showing a model anyway would misrepresent the state.";
  }
}

// ---------------------------------------------------------------------------
// attack state (Test F). Grounded in run_state attack_state.overall and
// the generation challenge records (killed / survived / escalated).
// ---------------------------------------------------------------------------

export function deriveAttackState(
  detail: SessionDetail,
  dossier: DossierBody | null | undefined
): AttackState {
  const running = !isTerminal(detail.status);
  const attack = detail.run_state?.attack_state;
  const overall = String(attack?.overall ?? "").toUpperCase();
  const gens = detail.run_state?.generations?.generations ?? [];
  const genChallenge = [...gens].reverse().find((g) => g.challenge)?.challenge;
  const stageAttack = (detail.stages ?? []).find((s) => s.stage === "ATTACK");

  if (genChallenge?.escalated_objection) return "CONTESTED";
  if (genChallenge?.killed) return "FAILED";
  if (genChallenge?.survived) return "SURVIVED";
  if (overall === "SURVIVED" || overall === "PASS" || overall === "COMPLETE_PASS") {
    return "SURVIVED";
  }
  if (overall === "CONTESTED") return "CONTESTED";
  if (overall === "KILL" || overall === "FAILED") return "FAILED";
  if (stageAttack?.status && /FAIL/i.test(stageAttack.status)) return "FAILED";
  if (running && (attack?.state === "IN_PROGRESS" || overall === "")) {
    return attack?.state === "IN_PROGRESS" ? "IN_PROGRESS" : "NOT_RUN";
  }
  return "NOT_RUN";
}

// ---------------------------------------------------------------------------
// R470 (external re-audit P1-3): kill causes in plain language, stated
// once. The eight canonical adversarial dimensions (a2/adversarial.py)
// are translated here — the single translation authority — instead of
// repeating the machine taxonomy on the buyer surface. The raw recorded
// cause stays in the technical record (run record / evidence pack).
// ---------------------------------------------------------------------------
const KILL_CAUSE_PROSE: Record<string, string> = {
  unsupported_mechanism: "the recorded evidence did not support the mechanism",
  weak_transfer: "the effect did not transfer convincingly from its source domain",
  obvious_combination: "it was an obvious combination of known techniques",
  prior_art: "prior work already covers the idea",
  contradiction: "it contradicted the recorded evidence",
  boundary_failure: "its boundary conditions were missing or violated",
  engineering_infeasibility: "it was not engineering-feasible as specified",
  regulatory_incompatibility: "it would face regulatory barriers",
};

export function killCauseSentence(
  killReason: string | null | undefined
): string {
  const raw = String(killReason ?? "").toLowerCase();
  const hits = Object.keys(KILL_CAUSE_PROSE).filter((k) => raw.includes(k));
  if (hits.length === 0) return "";
  const clauses = hits.map((k) => KILL_CAUSE_PROSE[k]);
  const list =
    clauses.length === 1
      ? clauses[0]
      : clauses.slice(0, -1).join("; ") + "; and " + clauses[clauses.length - 1];
  return ` The challenge rejected it on ${clauses.length} ` +
    `${clauses.length === 1 ? "front" : "fronts"}: ${list}.`;
}

export function attackSentence(state: AttackState, detail: SessionDetail): string {
  const genChallenge = [
    ...(detail.run_state?.generations?.generations ?? []),
  ].reverse().find((g) => g.challenge)?.challenge;
  switch (state) {
    case "SURVIVED":
      return "I tried to prove the leading candidate wrong — it survived the specified adversarial tests" +
        (strongestChallengeSentence(detail) ? `, including: "${strongestChallengeSentence(detail)}"` : "") +
        ".";
    case "CONTESTED":
      return "The adversarial instrument raised an objection it is not calibrated to decide, so the objection is preserved and escalated for adjudication — it is not treated as a verdict, and not treated as a pass either.";
    case "FAILED": {
      // R470 (P1-3): recognizable dimension taxonomies become one
      // plain-language enumeration (stated once, no "killed dimensions:
      // [same list]" repetition); a short non-taxonomy recorded cause
      // (e.g. "failure mode not documented") is quoted as-is; no cause
      // at all points to the technical record rather than inventing one.
      const causes = killCauseSentence(genChallenge?.kill_reason);
      if (causes) {
        return "The adversarial tests contradicted this candidate." + causes;
      }
      return "The adversarial tests contradicted this candidate." +
        (genChallenge?.kill_reason
          ? ` Recorded cause: ${genChallenge.kill_reason}`
          : "") +
        ".";
    }
    case "IN_PROGRESS":
      return "Now I'm trying to prove this wrong — the adversarial test is running.";
    case "NOT_RUN":
      return "The adversarial test has not been completed. Nothing is claimed either way — a candidate is never called 'survived' by default.";
    case "UNRESOLVED":
      return "The adversarial result is unresolved — the recorded state carries no verdict.";
  }
}

function strongestChallengeSentence(detail: SessionDetail): string | null {
  return (
    (detail.stages ?? []).find((s) => s.stage === "ATTACK")?.challenges?.[0]
      ?.challenge ?? null
  );
}

// ---------------------------------------------------------------------------
// R470 parallel-line reconciliation (P1-3): the sibling R470-C2 line's
// KILL_CAUSE_PROSE + killCauseSentence (above) is the ONE kill-prose
// authority — this line's equivalent helper set (drafted by the
// delegated engineer under CTO spec) was dropped here as the duplicate;
// the record-layer dedupe in a2/classify.py handles the double-listed
// taxonomy upstream, and the raw cause stays in the technical record.
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// candidates — competing hypotheses (brief §16), from the canonical
// generations projection only. The frontend never infers a candidate.
// ---------------------------------------------------------------------------

export function deriveCandidates(detail: SessionDetail): CandidateView[] {
  // R510 dry-run cliff: when the backend serves the canonical ranked
  // portfolio projection, it is rendered VERBATIM in canonical order
  // (no client-side sort, no derived rank/distinctness — React reads).
  const portfolio = detail.run_state?.portfolio?.candidates ?? null;
  if (portfolio !== null) {
    return portfolio.map((p) => ({
      label: p.candidate_id ?? "candidate",
      intervention: p.intervention ?? null,
      mechanism: p.mechanism ?? null,
      why: p.predicted_effect ?? null,
      whatChanged: null,
      risk: p.falsification_test ?? null,
      attack: "NOT_RUN" as AttackState,
      maturity: p.state ?? null,
      current: false,
      killed: false,
      candidateId: p.candidate_id ?? null,
      rank: typeof p.rank === "number" ? p.rank : null,
      distinctness: p.distinctness ?? null,
      rankingBasis:
        p.ranking_basis != null ? JSON.stringify(p.ranking_basis) : null,
    }));
  }
  const gens = detail.run_state?.generations?.generations ?? [];
  return gens.map((g) => {
    const ch = g.challenge ?? {};
    let attack: AttackState = "NOT_RUN";
    if (ch.escalated_objection) attack = "CONTESTED";
    else if (ch.killed) attack = "FAILED";
    else if (ch.survived) attack = "SURVIVED";
    return {
      label: g.label ?? `Invention ${String(g.gen).padStart(2, "0")}`,
      intervention: g.architecture?.intervention ?? null,
      mechanism: g.architecture?.mechanism ?? null,
      why: g.architecture?.expected_effect ?? null,
      whatChanged: g.what_changed ?? null,
      risk: g.architecture?.falsification_test ?? null,
      attack,
      maturity: g.maturity ?? null,
      current:
        detail.run_state?.generations?.current_invention?.gen === g.gen,
      killed: ch.killed === true,
      candidateId: null,
      rank: null,
      distinctness: null,
      rankingBasis: null,
    };
  });
}

// ---------------------------------------------------------------------------
// the single next-best action (brief §19) — one recommendation, from
// canonical state only. The user can override it; the UI recommends.
// ---------------------------------------------------------------------------

export function deriveNextAction(
  detail: SessionDetail,
  dossier: DossierBody | null | undefined,
  packageAvailable: boolean,
  engineNextAction?: EngineNextAction | null
): NextAction | null {
  if (suppressStalePositives(detail)) {
    return { label: "Resume the investigation", kind: "retry",
             source: "presentation" };
  }
  if (isTerminal(detail.status)) {
    // R471 (audit P1-2): a direction the user asked for while the run
    // was live is the FIRST thing offered at the terminal state — the
    // engine recorded it durably; running it opens the child round
    // through the canonical action endpoint. Never lost, never applied
    // mid-flight.
    const queued = detail.queued_directive;
    if (queued?.directive) {
      const short = queued.directive.length > 60
        ? `${queued.directive.slice(0, 57)}…`
        : queued.directive;
      return {
        label: `Run your saved direction — “${short}”`,
        kind: "run_queued",
        source: "presentation",
      };
    }
    // R477 (audit P0-4): the ENGINE's own recorded next step is the one
    // authority when it exists — read from GET /api/run/{id}/contract
    // (the NBA controller's live record, else the persisted
    // NEXT_BEST_ACTION stage output). Mapped to product language and
    // executed through the SAME canonical action endpoint the
    // conversation steers with; unknown engine actions fall through to
    // the presentation derivation rather than being invented into
    // buttons (Art. VI).
    const mapped = engineNextAction
      ? mapEngineNextAction(engineNextAction)
      : null;
    if (mapped) return mapped;
    if (packageAvailable) {
      return { label: "Download the technology package", kind: "package",
               source: "presentation" };
    }
    if (isKilledByChallenge(detail)) {
      return {
        label: "Reformulate the problem and run again",
        kind: "new",
        source: "presentation",
      };
    }
    if (isRejectedOutcome(detail)) {
      return { label: "Reformulate the problem and run again", kind: "new",
               source: "presentation" };
    }
    const unknowns =
      (dossier?.tabs?.overview?.key_unknowns as
        | { statement?: string; priority?: string | null }[]
        | undefined) ?? [];
    if (unknowns.length > 0) {
      return {
        label: "Resolve what remains uncertain",
        kind: "surface",
        surface: "overview",
        source: "presentation",
      };
    }
    const experiment = dossier?.tabs?.experiment;
    if (experiment?.availability === "AVAILABLE") {
      return {
        label: "Review the decisive experiment",
        kind: "surface",
        surface: "experiment",
        source: "presentation",
      };
    }
    const design = dossier?.tabs?.design as DesignTabShape | undefined;
    if (design?.availability === "AVAILABLE") {
      return {
        label: "Inspect the technology model",
        kind: "surface",
        surface: "model",
        source: "presentation",
      };
    }
    // R459 (audit P0-4): the always-available deliverable — every
    // terminal run carries a diagnostic record (executive brief,
    // evidence summary, what was killed and why). No run ends with
    // nothing to take away.
    return { label: "Download the diagnostic record", kind: "diagnostic",
             source: "presentation" };
  }
  // running: the investigation is the action — no button theater
  return null;
}

// ---------------------------------------------------------------------------
// R477 (audit P0-4): the engine action vocabulary → the product's next
// action. The vocabulary is the NBA controller's CLOSED set
// (toscanini/conversational/nba_controller.py). ASK_CLARIFICATION and
// STOP_HONEST are deliberately unmapped: the answer box and the outcome
// banner are their surfaces, and mapping them to a button would invent
// an action the record does not carry.
// ---------------------------------------------------------------------------

function mapEngineNextAction(ena: EngineNextAction): NextAction | null {
  const action = String(ena.action ?? "").toUpperCase();
  if (!action) return null;
  const basis =
    typeof ena.reason === "string" && ena.reason.trim()
      ? ena.reason
      : null;
  switch (action) {
    case "RETRIEVE_MORE_EVIDENCE":
      return { label: "Look for more evidence", kind: "act",
               verb: "FIND_EVIDENCE", basis, source: "engine-record" };
    case "ATTACK_CANDIDATE":
      return { label: "Challenge the strongest candidate", kind: "act",
               verb: "ATTACK", basis, source: "engine-record" };
    case "GENERATE_COMPETING_MECHANISM":
      return { label: "Try another mechanism", kind: "act",
               verb: "CHANGE_MECHANISM", basis, source: "engine-record" };
    case "ENGINEERING_ESCALATION":
      return { label: "Work out the engineering", kind: "act",
               verb: "REQUEST_ENGINEERING", basis, source: "engine-record" };
    case "PROPOSE_DECISIVE_EXPERIMENT":
      return { label: "Design the decisive experiment", kind: "act",
               verb: "REQUEST_EXPERIMENT", basis, source: "engine-record" };
    case "PACKAGE_READY":
      return { label: "Download the technology package", kind: "package",
               basis, source: "engine-record" };
    default:
      return null;
  }
}

// ---------------------------------------------------------------------------
// THE CONVERSATION — one discovery told as one conversation.
// ---------------------------------------------------------------------------

let seq = 0;
function mid(kind: string): string {
  seq += 1;
  return `${kind}-${seq}`;
}

function outcomeTone(detail: SessionDetail): "positive" | "development" | "rejected" | "unknown" | "blocked" {
  const usv: UserStateView | undefined = detail.user_state_view;
  if (suppressStalePositives(detail)) return "blocked";
  if (isRejectedOutcome(detail)) return "rejected";
  const key = usv?.user_state ?? "";
  if (
    key === "COMPLETED_PACKAGE" ||
    key === "COMPLETED_CANDIDATE" ||
    key === "COMPLETED_EVOLVED"
  ) {
    return "positive";
  }
  if (
    key === "COMPLETED_UNDER_DEVELOPMENT" ||
    key === "COMPLETED_GENERATION_FAILED"
  ) {
    return "development";
  }
  if (key === "COMPLETED_UNKNOWN") return "unknown";
  if (key === "BLOCKED_TRANSPORT" || key === "FAILED_TRANSPORT" || key === "FAILED_ENGINE" || key === "INTERRUPTED") {
    return "blocked";
  }
  return "unknown";
}

const EPI_META: Record<string, EpistemicMeta> = {
  RETRIEVED: "FOUND",
  INFERRED: "INFERRED",
  HYPOTHESIZED: "HYPOTHESIS",
  COMPUTED: "TESTED",
  SIMULATED: "TESTED",
  ENGINEERING_DEFINED: "TESTED",
  PHYSICALLY_OBSERVED: "FOUND",
  UNKNOWN: "UNKNOWN",
};

export function epistemicMeta(cls: string | null | undefined): EpistemicMeta | null {
  if (!cls) return null;
  return EPI_META[cls] ?? null;
}

// R461 (independent audit P1-10): the maturity boundary is FIRST-LINE.
// The canonical maturity value may be a machine label (e.g.
// ENGINEERING_DEFINITION); rendered raw it can read as physical
// validation when the record carries zero physical observations
// (Art. XXVIII: a passing simulation is not a physical finding; the
// promotion ladder LX/LIII is never narrated upward by the UI). Each
// known label translates to a human sentence that carries the
// modelled-vs-physical boundary IN the same line. An unknown label
// falls back to the honest default — never invented semantics, and
// never a raw enum as the headline (BS-009).
export const MATURITY_BOUNDARY_DEFAULT =
  "Modelled result — the record carries no physical observation yet";

const MATURITY_PRESENTATION: Record<string, string> = {
  ENGINEERING_DEFINITION:
    "Engineering definition — a modelled design, not physically validated",
  ENGINEERING_DEFINED:
    "Engineering defined — a modelled design, not physically validated",
  COMPUTATIONAL:
    "Held up in computation — modelled, not physically validated",
  SIMULATED: "Simulated — modelled, not physically validated",
  MODELLED: "Modelled — not physically validated",
  HYPOTHESIS: "Hypothesis — nothing has been tested yet",
  HYPOTHESIZED: "Hypothesis — nothing has been tested yet",
  PHYSICALLY_OBSERVED: "Physically observed — measured on the real artifact",
};

export function presentMaturity(
  maturity: string | null | undefined
): string | null {
  const m = String(maturity ?? "").trim();
  if (!m) return null;
  const hit = MATURITY_PRESENTATION[m.toUpperCase()];
  return hit ?? `${m.charAt(0).toUpperCase() + m.slice(1).toLowerCase()} — not physically validated unless the record carries a physical observation`;
}

// R476 (UI audit, complexity hiding): the visual quality gate's raw
// verdict vocabulary (PASS / COMPLETE_PASS / …) is machine language —
// BS-009: it never renders as badge text on the primary surface. The
// badge shows product language; the raw verdict rides the title
// tooltip (deep layer), exactly like the model kind badge
// (ModelViewer's badge/badgeTitle pair). Anything outside the
// certified set reads "not certified" — the ABSENCE of a certification
// is stated honestly, never softened into a specific failure verdict
// the record does not carry, and never passed through as raw enum.
const GATE_BADGE_PRESENTATION: Record<string, string> = {
  PASS: "certified",
  COMPLETE_PASS: "fully certified",
};

export function presentGateVerdict(verdict: string): string {
  const v = String(verdict ?? "").trim();
  if (!v) return "not certified";
  return GATE_BADGE_PRESENTATION[v.toUpperCase()] ?? "not certified";
}

// R461 (independent audit P0-2): the steering directive of an action-
// opened round, rendered as the user's own words. The stored directive
// is "[VERB] the user's words" (toscanini/actions.py::directive_text);
// the conversation shows the user's words verbatim — the machine tag
// stays in the record (BS-009: no raw enums on the primary surface).
export function directiveDisplayText(directive: unknown): string | null {
  if (typeof directive !== "string" || !directive.trim()) return null;
  return directive.replace(/^\[[A-Z_]+\]\s*/, "").trim() || null;
}

export function deriveRankedPackages(
  detail: SessionDetail
): RankedPackageView[] {
  // R540: the ranked result set — the contract's "ranked technology
  // packages". Read VERBATIM from the session's ranked package set (the
  // worker's per-survivor record) or the engine's RANKED_DISCOVERY_
  // RESULTS projection. No client-side re-sort, re-score, or rank
  // inference: rank, admissibility, and components are the engine's
  // records, not the UI's guesses (Art. X/XXVIII).
  const pkgs = detail.ranked_packages ?? null;
  const rec = detail.ranked_results ?? null;
  const list: RankedPackage[] =
    pkgs && pkgs.length > 0
      ? pkgs
      : rec?.ranked_results?.filter((r) => r.admissible) ?? [];
  const completion = detail.completion_states ?? rec?.completion ?? null;
  void completion;
  return list.map((r) => {
    const c = r.components ?? {};
    const ev = c.evidence ?? {};
    const mech = c.mechanism ?? {};
    const adv = c.adversarial ?? {};
    const eng = c.engineering ?? {};
    const exp = c.decisive_experiment ?? {};
    const pkg = r.package ?? c.package ?? {};
    return {
      rank: typeof r.rank === "number" ? r.rank : null,
      candidateId: r.candidate_id ?? null,
      admissible: r.admissible ?? false,
      selected: r.selected ?? false,
      evidence: {
        count: Array.isArray(ev.records) ? ev.records.length : null,
        span: ev.mechanism_source_span ?? null,
        status: ev.evidence_status ?? null,
        // R543-2: the actual source provenance (never just a count) —
        // the recorded source identities the evidence record carries.
        sources: Array.isArray(ev.sources) ? ev.sources : [],
        sourceIdentity:
          (Array.isArray(ev.sources) && ev.sources[0]) ||
          (ev.records?.[0]?.source ?? null),
      },
      mechanism: {
        mechanism: mech.mechanism ?? null,
        intervention: mech.intervention ?? null,
        expectedEffect: mech.expected_effect ?? null,
        falsificationTest: mech.falsification_test ?? null,
        competing: mech.competing_considered ?? [],
        // R543-2: the complete competing-candidate summaries carried on
        // the authoritative ranked projection (candidate + mechanism +
        // kill condition + disposition), not only the competing IDs.
        competingCandidates: (Array.isArray(mech.competing_candidates)
          ? mech.competing_candidates
          : []).map((cc: Record<string, unknown>) => ({
            candidateId: (cc.candidate_id as string | null) ?? null,
            mechanism: (cc.mechanism as string | null) ?? null,
            intervention: (cc.intervention as string | null) ?? null,
            whatWouldKillIt:
              (cc.what_would_kill_it as string | null) ?? null,
            disposition: (cc.disposition as string | null) ?? null,
          })),
      },
      adversarial: {
        overall: adv.overall ?? null,
        disposition: adv.disposition ?? "UNRESOLVED",
        survived: adv.survived ?? false,
        killed: adv.killed ?? false,
        unresolved: adv.unresolved ?? false,
      },
      engineering: {
        geometryPresent: eng.geometry_present ?? false,
        modelClass: eng.model_class ?? null,
        limitations: eng.limitations ?? null,
      },
      experiment: {
        experiment: exp.experiment ?? null,
        discriminator: exp.predicted_discriminator ?? null,
        decisionRule: exp.decision_rule ?? null,
        executionStatus: exp.execution_status ?? null,
      },
      package: {
        kind: pkg.kind ?? "TECHNOLOGY_PACKAGE",
        complete: pkg.complete ?? false,
        zipName: pkg.zip_name ?? null,
        maturity: pkg.maturity ?? null,
        // R541: the candidate-bound package identity — each survivor's
        // OWN package (candidate_id + rank + zip + hash + manifest),
        // never a reused #1 package.
        candidateId: pkg.candidate_id ?? r.candidate_id ?? null,
        rank: typeof pkg.rank === "number" ? pkg.rank : null,
        packageId: pkg.package_id ?? null,
        zipSha256: pkg.zip_sha256 ?? null,
        zipSha256Matches: pkg.zip_sha256_matches ?? true,
        // R541: the candidate-specific download route — "Download
        // technology package #N" resolves to THIS candidate's package
        // (?candidate=<id>), not a shared /package surface for every
        // ranked card. Derived from the session's ranked_package_
        // downloads record; absent when the candidate's package is not
        // compiled (honest, never a borrowed #1 URL).
        downloadUrl:
          detail.ranked_package_downloads?.find(
            (d) =>
              d.candidate_id === (pkg.candidate_id ?? r.candidate_id)
          )?.download_url ??
          (pkg.complete && pkg.candidate_id
            ? `/api/run/${detail.session_id}/package?candidate=${pkg.candidate_id}`
            : null),
      },
      rankBasis:
        r.rank_basis != null ? JSON.stringify(r.rank_basis) : null,
    };
  });
}

export function deriveConversation(
  detail: SessionDetail,
  dossier: DossierBody | null | undefined,
  packageAvailable: boolean,
  engineNextAction?: EngineNextAction | null
): Msg[] {
  const msgs: Msg[] = [];
  const running = !isTerminal(detail.status);
  const blocked = suppressStalePositives(detail);
  const usv = detail.user_state_view;
  const overview = dossier?.tabs?.overview;
  const evidence = dossier?.tabs?.evidence;

  // 1 — the user's problem
  msgs.push({
    kind: "user",
    id: mid("u"),
    text: detail.user_text || detail.title || "Untitled problem",
  });

  // R461 (independent audit P0-2): an action-opened round carries the
  // user's steering words as the FIRST line of the conversation — the
  // exact text the user typed, from the canonical user_directive the
  // engine recorded (byte-for-byte in the record; the visible line
  // strips only the machine verb tag). The user's words were previously
  // invisible in the child round — the steering looked discarded.
  //
  // R466 (reaudit residual friction, root cause): the worker CONSUMES
  // and CLEARS user_directive when the round starts (worker.py applies
  // it to the problem understanding, then writes user_directive={}) —
  // so the steering words vanished from the thread the moment the run
  // actually began. The DURABLE record of the directive is the child's
  // own conversation context: the engine appends the directive there
  // at round creation (conversation_memory.record_conversation_context,
  // an append-only guarded field that is never cleared). Read order:
  // the durable conversation record FIRST, the transient
  // user_directive second (it covers rounds whose conversation entry
  // predates nothing — both exist for R459+ rounds; for any round one
  // of the two carries the words). A directive with no record anywhere
  // renders nothing (Art. VI: nothing is invented).
  const recordedDirective = detail.parent_session_id
    ? (Array.isArray(detail.conversation)
        ? detail.conversation.find(
            (c) =>
              c &&
              c.role === "user" &&
              typeof c.text === "string" &&
              c.text.trim().length > 0
          )?.text
        : undefined)
    : undefined;
  const directiveLine =
    directiveDisplayText(recordedDirective) ??
    directiveDisplayText(
      (detail as { user_directive?: { directive?: unknown } })
        .user_directive?.directive
    );
  if (directiveLine) {
    msgs.push({
      kind: "user",
      id: mid("ud"),
      text: directiveLine,
    });
  }

  // R458-C2 (§4) — THE CLARIFICATION PAUSE. The engine asked exactly ONE
  // material question (C1's R446 §4 rule: ask only when the answer
  // changes the search space or the next action). This is the
  // conversation changing the discovery — it renders as Toscanini's own
  // question, and the composer becomes the answer box. The pause is a
  // first-class state, never a stall and never an error (nothing is
  // burned while the question is open).
  if (detail.status === "AWAITING_CLARIFICATION") {
    const q = detail.clarification;
    msgs.push({
      kind: "clarification",
      id: mid("cl"),
      question:
        (q && typeof q.question === "string" && q.question) ||
        "Before I continue: is there anything about the problem I should know that would change what to look for?",
      decisionChanged:
        q && typeof q.decision_changed === "string"
          ? q.decision_changed
          : null,
    });
    msgs.push({
      kind: "note",
      id: mid("n-cl"),
      text: "The investigation is paused — it will resume the moment you answer.",
    });
    return msgs;
  }

  // Test B: a blocked run renders the honest pause and SUPPRESSES every
  // stale positive interpretation (candidate/package/visual_complete).
  // The blocked wording is derived from the CURRENT status only — never
  // from user_state_view, whose snapshot may predate the blocking event.
  if (blocked) {
    msgs.push({
      kind: "note",
      id: mid("n"),
      text: "I stopped partway — the infrastructure I need became unavailable.",
    });
    const failed =
      detail.run_state?.failure_state?.error ?? detail.error ?? null;
    const blockedLabel = detail.status.startsWith("RUN_BLOCKED")
      ? "Current run blocked"
      : detail.status === "INTERRUPTED"
        ? "Run interrupted"
        : "Run stopped by an infrastructure failure";
    msgs.push({
      kind: "outcome",
      id: mid("o"),
      tone: "blocked",
      label: blockedLabel,
      body:
        "Nothing was concluded about your problem — this is an infrastructure " +
        "state, never a scientific result." +
        (failed ? ` Recorded failure: ${failed}.` : "") +
        " Anything on the record from before the interruption stays in the " +
        "technical view; the conversation does not read it as a present-tense result.",
      next: deriveNextAction(detail, dossier, packageAvailable,
                             engineNextAction),
    });
    return msgs;
  }

  // 2 — the opening
  msgs.push({
    kind: "note",
    id: mid("n"),
    text: running
      ? "I'm investigating this. I'll work through the evidence, form candidate mechanisms, and try to disprove the strongest one — you'll see each step here as the record is written. A full run takes minutes rather than seconds; you can leave and come back, and this conversation resumes from the record."
      : "Here is what the investigation found, and how far it got.",
  });

  // 3 — evidence (Test C/D: PENDING and FAILED are distinct honest states)
  const retrieval = deriveRetrievalState(detail, dossier);
  if (retrieval === "RETRIEVED_POSITIVE") {
    msgs.push({
      kind: "evidence",
      id: mid("e"),
      state: retrieval,
      retrieved:
        detail.run_state?.evidence_state?.records_found ??
        evidence?.retrieved_count ??
        null,
      used: evidence?.used_count ?? null,
      domains: detail.run_state?.evidence_state?.sources ?? [],
      body: retrievalSentence(retrieval, detail, dossier),
      openSurface: "evidence",
    });
  } else {
    msgs.push({
      kind: "note",
      id: mid("e"),
      text: retrievalSentence(retrieval, detail, dossier),
    });
  }

  // 4 — the mechanism / candidates (brief §16 — competing hypotheses)
  const candidates = deriveCandidates(detail);
  const mechanism =
    overview?.mechanism ??
    detail.run_state?.mechanism_state?.mechanism ??
    null;
  if (candidates.length > 0) {
    msgs.push({
      kind: "candidates",
      id: mid("c"),
      items: candidates,
    });
  } else if (mechanism) {
    msgs.push({
      kind: "note",
      id: mid("c"),
      epi: "HYPOTHESIS",
      text: `A candidate mechanism emerged: ${mechanism}`,
    });
  }

  // 5 — the attack (brief §17 — scientific skepticism; Test F)
  if (candidates.length > 0 || mechanism) {
    const attack = deriveAttackState(detail, dossier);
    const strongestChallenge =
      overview?.strongest_challenge ??
      dossier?.falsification?.challenge_condition ??
      null;
    msgs.push({
      kind: "attack",
      id: mid("a"),
      state: attack,
      challenge: strongestChallenge,
      body: attackSentence(attack, detail),
    });
  }

  // R464 (external audit P1-1): THE DECISIVE TEST rides the conversation
  // thread itself. The audit's mobile finding: the workspace never
  // auto-opens below the desktop breakpoint, so surfaces that live only
  // behind the panel are invisible without prior knowledge. The model and
  // package already ride artifact cards; the experiment surface had NO
  // in-thread affordance. Terminal runs with an AVAILABLE experiment tab
  // now get one — on every viewport, the conversation is the index.
  const experimentTab = dossier?.tabs?.experiment as
    | { availability?: string }
    | undefined;
  if (!running && experimentTab?.availability === "AVAILABLE") {
    msgs.push({
      kind: "artifact",
      id: mid("x"),
      surface: "experiment",
      title: "The decisive experiment",
      body: "The one test that could settle the leading candidate — specified with what it would take to falsify it, from the run's own record.",
      cta: "Open the experiment",
    });
  }

  // 6 — the artifact (the model) — honest geometry states (Test E).
  // When the run is terminal and NO geometry was established, the
  // unknown is REPRESENTED in the conversation (brief §13) — never
  // silently read as "unavailable" or as "complete".
  const geometry = deriveGeometryState(detail, dossier);
  if (
    geometry === "ENGINEERING" ||
    geometry === "CONCEPTUAL" ||
    (geometry === "UNAVAILABLE" &&
      (dossier?.tabs?.design as DesignTabShape | undefined)?.availability ===
        "AVAILABLE")
  ) {
    msgs.push({
      kind: "artifact",
      id: mid("m"),
      surface: "model",
      title: "The technology model",
      body: geometrySentence(geometry, dossier),
      cta: "Open the model",
    });
  } else if (!running && geometry === "UNKNOWN" && !isRejectedOutcome(detail)) {
    // a rejection stays the terminal word (Test A) — no geometry noise
    msgs.push({
      kind: "note",
      id: mid("g"),
      epi: "UNKNOWN",
      text: geometrySentence("UNKNOWN", dossier),
    });
  }

  // 7 — the outcome (terminal) or the live progress line
  if (!running) {
    // R477 (audit P0-1): the directive-outcome card — a direction the
    // user asked for while the run was live rides the thread BEFORE the
    // outcome, so the receipt is unmissable: the words are the user's
    // (verbatim from the engine record), and the statement is exact —
    // saved, never applied mid-flight, one tap away via the run_queued
    // next action below.
    const savedDirective = directiveDisplayText(
      detail.queued_directive?.directive
    );
    if (savedDirective) {
      msgs.push({
        kind: "queued",
        id: mid("q"),
        text: savedDirective,
      });
    }
    const tone = outcomeTone(detail);
    const next = deriveNextAction(detail, dossier, packageAvailable,
                                  engineNextAction);
    // R540: the ranked result set — when the run produced at least one
    // admissible ranked survivor, the conversation leads with the
    // RANKED DISCOVERIES (each carrying its six components + rank basis
    // + attached technology package), then the completion-state
    // summary. A diagnostic-only run (no admissible survivor) never
    // claims a finished discovery: it stays the honest non-finished
    // state (the diagnostic package, not a technology package).
    const ranked = deriveRankedPackages(detail);
    const completion = detail.completion_states ?? null;
    // R542: FINISHED_DISCOVERY is the BACKEND completion contract's
    // answer (the six-part contract verified against the run's own
    // artifacts at the run tail). The UI may not upgrade a run into a
    // finished conversation from the package state alone — a run whose
    // experiment/evidence/engineering component is missing is not
    // finished even when every package compiled (Art. X: one authority).
    const finished = completion?.FINISHED_DISCOVERY === true;
    if (ranked.length > 0) {
      msgs.push({
        kind: "ranked",
        id: mid("ranked"),
        items: ranked,
        completion,
        finished,
      });
    }
    if (tone === "positive") {
      msgs.push({
        kind: "outcome",
        id: mid("o"),
        tone,
        label: usv?.label ?? "A promising technology",
        body:
          usv?.decision ??
          "The surviving candidate is presented with its honest maturity — the verification gates decide maturity, never the wording.",
        next,
      });
      // the package artifact card rides the positive outcome
      if (packageAvailable) {
        msgs.push({
          kind: "artifact",
          id: mid("p"),
          surface: "package",
          title: "Technology package",
          body: "Everything needed to evaluate, build, or commission the decisive experiment — evidence, engineering, risks, and the falsification plan.",
          cta: "Open the package",
        });
      }
    } else if (tone === "rejected") {
      msgs.push({
        kind: "outcome",
        id: mid("o"),
        tone,
        label: "Rejected",
        body:
          usv?.decision ??
          "The evidence contradicted the problem's premise. Rejected is a finding — the investigation did its job.",
        next,
      });
    } else {
      msgs.push({
        kind: "outcome",
        id: mid("o"),
        tone,
        label: usv?.label ?? "Investigation complete",
        body:
          usv?.decision ??
          usv?.meaning ??
          "The run reached a terminal state; the recorded outcome is carried verbatim below.",
        next,
      });
    }
  } else {
    const live = [...(detail.stages ?? [])].reverse()[0];
    msgs.push({
      kind: "progress",
      id: mid("l"),
      live: true,
      text: live
        ? "Still working" + elapsedSuffix(detail.created_at) +
          " — the latest recorded step is below; this conversation updates as the run records them."
        : "Still working" + elapsedSuffix(detail.created_at) +
          " — I'm reading the problem and binding it to the evidence base.",
    });
  }

  return msgs;
}

// R461 (independent audit, P0 observability): how long the run has
// actually been going, in the user's language, derived from the
// record's own created_at — never an invented ETA, never machinery
// vocabulary. The audit's finding: "one progress sentence is good, but
// add elapsed time … without exposing provider details."
export function elapsedSuffix(
  createdAt: string | undefined,
  now: number = Date.now()
): string {
  const t = Date.parse(String(createdAt ?? ""));
  if (Number.isNaN(t)) return "";
  const mins = Math.max(0, Math.floor((now - t) / 60000));
  if (mins < 1) return "";
  if (mins < 60) return ` for ${mins} min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m ? ` for ${h} h ${m} min` : ` for ${h} h`;
}

// ---------------------------------------------------------------------------
// presentation-only render availability — DELEGATED (R453-C2 merge).
// The sentence implementation lives in lib/renderAvailability.ts: the R452
// external-audit version whose geometry phrase is DERIVED from the recorded
// authority (a conceptual model is never described as engineering geometry,
// Art. XXVIII), whose NOT_ATTEMPTED state is an explicit branch (never
// silence), and which is null-safe by construction. The old copy here
// asserted a blanket availability claim in every branch — the exact R452-B2
// defect class; the merge removes it so ONE implementation serves every
// surface. Callers pass the recorded geometry authority when they have it.
// ---------------------------------------------------------------------------

export function renderAvailabilitySentence(
  r: {
    status?: string;
    visual_gate?: { verdict?: string; hero_suppressed?: boolean };
  } | null | undefined,
  geometry?: {
    engineering_authority?: string | null;
    conceptual?: boolean | null;
  },
): string {
  return renderAvailabilityNotice(r, geometry);
}

// re-export the ask-response type consumer components already use
export type { AskResponse as AskResponseT } from "./present-types";
