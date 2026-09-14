"use client";

// R453-C2 — THE SIDEBAR: the new information architecture (brief §5).
//
//   New Discovery · Discoveries · Technology Packages · Projects · Settings
//
// Not 15 navigation destinations, and never the internal pipeline as
// navigation. Discoveries are states of ONE discovery (the conversation
// renders them); the rail only decides WHERE you are. Projects is an
// honest empty state until the backend grouping contract exists — no
// fake data (brief §43). Settings carries the engine identity honestly.

import type { HealthSummary, SessionRow, ShowcaseRow, UserStateView } from "@/lib/types";

function stateClass(usv: UserStateView | undefined): string {
  if (!usv) return "RUNNING";
  switch (usv.user_state) {
    case "COMPLETED_PACKAGE":
    case "COMPLETED_CANDIDATE":
    case "COMPLETED_EVOLVED":
      return "COMPLETE";
    case "COMPLETED_REJECTED":
    case "COMPLETED_FALSE_PREMISE":
      return "REJECTED";
    case "COMPLETED_UNKNOWN":
      return "ERROR";
    case "INTERRUPTED":
    case "FAILED_TRANSPORT":
    case "FAILED_ENGINE":
    case "BLOCKED_TRANSPORT":
      return "ERROR";
    default:
      return "RUNNING";
  }
}

function stateLabel(usv: UserStateView | undefined): string {
  if (!usv) return "Running";
  return usv.label;
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
        {sessions.slice(0, 14).map((s) => {
          const usv = s.user_state_view;
          return (
            <button
              key={s.session_id}
              className={`rail-item ${activeRun === s.session_id ? "active" : ""}`}
              onClick={() => onSelectRun(s.session_id)}
              type="button"
              title={s.title}
            >
              <span className={`pill ${stateClass(usv)}`}>
                {stateLabel(usv)}
              </span>
              <span className="rail-title">{s.title}</span>
              <span className="rail-when">{s.created_at?.slice(0, 10)}</span>
            </button>
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

      <div className="rail-section">
        <details className="rail-projects" data-sidebar-projects>
          <summary className="rail-h">Projects</summary>
          <div className="rail-empty">
            Projects will group discoveries, knowledge, and packages around
            one goal. Grouping needs a backend contract that doesn&apos;t
            exist yet — until then every discovery lives in Discoveries, and
            nothing is pretending otherwise.
          </div>
        </details>
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
