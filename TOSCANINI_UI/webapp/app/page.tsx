"use client";

// R430.1 — THE SCIENTIFIC TECHNOLOGY ARTIFACT WORKSPACE.
//
//   ┌────────────────────────────┬─────────────────────────────────┐
//   │ INVESTIGATION              │ TECHNOLOGY DOSSIER              │
//   │ conversation               │ Overview / Design / Evidence    │
//   │ scientific stages          │ Engineering / Experiment        │
//   │ evidence events            │ Transfer                        │
//   │ user interaction           │ (the living technology artifact)│
//   └────────────────────────────┴─────────────────────────────────┘
//
// ~40/60 on desktop, collapsing to a single flow on mobile with the
// dossier as a full-width panel (section 18). The 13-stage pipeline,
// the machine states, the G-gates — all of it stays underneath. The
// dossier exists from the first canonical state (section 3) — never
// gated on 3D or PACKAGE_READY. Honest states everywhere; the only
// prominent customer action is DOWNLOAD TECHNOLOGY PACKAGE.
//
// Section 12 (refresh recovery): the workspace hydrates from PERSISTED
// endpoints only — /result, /events, /dossier — then reconnects the
// live event stream if the job is still running. No UI state depends
// solely on transient React state.

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  getCIO,
  getDossier,
  getEvents,
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
  DossierBody,
  EventsBody,
  GauntletCard,
  HealthSummary,
  RealityLoopRecord,
  ScienceEvent,
  SessionDetail,
  SessionRow,
  ShowcaseDetail,
  ShowcaseRow,
} from "@/lib/types";
import HistoryRail from "@/components/HistoryRail";
import InvestigationPane from "@/components/InvestigationPane";
import DossierPane from "@/components/DossierPane";
import InventionArtifact from "@/components/InventionArtifact";
import InventionStory from "@/components/InventionStory";
import AskBox from "@/components/AskBox";
import { isTerminal } from "@/components/RunNarrative";

const EXAMPLES = [
  "Why do infusion pumps fail to detect downstream occlusion before patient harm?",
  "How can EV traction-battery thermal runaway initiation be prevented?",
  "Why do rails fracture in service under fatigue loading?",
  "How can we keep minimum drainage when a shunt's primary lumen obstructs?",
];

function TransportDot({ health }: { health: HealthSummary | null }) {
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
      <h1 className="brand-statement">DISCOVER. INVENT. ANYTHING.</h1>
      <p className="brand-subline">
        Give Toscanini a real problem. It will investigate the evidence,
        challenge its own ideas, and develop the strongest invention it
        can defend — while you watch the investigation unfold and the
        technology dossier grow.
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
            {submitting ? "Starting…" : "Start investigation"}
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
  // R422: a run id that 404s repeatedly must surface a VISIBLE state.
  const [runNotFound, setRunNotFound] = useState(false);
  // R430.1: the investigation event history + the dossier projection —
  // persisted endpoints; the refresh-recovery sources (section 12).
  const [events, setEvents] = useState<ScienceEvent[]>([]);
  const [gauntlet, setGauntlet] = useState<GauntletCard[]>([]);
  const [dossier, setDossier] = useState<DossierBody | null>(null);
  const [dossierLoading, setDossierLoading] = useState(false);
  const [invention, setInvention] = useState<ShowcaseDetail | null>(null);
  const [reality, setReality] = useState<RealityLoopRecord | null>(null);
  const [railOpen, setRailOpen] = useState(false);
  const [starting, setStarting] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const evtTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const es = useRef<EventSource | null>(null);

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

  // ---- R430.1 section 11/12: the event history poll (recovery +
  //      long-interval truth) + the live SSE science stream ----
  useEffect(() => {
    setEvents([]);
    setGauntlet([]);
    setDossier(null);
    if (evtTimer.current) clearInterval(evtTimer.current);
    es.current?.close();
    es.current = null;
    const id = runId ?? "";
    if (!id) return;
    let alive = true;

    async function refresh() {
      try {
        const body: EventsBody = await getEvents(id);
        if (!alive) return;
        setEvents(body.events ?? []);
        setGauntlet(body.gauntlet ?? []);
      } catch {
        /* honest absence — the result poll still drives the UI */
      }
      try {
        setDossierLoading(true);
        const d = await getDossier(id);
        if (!alive) return;
        setDossier(d);
      } finally {
        if (alive) setDossierLoading(false);
      }
    }
    refresh();
    evtTimer.current = setInterval(refresh, 5000);

    // live hydration: append SSE 'science' events as they are recorded
    // (only while the investigation is running; the terminal 'final'
    // event closes the stream)
    try {
      const source = new EventSource(`/api/run/${id}/stream`);
      es.current = source;
      source.addEventListener("science", (m) => {
        try {
          const evt = JSON.parse((m as MessageEvent).data);
          if (!alive || !evt?.event_id) return;
          setEvents((prev) =>
            prev.some((e) => e.event_id === evt.event_id)
              ? prev
              : [...prev, evt]
          );
        } catch {
          /* malformed frame — the poll remains the truth */
        }
      });
      source.addEventListener("final", () => {
        // terminal: one last refresh of everything, then close
        refresh();
        source.close();
        es.current = null;
        if (evtTimer.current) clearInterval(evtTimer.current);
      });
      source.addEventListener("done", () => {
        source.close();
        es.current = null;
      });
      source.onerror = () => {
        // the poll (5 s) carries recovery; SSE is an enhancement
      };
    } catch {
      /* EventSource unavailable — polling remains the hydration path */
    }

    return () => {
      alive = false;
      if (evtTimer.current) clearInterval(evtTimer.current);
      es.current?.close();
      es.current = null;
    };
  }, [runId]);

  // stop the events/dossier polling once terminal (the last refresh
  // already ran on 'final')
  useEffect(() => {
    if (detail && isTerminal(detail.status)) {
      if (evtTimer.current) clearInterval(evtTimer.current);
      es.current?.close();
      es.current = null;
    }
  }, [detail?.status]);

  // ---- R422: load the CIO once the run is terminal ----
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

  // ---- the single source of truth for package availability ----
  const packageAvailable = Boolean(
    cio?.downloads?.package_zip ||
    detail?.package?.zip_name ||
    detail?.package?.complete ||
    dossier?.tabs?.transfer?.download
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

        <main className="ws-investigation">
          {activeMode === "fresh" &&
            (starting ? (
              <div className="loading">Starting the investigation…</div>
            ) : (
              <NewProblemPane onStarted={onStarted} />
            ))}

          {activeMode === "run" &&
            (detail ? (
              <InvestigationPane
                detail={detail}
                events={events}
                gauntlet={gauntlet}
                dossier={dossier}
                packageAvailable={packageAvailable}
                onRetry={(id) =>
                  retryRun(id).then(() => location.reload())
                }
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
              <div className="loading">Loading investigation…</div>
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

        <aside className="ws-dossier">
          {activeMode === "run" && (
            <DossierPane
              dossier={dossier}
              gauntlet={gauntlet}
              loading={
                dossierLoading && !dossier && detail !== null
              }
            />
          )}

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
            <aside className="dossier">
              <div className="dossier-h">Technology Dossier</div>
              <div className="dossier-placeholder">
                <div className="ph-shape" aria-hidden="true" />
                <div>
                  Start an investigation and the dossier grows beside it:
                  problem, evidence, mechanism, challenge, engineering,
                  the decisive experiment — and the downloadable
                  technology package when the invention survives.
                </div>
                <div className="faint" style={{ fontSize: 12 }}>
                  the dossier exists from the first moment the
                  investigation starts — incomplete tabs are honest
                  pending states, never errors
                </div>
              </div>
            </aside>
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
