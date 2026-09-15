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
import { groupRounds, type RoundRow } from "@/lib/rounds";

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
  // R464 (audit P1-8): the idle cap is now STATED — a "show all"
  // affordance replaces the silent 14-row ceiling
  const [showAll, setShowAll] = useState(false);
  const q = query.trim().toLowerCase();
  const searching = q.length > 0;

  const visible = useMemo(
    () =>
      searching
        ? sessions.filter((s) => (s.title ?? "").toLowerCase().includes(q))
        : showAll
          ? sessions
          : sessions.slice(0, 14),
    [searching, q, sessions, showAll]
  );

  // R464 (audit P1-2): rounds group under the investigation they
  // continue — the parent thread stays one visual unit, children
  // indented with their round number (pure projection of the
  // parent_session_id the engine already records per row).
  const roundRows = useMemo(() => groupRounds(visible), [visible]);

  const grouped = useMemo(() => {
    const g: Record<"today" | "week" | "earlier", RoundRow<SessionRow>[]> = {
      today: [], week: [], earlier: [],
    };
    for (const r of roundRows) g[timeBucket(r.row.created_at)].push(r);
    return g;
  }, [roundRows]);

  // R466 (reaudit): the history is a LIST — an <ol> of <li> items, not
  // loose divs, so assistive tech announces "list, N items" and the
  // chronological order is semantic, not visual. The styling reset
  // lives in CSS (.rail-list); the item markup is unchanged.
  const renderItem = (r: RoundRow<SessionRow>) => {
    const s = r.row;
    const dot = stateDot(s.user_state_view);
    return (
      <li key={s.session_id} className={r.grouped ? "child" : undefined}>
        <button
          className={`rail-item ${r.grouped ? "child" : ""} ${activeRun === s.session_id ? "active" : ""}`}
          onClick={() => onSelectRun(s.session_id)}
          type="button"
          title={s.title}
        >
          <span className={`rail-dot rail-dot-${dot.cls}`} role="img" aria-label={dot.label} />
          <span className="rail-title">{s.title}</span>
          {/* R464 (audit P1-2): a continued round names its position in
              the thread — the history reads as one investigation, not
              as unrelated entries */}
          {r.round > 1 && (
            <span className="rail-round" data-rail-round>Round {r.round}</span>
          )}
          {/* R463 (audit P1-2): the parent row marks a thread that forked
              a steering round — the thread is visible from both ends */}
          {s.has_fork && (
            <span className="rail-fork faint" data-rail-fork title="This discovery has a continued round">
              continued
            </span>
          )}
          <span className="rail-when">{s.created_at?.slice(0, 10)}</span>
        </button>
      </li>
    );
  };

  // R466: the released packages are a list too (same semantics, same
  // reset) — the rail's two sections stay structurally consistent.
  const renderPackage = (s: ShowcaseRow) => (
    <li key={s.slot}>
      <button
        className={`rail-item inv ${activeInvention === s.slot ? "active" : ""}`}
        onClick={() => onSelectInvention(s.slot)}
        type="button"
        title={s.blurb}
      >
        <span className="rail-title">{s.title}</span>
        <span className="rail-when">{s.domain}</span>
      </button>
    </li>
  );

  return (
    <nav className="rail" aria-label="navigation">
      <button className="rail-new" onClick={onNewProblem} type="button">
        + New Discovery
      </button>

      <div className="rail-section">
        {/* R462 port (audit P1.4): semantic heading — screen-reader users
            can jump between rail sections; class kept, zero visual change. */}
        <h2 className="rail-h">Discoveries</h2>
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
            <ol className="rail-list">{roundRows.map(renderItem)}</ol>
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
              <ol className="rail-list">{items.map(renderItem)}</ol>
            </div>
          );
        })}
        {/* R464 (audit P1-8): the capped idle view says how much history
            exists and offers the rest in one tap — search already covers
            everything; this is the honest count, not a silent ceiling */}
        {!searching && !showAll && sessions.length > 14 && (
          <button
            type="button"
            className="rail-count"
            data-rail-see-all
            onClick={() => setShowAll(true)}
          >
            Show all {sessions.length} discoveries
          </button>
        )}
        {!searching && showAll && sessions.length > 14 && (
          <button
            type="button"
            className="rail-count"
            data-rail-collapse
            onClick={() => setShowAll(false)}
          >
            Show recent only
          </button>
        )}
      </div>

      <div className="rail-section">
        <h2 className="rail-h">Technology packages</h2>
        {/* R470 (external re-audit P1-7): exemplar distinction — the
            first-visit rail mixes pre-baked portfolio items with the
            visitor's empty Discoveries list, and nothing said these are
            examples of finished discoveries, not the visitor's own work.
            One line, in the rail's own voice, directly under the header;
            the packages remain one tap away as before. */}
        {showcase.length > 0 && (
          <div className="rail-empty" data-rail-exemplar-note>
            Portfolio exemplars — finished discoveries published by the
            machine&apos;s own research program, not yours. Yours live
            under Discoveries above.
          </div>
        )}
        {showcase.length === 0 && (
          <div className="rail-empty">
            {/* R464 (audit P2-6): the empty state explains what a
                package IS before the visitor has one — the section
                name alone was insider vocabulary */}
            When a discovery survives its challenges, it can be released
            as a technology package — the evidence, engineering, and
            decisive experiment, ready to evaluate. Released packages
            appear here as the portfolio produces them.
          </div>
        )}
        <ol className="rail-list">{focus.map(renderPackage)}</ol>
        {others.length > 0 && (
          <details className="rail-more">
            <summary>all {showcase.length} example packages</summary>
            <ol className="rail-list">{others.map(renderPackage)}</ol>
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
