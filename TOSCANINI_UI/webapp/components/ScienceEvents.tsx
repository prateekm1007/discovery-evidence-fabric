"use client";

// R430.1 sections 7-9: the structured scientific event stream — the
// investigation conversation. Raw LLM tokens never appear; every card
// is a backend event derived from a persisted artifact. Epistemic
// classes render as badges and are NEVER upgraded client-side
// (section 8 / Art. XXVIII).

import { useState } from "react";
import type { GauntletCard, ScienceEvent } from "@/lib/types";

const EPI_BADGE: Record<string, string> = {
  RETRIEVED: "ep-retrieved",
  INFERRED: "ep-inferred",
  HYPOTHESIZED: "ep-hypothesized",
  COMPUTED: "ep-computed",
  SIMULATED: "ep-simulated",
  ENGINEERING_DEFINED: "ep-engineering",
  PHYSICALLY_OBSERVED: "ep-physical",
  UNKNOWN: "ep-unknown",
};

const EPI_LABEL: Record<string, string> = {
  RETRIEVED: "retrieved",
  INFERRED: "inferred",
  HYPOTHESIZED: "hypothesized",
  COMPUTED: "computed",
  SIMULATED: "simulated",
  ENGINEERING_DEFINED: "engineering-defined",
  PHYSICALLY_OBSERVED: "physically-observed",
  UNKNOWN: "unknown",
};

const STATUS_CLASS: Record<string, string> = {
  QUEUED: "ev-queued",
  ACTIVE: "ev-active",
  COMPLETED: "ev-completed",
  BLOCKED: "ev-blocked",
  FAILED_INFRASTRUCTURE: "ev-infra",
  FAILED_SCIENTIFIC: "ev-sci",
  UNKNOWN: "ev-unknown",
};

export function EpistemicBadge({ cls }: { cls: string }) {
  return (
    <span
      className={`ep-badge ${EPI_BADGE[cls] ?? "ep-unknown"}`}
      title={`epistemic class: ${cls} — preserved from the backend record; never upgraded`}
    >
      {EPI_LABEL[cls] ?? cls.toLowerCase()}
    </span>
  );
}

// Section 9: the collapsible gauntlet — compact scientific cards,
// collapsed by default, expandable to the events that produced them.
export function Gauntlet({ cards }: { cards: GauntletCard[] }) {
  const [open, setOpen] = useState<string | null>(null);
  if (cards.length === 0) return null;
  return (
    <div className="gauntlet" aria-label="scientific progress">
      {cards.map((c) => (
        <div
          key={c.stage}
          className={`gcard g-${(c.state || "PENDING").toLowerCase()}`}
          onClick={() => setOpen(open === c.stage ? null : c.stage)}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ")
              setOpen(open === c.stage ? null : c.stage);
          }}
        >
          <div className="gcard-head">
            <span className="gmark" aria-hidden="true">{c.mark}</span>
            <span className="glabel">{c.label}</span>
            <span className={`gstate gs-${(c.state || "PENDING").toLowerCase()}`}>
              {c.state === "FAILED_INFRASTRUCTURE"
                ? "infrastructure"
                : c.state === "FAILED_SCIENTIFIC"
                  ? "scientific failure"
                  : c.state === "COMPLETED"
                    ? ""
                    : (c.state || "").toLowerCase()}
            </span>
          </div>
          {c.summary && <div className="gsummary">{c.summary}</div>}
          {open === c.stage && (
            <div className="gdetail faint">
              {c.events.length} recorded event{c.events.length === 1 ? "" : "s"} behind this
              card — expandable evidence lives in the dossier tabs; no
              internal reasoning is exposed
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// Section 7/11: the live structured event feed. During a run, events
// append as the backend records them (SSE science events + poll
// replay); after completion this is the full persisted history.
export function ScienceEventStream({
  events,
  dense,
}: {
  events: ScienceEvent[];
  dense?: boolean;
}) {
  const [expanded, setExpanded] = useState<string | null>(null);
  if (events.length === 0) return null;
  return (
    <div className="science-events" aria-live="polite">
      {events.map((e) => {
        const isOpen = expanded === e.event_id;
        return (
          <div
            key={e.event_id}
            className={`scevt ${STATUS_CLASS[e.status] ?? "ev-unknown"} ${
              dense ? "dense" : ""
            }`}
            onClick={() => setExpanded(isOpen ? null : e.event_id)}
            role="button"
            tabIndex={0}
            onKeyDown={(ev) => {
              if (ev.key === "Enter" || ev.key === " ")
                setExpanded(isOpen ? null : e.event_id);
            }}
          >
            <div className="scevt-head">
              <span
                className={`scdot sc-${(e.status || "UNKNOWN").toLowerCase()}`}
                aria-hidden="true"
              />
              <span className="scsummary">{e.summary}</span>
              <EpistemicBadge cls={e.epistemic_class} />
            </div>
            {isOpen && (
              <div className="scevt-detail faint">
                <div>
                  <b>stage</b> {e.stage} · <b>status</b> {e.status}
                </div>
                <div>
                  <b>recorded basis</b> {e.basis_ref}
                </div>
                {e.timestamp && (
                  <div>
                    <b>recorded at</b> {e.timestamp}
                  </div>
                )}
                <div className="scnote">
                  machine-readable provenance (event {e.event_id}); no
                  internal chain-of-thought is exposed
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// Section 12/13: the return-after-leaving banner — what the server
// says is running, never a client-side guess.
export function InvestigationProgress({
  lastCompletedLabel,
  activeLabel,
  pausedLabel,
}: {
  lastCompletedLabel?: string | null;
  activeLabel?: string | null;
  pausedLabel?: string | null;
}) {
  return (
    <div className="inv-progress">
      <div className="inv-progress-h">
        INVESTIGATION IN PROGRESS
        <span className="cursor" aria-hidden="true" />
      </div>
      {lastCompletedLabel && (
        <div className="faint">Last completed: {lastCompletedLabel}</div>
      )}
      {activeLabel && <div>Currently: {activeLabel}</div>}
      {/* R436 (audit §5B): an infrastructure pause is its own state —
          never presented as active investigation work */}
      {pausedLabel && !activeLabel && (
        <div className="inv-paused" data-inv-paused>
          Paused — infrastructure: {pausedLabel}
        </div>
      )}
      <div className="faint" style={{ fontSize: 12 }}>
        the investigation is persisted on the server; you can leave and
        return to it
      </div>
    </div>
  );
}
