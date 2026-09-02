"use client";

// The live run experience: watch the real engine stages stream from
// persisted artifacts, then see the engineering argument and the package.
// The reasoning display is derived from run artifacts — never private
// chain-of-thought (R389 Phase 4).

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { getRunResult, retryRun } from "@/lib/api";
import type { SessionDetail, StageDigest } from "@/lib/types";

// R391 (claude.ai principle): the run page shows the ENGINEERING ARGUMENT
// AS IT EMERGES — one plain sentence per persisted stage — not pipeline
// labels. Same artifact-derived data, same honest counters; the plumbing
// stays invisible ("complex pipeline, boring interface").
//
// R393 (CEO directive 6): the visible run experience is the eight
// human-readable narrative states. The 13 internal stages map underneath;
// the machine is never shown.

const NARRATIVE_GROUPS: { heading: string; stages: string[] }[] = [
  { heading: "Understanding the problem", stages: [] },
  { heading: "Searching the evidence", stages: ["RETRIEVE", "FREEZE"] },
  {
    heading: "Testing competing mechanisms",
    stages: ["SYNTHESIZE", "MULTI_SOURCE_DISCOVERY", "COLLISION"],
  },
  { heading: "Building the candidate", stages: ["VERIFY"] },
  { heading: "Attacking the candidate", stages: ["ATTACK", "CONTRADICTION"] },
  { heading: "Improving it", stages: ["ADJUDICATION"] },
  { heading: "Designing the experiment", stages: ["KILLER_EXPERIMENT"] },
  {
    heading: "Preparing the technology package",
    stages: ["CLASSIFY", "NEXT_BEST_ACTION", "RANK"],
  },
];

const STAGE_SENTENCE: Record<string, (s: StageDigest) => string> = {
  RETRIEVE: (s) =>
    s.records_found != null
      ? `Read ${s.records_found} evidence records from ${(s.sources ?? []).join(
          ", "
        )} — each custody-frozen with a content hash.`
        : "Reading the evidence base…",
  FREEZE: () =>
    "Evidence custody frozen: every claim will have to bind to an exact source span.",
  SYNTHESIZE: (s) =>
    [s.mechanism, s.intervention].filter(Boolean).length > 0
      ? `Candidate mechanism: ${[s.mechanism, s.intervention]
          .filter(Boolean)
          .join(" → ")}.`
        : "Synthesizing candidate mechanisms from the evidence…",
  VERIFY: () =>
    "Each claim verified against its exact evidence binding — no fuzzy matches admitted.",
  MULTI_SOURCE_DISCOVERY: (s) =>
    s.prior_art_count != null
      ? `Scanned ${s.prior_art_count} prior-art candidates across independent sources.`
      : "Scanning prior art across independent sources…",
  COLLISION: (s) =>
    (s.collisions ?? []).length > 0
      ? `Prior-art collision check: ${(s.collisions ?? [])
          .map((c) => `${c.universe ?? ""}: ${c.verdict ?? "?"}`)
          .join(" · ")}.`
      : "Prior-art collision check complete — nothing overlapped.",
  ATTACK: (s) =>
    s.overall
      ? `Adversarial gate: ${s.overall}.`
      : `${(s.challenges ?? []).length} adversarial attacks run against the candidate.`,
  CONTRADICTION: (s) =>
    s.count != null
      ? `${s.count} contradictions found and resolved against the evidence.`
      : "Resolving contradictions in the evidence…",
  KILLER_EXPERIMENT: (s) => {
    const ke = s.experiment as Record<string, unknown> | undefined;
    const name = String(ke?.name ?? ke?.description ?? "");
    return name
      ? `Decisive experiment designed: ${name}.`
      : "Designing the experiment that could kill the candidate…";
  },
  ADJUDICATION: (s) =>
    s.verdict
      ? `Adjudicated: ${s.verdict}.`
      : (s.reason ?? "Adjudicating the surviving candidate…"),
  CLASSIFY: (s) => {
    const es = s.epistemic_state as Record<string, unknown> | undefined;
    const state = String(es?.epistemic_state ?? es?.final_status ?? "");
    return state
      ? `Epistemic state: ${state}.`
      : "Classifying what is actually known…";
  },
  NEXT_BEST_ACTION: () => "Ranked the next actions by information value.",
  RANK: (s) =>
    s.score != null
      ? `Final ranking recorded — score ${s.score}.`
      : "Final ranking recorded.",
};

function stageSentence(s: StageDigest): string {
  const fn = STAGE_SENTENCE[s.stage];
  return fn ? fn(s) : `${s.stage.toLowerCase().replace(/_/g, " ")}…`;
}

const PHASE_LABELS: Record<string, string> = {
  BUILDING_PROBLEM: "Reading the problem and binding it to evidence…",
  PENDING: "Queued…",
  RUNNING: "Thinking…",
};

// R392 job lifecycle: a run is finished only at a REAL terminal state —
// COMPLETE, an honest ERROR_*, or INTERRUPTED (worker died; recoverable).
function isTerminal(status: string): boolean {
  return (
    status === "COMPLETE" ||
    status === "INTERRUPTED" ||
    status.startsWith("ERROR")
  );
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

export default function RunPage() {
  return (
    <Suspense fallback={<div className="loading">Loading run…</div>}>
      <RunPageInner />
    </Suspense>
  );
}

function RunPageInner() {
  const id = useSearchParams().get("id") ?? "";
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
        if (isTerminal(d.status)) {
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
  const done = detail ? isTerminal(detail.status) : false;

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

          <div className="narrative" aria-live="polite">
            {/* R393 directive 6: the eight narrative states. A heading
                appears only when its work has actually begun; stage
                sentences render beneath it. Unknown future stages fall
                into an honest trailing group — never hidden. */}
            {(() => {
              const byStage = new Map(stages.map((s) => [s.stage, s]));
              const seen = new Set<string>();
              const blocks: React.ReactNode[] = [];
              for (const g of NARRATIVE_GROUPS) {
                const present = g.stages.filter((st) => byStage.has(st));
                if (present.length === 0) continue;
                present.forEach((st) => seen.add(st));
                const isLast =
                  present[present.length - 1] === stages[stages.length - 1]?.stage;
                blocks.push(
                  <div className="ngroup" key={g.heading}>
                    <h3>{g.heading}</h3>
                    {present.map((st) => {
                      const s = byStage.get(st)!;
                      const last =
                        isLast && st === present[present.length - 1];
                      return (
                        <div
                          className={`nline ${
                            s.status === "FAIL" ? "fail" : done ? "" : "latest"
                          }`}
                          key={s.stage}
                        >
                          {s.status === "FAIL" ? "Blocked: " : ""}
                          {stageSentence(s)}
                          {last && !done && <span className="cursor" />}
                        </div>
                      );
                    })}
                  </div>
                );
              }
              // stage "Understanding the problem" while the problem is
              // still being built (before any stage lands)
              if (stages.length === 0 && !done) {
                blocks.push(
                  <div className="ngroup" key="understand">
                    <h3>Understanding the problem</h3>
                    <div className="nline working">
                      <span className="cursor" />
                      {detail.status === "BUILDING_PROBLEM"
                        ? "reading the problem and binding it to the evidence base…"
                        : PHASE_LABELS[detail.status] ?? "working…"}
                    </div>
                  </div>
                );
              }
              // honest fallback: engine stages outside the eight states
              const rest = stages.filter((s) => !seen.has(s.stage));
              if (rest.length > 0) {
                blocks.push(
                  <div className="ngroup" key="more">
                    <h3>Continuing</h3>
                    {rest.map((s) => (
                      <div
                        className={`nline ${s.status === "FAIL" ? "fail" : ""}`}
                        key={s.stage}
                      >
                        {s.status === "FAIL" ? "Blocked: " : ""}
                        {stageSentence(s)}
                      </div>
                    ))}
                  </div>
                );
              }
              return blocks;
            })()}
            {!done && stages.length > 0 && (
              <div className="nline working">
                <span className="cursor" />
                Working — {stages.length} of 13 steps recorded so far; every
                status comes from the run directory, never fabricated
              </div>
            )}
          </div>

          {(detail.status.startsWith("ERROR") ||
            detail.status === "INTERRUPTED") && (
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
