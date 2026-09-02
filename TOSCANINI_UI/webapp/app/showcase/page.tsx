"use client";

// The showcase experience (R389 Phases 5/6/8): a REAL portfolio package —
// interactive 3D design, live parameter rebuilds through the deterministic
// CAD sandbox, the engineering equations, and the buyer dossier download.
//
// Honesty is part of the product: every parameter is MODELLED (declared
// envelope), rebuilds are COMPUTATIONAL_RESULT, the reconstructed-world
// viewer (when shown) carries a RECONSTRUCTED badge, and the loop state
// says exactly what has and has not been verified against reality.

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { evaluateParam, getRealityLoop, getShowcase } from "@/lib/api";
import type {
  EvalResult,
  RealityLoopRecord,
  Refusal,
  ShowcaseDetail,
  ShowcaseParam,
} from "@/lib/types";
import ModelViewer from "@/components/ModelViewer";

function ParamCard({
  slot,
  param,
  onPreview,
  activeGlb,
}: {
  slot: string;
  param: ShowcaseParam;
  onPreview: (r: EvalResult) => void;
  activeGlb: string;
}) {
  const [value, setValue] = useState<number>(
    typeof param.value === "number" ? param.value : Number(param.value) || 0
  );
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<EvalResult | null>(null);
  const [refusal, setRefusal] = useState<Refusal | null>(null);
  const [shown, setShown] = useState<string | null>(null);

  const env = param.envelope;
  const lo = env?.[0];
  const hi = env?.[1];
  const dirty =
    typeof param.value === "number" && Math.abs(value - param.value) > 1e-9;

  async function run() {
    setBusy(true);
    setRefusal(null);
    setResult(null);
    const out = await evaluateParam(slot, param.param_id, value);
    setBusy(false);
    if (out.ok) {
      setResult(out.result);
      onPreview(out.result);
    } else {
      setRefusal(out.refusal);
    }
  }

  return (
    <div className="param">
      <div className="head">
        <span className="pid">{param.param_id}</span>
        <span className="val">
          {value}
          {param.unit ? ` ${param.unit}` : ""}
        </span>
      </div>
      {lo != null && hi != null && (
        <>
          <input
            type="range"
            min={lo}
            max={hi}
            step={(hi - lo) / 100}
            value={value}
            onChange={(e) => setValue(Number(e.target.value))}
          />
          <div className="row">
            <span>declared envelope: {lo}</span>
            <span>{hi}</span>
          </div>
        </>
      )}
      <div className="row">
        <span className="class">{param.value_class ?? "MODELLED"}</span>
        <span>{param.category ?? ""}</span>
      </div>
      {param.design_basis && (
        <div className="basis">{param.design_basis}</div>
      )}
      <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
        <button
          className="btn small"
          onClick={run}
          disabled={busy || !dirty || lo == null}
          type="button"
        >
          {busy ? "Rebuilding…" : "Rebuild geometry"}
        </button>
        {result?.preview_glb && (
          <button
            className="btn small ghost"
            onClick={() => {
              const serve = result.preview_glb!.serve;
              setShown(shown === serve ? null : serve);
              onPreview({ ...result, __activate: true } as EvalResult);
            }}
            type="button"
            style={
              activeGlb === result.preview_glb?.serve
                ? { borderColor: "var(--accent)", color: "var(--accent)" }
                : undefined
            }
          >
            {activeGlb === result.preview_glb?.serve ? "viewing" : "view preview"}
          </button>
        )}
      </div>
      {refusal && (
        <div className="evalresult" style={{ borderColor: "var(--bad)" }}>
          <span className="bad">{refusal.status}</span> — {refusal.reason}
        </div>
      )}
      {result && (
        <div className="evalresult">
          <span className={result.geometry_validation?.valid ? "ok" : "bad"}>
            {result.geometry_validation?.valid
              ? "geometry valid"
              : "geometry invalid"}
          </span>{" "}
          · model <span className="mono">{result.model_id}</span>
          {result.measurements?.objects &&
            Object.entries(result.measurements.objects)
              .slice(0, 1)
              .map(([oid, dims]) => {
                const d = dims as unknown as Record<string, number>;
                const bbox = (d.bbox ?? {}) as unknown as Record<string, number>;
                return (
                  <div key={oid} style={{ marginTop: 6 }}>
                    {oid}: volume {d.volume_mm3?.toFixed(2)} mm³ ·{" "}
                    {d.bbox
                      ? `bbox ${bbox.xlen}×${bbox.ylen}×${bbox.zlen} mm`
                      : ""}
                  </div>
                );
              })}
          <div style={{ marginTop: 6, fontSize: 11.5, color: "var(--ink-faint)" }}>
            {result.honesty}
          </div>
        </div>
      )}
    </div>
  );
}

// R390: the reality-loop panel (CEO directive #6 + #8). Shows the closed
// loop — a real observation that refuted a design basis and CHANGED a
// technical decision — as part of the investor-facing narrative.
// Every label is honest: MEASURED origin is shown with its event id and
// the declared basis it refuted; nothing ever claims PHYSICAL_VALIDATION
// (Art. XXXVIII — that word is structurally absent from the whole surface).
function RealityLoopPanel({ record }: { record: RealityLoopRecord }) {
  const obs = record.observation ?? {};
  const hyp = record.causal_hypothesis ?? {};
  const dec = record.decision_change ?? {};
  const ree = record.re_evaluation ?? {};
  const mut = dec.mutation ?? {};
  const real = record.real_event;

  return (
    <div className="section">
      <h2>Reality loop</h2>
      <div className="sub">
        a real external observation confronted this design — the proof that
        an observation changed a technical decision (not a styling claim)
      </div>

      <div className="loopcard">
        <div className="loophead">
          <span className={`pill ${real ? "COMPLETE" : "RUNNING"}`}>
            {obs.origin === "MEASURED" ? "MEASURED" : "RECONSTRUCTED"}
          </span>
          <span className="pill COMPLETE">{record.loop_verification_state}</span>
          <span className="loopev">{obs.event_id}</span>
        </div>

        <div className="loopgrid">
          <div className="block">
            <h4>The observation</h4>
            <div className="kv">
              <span className="k">design basis</span>
              <span>
                {obs.design_value} mPa·s — {obs.design_declared_basis}
              </span>
              <span className="k">measured</span>
              <span>
                {obs.measured_value?.toFixed(4)} mPa·s ({obs.origin})
              </span>
              {obs.origin_caveat && (
                <>
                  <span className="k">caveat</span>
                  <span className="faint">{obs.origin_caveat}</span>
                </>
              )}
              <span className="k">discrepancy</span>
              <span>
                {(obs.relative_delta ?? 0) * 100 > 0 ? "+" : ""}
                {((obs.relative_delta ?? 0) * 100).toFixed(1)}% vs declared
                ±{((obs.declared_uncertainty ?? 0) * 100).toFixed(0)}% —{" "}
                <b className="bad">{obs.status}</b>
              </span>
            </div>
          </div>

          <div className="block">
            <h4>The decision it changed</h4>
            <div className="kv">
              <span className="k">before</span>
              <span>{dec.before}</span>
              <span className="k">after</span>
              <span>
                <b>{dec.after}</b>
              </span>
              <span className="k">canonical package</span>
              <span>
                {mut.applied_to_canonical_package
                  ? "mutated"
                  : "untouched — recorded as a V2-class design decision with full provenance"}
              </span>
            </div>
          </div>
        </div>

        <div className="loopquote">{hyp.statement}</div>

        <div className="block">
          <h4>Re-evaluated technical result</h4>
          <div className="kv">
            <span className="k">conductance (design basis)</span>
            <span>
              {ree.before?.G_ml_min_mmHg?.toExponential(3)}{" "}
              mL/(min·mmHg)
            </span>
            <span className="k">as-built at old geometry</span>
            <span>
              {ree.as_built?.G_ml_min_mmHg?.toExponential(3)} — the
              over-drainage guard miscalibration the observation exposed
            </span>
            <span className="k">after rebuild (measured basis)</span>
            <span>
              <b>{ree.after?.G_ml_min_mmHg?.toExponential(3)}</b> — restored
              ratio {ree.restored_ratio?.toFixed(4)}
            </span>
          </div>
        </div>

        {dec.technical_result && (
          <div className="evalresult">{dec.technical_result}</div>
        )}

        {hyp.residual_unknown && (
          <div className="block">
            <h4>What is still unknown</h4>
            <ul>
              <li>{hyp.residual_unknown}</li>
            </ul>
          </div>
        )}

        {(record.causal_chain?.stages?.length ?? 0) > 0 && (
          <div className="chainpills">
            {(record.causal_chain?.stages ?? []).map((s) => (
              <span className="chainpill" key={s}>
                {s}
              </span>
            ))}
          </div>
        )}

        <div className="basis" style={{ marginTop: 12 }}>
          {record.honesty}
          {record.causal_chain?.recorded_in_canonical_ledger
            ? " Causal chain recorded in the append-only mutation ledger."
            : ""}
        </div>
      </div>
    </div>
  );
}

export default function ShowcasePage() {
  return (
    <Suspense fallback={<div className="loading">Loading package…</div>}>
      <ShowcasePageInner />
    </Suspense>
  );
}

function ShowcasePageInner() {
  const slot = useSearchParams().get("slot") ?? "";
  const [detail, setDetail] = useState<ShowcaseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeGlb, setActiveGlb] = useState<string | null>(null);
  const [loop, setLoop] = useState<RealityLoopRecord | null>(null);

  useEffect(() => {
    getShowcase(slot)
      .then((d) => {
        setDetail(d);
        setActiveGlb(d.model.glb);
      })
      .catch((e) =>
        setError(e instanceof Error ? e.message : "failed to load package")
      );
    getRealityLoop(slot).then(setLoop).catch(() => setLoop(null));
  }, [slot]);

  if (error) return <main><div className="errbox">{error}</div></main>;
  if (!detail) return <main><div className="loading">Loading package…</div></main>;

  const baseGlb = detail.model.glb;
  const brief = detail.brief ?? {};
  const ecc = detail.evidence_class_counts ?? {};

  return (
    <main className="runpage">
      {/* ---------------- TITLE ---------------- */}
      <div className="problem">
        <div className="label">
          {detail.package_id} · technology package · from the certified
          buyer-distribution chain
        </div>
        <div className="text" style={{ fontFamily: "var(--serif)", fontSize: 22 }}>
          {detail.title}
        </div>
      </div>

      {/* ---------------- WHAT IT DOES ---------------- */}
      {(brief.what_it_does || detail.mechanism_summary) && (
        <section className="section briefsec">
          <h2>What it does</h2>
          <div className="sub">from the released executive brief</div>
          {brief.what_it_does && (
            <p className="brieflead">{brief.what_it_does}</p>
          )}
          {detail.mechanism_summary && (
            <p className="briefbody">
              <b>The engineering model:</b> {detail.mechanism_summary}
            </p>
          )}
        </section>
      )}

      {/* ---------------- WHY IT MATTERS ---------------- */}
      {brief.why_it_matters && (
        <section className="section briefsec">
          <h2>Why it matters</h2>
          <div className="sub">the recorded problem, with its sources</div>
          <p className="briefbody">{brief.why_it_matters}</p>
        </section>
      )}

      {/* ---------------- 3D MODEL ---------------- */}
      {activeGlb && (
        <ModelViewer
          url={activeGlb}
          label={`${detail.package_id}${activeGlb === baseGlb ? " · released geometry" : " · preview rebuild"}`}
          note={
            activeGlb === baseGlb
              ? "the released engineering geometry — rotate, zoom, pan, wireframe"
              : "a preview rebuild from your parameter change — deterministic CAD sandbox, COMPUTATIONAL_RESULT, the released package is untouched"
          }
        />
      )}

      {/* ---------------- KEY TECHNICAL RESULT ---------------- */}
      {(detail.maturity || brief.established) && (
        <section className="section briefsec">
          <h2>Key technical result</h2>
          <div className="sub">what is actually established</div>
          <div className="resultgrid">
            {detail.maturity && (
              <span className="pill COMPLETE">{detail.maturity}</span>
            )}
            {detail.loop_verification_state && (
              <span className="pill RUNNING">
                loop state: {detail.loop_verification_state}
              </span>
            )}
          </div>
          {brief.established && (
            <p className="briefbody">{brief.established}</p>
          )}
        </section>
      )}

      {/* ---------------- EVIDENCE ---------------- */}
      {(Object.keys(ecc).length > 0 || brief.established) && (
        <section className="section briefsec">
          <h2>Evidence</h2>
          <div className="sub">honest evidence classes — nothing hidden</div>
          <div className="chainpills">
            {Object.entries(ecc).map(([cls, n]) => (
              <span className={`chainpill ${cls === "PHYSICAL_OBSERVATION" && n === 0 ? "" : ""}`} key={cls}>
                {cls.replace(/_/g, " ")}: {String(n)}
              </span>
            ))}
          </div>
          <p className="brieffoot">
            Every claim traces to its recorded evidence span. The full
            evidence summary, traceability records, and each source citation
            are inside the downloadable package.
          </p>
        </section>
      )}

      {/* ---------------- WHAT COULD KILL IT ---------------- */}
      {(brief.kill_condition || brief.not_established) && (
        <section className="section briefsec">
          <h2>What could kill it</h2>
          <div className="sub">stated before you buy — the design&apos;s own recorded kill condition</div>
          {brief.kill_condition && (
            <div className="killbox">
              <b>Kill condition:</b> {brief.kill_condition}
            </div>
          )}
          {brief.not_established && (
            <p className="briefbody">{brief.not_established}</p>
          )}
          {(detail.known_blockers ?? []).length > 0 && (
            <details className="tech">
              <summary>All recorded blockers and unknowns</summary>
              <ul>
                {(detail.known_blockers ?? []).map((b, i) => (
                  <li key={i}>{b}</li>
                ))}
              </ul>
            </details>
          )}
        </section>
      )}

      {/* ---------------- DECISIVE EXPERIMENT ---------------- */}
      {(brief.decisive_experiment || detail.first_decisive_work_package?.work_package) && (
        <section className="section briefsec">
          <h2>Decisive experiment</h2>
          <div className="sub">the first thing the buyer runs — it can falsify the mechanism</div>
          {brief.decisive_experiment && (
            <p className="brieflead">{brief.decisive_experiment}</p>
          )}
          {detail.first_decisive_work_package?.recorded_effort && (
            <p className="brieffoot">
              Recorded effort: {detail.first_decisive_work_package.recorded_effort}
            </p>
          )}
        </section>
      )}

      {/* ---------------- DOWNLOAD PACKAGE ---------------- */}
      <div className="download-cta">
        <div className="msg">
          <h3>Technology package</h3>
          <p>
            {detail.dossier.pdfs.length} buyer documents — executive brief,
            technology-transfer dossier, buyer decision card, evidence
            summary, transfer manifest, traceability, and the 3D model
            bundle. Loop state: {detail.loop_verification_state ?? "NONE"}{" "}
            (honest — no physical validation is claimed).
          </p>
        </div>
        <a className="btn download" href={detail.dossier.download}>
          Download technology package
        </a>
      </div>

      {loop && <RealityLoopPanel record={loop} />}

      {/* ---------------- technical inspection (secondary) ---------------- */}
      <details className="tech tech-wide" open={false}>
        <summary>
          Technical inspection — live parameters, equations, dimensions
        </summary>
        <div className="techbody">
          <div className="sub" style={{ marginTop: 14 }}>
            change a parameter inside its declared envelope — the real
            parametric model rebuilds in the engine&apos;s deterministic CAD
            sandbox and the geometry re-validates
          </div>
          <div className="params">
            {detail.parameters.map((p) => (
              <ParamCard
                key={p.param_id}
                slot={slot}
                param={p}
                activeGlb={activeGlb ?? ""}
                onPreview={(r) => {
                  if ((r as EvalResult & { __activate?: boolean }).__activate) {
                    setActiveGlb(r.preview_glb?.serve ?? activeGlb);
                  }
                }}
              />
            ))}
          </div>

          {detail.equations.length > 0 && (
            <div className="section" style={{ marginTop: 34 }}>
              <h2>Engineering equations</h2>
              <div className="sub">
                the closed-form relations bound to this design
              </div>
              <div className="params">
                {detail.equations.map((e, i) => (
                  <div className="param" key={i}>
                    <div className="pid" style={{ fontSize: 14 }}>
                      {e.expression}
                    </div>
                    {e.caption && (
                      <div className="basis" style={{ marginTop: 6 }}>
                        {e.caption}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {Object.keys(detail.key_dimensions).length > 0 && (
            <div className="section" style={{ marginTop: 34 }}>
              <h2>Key dimensions</h2>
              <div className="sub">
                independently re-measured from the geometry (computation log)
              </div>
              <div className="grid2">
                {Object.entries(detail.key_dimensions).map(([oid, dims]) => {
                  const d = dims as Record<string, unknown>;
                  const bbox = (d.bbox ?? {}) as Record<string, number>;
                  return (
                    <div className="block" key={oid}>
                      <h4>{oid}</h4>
                      <div className="kv">
                        <span className="k">volume</span>
                        <span>{String(d.volume_mm3)} mm³</span>
                        <span className="k">bbox</span>
                        <span>
                          {bbox.xlen}×{bbox.ylen}×{bbox.zlen} mm
                        </span>
                        <span className="k">min wall</span>
                        <span>{String(d.min_wall_thickness_mm ?? "—")} mm</span>
                        <span className="k">valid solid</span>
                        <span>{String(d.is_valid_solid)}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <p className="brieffoot" style={{ marginTop: 26 }}>
            {detail.provenance_note}{" "}
            {brief.source ? ` Brief sections extracted verbatim from ${brief.source}.` : ""}
          </p>
        </div>
      </details>

      <div className="backrow">
        <a href="/">← all packages</a>
      </div>
    </main>
  );
}
