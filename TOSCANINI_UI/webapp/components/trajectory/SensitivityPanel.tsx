// R450-C2 — the parameter sensitivity panel (directive §5).
//
// Rendered ONLY when Coder 1 supplies a legitimate sensitivity result.
// The panel renders parameter -> response points VERBATIM with the
// declared basis badge; it calculates nothing, fits nothing, and
// interprets nothing. Where no sensitivity result is supplied, this
// panel does not render at all (honest absence — the viewer never
// manufactures scientific interpretation).

import type { SensitivityRecord } from "@/lib/trajectory";
import { isSensitivityRecord } from "@/lib/trajectory";
import { StateBadge } from "./StateBadge";

export default function SensitivityPanel({
  record,
}: {
  record: unknown;
}) {
  if (!isSensitivityRecord(record)) return null; // honest absence
  const rec: SensitivityRecord = record;
  const values = rec.points.map((p) =>
    typeof p.value === "number" ? p.value : Number(p.value),
  );
  const objectives = rec.points.map((p) =>
    typeof p.objective === "number" ? p.objective : Number(p.objective),
  );
  const numeric = values.every((v) => Number.isFinite(v)) &&
    objectives.every((o) => Number.isFinite(o));

  return (
    <div className="section" data-sensitivity-panel data-basis={rec.basis}>
      <h2>Parameter sensitivity</h2>
      <div className="sub">
        the response {rec.objective ? `of ${rec.objective} ` : ""}to{" "}
        {rec.parameter}, supplied by the engineering evaluation state —
        rendered verbatim, interpreted nowhere.
      </div>

      <div className="sens-head">
        <span className="traj-mtype">{rec.parameter}</span>
        <StateBadge badge={rec.epistemic_badge} />
      </div>

      {numeric ? (
        <div className="sens-chart" data-sensitivity-chart>
          {rec.points.map((p, i) => {
            const v = Number(p.value);
            const o = Number(p.objective);
            const min = Math.min(...objectives);
            const max = Math.max(...objectives);
            const span = max - min || 1;
            // bar length encodes ONLY the supplied number's relative size;
            // the encoding is geometric, never causal
            const pct = 8 + ((o - min) / span) * 92;
            return (
              <div key={i} className="sens-row" data-sensitivity-point={i}>
                <span className="sens-val">{p.value}</span>
                <span className="sens-track">
                  <span className="sens-bar" style={{ width: `${pct}%` }} />
                </span>
                <span className="sens-obj">{p.objective}</span>
              </div>
            );
          })}
        </div>
      ) : (
        <table className="traj-delta" data-sensitivity-table>
          <thead>
            <tr>
              <th>{rec.parameter}</th>
              <th>{rec.objective ?? "objective"}</th>
            </tr>
          </thead>
          <tbody>
            {rec.points.map((p, i) => (
              <tr key={i}>
                <td>{p.value}</td>
                <td>{p.objective}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {rec.note ? <div className="traj-faint">{rec.note}</div> : null}
    </div>
  );
}
