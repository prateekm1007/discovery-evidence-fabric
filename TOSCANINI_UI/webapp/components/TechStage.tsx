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
import { isTerminal } from "./RunNarrative";
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

// the stage status — product language, derived from the run's own
// user_state_view (never re-derived from raw machine status here)
function stageStatus(detail: SessionDetail): {
  label: string;
  tone: string;
} {
  const usv = detail.user_state_view;
  if (!isTerminal(detail.status)) {
    return { label: "Investigating", tone: "live" };
  }
  if (
    detail.status === "RUN_BLOCKED_TRANSPORT" ||
    detail.status === "INTERRUPTED" ||
    detail.status.startsWith("ERROR")
  ) {
    return { label: "Paused — infrastructure", tone: "paused" };
  }
  if (usv?.package_available || usv?.found_something) {
    return { label: "Technology ready", tone: "done" };
  }
  if (usv?.rejected) {
    return { label: "Approach refuted", tone: "refuted" };
  }
  return { label: "Investigation complete", tone: "done" };
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

  const done = isTerminal(detail.status);
  const usv = detail.user_state_view;
  const status = stageStatus(detail);
  const blocked =
    detail.status === "RUN_BLOCKED_TRANSPORT" ||
    detail.status === "INTERRUPTED" ||
    detail.status.startsWith("ERROR");

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
  const gateOk = gateVerdict === "PASS";
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
      | { retrieved_count?: number; used_count?: number }
      | undefined) ?? undefined;
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

      {/* ---- the four insight cards ---- */}
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
          sub={
            evidenceCounts?.retrieved_count != null
              ? `${evidenceCounts.retrieved_count} sources retrieved · ${
                  evidenceCounts.used_count ?? 0
                } shaped the design`
              : null
          }
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

      {/* ---- the actions ---- */}
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
      {!packageAvailable && done && (
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

      {/* ---- blocked: the honest pause + resume ---- */}
      {blocked && onRetry && (
        <div className="retry-row">
          <button
            className="btn"
            onClick={() => onRetry(detail.session_id)}
            type="button"
          >
            Resume investigation
          </button>
          <span className="faint">
            the problem is saved; this is an infrastructure state, never a
            scientific verdict
          </span>
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
        viewingGen={viewingGen}
        onSelectGen={setViewingGen}
        highlight={highlight}
        onHighlight={setHighlight}
      />
    </div>
  );
}
