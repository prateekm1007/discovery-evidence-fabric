"use client";

// R435 — THE PRODUCT EXPERIENCE RESET: the technology stage.
//
//   TOP      "Designing: <the problem>" + live status
//   HERO     the technology model — large, dominant, interactive
//   AROUND   What changed · Why it works · What supports it ·
//            What could kill it
//   BOTTOM   Test this · Compare generations · Technology package
//   BELOW    DeepDive — every rigorous layer, progressively disclosed
//
// Product principles (the round directive):
//   * ONE objective, ONE calm workspace — complexity appears when
//     asked for, never upfront;
//   * the technology artifact IS the product — it becomes the dominant
//     surface the moment geometry exists, never a small card inside a
//     report;
//   * the dossier stays the canonical projection underneath (Art. X):
//     every field rendered here comes from /dossier + /events +
//     /result — the frontend never re-derives epistemic state;
//   * while the investigation runs, the journal is the show (watch it
//     think); when the model is ready, the model is the show;
//   * honest states everywhere: a model that is NOT ESTABLISHED says
//     so calmly — never a dead viewer, never a fake model.
//
// The ONE-viewer invariant (R433/R432): exactly one [data-model-viewer]
// on this page. Generation history and component highlighting act on
// THAT viewer — never a second one.

import { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import type {
  DossierBody,
  GauntletCard,
  ScienceEvent,
  SessionDetail,
} from "@/lib/types";
import {
  blockedInsightCards,
  isTerminal,
  resolvePresentationState,
} from "@/lib/presentationState";
import type { PresentationView } from "@/lib/presentationState";
import {
  GEOMETRY_ABSENT_COPY,
  renderBlockedCopy,
} from "@/lib/presentationState";
import { retryPresentation } from "@/lib/api";
import InfrastructureBlockedHero from "./InfrastructureBlockedHero";
import DiscoveryPipelineStrip from "./DiscoveryPipelineStrip";
import {
  Gauntlet,
  InvestigationProgress,
  ScienceEventStream,
} from "./ScienceEvents";
import DeepDive from "./DeepDive";
import type { DesignTabData } from "./DossierSections";

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

function shortTitle(detail: SessionDetail): string {
  const t = (detail.title || detail.user_text || "").trim();
  if (t.length <= 92) return t;
  return t.slice(0, 89).replace(/\s+\S*$/, "") + "…";
}

// the stage status — product language mapped through THE ONE
// presentation-state mapping (lib/presentationState.ts): the backend
// user-state projection decides; the frontend renders, never re-derives
// (Art. X). The three tones are the three documented semantic colors:
//   live   = investigating (green)
//   infra  = infrastructure paused (calm slate — distinct from failure)
//   refuted= scientific rejection (red)
//   done   = a completed scientific state (neutral)
function stageStatus(view: PresentationView): {
  label: string;
  tone: string;
} {
  switch (view.state) {
    case "INVESTIGATING":
      return { label: "Investigating", tone: "live" };
    case "INFRASTRUCTURE_PAUSED":
      return { label: "Discovery paused — infrastructure", tone: "infra" };
    case "SCIENTIFIC_REJECTION":
      return { label: "Premise refuted", tone: "refuted" };
    case "GEOMETRY_READY_RENDER_BLOCKED":
      // R451-C2.1: States C and D say different things — the renderer
      // being unavailable is never worded as a gate rejection, and a
      // gate rejection is never worded as renderer absence
      return view.renderBlockCause === "gate_not_passed"
        ? {
            label: "Model rendered — gate not passed",
            tone: "infra",
          }
        : {
            label: "Model ready — renderer unavailable",
            tone: "infra",
          };
    case "VISUAL_READY":
      return { label: "Technology ready", tone: "done" };
    case "GEOMETRY_UNAVAILABLE":
      // State B (R451-C2.1): the invention exists — what is missing is
      // the visualization, never the technology itself
      return {
        label: "Engineering visualization not available",
        tone: "done",
      };
    case "TECHNOLOGY_NOT_ESTABLISHED":
      return { label: "Investigation complete", tone: "done" };
  }
}

// ---- the hero surface while the investigation runs -------------------------
function HeroInvestigating({
  events,
  gauntlet,
  lastCompleted,
  active,
  paused,
}: {
  events: ScienceEvent[];
  gauntlet: GauntletCard[];
  lastCompleted: string | null;
  active: string | null;
  paused: string | null;
}) {
  return (
    <div className="hero-live" data-hero-live>
      <div className="hero-live-inner">
        <InvestigationProgress
          lastCompletedLabel={lastCompleted}
          activeLabel={active}
          pausedLabel={paused}
        />
        <div className="hero-live-line faint">
          The technology model will appear here as the design solidifies.
          The investigation is persisted on the server; you can leave and
          return to it.
        </div>
      </div>
    </div>
  );
}

// ---- the honest not-established hero ----------------------------------------
// R451-C2: this surface is ONLY for a COMPLETED run that reached its
// honest scientific end without establishing a technology. An
// infrastructure stop NEVER reaches this component — the presentation-
// state mapping routes those to InfrastructureBlockedHero before this
// branch is reachable. R451-C2.1: an invention WITH a visualization
// absence never reaches here either — State B has its own hero below.
function HeroNotEstablished({ design }: { design: DesignTabData | undefined }) {
  return (
    <div className="hero-honest" data-hero-not-established>
      <div className="hero-honest-h">Technology model</div>
      <div className="hero-honest-body">
        Not established on this run.
      </div>
      <div className="hero-honest-note faint">
        {design?.note ||
          "A physical-looking model was not generated for this technology — " +
          "showing one anyway would misrepresent the engineering state."}
      </div>
    </div>
  );
}

// ---- State B (R451-C2.1): the invention exists, the visualization does not --
// The exact directive sentence — the absence is the VISUALIZATION's, never
// the technology's. The recorded reason (not applicable vs the geometry
// build having failed) rides beneath, verbatim from the backend.
function HeroNoVisualization({
  view,
  design,
}: {
  view: PresentationView;
  design: DesignTabData | undefined;
}) {
  return (
    <div className="hero-honest hero-noviz" data-hero-no-visualization>
      <div className="hero-honest-h">{GEOMETRY_ABSENT_COPY.heading}</div>
      <div className="hero-honest-body">{GEOMETRY_ABSENT_COPY.line}</div>
      {(view.geometryAbsent?.detail || design?.note) && (
        <div className="hero-honest-note faint" data-noviz-reason>
          {view.geometryAbsent?.detail || design?.note}
        </div>
      )}
      <div className="hero-honest-note faint">
        The full technical record — the invention itself, its scores, and
        the recorded reason — is preserved below.
      </div>
    </div>
  );
}

// ---- R436 Direction 3: the UNEARNED hero -----------------------------------
// A geometry exists on this run (the record keeps it — inspectable and
// downloadable in the deep layer), but it did not EARN the primary
// surface: a generic fallback object or a model that does not
// faithfully represent the recorded architecture. No substitute model
// is shown (blind-spot register BS-006/007/024/025).
function HeroNotFaithful({ design }: { design: DesignTabData | undefined }) {
  const he = design?.hero_eligibility;
  const notVisualized = he?.not_visualized || [];
  return (
    <div className="hero-honest hero-unearned" data-hero-unearned>
      <div className="hero-honest-h">Technology visualization</div>
      <div className="hero-honest-body">
        Not established yet.
      </div>
      <div className="hero-honest-note faint">
        {he?.reason ||
          "The investigation found an architecture, but the system could " +
          "not produce a faithful visual representation of it. No " +
          "substitute model is shown."}
      </div>
      {notVisualized.length > 0 && (
        <div className="hero-honest-note faint" data-unearned-components>
          Architecture components not represented in the geometry: {""}
          {notVisualized.join(", ")}.
        </div>
      )}
      <div className="hero-honest-note faint">
        The full technical record — the model’s recorded scores, the
        geometry files, and the reason visualization was not earned — is
        preserved below.
      </div>
    </div>
  );
}

// ---- one insight card --------------------------------------------------------
function InsightCard({
  title,
  body,
  sub,
  state,
  onClick,
  dataAttr,
}: {
  title: string;
  body: string | null;
  sub?: string | null;
  state?: "pending" | "failed" | "done";
  onClick?: () => void;
  dataAttr?: string;
}) {
  const cls = state === "pending" ? " ic-pending" : "";
  return (
    <button
      type="button"
      className={`insight${cls}`}
      data-insight={dataAttr}
      onClick={onClick}
      disabled={!onClick}
    >
      <div className="ic-title">{title}</div>
      {body ? (
        <div className="ic-body">{body}</div>
      ) : state === "failed" ? (
        <div className="ic-body faint">
          The generator did not produce a usable answer for this field —
          recorded, never faked.
        </div>
      ) : (
        <div className="ic-body faint">
          Still being investigated — this appears as the run records it.
        </div>
      )}
      {sub && <div className="ic-sub faint">{sub}</div>}
      {onClick && <div className="ic-more faint">details ↓</div>}
    </button>
  );
}

export default function TechStage({
  detail,
  events,
  gauntlet,
  dossier,
  packageAvailable,
  onRetry,
}: {
  detail: SessionDetail;
  events: ScienceEvent[];
  gauntlet: GauntletCard[];
  dossier: DossierBody | null;
  packageAvailable: boolean;
  onRetry?: (id: string) => void;
}) {
  const [viewingGen, setViewingGen] = useState<number | null>(null);
  const [highlight, setHighlight] = useState<string | null>(null);
  const [focusRequest, setFocusRequest] = useState<string | null>(null);
  const [renderRetryNote, setRenderRetryNote] = useState<string | null>(null);

  // R451-C2: THE ONE presentation-state mapping (lib/presentationState.ts)
  // — consumed by every branch below. The backend user-state projection
  // (user_state_view) is authoritative; the frontend never re-derives a
  // state from raw fields and never reconciles conflicting signals
  // silently (adversarial attacks A–E are pinned by the UI test battery).
  const view = useMemo(
    () => resolvePresentationState(detail, dossier),
    [detail, dossier]
  );
  const done = isTerminal(detail.status);
  const usv = detail.user_state_view;
  const status = stageStatus(view);
  const blocked = view.infrastructurePaused;

  const design = dossier?.tabs?.design as DesignTabData | undefined;
  const overview = dossier?.tabs?.overview;
  const evidence = dossier?.tabs?.evidence;
  const evo = design?.evolution ?? [];

  // ---- hero resolution (the ONE viewer) ----
  // R436 Direction 3: the geometry must EARN the hero. The dossier
  // projection carries hero_eligibility (derived from the run's own
  // records — fallback_basis / semantic_identity); the frontend only
  // renders it (Art. X). An ineligible geometry renders the honest
  // unearned state — never a substitute object on the primary surface,
  // and never a second viewer to work around the first.
  const heroEligible = design?.hero_eligibility?.eligible !== false;
  const heroGlb =
    heroEligible && design && design.availability === "AVAILABLE"
      ? design.glb
      : null;
  const activeRow =
    viewingGen != null ? evo.find((r) => r.generation === viewingGen) : undefined;
  // history swap is gated on the SAME eligibility: an unearned current
  // generation cannot be bypassed by selecting a historical one
  const showingHistory = heroEligible && Boolean(activeRow?.glb);
  const viewerUrl = showingHistory && activeRow?.glb ? activeRow.glb : heroGlb;
  const genLabelNum = (design?.generation_id || "gen-1").replace("gen-", "");
  const genCount = design?.generation_count || evo.length || 1;
  // R441 Article LXXII: the hero the buyer sees is the hero the gate
  // approved — the verdict is surfaced on the stage, never hidden
  const renders = design?.renders;
  const gateVerdict = (renders?.visual_gate as
    | { verdict?: string }
    | undefined)?.verdict;
  // R446-C2 WS4: the canonical release-passing verdict is COMPLETE_PASS
  // (R443 visual-set completeness); legacy PASS remains valid while
  // pre-R443 trees exist. Treating COMPLETE_PASS as a failure badge
  // understated backend truth on every post-R443 certified render.
  const gateOk = gateVerdict === "PASS" || gateVerdict === "COMPLETE_PASS";
  const modelKind: "engineering" | "conceptual" | undefined =
    design?.fallback_basis
      ? "conceptual"
      : design?.conceptual
        ? "conceptual"
        : "engineering";

  // ---- insight data (all from the dossier projection — Art. X) ----
  const currentRow = useMemo(
    () => evo.find((r) => r.current) ?? evo[evo.length - 1],
    [evo]
  );
  const whatChanged = (currentRow?.why ??
    (overview?.invention_state as string | null | undefined) ?? null);
  const mechanism = overview?.mechanism ?? null;
  const mechanismFailed = Boolean(overview?.mechanism_generation_failed);
  const strongestEvidence = overview?.strongest_evidence ?? null;
  const evidenceCounts =
    (evidence as
      | {
          retrieval_state?: string;
          retrieval_note?: string | null;
          retrieved_count?: number;
          used_count?: number;
        }
      | undefined) ?? undefined;
  // R451-C2 (C2.5, Article XXV): numeric evidence counts exist ONLY when
  // the backend says retrieval actually executed (retrieval_state
  // RETRIEVED — its zero is a measured zero). NOT_REACHED / PENDING /
  // FAILED are typed unknowns — they render as words, never as "0".
  const evidenceSub =
    evidenceCounts?.retrieval_state === "RETRIEVED" &&
    evidenceCounts.retrieved_count != null
      ? `${evidenceCounts.retrieved_count} sources retrieved · ${
          evidenceCounts.used_count ?? 0
        } shaped the design`
      : null;
  const strongestChallenge =
    overview?.strongest_challenge ?? dossier?.falsification?.challenge_condition ?? null;
  const decisiveTest = overview?.decisive_experiment ?? null;

  // ---- journal helpers (while running, the journal is the show) ----
  const liveEvents = useMemo(() => {
    if (!done) return events;
    return events.slice(-6);
  }, [events, done]);
  const lastCompleted = useMemo(() => {
    const doneEvts = [...events]
      .reverse()
      .find((e) => e.status === "COMPLETED" && !e.kind.startsWith("investigation."));
    return doneEvts?.summary ?? null;
  }, [events]);
  const activeLabel = useMemo(() => {
    const act = [...events].reverse().find((e) => e.status === "ACTIVE");
    return act?.summary ?? null;
  }, [events]);
  // R436 (audit §5B): an infrastructure-failed event is NOT active work —
  // it renders as its own paused state, never as "Currently: …".
  const pausedLabel = useMemo(() => {
    const paused = [...events]
      .reverse()
      .find((e) => e.status === "FAILED_INFRASTRUCTURE");
    return paused?.summary ?? null;
  }, [events]);

  function focus(section: string) {
    setFocusRequest(`${section}:${Date.now()}`);
  }

  const downloadUrl = (dossier?.tabs?.transfer as
    | { download?: string | null }
    | undefined)?.download;

  return (
    <div className="tech-stage" data-tech-stage>
      {/* ---- R451-C2.1: THE DISCOVERY PIPELINE strip (top of the page) ----
          the seven product stages with backend-derived statuses — the
          surface that answers "why don't I have a 3D model?" with the
          recorded truth instead of a blanket geometry-unavailable line */}
      <DiscoveryPipelineStrip pipeline={dossier?.pipeline} />

      {/* ---- the stage head ---- */}
      <div className="stage-head">
        <div className="stage-kicker faint">Designing</div>
        <h1 className="stage-title">{shortTitle(detail)}</h1>
        <div className="stage-meta">
          <span className={`stage-pill sp-${status.tone}`}>
            <span className="cursor" aria-hidden="true" />
            {status.label}
          </span>
          {done && usv?.outcome_label && (
            <span className="faint stage-outcome">{usv.outcome_label}</span>
          )}
          {genCount > 1 && (
            <span className="faint stage-outcome">
              {genCount} generations evolved
            </span>
          )}
        </div>
      </div>

      {/* ---- THE HERO: the technology artifact ---- */}
      {/* R451-C2: an infrastructure pause gets the dedicated COMPACT
          blocked surface — never the large model viewport, never the
          "Not established" hero (sections 1/2/6/9 of the directive). */}
      {blocked ? (
        <InfrastructureBlockedHero
          view={view}
          problemText={detail.user_text || detail.title || ""}
          onResume={() => onRetry?.(detail.session_id)}
          onOpenJournal={() => focus("journal")}
        />
      ) : (
      <>
      {view.state === "GEOMETRY_READY_RENDER_BLOCKED" && (() => {
        // R451-C2.1: States C and D — the exact copy per the backend's
        // typed presentation_cause; the canonical GLB stays interactive
        // in the viewer below either way
        const rb = renderBlockedCopy(view.renderBlockCause);
        return (
        <div className="render-blocked-ribbon" data-render-blocked-ribbon>
          <div className="rbr-main">
            <span className="rbr-title">{rb.title}</span>
            <span className="rbr-sub faint">{rb.line}</span>
          </div>
          <div className="rbr-actions">
            <button
              type="button"
              className="btn small"
              onClick={() =>
                retryPresentation(detail.session_id)
                  .then(() =>
                    setRenderRetryNote(
                      "presentation build queued — this page updates when it finishes"
                    )
                  )
                  .catch(() =>
                    setRenderRetryNote(
                      "the presentation build could not be queued — the engineering model remains available below"
                    )
                  )
              }
              data-retry-presentation
            >
              Retry presentation
            </button>
            <button
              type="button"
              className="btn small ghost"
              onClick={() => focus("model")}
            >
              Open model files
            </button>
          </div>
          {view.renderBlockDetail && (
            <div className="rbr-note faint" data-render-block-detail>
              {view.renderBlockDetail}
            </div>
          )}
          {renderRetryNote && (
            <div className="rbr-note faint" data-render-retry-note>
              {renderRetryNote}
            </div>
          )}
        </div>
        );
      })()}
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
                onClick={() => setViewingGen(null)}
              >
                ← back to the current generation
              </button>
            )}
            {highlight && (
              <button
                type="button"
                className="hero-clear"
                onClick={() => setHighlight(null)}
              >
                clear highlight ({highlight})
              </button>
            )}
          </>
        ) : done && design && design.availability === "AVAILABLE" ? (
          // R436 Direction 3: geometry exists but did not earn the hero —
          // the honest unearned state (no substitute model)
          <HeroNotFaithful design={design} />
        ) : view.state === "GEOMETRY_UNAVAILABLE" ? (
          // R451-C2.1 State B: the invention exists, the visualization
          // does not — the exact directive sentence, never "Not
          // established on this run" for an invention that DOES exist
          <HeroNoVisualization view={view} design={design} />
        ) : done ? (
          <HeroNotEstablished design={design} />
        ) : (
          <HeroInvestigating
            events={events}
            gauntlet={gauntlet}
            lastCompleted={lastCompleted}
            active={activeLabel}
            paused={pausedLabel}
          />
        )}
      </div>
      <div className="hero-hint faint">
        {viewerUrl
          ? "rotate · zoom · pan · wireframe · clip — the model is built from the canonical CAD source the package carries"
          : done
            ? "the scientific record below is complete regardless — a model is a presentation, never a claim"
            : ""}
        {gateVerdict && (
          <span
            className="gate-badge"
            title={gateOk
              ? "Article LXXII — this render passed the Visual Quality Gate (frame occupancy, contact shadow, semantic materials, single viewer)"
              : "Article LXXII — Visual Quality Gate verdict: " + gateVerdict}
            style={{
              marginLeft: 12,
              padding: "1px 8px",
              borderRadius: 999,
              fontSize: 11,
              border: "1px solid " + (gateOk ? "#3d7a4d" : "#a05a3d"),
              color: gateOk ? "#3d7a4d" : "#a05a3d",
            }}
          >
            visual gate {gateOk ? "\u2713" : "\u2715 " + gateVerdict}
          </span>
        )}
      </div>
      </>
      )}

      {/* ---- the four insight cards ---- */}
      {/* R451-C2: a blocked run gets the DEDICATED blocked-state cards
          ("not evaluated because execution stopped") — never the
          ordinary-incompleteness wording, never scientific absence. */}
      {blocked ? (
        <div className="stage-insights" data-stage-insights-blocked>
          {blockedInsightCards(evidence as
            | Parameters<typeof blockedInsightCards>[0]
            | undefined).map((card) => (
            <div
              className="insight insight-blocked"
              key={card.title}
              data-blocked-insight={
                card.title.toLowerCase().replace(/\s+/g, "-")
              }
            >
              <div className="ic-title">{card.title}</div>
              <div className="ic-body ic-blocked-headline">
                {card.headline}
              </div>
              <div className="ic-sub faint">{card.body}</div>
            </div>
          ))}
        </div>
      ) : (
      <div className="stage-insights" data-stage-insights>
        <InsightCard
          title="What changed"
          body={whatChanged}
          sub={
            genCount > 1
              ? `generation ${currentRow?.generation ?? genCount} of ${genCount}`
              : null
          }
          state={done && !whatChanged ? "pending" : undefined}
          onClick={() => focus("model")}
          dataAttr="what-changed"
        />
        <InsightCard
          title="Why it works"
          body={mechanism}
          state={
            mechanismFailed ? "failed" : !mechanism && !done ? "pending" : undefined
          }
          onClick={() => focus("summary")}
          dataAttr="why-it-works"
        />
        <InsightCard
          title="What supports it"
          body={
            strongestEvidence?.title
              ? strongestEvidence.title
              : (evidence as { note?: string } | undefined)?.note ?? null
          }
          sub={evidenceSub}
          state={!strongestEvidence && !done ? "pending" : undefined}
          onClick={() => focus("evidence")}
          dataAttr="what-supports-it"
        />
        <InsightCard
          title="What could kill it"
          body={strongestChallenge ?? decisiveTest}
          sub={strongestChallenge && decisiveTest ? "the decisive test is specified below" : null}
          state={done && !strongestChallenge && !decisiveTest ? "pending" : undefined}
          onClick={() => focus("experiment")}
          dataAttr="what-could-kill-it"
        />
      </div>
      )}

      {/* ---- the actions ---- */}
      {/* R451-C2: for an infrastructure pause the action hierarchy is
          owned by the blocked hero (Resume primary · journal secondary ·
          package disabled with its reason). The standard row — where
          "Test this" would read as the primary continuation path —
          is not rendered for that state. */}
      {!blocked && (
      <div className="stage-actions" data-stage-actions>
        <button
          type="button"
          className="btn ghost big"
          onClick={() => focus("experiment")}
        >
          Test this
        </button>
        {genCount > 1 && heroEligible && (
          <button
            type="button"
            className="btn ghost big"
            onClick={() => focus("model")}
          >
            Compare generations
          </button>
        )}
        {packageAvailable && downloadUrl ? (
          <a
            className="btn primary big stage-download"
            href={downloadUrl}
            data-stage-package
          >
            Download the technology package
          </a>
        ) : (
          <button
            type="button"
            className="btn primary big stage-download"
            disabled
            title={
              done
                ? "no package on this run — the recorded reason is the truth"
                : "the package is built when the invention survives its challenges"
            }
          >
            Technology package
          </button>
        )}
      </div>
      )}
      {!blocked && !packageAvailable && done && (
        <div className="stage-actions-note faint">
          No technology package on this run —{" "}
          {(dossier?.tabs?.transfer as { note?: string } | undefined)?.note ??
            "the invention did not reach the transfer bar; the recorded reason is the truth."}
        </div>
      )}

      {/* ---- the live journal (while the investigation runs) ---- */}
      {!done && (liveEvents.length > 0 || gauntlet.length > 0) && (
        <div className="stage-journal" data-stage-journal-live>
          <div className="stage-journal-h">The investigation, as it happens</div>
          {gauntlet.length > 0 && <Gauntlet cards={gauntlet} />}
          {liveEvents.length > 0 && (
            <ScienceEventStream events={liveEvents} dense />
          )}
        </div>
      )}

      {/* ---- the terminal verdict line ---- */}
      {done && usv && (
        <div className="stage-verdict" data-stage-verdict>
          <div className="sv-label">{usv.label}</div>
          <div className="sv-decision">{usv.decision}</div>
          {usv.meaning && <div className="sv-meaning faint">{usv.meaning}</div>}
        </div>
      )}

      {/* ---- EVERYTHING ELSE, progressively disclosed ---- */}
      <DeepDive
        dossier={dossier}
        detail={detail}
        events={events}
        gauntlet={gauntlet}
        packageAvailable={packageAvailable}
        focusRequest={focusRequest}
        paused={blocked}
        viewingGen={viewingGen}
        onSelectGen={setViewingGen}
        highlight={highlight}
        onHighlight={setHighlight}
      />
    </div>
  );
}
