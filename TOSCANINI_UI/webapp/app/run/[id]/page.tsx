"use client";

// The live run experience: watch the real engine stages stream from
// persisted artifacts, then see the engineering argument and the package.
// The reasoning display is derived from run artifacts — never private
// chain-of-thought (R389 Phase 4).

import { use, useEffect, useRef, useState } from "react";
import { getRunResult, retryRun } from "@/lib/api";
import type { SessionDetail, StageDigest } from "@/lib/types";

const STAGE_LABELS: Record<string, string> = {
  RETRIEVE: "Retrieving evidence",
  FREEZE: "Freezing evidence custody",
  SYNTHESIZE: "Synthesizing mechanisms",
  VERIFY: "Verifying evidence bindings",
  MULTI_SOURCE_DISCOVERY: "Multi-source discovery",
  COLLISION: "Checking prior art",
  ATTACK: "Adversarial attacks",
  CONTRADICTION: "Resolving contradictions",
  KILLER_EXPERIMENT: "Designing decisive experiment",
  ADJUDICATION: "Adjudicating",
  CLASSIFY: "Classifying epistemic state",
  NEXT_BEST_ACTION: "Ranking next actions",
  RANK: "Final ranking",
};

const PHASE_LABELS: Record<string, string> = {
  BUILDING_PROBLEM: "Building an evidence-bound problem statement…",
  PENDING: "Queued…",
  RUNNING: "The engine is running…",
};

function stageInfo(s: StageDigest): string {
  switch (s.stage) {
    case "RETRIEVE":
      return s.records_found != null
        ? `${s.records_found} records from ${(s.sources ?? []).join(", ")}`
        : "";
    case "FREEZE":
      return "content hashes + exact spans bound";
    case "SYNTHESIZE":
      return [s.mechanism, s.intervention].filter(Boolean).join(" → ") || "";
    case "VERIFY":
      return "claim-level verification";
    case "MULTI_SOURCE_DISCOVERY":
      return s.prior_art_count != null
        ? `${s.prior_art_count} prior-art candidates scanned`
        : "";
    case "COLLISION":
      return (s.collisions ?? [])
        .map((c) => `${c.universe ?? ""}: ${c.verdict ?? "?"}`)
        .join(" · ");
    case "ATTACK":
      return s.overall
        ? `adversarial gate: ${s.overall}`
        : `${(s.challenges ?? []).length} attacks`;
    case "CONTRADICTION":
      return s.count != null ? `${s.count} contradictions` : "";
    case "KILLER_EXPERIMENT": {
      const ke = s.experiment as Record<string, unknown> | undefined;
      return String(ke?.name ?? ke?.description ?? "");
    }
    case "ADJUDICATION":
      return s.verdict ? `verdict: ${s.verdict}` : (s.reason ?? "");
    case "CLASSIFY": {
      const es = s.epistemic_state as Record<string, unknown> | undefined;
      return String(es?.epistemic_state ?? es?.final_status ?? "");
    }
    case "RANK":
      return s.score != null ? `score ${s.score}` : "";
    default:
      return "";
  }
}

function str(x: unknown, max = 400): string {
  if (x == null) return "";
  if (typeof x === "string") return x;
  if (typeof x === "number" || typeof x === "boolean") return String(x);
  try {
    return JSON.stringify(x).slice(0, max);
  } catch {
    return String(x);
  }
}

function pick(obj: Record<string, unknown> | null | undefined, key: string) {
  if (!obj) return undefined;
  return obj[key];
}

function RunView({ detail }: { detail: NonNullable<SessionDetail> }) {
  const inv = (detail.invention_specification ??
    {}) as Record<string, unknown>;
  const invMech = pick(inv, "mechanism") as Record<string, unknown> | undefined;
  const invCausal = pick(inv, "causal_chain") as
    | Record<string, unknown>
    | undefined;
  const invNovelty = pick(inv, "novelty_hypothesis") as
    | Record<string, unknown>
    | undefined;
  const unc = pick(inv, "uncertainties");
  const ke = (detail.decisive_experiment ?? {}) as Record<string, unknown>;
  const keSel = (ke.selected ?? ke) as Record<string, unknown>;
  const fs = (detail.final_state ?? {}) as Record<string, unknown>;
  const pkg = detail.package ?? null;
  const epRetrieval = detail.evidence_pack?.retrieval ?? [];

  const synthesizeStage = detail.stages?.find((s) => s.stage === "SYNTHESIZE");
  const retrieveStage = detail.stages?.find((s) => s.stage === "RETRIEVE");

  return (
    <>
      <div className="problem">
        <div className="label">The problem</div>
        <div className="text">{detail.user_text}</div>
      </div>

      {/* ------- the engineering argument (not chain-of-thought) ------- */}
      <div className="reasoning">
        <h3>The engineering argument</h3>
        <div className="sub">
          derived from the run&apos;s persisted artifacts — evidence,
          mechanisms, decisions, and what is still unknown
        </div>
        <div className="arg">
          <div className="step">
            <div className="k">Problem</div>
            <div className="v">{detail.title}</div>
          </div>
          <div className="step">
            <div className="k">Observation</div>
            <div className="v">
              {str(
                (pick(inv, "problem") as Record<string, unknown>)?.description ??
                  fs.observation,
                500
              ) || (
                <span className="faint">
                  {retrieveStage?.records_found ?? 0} evidence records
                  retrieved across{" "}
                  {(retrieveStage?.sources ?? []).length || "several"} sources
                </span>
              )}
            </div>
          </div>
          <div className="step">
            <div className="k">Evidence</div>
            <div className="v">
              {(epRetrieval.length > 0
                ? epRetrieval.slice(0, 4).map((r, i) => (
                    <div key={i}>
                      · <b>{r.source ?? "?"}</b> — {str(r.title, 160)}
                    </div>
                  ))
                : (retrieveStage?.sample_titles ?? []).map((t, i) => (
                    <div key={i}>· {t}</div>
                  ))) || (
                <span className="faint">no retrieval evidence displayed</span>
              )}
              <div className="faint">
                {retrieveStage?.records_found ?? 0} records · custody-frozen
                with content hashes
              </div>
            </div>
          </div>
          <div className="step">
            <div className="k">Mechanism</div>
            <div className="v">
              {str(invMech?.value ?? synthesizeStage?.mechanism, 500) || (
                <span className="faint">not established by this run</span>
              )}
            </div>
          </div>
          <div className="step">
            <div className="k">Design decision</div>
            <div className="v">
              {str(invCausal?.value ?? synthesizeStage?.intervention, 500) || (
                <span className="faint">not established by this run</span>
              )}
            </div>
          </div>
          <div className="step">
            <div className="k">Technical result</div>
            <div className="v">
              {str(fs.final_status, 300) || detail.final_status || (
                <span className="faint">pending</span>
              )}
              {pkg?.maturity && (
                <div className="faint">package maturity: {pkg.maturity}</div>
              )}
            </div>
          </div>
          <div className="step">
            <div className="k">Uncertainty</div>
            <div className="v">
              {str(
                (unc as Record<string, unknown> | undefined)?.value ?? unc,
                420
              ) || (
                <span className="faint">
                  key uncertainties recorded with the invention specification
                </span>
              )}
            </div>
          </div>
          <div className="step">
            <div className="k">Next experiment</div>
            <div className="v">
              {str(keSel.name ?? keSel.description, 400) || (
                <span className="faint">
                  the decisive experiment stage will appear here
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ------- novelty + negative knowledge ------- */}
      <div className="grid2">
        <div className="block">
          <h4>Novelty hypothesis</h4>
          <div style={{ fontSize: 14 }}>
            {str(invNovelty?.value, 600) || "not established"}
          </div>
        </div>
        <div className="block">
          <h4>Cemetery update (negative knowledge)</h4>
          <ul>
            {detail.cemetery_update ? (
              <li style={{ fontSize: 13.5 }}>
                {str(detail.cemetery_update, 500)}
              </li>
            ) : (
              <li>
                no cemetery entry from this run{" "}
                <span className="faint">
                  (only kills and rejects are recorded — kept forever)
                </span>
              </li>
            )}
          </ul>
        </div>
      </div>

      {pkg?.zip_name ? (
        <div className="download-cta">
          <div className="msg">
            <h3>Technology package</h3>
            <p>
              The complete dossier — executive brief, engineering
              technology-transfer dossier, buyer decision card, evidence
              summary, transfer manifest, and traceability records.
            </p>
          </div>
          <a
            className="btn download"
            href={`/api/run/${detail.session_id}/package`}
          >
            Download technology package
          </a>
        </div>
      ) : (
        <div className="notavail">
          <b>No buyer package.</b> A package is produced only when a candidate
          survives the full adversarial chain — no survivor reached the
          release gate on this run. That is an honest result, not a failure
          of the product: kills are recorded to the mechanism cemetery and
          improve the next run.
        </div>
      )}
    </>
  );
}

export default function RunPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let alive = true;

    async function poll() {
      try {
        const d = await getRunResult(id);
        if (!alive) return;
        setDetail(d);
        setError(null);
        if (d.status === "COMPLETE" || d.status.startsWith("ERROR")) {
          if (timer.current) clearInterval(timer.current);
        }
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : "load failed");
      }
    }

    poll();
    timer.current = setInterval(poll, 2500);
    return () => {
      alive = false;
      if (timer.current) clearInterval(timer.current);
    };
  }, [id]);

  const stages = detail?.stages ?? [];
  const done =
    detail?.status === "COMPLETE" || (detail?.status ?? "").startsWith("ERROR");

  return (
    <main className="runpage">
      {error && <div className="errbox">{error}</div>}
      {!detail && !error && <div className="loading">Loading run…</div>}

      {detail && (
        <>
          <div className="statusbar">
            {!done && <div className="spinner" />}
            <span
              className={`pill ${
                detail.status.startsWith("ERROR") ? "ERROR" : detail.status
              }`}
            >
              {detail.status}
            </span>
            <span className="phase">
              {done
                ? detail.final_status ?? detail.status
                : PHASE_LABELS[detail.status] ?? "working…"}
            </span>
          </div>

          <div className="stages">
            {stages.map((s) => (
              <div className={`stage ${s.status ?? ""}`} key={s.stage}>
                <div className="name">
                  <span className="dot" />
                  {STAGE_LABELS[s.stage] ?? s.stage}
                </div>
                <div className="info">{stageInfo(s)}</div>
              </div>
            ))}
            {!done && (
              <div className="stage">
                <div className="name">
                  <span className="dot" /> …
                </div>
                <div className="info">
                  {stages.length}/13 stages persisted · statuses come from the
                  run directory, never fabricated
                </div>
              </div>
            )}
          </div>

          {detail.status.startsWith("ERROR") && (
            <div className="errbox">
              <b>{detail.status}</b> — {detail.error ?? "unknown error"}
              <div style={{ marginTop: 10 }}>
                <button
                  className="btn ghost small"
                  onClick={() => retryRun(id).then(() => location.reload())}
                  type="button"
                >
                  Retry through the same worker path
                </button>
              </div>
            </div>
          )}

          {detail.status === "COMPLETE" && <RunView detail={detail} />}

          <div className="backrow">
            <a href="/">← new problem</a>
          </div>
        </>
      )}
    </main>
  );
}
