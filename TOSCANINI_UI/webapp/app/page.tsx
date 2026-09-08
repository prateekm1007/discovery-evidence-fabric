"use client";

// R395: THE WORKSPACE — the product's one experience (CEO directive:
// the interaction model gets one decisive redesign, borrowed from the
// Claude philosophy: conversation as the primary workspace, the
// substantial artifact beside it).
//
//   ┌────────────────────────────────────────────────────────────┐
//   │ Toscanini · engine status          [+ New problem]         │
//   ├───────────────┬────────────────────────────┬───────────────┤
//   │ HISTORY       │ CONVERSATION               │ ARTIFACT      │
//   │ your runs     │ problem → investigation    │ 3D design     │
//   │ inventions    │ → engineering argument     │ parameters    │
//   │               │ → ask about it             │ downloads     │
//   └───────────────┴────────────────────────────┴───────────────┘
//
// The 13-stage pipeline, the machine states, the G-gates — all of it
// stays underneath (complexity hidden behind a simple surface).
// Honest states everywhere: user_state_view pills, honest refusals,
// no fabricated progress, nothing claims physical validation.

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  getCIO,
  getHealth,
  getRealityLoop,
  getRunResult,
  getShowcase,
  listSessions,
  listShowcase,
  retryRun,
  startRun,
} from "@/lib/api";
import type {
  CIO,
  HealthSummary,
  RealityLoopRecord,
  SessionDetail,
  SessionRow,
  ShowcaseDetail,
  ShowcaseRow,
} from "@/lib/types";
import HistoryRail from "@/components/HistoryRail";
import RunNarrative, { isTerminal } from "@/components/RunNarrative";
import {
  EngineeringArgument,
  NoveltyAndCemetery,
} from "@/components/EngineeringArgument";
import AskBox from "@/components/AskBox";
import RunArtifact from "@/components/RunArtifact";
import InventionArtifact from "@/components/InventionArtifact";
import InventionStory from "@/components/InventionStory";
import InventionEssay from "@/components/InventionEssay";

const EXAMPLES = [
  "Why do infusion pumps fail to detect downstream occlusion before patient harm?",
  "How can EV traction-battery thermal runaway initiation be prevented?",
  "Why do rails fracture in service under fatigue loading?",
  "How can we keep minimum drainage when a shunt's primary lumen obstructs?",
];

function TransportDot({ health }: { health: HealthSummary | null }) {
  // R415 (directive §10) + R419 (§20): the CALM product surface —
  // "Discovery ready" or "Discovery temporarily unavailable". Provider
  // failover is INVISIBLE: the routing ladder switches models
  // internally (MODEL A → B → C) and the user never sees provider
  // names, degradation counts, or failover events; only a full
  // transport exhaustion reaches the surface (and then honestly).
  const r = health?.readiness;
  const ready = r?.discovery_ready ?? health?.discovery_ready ??
    health?.llm_transport_ready === true;
  return (
    <span
      className={`transport-dot ${ready ? "ok" : "down"}`}
      title={
        ready
          ? "discovery ready — engine live, transport verified by a real probe"
          : "discovery temporarily unavailable — runs will say so honestly"
      }
    />
  );
}

function EngineStatusText({ health }: { health: HealthSummary | null }) {
  // R419 (§20): status wording GENERATED from /api/health —
  // "Discovery ready" / "Showcase ready · Discovery temporarily
  // unavailable". Per-provider degradation never reaches this text
  // (failover is internal); the technical per-provider truth stays in
  // the health payload for audits, not for the product surface.
  // "engine starting…" is BANNED as a persistent state.
  const r = health?.readiness;
  const ready = r?.discovery_ready ?? health?.discovery_ready ??
    health?.llm_transport_ready === true;
  if (ready) {
    return "Discovery ready";
  }
  if (health === null) {
    return ""; // first poll in flight — never a fake persistent state
  }
  const showcase = health?.showcase_ready ?? r?.showcase_ready ??
    health?.portfolio_ready;
  return showcase
    ? "Showcase ready · Discovery temporarily unavailable"
    : "Discovery temporarily unavailable";
}

const STORY_STEPS = [
  "DISCOVER",
  "INVENT",
  "INSPECT",
  "CHALLENGE",
  "REBUILD",
  "EXPERIMENT",
];

function NewProblemPane({
  onStarted,
}: {
  onStarted: (id: string) => void;
}) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit() {
    const t = text.trim();
    if (t.length < 15) {
      setError(
        "Please describe the problem in a bit more detail (at least 15 characters)."
      );
      return;
    }
    if (submitting) return;
    setError(null);
    setSubmitting(true);
    onStarted("busy");
    try {
      const session = await startRun(t);
      onStarted(session.session_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to start the run");
      onStarted("");
      setSubmitting(false);
    }
  }

  return (
    <section className="hero workspace-hero">
      {/* R415 (P0 directive §10/§11/§21): the main brand statement and
          the landing hierarchy — the problem input is the dominant
          element until an invention exists, then the 3D artifact takes
          over. No "AI platform" language. */}
      <h1 className="brand-statement">DISCOVER. INVENT. ANYTHING.</h1>
      <p className="brand-subline">
        Give Toscanini a real problem. It will investigate the evidence,
        challenge its own ideas, and develop the strongest invention it
        can defend.
      </p>
      <h2 className="ask-title">What problem should Toscanini investigate?</h2>
      <div className="ask">
        <textarea
          placeholder="Describe a real technical problem…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
          }}
        />
        <div className="ask-foot">
          <span className="hint">
            ⌘↵ to start · runs take minutes; you can leave and come back
          </span>
          <button className="btn" onClick={submit} type="button">
            {submitting ? "Starting…" : "Start discovery"}
          </button>
        </div>
      </div>
      {error && (
        <div className="errbox" style={{ textAlign: "left" }}>
          {error}
        </div>
      )}
      <div className="story-strip" aria-label="how it works">
        {STORY_STEPS.map((step, i) => (
          <span className="story-step" key={step}>
            <span className="story-word">{step}</span>
            {i < STORY_STEPS.length - 1 && (
              <span className="story-arrow" aria-hidden="true">↓</span>
            )}
          </span>
        ))}
      </div>
      <div className="examples">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            className="example"
            onClick={() => setText(ex)}
            type="button"
          >
            {ex.length > 62 ? ex.slice(0, 60) + "…" : ex}
          </button>
        ))}
      </div>
    </section>
  );
}

function RunConversation({
  detail,
  packageAvailable,
}: {
  detail: SessionDetail;
  packageAvailable: boolean;
}) {
  const done = isTerminal(detail.status);
  const usv = detail.user_state_view;
  return (
    <>
      {/* the user's message: the problem itself */}
      <div className="msg user">
        <div className="msg-role">You</div>
        <div className="msg-body">{detail.user_text}</div>
      </div>

      {/* Toscanini's live reply: the narrative stream */}
      <div className="msg tosca">
        <div className="msg-role">
          Toscanini
          {usv && done && (
            <span className="pill COMPLETE">{usv.label}</span>
          )}
        </div>
        <div className="msg-body">
          <RunNarrative
            detail={detail}
            packageAvailable={packageAvailable}
          />

          {done && usv && (
            <div className="narrative-summary">
              {usv.decision}
              {usv.meaning && (
                <div className="faint" style={{ marginTop: 4 }}>
                  {usv.meaning}
                </div>
              )}
            </div>
          )}

          {done && detail.status === "COMPLETE" && (
            <>
              <div className="reasoning">
                <h3>The engineering argument</h3>
                <div className="sub">
                  derived from the run&apos;s persisted artifacts — evidence,
                  mechanisms, decisions, and what is still unknown
                </div>
                <EngineeringArgument
                  detail={detail}
                  packageAvailable={packageAvailable}
                />
              </div>
              {/* R419 section 11: the engineer's 8-section narrative —
                  "What Toscanini invented", from the canonical state */}
              <InventionEssay sessionId={detail.session_id} />
              <NoveltyAndCemetery detail={detail} />
            </>
          )}
        </div>
      </div>

      {done && (
        <AskBox
          mode="run"
          subject={detail.session_id}
          enabled={detail.status === "COMPLETE"}
        />
      )}
    </>
  );
}

function WorkspaceInner() {
  const params = useSearchParams();
  const router = useRouter();
  const runId = params.get("run");
  const slot = params.get("invention");

  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [showcase, setShowcase] = useState<ShowcaseRow[]>([]);
  const [health, setHealth] = useState<HealthSummary | null>(null);
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [cio, setCio] = useState<CIO | null>(null);
  const [cioLoading, setCioLoading] = useState(false);
  // R422 (P0 triage item 6): a run id that 404s repeatedly must surface
  // a VISIBLE state — "Loading run…" forever was the silent-404 trap that
  // made the R421 session misdiagnose the live pipeline as dead. The
  // counter tracks consecutive result-poll failures; 4 misses (~10 s)
  // flips the center pane to an honest not-found / not-visible state.
  const [runNotFound, setRunNotFound] = useState(false);
  const [invention, setInvention] = useState<ShowcaseDetail | null>(null);
  const [reality, setReality] = useState<RealityLoopRecord | null>(null);
  const [railOpen, setRailOpen] = useState(false);
  const [starting, setStarting] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  // ---- load rails + health once ----
  useEffect(() => {
    listSessions().then(setSessions).catch(() => setSessions([]));
    listShowcase().then(setShowcase).catch(() => setShowcase([]));
    getHealth().then(setHealth).catch(() => setHealth(null));
    const h = setInterval(() => {
      getHealth().then(setHealth).catch(() => {});
      if (!runId) {
        listSessions().then(setSessions).catch(() => {});
      }
    }, 30000);
    return () => clearInterval(h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- load the focused run (and poll while it works) ----
  useEffect(() => {
    setDetail(null);
    setRunNotFound(false);
    let misses = 0;
    if (timer.current) clearInterval(timer.current);
    const id = runId ?? "";
    if (!id) return;
    let alive = true;
    async function poll() {
      try {
        const d = await getRunResult(id);
        if (!alive) return;
        misses = 0;
        setRunNotFound(false);
        setDetail(d);
        if (isTerminal(d.status)) {
          if (timer.current) clearInterval(timer.current);
          listSessions().then(setSessions).catch(() => {});
        }
      } catch (e) {
        if (!alive) return;
        // R422: a 404 is NOT transient noise when it repeats — it means
        // the run id does not exist or is scoped to another owner (R394
        // s15). Four consecutive misses stop the silent spinner and show
        // an honest state; other errors stay transient (network blips).
        if (e instanceof Error && e.message.startsWith("404")) {
          misses += 1;
          if (misses >= 4) setRunNotFound(true);
        }
      }
    }
    poll();
    timer.current = setInterval(poll, 2500);
    return () => {
      alive = false;
      if (timer.current) clearInterval(timer.current);
    };
  }, [runId]);

  // ---- R422: load the CIO once the run is terminal (the ONE invention
  // object; an honest null when the run produced no invention-side
  // artifacts). Lifted here from RunArtifact so EVERY package-availability
  // assertion on the page derives from the same fresh data. ----
  useEffect(() => {
    setCio(null);
    setCioLoading(false);
    if (!detail || !isTerminal(detail.status)) return;
    let alive = true;
    setCioLoading(true);
    getCIO(detail.session_id)
      .then((c) => {
        if (!alive) return;
        setCio(c);
        setCioLoading(false);
      })
      .catch(() => {
        if (!alive) return;
        setCio(null);
        setCioLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [detail?.session_id, detail?.status]);

  // ---- R422 (directive 1 — UI copy reconciliation): the SINGLE source
  // of truth for package availability, computed from the FRESHEST data:
  // the live CIO's download endpoint (reflects the async artifact gate's
  // package) or the run record's package field (re-derived from the run
  // dir on every result poll — the authority, Art. X). TRUE iff a
  // package is actually downloadable right now. The completion-time
  // user_state_view.package_available is NEVER the only basis for copy —
  // a run whose bridge package landed after completion can no longer
  // say "no package" above a live download link.
  // ----
  const packageAvailable = Boolean(
    cio?.downloads?.package_zip ||
    detail?.package?.zip_name ||
    detail?.package?.complete
  );

  // ---- load the focused invention ----
  useEffect(() => {
    setInvention(null);
    setReality(null);
    if (!slot) return;
    getShowcase(slot)
      .then(setInvention)
      .catch(() => setInvention(null));
    getRealityLoop(slot).then(setReality).catch(() => setReality(null));
  }, [slot]);

  const selectRun = useCallback(
    (id: string) => {
      setRailOpen(false);
      router.push(`/?run=${id}`);
    },
    [router]
  );
  const selectInvention = useCallback(
    (s: string) => {
      setRailOpen(false);
      router.push(`/?invention=${s}`);
    },
    [router]
  );
  const newProblem = useCallback(() => {
    setRailOpen(false);
    router.push("/");
  }, [router]);

  function onStarted(id: string) {
    if (id === "busy") {
      setStarting(true);
      return;
    }
    setStarting(false);
    if (id) {
      listSessions().then(setSessions).catch(() => {});
      selectRun(id);
    }
  }

  const activeMode = runId ? "run" : slot ? "invention" : "fresh";

  return (
    <div className="workspace">
      <header className="ws-top">
        <button
          className="rail-toggle"
          onClick={() => setRailOpen(!railOpen)}
          type="button"
          aria-label="toggle history"
        >
          ☰
        </button>
        <a className="brand" href="/">
          Toscanini
        </a>
        <span className="ws-status">
          <TransportDot health={health} />
          <span className="ws-status-text">
            <EngineStatusText health={health} />
          </span>
        </span>
        <span className="ws-spacer" />
        <button className="btn small ghost" onClick={newProblem} type="button">
          + New problem
        </button>
      </header>

      <div className="ws-body">
        <div className={`ws-rail ${railOpen ? "open" : ""}`}>
          <HistoryRail
            sessions={sessions}
            showcase={showcase}
            activeRun={runId}
            activeInvention={slot}
            onSelectRun={selectRun}
            onSelectInvention={selectInvention}
            onNewProblem={newProblem}
          />
        </div>
        {railOpen && (
          <div
            className="ws-rail-backdrop"
            onClick={() => setRailOpen(false)}
          />
        )}

        <main className="ws-center">
          {activeMode === "fresh" &&
            (starting ? (
              <div className="loading">Starting the run…</div>
            ) : (
              <NewProblemPane onStarted={onStarted} />
            ))}

          {activeMode === "run" &&
            (detail ? (
              <RunConversation
                detail={detail}
                packageAvailable={packageAvailable}
              />
            ) : runNotFound ? (
              <div className="errbox" style={{ marginTop: 24 }}>
                <b>Run not found.</b> This run id does not exist, or it
                belongs to a different visitor (runs are private to the
                session that created them). If you just started this run,
                use the history rail — if the rail is empty, the run did
                not register and nothing was invented on it (an
                infrastructure state, never a scientific result).
              </div>
            ) : (
              <div className="loading">Loading run…</div>
            ))}

          {activeMode === "invention" &&
            (invention ? (
              <div className="invstory">
                <InventionStory detail={invention} loop={reality} />
                <AskBox
                  mode="invention"
                  subject={slot ?? ""}
                  enabled={true}
                  placeholder="Ask about this technology — answered from its own record…"
                />
              </div>
            ) : (
              <div className="loading">Loading package…</div>
            ))}
        </main>

        <aside className="ws-artifact">
          {activeMode === "run" &&
            (detail ? (
              <RunArtifact
                detail={detail}
                cio={cio}
                cioLoading={cioLoading}
                packageAvailable={packageAvailable}
                onRetry={(id) =>
                  retryRun(id).then(() => location.reload())
                }
              />
            ) : (
              <div className="artifact">
                <div className="artifact-h">Artifact</div>
                <div className="faint">loading…</div>
              </div>
            ))}

          {activeMode === "invention" &&
            (invention ? (
              <InventionArtifact detail={invention} slot={slot ?? ""} />
            ) : (
              <div className="artifact">
                <div className="artifact-h">Artifact</div>
                <div className="faint">loading…</div>
              </div>
            ))}

          {activeMode === "fresh" && (
            <div className="artifact artifact-quite">
              <div className="artifact-h">Artifact</div>
              <div className="artifact-placeholder">
                <div className="ph-shape" aria-hidden="true" />
                <div>
                  The invention will appear here — the inspectable 3D
                  design, live parameters, dimensions, and the downloadable
                  technology package.
                </div>
                <div className="faint" style={{ fontSize: 12 }}>
                  released inventions in the rail load instantly with full
                  3D
                </div>
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

export default function Page() {
  return (
    <Suspense fallback={<div className="loading">Loading…</div>}>
      <WorkspaceInner />
    </Suspense>
  );
}
