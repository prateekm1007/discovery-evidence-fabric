"use client";

// R435 — THE PRODUCT EXPERIENCE RESET: the dossier renderers.
//
// The Technology Dossier stays the canonical projection underneath
// (Art. X — every field rendered here comes from /api/run/{id}/dossier
// and the frontend never re-derives epistemic state). What changed in
// R435 is WHERE these renderers live and HOW they speak:
//
//   * they are no longer a tabbed right pane bolted beside a report —
//     they are the progressively-disclosed DEEP LAYER under the
//     technology stage (components/TechStage.tsx);
//   * the primary surface speaks product language ("What supports it",
//     "Engineering model", "generation 2") — engine vocabulary
//     (COMPUTATIONAL_RESULT, FAILED_SCIENTIFIC, ...) appears only in
//     the expandable provenance detail rows, where rigor lives;
//   * the ONE 3D viewer lives in the stage hero — these sections render
//     everything else (evolution rows swap the hero viewer via
//     onSelectGen; component chips highlight it via onHighlight).
//
// Honest states are structural (inherited from R430.1): PENDING /
// UNAVAILABLE / NOT_ESTABLISHED render their recorded reason, never a
// dead link, never a fabricated value.

import type {
  DossierBody,
  DossierTab,
  EvidenceLedgerItem,
  FalsificationRecord,
} from "@/lib/types";
import { renderAvailabilityNotice } from "@/lib/renderAvailability";
import { EpistemicBadge } from "./ScienceEvents";

// ---- render availability (R446-C2 WS3; R452 B2/B3/C7) ----------------------
// THE NOTICE MOVED: the pure string logic now lives in
// lib/renderAvailability.ts (R452) so the deterministic battery compiles
// and exercises the BEHAVIOR directly (the audit's three defects — the
// false authority claim, the silent null-status gap, the undefined
// throw — are pinned by behavior tests, not source-shape pins alone).
// The summary comment below is the change record:
// R452: the function body lives in lib/renderAvailability.ts (imported
// above) — the audit's B2 (authority-derived phrase), B3 (NOT_ATTEMPTED
// branch) and C7 (null-safe) fixes are behavior-tested in the battery.

// ---- shared types (migrated from the retired DossierPane) ------------------

type ScoreDim = {
  score?: string | null;
  passed?: boolean | null;
  failures?: string[];
};

export type EvolutionRowData = {
  generation: number;
  invention_id?: string | null;
  status?: string | null;
  status_basis?: string | null;
  why?: string | null;
  domain_family?: string | null;
  component_count?: number | null;
  glb?: string | null;
  current?: boolean;
};

export type DesignTabData = DossierTab & {
  glb?: string | null;
  geometry_class?: string | null;
  conceptual?: boolean;
  // R436 Direction 3 — the hero suppression invariant, projected by
  // the dossier (the frontend renders, never re-derives)
  hero_eligibility?: {
    eligible?: boolean;
    reason?: string | null;
    rule?: string | null;
    not_visualized?: string[];
  } | null;
  parameters?: {
    param_id?: string;
    value?: number | string;
    unit?: string;
    envelope?: [number, number] | null;
  }[];
  key_dimensions?: unknown;
  components?: (string | {
    name?: string;
    label?: string;
    role?: string;
    type?: string;
  })[];
  renders?: {
    status?: string;
    hero_png?: string;
    section_png?: string;
    exploded_png?: string;
    poster_png?: string;
    dimension_png?: string;
    orthographic?: Record<string, string>;
    turntable_frame_count?: number;
    turntable_first?: string;
    visual_gate?: {
      verdict?: string;
      hero_suppressed?: boolean;
      failed_rules?: string[];
    };
  } & Record<string, unknown>;
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
  evolution?: EvolutionRowData[] | null;
  generation_id?: string | null;
  generation_count?: number | null;
};

// ---- honest-state helpers ---------------------------------------------------

export function AvailPill({ tab }: { tab: DossierTab }) {
  const a = tab.availability;
  const label =
    a === "AVAILABLE"
      ? ""
      : a === "PENDING"
        ? "in progress"
        : a === "UNAVAILABLE"
          ? "not on this run"
          : "not established";
  if (!label) return null;
  return <span className={`avail av-${a.toLowerCase()}`}>{label}</span>;
}

export function PendingNote({ tab }: { tab: DossierTab }) {
  // An incomplete dossier is not a failure — it is an honest
  // representation of incomplete state (R430.1 sections 3/6).
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

// ---- Summary (the overview projection, product language) --------------------

export function SummarySection({
  tab,
  gauntlet,
}: {
  tab: DossierTab;
  gauntlet?: { stage: string; mark: string; label: string }[];
}) {
  const m = tab as DossierTab & {
    problem?: string;
    mechanism?: string | null;
    mechanism_generation_failed?: boolean;
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
          <div className="tech-status-h">Technology status</div>
          {m.status_line}
        </div>
      )}
      {m.problem && (
        <div className="ov-block">
          <h4>The problem</h4>
          <p>{m.problem}</p>
        </div>
      )}
      {m.mechanism && (
        <div className="ov-block">
          <h4>Proposed mechanism</h4>
          <p>{m.mechanism}</p>
        </div>
      )}
      {m.mechanism_generation_failed && !m.mechanism && (
        <div className="ov-block">
          <h4>Proposed mechanism</h4>
          <p className="faint">
            The invention generator did not produce a usable mechanism for
            the surviving generation — the run record keeps the raw field,
            and it is not presented here as the invention.
          </p>
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
                  <span className="pill small mat-early">{u.priority}</span>
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
      {(gauntlet?.length ?? 0) > 0 && (
        <div className="ov-block">
          <h4>Scientific progress</h4>
          <ul className="mini-gauntlet">
            {gauntlet!.map((g) => (
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

// ---- The technology model (design details; the viewer itself is the hero) --

export function EvolutionRow({
  row,
  active,
  onSelect,
}: {
  row: EvolutionRowData;
  active: boolean;
  onSelect: () => void;
}) {
  const status =
    row.status === "CURRENT"
      ? "Current"
      : row.status === "CHALLENGED"
        ? "Challenged"
        : "Superseded";
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
      <span className="evo-why">{row.why || "—"}</span>
      <span className="evo-meta faint">
        {row.domain_family ? `${row.domain_family.toLowerCase()} · ` : ""}
        {row.component_count != null
          ? `${row.component_count} components`
          : ""}
      </span>
    </button>
  );
}

export function ModelDetailsSection({
  tab,
  viewingGen,
  onSelectGen,
  highlight,
  onHighlight,
}: {
  tab: DossierTab;
  viewingGen: number | null;
  onSelectGen: (gen: number | null) => void;
  highlight: string | null;
  onHighlight: (id: string | null) => void;
}) {
  const d = tab as DesignTabData;
  const evo = d.evolution || [];
  const genLabel = (d.generation_id || "gen-1").replace("gen-", "");
  const genCount = d.generation_count || evo.length || 1;
  const hash = (h?: string | null) => (h ? `${h.slice(0, 12)}…` : "—");
  // R436: the deep layer explains hero suppression — when the geometry
  // did not earn the stage, the record (this section) carries the WHY
  const heroSuppressed = d.hero_eligibility?.eligible === false;

  // component selector uses the CANONICAL component IDs — the same ids
  // the GLB scene graph carries (R433 section 5); chips highlight the
  // named node in the stage hero. NOT VISUALIZED entries are surfaced.
  // R447: `name` is the stable-vocabulary GLB node id (what the
  // browser's GLTFLoader actually produces); `label` is the recorded
  // human text shown on the chip when present — match by name,
  // display the label, never the reverse (frontend truth traces to
  // the canonical backend object, Art. III/X).
  const componentIds = (d.components || [])
    .map((c) => (typeof c === "string"
      ? { name: c, label: c }
      : {
          name: (c as { name?: string })?.name || "",
          label: (c as { label?: string })?.label
            || (c as { name?: string })?.name || "",
        }))
    .filter((c): c is { name: string; label: string } => Boolean(c.name));
  const notVisualized = d.not_visualized || d.scores?.not_visualized || [];

  return (
    <div className="dtab design-tab">
      {d.fallback_basis ? (
        <div className="conceptual-note" data-fallback-disclosure>
          Technology visualization
          <div className="faint" style={{ marginTop: 4 }}>
            A domain-specific physical model could not be generated from
            the current engineering state. Conceptual architecture shown.
            <br />
            <b>Engineering geometry: not established</b>
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

      <div className="ov-block">
        <h4>{heroSuppressed ? "The model record" : "The model on stage"}</h4>
        {heroSuppressed ? (
          <p>
            The geometry on this run did not earn the technology stage —
            no substitute model is shown on the primary surface. The
            record below is the truth about what was produced and why
            it was withheld.
            <br />
            <b>Reason: </b>
            {d.hero_eligibility?.reason ||
              "semantic identity below acceptance threshold"}
          </p>
        ) : viewingGen != null ? (
          <p>
            Generation {viewingGen} (history) is on stage —{" "}
            <button
              type="button"
              className="linklike"
              onClick={() => onSelectGen(null)}
            >
              return to the current generation
            </button>
            .
          </p>
        ) : (
          <p>
            Generation {genLabel} · current
            {genCount > 1 ? ` · ${genCount} generations recorded` : ""}
            {d.domain_family
              ? ` · ${d.domain_family.toLowerCase().replace(/_/g, " ")}`
              : ""}
            .
          </p>
        )}
        <div className="faint" style={{ fontSize: 12 }}>
          {heroSuppressed
            ? "the geometry files remain part of this run's record — the scores, the components, and the suppression reason are all below"
            : "the interactive model lives on the stage above — rotate, zoom, inspect components; it is built from the same canonical CAD source the technology package carries"}
        </div>
      </div>

      {(componentIds.length > 0 || notVisualized.length > 0) && (
        <div className="ov-block">
          <h4>Components</h4>
          <div className="comp-select" data-component-selector>
            {componentIds.map((c) => (
              <button
                key={c.name}
                type="button"
                className={`chip${highlight === c.name ? " on" : ""}`}
                data-component-id={c.name}
                onClick={() => onHighlight(highlight === c.name ? null : c.name)}
                title={
                  heroSuppressed
                    ? "recorded component of the canonical architecture"
                    : highlight === c.name
                      ? "clear highlight"
                      : "highlight on stage"
                }
              >
                {c.label}
              </button>
            ))}
            {notVisualized.map((c) => (
              <span
                key={`nv-${c}`}
                className="chip nv"
                title="recorded in the canonical architecture but not present in the model"
              >
                {c} · not visualized
              </span>
            ))}
            {highlight && (
              <button
                type="button"
                className="chip clear"
                onClick={() => onHighlight(null)}
              >
                clear
              </button>
            )}
          </div>
        </div>
      )}

      {evo.length > 1 && (
        <div className="ov-block" data-evolution>
          <h4>Generation history</h4>
          <div className="evo-list">
            {evo.map((row) => (
              <EvolutionRow
                key={row.generation}
                row={row}
                active={viewingGen === row.generation}
                onSelect={() =>
                  onSelectGen(
                    viewingGen === row.generation ? null : row.generation
                  )
                }
              />
            ))}
          </div>
          <div className="faint" style={{ fontSize: 12, paddingTop: 4 }}>
            {heroSuppressed
              ? "the generation history is part of the record; the interactive stage is withheld on this run"
              : "selecting a generation puts that historical model on stage; the current generation is GEN " +
                genLabel}
          </div>
        </div>
      )}

      {d.scores && (
        <div className="ov-block" data-scores>
          <h4>Model quality — three separated scores</h4>
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
              Not visualized (canonical architecture, absent from the
              model): {notVisualized.join(", ")}
            </p>
          )}
          <div className="faint" style={{ fontSize: 12 }}>
            {d.scores.note ||
              "three separated dimensions — never combined into one score"}
          </div>
        </div>
      )}

      {d.artifact_identity && (
        <div className="ov-block" data-model-identity>
          <h4>Model identity</h4>
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
      )}

      {d.quality_gates && (
        <div className="ov-block" data-quality-gates>
          <h4>
            Geometry quality gates
            {d.quality_gates.passed ? " · passed" : " · failures recorded"}
          </h4>
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
      )}

      {(d.parameters?.length ?? 0) > 0 && (
        <div className="ov-block" data-parameters>
          <h4>Parameters · {d.parameters!.length}</h4>
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
      )}

      {d.renders?.hero_png && (
        <div className="ov-block" data-renders>
          <h4>Presentation renders</h4>
          <div className="render-row">
            <img src={d.renders.hero_png} alt="hero render" loading="lazy" />
            {d.renders.section_png && (
              <img src={d.renders.section_png} alt="section render" loading="lazy" />
            )}
            {d.renders.exploded_png && (
              <img src={d.renders.exploded_png} alt="exploded render" loading="lazy" />
            )}
          </div>
          <div className="faint" style={{ fontSize: 12 }}>
            presentation renders —{" "}
            {d.engineering_authority === "ENGINEERING" && d.conceptual !== true
              ? "the authoritative geometry is the CAD-built model on stage"
              : "the geometry on stage is the recorded conceptual " +
                "representation (no engineering CAD claim)"}{" "}
            — renders never validate physics
          </div>
        </div>
      )}

      {!d.renders?.hero_png && (
        // R452 B3: the guard no longer suppresses the notice when the
        // renders object or its status is null — the NOT_ATTEMPTED case
        // renders its own honest sentence (the "silent gap" the audit
        // measured is closed); renderAvailabilityNotice is null-safe
        // (C7), so an absent object cannot crash
        <div className="ov-block" data-render-absent>
          <h4>Presentation renders</h4>
          <div className="faint" style={{ fontSize: 13 }}>
            {renderAvailabilityNotice(d.renders, {
              engineering_authority: d.engineering_authority,
              conceptual: d.conceptual,
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ---- Evidence (the ledger) ---------------------------------------------------

export function EvidenceSection({ tab }: { tab: DossierTab }) {
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

// ---- Engineering ---------------------------------------------------------------

export function EngineeringSection({ tab }: { tab: DossierTab }) {
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

// ---- The decisive test -----------------------------------------------------------

export function ExperimentSection({ tab }: { tab: DossierTab }) {
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
  // R458-C2 (§1/BS-009): the recorded experiment renders as HUMAN PROSE
  // — what would kill the candidate, what the answer decides, and what
  // it costs (UNKNOWN stays UNKNOWN, Art. XXV). The raw recorded object
  // stays one disclosure away in the collapsed record (§15: technical
  // details remain accessible — they are just not the surface).
  const rec = (x.recorded ?? null) as
    | {
        shortlist?: {
          experiment?: string;
          source_stage?: string;
          decision_impact?: string;
          kill_probability?: string;
          cost?: string;
          time?: string;
          dependency?: string;
          is_selected_killer?: boolean;
          basis?: string;
          hypotheses?: { name?: string; description?: string }[];
        }[];
      }
    | null;
  const killer =
    rec?.shortlist?.find((s) => s.is_selected_killer) ??
    rec?.shortlist?.[0] ??
    null;
  return (
    <div className="dtab experiment-tab">
      <div className="exp-note">
        The decisive (falsification) experiment — specified, not
        executed. Executing it is a physical act this machine never
        claims (reality boundary).
      </div>
      {killer && (
        <div className="ov-block" data-experiment-prose>
          {killer.experiment && (
            <div>
              <b>Decisive test:</b> {String(killer.experiment).replace(/_/g, " ")}
            </div>
          )}
          {killer.hypotheses?.[0]?.description && (
            <div>
              <b>What it tests:</b> {killer.hypotheses[0].description}
            </div>
          )}
          {killer.decision_impact != null && (
            <div>
              <b>What the answer decides:</b>{" "}
              {typeof killer.decision_impact === "number"
                ? `decision impact ${killer.decision_impact} on the 0–1 information-gain scale`
                : String(killer.decision_impact)}
            </div>
          )}
          {killer.kill_probability != null && (
            <div>
              <b>Chance it kills the candidate:</b>{" "}
              {killer.kill_probability === "UNKNOWN"
                ? "unknown — no sourced base rate exists"
                : String(killer.kill_probability)}
            </div>
          )}
          <div>
            <b>Cost:</b> {String(killer.cost ?? "UNKNOWN").replace(/_/g, " ")} ·{" "}
            <b>Time:</b> {String(killer.time ?? "UNKNOWN").replace(/_/g, " ")}
          </div>
          {killer.dependency && (
            <div className="faint">
              Depends on: {String(killer.dependency).replace(/_/g, " ")}
            </div>
          )}
          {killer.basis && (
            <div className="faint">Basis: {killer.basis}</div>
          )}
        </div>
      )}
      {x.recorded != null && (
        <details className="dd-record" data-experiment-record>
          <summary className="faint">The recorded experiment object</summary>
          <pre className="mono-block">
            {JSON.stringify(x.recorded, null, 1).slice(0, 900)}
          </pre>
        </details>
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
                          (typeof v === "object"
                            ? JSON.stringify(v).slice(0, 120)
                            : v)
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

// ---- The technology package --------------------------------------------------------

export function PackageSection({ tab }: { tab: DossierTab }) {
  const t = tab as DossierTab & {
    download?: string | null;
    primary_action?: string;
    zip_name?: string | null;
    package_maturity?: string | null;
    package_kind?: string | null;
    document_count?: number | null;
    package_origin?: string | null;
    package_state?: string | null;
    package_blocked_stage?: string | null;
    package_blocked_reason?: string | null;
    package_next_action?: string | null;
    package_release_verdict?: string | null;
    visual_gate_verdict?: string | null;
    evidence_coverage?: { used_in_design?: number; retrieved?: number } | null;
    validation_state?: unknown;
    decisive_experiment?: string | null;
    key_unknowns?: { statement?: string; priority?: string | null }[];
    build_requirements?: unknown;
  };
  if (tab.availability !== "AVAILABLE") {
    // R447 Phase 2: a BLOCKED package is a typed terminal state from
    // the canonical object (run_state.package_terminal_state) — the
    // stage, the verbatim reason, and the typed next action are
    // rendered from the backend record, never guessed here.
    if (t.package_blocked_stage) {
      return (
        <div className="tab-note tn-not_established">
          <AvailPill tab={tab} />
          <span>
            The package build was blocked at{" "}
            <b>{t.package_blocked_stage}</b> — no package is presented
            (an honest absence, never a partial ZIP).
          </span>
          {t.package_blocked_reason && (
            <div className="faint tab-reason">
              <b>Reason:</b> {t.package_blocked_reason}
            </div>
          )}
          {t.package_next_action && (
            <div className="faint tab-reason">
              <b>Next action:</b> {t.package_next_action}
            </div>
          )}
          {t.package_release_verdict && (
            <div className="faint tab-reason">
              <b>Release verdict:</b> {t.package_release_verdict}
            </div>
          )}
        </div>
      );
    }
    return <PendingNote tab={tab} />;
  }
  return (
    <div className="dtab transfer-tab">
      {t.download && (
        <a className="btn primary big download-package" href={t.download}>
          {t.package_state === "ENGINEERING_DRAFT_VISUAL_RELEASE_PENDING"
            ? "Download engineering draft (visual release pending)"
            : (t.primary_action ?? "Download the technology package")}
        </a>
      )}
      {t.package_state === "ENGINEERING_DRAFT_VISUAL_RELEASE_PENDING" && (
        <p className="faint" style={{ fontSize: 12, marginTop: 6 }}>
          Visual gate {t.visual_gate_verdict ?? "NOT_RUN"} — this
          engineering evaluation draft contains zero visual artifacts by
          design (Article LXXII); the buyer release stays blocked until
          the visual gate passes.
        </p>
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

// ---- The honest failure record --------------------------------------------------------

export function FalsificationCard({
  f,
}: {
  f: FalsificationRecord | null | undefined;
}) {
  if (!f) return null;
  if (f.kind === "VALIDATION_INCOMPLETE") {
    return (
      <div className="falsification fi-incomplete">
        <div className="fal-h">Validation incomplete</div>
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
        <div className="fal-h">Development record</div>
        <div>{f.note}</div>
        {f.stop_reason && (
          <div className="faint">stop reason: {f.stop_reason}</div>
        )}
      </div>
    );
  }
  return (
    <div className="falsification">
      <div className="fal-h">Falsification record</div>
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

export function DossierFoot({ dossier }: { dossier: DossierBody }) {
  return <div className="dossier-foot faint">{dossier.derived_from}</div>;
}
