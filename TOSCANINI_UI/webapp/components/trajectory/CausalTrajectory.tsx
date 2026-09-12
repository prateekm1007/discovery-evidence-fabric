// R450-C2 — the causal trajectory surface (directive §6).
//
// The compact causal chain over the WHOLE trajectory:
//
//     FAILURE -> CAUSE -> DIRECTION -> MUTATION -> RESULT -> UPDATE
//
// Aggregated from the same canonical projection the TrajectoryViewer
// renders (no second data source, no duplicated business logic). Where a
// stage has no recorded content the stage renders as an honest gap —
// never fabricated from prose.

import type { TrajectoryRecord } from "@/lib/trajectory";
import { StateBadge } from "./StateBadge";

const CHAIN_STAGES = [
  "FAILURE",
  "CAUSE",
  "DIRECTION",
  "MUTATION",
  "RESULT",
  "UPDATE",
] as const;

type StageKind = (typeof CHAIN_STAGES)[number];

interface StageCell {
  stage: StageKind;
  present: boolean;
  badge?: unknown;
  summary?: string | null;
}

function aggregate(trajectory: TrajectoryRecord): StageCell[] {
  const transitions = trajectory.transitions ?? [];
  const first = <T,>(sel: (t: TrajectoryRecord["transitions"][number]) => T): T | null => {
    for (const t of transitions) {
      const v = sel(t);
      if (v) return v;
    }
    return null;
  };
  const failure = first((t) => t.failure);
  const cause = first((t) => t.cause);
  const direction = first((t) => t.direction);
  const mutation = first((t) => t.mutation);
  const result = transitions[transitions.length - 1]?.result ?? null;
  const update = transitions[transitions.length - 1]?.update ?? null;

  const trunc = (s: unknown, n = 160) =>
    s ? String(s).slice(0, n) : null;

  return [
    {
      stage: "FAILURE",
      present: !!failure,
      badge: failure?.epistemic_badge,
      summary: failure
        ? trunc(failure.kill_reason ?? failure.attack_overall)
        : null,
    },
    {
      stage: "CAUSE",
      present: !!cause,
      badge: cause?.epistemic_badge,
      summary: cause ? trunc(cause.cause) : null,
    },
    {
      stage: "DIRECTION",
      present: !!direction,
      badge: direction?.epistemic_badge,
      summary: direction ? trunc(direction.causal_change) : null,
    },
    {
      stage: "MUTATION",
      present: !!mutation,
      badge: mutation?.epistemic_badge,
      summary: mutation
        ? trunc(
            mutation.shape === "STRUCTURED"
              ? (mutation.mutation_type ?? "recorded field changes")
              : mutation.change_delta,
          )
        : null,
    },
    {
      stage: "RESULT",
      present: !!result,
      badge: result?.epistemic_badge,
      summary: result ? `${result.status} (V${result.gen})` : null,
    },
    {
      stage: "UPDATE",
      present: !!update,
      badge: undefined,
      summary: update?.stop_reason ? trunc(update.stop_reason) : null,
    },
  ];
}

export default function CausalTrajectory({
  trajectory,
}: {
  trajectory: TrajectoryRecord;
}) {
  const cells = aggregate(trajectory);
  return (
    <div className="causal-flow" data-causal-trajectory>
      <div className="sub">
        the causal loop this trajectory records — every stage carries its
        epistemic badge; an empty stage is an honest gap, not a hidden one.
      </div>
      <div className="causal-chain">
        {cells.map((c, i) => (
          <div key={c.stage} className="causal-cell-wrap">
            <div
              className={`causal-cell ${c.present ? "causal-present" : "causal-gap"}`}
              data-causal-stage={c.stage}
              title={
                c.present
                  ? undefined
                  : `${c.stage}: not recorded in this trajectory (honest absence)`
              }
            >
              <div className="causal-stage">
                {c.stage}
                {c.badge !== undefined && c.present ? (
                  <StateBadge badge={c.badge} />
                ) : null}
              </div>
              <div className="causal-summary">
                {c.present ? c.summary : "not recorded"}
              </div>
            </div>
            {i < cells.length - 1 && (
              <div className="causal-arrow" aria-hidden>
                ▼
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
