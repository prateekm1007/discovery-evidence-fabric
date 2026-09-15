"use client";

// R453-C2 — THE CONVERSATION: one discovery told as one conversation.
//
// The pipeline is visible as a STORY, not as machinery. Every message
// here is derived from canonical state through lib/present.ts — the
// component renders; it never re-derives epistemic state, never
// upgrades a class, never converts unknown into certainty (Art. X /
// XXV / XXVIII / LXI).
//
// R458-C2 — THE CONVERSATION CONTROLS THE DISCOVERY (§4/§5/§6/§7):
//   * Ask vs Act — the composer distinguishes a question over the
//     record (read-only /ask, live today) from a canonical action
//     request (lib/actionContract.ts → the engine's action endpoint).
//     An action the engine cannot yet execute is stated honestly —
//     never a fake success, never a frontend-side state change.
//   * The clarification pause — the engine's ONE material question
//     renders as Toscanini's own message; the composer becomes the
//     answer box (POST /api/run/{id}/answer — C1's live contract).
//   * ONE progress sentence (§7) — the live line is a single
//     meaningful sentence; the four-event tail is gone (the full
//     stream stays in the technical record). A rotation after a
//     transport failure renders as one calm sentence (§26) — the
//     route identity stays in the technical record.

import { useMemo, useState } from "react";
import type { ScienceEvent, SessionDetail, DossierBody, AskResponse } from "@/lib/present-types";
import {
  deriveConversation,
  isTerminal,
  presentMaturity,
  type Msg,
  type NextAction,
  type SurfaceId,
} from "@/lib/present";
// Backend events reach the conversation ONLY through the product event
// map — machine vocabulary stays in the technical record (BS-009).
import {
  pickLiveEvent,
  productEventSentence,
  deriveRotationNote,
  progressContext,
  stageProgressSuffix,
} from "@/lib/productEvents";
import {
  classifyMessage,
  sendAction,
  buildActionParams,
  ACTION_LABEL,
  ACTION_NOT_AVAILABLE_COPY,
  type ActionVerb,
} from "@/lib/actionContract";
import { apiPost } from "@/lib/api";
import { AnswerView } from "./AskBox";

const ATTACK_LABEL: Record<string, string> = {
  NOT_RUN: "not yet tested",
  IN_PROGRESS: "testing",
  SURVIVED: "survived attack",
  CONTESTED: "contested",
  // R470 (audit §2C/P1-3): a killed candidate's chip reads "rejected" —
  // one frame. The old "failed" next to the maturity chip
  // ("INVENTION 01 failed Evidence_supported") read as a
  // self-contradiction; the evidence basis lives in the card body.
  FAILED: "rejected",
  UNRESOLVED: "unresolved",
};

function MetaChip({ epi }: { epi: string }) {
  return <span className="conv-meta">{epi}</span>;
}

function EvidenceCard({
  m,
  onOpen,
}: {
  m: Extract<Msg, { kind: "evidence" }>;
  onOpen: (s: SurfaceId) => void;
}) {
  return (
    <div className="conv-card conv-evidence" data-conv-evidence={m.state}>
      <div className="conv-card-h">Evidence</div>
      <div className="conv-evidence-line">
        {m.retrieved != null ? (
          <>
            <b>{m.retrieved}</b> relevant {m.retrieved === 1 ? "source" : "sources"}
            {m.used != null && (
              <> · <b>{m.used}</b> shaped the design</>
            )}
          </>
        ) : (
          m.body
        )}
      </div>
      {m.domains.length > 0 && (
        <div className="conv-evidence-domains faint">
          {m.domains.slice(0, 3).join(" · ")}
          {m.domains.length > 3 ? ` · +${m.domains.length - 3}` : ""}
        </div>
      )}
      <button type="button" className="conv-open faint" onClick={() => onOpen(m.openSurface)}>
        View evidence →
      </button>
    </div>
  );
}

function Candidates({
  m,
  onQuickAction,
}: {
  m: Extract<Msg, { kind: "candidates" }>;
  onQuickAction?: (verb: Exclude<ActionVerb, "ASK">, label: string) => void;
}) {
  return (
    <div className="conv-candidates" data-conv-candidates>
      {m.items.map((c) => (
        <div
          key={c.label}
          className={`conv-cand ${c.current ? "current" : ""} ${c.killed ? "killed" : ""}`}
          data-conv-candidate
        >
          <div className="conv-cand-head">
            <span className="conv-cand-label">{c.label}</span>
            <span className={`conv-attack atk-${c.attack.toLowerCase()}`}>
              {ATTACK_LABEL[c.attack] ?? c.attack}
            </span>
          </div>
          {c.maturity && (
            // R461 (independent audit P1-10): the maturity boundary is
            // FIRST-LINE — a human sentence that can never read as
            // physical validation when the record carries none. The raw
            // machine label no longer headlines (BS-009).
            <div className="conv-cand-maturity" data-conv-maturity>
              {presentMaturity(c.maturity)}
            </div>
          )}
          {c.intervention && <div className="conv-cand-int">{c.intervention}</div>}
          {c.why && <div className="conv-cand-body"><b>Why it might work:</b> {c.why}</div>}
          {c.whatChanged && (
            <div className="conv-cand-body faint"><b>What changed:</b> {c.whatChanged}</div>
          )}
          {c.risk && <div className="conv-cand-body faint"><b>Risk / kill condition:</b> {c.risk}</div>}
          {!c.killed && c.attack !== "SURVIVED" && onQuickAction && (
            <div className="conv-cand-actions">
              <button
                type="button"
                className="conv-quick faint"
                onClick={() => onQuickAction("ATTACK", `Challenge ${c.label}`)}
              >
                Challenge this candidate
              </button>
              <button
                type="button"
                className="conv-quick faint"
                onClick={() => onQuickAction("CHANGE_MECHANISM", "Try another mechanism")}
              >
                Try another mechanism
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function Outcome({
  m,
  onNext,
  onTechnical,
}: {
  m: Extract<Msg, { kind: "outcome" }>;
  onNext: (n: NextAction) => void;
  onTechnical: () => void;
}) {
  return (
    <div className={`conv-outcome ob-${m.tone}`} data-conv-outcome={m.tone}>
      <div className="conv-outcome-label">{m.label}</div>
      <div className="conv-outcome-body">{m.body}</div>
      {m.next && (
        <div className="conv-next">
          <div className="conv-next-k faint">Next step</div>
          <button
            type="button"
            className={`btn ${m.next.kind === "package" || m.next.kind === "retry" ? "primary" : ""}`}
            data-next-resume={m.next.kind === "retry" || undefined}
            onClick={() => onNext(m.next!)}
          >
            {m.next.label}
          </button>
          <button type="button" className="conv-technical faint" onClick={onTechnical}>
            Show the technical record
          </button>
        </div>
      )}
    </div>
  );
}

export default function Conversation({
  detail,
  dossier,
  events,
  packageAvailable,
  asks,
  onOpenSurface,
  onAsk,
  onTechnical,
  onNextAction,
  onActionRound,
  roundNumber,
  askEnabledNote,
}: {
  detail: SessionDetail;
  dossier: DossierBody | null;
  events: ScienceEvent[];
  packageAvailable: boolean;
  asks: { question: string; response: AskResponse }[];
  onOpenSurface: (s: SurfaceId) => void;
  onAsk: (q: string) => Promise<void>;
  onTechnical: () => void;
  onNextAction: (n: NextAction) => void;
  /** R459: an accepted steering action opens a NEW round of the same
   * investigation — the shell navigates to it. */
  onActionRound?: (newRunId: string) => void;
  /** R466 (reaudit residual friction): WHICH round of the thread this
      is (derived by page.tsx from the recorded parentage) — the
      continuation card names it inside the conversation surface. */
  roundNumber?: number;
  askEnabledNote?: string | null;
}) {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [sendAsAction, setSendAsAction] = useState(false);
  const [actionNote, setActionNote] = useState<string | null>(null);
  const msgs = deriveConversation(detail, dossier, packageAvailable);

  // R464 (external audit P1-3): while the run is live the engine refuses
  // every steering action (its typed mid-flight gate) — yet the composer
  // sits open and the steer chips sit visible, both inviting input that
  // will bounce. The chips now render only when steering is actually
  // accepted (a terminal or paused run); a running run says, in one calm
  // line, when steering opens. Asking about the record stays available
  // throughout.
  const steerOpen = isTerminal(detail.status);

  // R458-C2 (§7) — ONE progress sentence. The live line is the newest
  // ACTIVE event (or the honest pause) in product language; the full
  // event stream stays in the technical record, not under the composer.
  // R464 (audit P0-2): the sentence carries the run's POSITION (how
  // many distinct stages the record shows complete, plus the active
  // one) — derived from recorded events only, never a total.
  const live = pickLiveEvent(events);
  const liveSentence = productEventSentence(live);
  const liveStageSuffix = useMemo(() => stageProgressSuffix(events), [events]);
  // R470 (audit P1-1): the progress context line — the waiting user can
  // state the current phase (the live sentence), the LAST COMPLETED step,
  // and the EVIDENCE COUNT, all derived from the run's own record.
  const recordsFound = detail.run_state?.evidence_state?.records_found;
  const progress = useMemo(
    () => progressContext(events, recordsFound),
    [events, recordsFound]
  );
  const progressLine = useMemo(() => {
    const parts: string[] = [];
    if (progress.lastCompleted) parts.push(progress.lastCompleted);
    if (progress.evidenceCount != null) {
      parts.push(`${progress.evidenceCount} evidence record${progress.evidenceCount === 1 ? "" : "s"} on the record`);
    }
    return parts.join(" · ");
  }, [progress]);
  const liveSummary =
    live && typeof live.summary === "string" ? live.summary : null;
  const paused = [...events].reverse().find((e) => e.status === "FAILED_INFRASTRUCTURE");
  const pausedSentence = productEventSentence(paused);
  const pausedSummary =
    paused && typeof paused.summary === "string" ? paused.summary : null;
  // §26 — the provider-rotation abstraction: work stopped, then
  // continued. One calm sentence; the route stays in the ledger.
  const rotationNote = useMemo(() => deriveRotationNote(events), [events]);
  const done = detail.status === "COMPLETE";

  // §4 — the clarification pause: the composer is the answer box.
  const clarificationPending = detail.status === "AWAITING_CLARIFICATION";

  // §5 — Ask vs Act: the composer routes the message. The phrase table
  // is deterministic presentation logic (lib/actionContract.ts); the
  // user always sees which way their message will go and can flip it.
  const route = useMemo(() => classifyMessage(q), [q]);
  const routeIsAction = route.kind === "action";

  async function submit() {
    const text = q.trim();
    if (!text || busy) return;

    // — the clarification pause: every message answers the question —
    if (clarificationPending) {
      setBusy(true);
      setQ("");
      try {
        await onAsk(text); // renders the answer in the thread honestly
      } finally {
        setBusy(false);
      }
      return;
    }

    // — an action: send the canonical action request to the engine —
    if (sendAsAction && route.kind === "action") {
      setBusy(true);
      setQ("");
      const verb = route.verb;
      try {
        // R459: the invocation rides the owner-capability transport
        // (apiPost) — the same header every run-scoped call carries.
        // R461 (independent audit P0-2): the user's typed words ride
        // the action verbatim (buildActionParams → params.direction,
        // the R458 contract's "the user's own words") — previously the
        // payload was {} and the child round received only the verb.
        const result = await sendAction(
          detail.session_id,
          verb,
          buildActionParams(verb, text),
          apiPost
        );
        if (result.not_available) {
          setActionNote(ACTION_NOT_AVAILABLE_COPY);
        } else if (result.accepted && result.new_run_id) {
          // the engine opened a NEW round of this investigation with the
          // user's direction recorded — navigate to it
          onActionRound?.(result.new_run_id);
        } else if (result.accepted) {
          setActionNote(
            `Done — "${ACTION_LABEL[verb]}" is with the engine. ` +
              `The conversation will show what actually changed, ` +
              `from the record, when it happens.`
          );
        } else if (result.refusal) {
          setActionNote(result.refusal);
        } else {
          setActionNote(
            "The action could not be delivered — an infrastructure " +
              "state, not a verdict about the idea. " +
              (result.detail ?? "")
          );
        }
      } finally {
        setBusy(false);
        setSendAsAction(false);
      }
      return;
    }

    // — a question: the live read-only path over the run's record —
    setBusy(true);
    setQ("");
    try {
      await onAsk(text);
    } finally {
      setBusy(false);
    }
  }

  function quickAction(verb: Exclude<ActionVerb, "ASK">, label: string) {
    setActionNote(null);
    setQ(label);
    setSendAsAction(true);
    void routeAnnounce(verb);
  }

  async function routeAnnounce(_verb: Exclude<ActionVerb, "ASK">) {
    // the composer text is pre-filled; the user presses Enter to send
  }

  const actionToggleLabel = routeIsAction
    ? `Send as: ${ACTION_LABEL[(route as { verb: Exclude<ActionVerb, "ASK"> }).verb]}`
    : "Send as a question";

  // R463 (audit P2-3): the empty state — zero derivable messages, zero
  // attachments, zero results: the conversation never renders as a
  // blank wall, and never pretends progress (one honest sentence).
  const meaningful = msgs.filter((m) => m.kind !== "user");
  const emptyState = meaningful.length === 0 && asks.length === 0;

  // R463 (audit P1-4): the PERSISTENT steer affordance — steering must
  // not depend on discovering a chip inside a candidate card. One calm
  // row, always above the composer, opening the same canonical actions
  // the conversation accepts in plain language.
  const STEER_CHIPS: { verb: Exclude<ActionVerb, "ASK">; label: string }[] = [
    { verb: "CHANGE_MECHANISM", label: "Try another mechanism" },
    { verb: "ATTACK", label: "Challenge this candidate" },
    { verb: "FIND_EVIDENCE", label: "Look for contradictory evidence" },
    { verb: "COMPARE_MECHANISMS", label: "Compare the mechanisms" },
    { verb: "REQUEST_EXPERIMENT", label: "Design the decisive experiment" },
  ];

  return (
    <div className="conv" data-conversation>
      {/* R466 (reaudit residual friction): the thread continuation is
          visible WITHIN the conversation surface — not only as the thin
          page-level fork row above it. A round opened by steering says
          which round it is and keeps the parent one tap away, right
          where the thread begins (the audit's acceptance lives here:
          the new round, the link back, and — as the first user bubble
          below — the instruction that carried, all in one surface).
          The round number comes from the recorded parentage chain
          (lib/rounds.ts); the card renders only what the record
          supports and nothing when there is no parent. */}
      {detail.parent_session_id && (
        <div className="conv-row" data-continued-card data-round={roundNumber ?? 1}>
          <div className="conv-continued">
            <span className="conv-continued-round">
              {roundNumber && roundNumber > 1
                ? `Round ${roundNumber} of this investigation`
                : "A continued round of this investigation"}
            </span>
            <a
              className="conv-continued-link faint"
              href={`/?run=${encodeURIComponent(detail.parent_session_id)}`}
            >
              Continue from the earlier round →
            </a>
          </div>
        </div>
      )}
      {/* R467 (audit P0-5): "a 'what changed because of your direction'
          card in the UI" — rendered ONLY from the worker's typed
          directive_outcome record (computed from the parent and child
          runs' own records). No-change states render honestly as
          no-change; when the record is absent the card is absent. */}
      {detail.directive_outcome?.summary && (
        <div
          className="conv-row"
          data-directive-outcome-card
          data-mechanism-changed={detail.directive_outcome.mechanism_changed ? "true" : "false"}
          data-compliance-verdict={detail.directive_outcome.compliance_verdict ?? undefined}
        >
          <div className="conv-continued">
            <span className="conv-continued-round">What changed because of your direction</span>
            <span>{detail.directive_outcome.summary}</span>
          </div>
        </div>
      )}
      {emptyState && (
        <div className="conv-row" data-conv-empty>
          <div className="conv-note faint">
            Nothing has been retrieved, generated, or concluded yet — the
            investigation is working from your problem statement alone.
            You can steer it below, or just ask about the record.
          </div>
        </div>
      )}
      {msgs.map((m) => {
        switch (m.kind) {
          case "user":
            return (
              <div className="conv-row user" key={m.id} data-conv-user>
                <div className="conv-user-bubble">{m.text}</div>
              </div>
            );
          case "clarification":
            return (
              <div className="conv-row" key={m.id}>
                <div className="conv-clarification" data-conv-clarification>
                  <div className="conv-clarification-q">{m.question}</div>
                  {m.decisionChanged && (
                    <div className="conv-clarification-why faint">
                      Your answer decides: {m.decisionChanged}
                    </div>
                  )}
                </div>
              </div>
            );
          case "note":
            return (
              <div className="conv-row" key={m.id}>
                <div className="conv-note">
                  {m.text}
                  {m.epi && <MetaChip epi={m.epi} />}
                </div>
              </div>
            );
          case "progress":
            // §7 — ONE progress sentence: when the live event line (or
            // the honest pause) is rendering below, the derived "still
            // working" line is redundant — exactly one line, ever.
            if (liveSentence.text || pausedSentence.text) return null;
            return (
              <div className="conv-row" key={m.id}>
                <div className="conv-live" data-conv-live>
                  <span className="cursor" aria-hidden="true" />
                  {m.text}
                </div>
              </div>
            );
          case "evidence":
            return (
              <div className="conv-row" key={m.id}>
                <EvidenceCard m={m} onOpen={onOpenSurface} />
              </div>
            );
          case "candidates":
            return (
              <div className="conv-row" key={m.id}>
                <Candidates m={m} onQuickAction={quickAction} />
              </div>
            );
          case "attack":
            return (
              <div className="conv-row" key={m.id}>
                <div className="conv-attack-line" data-conv-attack={m.state}>
                  <div className="conv-note">{m.body}</div>
                  {m.challenge && (
                    <div className="conv-challenge faint">
                      Strongest objection: {m.challenge}
                    </div>
                  )}
                </div>
              </div>
            );
          case "artifact":
            return (
              <div className="conv-row" key={m.id}>
                <button
                  type="button"
                  className="conv-card conv-artifact"
                  data-conv-artifact={m.surface}
                  onClick={() => onOpenSurface(m.surface)}
                >
                  <div className="conv-card-h">{m.title}</div>
                  {m.body && <div className="conv-artifact-body">{m.body}</div>}
                  <div className="conv-open faint">{m.cta} →</div>
                </button>
              </div>
            );
          case "outcome":
            return (
              <div className="conv-row" key={m.id}>
                <Outcome m={m} onNext={onNextAction} onTechnical={onTechnical} />
              </div>
            );
          case "ask":
            return null;
        }
      })}

      {/* the follow-up thread — the conversation continues */}
      {asks.map((a, i) => (
        <div className="conv-row" key={`ask-${i}`}>
          <div className="conv-row user">
            <div className="conv-user-bubble">{a.question}</div>
          </div>
          <div className="conv-note conv-answer" data-conv-answer={a.response.status}>
            <AnswerView a={a.response} />
          </div>
        </div>
      ))}

      {/* the action delivery note — honest, one line, never a fake
          success (§4/§27: the engine's record is the only authority on
          what actually changed). R464 (audit P1-7): the note carries its
          own dismissal — a refusal or delivery note no longer squats
          over the composer until the next navigation. */}
      {actionNote && (
        <div className="conv-row" data-conv-action-note>
          <div className="conv-note conv-action-note">
            {actionNote}
            <button
              type="button"
              className="conv-action-dismiss"
              aria-label="dismiss this note"
              onClick={() => setActionNote(null)}
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* live investigation — ONE sentence from the event record, in
          product language (§7/§16/§22); the backend summary rides the
          title attribute and lives in full in the technical record */}
      {!done && !clarificationPending && (
        <div className="conv-row" data-conv-live-block aria-live="polite">
          {rotationNote && (
            <div className="conv-note faint" data-conv-rotation>
              {rotationNote}
            </div>
          )}
          {paused && !liveSentence.loading && pausedSentence.text && (
            <div className="conv-live paused" data-conv-paused title={pausedSummary ?? undefined}>
              {pausedSentence.text}
            </div>
          )}
          {liveSentence.loading && liveSentence.text && (
            <div className="conv-live" data-conv-active title={liveSummary ?? undefined}>
              <span className="cursor" aria-hidden="true" />
              {liveSentence.text}
              <span className="faint">{liveStageSuffix}</span>
            </div>
          )}
          {liveSentence.loading && progressLine && (
            <div className="conv-note faint" data-conv-progress>
              {progressLine}
            </div>
          )}
        </div>
      )}

      {/* R463 (audit P1-4): the persistent steer affordance — visible
          whenever the conversation accepts steering (the composer's
          Ask/Act routing still decides how each message is sent).
          R464 (audit P1-3): a RUNNING run shows the calm note instead —
          the engine's own gate refuses mid-flight steering, so the
          chips would invite a guaranteed refusal. */}
      {!clarificationPending &&
        (steerOpen ? (
          <div className="conv-steer" data-conv-steer>
            <span className="conv-steer-k faint">Steer this discovery:</span>
            {STEER_CHIPS.map((c) => (
              <button
                key={c.verb}
                type="button"
                className="conv-quick faint"
                onClick={() => quickAction(c.verb, c.label)}
              >
                {c.label}
              </button>
            ))}
          </div>
        ) : (
          !done && (
            <div className="conv-steer-note" data-conv-steer-locked>
              Steering opens when this investigation completes — you can
              still ask about its record below.
            </div>
          )
        ))}

      {/* the composer — conversation-first (§4: it can ask, act, and
          answer the engine's question) */}
      <div className="conv-composer" data-conv-composer>
        <input
          className="conv-input"
          value={q}
          placeholder={
            clarificationPending
              ? "Type your answer — the investigation resumes the moment you send it…"
              : done || detail.status === "RUN_BLOCKED_TRANSPORT"
                ? "Ask about this discovery — answered from its own record…"
                : askEnabledNote ?? "Ask about this, or tell me what to do next…"
          }
          onChange={(e) => {
            setQ(e.target.value);
            if (!routeIsAction) setSendAsAction(false);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void submit();
            }
          }}
          aria-label={
            clarificationPending ? "Answer the investigation's question" : "Message Toscanini"
          }
        />
        <button
          type="button"
          className={`btn small ${sendAsAction && routeIsAction ? "primary" : ""}`}
          onClick={() => void submit()}
          disabled={busy || !q.trim()}
        >
          {busy ? "…" : clarificationPending ? "Answer" : sendAsAction && routeIsAction ? "Do it" : "Ask"}
        </button>
      </div>
      {!clarificationPending && routeIsAction && (
        <div className="conv-routenote faint" data-conv-route-note>
          <button
            type="button"
            className="conv-route-toggle"
            onClick={() => setSendAsAction(!sendAsAction)}
          >
            {sendAsAction ? actionToggleLabel : actionToggleLabel + " (send as a question instead)"}
          </button>
        </div>
      )}
      <div className="conv-composer-note faint">
        answers come from this investigation&apos;s own records — unknowns stay
        unknown, and nothing is presented as physically validated unless the
        record carries a physical observation
      </div>
    </div>
  );
}
