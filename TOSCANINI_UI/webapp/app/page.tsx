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

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  answerClarification,
  apiPost,
  askRun,
  createShare,
  diagnosticPackageUrl,
  attachUrl,
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
import { suppressStalePositives, isTerminal } from "@/lib/present";
import { latestChildOf, roundNumberOf } from "@/lib/rounds";
import Sidebar from "@/components/Sidebar";
// R466 (audit performance measurement, LCP acceptance): the landing is
// the cold-start surface and the LCP acceptance lives there ("<2.5s on
// mobile"). The run-mode and invention-mode component graphs (the
// conversation, the workspace panel, the invention stage, and their
// import subtrees — dossier sections, narrative, math rendering) were
// statically imported by this page chunk, so a first-time visitor
// parsed ~230KB of code the landing never executes. They are now
// route-mode-split chunks (next/dynamic — default exports unchanged,
// markup unchanged, contracts unchanged); the landing chunk carries
// only the hero/composer graph. ModelViewer's three.js stays in its
// own lazy chunk (unchanged — it was already split and loads only when
// a real geometry exists).
import dynamic from "next/dynamic";
const Conversation = dynamic(() => import("@/components/Conversation"));
const Workspace = dynamic(() => import("@/components/Workspace"));
const InventionStage = dynamic(() => import("@/components/InventionStage"));
// R466: isTerminal now comes from lib/present (the one definition it
// always re-exported) — importing it from RunNarrative kept the whole
// narrative component graph (and MathText's KaTeX CSS chunk) on the
// landing's render-blocking critical path for one boolean helper.

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

// R464 (audit P1-6): the file picker names what it takes — the
// engine-side ingestion table is the authority (text-like files and
// text PDFs are READ; images, CAD, and archives are stored on the
// record with a content hash, not text-extracted). The accept list
// mirrors the backend's own extension vocabulary; a visitor can still
// override it in the picker (an off-list file uploads and meets the
// honest ingestion verdict, never a silent pretense).
const UPLOAD_ACCEPT =
  ".txt,.md,.markdown,.csv,.tsv,.json,.log,.xml,.yaml,.yml,.html,.htm,.tex,.bib," +
  ".pdf,.docx,.png,.jpg,.jpeg,.gif,.webp,.step,.stp,.stl,.glb,.zip";

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
  // R471 (audit P0-6): a pasted URL reference rides the SAME pending
  // queue — one canonical ingestion path, one honest chip per input.
  const [pending, setPending] = useState<
    { key: string; label: string; file?: File; state: "uploading" | "ingested" | "rejected"; record?: AttachmentUploadResult }[]
  >([]);
  const [urlValue, setUrlValue] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  // drag-and-drop: a dropped file is the same as a selected file — it
  // uploads server-side the moment it lands
  const [dragging, setDragging] = useState(false);

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
      key: `file-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      label: file.name,
      file,
      state: "uploading" as const,
    }));
    setPending((prev) => [...prev, ...incoming]);
    for (const item of incoming) {
      try {
        const rec = await uploadAttachment(item.file);
        setPending((prev) =>
          prev.map((p) =>
            p.key === item.key
              ? { ...p, state: rec.rejected ? "rejected" : "ingested", record: rec }
              : p
          )
        );
      } catch {
        setPending((prev) =>
          prev.map((p) =>
            p.key === item.key
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

  // R471 (audit P0-6): the URL leg — a pasted reference is fetched
  // server-side (SSRF-guarded) and lands in the same pending queue;
  // the chip states the typed verdict (read / stored / blocked+reason).
  async function addUrl() {
    const u = urlValue.trim();
    if (!u) return;
    setError(null);
    setUrlValue("");
    const item = {
      key: `url-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      label: u,
      state: "uploading" as const,
    };
    setPending((prev) => [...prev, item]);
    try {
      const rec = await attachUrl(u);
      setPending((prev) =>
        prev.map((p) =>
          p.key === item.key
            ? { ...p, state: rec.rejected ? "rejected" : "ingested", record: rec }
            : p
        )
      );
    } catch {
      setPending((prev) =>
        prev.map((p) =>
          p.key === item.key
            ? {
                ...p,
                state: "rejected",
                record: { name: u, rejected: true,
                          ingestion: { status: "FETCH_FAILED",
                                       note: "the reference could not be delivered" } },
              }
            : p
        )
      );
    }
  }

  return (
    <section className="hero workspace-hero" data-new-discovery>
      <h1 className="brand-statement">DISCOVER. INVENT. ANYTHING.</h1>
      <h2 className="ask-title">What do you want to discover?</h2>
      <div
        className={`ask${dragging ? " dragging" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={(e) => {
          if (e.currentTarget.contains(e.relatedTarget as Node)) return;
          setDragging(false);
        }}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          void onFiles(e.dataTransfer.files);
        }}
      >
        <textarea
          autoFocus
          placeholder="What problem do you want to solve or invent?"
          // R471 (audit P2-3): the placeholder is not an accessible name
          // — the primary input gets an explicit label.
          aria-label="Describe the problem you want to solve or invent"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void submit();
            }
          }}
        />
        {dragging && (
          <div className="ask-dropnote" role="status">
            Drop to attach — it is read server-side and joins the
            investigation&apos;s record
          </div>
        )}
        {pending.length > 0 && (
          <div className="ask-attachments" data-pending-attachments>
            {pending.map((p, i) => {
              // R464 (audit P1-6 / red-team table): the chip states WHAT
              // THE ENGINE DID with the file — text was read, or the file
              // is stored on the record without text extraction. A user
              // attaching a diagram must never believe it was read into
              // the investigation when it was only stored.
              const ing = p.record?.ingestion?.status;
              const stored =
                p.state === "ingested" &&
                (ing === "STORED" || ing === "STORED_TEXT_UNREADABLE");
              return (
                <span
                  className={`ask-attachment ${p.state === "rejected" ? "bad" : ""}`}
                  key={p.key}
                  title={p.record?.ingestion?.note ?? (p.state === "uploading" ? "uploading…" : undefined)}
                >
                  {p.label}
                  {p.state === "ingested" && ing === "TEXT_EXTRACTED" && (
                    <span className="faint">
                      {" · "}{p.record?.ingestion?.text_chars_total ?? 0} characters read
                    </span>
                  )}
                  {stored && (
                    <span className="faint" data-attachment-stored>
                      {" · "}stored on the record{ing === "STORED_TEXT_UNREADABLE" ? " — no text could be read from it" : " — not read as text"}
                    </span>
                  )}
                  {p.state === "uploading" && <span className="faint"> · fetching…</span>}
                  {p.state === "rejected" && (
                    <span className="faint">
                      {" · "}{p.record?.ingestion?.note ?? "could not be read"}
                    </span>
                  )}
                  <button
                    type="button"
                    className="ask-attachment-x"
                    aria-label={`remove ${p.label}`}
                    onClick={() =>
                      setPending((prev) => prev.filter((_, j) => j !== i))
                    }
                  >
                    ×
                  </button>
                </span>
              );
            })}
          </div>
        )}
        <div className="ask-foot">
          <span className="hint">
            Enter to start · Shift+Enter for a new line
          </span>
          <div className="ask-actions">
            <input
              ref={fileRef}
              type="file"
              multiple
              accept={UPLOAD_ACCEPT}
              hidden
              aria-label="Attach documents"
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
        {/* R471 (audit P0-6): the URL/reference leg of the input model —
            fetched server-side, SSRF-guarded; the chip carries the typed
            verdict. Enter here adds the reference instead of starting. */}
        <div className="ask-urlrow">
          <input
            type="url"
            className="ask-url"
            placeholder="Paste a reference URL (optional) — fetched and read server-side"
            aria-label="Reference URL"
            value={urlValue}
            onChange={(e) => setUrlValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void addUrl();
              }
            }}
          />
          <button
            type="button"
            className="btn small ghost"
            onClick={() => void addUrl()}
            disabled={!urlValue.trim()}
          >
            + Add reference
          </button>
        </div>
        {/* R464 (audit P1-6): types and the size limit, said up front —
            the ingestion verdict on each chip stays the authority */}
        <div className="ask-files-hint faint">
          Documents up to 20 MB, plus web references by URL. Text files,
          text PDFs, and web pages are read server-side; images, CAD, and
          archives are stored on the record with a content hash — the
          chip under each input says which happened.
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
      {/* R464 (audit P0-2): the duration is product-critical information —
          stated at full visual weight BEFORE the first run, not whispered
          in keyboard-hint grey. The phrasing stays honest: minutes as a
          class, never a precise promise the engine cannot keep. */}
      <div className="hero-note" data-hero-note>
        <b>A discovery run takes minutes, not seconds.</b> The engine
        investigates evidence, competing mechanisms, and adversarial
        tests before it answers — you can leave this page and come back;
        everything is recorded on the server and the conversation
        resumes from the record.
      </div>
      {/* R464 (audit P0-3): first-use orientation — one concrete example
          of what a finished discovery looks like, so a first-time visitor
          can answer "what do I receive?" within 20 seconds of landing.
          Labeled as an example; every line mirrors the real result
          vocabulary (outcome, candidates with honest maturity, package,
          decisive experiment). */}
      <div className="expect-card" data-expect-card>
        <div className="expect-kicker">Example result</div>
        <h3 className="expect-h">
          What a finished discovery looks like
        </h3>
        <p className="expect-body">
          You describe an engineering problem in your own words. The
          engine investigates it and answers in one conversation —
          exactly this shape:
        </p>
        <ul className="expect-list">
          <li>the evidence it found, and where each source came from</li>
          <li>competing candidate mechanisms, each with what would kill it</li>
          <li>the adversarial challenge — which candidates survived</li>
          <li>the engineering: geometry, parameters, and a 3D technology model</li>
          <li>the decisive experiment that would settle the question</li>
          <li>a downloadable technology package with all of it inside</li>
        </ul>
        <span className="expect-tag">
          An illustrative example — every real result states its own
          evidence and its own limits, never more.
        </span>
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
// R466 (performance measurement, LCP acceptance): the shell's mode used to
// come from useSearchParams, whose server snapshot bails the static
// export's prerender to the Suspense fallback ("Loading…") — the
// prerendered landing HTML was EMPTY and every first paint waited for
// full React hydration (~3s of render delay at mobile-class CPU; the
// Lighthouse LCP element was a text node that only existed after
// hydration). The location search is now read through a
// hydration-gated store: the server snapshot AND the first client
// render both say "landing" (byte-identical HTML → no hydration
// mismatch), and the real query (?run=… / ?invention=…) applies in the
// post-hydration effect — the same moment the previous design fetched
// its data anyway. Navigations notify through patched
// history.pushState/replaceState (router.push's transport) + popstate
// (back/forward/direct edits) — every entry point useSearchParams
// served, with the landing now statically prerendered.
const searchNotify = new Set<() => void>();
function notifySearch() {
  for (const fn of searchNotify) fn();
}
function subscribeSearch(fn: () => void): () => void {
  searchNotify.add(fn);
  return () => searchNotify.delete(fn);
}
function useWindowSearch(): string {
  const [hydrated, setHydrated] = useState(false);
  const [search, setSearch] = useState("");
  useEffect(() => {
    const apply = () => setSearch(window.location.search);
    for (const kind of ["pushState", "replaceState"] as const) {
      const orig = history[kind].bind(history);
      history[kind] = (...args: Parameters<typeof history.pushState>) => {
        const r = orig(...args);
        notifySearch();
        return r;
      };
    }
    window.addEventListener("popstate", onPop);
    function onPop() {
      apply();
      for (const fn of searchNotify) fn();
    }
    apply();
    setHydrated(true);
    return () => {
      window.removeEventListener("popstate", onPop);
    };
  }, []);
  useEffect(() => subscribeSearch(() => setSearch(window.location.search)), []);
  return hydrated ? search : "";
}

function WorkspaceInner() {
  const search = useWindowSearch();
  const router = useRouter();
  const runId = useMemo(() => new URLSearchParams(search).get("run"), [search]);
  const slot = useMemo(
    () => new URLSearchParams(search).get("invention"),
    [search]
  );

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
  // R461 (independent audit P1-7): below the drawer breakpoint the rail
  // is an OFFSCREEN fixed panel when closed — it must be INERT and
  // aria-hidden then, or keyboard users tab into invisible controls.
  // The breakpoint is matched client-side (CSS owns the layout truth:
  // ≤1180px per globals.css); on desktop the rail is inline and never
  // inert. React 19 renders `inert` as the native boolean attribute.
  const [railInline, setRailInline] = useState(true);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 1180px)");
    const update = () => setRailInline(!mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);
  const railHidden = !railInline && !railOpen;
  const [starting, setStarting] = useState(false);
  // the contextual workspace surface (brief §12) — null = closed
  const [surface, setSurface] = useState<SurfaceId | null>(null);
  const [asks, setAsks] = useState<{ question: string; response: AskResponse }[]>([]);
  // R471 (audit P0-2): the Resume action's honest outcome line — an
  // accepted retry reloads into PENDING/RUNNING; a typed refusal is
  // STATED here instead of silently doing nothing (the measured
  // defect: the thrown error swallowed the reload and the UI froze on
  // the interrupted card).
  const [retryNote, setRetryNote] = useState<string | null>(null);
  // R459 (audit P1-3): the share flow — the backend endpoint existed;
  // the product surface now offers it.
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [shareCopied, setShareCopied] = useState(false);
  const autoOpened = useRef<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const evtTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const es = useRef<EventSource | null>(null);
  // R467 (the R466 disclosed P2: the store cold-start 404 window): the
  // engine-proven-healthy marker for THIS browser session. A 404 on
  // /api/run/{id}/result is only evidence the run is absent when the
  // engine has answered /api/health ok at least once around it — during
  // a freshly (re)started process the first polls can hit an
  // enumeration-safe 404 before the store finishes hydrating (observed
  // live twice in R466), and the Art. XXI §3 discipline applies verbatim:
  // a provider/store failure is not absence. Reset to false whenever a
  // health poll FAILS, so a mid-session restart gets the same honest
  // grading as a cold start.
  const engineSeenUp = useRef(false);

  // R463 (audit P2-4): Alt+W opens/closes the contextual workspace
  // panel, Escape closes it — a keyboard path to the same toggle the
  // workspace tabs offer (works at every viewport width; the surface
  // toggle buttons remain the primary affordance). Ignored while the
  // user is typing in an input, textarea, or contenteditable field.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const t = e.target as HTMLElement | null;
      const typing = !!t && (t.tagName === "INPUT"
        || t.tagName === "TEXTAREA" || t.isContentEditable);
      if (e.key === "w" && e.altKey && !typing) {
        e.preventDefault();
        setSurface((s) => (s ? null : "overview"));
      } else if (e.key === "Escape" && !typing) {
        setSurface((s) => (s ? null : s));
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // ---- rails + health ----
  useEffect(() => {
    listSessions().then(setSessions).catch(() => setSessions([]));
    listShowcase().then(setShowcase).catch(() => setShowcase([]));
    getHealth()
      .then((h) => {
        engineSeenUp.current = !!h?.ok;
        setHealth(h);
      })
      .catch(() => {
        engineSeenUp.current = false;
        setHealth(null);
      });
    const h = setInterval(() => {
      // R458-C2 (§21): a hidden tab needs no engine traffic — polling
      // resumes on return; SSE and the poll keep the same truth
      if (typeof document !== "undefined" && document.hidden) return;
      getHealth()
        .then((hh) => {
          engineSeenUp.current = !!hh?.ok;
          setHealth(hh);
        })
        .catch(() => {
          engineSeenUp.current = false;
        });
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
          // R467 (the R466 P2 fix): grade a 404 toward "run not found"
          // ONLY when the engine has proven healthy this session —
          // before that, a 404 is the cold-start/hydration window (or
          // the host edge answering for a starting process), and the
          // honest state is the connection-lost copy (persisted,
          // recovering, no verdict).
          // R470 (the re-audit's P2: "fast-fail run not found < 2 s"):
          // once the engine is up, the first 404 schedules ONE 750 ms
          // confirmation re-check; two independent 404s render the
          // verdict in ~1-1.8 s (the old 4-miss rule at a 2.5 s
          // interval held the ambiguity window at ~10 s). A
          // single-sample verdict is never rendered — the confirmation
          // poll is a real second request, and the standing interval
          // remains the backstop.
          if (engineSeenUp.current) {
            misses += 1;
            if (misses === 1) {
              setTimeout(() => {
                if (alive) poll();
              }, 750);
            }
            if (misses >= 2) setRunNotFound(true);
          } else {
            connMisses += 1;
            if (connMisses >= 3 && connMisses % 3 === 0)
              setConnLost(true);
          }
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
      setRetryNote(null);
      retryRun(detail.session_id)
        .then((outcome) => {
          if (outcome.ok) {
            // the audit's acceptance: the UI refreshes and shows
            // PENDING/RUNNING — the reload renders the new state.
            location.reload();
            return;
          }
          // a typed refusal is shown, never swallowed
          setRetryNote(
            outcome.refusal === "RETRY_NOT_PERMITTED"
              ? `This run can't be resumed right now (its state is ${outcome.sessionStatus ?? "unknown"}). ${outcome.error ?? ""}`.trim()
              : outcome.error ?? "The resume request was refused."
          );
        })
        .catch(() => {
          setRetryNote(
            "The resume request could not be delivered — the run's state on the page will refresh with the truth."
          );
          location.reload();
        });
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

  // R464 (audit P0-1/P1-2): the focused run's ROUND STRUCTURE, derived
  // from the parentage the engine already records (parent_session_id
  // on the row/detail). The back-link names which round you are IN;
  // the forward link exists on a parent that forked — previously the
  // thread was only navigable backwards, and a user who steered could
  // not return to their newest round without hunting the rail.
  const byId = useMemo(
    () => new Map(sessions.map((s) => [s.session_id, s] as const)),
    [sessions]
  );
  const currentRound = detail ? roundNumberOf(detail, byId) : 1;
  const childOfCurrent = detail
    ? latestChildOf(detail.session_id, sessions)
    : null;

  return (
    <div className="workspace">
      <header className="ws-top">
        <button
          className="rail-toggle"
          onClick={() => setRailOpen(!railOpen)}
          type="button"
          aria-label="toggle navigation"
          aria-expanded={railOpen}
          onKeyDown={(e) => {
            // R461 (audit P1-7): Escape dismisses the drawer and the
            // focus never lands inside the now-inert panel.
            if (e.key === "Escape" && railOpen) setRailOpen(false);
          }}
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
        <div
          className={`ws-rail ${railOpen ? "open" : ""}`}
          inert={railHidden || undefined}
          aria-hidden={railHidden || undefined}
        >
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
                {/* R463 (audit P1-2) + R464 (P0-1): steering continuity
                    — a forked round names WHICH round of the thread it is
                    and links back to the round it steered from; a parent
                    that forked links forward to its newest round. The
                    whole investigation stays one navigable unit. */}
                {(detail.parent_session_id || childOfCurrent) && (
                  <div className="fork-row" data-fork-row>
                    {detail.parent_session_id && (
                      <a
                        className="fork-note faint"
                        data-fork-note
                        data-round={currentRound}
                        href={`/?run=${encodeURIComponent(detail.parent_session_id)}`}
                      >
                        {currentRound > 1
                          ? `Round ${currentRound} — continued from the earlier round`
                          : "Continued from the earlier round"}{" of this investigation →"}
                      </a>
                    )}
                    {childOfCurrent && isTerminal(detail.status) && (
                      <a
                        className="fork-note faint fwd"
                        data-fork-fwd
                        href={`/?run=${encodeURIComponent(childOfCurrent.session_id)}`}
                      >
                        This investigation continued in a new round →
                      </a>
                    )}
                  </div>
                )}
                {/* R471 (audit P0-2): the Resume action's outcome is
                    stated, never swallowed — an accepted retry reloads
                    into the new state; a typed refusal or a delivery
                    failure says exactly what happened. */}
                {retryNote && (
                  <div className="errbox" style={{ marginTop: 16 }} data-retry-note>
                    {retryNote}
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
                  roundNumber={currentRound}
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
