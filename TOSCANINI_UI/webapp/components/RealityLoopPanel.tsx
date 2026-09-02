"use client";

// R390: the reality-loop panel (CEO directive #6 + #8). Shows the closed
// loop — a real external observation that refuted a design basis and
// CHANGED a technical decision — as part of the investor-facing
// narrative. Every label is honest: MEASURED origin is shown with its
// event id and the declared basis it refuted; nothing ever claims
// PHYSICAL_VALIDATION (Art. XXXVIII — that word is structurally absent
// from the whole surface).

import type { RealityLoopRecord } from "@/lib/types";

export default function RealityLoopPanel({
  record,
}: {
  record: RealityLoopRecord;
}) {
  const obs = record.observation ?? {};
  const hyp = record.causal_hypothesis ?? {};
  const dec = record.decision_change ?? {};
  const ree = record.re_evaluation ?? {};
  const mut = dec.mutation ?? {};
  const real = record.real_event;

  return (
    <div className="section">
      <h2>Reality loop</h2>
      <div className="sub">
        a real external observation confronted this design — the proof that
        an observation changed a technical decision (not a styling claim)
      </div>

      <div className="loopcard">
        <div className="loophead">
          <span className={`pill ${real ? "COMPLETE" : "RUNNING"}`}>
            {obs.origin === "MEASURED" ? "MEASURED" : "RECONSTRUCTED"}
          </span>
          <span className="pill COMPLETE">{record.loop_verification_state}</span>
          <span className="loopev">{obs.event_id}</span>
        </div>

        <div className="loopgrid">
          <div className="block">
            <h4>The observation</h4>
            <div className="kv">
              <span className="k">design basis</span>
              <span>
                {obs.design_value} mPa·s — {obs.design_declared_basis}
              </span>
              <span className="k">measured</span>
              <span>
                {obs.measured_value?.toFixed(4)} mPa·s ({obs.origin})
              </span>
              {obs.origin_caveat && (
                <>
                  <span className="k">caveat</span>
                  <span className="faint">{obs.origin_caveat}</span>
                </>
              )}
              <span className="k">discrepancy</span>
              <span>
                {(obs.relative_delta ?? 0) * 100 > 0 ? "+" : ""}
                {((obs.relative_delta ?? 0) * 100).toFixed(1)}% vs declared
                ±{((obs.declared_uncertainty ?? 0) * 100).toFixed(0)}% —{" "}
                <b className="bad">{obs.status}</b>
              </span>
            </div>
          </div>

          <div className="block">
            <h4>The decision it changed</h4>
            <div className="kv">
              <span className="k">before</span>
              <span>{dec.before}</span>
              <span className="k">after</span>
              <span>
                <b>{dec.after}</b>
              </span>
              <span className="k">canonical package</span>
              <span>
                {mut.applied_to_canonical_package
                  ? "mutated"
                  : "untouched — recorded as a V2-class design decision with full provenance"}
              </span>
            </div>
          </div>
        </div>

        <div className="loopquote">{hyp.statement}</div>

        <div className="block">
          <h4>Re-evaluated technical result</h4>
          <div className="kv">
            <span className="k">conductance (design basis)</span>
            <span>
              {ree.before?.G_ml_min_mmHg?.toExponential(3)}{" "}
              mL/(min·mmHg)
            </span>
            <span className="k">as-built at old geometry</span>
            <span>
              {ree.as_built?.G_ml_min_mmHg?.toExponential(3)} — the
              over-drainage guard miscalibration the observation exposed
            </span>
            <span className="k">after rebuild (measured basis)</span>
            <span>
              <b>{ree.after?.G_ml_min_mmHg?.toExponential(3)}</b> — restored
              ratio {ree.restored_ratio?.toFixed(4)}
            </span>
          </div>
        </div>

        {dec.technical_result && (
          <div className="evalresult">{dec.technical_result}</div>
        )}

        {hyp.residual_unknown && (
          <div className="block">
            <h4>What is still unknown</h4>
            <ul>
              <li>{hyp.residual_unknown}</li>
            </ul>
          </div>
        )}

        {(record.causal_chain?.stages?.length ?? 0) > 0 && (
          <div className="chainpills">
            {(record.causal_chain?.stages ?? []).map((s) => (
              <span className="chainpill" key={s}>
                {s}
              </span>
            ))}
          </div>
        )}

        <div className="basis" style={{ marginTop: 12 }}>
          {record.honesty}
          {record.causal_chain?.recorded_in_canonical_ledger
            ? " Causal chain recorded in the append-only mutation ledger."
            : ""}
        </div>
      </div>
    </div>
  );
}
