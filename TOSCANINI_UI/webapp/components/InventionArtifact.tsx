"use client";

// R395 + R435: the parameter/downloads/dimensions panel for a RELEASED
// INVENTION. The interactive 3D viewer itself now lives in the stage
// hero (components/InventionStage.tsx) — this panel carries the live
// parameter rebuilds through the deterministic CAD sandbox with real
// re-measured geometry, the downloadable STEP/STL/GLB geometry, the
// buyer dossier, and re-measured key dimensions. The released package
// bytes are never modified (Art. IX); rebuilds are MODELLED previews
// (COMPUTATIONAL_RESULT) that swap the single hero viewer.

import { useState } from "react";
import type {
  EvalResult,
  Refusal,
  ShowcaseDetail,
  ShowcaseParam,
} from "@/lib/types";
import { evaluateParam } from "@/lib/api";

function ParamCard({
  slot,
  param,
  onPreview,
}: {
  slot: string;
  param: ShowcaseParam;
  onPreview: (r: EvalResult) => void;
}) {
  const [value, setValue] = useState<number>(
    typeof param.value === "number" ? param.value : Number(param.value) || 0
  );
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<EvalResult | null>(null);
  const [refusal, setRefusal] = useState<Refusal | null>(null);

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
                const bbox = (d.bbox ?? {}) as unknown as Record<
                  string,
                  number
                >;
                return (
                  <div key={oid} style={{ marginTop: 6 }}>
                    {oid}: volume {d.volume_mm3?.toFixed(2)} mm³ ·{" "}
                    {d.bbox
                      ? `bbox ${bbox.xlen}×${bbox.ylen}×${bbox.zlen} mm`
                      : ""}
                  </div>
                );
              })}
          <div
            style={{
              marginTop: 6,
              fontSize: 11.5,
              color: "var(--ink-faint)",
            }}
          >
            {result.honesty}
          </div>
        </div>
      )}
    </div>
  );
}

export default function InventionArtifact({
  detail,
  slot,
  onPreview,
}: {
  detail: ShowcaseDetail;
  slot: string;
  /** a preview rebuild puts its GLB on the stage hero (single viewer) */
  onPreview: (url: string | null) => void;
}) {
  const baseGlb = detail.model.glb;
  const downloads = detail.model.downloads ?? {};

  function handleResult(r: EvalResult) {
    onPreview(r.preview_glb?.serve ?? null);
  }

  return (
    <div className="artifact">
      <div className="artifact-h">
        Geometry & parameters
        <span className="faint" style={{ fontWeight: 400, fontSize: 12 }}>
          {" "}
          · {detail.package_id}
        </span>
      </div>

      {/* ---------- the stage hero mirror note ---------- */}
      {baseGlb && (
        <div className="faint" style={{ fontSize: 12.5, marginBottom: 12 }}>
          The interactive model lives on the stage above. A parameter
          rebuild swaps it with the preview version — the released
          package is untouched (deterministic CAD sandbox,
          COMPUTATIONAL_RESULT).
        </div>
      )}

      {/* ---------- downloads ---------- */}
      <div className="artifact-dls">
        <div className="rail-h">Downloads</div>
        <a className="btn download artifact-dl" href={detail.dossier.download}>
          Download technology package
        </a>
        <div className="dl-row">
          {downloads.glb && (
            <a className="dl-chip" href={downloads.glb}>
              GLB · 3D
            </a>
          )}
          {downloads.step && (
            <a className="dl-chip" href={downloads.step}>
              STEP · CAD
            </a>
          )}
          {downloads.stl && (
            <a className="dl-chip" href={downloads.stl}>
              STL · print
            </a>
          )}
          <a className="dl-chip" href={detail.model.glb}>
            view GLB
          </a>
        </div>
        <div className="faint" style={{ fontSize: 11.5, marginTop: 6 }}>
          {detail.dossier.pdfs.length} buyer documents inside the ZIP —
          executive brief, dossier, decision card, evidence, manifest,
          traceability
        </div>
      </div>

      {/* ---------- live parameters ---------- */}
      {detail.parameters.length > 0 && (
        <div className="artifact-params">
          <div className="rail-h">Live parameters</div>
          <div className="faint" style={{ fontSize: 12.5, marginBottom: 8 }}>
            change a value inside its declared envelope — the real
            parametric model rebuilds in the engine&apos;s CAD sandbox
          </div>
          {detail.parameters.slice(0, 8).map((p) => (
            <ParamCard
              key={p.param_id}
              slot={slot}
              param={p}
              onPreview={handleResult}
            />
          ))}
        </div>
      )}

      {/* ---------- key dimensions ---------- */}
      {Object.keys(detail.key_dimensions).length > 0 && (
        <div className="artifact-dims">
          <div className="rail-h">Key dimensions</div>
          <div className="faint" style={{ fontSize: 12.5, marginBottom: 8 }}>
            independently re-measured from the geometry (computation log)
          </div>
          {Object.entries(detail.key_dimensions).map(([oid, dims]) => {
            const d = dims as Record<string, unknown>;
            const bbox = (d.bbox ?? {}) as Record<string, number>;
            return (
              <div className="dim-row" key={oid}>
                <span className="dim-k">{oid}</span>
                <span className="dim-v">
                  {String(d.volume_mm3)} mm³ ·{" "}
                  {bbox.xlen}×{bbox.ylen}×{bbox.zlen} mm · wall{" "}
                  {String(d.min_wall_thickness_mm ?? "—")} mm
                </span>
              </div>
            );
          })}
        </div>
      )}

      <div className="artifact-note" style={{ fontSize: 11.5 }}>
        {detail.provenance_note}
      </div>
    </div>
  );
}
