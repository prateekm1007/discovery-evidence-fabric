"use client";

// R453-C2 — THE SIDEBAR: the information architecture (brief §5).
//
//   New Discovery · Discoveries · Technology Packages
//
// R458-C2 (§10/§11): Projects is GONE — the product never advertises
// unfinished capability as navigation (the section was an honest empty
// state, but honesty does not make an unusable surface navigable).
// Settings stays account-level, outside the discovery navigation.
//
// §11 — history items lead with WHAT you were working on: human title,
// small date, a subtle state dot (color-independent: the state also
// rides an aria-label). No large status pills — the state-machine
// vocabulary is not the headline.
//
// R459-reaudit (P1-2): the flat 14-item list gains CLIENT-SIDE search
// (a substring filter over the already-loaded titles — presentational,
// no new backend contract) and honest time grouping (Today / This
// week / Earlier, derived from each item's own created_at — no
// invented folder entity). Search runs across EVERY loaded discovery;
// the idle view keeps the calm 14-item cap.

import { useMemo, useState } from "react";
import type { HealthSummary, SessionRow, ShowcaseRow, UserStateView } from "@/lib/types";

// the three honest recency buckets, derived from the item's own date
function timeBucket(iso: string | undefined): "today" | "week" | "earlier" {
  if (!iso) return "earlier";
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return "earlier";
  const now = Date.now();
  const dayStart = new Date(); dayStart.setHours(0, 0, 0, 0);
  if (t >= dayStart.getTime()) return "today";
  if (now - t <= 7 * 24 * 60 * 60 * 1000) return "week";
  return "earlier";
}

const BUCKET_LABELS: Record<string, string> = {
  today: "Today",
  week: "This week",
  earlier: "Earlier",
};

// the subtle state dot — a small visual cue, never the headline.
// Classes are the dot's color family only; the meaning is carried by
// the aria-label text (§20: color-independent status).
function stateDot(usv: UserStateView | undefined): { cls: string; label: string } {
  if (!usv) return { cls: "running", label: "In progress" };
  switch (usv.user_state) {
    case "COMPLETED_PACKAGE":
    case "COMPLETED_CANDIDATE":
    case "COMPLETED_EVOLVED":
      return { cls: "complete", label: "Complete" };
    case "COMPLETED_UNDER_DEVELOPMENT":
    case "COMPLETED_GENERATION_FAILED":
      return { cls: "development", label: "In development" };
    case "COMPLETED_REJECTED":
    case "COMPLETED_FALSE_PREMISE":
      return { cls: "rejected", label: "Rejected" };
    case "COMPLETED_UNKNOWN":
      return { cls: "unknown", label: "Outcome unknown" };
    // R459 (audit P0-1): the one-question pause is ACTIVE work — amber,
      // pulsing, and named, never a gray "outcome unknown"
    case "AWAITING_CLARIFICATION":
      return { cls: "attention", label: "Action needed — answer below" };
    case "INTERRUPTED":
    case "FAILED_TRANSPORT":
    case "FAILED_ENGINE":
    case "BLOCKED_TRANSPORT":
      return { cls: "paused", label: "Paused by infrastructure" };
    default:
      return { cls: "running", label: "In progress" };
  }
}

export default function Sidebar({
  sessions,
  showcase,
  activeRun,
  activeInvention,
  onSelectRun,
  onSelectInvention,
  onNewProblem,
  health,
}: {
  sessions: SessionRow[];
  showcase: ShowcaseRow[];
  activeRun: string | null;
  activeInvention: string | null;
  onSelectRun: (id: string) => void;
  onSelectInvention: (slot: string) => void;
  onNewProblem: () => void;
  health: HealthSummary | null;
}) {
  const focus = showcase.filter((s) => s.demo_focus);
  const others = showcase.filter((s) => !s.demo_focus);

  // client-side search over the already-loaded titles + honest time
  // grouping (both derived from data already in the browser)
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();
  const searching = q.length > 0;

  const visible = useMemo(
    () =>
      searching
        ? sessions.filter((s) => (s.title ?? "").toLowerCase().includes(q))
        : sessions.slice(0, 14),
    [searching, q, sessions]
  );

  const grouped = useMemo(() => {
    const g: Record<"today" | "week" | "earlier", SessionRow[]> = {
      today: [], week: [], earlier: [],
    };
    for (const s of visible) g[timeBucket(s.created_at)].push(s);
    return g;
  }, [visible]);

  const renderItem = (s: SessionRow) => {
    const dot = stateDot(s.user_state_view);
    return (
      <button
        key={s.session_id}
        className={`rail-item ${activeRun === s.session_id ? "active" : ""}`}
        onClick={() => onSelectRun(s.session_id)}
        type="button"
        title={s.title}
      >
        <span className={`rail-dot rail-dot-${dot.cls}`} role="img" aria-label={dot.label} />
        <span className="rail-title">{s.title}</span>
        {/* R463 (audit P1-2): the parent row marks a thread that forked
            a steering round — the thread is visible from both ends */}
        {s.has_fork && (
          <span className="rail-fork faint" data-rail-fork title="This discovery has a continued round">
            continued
          </span>
        )}
        <span className="rail-when">{s.created_at?.slice(0, 10)}</span>
      </button>
    );
  };

  return (
    <nav className="rail" aria-label="navigation">
      <button className="rail-new" onClick={onNewProblem} type="button">
        + New Discovery
      </button>

      <div className="rail-section">
        <div className="rail-h">Discoveries</div>
        {sessions.length === 0 && (
          <div className="rail-empty">
            You haven&apos;t started a discovery yet — describe a problem,
            observation, or technology you&apos;d like to investigate.
          </div>
        )}
        {sessions.length > 0 && (
          <input
            className="rail-search"
            type="search"
            placeholder="Search discoveries"
            aria-label="Search discoveries"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        )}
        {searching && visible.length === 0 && (
          <div className="rail-empty">
            No discovery matches &ldquo;{query.trim()}&rdquo;.
          </div>
        )}
        {searching && visible.length > 0 && (
          <>
            <div className="rail-group-h" aria-hidden="true">
              {visible.length} match{visible.length === 1 ? "" : "es"}
            </div>
            {visible.map(renderItem)}
          </>
        )}
        {!searching && (["today", "week", "earlier"] as const).map((b) => {
          const items = grouped[b];
          if (items.length === 0) return null;
          return (
            <div key={b}>
              {b !== "today" || grouped.week.length > 0 || grouped.earlier.length > 0 ? (
                <div className="rail-group-h" aria-hidden="true">
                  {BUCKET_LABELS[b]}
                </div>
              ) : null}
              {items.map(renderItem)}
            </div>
          );
        })}
      </div>

      <div className="rail-section">
        <div className="rail-h">Technology packages</div>
        {showcase.length === 0 && (
          <div className="rail-empty">
            Released packages appear here as the portfolio produces them.
          </div>
        )}
        {focus.map((s) => (
          <button
            key={s.slot}
            className={`rail-item inv ${activeInvention === s.slot ? "active" : ""}`}
            onClick={() => onSelectInvention(s.slot)}
            type="button"
            title={s.blurb}
          >
            <span className="rail-title">{s.title}</span>
            <span className="rail-when">{s.domain}</span>
          </button>
        ))}
        {others.length > 0 && (
          <details className="rail-more">
            <summary>all {showcase.length} packages</summary>
            {others.map((s) => (
              <button
                key={s.slot}
                className={`rail-item inv ${activeInvention === s.slot ? "active" : ""}`}
                onClick={() => onSelectInvention(s.slot)}
                type="button"
                title={s.blurb}
              >
                <span className="rail-title">{s.title}</span>
                <span className="rail-when">{s.domain}</span>
              </button>
            ))}
          </details>
        )}
      </div>

      <div className="rail-section rail-settings" data-sidebar-settings>
        <details className="rail-projects">
          <summary className="rail-h">Settings</summary>
          <div className="rail-empty">
            {health?.engine_commit ? (
              <>
                Engine build <span className="mono">{health.engine_commit.slice(0, 7)}</span>{" "}
                — the deployed identity is also shown on the health endpoint,
                never asserted by the UI.
              </>
            ) : (
              "Engine identity appears when the health endpoint responds."
            )}
            <br />
            Technical detail (provenance, gate verdicts, machine states)
            lives inside each discovery under “Show the technical record” —
            present, never in the way.
          </div>
        </details>
      </div>
    </nav>
  );
}
