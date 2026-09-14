"use client";

// R453-C2 — THE CONVERSATION: one discovery told as one conversation.
//
// The pipeline is visible as a STORY, not as machinery (the directive's
// closing correction). Every message here is derived from canonical
// state through lib/present.ts — the component renders; it never
// re-derives epistemic state, never upgrades a class, never converts
// unknown into certainty (Art. X / XXV / XXVIII / LXI).
//
// Message → surface mapping:
//   user        the problem, right-aligned
//   note        plain conversational text (no card — brief §13)
//   progress    the live line while the run records steps
//   evidence    ONE inline card (the counts are meaningful structure)
//   candidates  the inventions as competing hypotheses (brief §16)
//   attack      "now I'm trying to prove this wrong" (brief §17)
//   artifact    substantial output → opens the right-side workspace
//   outcome     the terminal state + THE single next-best action
//   ask         the user's follow-up + the honest answer/refusal

import { useState } from "react";
import type { ScienceEvent, SessionDetail, DossierBody, AskResponse } from "@/lib/present-types";
import {
  deriveConversation,
  type Msg,
  type NextAction,
  type SurfaceId,
} from "@/lib/present";
import { AnswerView } from "./AskBox";
import { EpistemicBadge } from "./ScienceEvents";

const ATTACK_LABEL: Record<string, string> = {
  NOT_RUN: "not yet tested",
  IN_PROGRESS: "testing",
  SURVIVED: "survived attack",
  CONTESTED: "contested",
  FAILED: "failed",
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
}: {
  m: Extract<Msg, { kind: "candidates" }>;
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
            {c.maturity && <span className="conv-cand-mat faint">{c.maturity}</span>}
            <span className={`conv-attack atk-${c.attack.toLowerCase()}`}>
              {ATTACK_LABEL[c.attack] ?? c.attack}
            </span>
          </div>
          {c.intervention && <div className="conv-cand-int">{c.intervention}</div>}
          {c.why && <div className="conv-cand-body"><b>Why it might work:</b> {c.why}</div>}
          {c.whatChanged && (
            <div className="conv-cand-body faint"><b>What changed:</b> {c.whatChanged}</div>
          )}
          {c.risk && <div className="conv-cand-body faint"><b>Risk / kill condition:</b> {c.risk}</div>}
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
  askEnabledNote?: string | null;
}) {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const msgs = deriveConversation(detail, dossier, packageAvailable);

  // the live line, from the run's own event record — never a guess
  const active = [...events].reverse().find((e) => e.status === "ACTIVE");
  const paused = [...events].reverse().find((e) => e.status === "FAILED_INFRASTRUCTURE");
  const done = detail.status === "COMPLETE";

  async function submit() {
    const question = q.trim();
    if (!question || busy) return;
    setBusy(true);
    setQ("");
    try {
      await onAsk(question);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="conv" data-conversation>
      {msgs.map((m) => {
        switch (m.kind) {
          case "user":
            return (
              <div className="conv-row user" key={m.id} data-conv-user>
                <div className="conv-user-bubble">{m.text}</div>
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
                <Candidates m={m} />
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

      {/* live investigation line — from the event record only */}
      {!done && (
        <div className="conv-row" data-conv-live-block>
          {paused && !active && (
            <div className="conv-live paused" data-conv-paused>
              Paused — infrastructure: {paused.summary}
            </div>
          )}
          {active && (
            <div className="conv-live" data-conv-active>
              <span className="cursor" aria-hidden="true" />
              {active.summary}
              <EpistemicBadge cls={active.epistemic_class} />
            </div>
          )}
          {events.length > 0 && (
            <div className="conv-events faint" data-conv-events>
              {events.slice(-4).map((e) => (
                <div className="conv-event" key={e.event_id}>
                  <span className={`scdot sc-${(e.status || "unknown").toLowerCase()}`} aria-hidden="true" />
                  {e.summary}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* the composer — conversation-first (brief §7) */}
      <div className="conv-composer" data-conv-composer>
        <input
          className="conv-input"
          value={q}
          placeholder={
            done || detail.status === "RUN_BLOCKED_TRANSPORT"
              ? "Ask about this discovery — answered from its own record…"
              : askEnabledNote ?? "Ask while I work — I'll answer honestly if the record can't yet…"
          }
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void submit();
            }
          }}
          aria-label="Ask Toscanini"
        />
        <button
          type="button"
          className="btn small"
          onClick={() => void submit()}
          disabled={busy || !q.trim()}
        >
          {busy ? "…" : "Ask"}
        </button>
      </div>
      <div className="conv-composer-note faint">
        answers come from this investigation&apos;s own records — unknowns stay
        unknown, and nothing is presented as physically validated unless the
        record carries a physical observation
      </div>
    </div>
  );
}
