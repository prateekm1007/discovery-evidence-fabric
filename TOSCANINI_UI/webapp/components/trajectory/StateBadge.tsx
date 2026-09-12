// R450-C2 — the epistemic state badge (directive §8).
//
// The interface distinguishes MEASURED / SIMULATED / INFERRED / PROPOSED /
// UNVERIFIED. The user never has to infer this from prose. A beautiful
// render marked incorrectly as validated is dangerous; a mediocre render
// with perfect epistemic labeling is acceptable. Truth controls the labels:
// the badge value arrives from the canonical projection (or degrades to
// UNVERIFIED client-side) — this component can never manufacture one.

import { safeBadge } from "@/lib/trajectory";

const BADGE_TITLE: Record<string, string> = {
  MEASURED:
    "MEASURED — physical observation with an attested event (Art. XXXVIII). " +
    "Reality produced this evidence.",
  SIMULATED:
    "SIMULATED — computational result from a named instrument. " +
    "Computation is not reality.",
  INFERRED:
    "INFERRED — the engine's recorded determination from its stated basis.",
  PROPOSED:
    "PROPOSED — model-proposed content. Never evidence (Art. XVIII).",
  UNVERIFIED:
    "UNVERIFIED — provenance incomplete. Unknown stays unknown (Art. XXV).",
};

const BADGE_CLASS: Record<string, string> = {
  MEASURED: "epi-MEASURED",
  SIMULATED: "epi-SIMULATED",
  INFERRED: "epi-INFERRED",
  PROPOSED: "epi-PROPOSED",
  UNVERIFIED: "epi-UNVERIFIED",
};

export function StateBadge({
  badge,
  title,
}: {
  badge: unknown;
  title?: string;
}) {
  const b = safeBadge(badge);
  return (
    <span
      className={`pill epi-badge ${BADGE_CLASS[b]}`}
      title={title ?? BADGE_TITLE[b]}
      data-badge={b}
    >
      {b}
    </span>
  );
}

export function BadgeLegend() {
  return (
    <div className="epi-legend" data-badge-legend>
      {Object.keys(BADGE_TITLE).map((b) => (
        <span key={b} className="epi-legend-item" title={BADGE_TITLE[b]}>
          <StateBadge badge={b} title={undefined} />
        </span>
      ))}
    </div>
  );
}
