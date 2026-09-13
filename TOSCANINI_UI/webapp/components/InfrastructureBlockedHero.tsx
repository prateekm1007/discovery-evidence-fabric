"use client";

// R451-C2 — the INFRASTRUCTURE-BLOCKED presentation surface.
//
// One canonical component for the state the directive describes:
// an infrastructure interruption must never be visually confused with
// scientific absence, invention failure, a rejected architecture,
// insufficient evidence, or an unestablished technology (Art. LXI;
// blind spots BS-008/009/011/018).
//
// PRESENTATION-ONLY: this component receives the already-derived
// backend/user-state projection (the PresentationView from
// lib/presentationState.ts, which consumes user_state_view — the
// authoritative backend projection). It decides NOTHING from raw
// fields and interprets nothing: the wording below states only
//   * what the infrastructure state is (recorded),
//   * that no scientific conclusion was reached (true by definition
//     of the state), and
//   * that the problem is saved and resumable (recorded capability).
//
// The layout is deliberately COMPACT (directive sections 6/9): an
// absence state does not get the visual real estate of a technology
// artifact. No fake model viewport, no fallback 3D object, no
// synthetic geometry — the problem-context panel below is a diagram
// of the USER'S PROBLEM, explicitly labeled "not an invention model".

import type { PresentationView } from "@/lib/presentationState";

export function InfrastructureBlockedHero({
  view,
  problemText,
  onResume,
  onOpenJournal,
}: {
  view: PresentationView;
  problemText: string;
  onResume: () => void;
  onOpenJournal: () => void;
}) {
  const b = view.blocked;
  if (!b) return null;
  return (
    <section className="infra-block" data-infra-block>
      <div className="infra-hero" data-infra-hero>
        <div className="infra-hero-state" data-infra-headline>
          {b.headline}
        </div>
        <div className="infra-hero-sub" data-infra-subline>
          {b.subline}
        </div>
        <div className="infra-hero-verdict" data-infra-verdict>
          {b.verdictLine}
        </div>
        <div className="infra-hero-saved" data-infra-saved>
          {b.savedLine}
        </div>
        <div className="infra-hero-cta" data-infra-cta>
          <button
            type="button"
            className="btn primary big"
            onClick={onResume}
            data-resume-cta
          >
            Resume investigation
          </button>
          <button
            type="button"
            className="btn ghost big"
            onClick={onOpenJournal}
            data-journal-cta
          >
            View investigation journal
          </button>
          <button
            type="button"
            className="btn ghost big"
            disabled
            title="Available after the investigation produces a releasable technology package."
            data-package-cta-disabled
          >
            Technology package
          </button>
        </div>
        <div className="infra-hero-note faint" data-infra-note>
          this is an infrastructure state, never a scientific verdict —
          the pause says nothing about the problem, the evidence, or any
          technology
        </div>
      </div>

      <div className="infra-recovery" data-infra-recovery>
        <div className="infra-recovery-row">
          <div className="infra-recovery-h">What happened</div>
          <div className="infra-recovery-b">{b.whatHappened}</div>
        </div>
        <div className="infra-recovery-row">
          <div className="infra-recovery-h">What was established</div>
          <div className="infra-recovery-b">{b.whatWasEstablished}</div>
        </div>
        <div className="infra-recovery-row">
          <div className="infra-recovery-h">What remains unknown</div>
          <div className="infra-recovery-b">{b.whatRemainsUnknown}</div>
        </div>
      </div>

      <ProblemContextPanel problemText={problemText} />
    </section>
  );
}

// C2.4 — the problem-context visualization: a visualization of the
// USER'S PROBLEM, never of an invented technology. Its state says
// exactly that. No dimensional claims, no fake CAD, no synthetic
// invention, no visual-side causal story — the panel renders the
// problem's own recorded words and the investigation's recorded
// position, nothing more.
export function ProblemContextPanel({
  problemText,
}: {
  problemText: string;
}) {
  const text = (problemText || "").trim();
  if (!text) return null;
  return (
    <div className="problem-context" data-problem-context>
      <div className="pc-state" data-problem-context-state>
        Problem context — not an invention model
      </div>
      <div className="pc-body">
        <div className="pc-label faint">The problem you asked about</div>
        <div className="pc-problem" data-problem-context-text>
          {text}
        </div>
        <div className="pc-note faint" data-problem-context-note>
          This panel describes your problem, not a technology. No
          dimensional claims, no engineering geometry, no synthetic
          invention — nothing here was produced by an engine that has
          not run.
        </div>
      </div>
    </div>
  );
}

export default InfrastructureBlockedHero;
