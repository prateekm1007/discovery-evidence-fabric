"use client";

// R395: the workspace's left rail — the problem history (user-state
// pills, never raw machine states) and the released inventions (the
// 15-package portfolio as PROOF, not the homepage).

import type { SessionRow, ShowcaseRow, UserStateView } from "@/lib/types";

// user_state -> pill class (reuses the status pill palette)
function stateClass(usv: UserStateView | undefined): string {
  if (!usv) return "RUNNING";
  switch (usv.user_state) {
    case "COMPLETED_PACKAGE":
      return "COMPLETE";
    case "COMPLETED_CANDIDATE":
      return "COMPLETE";
    case "COMPLETED_REJECTED":
      return "REJECTED";
    case "COMPLETED_UNKNOWN":
      return "ERROR";
    case "INTERRUPTED":
      return "ERROR";
    case "FAILED_TRANSPORT":
    case "FAILED_ENGINE":
      return "ERROR";
    default:
      return "RUNNING";
  }
}

export function stateLabel(usv: UserStateView | undefined): string {
  if (!usv) return "Running";
  return usv.label;
}

export default function HistoryRail({
  sessions,
  showcase,
  activeRun,
  activeInvention,
  onSelectRun,
  onSelectInvention,
  onNewProblem,
}: {
  sessions: SessionRow[];
  showcase: ShowcaseRow[];
  activeRun: string | null;
  activeInvention: string | null;
  onSelectRun: (id: string) => void;
  onSelectInvention: (slot: string) => void;
  onNewProblem: () => void;
}) {
  const focus = showcase.filter((s) => s.demo_focus);
  const others = showcase.filter((s) => !s.demo_focus);

  return (
    <nav className="rail" aria-label="history and inventions">
      <button className="rail-new" onClick={onNewProblem} type="button">
        + New problem
      </button>

      <div className="rail-section">
        <div className="rail-h">Your runs</div>
        {sessions.length === 0 && (
          <div className="rail-empty">
            no runs yet — describe a problem to start one
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
              <span className="rail-when">
                {s.created_at?.slice(0, 10)}
              </span>
            </button>
          );
        })}
      </div>

      <div className="rail-section">
        <div className="rail-h">Released inventions</div>
        <div className="rail-sub">
          proof the engine produces technology packages — 3D designs,
          parameters, dossiers
        </div>
        {focus.map((s) => (
          <button
            key={s.slot}
            className={`rail-item inv ${activeInvention === s.slot ? "active" : ""}`}
            onClick={() => onSelectInvention(s.slot)}
            type="button"
            title={s.blurb}
          >
            <span className="rail-inv-id">{s.package_id}</span>
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
                <span className="rail-inv-id">{s.package_id}</span>
                <span className="rail-title">{s.title}</span>
                <span className="rail-when">{s.domain}</span>
              </button>
            ))}
          </details>
        )}
      </div>
    </nav>
  );
}
