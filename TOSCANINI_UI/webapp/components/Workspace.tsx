"use client";

// R453-C2 — THE WORKSPACE: the contextual surface where substantial
// output lives while the conversation continues (the Artifacts role —
// brief §12/§36). Desktop: a right-side column that appears when useful.
// Mobile: the same surface as a bottom sheet. It is NEVER permanently
// on screen and never a second pipeline browser.
//
// Surfaces: overview · model · evidence · engineering · experiment ·
// package · journal. Everything rendered here comes from the canonical
// dossier/run projections (Art. X) — the deep sections are REUSED
// unchanged from DossierSections/RunNarrative (no second renderer).
//
// The ONE-viewer invariant (R432/R433/R435): the 3D viewer mounts ONLY
// inside the model surface, so exactly one [data-model-viewer] exists.

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import type {
  DossierBody,
  DossierTab,
  GauntletCard,
  ScienceEvent,
  SessionDetail,
} from "@/lib/present-types";
import type { DesignTabShape } from "@/lib/present";
import { renderAvailabilitySentence } from "@/lib/present";
import RunNarrative from "./RunNarrative";
import { EngineeringArgument, NoveltyAndCemetery } from "./EngineeringArgument";
import InventionEssay from "./InventionEssay";
import { Gauntlet, ScienceEventStream } from "./ScienceEvents";
import {
  EvidenceSection,
  EngineeringSection,
  ExperimentSection,
  FalsificationCard,
  ModelDetailsSection,
  PackageSection,
  SummarySection,
} from "./DossierSections";

const ModelViewer = dynamic(() => import("./ModelViewer"), {
  ssr: false,
  loading: () => (
    <div className="hero-preparing" data-hero-preparing>
      <div className="hero-preparing-label">
        Preparing technology visualization…
      </div>
      <div className="hero-preparing-sub">
        the model is built from the same canonical engineering geometry
        the technology package carries
      </div>
    </div>
  ),
});

export const SURFACE_TITLES: Record<string, string> = {
  overview: "Summary",
  model: "The technology model",
  evidence: "Evidence",
  engineering: "Engineering",
  experiment: "The decisive test",
  package: "Technology package",
  journal: "The technical record",
};

function ModelSurface({
  detail,
  dossier,
  viewingGen,
  onSelectGen,
  highlight,
  onHighlight,
}: {
  detail: SessionDetail;
  dossier: DossierBody | null;
  viewingGen: number | null;
  onSelectGen: (g: number | null) => void;
  highlight: string | null;
  onHighlight: (id: string | null) => void;
}) {
  const design = dossier?.tabs?.design as DesignTabShape | undefined;
  // structural subset of the design tab's evolution rows (the canonical
  // shape lives in DossierSections::EvolutionRowData — React-owned)
  const evo =
    (design?.evolution as
      | { generation: number; glb?: string | null; why?: string | null }[]
      | undefined) ?? [];
  const heroEligible = design?.hero_eligibility?.eligible !== false;
  const heroGlb =
    heroEligible && design && design.availability === "AVAILABLE"
      ? (design.glb as string | undefined) ?? null
      : null;
  const activeRow =
    viewingGen != null ? evo.find((r) => r.generation === viewingGen) : undefined;
  const showingHistory = heroEligible && Boolean(activeRow?.glb);
  const viewerUrl = showingHistory && activeRow?.glb ? activeRow.glb : heroGlb;
  const genLabelNum = String(design?.generation_id ?? "gen-1").replace("gen-", "");
  const renders = design?.renders as
    | { status?: string; visual_gate?: { verdict?: string; hero_suppressed?: boolean } }
    | undefined;
  const gateVerdict = renders?.visual_gate?.verdict;
  const gateOk = gateVerdict === "PASS" || gateVerdict === "COMPLETE_PASS";
  const modelKind: "engineering" | "conceptual" | undefined = design?.fallback_basis
    ? "conceptual"
    : design?.conceptual
      ? "conceptual"
      : "engineering";

  return (
    <div className="wk-model" data-wk-model>
      <div className="hero-viewport" data-hero-viewport>
        {viewerUrl ? (
          <>
            <ModelViewer
              url={viewerUrl}
              variant="hero"
              height="100%"
              modelKind={modelKind}
              genLabel={
                showingHistory
                  ? `generation ${viewingGen} · history`
                  : `generation ${genLabelNum}`
              }
              label={
                showingHistory
                  ? `GEN ${viewingGen} historical architecture — the current model is GEN ${genLabelNum}`
                  : modelKind === "conceptual"
                    ? "conceptual architecture"
                    : "engineering geometry — canonical CAD source"
              }
              highlight={highlight}
            />
            {showingHistory && (
              <button
                type="button"
                className="hero-return"
                onClick={() => onSelectGen(null)}
              >
                ← back to the current generation
              </button>
            )}
            {highlight && (
              <button
                type="button"
                className="hero-clear"
                onClick={() => onHighlight(null)}
              >
                clear highlight ({highlight})
              </button>
            )}
          </>
        ) : design && design.availability === "AVAILABLE" && !heroEligible ? (
          <div className="hero-honest hero-unearned" data-hero-unearned>
            <div className="hero-honest-h">Technology visualization</div>
            <div className="hero-honest-body">Not established yet.</div>
            <div className="hero-honest-note faint">
              {design.hero_eligibility?.reason ||
                "The investigation found an architecture, but the system could not produce a faithful visual representation of it. No substitute model is shown."}
            </div>
          </div>
        ) : design && design.availability === "AVAILABLE" && renders?.status ? (
          <div className="hero-honest" data-hero-render-unavailable>
            <div className="hero-honest-h">Technology model</div>
            <div className="hero-honest-body">
              {renderAvailabilitySentence(renders)}
            </div>
          </div>
        ) : (
          <div className="hero-honest" data-hero-not-established>
            <div className="hero-honest-h">Technology model</div>
            <div className="hero-honest-body">Not established on this run.</div>
            <div className="hero-honest-note faint">
              {design?.note ||
                "A physical-looking model was not generated for this technology — showing one anyway would misrepresent the engineering state."}
            </div>
          </div>
        )}
      </div>
      {gateVerdict && (
        <div className="wk-gate faint">
          visual gate{" "}
          <span
            className="gate-badge"
            style={{
              borderColor: gateOk ? "#3d7a4d" : "#a05a3d",
              color: gateOk ? "#3d7a4d" : "#a05a3d",
            }}
          >
            {gateOk ? "✓" : "✕"} {gateVerdict}
          </span>
          — the presentation is what the gate certified, no more (Art. LXXII)
        </div>
      )}
      <ModelDetailsSection
        tab={dossier?.tabs?.design as DossierTab}
        viewingGen={viewingGen}
        onSelectGen={onSelectGen}
        highlight={highlight}
        onHighlight={onHighlight}
      />
    </div>
  );
}

function JournalSurface({
  detail,
  events,
  gauntlet,
  packageAvailable,
}: {
  detail: SessionDetail;
  events: ScienceEvent[];
  gauntlet: GauntletCard[];
  packageAvailable: boolean;
}) {
  const done = detail.status === "COMPLETE";
  const hasJournal =
    events.length > 0 || gauntlet.length > 0 || detail.stages != null;
  return (
    <div className="wk-journal" data-wk-journal>
      {hasJournal ? (
        <>
          <RunNarrative detail={detail} packageAvailable={packageAvailable} />
          {done && (
            <>
              <div className="dd-part">
                <h3>The engineering argument</h3>
                <EngineeringArgument
                  detail={detail}
                  packageAvailable={packageAvailable}
                />
              </div>
              <div className="dd-part">
                <InventionEssay sessionId={detail.session_id} />
              </div>
              <div className="dd-part">
                <NoveltyAndCemetery detail={detail} />
              </div>
            </>
          )}
          {gauntlet.length > 0 && (
            <div className="dd-part">
              <h3>Scientific gauntlet</h3>
              <Gauntlet cards={gauntlet} />
            </div>
          )}
          {events.length > 0 && (
            <div className="dd-part">
              <h3>Event history</h3>
              <div className="sub faint">
                {events.length} recorded events — each carries its own
                provenance; expand any card
              </div>
              <ScienceEventStream events={events} />
            </div>
          )}
        </>
      ) : (
        <div className="tab-note tn-pending">
          No recorded events yet — the journal fills as the investigation runs.
        </div>
      )}
    </div>
  );
}

export default function Workspace({
  detail,
  dossier,
  events,
  gauntlet,
  packageAvailable,
  surface,
  onClose,
}: {
  detail: SessionDetail;
  dossier: DossierBody | null;
  events: ScienceEvent[];
  gauntlet: GauntletCard[];
  packageAvailable: boolean;
  surface: string | null;
  onClose: () => void;
}) {
  // the model surface's generation navigation + component highlight live
  // HERE (they act on the ONE viewer inside this workspace)
  const [viewingGen, setViewingGen] = useState<number | null>(null);
  const [highlight, setHighlight] = useState<string | null>(null);

  // Escape closes the surface — the conversation stays primary
  useEffect(() => {
    if (!surface) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [surface, onClose]);

  if (!surface) return null;
  const tabs = dossier?.tabs;

  return (
    <aside className="wk" data-workspace data-wk-surface={surface}>
      <div className="wk-head">
        <span className="wk-title">{SURFACE_TITLES[surface] ?? surface}</span>
        <button
          type="button"
          className="wk-close"
          onClick={onClose}
          aria-label="close workspace"
        >
          ✕
        </button>
      </div>
      <div className="wk-body">
        {surface === "overview" &&
          (tabs ? (
            <SummarySection tab={tabs.overview as DossierTab} gauntlet={[]} />
          ) : (
            <div className="tab-note tn-pending">
              The summary appears as soon as the investigation has a canonical
              state.
            </div>
          ))}
        {surface === "model" && (
          <ModelSurface
            detail={detail}
            dossier={dossier}
            viewingGen={viewingGen}
            onSelectGen={setViewingGen}
            highlight={highlight}
            onHighlight={setHighlight}
          />
        )}
        {surface === "evidence" &&
          (tabs ? (
            <EvidenceSection tab={tabs.evidence as DossierTab} />
          ) : (
            <div className="tab-note tn-pending">
              The evidence ledger appears as sources are retrieved.
            </div>
          ))}
        {surface === "engineering" &&
          (tabs ? (
            <EngineeringSection tab={tabs.engineering as DossierTab} />
          ) : (
            <div className="tab-note tn-pending">
              Engineering details appear when the design reaches the
              engineering stage.
            </div>
          ))}
        {surface === "experiment" &&
          (tabs ? (
            <ExperimentSection tab={tabs.experiment as DossierTab} />
          ) : (
            <div className="tab-note tn-pending">
              The decisive test is specified once the invention survives its
              challenges.
            </div>
          ))}
        {surface === "package" && (
          <>
            {tabs ? (
              <>
                <PackageSection tab={tabs.transfer as DossierTab} />
                {dossier?.falsification && (
                  <div className="dd-part">
                    <FalsificationCard f={dossier.falsification} />
                  </div>
                )}
                <div className="dossier-foot faint">{dossier?.derived_from}</div>
              </>
            ) : (
              <div className="tab-note tn-pending">
                Package details appear when a package exists on this run.
              </div>
            )}
          </>
        )}
        {surface === "journal" && (
          <JournalSurface
            detail={detail}
            events={events}
            gauntlet={gauntlet}
            packageAvailable={packageAvailable}
          />
        )}
      </div>
    </aside>
  );
}
