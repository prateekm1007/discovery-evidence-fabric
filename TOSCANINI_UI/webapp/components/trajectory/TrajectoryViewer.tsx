// R450-C2 — the trajectory viewer (directive §3, §6, §9).
//
// The signature visual experience: the design-evolution trajectory rendered
// from the canonical projection of Coder 1's INVENTION_LINEAGE —
//
//     V1 -> FAILURE -> CAUSE -> DIRECTION -> MUTATION -> V2 -> UPDATE
//
// answering three questions visually: WHAT changed, WHY it changed, and
// WHAT HAPPENED. Every element carries its epistemic badge; uncertain
// state shows its uncertainty verbatim; a prediction without a recorded
// evaluation reads NOT_EVALUATED — never "held". The viewer contains no
// business logic and no physics interpretation: everything it renders is
// copied from the projection record (visual presentation is not
// engineering validation).

import type {
  TrajectoryRecord,
  TrajectoryTransition,
} from "@/lib/trajectory";
import { safePredictionOutcome } from "@/lib/trajectory";
import { StateBadge, BadgeLegend } from "./StateBadge";

function Verbatim({
  value,
  className,
}: {
  value?: string | null;
  className?: string;
}) {
  if (!value) return null;
  return <span className={className}>{value}</span>;
}

function FailureCard({ tr }: { tr: TrajectoryTransition }) {
  const f = tr.failure;
  if (!f) return null;
  return (
    <div className="traj-step" data-traj-step="FAILURE">
      <div className="traj-step-head">
        <span className="traj-step-kind">FAILURE</span>
        <StateBadge badge={f.epistemic_badge} />
      </div>
      <div className="traj-step-body">
        {f.killed ? (
          <div className="traj-kill">
            {f.kill_reason ?? "challenge killed the candidate"}
          </div>
        ) : f.survived_with_uncertainties ? (
          <div className="traj-warn">
            survived with uncertainties
            {f.uncertainties ? <> — {f.uncertainties}</> : null}
          </div>
        ) : (
          <Verbatim value={f.attack_overall} className="traj-warn" />
        )}
        <Verbatim value={f.final_status} className="traj-faint" />
      </div>
    </div>
  );
}

function CauseCard({ tr }: { tr: TrajectoryTransition }) {
  const c = tr.cause;
  if (!c) return null;
  const basis = Array.isArray(c.basis) ? c.basis : c.basis ? [c.basis] : [];
  return (
    <div className="traj-step" data-traj-step="CAUSE">
      <div className="traj-step-head">
        <span className="traj-step-kind">CAUSE</span>
        <StateBadge badge={c.epistemic_badge} />
      </div>
      <div className="traj-step-body">
        <div className="traj-cause">
          {c.cause ?? "cause not determined"}
          {c.infrastructure_class ? (
            <span className="pill epi-UNVERIFIED">INFRASTRUCTURE</span>
          ) : null}
        </div>
        {basis.length > 0 && (
          <ul className="traj-basis">
            {basis.map((b, i) => (
              <li key={i}>{b}</li>
            ))}
          </ul>
        )}
        <Verbatim value={c.diagnosed_by} className="traj-faint" />
      </div>
    </div>
  );
}

function DirectionCard({ tr }: { tr: TrajectoryTransition }) {
  const d = tr.direction;
  if (!d) return null;
  return (
    <div className="traj-step" data-traj-step="DIRECTION">
      <div className="traj-step-head">
        <span className="traj-step-kind">DIRECTION</span>
        <StateBadge badge={d.epistemic_badge} />
      </div>
      <div className="traj-step-body">
        {d.causal_change && <div className="traj-dir">{d.causal_change}</div>}
        {d.transferred_capability && (
          <div className="traj-faint">{d.transferred_capability}</div>
        )}
      </div>
    </div>
  );
}

function MutationCard({ tr }: { tr: TrajectoryTransition }) {
  const m = tr.mutation;
  if (!m) return null;
  return (
    <div className="traj-step" data-traj-step="MUTATION">
      <div className="traj-step-head">
        <span className="traj-step-kind">MUTATION</span>
        <StateBadge badge={m.epistemic_badge} />
        {m.mutation_type ? (
          <span className="traj-mtype">{m.mutation_type}</span>
        ) : null}
      </div>
      <div className="traj-step-body">
        {m.shape === "STRUCTURED" && m.fields ? (
          <BeforeAfterDelta fields={m.fields} />
        ) : (
          <div className="traj-dir">
            {m.change_delta}
            <span className="traj-faint"> (recorded change narrative)</span>
          </div>
        )}
      </div>
    </div>
  );
}

export function BeforeAfterDelta({
  fields,
}: {
  fields: { field: string; before: string; after: string; changed: boolean }[];
}) {
  // BEFORE / AFTER / DELTA — the recorded field changes, verbatim. The
  // delta column shows the BEFORE->AFTER pair itself; the visual layer
  // computes no physics from it.
  return (
    <table className="traj-delta" data-before-after-delta>
      <thead>
        <tr>
          <th>field</th>
          <th>BEFORE</th>
          <th>AFTER</th>
          <th>DELTA</th>
        </tr>
      </thead>
      <tbody>
        {fields.map((f) => (
          <tr key={f.field} data-delta-field={f.field}>
            <td className="traj-df">{f.field}</td>
            <td className="traj-db">{f.before || "—"}</td>
            <td className="traj-da">{f.after || "—"}</td>
            <td
              className={f.changed ? "traj-delta-changed" : "traj-faint"}
            >
              {f.changed ? "CHANGED" : "unchanged"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function PredictionCard({ tr }: { tr: TrajectoryTransition }) {
  const p = tr.prediction;
  if (!p) return null;
  const outcome = safePredictionOutcome(p.prediction_outcome);
  return (
    <div className="traj-step" data-traj-step="PREDICTION">
      <div className="traj-step-head">
        <span className="traj-step-kind">PREDICTION</span>
        <StateBadge badge={p.epistemic_badge} />
        <span
          className={`pill pred-outcome pred-${outcome}`}
          data-prediction-outcome={outcome}
        >
          {outcome}
        </span>
      </div>
      <div className="traj-step-body">
        {p.expected_effect && (
          <div className="traj-dir">expected: {p.expected_effect}</div>
        )}
        {p.falsification_test && (
          <div className="traj-faint">would be killed by: {p.falsification_test}</div>
        )}
      </div>
    </div>
  );
}

function StateNode({
  gen,
  status,
  maturity,
  badge,
  current,
  inventionId,
  challenge,
}: {
  gen: number;
  status: string;
  maturity?: string | null;
  badge: unknown;
  current: boolean;
  inventionId?: string | null;
  challenge?: TrajectoryRecord["states"][number]["challenge"];
}) {
  return (
    <div
      className={`traj-state ${current ? "traj-current" : ""}`}
      data-traj-state={gen}
      data-traj-status={status}
    >
      <div className="traj-state-head">
        <span className="traj-gen">V{gen}</span>
        <span className="pill traj-status">{status}</span>
        <StateBadge badge={badge} />
      </div>
      {challenge?.survived_with_uncertainties && (
        <div className="traj-warn" data-uncertainty-label>
          {challenge.uncertainties ?? "survived with uncertainties"}
        </div>
      )}
      {challenge?.killed && (
        <div className="traj-kill">{challenge.kill_reason ?? "killed"}</div>
      )}
      <div className="traj-faint">
        {inventionId ? `${inventionId} · ` : ""}
        {maturity ? `maturity ${maturity}` : ""}
        {current ? " · CURRENT" : ""}
      </div>
    </div>
  );
}

export default function TrajectoryViewer({
  trajectory,
}: {
  trajectory: TrajectoryRecord;
}) {
  const states = trajectory.states ?? [];
  const transitions = trajectory.transitions ?? [];
  return (
    <div className="section" data-trajectory-viewer>
      <h2>Design evolution</h2>
      <div className="sub">
        the recorded improvement trajectory — what changed, why it changed,
        and what happened. Rendered from the engine&apos;s own lineage;
        visual presentation is not engineering validation.
      </div>
      <BadgeLegend />

      <div className="traj-flow">
        {states.map((st, i) => {
          const tr = transitions[i]; // transition AFTER this state (i -> i+1)
          const prev = transitions[i - 1];
          return (
            <div key={st.gen} className="traj-row">
              <StateNode
                gen={st.gen}
                status={st.status}
                maturity={st.maturity}
                badge={st.epistemic_badge}
                current={st.current}
                inventionId={st.invention_id}
                challenge={st.challenge}
              />
              {tr && (
                <div className="traj-transition" data-traj-transition>
                  <div className="traj-arrow" aria-hidden>
                    ↓
                  </div>
                  <FailureCard tr={tr} />
                  <CauseCard tr={tr} />
                  <DirectionCard tr={tr} />
                  <MutationCard tr={tr} />
                  <PredictionCard tr={tr} />
                  <div className="traj-step" data-traj-step="RESULT">
                    <div className="traj-step-head">
                      <span className="traj-step-kind">RESULT</span>
                      <StateBadge badge={tr.result.epistemic_badge} />
                    </div>
                    <div className="traj-step-body">
                      <span className="pill traj-status">
                        {tr.result.status}
                      </span>
                      <Verbatim
                        value={tr.result.maturity}
                        className="traj-faint"
                      />
                    </div>
                  </div>
                  {tr.update && !tr.update.superseded && (
                    <div className="traj-step" data-traj-step="UPDATE">
                      <div className="traj-step-head">
                        <span className="traj-step-kind">UPDATE</span>
                      </div>
                      <div className="traj-step-body">
                        <Verbatim
                          value={tr.update.stop_reason}
                          className="traj-upd"
                        />
                        {tr.update.survivor_reached ? (
                          <span className="traj-faint">
                            {" "}
                            · survivor reached
                          </span>
                        ) : null}
                      </div>
                    </div>
                  )}
                </div>
              )}
              {!tr && prev?.update?.superseded === false && null}
            </div>
          );
        })}
      </div>

      {trajectory.stop_reason ? (
        <div className="traj-stop">
          trajectory stop: <span className="traj-upd">{trajectory.stop_reason}</span>
        </div>
      ) : null}
    </div>
  );
}
