"use client";

// R435 — the technology stage for a RELEASED invention (showcase mode).
//
// The same product principles as the run stage (TechStage), applied to
// a finished technology from the certified buyer-distribution chain:
// the 3D artifact is the hero; the story, parameters, reality loop and
// package live underneath, progressively disclosed. The released
// package bytes are never modified (Art. IX) — parameter rebuilds are
// MODELLED previews that swap the single hero viewer, clearly labeled.

import { useState } from "react";
import dynamic from "next/dynamic";
import type { RealityLoopRecord, ShowcaseDetail } from "@/lib/types";
import InventionArtifact from "./InventionArtifact";
import InventionStory from "./InventionStory";
import AskBox from "./AskBox";

const ModelViewer = dynamic(() => import("./ModelViewer"), {
  ssr: false,
  loading: () => (
    <div className="hero-preparing" data-hero-preparing>
      <div className="hero-preparing-label">
        Preparing technology visualization…
      </div>
      <div className="hero-preparing-sub">
        the model is the released engineering geometry the package carries
      </div>
    </div>
  ),
});

function InsightCard({
  title,
  body,
  onClick,
  dataAttr,
}: {
  title: string;
  body: string | null;
  onClick?: () => void;
  dataAttr?: string;
}) {
  return (
    <button
      type="button"
      className="insight"
      data-insight={dataAttr}
      onClick={onClick}
      disabled={!onClick}
    >
      <div className="ic-title">{title}</div>
      <div className={body ? "ic-body" : "ic-body faint"}>
        {body || "—"}
      </div>
      {onClick && <div className="ic-more faint">details ↓</div>}
    </button>
  );
}

export default function InventionStage({
  detail,
  loop,
  slot,
}: {
  detail: ShowcaseDetail;
  loop: RealityLoopRecord | null;
  slot: string;
}) {
  const [previewGlb, setPreviewGlb] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(true);
  const baseGlb = detail.model.glb;
  const showing = previewGlb && showPreview ? previewGlb : baseGlb;
  const brief = detail.brief ?? {};

  function focus(id: string) {
    const el = document.querySelector(`[data-dd-section="${id}"]`);
    if (el) {
      (el as HTMLDetailsElement).open = true;
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  return (
    <div className="tech-stage" data-tech-stage data-invention-stage>
      {/* ---- the stage head ---- */}
      <div className="stage-head">
        <div className="stage-kicker faint">Technology</div>
        <h1 className="stage-title">{detail.title}</h1>
        <div className="stage-meta">
          <span className="stage-pill sp-done">Released package</span>
          {detail.maturity && (
            <span className="faint stage-outcome">{detail.maturity}</span>
          )}
          {detail.domain && (
            <span className="faint stage-outcome">{detail.domain}</span>
          )}
        </div>
        {detail.blurb && <div className="stage-blurb">{detail.blurb}</div>}
      </div>

      {/* ---- THE HERO: the released technology artifact ---- */}
      <div className="hero-viewport" data-hero-viewport>
        {baseGlb && (
          <>
            <ModelViewer
              url={showing}
              variant="hero"
              height="100%"
              modelKind="engineering"
              label={
                showing === baseGlb
                  ? "released geometry"
                  : "preview rebuild — your parameter change"
              }
              note={
                showing === baseGlb
                  ? undefined
                  : "a preview rebuild from your parameter change — deterministic CAD sandbox; the released package is untouched"
              }
            />
            {previewGlb && (
              <div className="hero-ab">
                <span className="ab-label faint">comparing</span>
                <div className="ab-toggle">
                  <button
                    className={showing === baseGlb ? "on" : ""}
                    onClick={() => setShowPreview(false)}
                    type="button"
                  >
                    released
                  </button>
                  <button
                    className={showing !== baseGlb ? "on" : ""}
                    onClick={() => setShowPreview(true)}
                    type="button"
                  >
                    your rebuild
                  </button>
                </div>
                <button
                  className="ab-clear"
                  onClick={() => setPreviewGlb(null)}
                  type="button"
                >
                  clear preview
                </button>
              </div>
            )}
          </>
        )}
      </div>
      <div className="hero-hint faint">
        rotate · zoom · pan · wireframe · clip — this is the released
        engineering geometry from the certified buyer-distribution chain
      </div>

      {/* ---- the four insight cards ---- */}
      <div className="stage-insights" data-stage-insights>
        <InsightCard
          title="What it does"
          body={brief.what_it_does ?? detail.mechanism_summary ?? null}
          onClick={() => focus("story")}
          dataAttr="what-it-does"
        />
        <InsightCard
          title="Why it matters"
          body={brief.why_it_matters ?? null}
          onClick={() => focus("story")}
          dataAttr="why-it-matters"
        />
        <InsightCard
          title="What is established"
          body={brief.established ?? detail.maturity ?? null}
          onClick={() => focus("story")}
          dataAttr="whats-established"
        />
        <InsightCard
          title="What could kill it"
          body={
            brief.kill_condition ?? brief.decisive_experiment ?? null
          }
          onClick={() => focus("story")}
          dataAttr="what-could-kill-it"
        />
      </div>

      {/* ---- the actions ---- */}
      <div className="stage-actions" data-stage-actions>
        {detail.dossier.download && (
          <a
            className="btn primary big stage-download"
            href={detail.dossier.download}
            data-stage-package
          >
            Download the technology package
          </a>
        )}
        {detail.parameters.length > 0 && (
          <button
            type="button"
            className="btn ghost big"
            onClick={() => focus("parameters")}
          >
            Explore parameters
          </button>
        )}
        {loop?.real_event && (
          <button
            type="button"
            className="btn ghost big"
            onClick={() => focus("reality")}
          >
            Reality loop
          </button>
        )}
      </div>

      {/* ---- EVERYTHING ELSE, progressively disclosed ---- */}
      <div className="deep-dive" data-deep-dive>
        <div className="dd-head faint">
          Under the surface — the full record: every claim, every class,
          every provenance trail
        </div>

        <details className="dd-sec" data-dd-section="parameters" open={false}>
          <summary>
            <span className="dd-title">Interactive parameters</span>
            <span className="dd-sub faint">
              change a value inside its declared envelope — the real
              parametric model rebuilds in the CAD sandbox
            </span>
          </summary>
          <div className="dd-body">
            <InventionArtifact
              detail={detail}
              slot={slot}
              onPreview={(url) => {
                setPreviewGlb(url);
                setShowPreview(true);
              }}
            />
          </div>
        </details>

        <details className="dd-sec" data-dd-section="story" open={false}>
          <summary>
            <span className="dd-title">The technology story</span>
            <span className="dd-sub faint">
              from the released executive brief — the buyer chain&apos;s
              own words
            </span>
          </summary>
          <div className="dd-body">
            <InventionStory detail={detail} loop={loop} />
          </div>
        </details>

        <details className="dd-sec" data-dd-section="reality" open={false}>
          <summary>
            <span className="dd-title">Ask a question</span>
            <span className="dd-sub faint">
              answered from this technology&apos;s own records — or an
              honest refusal
            </span>
          </summary>
          <div className="dd-body">
            <AskBox
              mode="invention"
              subject={slot}
              enabled={true}
              placeholder="Ask about this technology — answered from its own record…"
            />
          </div>
        </details>
      </div>
    </div>
  );
}
