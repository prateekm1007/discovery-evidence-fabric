"use client";

// R395: the workspace's right pane for a RUN — the live artifact card
// while the engine works, then the honest terminal card: package
// download when one was produced, the honest no-package explanation
// when not (a real result, never a failure of the product).
//
// R414 (directive §12-14): the terminal card renders the CANONICAL
// INVENTION OBJECT — one object, one source of truth. The 3D viewer
// appears only when the CIO's geometry actually exists (never inferred
// from anything else); the reality-status badges are CIO FIELDS
// (DESIGNED / SIMULATED / EVIDENCE-SUPPORTED / EXPERIMENTALLY
// VERIFIED), never frontend inventions. R423A Phase 3: ONE package —
// the technology transfer package is the single customer deliverable
// (no separate counsel export; Toscanini is not a patent court).
//
// R416 (Phase H): each invention GENERATION gets its own geometry
// artifact (model-001.glb, model-002.glb, …) — the user moves through
// GEN 1 / GEN 2 / GEN 3 / CURRENT with the "What changed?" panel. The
// models are served per generation by /api/run/{id}/model?gen=N; the
// UI never infers an invention exists because a GLB exists.

import { useState } from "react";
import type { CIO, GenerationRecord, SessionDetail } from "@/lib/types";
import { isTerminal } from "./RunNarrative";
import ModelViewer from "./ModelViewer";
import RenderGallery from "./RenderGallery";

const MATURITY_STEPS: {
  key: "design" | "simulation" | "evidence_supported" | "experimentally_verified";
  label: string;
}[] = [
  { key: "design", label: "DESIGNED" },
  { key: "simulation", label: "SIMULATED" },
  { key: "evidence_supported", label: "EVIDENCE-SUPPORTED" },
  {
    key: "experimentally_verified",
    label: "EXPERIMENTALLY VERIFIED",
  },
];

function MaturityBadges({ cio }: { cio: CIO }) {
  const m = cio.maturity;
  if (!m) return null;
  return (
    <div className="maturity-row" aria-label="reality status">
      {MATURITY_STEPS.map((s) => {
        const on = Boolean(m[s.key]);
        return (
          <span
            key={s.key}
            className={`maturity ${on ? "on" : "off"}`}
            title={
              m.maturity_basis?.[s.key] ??
              (on ? "established by the run's own artifacts" : "not established on this run")
            }
          >
            {s.label}
          </span>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// R422 (directive 3 — the Technology Package Downloads block): the ZIP is
// the actual licensable asset, so it is the FIRST, most prominent download
// in the Artifact panel — same markup and label as the released-invention
// page ("Technology package (ZIP)") so a buyer moving between surfaces
// recognizes the same asset class. GLB/STEP/STL are secondary chips. The
// document count is the package manifest's OWN count — never hardcoded.
// The honest-tier note is always shown: rendering completeness never
// implies buyer-readiness (invention existence, maturity, and
// buyer-release are separate states).
// ---------------------------------------------------------------------------
// R423A Phase 3 — ONE package: the technology transfer package is
// the single customer deliverable. The buyer-vs-bridge product split
// is gone from the UI (the honest maturity label stays); the separate
// "Prepare for IP counsel" export is removed (its content rides inside
// the one package; Toscanini is not a patent court).
function PackageDownloads({
  detail,
  zipHref,
  packageKind,
  docCount,
  maturity,
  geometry,
  packageOrigin,
}: {
  detail: SessionDetail;
  zipHref: string;
  packageKind?: string | null;
  docCount?: number | null;
  maturity?: string | null;
  geometry?: CIO["geometry"];
  packageOrigin?: string | null;
}) {
  const glb = geometry?.glb ?? `/api/run/${detail.session_id}/model`;
  const step = geometry?.step?.[0];
  const stl = geometry?.stl?.[0];
  return (
    <div className="artifact-dls">
      <div className="rail-h">Downloads</div>
      <a className="btn download artifact-dl" href={zipHref}>
        Download technology package
      </a>
      <div className="dl-row">
        <a className="dl-chip" href={glb}>
          GLB · 3D
        </a>
        {step && (
          <a className="dl-chip" href={step}>
            STEP · CAD
          </a>
        )}
        {stl && (
          <a className="dl-chip" href={stl}>
            STL · print
          </a>
        )}
      </div>
      {docCount ? (
        <div className="faint" style={{ fontSize: 11.5, marginTop: 6 }}>
          {docCount} documents inside the ZIP — executive brief, engineering
          dossier, buyer decision card, evidence summary, transfer
          manifest, plus machine-readable layers (traceability, equation
          registry, unknown roadmap, validation economics)
          {maturity ? ` · maturity: ${String(maturity).replace(/_/g, " ").toLowerCase()}` : ""}
        </div>
      ) : null}
      <div className="faint" style={{ fontSize: 11.5, marginTop: 2 }}>
        the single deliverable for this technology — its maturity label is the
        honest state{packageOrigin === "BUYER_RELEASE_CHAIN"
          ? "; this one came from the certified release chain"
          : "; invention existence, maturity and buyer-readiness are separate states"}
      </div>
    </div>
  );
}

function CioPanel({ cio, detail }: { cio: CIO; detail: SessionDetail }) {
  const geo = cio.geometry;
  const downloads = cio.downloads ?? {};
  const languageQuarantined = cio.language_guard?.clean === false;
  const conceptual = geo?.conceptual ?? false;
  const geoClass = geo?.class ?? (conceptual ? "CONCEPTUAL_3D" : "ENGINEERING_3D");
  // R419 section 12: text↔component linkage — the selected component
  // highlights in the viewer (presentation only; the GLB is unchanged)
  const [highlight, setHighlight] = useState<string | null>(null);
  const components = geo?.components ?? [];
  return (
    <>
      <MaturityBadges cio={cio} />

      {geo?.present && geo.glb ? (
        <div className="artifact-3d">
          {/* R418 (operator §8): the artifact pane labels WHAT the model
              is — engineering geometry vs conceptual architecture —
              from the CIO's own class field, never inferred. */}
          <div className={`geo-class-chip ${conceptual ? "conceptual" : "engineering"}`}>
            {conceptual ? "CONCEPTUAL ARCHITECTURE" : "ENGINEERING MODEL"}
            <span className="faint" style={{ marginLeft: 8, fontSize: 10.5 }}>
              {geoClass} · CadQuery/OCCT
            </span>
          </div>
          <ModelViewer
            url={geo.glb}
            height={300}
            compact
            highlight={highlight}
            label={conceptual ? "conceptual architecture" : "run geometry"}
            note={conceptual
              ? "the invention's system architecture as an explicitly conceptual 3D visualization — topology and named components, NOT engineering geometry; engineering CAD is earned only when parameters are sourced"
              : "the run's engineering geometry (CadQuery/OCCT authority; renders are derived artifacts — never physical truth)"}
          />
          {components.length > 0 && (
            <div className="component-panel">
              <div className="rail-h">
                Components
                <span className="faint" style={{ marginLeft: 6, fontSize: 10.5 }}>
                  click to isolate in the viewer
                </span>
              </div>
              <div className="component-list">
                {components.slice(0, 12).map((c, i) => {
                  const name =
                    typeof c === "string" ? c : (c?.name ?? `component ${i + 1}`);
                  const role =
                    typeof c === "string" ? null : (c?.role ?? c?.type ?? null);
                  return (
                    <button
                      key={`${name}-${i}`}
                      type="button"
                      className={`component-chip ${
                        highlight === name ? "sel" : ""
                      }`}
                      title={role ?? undefined}
                      onClick={() =>
                        setHighlight(highlight === name ? null : name)
                      }
                    >
                      {name}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
          {conceptual && (
            <div className="faint" style={{ fontSize: 11.5, marginTop: 4 }}>
              no engineering dimensions are claimed by this artifact —
              components mirror the recorded subsystem names
            </div>
          )}
          {/* R419 sections 5/8: the studio render gallery (hero/section/
              exploded) — pointers from the CIO's visualization.renders
              only; presentation variants, honestly labeled */}
          <RenderGallery
            renders={cio.visualization?.renders}
            conceptual={conceptual}
          />
          {(() => {
            const r = cio.visualization?.renders;
            if (!r || !r.status || r.status === "OK" ||
                r.status === "RENDER_PARTIAL" || r.hero_png) return null;
            return (
              <div className="faint" style={{ fontSize: 11.5, marginTop: 4 }}>
                studio renders unavailable on this run ({r.status.toLowerCase().replace(/_/g, " ")})
                — the interactive 3D above is the artifact
              </div>
            );
          })()}
        </div>
      ) : (
        <div className="artifact-note">
          {/* R418 (operator §4): the backend must answer WHY. The only
              remaining no-3D states are honest failures of the bridge
              itself — disclosed with their recorded reason, never the
              old blanket "No 3D on this run." */}
          <b>Visual artifact unavailable.</b>{" "}
          {geo?.bridge_why ? (
            <span>
              {geo.bridge_outcome === "BRIDGE_GEOMETRY_FAILED"
                ? "The automatic 3D bridge attempted generation, failed after diagnosis and repair, and recorded every attempt — an engine defect, not an honest absence. "
                : ""}
              Recorded reason: {geo.bridge_why}
            </span>
          ) : geo?.bridge_outcome === "BRIDGE_GEOMETRY_FAILED" ? (
            "The automatic 3D bridge attempted generation, failed after diagnosis and repair, and recorded every attempt — the failure record is in the run directory."
          ) : geo?.parametric_model_present ? (
            "A parametric model was produced but no exported mesh — design is DESIGNED, the 3D export was not reached."
          ) : (
            "No visual artifact was produced for this invention — the bridge gate recorded its reason (an implementation failure by the product contract, disclosed honestly)."
          )}
        </div>
      )}

      {(geo?.step?.length ?? 0) > 0 && (
        <div className="dl-row">
          {(geo?.step ?? []).slice(0, 2).map((s) => (
            <a key={s} className="btn ghost small" href={s}>
              STEP
            </a>
          ))}
          {(geo?.stl ?? []).slice(0, 2).map((s) => (
            <a key={s} className="btn ghost small" href={s}>
              STL
            </a>
          ))}
        </div>
      )}

      {downloads.package_zip ? (
        <PackageDownloads
          detail={detail}
          zipHref={downloads.package_zip}
          packageKind={downloads.package_kind}
          docCount={downloads.document_count}
          maturity={downloads.package_maturity}
          geometry={geo}
          packageOrigin={downloads.package_origin}
        />
      ) : (
        <div className="artifact-note">
          <b>Package not produced on this run.</b> The bridge gate
          recorded the reason on the run record — an implementation
          state, disclosed (never “earned by survival” language again:
          the invention exists above with its honest maturity).
        </div>
      )}

      {cio.simulation?.executed && (
        <div className="artifact-note">
          <b>Simulation:</b>{" "}
          {String(cio.simulation.lifecycle_verdict ?? "").replace(/_/g, " ").toLowerCase()}{" "}
          · baseline {String(cio.simulation.baseline_outcome ?? "?").replace(/_/g, " ").toLowerCase()}{" "}
          — <span className="faint">COMPUTATIONAL_RESULT, never a physical observation</span>
        </div>
      )}

      {languageQuarantined && (
        <div className="errbox" style={{ marginTop: 10 }}>
          Narrative quarantined: model-generated text carried language the
          product surface must not assert (patentability). The
          deterministic record is unaffected.
        </div>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// R416 (Phase H): the generation navigator — GEN 1 / GEN 2 / GEN 3 /
// CURRENT. Each generation loads its own GLB (model-00N.glb) and shows
// "What changed?" — the causal delta from the lineage record, never
// client-side inference.
// ---------------------------------------------------------------------------
function GenerationNavigator({
  detail,
  generations,
  currentGen,
}: {
  detail: SessionDetail;
  generations: GenerationRecord[];
  currentGen?: number | null;
}) {
  const withModels = generations.filter((g) => g.model_available);
  const [selected, setSelected] = useState<number>(
    currentGen ?? withModels[withModels.length - 1]?.gen ?? generations[0]?.gen ?? 1
  );
  const gen = generations.find((g) => g.gen === selected) ?? generations[0];
  const hasModel = withModels.some((g) => g.gen === selected);
  const modelUrl = `/api/run/${detail.session_id}/model?gen=${selected}`;

  return (
    <div className="gen-nav">
      <div className="gen-nav-tabs" role="tablist" aria-label="invention generations">
        {generations.map((g) => {
          const isCurrent = currentGen != null && g.gen === currentGen;
          return (
            <button
              key={g.gen}
              type="button"
              role="tab"
              aria-selected={g.gen === selected}
              className={`gen-tab ${g.gen === selected ? "sel" : ""} ${
                g.challenge?.killed ? "dead" : g.challenge?.survived ? "ok" : ""
              }`}
              onClick={() => setSelected(g.gen)}
            >
              GEN {g.gen}
              {isCurrent ? " · CURRENT" : ""}
            </button>
          );
        })}
      </div>

      <div className="gen-view">
        {hasModel ? (
          <>
            <ModelViewer
              url={modelUrl}
              height={280}
              compact
              label={`architecture ${selected} geometry`}
              note={`model-${String(selected).padStart(3, "0")}.glb — this generation's own geometry artifact (CadQuery/OCCT authority; a render is a derived artifact, never physical truth)`}
            />
            <div className="faint" style={{ fontSize: 11, marginTop: 3 }}>
              conceptual system architecture when no engineering
              parameters are sourced — the class is labeled on the
              invention object, never inferred from the mesh
            </div>
          </>
        ) : (
          <div className="artifact-note">
            <b>GEN {selected} has no 3D model.</b>{" "}
            {gen?.challenge?.killed
              ? "This architecture was challenged before its engineering realization — no geometry was built (recorded, never a placeholder)."
              : "No visual artifact was produced for this generation — the bridge gate recorded its reason on the run record (an implementation state by the product contract, disclosed)."}
          </div>
        )}

        {gen?.what_changed && (
          <div className="gen-what-changed">
            <div className="rail-h">What changed?</div>
            <div>{gen.what_changed}</div>
            {gen.causal_delta?.new_capability && (
              <div className="faint" style={{ fontSize: 12, marginTop: 4 }}>
                New capability: {gen.causal_delta.new_capability}
              </div>
            )}
            {gen.causal_delta?.new_interaction && (
              <div className="faint" style={{ fontSize: 12, marginTop: 2 }}>
                New interaction: {gen.causal_delta.new_interaction}
              </div>
            )}
            {gen.causal_delta?.new_operating_regime && (
              <div className="faint" style={{ fontSize: 12, marginTop: 2 }}>
                New operating regime: {gen.causal_delta.new_operating_regime}
              </div>
            )}
            {gen.causal_delta?.frontier_capability && (
              <div className="faint" style={{ fontSize: 12, marginTop: 2 }}>
                Frontier transfer: {gen.causal_delta.frontier_capability}
              </div>
            )}
            {gen.reason_for_change && (
              <div className="faint" style={{ fontSize: 12, marginTop: 4 }}>
                Why: {gen.reason_for_change}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function RunArtifact({
  detail,
  cio,
  cioLoading,
  packageAvailable,
  onRetry,
}: {
  detail: SessionDetail;
  cio: CIO | null;
  cioLoading: boolean;
  packageAvailable: boolean;
  onRetry: (id: string) => void;
}) {
  const usv = detail.user_state_view;
  const done = isTerminal(detail.status);
  const stages = detail.stages ?? [];
  const pkg = detail.package ?? null;
  const runState = detail.run_state;
  const generations = runState?.generations?.generations ?? [];
  const currentGen = runState?.generations?.current_invention?.gen;

  // R422: the CIO is fetched by the WORKSPACE (app/page.tsx) once the run
  // is terminal, so every package-availability assertion on the page —
  // the Reality row, the outcome banner, and this panel — derives from
  // the SAME fresh object (one source of truth, never two that can
  // disagree; see the UI copy reconciliation note in page.tsx).

  const pillClass = usv
    ? usv.user_state.startsWith("COMPLETED")
      ? "COMPLETE"
      : usv.user_state.startsWith("FAILED") ||
          usv.user_state === "INTERRUPTED" ||
          usv.user_state === "BLOCKED_TRANSPORT"
        ? "ERROR"
        : "RUNNING"
    : detail.status.startsWith("ERROR") ||
        detail.status.startsWith("RUN_BLOCKED")
      ? "ERROR"
      : detail.status;

  return (
    <div className="artifact">
      <div className="artifact-h">Artifact</div>
      {!done && (
        <>
          <div className="artifact-live">
            <div className="spinner" />
            <div>
              <div className="artifact-state">{usv?.label ?? "Running"}</div>
              <div className="faint" style={{ fontSize: 12.5 }}>
                {stages.length} of 16 engine steps recorded — the design
                and package will appear here when the run finishes
              </div>
            </div>
          </div>
          <div className="artifact-note">
            Toscanini investigates with real evidence retrieval, adversarial
            attacks, and honest gates. Runs take minutes — you can leave
            and come back.
          </div>
        </>
      )}

      {done && usv && (
        <>
          <div className={`pill ${pillClass}`}>{usv.outcome_label ?? usv.label}</div>
          <div className="artifact-decision">{usv.decision}</div>
          <div className="artifact-meaning faint">{usv.meaning}</div>

          {generations.length > 0 && (
            <GenerationNavigator
              detail={detail}
              generations={generations}
              currentGen={currentGen}
            />
          )}

          {cio?.present ? (
            <CioPanel cio={cio} detail={detail} />
          ) : packageAvailable ? (
            /* R422 (directive 3): the package exists (run-record truth)
               even though the CIO view is absent — the polished Downloads
               block, NOT a bare button. The ZIP is the first, most
               prominent download; the count comes from the package's own
               records. */
            <PackageDownloads
              detail={detail}
              zipHref={`/api/run/${detail.session_id}/package`}
              packageKind={pkg?.package_kind}
              docCount={pkg?.document_count}
              maturity={pkg?.maturity}
              packageOrigin={pkg?.package_origin}
            />
          ) : cioLoading ? null /* never flash "artifacts pending" while a
               package may still resolve — the CIO fetch decides */ : usv.found_something ? (
            <div className="artifact-note">
              <b>Invention recorded, artifacts pending.</b> This run
              recorded an invention; the automatic artifact
              gate ({detail.status === "COMPLETE" ? "ran" : "will run"})
              on completion — if this persists, the bridge gate recorded
              its failure reason on the run record (disclosed, never a
              silent gap).
            </div>
          ) : (
            <div className="artifact-note">
              <b>No invention on this run.</b> The problem was
              investigated honestly and nothing defensible was found —
              the generations above carry what was tried, what killed
              each architecture, and what was learned (negative
              knowledge is kept).
            </div>
          )}

          {/* R422 (directive 1 — the reconciler): the completion-time
              snapshot above can predate the async artifact gate. When the
              summary text said no package and one now exists, ONE calm
              disclosure prevents the two texts from fighting — the run
              record itself is never edited (presentation-only). */}
          {packageAvailable &&
            usv.package_available === false &&
            !cio?.present && (
              <div className="artifact-note">
                The technology transfer package was produced by the automatic
                artifact gate after the run completed — the run summary
                above was recorded at completion. The package below is
                the current state.
              </div>
            )}

          {(detail.status.startsWith("ERROR") ||
            detail.status.startsWith("RUN_BLOCKED") ||
            detail.status === "INTERRUPTED") && (
            <div className="errbox" style={{ marginTop: 12 }}>
              <b>{detail.status.startsWith("RUN_BLOCKED")
                ? "Blocked by infrastructure — not a verdict"
                : detail.status}</b>{" "}
              — {detail.error ?? "unknown error"}
              <div style={{ marginTop: 10 }}>
                <button
                  className="btn ghost small"
                  onClick={() => onRetry(detail.session_id)}
                  type="button"
                >
                  {detail.status.startsWith("RUN_BLOCKED")
                    ? "Resume the run — problem saved"
                    : "Retry through the same worker path"}
                </button>
              </div>
            </div>
          )}
        </>
      )}

      <div className="artifact-explore">
        <div className="rail-h">Explore released inventions</div>
        <div className="faint" style={{ fontSize: 12.5 }}>
          the 15 finished technology packages — interactive 3D designs,
          live parameters, buyer dossiers — in the left rail
        </div>
      </div>
    </div>
  );
}
