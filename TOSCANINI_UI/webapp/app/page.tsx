"use client";

// R453-C2 — THE CLAUDE-CLASS RECONSTRUCTION: one conversation → one
// discovery.
//
//   ┌────────────────────────────────────────────────────────────────┐
//   │ Toscanini   ● Discovery ready                       + New      │
//   ├──────────┬──────────────────────────────────┬──────────────────┤
//   │ SIDEBAR  │  THE CONVERSATION                │  THE WORKSPACE   │
//   │ New      │  you: the problem                │  (appears when   │
//   │ Discoveries│ Toscanini: what it found,      │   there is a     │
//   │ Packages │  what it believes, what attacked │   substantial    │
//   │ Projects │  it, what remains uncertain,     │   output) model· │
//   │ Settings │  the next decisive action        │  evidence·eng·   │
//   │          │  [ composer ]                    │  experiment·pkg  │
//   └──────────┴──────────────────────────────────┴──────────────────┘
//
// What changed from R435 (and why — Art. LXIV dispositions in the audit):
//   * TechStage.tsx DELETED — the stage+report layout is superseded by
//     the conversation (Conversation.tsx) and the contextual workspace
//     (Workspace.tsx); the hero viewer moved INTO the workspace's model
//     surface (the ONE-viewer invariant is preserved by construction).
//   * HistoryRail.tsx DELETED — superseded by Sidebar.tsx (the new IA).
//   * DeepDive stays as the canonical deep layer but renders INSIDE the
//     workspace surfaces; nothing re-derived.
//   * The pipeline appears as a story (present.ts), never as machinery.
//
// The frontend remains a PROJECTION of canonical state (Art. X): every
// sentence flows through lib/present.ts; adversarial fixtures pin the
// honesty contracts (tests/adversarial_present.test.mjs).

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  answerClarification,
  apiPost,
  askRun,
  createShare,
  diagnosticPackageUrl,
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
  streamUrl,
  uploadAttachment,
  type AttachmentUploadResult,
} from "@/lib/api";
import type {
  AskResponse,
  CIO,
  DossierBody,
  EventsBody,
  HealthSummary,
  RealityLoopRecord,
  ScienceEvent,
  SessionDetail,
  SessionRow,
  ShowcaseDetail,
  ShowcaseRow,
} from "@/lib/types";
import type { NextAction, SurfaceId } from "@/lib/present";
import { suppressStalePositives } from "@/lib/present";
import Sidebar from "@/components/Sidebar";
import Conversation from "@/components/Conversation";
import Workspace from "@/components/Workspace";
import InventionStage from "@/components/InventionStage";
import { isTerminal } from "@/components/RunNarrative";

const EXAMPLES = [
  "Why do infusion pumps fail to detect downstream occlusion before patient harm?",
  "How can EV traction-battery thermal runaway initiation be prevented?",
  "Why do rails fracture in service under fatigue loading?",
  "How can we keep minimum drainage when a shunt's primary lumen obstructs?",
];

const SUGGESTIONS = [
  { label: "Explore a technical problem", example: EXAMPLES[1] },
  { label: "Investigate an observation", example: EXAMPLES[0] },
  { label: "Improve an existing design", example: EXAMPLES[2] },
  { label: "Find an unmet need", example: EXAMPLES[3] },
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

// ---------------------------------------------------------------------------
// HOME — one dominant composer, a few lightweight suggestions. No
// dashboard wall, no KPI cards, no pipeline diagram (brief §6).
//
// R458-C2 — THE INPUT MODEL (§2/§3/§15): one interaction carries the
// problem + a URL + attachments + constraints. Attachments are ingested
// SERVER-SIDE (upload → canonical document/reference → evidence) — the
// browser never reads a file into the problem string. Until the
// engine's attachment endpoint goes live (contract → Coder 1), the
// limitation is stated honestly and nothing is pretended.
// ---------------------------------------------------------------------------
function NewDiscoveryPane({
  onStarted,
}: {
  onStarted: (id: string) => void;
}) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  // R459 (audit P0-3): files upload the moment they are selected —
  // server-side extraction + content hash happen up front, so submit
  // can never hit a missing-capability wall.
  const [pending, setPending] = useState<
    { file: File; state: "uploading" | "ingested" | "rejected"; record?: AttachmentUploadResult }[]
  >([]);
  const [submitting, setSubmitting] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function submit() {
    const t = text.trim();
    if (t.length < 15) {
      setError(
        "Describe the problem in a sentence or two — the engine infers the rest."
      );
      return;
    }
    if (submitting) return;
    if (pending.some((p) => p.state === "uploading")) return; // uploads in flight
    setError(null);
    setSubmitting(true);
    onStarted("busy");
    try {
      const ids = pending
        .filter((p) => p.state === "ingested" && p.record?.attachment_id)
        .map((p) => p.record!.attachment_id!);
      const session = await startRun(t, ids);
      onStarted(session.session_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to start the run");
      onStarted("");
      setSubmitting(false);
    }
  }

  async function onFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    const incoming = Array.from(files).map((file) => ({
      file,
      state: "uploading" as const,
    }));
    setPending((prev) => [...prev, ...incoming]);
    for (const item of incoming) {
      try {
        const rec = await uploadAttachment(item.file);
        setPending((prev) =>
          prev.map((p) =>
            p.file === item.file
              ? { ...p, state: rec.rejected ? "rejected" : "ingested", record: rec }
              : p
          )
        );
      } catch {
        setPending((prev) =>
          prev.map((p) =>
            p.file === item.file
              ? {
                  ...p,
                  state: "rejected",
                  record: { name: item.file.name, rejected: true,
                            ingestion: { status: "UPLOAD_FAILED",
                                         note: "the upload could not be delivered" } },
                }
              : p
          )
        );
      }
    }
  }

  return (
    <section className="hero workspace-hero" data-new-discovery>
      <h1 className="brand-statement">DISCOVER. INVENT. ANYTHING.</h1>
      <h2 className="ask-title">What do you want to discover?</h2>
      <div className="ask">
        <textarea
          autoFocus
          placeholder="Describe a problem, an observation, or a technology you want investigated — in your own words. A URL, constraints, and specs are welcome."
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void submit();
            }
          }}
        />
        {pending.length > 0 && (
          <div className="ask-attachments" data-pending-attachments>
            {pending.map((p, i) => (
              <span
                className={`ask-attachment ${p.state === "rejected" ? "bad" : ""}`}
                key={`${p.file.name}-${i}`}
                title={p.record?.ingestion?.note ?? (p.state === "uploading" ? "uploading…" : undefined)}
              >
                {p.file.name}
                {p.state === "ingested" && p.record?.ingestion?.status === "TEXT_EXTRACTED" && (
                  <span className="faint">
                    {" · "}{p.record.ingestion.text_chars_total ?? 0} characters read
                  </span>
                )}
                {p.state === "uploading" && <span className="faint"> · uploading…</span>}
                {p.state === "rejected" && (
                  <span className="faint">
                    {" · "}{p.record?.ingestion?.note ?? "could not be read"}
                  </span>
                )}
                <button
                  type="button"
                  className="ask-attachment-x"
                  aria-label={`remove ${p.file.name}`}
                  onClick={() =>
                    setPending((prev) => prev.filter((_, j) => j !== i))
                  }
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
        <div className="ask-foot">
          <span className="hint">
            Enter to start · Shift+Enter for a new line · runs take minutes;
            you can leave and come back
          </span>
          <div className="ask-actions">
            <input
              ref={fileRef}
              type="file"
              multiple
              hidden
              onChange={(e) => {
                void onFiles(e.target.files);
                e.target.value = "";
              }}
            />
            <button
              type="button"
              className="btn small ghost"
              onClick={() => fileRef.current?.click()}
              title="attach a document — it is read server-side, hashed, and joins the investigation's record"
            >
              + Attach
            </button>
            <button
              className="btn"
              onClick={() => void submit()}
              type="button"
              disabled={pending.some((p) => p.state === "uploading")}
            >
              {submitting ? "Starting…" : "Start the discovery"}
            </button>
          </div>
        </div>
      </div>
      {error && (
        <div className="errbox" style={{ textAlign: "left" }}>
          {error}
        </div>
      )}
      <div className="suggestions" aria-label="where to start">
        {SUGGESTIONS.map((s) => (
          <button
            key={s.label}
            className="suggestion"
            type="button"
            onClick={() => {
              setText(s.example);
            }}
            title={s.example}
          >
            {s.label}
          </button>
        ))}
      </div>
      <div className="hero-privacy faint">
        The engine infers domain, mechanism space, and evidence strategy from
        your words — you are never asked to fill a form first.
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// THE WORKSPACE SHELL
// ---------------------------------------------------------------------------
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
  const [runNotFound, setRunNotFound] = useState(false);
  // R453-C2 (BS-018 class): the engine being unreachable is ITS OWN honest
  // state — never a silent spinner, never a fake scientific conclusion.
  const [connLost, setConnLost] = useState(false);
  const [events, setEvents] = useState<ScienceEvent[]>([]);
  const [gauntlet, setGauntlet] = useState<EventsBody["gauntlet"]>([]);
  const [dossier, setDossier] = useState<DossierBody | null>(null);
  const [invention, setInvention] = useState<ShowcaseDetail | null>(null);
  const [reality, setReality] = useState<RealityLoopRecord | null>(null);
  const [railOpen, setRailOpen] = useState(false);
  const [starting, setStarting] = useState(false);
  // the contextual workspace surface (brief §12) — null = closed
  const [surface, setSurface] = useState<SurfaceId | null>(null);
  const [asks, setAsks] = useState<{ question: string; response: AskResponse }[]>([]);
  // R459 (audit P1-3): the share flow — the backend endpoint existed;
  // the product surface now offers it.
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [shareCopied, setShareCopied] = useState(false);
  const autoOpened = useRef<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const evtTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const es = useRef<EventSource | null>(null);

  // ---- rails + health ----
  useEffect(() => {
    listSessions().then(setSessions).catch(() => setSessions([]));
    listShowcase().then(setShowcase).catch(() => setShowcase([]));
    getHealth().then(setHealth).catch(() => setHealth(null));
    const h = setInterval(() => {
      // R458-C2 (§21): a hidden tab needs no engine traffic — polling
      // resumes on return; SSE and the poll keep the same truth
      if (typeof document !== "undefined" && document.hidden) return;
      getHealth().then(setHealth).catch(() => {});
      if (!runId) {
        listSessions().then(setSessions).catch(() => {});
      }
    }, 30000);
    return () => clearInterval(h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- the focused run ----
  useEffect(() => {
    setDetail(null);
    setRunNotFound(false);
    setConnLost(false);
    setAsks([]);
    setSurface(null);
    autoOpened.current = null;
    let misses = 0;
    let connMisses = 0;
    if (timer.current) clearInterval(timer.current);
    const id = runId ?? "";
    if (!id) return;
    let alive = true;
    async function poll() {
      // R458-C2 (§21): skip engine traffic while the tab is hidden —
      // the interval keeps ticking so recovery is immediate on return
      if (typeof document !== "undefined" && document.hidden) return;
      try {
        const d = await getRunResult(id);
        if (!alive) return;
        misses = 0;
        connMisses = 0;
        setRunNotFound(false);
        setConnLost(false);
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
        } else {
          // transport-level failure (engine restarting, network down):
          // say so after a short grace — the poll keeps trying either way
          connMisses += 1;
          if (connMisses >= 3 && connMisses % 3 === 0) setConnLost(true);
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

  // ---- events + dossier + live stream ----
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
      if (typeof document !== "undefined" && document.hidden) return;
      try {
        const body: EventsBody = await getEvents(id);
        if (!alive) return;
        setEvents(body.events ?? []);
        setGauntlet(body.gauntlet ?? []);
      } catch {
        /* honest absence — the result poll still drives the UI */
      }
      try {
        const d = await getDossier(id);
        if (!alive) return;
        setDossier(d);
      } catch {
        /* the dossier is a projection — honest absence until it exists */
      }
    }
    refresh();
    evtTimer.current = setInterval(refresh, 5000);

    try {
      const source = new EventSource(streamUrl(id));
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
        /* the poll (5 s) carries recovery; SSE is an enhancement */
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

  useEffect(() => {
    if (detail && isTerminal(detail.status)) {
      if (evtTimer.current) clearInterval(evtTimer.current);
      es.current?.close();
      es.current = null;
    }
  }, [detail?.status]);

  // ---- CIO once terminal ----
  useEffect(() => {
    setCio(null);
    if (!detail || !isTerminal(detail.status)) return;
    let alive = true;
    getCIO(detail.session_id)
      .then((c) => {
        if (!alive) return;
        setCio(c);
      })
      .catch(() => {
        if (!alive) return;
        setCio(null);
      });
    return () => {
      alive = false;
    };
  }, [detail?.session_id, detail?.status]);

  const packageAvailable = Boolean(
    cio?.downloads?.package_zip ||
      detail?.package?.zip_name ||
      detail?.package?.complete ||
      dossier?.tabs?.transfer?.download
  );

  // ---- the invention (showcase) ----
  useEffect(() => {
    setInvention(null);
    setReality(null);
    if (!slot) return;
    getShowcase(slot)
      .then(setInvention)
      .catch(() => setInvention(null));
    getRealityLoop(slot).then(setReality).catch(() => setReality(null));
  }, [slot]);

  // ---- auto-open the workspace when a substantial output exists ----
  // (desktop only; the conversation stays primary on mobile). A blocked
  // run NEVER auto-opens a surface: stale-positive presentation stays
  // suppressed (brief §14 / Test B — the Resume CTA is the one action).
  // R458-C2 (§12): the surface opens BECAUSE something important exists
  // — package ready → Package; a real model → Model; a decisive test
  // defined → Experiment. Never all of them, never as navigation.
  useEffect(() => {
    if (!runId || !detail || !isTerminal(detail.status)) return;
    if (suppressStalePositives(detail)) return;
    if (autoOpened.current === runId) return;
    if (!window.matchMedia("(min-width: 1181px)").matches) return;
    const design = dossier?.tabs?.design as
      | { availability?: string; hero_eligibility?: { eligible?: boolean } }
      | undefined;
    const heroEligible =
      design?.availability === "AVAILABLE" &&
      design?.hero_eligibility?.eligible !== false;
    if (packageAvailable) {
      autoOpened.current = runId;
      setSurface(heroEligible ? "model" : "package");
    } else if (heroEligible) {
      autoOpened.current = runId;
      setSurface("model");
    } else if (
      (dossier?.tabs?.experiment as { availability?: string } | undefined)
        ?.availability === "AVAILABLE"
    ) {
      autoOpened.current = runId;
      setSurface("experiment");
    }
  }, [runId, detail?.status, dossier, packageAvailable]);

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

  async function handleAsk(question: string) {
    if (!detail) return;
    // R458-C2 (§4): while the engine's ONE material question is open,
    // every composer message is an ANSWER to it — resuming the same run
    // through C1's live contract. Anything else stays a read-only ask.
    if (detail.status === "AWAITING_CLARIFICATION") {
      try {
        await answerClarification(detail.session_id, question);
        setAsks((prev) => [
          ...prev,
          {
            question,
            response: {
              status: "ANSWERED",
              answer:
                "Answer recorded — the investigation resumes with it. What happens next appears here, from the record.",
              basis: "the engine's clarification pause (one material question)",
            },
          },
        ]);
      } catch (e) {
        setAsks((prev) => [
          ...prev,
          {
            question,
            response: {
              status: "TRANSPORT_ERROR",
              reason:
                e instanceof Error ? e.message : "the answer could not be delivered",
            },
          },
        ]);
      }
      return;
    }
    try {
      const response = await askRun(detail.session_id, question);
      setAsks((prev) => [...prev, { question, response }]);
    } catch (e) {
      setAsks((prev) => [
        ...prev,
        {
          question,
          response: {
            status: "TRANSPORT_ERROR",
            reason: e instanceof Error ? e.message : "request failed",
          },
        },
      ]);
    }
  }

  function handleNext(next: NextAction) {
    if (!detail) return;
    if (next.kind === "retry") {
      retryRun(detail.session_id).then(() => location.reload());
      return;
    }
    if (next.kind === "package") {
      const url = (dossier?.tabs?.transfer as { download?: string | null })
        ?.download;
      if (url) {
        window.location.href = url;
        return;
      }
      setSurface("package");
      return;
    }
    // R459 (audit P0-4): the always-available deliverable — a direct,
    // authenticated download of the run's diagnostic record
    if (next.kind === "diagnostic") {
      window.location.href = diagnosticPackageUrl(detail.session_id);
      return;
    }
    if (next.kind === "new") {
      newProblem();
      return;
    }
    setSurface(next.surface ?? "overview");
  }

  const activeMode = runId ? "run" : slot ? "invention" : "fresh";

  return (
    <div className="workspace">
      <header className="ws-top">
        <button
          className="rail-toggle"
          onClick={() => setRailOpen(!railOpen)}
          type="button"
          aria-label="toggle navigation"
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
        {activeMode === "run" && (
          <button
            className="btn small ghost"
            type="button"
            data-share-btn
            onClick={() => {
              if (shareUrl) {
                navigator.clipboard?.writeText(shareUrl).catch(() => {});
                setShareCopied(true);
                setTimeout(() => setShareCopied(false), 2000);
                return;
              }
              if (detail)
                createShare(detail.session_id)
                  .then((sid) => {
                    if (sid) {
                      setShareUrl(`${window.location.origin}/share?id=${sid}`);
                    }
                  })
                  .catch(() => setShareUrl(null));
            }}
          >
            {shareCopied ? "Link copied" : shareUrl ? "Copy share link" : "Share"}
          </button>
        )}
        <button className="btn small ghost" onClick={newProblem} type="button">
          + New Discovery
        </button>
      </header>

      <div className={`ws-body ${surface && activeMode === "run" ? "ws-has-panel" : ""}`}>
        <div className={`ws-rail ${railOpen ? "open" : ""}`}>
          <Sidebar
            sessions={sessions}
            showcase={showcase}
            activeRun={runId}
            activeInvention={slot}
            onSelectRun={selectRun}
            onSelectInvention={selectInvention}
            onNewProblem={newProblem}
            health={health}
          />
        </div>
        {railOpen && (
          <div
            className="ws-rail-backdrop"
            onClick={() => setRailOpen(false)}
          />
        )}

        <main className="ws-main" data-ws-main>
          {activeMode === "fresh" &&
            (starting ? (
              <div className="loading">Starting the discovery…</div>
            ) : (
              <NewDiscoveryPane onStarted={onStarted} />
            ))}

          {activeMode === "run" &&
            (detail ? (
              <>
                {/* R459 (audit P1-2): a queued run SAYS it is queued */}
                {detail.queue_state?.queued && (
                  <div className="queue-note faint" data-queue-note>
                    {detail.queue_state.reason}
                  </div>
                )}
                <Conversation
                  detail={detail}
                  dossier={dossier}
                  events={events}
                  packageAvailable={packageAvailable}
                  asks={asks}
                  onOpenSurface={(s) => setSurface(s)}
                  onAsk={handleAsk}
                  onTechnical={() => setSurface("journal")}
                  onNextAction={handleNext}
                  onActionRound={(newId) => selectRun(newId)}
                />
              </>
            ) : runNotFound ? (
              <div className="errbox" style={{ marginTop: 24 }}>
                <b>Run not found.</b> This run id does not exist, or it
                belongs to a different visitor (runs are private to the
                session that created them). If you just started this run,
                use Discoveries — if it is empty, the run did not register
                and nothing was invented on it (an infrastructure state,
                never a scientific result).
              </div>
            ) : connLost ? (
              <div className="errbox" style={{ marginTop: 24 }} data-conn-lost>
                <b>The discovery service is not responding right now.</b> Your
                runs are persisted on the server and will reappear here when
                the service is reachable again — nothing about any discovery
                outcome is implied by this.
              </div>
            ) : (
              <div className="loading">Opening the discovery…</div>
            ))}

          {activeMode === "invention" &&
            (invention ? (
              <InventionStage
                detail={invention}
                loop={reality}
                slot={slot ?? ""}
              />
            ) : (
              <div className="loading">Opening the technology…</div>
            ))}
        </main>

        {activeMode === "run" && (
          <div className={`ws-panel ${surface ? "open" : ""}`} data-ws-panel>
            <Workspace
              detail={detail!}
              dossier={dossier}
              events={events}
              gauntlet={gauntlet}
              packageAvailable={packageAvailable}
              surface={surface}
              onClose={() => setSurface(null)}
              onSwitch={(s) => setSurface(s)}
            />
          </div>
        )}
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
