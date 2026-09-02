"use client";

// R395: the workspace's right pane for a RELEASED INVENTION — the
// artifact is first-class: interactive 3D (rotate/zoom/pan/reset/
// fullscreen/wireframe/clip), real parameter rebuilds through the
// deterministic CAD sandbox with A/B version compare, downloadable
// STEP/STL/GLB geometry, the buyer dossier, and re-measured key
// dimensions. The released package bytes are never modified (Art. IX);
// rebuilds are MODELLED previews (COMPUTATIONAL_RESULT).

import { useState } from "react";
import type {
  EvalResult,
  Refusal,
  ShowcaseDetail,
  ShowcaseParam,
} from "@/lib/types";
import { evaluateParam } from "@/lib/api";
import ModelViewer from "./ModelViewer";

function ParamCard({
  slot,
  param,
  onPreview,
  activeGlb,
}: {
  slot: string;
  param: ShowcaseParam;
  onPreview: (r: EvalResult, activate: boolean) => void;
  activeGlb: string;
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
      onPreview(out.result, true);
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
}: {
  detail: ShowcaseDetail;
  slot: string;
}) {
  const [activeGlb, setActiveGlb] = useState<string>(detail.model.glb);
  const [previewGlb, setPreviewGlb] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(true);
  const baseGlb = detail.model.glb;
  const downloads = detail.model.downloads ?? {};
  const showing = previewGlb && showPreview ? previewGlb : baseGlb;

  return (
    <div className="artifact">
      <div className="artifact-h">
        Artifact
        <span className="faint" style={{ fontWeight: 400, fontSize: 12 }}>
          {" "}
          · {detail.package_id}
        </span>
      </div>

      {/* ---------- the 3D design ---------- */}
      {detail.model.glb && (
        <>
          <ModelViewer
            url={showing}
            height={340}
            compact
            label={
              showing === baseGlb
                ? "released geometry"
                : "preview rebuild — your parameter change"
            }
            note={
              showing === baseGlb
                ? "the released engineering geometry — rotate, zoom, pan, reset, wireframe, clip, fullscreen"
                : "a preview rebuild from your parameter change — deterministic CAD sandbox, COMPUTATIONAL_RESULT, the released package is untouched"
            }
          />

          {/* ---------- A/B version compare ---------- */}
          {previewGlb && (
            <div className="ab-compare">
              <span className="ab-label">compare versions</span>
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
                onClick={() => {
                  setPreviewGlb(null);
                }}
                type="button"
              >
                clear preview
              </button>
            </div>
          )}
        </>
      )}

      {/* ---------- downloads ---------- */}
      <div className="artifact-dls">
        <div className="rail-h">Downloads</div>
        <a className="btn download artifact-dl" href={detail.dossier.download}>
          Technology package (ZIP)
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
              activeGlb={activeGlb}
              onPreview={(r, activate) => {
                if (activate && r.preview_glb?.serve) {
                  setPreviewGlb(r.preview_glb.serve);
                  setActiveGlb(r.preview_glb.serve);
                } else if (r.preview_glb?.serve) {
                  setPreviewGlb(r.preview_glb.serve);
                }
              }}
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
