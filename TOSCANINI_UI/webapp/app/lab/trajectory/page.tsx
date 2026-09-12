"use client";

// R450-C2 — the Visual Feedback Layer lab route (LABORATORY capability,
// NOT production truth).
//
// The operator directive is explicit: the R448 lab line stays
// laboratory/provisional; nothing here claims production integration.
// This route renders the trajectory layer from REAL canonical data —
// the projection of the engine's committed INVENTION_LINEAGE (R445
// evolution run evol-x02-bus-fastcharge-lithium-plating) — plus the
// clearly-labeled sensitivity SCHEMA_EXAMPLE. The production dossier
// path renders the same viewer ONLY when the backend serves a
// TOSCANINI_TRAJECTORY record (honest absence otherwise).

import CausalTrajectory from "@/components/trajectory/CausalTrajectory";
import SensitivityPanel from "@/components/trajectory/SensitivityPanel";
import TrajectoryViewer from "@/components/trajectory/TrajectoryViewer";
import { isTrajectoryRecord } from "@/lib/trajectory";
import demoTrajectory from "@/lib/fixtures/r450-trajectory-evol-x02.json";
import structuredExample from "@/lib/fixtures/r450-trajectory-structured-example.json";
import demoSensitivity from "@/lib/fixtures/r450-sensitivity-schema-example.json";

export default function LabTrajectoryPage() {
  const trajectory = demoTrajectory as unknown;
  return (
    <main style={{ maxWidth: 880, margin: "0 auto", padding: "48px 22px" }}>
      <div className="pill RUNNING" style={{ marginBottom: 12 }}>
        VISUAL FEEDBACK LABORATORY — provisional capability, not production
        truth
      </div>
      <h1 style={{ fontSize: 26, marginBottom: 6 }}>
        Design evolution — the improvement trajectory
      </h1>
      <p className="sub" style={{ color: "var(--ink-faint)" }}>
        Rendered from the engineering state Coder 1 established (the
        engine&apos;s recorded INVENTION_LINEAGE). Visual presentation is not
        engineering validation: every physical claim originates from the
        engineering/evaluation state, and every element carries its
        epistemic badge.
      </p>

      {isTrajectoryRecord(trajectory) ? (
        <>
          <TrajectoryViewer trajectory={trajectory} />
          <div className="section">
            <h2>Causal trajectory</h2>
            <CausalTrajectory trajectory={trajectory} />
          </div>
        </>
      ) : (
        <div className="pill ERROR">fixture is not a trajectory record</div>
      )}

      <div className="section">
        <div
          className="pill epi-badge epi-PROPOSED"
          style={{ marginBottom: 12 }}
          title="This panel demonstrates the rendering contract with a
                 labeled schema example. No canonical sensitivity result
                 exists yet."
        >
          SCHEMA EXAMPLE — not a Toscanini result
        </div>
        <SensitivityPanel record={demoSensitivity} />
      </div>

      <div className="section">
        <h2>Before / after / delta — structured shape</h2>
        <div
          className="pill epi-badge epi-PROPOSED"
          style={{ marginBottom: 12 }}
          title="Demonstrates the BEFORE/AFTER/DELTA table contract with the
                 improvement engine's structured mutation record shape.
                 Values are illustrative of the rendering contract."
        >
          SCHEMA EXAMPLE — not a Toscanini result
        </div>
        {isTrajectoryRecord(structuredExample) && (
          <TrajectoryViewer trajectory={structuredExample} />
        )}
      </div>
    </main>
  );
}
