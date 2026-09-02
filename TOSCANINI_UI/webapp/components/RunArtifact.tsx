"use client";

// R395: the workspace's right pane for a RUN — the live artifact card
// while the engine works, then the honest terminal card: package
// download when one was produced, the honest no-package explanation
// when not (a real result, never a failure of the product).

import type { SessionDetail } from "@/lib/types";
import { isTerminal } from "./RunNarrative";

export default function RunArtifact({
  detail,
  onRetry,
}: {
  detail: SessionDetail;
  onRetry: (id: string) => void;
}) {
  const usv = detail.user_state_view;
  const done = isTerminal(detail.status);
  const stages = detail.stages ?? [];
  const pkg = detail.package ?? null;

  const pillClass = usv
    ? usv.user_state.startsWith("COMPLETED")
      ? "COMPLETE"
      : usv.user_state.startsWith("FAILED") || usv.user_state === "INTERRUPTED"
        ? "ERROR"
        : "RUNNING"
    : detail.status.startsWith("ERROR")
      ? "ERROR"
      : detail.status;

  return (
    <div className="artifact">
      <div className="artifact-h">Artifact</div>
      {!done && (
        <>
          <div className="artifact-live">
            <div className="spinner" />
            <div>
              <div className="artifact-state">
                {usv?.label ?? "Running"}
              </div>
              <div className="faint" style={{ fontSize: 12.5 }}>
                {stages.length} of 13 engine steps recorded — the design
                and package will appear here when the run finishes
              </div>
            </div>
          </div>
          <div className="artifact-note">
            Toscanini investigates with real evidence retrieval, adversarial
            attacks, and honest gates. Runs take minutes — you can leave
            and come back.
          </div>
        </>
      )}

      {done && usv && (
        <>
          <div className={`pill ${pillClass}`}>{usv.label}</div>
          <div className="artifact-decision">{usv.decision}</div>
          <div className="artifact-meaning faint">{usv.meaning}</div>

          {pkg?.zip_name ? (
            <a
              className="btn download artifact-dl"
              href={`/api/run/${detail.session_id}/package`}
            >
              Download technology package
            </a>
          ) : usv.found_something ? (
            <div className="artifact-note">
              <b>Candidate, no package.</b> This run recorded an invention
              candidate, but no buyer package was produced — the release
              gate was not reached. An honest result: candidates are
              recorded, packages are earned.
            </div>
          ) : (
            <div className="artifact-note">
              <b>No buyer package.</b> A package is produced only when a
              candidate survives the full adversarial chain — no survivor
              reached the release gate on this run. That is an honest
              result, not a failure of the product: kills are recorded to
              the mechanism cemetery and improve the next run.
            </div>
          )}

          {(detail.status.startsWith("ERROR") ||
            detail.status === "INTERRUPTED") && (
            <div className="errbox" style={{ marginTop: 12 }}>
              <b>{detail.status}</b> — {detail.error ?? "unknown error"}
              <div style={{ marginTop: 10 }}>
                <button
                  className="btn ghost small"
                  onClick={() => onRetry(detail.session_id)}
                  type="button"
                >
                  Retry through the same worker path
                </button>
              </div>
            </div>
          )}
        </>
      )}

      <div className="artifact-explore">
        <div className="rail-h">Explore released inventions</div>
        <div className="faint" style={{ fontSize: 12.5 }}>
          the 15 finished technology packages — interactive 3D designs,
          live parameters, buyer dossiers — in the left rail
        </div>
      </div>
    </div>
  );
}
