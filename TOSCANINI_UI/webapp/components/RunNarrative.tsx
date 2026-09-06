"use client";

// The live run narrative — R393 directive 6: eight human-readable
// narrative states over the 13-stage pipeline; the machine is never
// shown. Ported from run/page.tsx into the workspace (R395).

import type { RunPhase, RunStateObject, SessionDetail, StageDigest } from "@/lib/types";
import type { RunOutcome } from "@/lib/types";

export const NARRATIVE_GROUPS: { heading: string; stages: string[] }[] = [
  { heading: "Understanding the problem", stages: [] },
  { heading: "Searching the evidence", stages: ["RETRIEVE", "FREEZE"] },
  {
    heading: "Testing competing mechanisms",
    stages: ["SYNTHESIZE", "MULTI_SOURCE_DISCOVERY", "COLLISION"],
  },
  { heading: "Building the candidate", stages: ["VERIFY", "PHYSICS"] },
  { heading: "Attacking the candidate", stages: ["ATTACK", "CONTRADICTION"] },
  { heading: "Improving it", stages: ["ADJUDICATION"] },
  { heading: "Designing the experiment", stages: ["KILLER_EXPERIMENT"] },
  {
    heading: "Preparing the technology package",
    stages: ["CLASSIFY", "NEXT_BEST_ACTION", "RANK"],
  },
];

export const STAGE_SENTENCE: Record<string, (s: StageDigest) => string> = {
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
  PHYSICS: (s) => {
    const verdict = s.lifecycle_verdict ?? s.baseline_outcome;
    return verdict
      ? `Physics gate: ${String(verdict).replace(/_/g, " ").toLowerCase()} against the un-invented baseline.`
      : "Solving the candidate's physics against its baseline — plausibility bounds, failure modes, and the baseline comparison.";
  },
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

export const PHASE_LABELS: Record<string, string> = {
  BUILDING_PROBLEM: "Reading the problem and binding it to evidence…",
  PENDING: "Queued…",
  RUNNING: "Thinking…",
};


// ---------------------------------------------------------------------------
// R414 (directive §5 + §18): the canonical phase progression and the
// four terminal outcomes — both READ from the backend's run_state
// (toscanini/run_state.py). The frontend never re-derives states and
// never infers an invention exists because a GLB exists.
// ---------------------------------------------------------------------------
const PHASE_MARK: Record<string, string> = {
  NOT_STARTED: "·",
  IN_PROGRESS: "…",
  DONE: "✓",
  FAILED: "✕",
};

export function PhaseProgression({
  phases,
}: {
  phases: RunPhase[] | undefined;
}) {
  if (!phases || phases.length === 0) return null;
  return (
    <div className="phasebar" aria-label="discovery progress">
      {phases.map((ph) => (
        <div
          key={ph.phase}
          className={`phase phase-${ph.state.toLowerCase()}`}
          title={Object.entries(ph.stages ?? {})
            .map(([k, v]) => `${k}: ${v}`)
            .join(" · ")}
        >
          <span className="phase-mark">{PHASE_MARK[ph.state] ?? "·"}</span>
          <span className="phase-label">{ph.label}</span>
        </div>
      ))}
    </div>
  );
}

const OUTCOME_CLASS: Record<RunOutcome, string> = {
  PENDING: "RUNNING",
  INVENTION_SURVIVED: "COMPLETE",
  INVENTION_REQUIRES_EXPERIMENT: "COMPLETE",
  NO_DEFENSIBLE_INVENTION: "REJECTED",
  RUN_BLOCKED: "ERROR",
};

export function OutcomeBanner({
  runState,
  detail,
}: {
  runState: RunStateObject | undefined;
  detail: SessionDetail;
}) {
  const outcome = runState?.outcome ?? detail.user_state_view?.outcome;
  if (!outcome || outcome === "PENDING") return null;
  const label =
    runState?.outcome_label ??
    detail.user_state_view?.outcome_label ??
    outcome;
  // directive §2: the honest no-invention shape — never "nothing found,
  // try again". Most promising mechanism, missing evidence, best next
  // step are read from the run state's own fields.
  const mechanism = runState?.mechanism_state?.mechanism;
  const nextAction = (() => {
    const stage = (detail.stages ?? []).find(
      (s) => s.stage === "NEXT_BEST_ACTION"
    );
    const a = stage?.action as Record<string, unknown> | undefined;
    return (a?.action as string | undefined) ?? (a?.summary as string | undefined);
  })();
  const isNo = outcome === "NO_DEFENSIBLE_INVENTION";
  const isBlocked = outcome === "RUN_BLOCKED";
  return (
    <div className={`outcome-banner ob-${OUTCOME_CLASS[outcome]}`}>
      <div className="outcome-line">
        {isNo
          ? "No defensible invention survived this run."
          : isBlocked
            ? "Discovery temporarily blocked by infrastructure. Your problem is saved and ready to resume."
            : label}
      </div>
      {isNo && (
        <div className="outcome-detail">
          {mechanism ? (
            <div>
              <b>Most promising mechanism explored:</b> {mechanism}
            </div>
          ) : null}
          <div className="faint">
            kills are recorded to the mechanism cemetery and improve
            future runs — a real discovery result, not a failure
          </div>
          {nextAction ? (
            <div>
              <b>Best next step:</b> {nextAction}
            </div>
          ) : null}
        </div>
      )}
      {isBlocked && (
        <div className="outcome-detail faint">
          {runState?.failure_state?.error ?
            "retry from the run page — every provider failure was recorded with its provider, model, and failure class" : "retry from the run page — the failure is recorded in the run's own artifacts"}{" "}
          (Art. LXI: infrastructure failure is never a scientific rejection)
        </div>
      )}
      {outcome === "INVENTION_REQUIRES_EXPERIMENT" && (
        <div className="outcome-detail faint">
          the candidate is strong enough conceptually; the decisive
          physical experiment is specified but not executed — that is
          the recorded reason no package was reached
        </div>
      )}
    </div>
  );
}

export function isTerminal(status: string): boolean {
  return (
    status === "COMPLETE" ||
    status === "INTERRUPTED" ||
    status.startsWith("ERROR") ||
    status.startsWith("RUN_BLOCKED")  // R415: RUN_BLOCKED_TRANSPORT —
    // infrastructure-blocked terminal, distinct from every verdict
  );
}

export default function RunNarrative({
  detail,
}: {
  detail: NonNullable<SessionDetail>;
}) {
  const stages = detail.stages ?? [];
  const done = isTerminal(detail.status);
  const runState = detail.run_state as RunStateObject | undefined;

  return (
    <div className="narrative" aria-live="polite">
      <PhaseProgression phases={runState?.phase_progression} />
      {done && <OutcomeBanner runState={runState} detail={detail} />}
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
                const last = isLast && st === present[present.length - 1];
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
          Working — {stages.length} of 15 steps recorded so far; every
          status comes from the run directory, never fabricated
        </div>
      )}
    </div>
  );
}
