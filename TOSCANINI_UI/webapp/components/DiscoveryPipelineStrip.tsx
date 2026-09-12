// R451-C2.1 — THE DISCOVERY PIPELINE STRIP.
//
// At the top of the run page: the seven product stages with their
// backend-derived statuses. This is the surface that answers "why
// don't I have a 3D model?" with the truth — "because the system
// never got as far as inventing one" — instead of a blanket "3D
// GEOMETRY UNAVAILABLE".
//
// PRESENTATION-ONLY: every status comes from the dossier's `pipeline`
// projection (toscanini/dossier.py::pipeline_projection), derived from
// canonical records. This component renders verbatim, decides nothing,
// and invents no status: when the projection is absent (older dossier
// payloads) it renders nothing — never a guessed strip (Art. XXV).
//
// Status vocabulary (backend-owned, Art. X):
//   RECEIVED               the stage's recorded artifact exists
//   IN_PROGRESS            the run is active and work is at this stage
//   NOT_REACHED            execution has not arrived here
//   STOPPED                execution arrived and did not complete
//                          (recorded reason in `detail`)
//   PAUSED_INFRASTRUCTURE  execution arrived and stopped on
//                          infrastructure — never a scientific statement
//                          (Art. LXI; the calm slate color)

import type { DossierBody } from "@/lib/types";

const STATUS_MARK: Record<string, string> = {
  RECEIVED: "\u2713",
  IN_PROGRESS: "\u25CF",
  NOT_REACHED: "\u2014",
  STOPPED: "\u2014",
  PAUSED_INFRASTRUCTURE: "\u2014",
};

const STATUS_LABEL: Record<string, string> = {
  RECEIVED: "RECEIVED",
  IN_PROGRESS: "IN PROGRESS",
  NOT_REACHED: "NOT REACHED",
  STOPPED: "STOPPED",
  PAUSED_INFRASTRUCTURE: "PAUSED \u2014 INFRASTRUCTURE",
};

function stageClass(status: string): string {
  switch (status) {
    case "RECEIVED":
      return "done";
    case "IN_PROGRESS":
      return "live";
    case "PAUSED_INFRASTRUCTURE":
      return "infra";
    case "STOPPED":
      return "stopped";
    default:
      return "unreached";
  }
}

export default function DiscoveryPipelineStrip({
  pipeline,
}: {
  pipeline: DossierBody["pipeline"] | null | undefined;
}) {
  if (!pipeline || !Array.isArray(pipeline) || pipeline.length === 0) {
    return null;
  }
  return (
    <section className="pipeline-strip" data-pipeline-strip aria-label="discovery pipeline">
      <div className="pipeline-title faint">DISCOVERY PIPELINE</div>
      <div className="pipeline-rows">
        {pipeline.map((row) => (
          <div
            className={`pipeline-row pr-${stageClass(row.status)}`}
            key={row.key}
            data-pipeline-stage={row.key}
            data-pipeline-status={row.status}
          >
            <span className="pipeline-mark" aria-hidden="true">
              {STATUS_MARK[row.status] ?? "\u2014"}
            </span>
            <span className="pipeline-label">{row.label}</span>
            <span className="pipeline-status">
              {STATUS_LABEL[row.status] ?? row.status}
            </span>
            {row.detail ? (
              <span
                className="pipeline-detail faint"
                data-pipeline-detail={row.key}
              >
                {row.detail}
              </span>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}
