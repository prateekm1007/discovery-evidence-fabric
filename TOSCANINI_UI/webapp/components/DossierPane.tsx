"use client";

// R430.1 sections 2-6, 10, 14-15 + R433: the TECHNOLOGY DOSSIER — the
// right pane of the workspace. Six tabs (never the internal 16-step
// engine): Overview / Design / Evidence / Engineering / Experiment /
// Transfer.
//
// R433 — the Design tab is ONE CANONICAL TECHNOLOGY MODEL:
//   * exactly ONE primary 3D viewer (data-model-viewer, machine-counted)
//   * the header says TECHNOLOGY MODEL / GEN N · CURRENT
//   * previous generations are HISTORY (Evolution, progressive
//     disclosure); selecting one temporarily swaps the single viewer
//   * components / evolution / identity / gates live BELOW or behind
//     <details> — the first viewport is the model, not metadata
//   * the three SEPARATED quality scores (semantic identity /
//     engineering coherence / presentation quality — never combined)
//   * NOT VISUALIZED components are surfaced, never silently omitted
//
// The dossier is a PROJECTION of the canonical run state (Art. X):
// every field renders from the backend object; the frontend never
// re-derives maturity, evidence, or validation state, and never
// upgrades an epistemic class (section 8). The 3D viewer loads
// LAZILY — only when the Design tab is actually opened with geometry
// present (section 19: no three.js on the landing page).

import { useState } from "react";
import dynamic from "next/dynamic";
import type {
  DossierBody,
  DossierTab,
  EvidenceLedgerItem,
  FalsificationRecord,
  GauntletCard,
} from "@/lib/types";
import { EpistemicBadge } from "./ScienceEvents";

// Section 19: the 3D stack is NOT part of the initial page payload.
const ModelViewer = dynamic(() => import("./ModelViewer"), {
  ssr: false,
  loading: () => (
    <div className="loading">Loading the 3D viewer…</div>
  ),
});

const TABS = [
  ["overview", "Overview"],
  ["design", "Design"],
  ["evidence", "Evidence"],
  ["engineering", "Engineering"],
  ["experiment", "Experiment"],
  ["transfer", "Transfer"],
] as const;

type TabId = (typeof TABS)[number][0];

function AvailPill({ tab }: { tab: DossierTab }) {
  const a = tab.availability;
  const label =
    a === "AVAILABLE"
      ? ""
      : a === "PENDING"
        ? "pending"
        : a === "UNAVAILABLE"
          ? "unavailable"
          : "not established";
  if (!label) return null;
  return <span className={`avail av-${a.toLowerCase()}`}>{label}</span>;
}

function PendingNote({ tab }: { tab: DossierTab }) {
  // sections 3/6: an incomplete dossier is not a failure — it is an
  // honest representation of incomplete state.
  return (
    <div className={`tab-note tn-${tab.availability.toLowerCase()}`}>
      <AvailPill tab={tab} />
      <span>{tab.note}</span>
      {tab.reason && (
        <div className="faint tab-reason">
          <b>Reason:</b> {String(tab.reason)}
        </div>
      )}
    </div>
  );
}

// ---- Overview (section 5) -------------------------------------------------
function OverviewTab({
  tab,
  gauntlet,
}: {
  tab: DossierTab;
  gauntlet: GauntletCard[];
}) {
  const m = tab as DossierTab & {
    problem?: string;
    mechanism?: string | null;
    invention_state?: string | null;
    strongest_evidence?: EvidenceLedgerItem | null;
    strongest_challenge?: string | null;
    key_unknowns?: { statement?: string; priority?: string | null }[];
    decisive_experiment?: string | null;
    epistemic_status?: string;
    status_line?: string;
  };
  return (
    <div className="dtab overview-tab">
      {m.status_line && (
        <div className="tech-status">
          <div className="tech-status-h">TECHNOLOGY STATUS</div>
          {m.status_line}
        </div>
      )}
      {m.problem && (
        <div className="ov-block">
          <h4>Problem</h4>
          <p>{m.problem}</p>
        </div>
      )}
      {m.mechanism && (
        <div className="ov-block">
          <h4>Proposed mechanism</h4>
          <p>{m.mechanism}</p>
        </div>
      )}
      {m.invention_state && (
        <div className="ov-block">
          <h4>Current invention state</h4>
          <p>{m.invention_state}</p>
        </div>
      )}
      {m.strongest_evidence?.title && (
        <div className="ov-block">
          <h4>Strongest supporting evidence</h4>
          <p>
            {m.strongest_evidence.title}
            {m.strongest_evidence.source
              ? ` · ${m.strongest_evidence.source}`
              : ""}
          </p>
        </div>
      )}
      {m.strongest_challenge && (
        <div className="ov-block">
          <h4>Strongest challenge</h4>
          <p>{m.strongest_challenge}</p>
        </div>
      )}
      {m.decisive_experiment && (
        <div className="ov-block">
          <h4>Decisive experiment</h4>
          <p>{m.decisive_experiment}</p>
        </div>
      )}
      {(m.key_unknowns?.length ?? 0) > 0 && (
        <div className="ov-block">
          <h4>Key unknowns</h4>
          <ul className="unknowns">
            {m.key_unknowns!.map((u, i) => (
              <li key={i}>
                {u.statement}
                {u.priority && (
                  <span className="pill small mat-early">
                    {u.priority}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="ov-block faint">
        <h4>Epistemic status</h4>
        <p>{m.epistemic_status ?? "UNKNOWN"}</p>
        <div className="epi-row">
          epistemic class <EpistemicBadge cls={tab.epistemic_class} />
        </div>
      </div>
      {gauntlet.length > 0 && (
        <div className="ov-block">
          <h4>Scientific progress</h4>
          <ul className="mini-gauntlet">
            {gauntlet.map((g) => (
              <li key={g.stage}>
                <span aria-hidden="true">{g.mark}</span> {g.label}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// R433 section 2: one evolution row (history, not a competing
// artifact — the projection's own fields, rendered verbatim)
function EvolutionRow({
  row,
  active,
  onSelect,
}: {
  row: NonNullable<DesignTabData["evolution"]>[number];
  active: boolean;
  onSelect: () => void;
}) {
  const status = row.status === "CURRENT" ? "Current" : row.status === "CHALLENGED" ? "Challenged" : "Superseded";
  return (
    <button
      type="button"
      className={`evo-row${active ? " active" : ""}${row.current ? " current" : ""}`}
      data-generation={row.generation}
      onClick={onSelect}
      aria-pressed={active}
    >
      <span className="evo-gen">GEN {row.generation}</span>
      <span className={`evo-status st-${(row.status || "").toLowerCase()}`}>
        {status}
      </span>
      <span className="evo-why">{row.why}</span>
      <span className="evo-meta faint">
        {row.domain_family ? `${row.domain_family.toLowerCase()} · ` : ""}
        {row.component_count != null
          ? `${row.component_count} components`
          : ""}
      </span>
    </button>
  );
}

type DesignTabData = DossierTab & {
  glb?: string | null;
  geometry_class?: string | null;
  conceptual?: boolean;
  parameters?: {
    param_id?: string;
    value?: number | string;
    unit?: string;
    envelope?: [number, number] | null;
  }[];
  key_dimensions?: unknown;
  components?: (string | { name?: string; role?: string; type?: string })[];
  renders?: { hero_png?: string; section_png?: string; exploded_png?: string } & Record<
    string,
    unknown
  >;
  authority?: string;
  domain_family?: string | null;
  quality_gates?: {
    passed?: boolean;
    failures?: string[];
    note?: string;
  } | null;
  artifact_identity?: {
    technology_id?: string | null;
    run_id?: string | null;
    generation_id?: string | null;
    geometry_hash?: string | null;
    source_geometry_hash?: string | null;
    blender_scene_hash?: string | null;
    glb_matches_geometry_hash?: boolean | null;
  } | null;
  fallback_basis?: string | null;
  geometry_spec?: string | null;
  scores?: {
    semantic_identity?: ScoreDim;
    engineering_coherence?: ScoreDim;
    presentation_quality?: ScoreDim;
    not_visualized?: string[];
    note?: string;
  } | null;
  not_visualized?: string[];
  evolution?: {
    generation: number;
    invention_id?: string | null;
    status?: string | null;
    status_basis?: string | null;
    why?: string | null;
    domain_family?: string | null;
    component_count?: number | null;
    glb?: string | null;
    current?: boolean;
  }[] | null;
  generation_id?: string | null;
  generation_count?: number | null;
};

type ScoreDim = {
  score?: string | null;
  passed?: boolean | null;
  failures?: string[];
};

// ---- Design (section 6; R433: the ONE canonical technology model) --------
function DesignTab({ tab }: { tab: DossierTab }) {
  const d = tab as DesignTabData;
  if (tab.availability !== "AVAILABLE" || !d.glb) {
    // section 6 / R433 section 18: the honest unavailable block — never
    // a dead link that looks like a live model, never a misleading
    // physical-looking stand-in
    return <PendingNote tab={tab} />;
  }
  const hash = (h?: string | null) =>
    h ? `${h.slice(0, 12)}…` : "—";
  const genLabel = (d.generation_id || "gen-1").replace("gen-", "");
  const genCount = d.generation_count || d.evolution?.length || 1;

  // R433 sections 2/15: generation history is BEHIND disclosure; the
  // single primary viewer shows the CURRENT model. Selecting a
  // historical row TEMPORARILY swaps the same single viewer (the
  // count stays ONE — never several primary models at once).
  const [viewingGen, setViewingGen] = useState<number | null>(null);
  const [highlight, setHighlight] = useState<string | null>(null);
  const evo = d.evolution || [];
  const activeRow = viewingGen != null ? evo.find((r) => r.generation === viewingGen) : undefined;
  const showingHistory = Boolean(activeRow && activeRow.glb);
  const viewerUrl = showingHistory && activeRow?.glb ? activeRow.glb : d.glb;

  // the component selector uses the CANONICAL component IDs (the same
  // ids the GLB scene graph carries — R433 section 5). The bridge
  // reports components as {name, type, role} objects (canonical IDs in
  // .name); plain strings are accepted too.
  const componentIds = (d.components || [])
    .map((c) => (typeof c === "string" ? c : (c as { name?: string })?.name))
    .filter((c): c is string => Boolean(c));
  const notVisualized = d.not_visualized || d.scores?.not_visualized || [];

  return (
    <div className="dtab design-tab">
      {/* R433 section 18: the honest failure artifact — a domain-specific
          physical model could not be generated; NEVER a silent slab+boxes */}
      {d.fallback_basis ? (
        <div className="conceptual-note" data-fallback-disclosure>
          TECHNOLOGY VISUALIZATION
          <div className="faint" style={{ marginTop: 4 }}>
            A domain-specific physical model could not be generated from
            the current engineering state. Conceptual architecture shown.
            <br />
            <b>Engineering geometry: NOT ESTABLISHED</b>
          </div>
          <div className="faint" style={{ marginTop: 4 }}>
            {d.fallback_basis}
          </div>
        </div>
      ) : (
        d.conceptual && (
          <div className="conceptual-note">
            Conceptual {d.domain_family ? `${d.domain_family.toLowerCase()} ` : ""}
            architecture visualization — not engineering CAD. Engineering
            dimensions are not claimed.
          </div>
        )
      )}

      {/* R433 sections 2/14: the TECHNOLOGY MODEL header — ONE current
          model, generation identity visible, no competing artifacts */}
      <div className="tech-model-head">
        <div className="tm-title">TECHNOLOGY MODEL</div>
        <div className="tm-gen">
          {showingHistory ? (
            <>
              <span className="tm-history">GEN {viewingGen} · HISTORY</span>
              <button
                type="button"
                className="tm-return"
                onClick={() => setViewingGen(null)}
              >
                return to current →
              </button>
            </>
          ) : (
            <span className="tm-current" data-generation-current>
              GEN {genLabel} · CURRENT
            </span>
          )}
          <span className="faint tm-family">
            {d.domain_family
              ? d.domain_family.toLowerCase().replace(/_/g, " ")
              : ""}
            {genCount > 1 ? ` · ${genCount} generations recorded` : ""}
          </span>
        </div>
      </div>

      {/* sections 1/14: the ONE primary viewer — large, first, alone */}
      <div className="viewer-wrap">
        <ModelViewer
          url={viewerUrl}
          height={520}
          highlight={highlight}
          label={showingHistory
            ? `GEN ${viewingGen} historical architecture — the current model is GEN ${genLabel}`
            : d.conceptual
              ? d.domain_family && !d.fallback_basis
                ? `Conceptual ${d.domain_family.toLowerCase()} architecture — not engineering CAD`
                : "Conceptual architecture — not engineering CAD"
              : "Engineering geometry — canonical CAD source"}
        />
      </div>
      <div className="viewer-hints faint">
        rotate · zoom · pan · reset · fullscreen — the geometry comes from
        the same canonical CAD source the package carries
      </div>

      {/* R433 sections 5/14: the component selector — canonical IDs, the
          same ids the GLB scene graph carries; chips highlight the named
          node in the single viewer. NOT VISUALIZED entries are surfaced
          (section 6), never silently omitted. */}
      {(componentIds.length > 0 || notVisualized.length > 0) && (
        <div className="comp-select" data-component-selector>
          <span className="faint cs-label">components</span>
          {componentIds.map((c) => (
            <button
              key={c}
              type="button"
              className={`chip${highlight === c ? " on" : ""}`}
              data-component-id={c}
              onClick={() => setHighlight(highlight === c ? null : c)}
              title={highlight === c ? "clear highlight" : "highlight in model"}
            >
              {c}
            </button>
          ))}
          {notVisualized.map((c) => (
            <span key={`nv-${c}`} className="chip nv" title="recorded in the canonical architecture but not present in the model">
              {c} · NOT VISUALIZED
            </span>
          ))}
          {highlight && (
            <button
              type="button"
              className="chip clear"
              onClick={() => setHighlight(null)}
            >
              clear
            </button>
          )}
        </div>
      )}

      {/* R433 section 13: the three SEPARATED scores — semantic identity,
          engineering coherence, presentation quality. NEVER combined. */}
      {d.scores && (
        <details className="ov-disclose" data-scores>
          <summary>
            Model quality — three separated scores
            {d.scores.semantic_identity?.passed &&
            d.scores.engineering_coherence?.passed &&
            d.scores.presentation_quality?.passed
              ? " · all three PASS"
              : " · attention required"}
          </summary>
          <div className="ov-block">
            <div className="score-row">
              <span className="sc-name">semantic identity</span>
              <span className={`sc-val ${d.scores.semantic_identity?.passed ? "ok" : "fail"}`}>
                {d.scores.semantic_identity?.score || "—"}
              </span>
              <span className="faint sc-note">
                does the model represent the requested technology?
              </span>
            </div>
            <div className="score-row">
              <span className="sc-name">engineering coherence</span>
              <span className={`sc-val ${d.scores.engineering_coherence?.passed ? "ok" : "fail"}`}>
                {d.scores.engineering_coherence?.score || "—"}
              </span>
              <span className="faint sc-note">
                geometry corresponds to canonical components/interfaces
              </span>
            </div>
            <div className="score-row">
              <span className="sc-name">presentation quality</span>
              <span className={`sc-val ${d.scores.presentation_quality?.passed ? "ok" : "fail"}`}>
                {d.scores.presentation_quality?.score || "—"}
              </span>
              <span className="faint sc-note">
                professional visualization (structural metrics, not taste)
              </span>
            </div>
            {notVisualized.length > 0 && (
              <p className="gate-fail" style={{ fontSize: 12.5 }}>
                NOT VISUALIZED (canonical architecture, absent from the
                model): {notVisualized.join(", ")}
              </p>
            )}
            <div className="faint" style={{ fontSize: 12 }}>
              {d.scores.note ||
                "three separated dimensions — never combined into one score"}
            </div>
          </div>
        </details>
      )}

      {/* R433 sections 2/15: EVOLUTION — generation history behind
          progressive disclosure. Selecting a row swaps the SINGLE
          viewer temporarily; never several primary models at once. */}
      {evo.length > 1 && (
        <details className="ov-disclose" data-evolution>
          <summary>
            Evolution — {evo.length} generations (history)
          </summary>
          <div className="evo-list">
            {evo.map((row) => (
              <EvolutionRow
                key={row.generation}
                row={row}
                active={viewingGen === row.generation}
                onSelect={() =>
                  setViewingGen(
                    viewingGen === row.generation ? null : row.generation,
                  )
                }
              />
            ))}
          </div>
          <div className="faint" style={{ fontSize: 12, paddingTop: 4 }}>
            selecting a generation temporarily replaces the single viewer
            above with that historical model; the current model is GEN{" "}
            {genLabel}
          </div>
        </details>
      )}

      {d.artifact_identity && (
        // R432 section 20: THIS MODEL = THIS INVENTION GENERATION = THIS
        // CANONICAL GEOMETRY — the identity chain, behind disclosure
        <details className="ov-disclose" data-model-identity>
          <summary>Model identity</summary>
          <div className="ov-block">
            <table className="param-table">
              <tbody>
                <tr>
                  <td>technology</td>
                  <td>{d.artifact_identity.technology_id || "—"}</td>
                  <td className="faint">run {d.artifact_identity.run_id || "—"}</td>
                </tr>
                <tr>
                  <td>generation</td>
                  <td>{d.artifact_identity.generation_id || "—"}</td>
                  <td className="faint">
                    {d.artifact_identity.glb_matches_geometry_hash === true
                      ? "model = canonical geometry (hash verified)"
                      : d.artifact_identity.glb_matches_geometry_hash === false
                        ? "hash mismatch — see audit records"
                        : "hash verification pending"}
                  </td>
                </tr>
                <tr>
                  <td>geometry hash</td>
                  <td>{hash(d.artifact_identity.geometry_hash)}</td>
                  <td className="faint">
                    spec {hash(d.artifact_identity.source_geometry_hash)} · blender{" "}
                    {hash(d.artifact_identity.blender_scene_hash)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </details>
      )}
      {d.quality_gates && (
        <details className="ov-disclose" data-quality-gates>
          <summary>
            Geometry quality gates
            {d.quality_gates.passed ? " · passed" : " · failures recorded"}
          </summary>
          <div className="ov-block">
            <p className={d.quality_gates.passed ? "" : "gate-fail"}>
              {d.quality_gates.passed
                ? "All machine-checkable geometry and presentation gates passed " +
                  "for this artifact."
                : `Gate failures recorded: ${
                    (d.quality_gates.failures || []).join(", ")
                  } — disclosed, never hidden.`}
            </p>
            {d.quality_gates.note && (
              <div className="faint" style={{ fontSize: 12 }}>
                {d.quality_gates.note}
              </div>
            )}
          </div>
        </details>
      )}
      {(d.parameters?.length ?? 0) > 0 && (
        <details className="ov-disclose" data-parameters>
          <summary>Parameters · {d.parameters!.length}</summary>
          <div className="ov-block">
            <table className="param-table">
              <tbody>
                {d.parameters!.map((p, i) => (
                  <tr key={i}>
                    <td>{p.param_id}</td>
                    <td>
                      {String(p.value)}
                      {p.unit ? ` ${p.unit}` : ""}
                    </td>
                    <td className="faint">
                      {p.envelope
                        ? `envelope ${p.envelope[0]}–${p.envelope[1]}`
                        : "recorded value"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="faint" style={{ fontSize: 12 }}>
              parameter controls appear only when the canonical state
              declares mutable envelopes
            </div>
          </div>
        </details>
      )}
      {d.renders?.hero_png && (
        <details className="ov-disclose" data-renders>
          <summary>Presentation renders</summary>
          <div className="ov-block">
            <div className="render-row">
              <img src={d.renders.hero_png} alt="hero render" />
              {d.renders.section_png && (
                <img src={d.renders.section_png} alt="section render" />
              )}
              {d.renders.exploded_png && (
                <img src={d.renders.exploded_png} alt="exploded render" />
              )}
            </div>
            <div className="faint" style={{ fontSize: 12 }}>
              presentation renders — the authoritative geometry is the
              CAD-built GLB above; renders never validate physics
            </div>
          </div>
        </details>
      )}
    </div>
  );
}

// ---- Evidence (section 10) ------------------------------------------------
function EvidenceTab({ tab }: { tab: DossierTab }) {
  const e = tab as DossierTab & {
    items?: EvidenceLedgerItem[];
    retrieved_count?: number;
    used_count?: number;
  };
  if (tab.availability !== "AVAILABLE" || !e.items?.length) {
    return <PendingNote tab={tab} />;
  }
  const used = e.items.filter((i) => i.used_in_design);
  const unused = e.items.filter((i) => !i.used_in_design);
  return (
    <div className="dtab evidence-tab">
      <div className="ev-counts">
        <span>
          <b>{e.retrieved_count ?? e.items.length}</b> records retrieved
        </span>
        <span>
          <b>{e.used_count ?? used.length}</b> influenced the invention
        </span>
      </div>
      {used.length > 0 && (
        <>
          <h4 className="ev-group">Used in design</h4>
          <ul className="ev-list">
            {used.map((i) => (
              <li key={i.id} className="ev-item used">
                <div className="ev-title">{i.title}</div>
                <div className="ev-meta faint">
                  {i.source}
                  {i.publication_date ? ` · ${i.publication_date}` : ""}
                </div>
                <div className="ev-rel">
                  Supports the surviving design — bound in the invention
                  specification&apos;s evidence index
                </div>
                {i.source_uri && (
                  <a
                    href={i.source_uri}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="ev-link"
                  >
                    View source
                  </a>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
      {unused.length > 0 && (
        <>
          <h4 className="ev-group">Retrieved, not used</h4>
          <ul className="ev-list">
            {unused.map((i) => (
              <li key={i.id} className="ev-item">
                <div className="ev-title">{i.title}</div>
                <div className="ev-meta faint">
                  {i.source}
                  {i.publication_date ? ` · ${i.publication_date}` : ""}
                </div>
                <div className="ev-rel faint">
                  retrieved into the evidence pool; did not materially
                  influence the invention
                </div>
                {i.source_uri && (
                  <a
                    href={i.source_uri}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="ev-link"
                  >
                    View source
                  </a>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

// ---- Engineering (section 4/15) --------------------------------------------
function EngineeringTab({ tab }: { tab: DossierTab }) {
  const g = tab as DossierTab & {
    parameters?: {
      param_id?: string;
      value?: number | string;
      unit?: string;
      value_class?: string;
    }[];
    failure_modes?: unknown;
    constraints?: unknown;
    assumptions?: unknown;
    build_steps?: { step?: string; description?: string }[] | string[];
    traceability?: { coverage?: unknown; state?: string } | null;
  };
  if (tab.availability !== "AVAILABLE") {
    return <PendingNote tab={tab} />;
  }
  return (
    <div className="dtab engineering-tab">
      {(g.parameters?.length ?? 0) > 0 && (
        <div className="ov-block">
          <h4>Engineering parameters</h4>
          <table className="param-table">
            <tbody>
              {g.parameters!.map((p, i) => (
                <tr key={i}>
                  <td>{p.param_id}</td>
                  <td>
                    {String(p.value)}
                    {p.unit ? ` ${p.unit}` : ""}
                  </td>
                  <td className="faint">{p.value_class ?? "UNKNOWN"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="faint" style={{ fontSize: 12 }}>
            every value carries its recorded provenance class — unmarked
            values are UNKNOWN, never assumed
          </div>
        </div>
      )}
      {g.traceability?.state && (
        <div className="ov-block">
          <h4>Traceability</h4>
          <p>
            {g.traceability.state}
            {g.traceability.coverage != null && (
              <span className="faint">
                {" "}
                · coverage {JSON.stringify(g.traceability.coverage)}
              </span>
            )}
          </p>
        </div>
      )}
      {(g.build_steps?.length ?? 0) > 0 && (
        <div className="ov-block">
          <h4>Build steps</h4>
          <ol className="build-steps">
            {g.build_steps!.map((s, i) => (
              <li key={i}>
                {typeof s === "string" ? s : (s.description ?? s.step)}
              </li>
            ))}
          </ol>
        </div>
      )}
      {g.failure_modes != null && (
        <div className="ov-block">
          <h4>Failure modes</h4>
          <pre className="mono-block">
            {JSON.stringify(g.failure_modes, null, 1).slice(0, 600)}
          </pre>
        </div>
      )}
    </div>
  );
}

// ---- Experiment (section 15) ----------------------------------------------
function ExperimentTab({ tab }: { tab: DossierTab }) {
  const x = tab as DossierTab & {
    recorded?: unknown;
    contract?: Record<string, { status?: string; value?: unknown }> | null;
    execution_note?: string;
  };
  if (tab.availability !== "AVAILABLE") {
    return <PendingNote tab={tab} />;
  }
  const contract = x.contract ?? {};
  const fields = Object.entries(contract);
  return (
    <div className="dtab experiment-tab">
      <div className="exp-note">
        The decisive (falsification) experiment — specified, not
        executed. Executing it is a physical act this machine never
        claims (reality boundary).
      </div>
      {x.recorded != null && (
        <pre className="mono-block">
          {JSON.stringify(x.recorded, null, 1).slice(0, 900)}
        </pre>
      )}
      {fields.length > 0 && (
        <div className="ov-block">
          <h4>Buyer-runnable contract</h4>
          <table className="param-table">
            <tbody>
              {fields.map(([k, v]) => (
                <tr key={k}>
                  <td>{k}</td>
                  <td>
                    {v?.status === "NOT_DEFINED_IN_CANONICAL_STATE" ? (
                      <span className="not-defined">
                        not defined in canonical state
                      </span>
                    ) : (
                      String(
                        v?.value ??
                        (typeof v === "object" ? JSON.stringify(v).slice(0, 120) : v)
                      ).slice(0, 160)
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="faint" style={{ fontSize: 12 }}>
            every field is either derived from a named canonical record
            or explicitly NOT_DEFINED — no generic filler
          </div>
        </div>
      )}
    </div>
  );
}

// ---- Transfer (section 15) ------------------------------------------------
function TransferTab({ tab }: { tab: DossierTab }) {
  const t = tab as DossierTab & {
    download?: string | null;
    primary_action?: string;
    zip_name?: string | null;
    package_maturity?: string | null;
    package_kind?: string | null;
    document_count?: number | null;
    package_origin?: string | null;
    evidence_coverage?: { used_in_design?: number; retrieved?: number } | null;
    validation_state?: unknown;
    decisive_experiment?: string | null;
    key_unknowns?: { statement?: string; priority?: string | null }[];
    build_requirements?: unknown;
  };
  if (tab.availability !== "AVAILABLE") {
    return <PendingNote tab={tab} />;
  }
  return (
    <div className="dtab transfer-tab">
      {t.download && (
        <a className="btn primary big download-package" href={t.download}>
          {t.primary_action ?? "DOWNLOAD TECHNOLOGY PACKAGE"}
        </a>
      )}
      <div className="ov-block">
        <h4>Package</h4>
        <p>
          {t.package_kind ?? "technology transfer package"}
          {t.package_maturity ? ` · maturity ${t.package_maturity}` : ""}
          {t.document_count != null ? ` · ${t.document_count} documents` : ""}
        </p>
        {t.zip_name && <p className="faint mono">{t.zip_name}</p>}
        {t.package_origin && (
          <p className="faint" style={{ fontSize: 12 }}>
            origin: {t.package_origin}
          </p>
        )}
      </div>
      {t.evidence_coverage && (
        <div className="ov-block">
          <h4>Evidence coverage</h4>
          <p>
            {t.evidence_coverage.used_in_design ?? 0} of{" "}
            {t.evidence_coverage.retrieved ?? 0} retrieved records
            materially influenced the invention
          </p>
        </div>
      )}
      {t.validation_state != null && (
        <div className="ov-block">
          <h4>Validation state</h4>
          <pre className="mono-block">
            {JSON.stringify(t.validation_state, null, 1).slice(0, 400)}
          </pre>
        </div>
      )}
      {(t.key_unknowns?.length ?? 0) > 0 && (
        <div className="ov-block">
          <h4>Key unknowns</h4>
          <ul className="unknowns">
            {t.key_unknowns!.map((u, i) => (
              <li key={i}>{u.statement}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ---- Section 14: the honest failure dossier --------------------------------
export function FalsificationCard({
  f,
}: {
  f: FalsificationRecord | null | undefined;
}) {
  if (!f) return null;
  if (f.kind === "VALIDATION_INCOMPLETE") {
    return (
      <div className="falsification fi-incomplete">
        <div className="fal-h">VALIDATION INCOMPLETE</div>
        <div className="faint">
          The challenge could not be completed because of:
        </div>
        <div className="fal-cause">{f.cause ?? "infrastructure"}</div>
        {f.detail && <div className="fal-detail faint">{f.detail}</div>}
        <div className="fal-sci">
          Scientific conclusions: {f.scientific_conclusions ?? "NOT ESTABLISHED"}
        </div>
      </div>
    );
  }
  if (f.kind === "DEVELOPMENT_RECORD") {
    return (
      <div className="falsification fi-dev">
        <div className="fal-h">DEVELOPMENT RECORD</div>
        <div>{f.note}</div>
        {f.stop_reason && (
          <div className="faint">stop reason: {f.stop_reason}</div>
        )}
      </div>
    );
  }
  return (
    <div className="falsification">
      <div className="fal-h">FALSIFICATION DOSSIER</div>
      <ol className="fal-chain">
        <li>
          <b>Initial candidate</b>
          <div>{f.initial_candidate ?? "— see the lineage record"}</div>
        </li>
        <li>
          <b>Challenge condition</b>
          <div>{f.challenge_condition}</div>
        </li>
        <li>
          <b>Observed computational failure</b>
          <div>{f.observed_failure ?? "recorded on the run"}</div>
        </li>
        <li>
          <b>Rejected mechanism</b>
          <div>{f.rejected_mechanism ?? "—"}</div>
        </li>
        <li>
          <b>Why it failed</b>
          <div>{f.why_it_failed}</div>
        </li>
        <li>
          <b>What remains unknown</b>
          <div>{f.what_remains_unknown}</div>
        </li>
      </ol>
      <div className="faint" style={{ fontSize: 12 }}>
        auditable scientific failure — the basis is {f.basis}; nothing
        here is dramatized
      </div>
    </div>
  );
}

// ---- The pane --------------------------------------------------------------
export default function DossierPane({
  dossier,
  gauntlet,
  loading,
}: {
  dossier: DossierBody | null;
  gauntlet: GauntletCard[];
  loading?: boolean;
}) {
  const [active, setActive] = useState<TabId>("overview");
  if (loading && !dossier) {
    return (
      <aside className="dossier">
        <div className="dossier-h">Technology Dossier</div>
        <div className="loading">Hydrating the dossier…</div>
      </aside>
    );
  }
  if (!dossier) {
    return (
      <aside className="dossier">
        <div className="dossier-h">Technology Dossier</div>
        <div className="tab-note tn-pending">
          The dossier appears as soon as the investigation has a
          canonical state.
        </div>
      </aside>
    );
  }
  const tabs = dossier.tabs;
  return (
    <aside className="dossier" aria-label="technology dossier">
      <div className="dossier-h">
        Technology Dossier
        {dossier.running && (
          <span className="pill small RUNNING">
            <span className="cursor" /> live
          </span>
        )}
      </div>
      <div className="dossier-tabs" role="tablist">
        {TABS.map(([id, label]) => (
          <button
            key={id}
            role="tab"
            aria-selected={active === id}
            className={`dtab-btn ${active === id ? "active" : ""} ${
              tabs[id]?.availability === "AVAILABLE" ? "has-content" : ""
            }`}
            onClick={() => setActive(id)}
            type="button"
          >
            {label}
            {tabs[id]?.availability === "PENDING" && (
              <span className="tab-pend" aria-label="pending" />
            )}
          </button>
        ))}
      </div>
      <div className="dossier-body">
        {active === "overview" && (
          <OverviewTab tab={tabs.overview} gauntlet={gauntlet} />
        )}
        {active === "design" && <DesignTab tab={tabs.design} />}
        {active === "evidence" && <EvidenceTab tab={tabs.evidence} />}
        {active === "engineering" && (
          <EngineeringTab tab={tabs.engineering} />
        )}
        {active === "experiment" && <ExperimentTab tab={tabs.experiment} />}
        {active === "transfer" && <TransferTab tab={tabs.transfer} />}
        {dossier.falsification && (
          <FalsificationCard f={dossier.falsification} />
        )}
        <div className="dossier-foot faint">
          {dossier.derived_from}
        </div>
      </div>
    </aside>
  );
}
