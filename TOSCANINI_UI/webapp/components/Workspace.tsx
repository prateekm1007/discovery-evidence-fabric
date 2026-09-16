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

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import type {
  DossierBody,
  DossierTab,
  GauntletCard,
  ScienceEvent,
  SessionDetail,
} from "@/lib/present-types";
import type { DesignTabShape, SurfaceId } from "@/lib/present";
import { presentGateVerdict, renderAvailabilitySentence } from "@/lib/present";
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
  // R459 (audit P1-4): on touch devices the canvas traps scroll — a
  // one-tap shield stands between the page and the viewer until the
  // user explicitly engages with the 3D interaction.
  const [touchEngaged, setTouchEngaged] = useState(false);
  const isTouch =
    typeof window !== "undefined" &&
    window.matchMedia("(pointer: coarse)").matches;
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
        {viewerUrl && isTouch && !touchEngaged && (
          <button
            type="button"
            className="hero-touch-shield"
            data-touch-shield
            aria-label="tap to interact with the 3D model"
            onClick={() => setTouchEngaged(true)}
          >
            <span>Tap to explore the model in 3D</span>
          </button>
        )}
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
            {/* R462 port (audit P1.4): semantic heading, class kept. */}
            <h2 className="hero-honest-h">Technology visualization</h2>
            <div className="hero-honest-body">Not established yet.</div>
            <div className="hero-honest-note faint">
              {design.hero_eligibility?.reason ||
                "The investigation found an architecture, but the system could not produce a faithful visual representation of it. No substitute model is shown."}
            </div>
          </div>
        ) : design && design.availability === "AVAILABLE" && renders?.status ? (
          <div className="hero-honest" data-hero-render-unavailable>
            <h2 className="hero-honest-h">Technology model</h2>
            <div className="hero-honest-body">
              {renderAvailabilitySentence(renders, {
                // R453-C2 merge: the geometry phrase is DERIVED from the
                // recorded authority — never asserted (R452 B2, Art. XXVIII)
                engineering_authority: (design?.engineering_authority ?? null) as
                  | "ENGINEERING"
                  | "CONCEPTUAL"
                  | "UNKNOWN"
                  | null,
                conceptual: design?.conceptual,
              })}
            </div>
          </div>
        ) : (
          <div className="hero-honest" data-hero-not-established>
            <h2 className="hero-honest-h">Technology model</h2>
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
            /* R476 (UI audit): product language on the surface — the raw
               machine verdict (PASS / COMPLETE_PASS / …) rides the title
               deep layer, never the badge text (BS-009, same discipline
               as MATURITY_PRESENTATION and the model kind badge). */
            title={`visual quality gate verdict: ${gateVerdict}`}
            style={{
              borderColor: gateOk ? "#3d7a4d" : "#a05a3d",
              color: gateOk ? "#3d7a4d" : "#a05a3d",
            }}
          >
            {gateOk ? "✓" : "✕"} {presentGateVerdict(gateVerdict)}
          </span>
          — the presentation is exactly what the visual quality gate certified, no more
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
  packageGate,
  surface,
  onClose,
  onSwitch,
}: {
  detail: SessionDetail;
  dossier: DossierBody | null;
  events: ScienceEvent[];
  gauntlet: GauntletCard[];
  packageAvailable: boolean;
  /** R477 (audit P0-5): the typed 409 payload from the package
   * 200-probe — rendered as the gate sentence + the diagnostic
   * fallback, so a gated package is a stated state, never a dead
   * click. */
  packageGate?: Record<string, unknown> | null;
  surface: string | null;
  onClose: () => void;
  /** §13: contextual switching between sibling surfaces (one artifact,
   * no tab strip) — the parent owns the surface state. */
  onSwitch: (s: SurfaceId) => void;
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

  // R476 (UI audit, a11y): the workspace is a NAMED non-modal panel —
  // keyboard users land inside it when it opens (and when the surface
  // switches), instead of focus staying behind in the conversation.
  // Deliberately NOT a focus-trap: the panel coexists with the
  // conversation (non-modal), so trapping would break the contract;
  // initial focus + Escape-close is the correct pattern here.
  const panelRef = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (!surface) return;
    panelRef.current?.focus();
  }, [surface]);

  if (!surface) return null;
  const tabs = dossier?.tabs;

  // R458-C2 (§13): ONE current workspace title + a SMALL secondary nav
  // to the sibling surfaces — the workspace is one artifact with
  // contextual switching, not a second pipeline browser with a
  // permanent tab strip. The journal is deliberately NOT in this row
  // (§14: the technical record must not compete with the discovery
  // surface); it stays reachable via the outcome's "Show the technical
  // record" and the small link at the bottom of this panel.
  const siblings = (Object.keys(SURFACE_TITLES) as SurfaceId[]).filter(
    (s) => s !== surface && s !== "journal"
  );
  const siblingLabel = (s: SurfaceId): string =>
    ({ overview: "Summary", model: "Technology model", evidence: "Evidence",
       engineering: "Engineering", experiment: "Experiment",
       package: "Package", journal: "Journal" }[s] ?? SURFACE_TITLES[s]);

  return (
    <aside
      ref={panelRef}
      className="wk"
      data-workspace
      data-wk-surface={surface}
      aria-label={SURFACE_TITLES[surface] ?? surface}
      tabIndex={-1}
    >
      <div className="wk-head">
        {/* R464 (audit P1-4): a real heading — screen readers navigate
            the workspace surfaces by h2, not by a styled span. The
            visual weight is unchanged (h2.wk-title resets its margins
            and inherits the panel's own type). */}
        <h2 className="wk-title">{SURFACE_TITLES[surface] ?? surface}</h2>
        <div className="wk-siblings" data-wk-siblings>
          {siblings.map((s) => (
            <button
              key={s}
              type="button"
              className="wk-sibling faint"
              onClick={() => onSwitch(s)}
            >
              {siblingLabel(s)}
            </button>
          ))}
        </div>
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
        {surface === "package" &&
          (packageGate ? (
            // R477 (audit P0-5): the gate's own typed words + the
            // always-available diagnostic fallback — the click that
            // would have 409'd becomes a stated state with a working
            // alternative.
            <div className="pkg-gate-note" data-package-gate>
              <div className="pkg-gate-title">
                The package download is blocked by this run's release
                gate
              </div>
              {typeof packageGate.package_state === "string" && (
                <div className="faint">state: {packageGate.package_state}</div>
              )}
              {typeof packageGate.reason === "string" && (
                <div className="tab-reason">{packageGate.reason}</div>
              )}
              {Array.isArray(packageGate.reasons) &&
                packageGate.reasons.length > 0 && (
                  <div className="tab-reason">
                    {(packageGate.reasons as string[]).join(" ")}
                  </div>
                )}
              {typeof packageGate.note === "string" && (
                <div className="faint tab-reason">{packageGate.note}</div>
              )}
              <a
                className="btn download"
                href={`/api/run/${encodeURIComponent(detail.session_id)}/diagnostic-package`}
              >
                Download the diagnostic record instead
              </a>
            </div>
          ) : tabs ? (
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
            ))}
        {surface === "journal" && (
          <JournalSurface
            detail={detail}
            events={events}
            gauntlet={gauntlet}
            packageAvailable={packageAvailable}
          />
        )}
      </div>
      {surface !== "journal" && (
        <div className="wk-foot">
          <button
            type="button"
            className="conv-technical faint"
            onClick={() => onSwitch("journal")}
          >
            Technical record
          </button>
        </div>
      )}
    </aside>
  );
}
