"use client";

// The live run narrative — R393 directive 6: eight human-readable
// narrative states over the 13-stage pipeline; the machine is never
// shown. Ported from run/page.tsx into the workspace (R395).
//
// R416 (honest-causes-evolution): the narrative follows the
// architecture GENERATIONS. The user always sees forward progress
// toward an invention: "Inventing architecture 1" -> "Challenging
// architecture 1" -> "Developing architecture 2" -> ... -> "Preparing
// technology package". The terminal presents the CURRENT invention
// with its honest maturity — the banned dead-end sentences ("No
// defensible invention survived this run", "candidate rejected") are
// structurally impossible to render here.

import type { RunPhase, RunStateObject, SessionDetail, StageDigest } from "@/lib/types";
import type { GenerationRecord, RunOutcome } from "@/lib/types";
import { isTerminal } from "@/lib/presentationState";
import { isBlockedStatus } from "@/lib/present";

export const NARRATIVE_GROUPS: { heading: string; stages: string[] }[] = [
  { heading: "Understanding the problem", stages: [] },
  { heading: "Searching the evidence", stages: ["RETRIEVE", "FREEZE"] },
  {
    heading: "Inventing architecture 1",
    stages: ["SYNTHESIZE", "MULTI_SOURCE_DISCOVERY", "COLLISION"],
  },
  { heading: "Developing the invention", stages: ["VERIFY", "PHYSICS"] },
  { heading: "Challenging architecture 1", stages: ["ATTACK", "CONTRADICTION"] },
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
      ? `Invention 01 — mechanism: ${[s.mechanism, s.intervention]
          .filter(Boolean)
          .join(" → ")}.`
      : "Inventing the first architecture from the evidence…",
  VERIFY: () =>
    "Each claim verified against its exact evidence binding — no fuzzy matches admitted.",
  PHYSICS: (s) => {
    const verdict = s.lifecycle_verdict ?? s.baseline_outcome;
    return verdict
      ? `Physics gate: ${String(verdict).replace(/_/g, " ").toLowerCase()} against the un-invented baseline.`
      : "Solving the invention's physics against its baseline — plausibility bounds, failure modes, and the baseline comparison.";
  },
  MULTI_SOURCE_DISCOVERY: (s) =>
    s.prior_art_count != null
      ? `Scanned ${s.prior_art_count} prior-art references across independent sources.`
      : "Scanning prior art across independent sources…",
  COLLISION: (s) =>
    (s.collisions ?? []).length > 0
      ? `Prior-art collision check: ${(s.collisions ?? [])
          .map((c) => `${c.universe ?? ""}: ${c.verdict ?? "?"}`)
          .join(" · ")}.`
      : "Prior-art collision check complete — nothing overlapped.",
  ATTACK: (s) =>
    s.overall
      ? `Challenging architecture 1 — adversarial gate: ${s.overall}.`
      : `${(s.challenges ?? []).length} adversarial challenges run against this architecture.`,
  CONTRADICTION: (s) =>
    s.count != null
      ? `${s.count} contradictions found and resolved against the evidence.`
      : "Resolving contradictions in the evidence…",
  KILLER_EXPERIMENT: (s) => {
    const ke = s.experiment as Record<string, unknown> | undefined;
    const name = String(ke?.name ?? ke?.description ?? "");
    return name
      ? `Decisive experiment designed: ${name}.`
      : "Designing the experiment that could kill this invention…";
  },
  ADJUDICATION: (s) =>
    s.verdict
      ? `Adjudicated: ${s.verdict}.`
      : (s.reason ?? "Adjudicating the surviving architecture…"),
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
// R414 (directive §5 + §18) / R416: the canonical phase progression and
// the terminal outcomes — both READ from the backend's run_state
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
  INVENTION_UNDER_DEVELOPMENT: "RUNNING",
  // R458-C2: the machine killed its own invention and no verified
  // survivor replaced it — presented as in-development (R416), never a
  // bare dead end; the generation records carry what was killed and why
  INVENTION_KILLED_BY_CHALLENGE: "RUNNING",
  FALSE_PREMISE_INCOHERENT: "REJECTED",
  NO_DEFENSIBLE_INVENTION: "RUNNING",
  RUN_BLOCKED: "ERROR",
};

// ---------------------------------------------------------------------------
// R416: the invention generations timeline — INVENTION 01, 02, ... with
// each generation's state, what changed, and the diagnosed cause. The
// user sees the machine WORKING the problem across generations.
// ---------------------------------------------------------------------------
export function GenerationsTimeline({
  generations,
  currentGen,
}: {
  generations: GenerationRecord[] | undefined;
  currentGen?: number | null;
}) {
  if (!generations || generations.length === 0) return null;
  return (
    <div className="generations" aria-label="invention generations">
      {generations.map((g) => {
        const ch = g.challenge ?? {};
        const isCurrent = currentGen != null && g.gen === currentGen;
        const stateLabel = g.state
          ? String(g.state)
              .replace("INVENTION_", "")
              .replace(/_/g, " ")
              .toLowerCase()
          : "";
        return (
          <div
            key={g.invention_id ?? g.gen}
            className={`gen ${isCurrent ? "current" : ""} ${
              ch.killed ? "killed" : ch.survived ? "survived" : ""
            }`}
          >
            <div className="gen-head">
              <span className="gen-label">{g.label ?? `INVENTION ${String(g.gen).padStart(2, "0")}`}</span>
              {g.maturity && (
                <span className={`pill small mat-${g.maturity.toLowerCase()}`}>
                  {g.maturity}
                </span>
              )}
              {isCurrent && <span className="gen-current">CURRENT</span>}
            </div>
            {g.architecture?.intervention && (
              <div className="gen-intervention">{g.architecture.intervention}</div>
            )}
            {g.what_changed && (
              <div className="gen-change">
                <b>What changed:</b> {g.what_changed}
              </div>
            )}
            {g.causal_delta?.new_operating_regime && (
              <div className="gen-detail faint">
                New operating regime: {g.causal_delta.new_operating_regime}
              </div>
            )}
            {g.causal_delta?.frontier_capability && (
              <div className="gen-detail faint">
                Frontier transfer: {g.causal_delta.frontier_capability}
              </div>
            )}
            {ch.killed && (
              <div className="gen-kill">
                Challenged and killed at {String(ch.kill_stage ?? "the gauntlet").toLowerCase()} —
                {g.diagnosis?.cause
                  ? ` diagnosed cause: ${String(g.diagnosis.cause)
                      .replace(/_/g, " ")
                      .toLowerCase()}`
                  : ""}
              </div>
            )}
            {ch.escalated_objection && (
              <div className="gen-escalated">
                <b>Independent-attack objection preserved (not executed).</b>{" "}
                The attacker instrument is measured not calibrated — it kills
                {" "}
                {ch.escalated_objection.measured?.fpr_known_good != null
                  ? `${Math.round((ch.escalated_objection.measured.fpr_known_good ?? 0) * 100)}% of`
                  : ""}{" "}
                sealed known-good mechanisms too — so its objection is
                escalated for adjudication, never treated as a verdict.
                {ch.escalated_objection.preserved_objections?.[0]?.basis
                  ? ` Strongest objection: ${String(ch.escalated_objection.preserved_objections[0].basis).slice(0, 220)}`
                  : ""}
              </div>
            )}
            {ch.survived && (
              <div className="gen-survive">
                Survived the challenge gauntlet
                {g.maturity === "SIMULATED" ? " — physics beat the baseline" : ""}
                {ch.evidence_verified ? " — evidence-verified" : ""}
              </div>
            )}
            {g.stop_note && <div className="gen-stop faint">{g.stop_note}</div>}
            {stateLabel && !ch.killed && !ch.survived && (
              <div className="faint" style={{ fontSize: 12 }}>
                {stateLabel}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export function OutcomeBanner({
  runState,
  detail,
  packageAvailable,
}: {
  runState: RunStateObject | undefined;
  detail: SessionDetail;
  packageAvailable: boolean;
}) {
  const outcome = runState?.outcome ?? detail.user_state_view?.outcome;
  if (!outcome || outcome === "PENDING") return null;
  const label =
    runState?.outcome_label ??
    detail.user_state_view?.outcome_label ??
    outcome;
  const mechanism = runState?.mechanism_state?.mechanism;
  const generations = runState?.generations;
  const current = generations?.current_invention;
  const isDev =
    outcome === "INVENTION_UNDER_DEVELOPMENT" ||
    outcome === "NO_DEFENSIBLE_INVENTION";
  const isBlocked = outcome === "RUN_BLOCKED";
  const isPremise = outcome === "FALSE_PREMISE_INCOHERENT";
  // R467 (audit P1-2, terminal-state de-collision): when the run is
  // TERMINAL and its own records say the last challenged generation
  // was killed with no survivor, the banner says that in one frame —
  // "finished, nothing survived" — in a settled visual class. The
  // R458-C2 in-development presentation stays for everything the
  // records do not settle (a live run, a lineage still developing).
  const settledNoSurvivor =
    isTerminal(detail.status) &&
    !generations?.survivor_reached &&
    (outcome === "INVENTION_KILLED_BY_CHALLENGE" ||
      (isDev && (() => {
        const recs = generations?.generations ?? [];
        const last = recs[recs.length - 1];
        return Boolean(last?.challenge?.killed);
      })()));
  const bannerClass = settledNoSurvivor
    ? "ob-SETTLED"
    : `ob-${OUTCOME_CLASS[outcome]}`;
  const nextAction = (() => {
    const stage = (detail.stages ?? []).find(
      (s) => s.stage === "NEXT_BEST_ACTION"
    );
    const a = stage?.action as Record<string, unknown> | undefined;
    return (a?.action as string | undefined) ?? (a?.summary as string | undefined);
  })();
  return (
    <div className={`outcome-banner ${bannerClass}`}>
      <div className="outcome-line">
        {settledNoSurvivor
          ? "Run finished — no candidate survived the machine's own challenge gauntlet. Every cause and every generation's lesson is on the record below."
          : isDev
          ? `Invention ${generations?.n_generations ?? 1} generation${(generations?.n_generations ?? 1) > 1 ? "s" : ""} explored — the current architecture (GEN ${current?.gen ?? 1}) is presented with its honest maturity.`
          : isPremise
            ? "The problem's premise is physically incoherent — reformulate it and run again."
            : isBlocked
              ? "Discovery temporarily blocked by infrastructure. Your problem is saved and ready to resume."
              : label}
      </div>
      {/* R467 (audit P1-6): every terminal run leaves something in the
          user's hands — the interim evidence pack, offered exactly
          where the outcome is stated. The technology package keeps
          its own place when one exists; this offer renders only when
          none does. */}
      {isTerminal(detail.status) && !packageAvailable && (
        <a
          className="btn download"
          data-evidence-pack
          href={`/api/run/${encodeURIComponent(detail.session_id)}/evidence-pack`}
        >
          Download the evidence pack — the run's complete record
        </a>
      )}
      {isDev && (
        <div className="outcome-detail">
          {current?.maturity && (
            <div>
              <b>Current invention maturity:</b> {current.maturity} — the
              verification gates decide maturity, never the wording.
            </div>
          )}
          {mechanism ? (
            <div>
              <b>Most promising mechanism explored:</b> {mechanism}
            </div>
          ) : null}
          <div className="faint">
            the machine keeps every diagnosed cause on record — each
            generation builds on what the last one learned, and nothing
            is softened into a survivor
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
            "retry from the run page — every transport failure was recorded with its full route detail" : "retry from the run page — the failure is recorded in the run's own artifacts"}{" "}
          (an infrastructure failure is never a scientific rejection)
        </div>
      )}
      {/* R422 (directive 1 — UI copy reconciliation): the async artifact
          gate can land a bridge package AFTER the run's completion
          snapshot recorded "no package was reached". When that happened,
          this banner renders ONE calm reconciler line instead of letting
          the banner text and the Artifact panel's download link fight —
          presentation-only; the run record itself is never edited. */}
      {packageAvailable &&
        detail.user_state_view?.package_available === false && (
          <div className="outcome-detail">
            The technology package was produced by the automatic artifact
            gate after the run completed — the summary above was recorded
            at completion. The package in the Artifact panel is the
            current state.
          </div>
        )}
      {outcome === "INVENTION_REQUIRES_EXPERIMENT" && !packageAvailable && (
        <div className="outcome-detail faint">
          the invention is strong enough conceptually; the decisive
          physical experiment is specified but not executed — that is
          the recorded reason no package was reached
        </div>
      )}
    </div>
  );
}

// R451-C2: the canonical isTerminal lives in lib/presentationState.ts
// (dependency-free, deterministically testable); the re-export below
// keeps every component caller unchanged — one definition, never two.
export { isTerminal };

export default function RunNarrative({
  detail,
  packageAvailable,
}: {
  detail: NonNullable<SessionDetail>;
  packageAvailable?: boolean;
}) {
  const stages = detail.stages ?? [];
  const done = isTerminal(detail.status);
  const runState = detail.run_state as RunStateObject | undefined;
  const generations = runState?.generations?.generations;
  const currentGen = runState?.generations?.current_invention?.gen;
  const evolutionLive = runState?.evolution_state;

  return (
    <div className="narrative" aria-live="polite">
      {/* R453-C2 merge: the R451-C2 §10 journal banner, ported from the
          retired DeepDive surface — an infrastructure stop renders here
          too, so the technical record can never read as a scientific
          verdict. The predicate is the presentation layer's blocked-state
          classifier (one owner); the banner CSS (.jpb-*) is unchanged. */}
      {isBlockedStatus(detail.status) && (
        <div className="journal-paused-banner" data-journal-paused-banner>
          <div className="jpb-title">PAUSED AT INFRASTRUCTURE</div>
          <div className="jpb-line">
            The investigation has not produced a scientific verdict.
          </div>
          <div className="jpb-line faint">
            Earlier recorded events remain valid. Downstream stages were not
            evaluated.
          </div>
        </div>
      )}
      <PhaseProgression phases={runState?.phase_progression} />

      {/* R416: the live evolution line — "Developing architecture 3 ·
          Frontier transfer in progress" while a generation is in flight */}
      {evolutionLive && !done && (
        <div className="nline working gen-live">
          <span className="cursor" />
          {evolutionLive.label} — {evolutionLive.subline}
        </div>
      )}

      {done && (
        <OutcomeBanner
          runState={runState}
          detail={detail}
          packageAvailable={Boolean(packageAvailable)}
        />
      )}
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

      {/* R416: the generations timeline — INVENTION 01 → 02 → … with
          what changed at each step (progressive disclosure: shown as
          soon as the first generation record exists) */}
      {(generations?.length ?? 0) > 0 && (
        <div className="ngroup">
          <h3>The inventions, so far</h3>
          <GenerationsTimeline generations={generations} currentGen={currentGen} />
        </div>
      )}

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
