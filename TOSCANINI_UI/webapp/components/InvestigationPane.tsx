"use client";

// R430.1 sections 2, 7-13: the INVESTIGATION pane — the left side of
// the workspace. One conversation-shaped surface:
//   user problem → structured scientific events → terminal narrative.
// The event feed comes from the backend's persisted event history
// (GET /api/run/{id}/events) plus live SSE 'science' events — every
// displayed state corresponds to an actual backend event; no fake
// percentages, no fabricated progress (section 11).

import { useMemo } from "react";
import type {
  DossierBody,
  GauntletCard,
  ScienceEvent,
  SessionDetail,
} from "@/lib/types";
import RunNarrative, { isTerminal } from "./RunNarrative";
import {
  EngineeringArgument,
  NoveltyAndCemetery,
} from "./EngineeringArgument";
import InventionEssay from "./InventionEssay";
import AskBox from "./AskBox";
import {
  EpistemicBadge,
  Gauntlet,
  InvestigationProgress,
  ScienceEventStream,
} from "./ScienceEvents";

function lastCompletedLabel(events: ScienceEvent[]): string | null {
  const done = [...events]
    .reverse()
    .find(
      (e) =>
        e.status === "COMPLETED" &&
        !e.kind.startsWith("investigation.")
    );
  return done?.summary ?? null;
}

function activeLabel(events: ScienceEvent[]): string | null {
  const active = [...events]
    .reverse()
    .find(
      (e) => e.status === "ACTIVE" || e.status === "FAILED_INFRASTRUCTURE"
    );
  return active?.summary ?? null;
}

export default function InvestigationPane({
  detail,
  events,
  gauntlet,
  dossier,
  packageAvailable,
  onRetry,
}: {
  detail: SessionDetail;
  events: ScienceEvent[];
  gauntlet: GauntletCard[];
  dossier: DossierBody | null;
  packageAvailable: boolean;
  onRetry?: (id: string) => void;
}) {
  const done = isTerminal(detail.status);
  const usv = detail.user_state_view;
  const blocked =
    detail.status === "RUN_BLOCKED_TRANSPORT" ||
    detail.status === "INTERRUPTED" ||
    detail.status.startsWith("ERROR");

  // the live science events: newest LAST, only while the run is live
  // or the most recent N after completion (the full history is
  // expandable; the gauntlet is the compact summary)
  const liveEvents = useMemo(() => {
    if (done) return events.slice(-8);
    return events;
  }, [events, done]);

  return (
    <div className="investigation">
      {/* the user's message: the problem itself */}
      <div className="msg user">
        <div className="msg-role">You</div>
        <div className="msg-body">{detail.user_text}</div>
      </div>

      {/* Toscanini's reply: the structured scientific process */}
      <div className="msg tosca">
        <div className="msg-role">
          Toscanini
          {usv && done && <span className="pill COMPLETE">{usv.label}</span>}
          {events.length > 0 && (
            <span className="evt-count faint">
              {events.length} recorded event
              {events.length === 1 ? "" : "s"}
            </span>
          )}
        </div>
        <div className="msg-body">
          {/* section 13: the return banner while the server works */}
          {!done && (
            <InvestigationProgress
              lastCompletedLabel={lastCompletedLabel(events)}
              activeLabel={activeLabel(events)}
            />
          )}

          {/* section 9: the collapsible gauntlet — compact cards */}
          {gauntlet.length > 0 && <Gauntlet cards={gauntlet} />}

          {/* section 7/11: the structured event feed */}
          {liveEvents.length > 0 && (
            <ScienceEventStream events={liveEvents} dense />
          )}

          {/* the narrative (phases + generations) — from the same
              backend state, human-shaped */}
          <RunNarrative detail={detail} packageAvailable={packageAvailable} />

          {done && usv && (
            <div className="narrative-summary">
              {usv.decision}
              {usv.meaning && (
                <div className="faint" style={{ marginTop: 4 }}>
                  {usv.meaning}
                </div>
              )}
            </div>
          )}

          {blocked && onRetry && (
            <div className="retry-row">
              <button
                className="btn"
                onClick={() => onRetry(detail.session_id)}
                type="button"
              >
                Resume investigation
              </button>
              <span className="faint">
                the problem is saved; this is an infrastructure state,
                never a scientific verdict
              </span>
            </div>
          )}

          {done && detail.status === "COMPLETE" && (
            <>
              <div className="reasoning">
                <h3>The engineering argument</h3>
                <div className="sub">
                  derived from the run&apos;s persisted artifacts —
                  evidence, mechanisms, decisions, and what is still
                  unknown
                </div>
                <EngineeringArgument
                  detail={detail}
                  packageAvailable={packageAvailable}
                />
              </div>
              <InventionEssay sessionId={detail.session_id} />
              <NoveltyAndCemetery detail={detail} />
            </>
          )}
        </div>
      </div>

      {done && (
        <AskBox
          mode="run"
          subject={detail.session_id}
          enabled={detail.status === "COMPLETE"}
        />
      )}

      {/* epistemic footer: the classes currently in play */}
      {(() => {
        const classes = [...new Set(events.map((e) => e.epistemic_class))];
        if (classes.length === 0) return null;
        return (
          <div className="epi-footer faint">
            epistemic classes in this investigation:{" "}
            {classes.map((c) => (
              <EpistemicBadge key={c} cls={c} />
            ))}
          </div>
        );
      })()}
      {dossier === null && null}
    </div>
  );
}
