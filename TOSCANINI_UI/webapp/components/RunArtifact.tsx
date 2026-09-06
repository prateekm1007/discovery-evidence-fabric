"use client";

// R395: the workspace's right pane for a RUN — the live artifact card
// while the engine works, then the honest terminal card: package
// download when one was produced, the honest no-package explanation
// when not (a real result, never a failure of the product).
//
// R414 (directive §12-14, §20): the terminal card renders the CANONICAL
// INVENTION OBJECT — one object, one source of truth. The 3D viewer
// appears only when the CIO's geometry actually exists (never inferred
// from anything else); the reality-status badges are CIO FIELDS
// (DESIGNED / SIMULATED / EVIDENCE-SUPPORTED / EXPERIMENTALLY
// VERIFIED), never frontend inventions; the counsel button exports the
// technical evidence package for IP counsel review — it never says
// "patent this" (Toscanini is not a patent court).

import { useEffect, useState } from "react";
import type { CIO, SessionDetail } from "@/lib/types";
import { getCIO } from "@/lib/api";
import { isTerminal } from "./RunNarrative";
import ModelViewer from "./ModelViewer";

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

function CioPanel({ cio, detail }: { cio: CIO; detail: SessionDetail }) {
  const geo = cio.geometry;
  const downloads = cio.downloads ?? {};
  const languageQuarantined = cio.language_guard?.clean === false;
  return (
    <>
      <MaturityBadges cio={cio} />

      {geo?.present && geo.glb ? (
        <div className="artifact-3d">
          <ModelViewer
            url={geo.glb}
            height={300}
            compact
            label="run geometry"
            note="the run's engineering geometry (CadQuery/OCCT authority; renders are derived artifacts — never physical truth)"
          />
        </div>
      ) : (
        <div className="artifact-note">
          <b>No 3D on this run.</b>{" "}
          {geo?.parametric_model_present
            ? "A parametric model was produced but no exported mesh — design is DESIGNED, the 3D export was not reached."
            : "The run produced no engineering geometry (the CAD pipeline did not reach a model on this run — honest absence, never a placeholder object)."}
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
        <a className="btn download artifact-dl" href={downloads.package_zip}>
          Download technology package
        </a>
      ) : (
        <div className="artifact-note">
          <b>Candidate, no package.</b> A package is produced only when a
          candidate survives the full adversarial chain — candidates are
          recorded, packages are earned.
        </div>
      )}

      <a
        className="btn counsel artifact-dl"
        href={`/api/run/${detail.session_id}/counsel-package`}
      >
        Prepare for IP counsel
      </a>
      <div className="faint" style={{ fontSize: 12, marginTop: 4 }}>
        exports the technical evidence package — invention description,
        cited evidence, prior-art results, provenance — for your patent
        attorney to review. Toscanini does not determine patentability:
        <i> potential IP territory — formal legal review required.</i>
      </div>

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

export default function RunArtifact({
  detail,
  onRetry,
}: {
  detail: SessionDetail;
  onRetry: (id: string) => void;
}) {
  const usv = detail.user_state_view;
  const done = isTerminal(detail.status);
  const stages = detail.stages ?? [];
  const pkg = detail.package ?? null;
  const [cio, setCio] = useState<CIO | null>(null);

  // R414: fetch the CIO once the run is terminal (the invention object
  // exists only when the run produced invention-side artifacts — an
  // honest null otherwise, never a fabricated object).
  useEffect(() => {
    if (!done) return;
    let alive = true;
    getCIO(detail.session_id)
      .then((c) => alive && setCio(c))
      .catch(() => alive && setCio(null));
    return () => {
      alive = false;
    };
  }, [done, detail.session_id]);

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

          {cio?.present ? (
            <CioPanel cio={cio} detail={detail} />
          ) : pkg?.zip_name ? (
            <a
              className="btn download artifact-dl"
              href={`/api/run/${detail.session_id}/package`}
            >
              Download technology package
            </a>
          ) : usv.found_something ? (
            <div className="artifact-note">
              <b>Candidate, no package.</b> This run recorded an invention
              candidate, but no buyer package was produced — the release
              gate was not reached. An honest result: candidates are
              recorded, packages are earned.
            </div>
          ) : (
            <div className="artifact-note">
              <b>No buyer package.</b> A package is produced only when a
              candidate survives the full adversarial chain — no survivor
              reached the release gate on this run. That is an honest
              result, not a failure of the product: kills are recorded to
              the mechanism cemetery and improve the next run.
            </div>
          )}

          {!cio?.present && done && (
            <a
              className="btn counsel artifact-dl"
              href={`/api/run/${detail.session_id}/counsel-package`}
            >
              Prepare for IP counsel
            </a>
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
