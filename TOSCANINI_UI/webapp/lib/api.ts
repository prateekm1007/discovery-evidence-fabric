// Job-API client. The frontend only ever speaks this API (R389 Phase 7):
//   POST /api/run {text}
//   GET  /api/run/{id}/result
//   GET  /api/run/{id}/stream      (SSE)
//   GET  /api/sessions
//   GET  /api/showcase[...]
//   POST /api/showcase/{slot}/evaluate
// All paths are same-origin — Next.js rewrites forward them to the engine
// service, so no CORS and no internal-module coupling.
//
// R447 (run-not-found fix): the owner capability transport that does not
// depend on cookie policy. HuggingFace embeds this app in a third-party
// iframe where SameSite cookies are blocked; relying on the tosca_owner
// cookie alone made every browser request arrive as a NEW visitor — runs
// 404'd ("Run not found") and the history rail was empty while the runs
// existed on disk the whole time. The engine now returns our own opaque
// owner_key (run creation + /api/sessions) and accepts it back via the
// X-Tosca-Owner header; we persist it client-side and attach it to every
// call. The cookie path keeps working unchanged wherever cookies are
// allowed — the header converges with it server-side.

import type {
  AskResponse,
  CIO,
  DossierBody,
  EssayBody,
  EventsBody,
  EvalResult,
  HealthSummary,
  RealityLoopRecord,
  Refusal,
  RunStateObject,
  SessionDetail,
  SessionRow,
  ShowcaseDetail,
  ShowcaseRow,
} from "./types";

const JSON_HEADERS = { "Content-Type": "application/json" };
const OWNER_KEY_STORAGE = "tosca_owner_key";
const OWNER_HEADER = "X-Tosca-Owner";

export function storedOwnerKey(): string | null {
  try {
    return window.localStorage.getItem(OWNER_KEY_STORAGE);
  } catch {
    // storage partitioned or unavailable — the cookie transport still
    // applies wherever the browser allows it
    return null;
  }
}

export function rememberOwnerKey(key: string | null | undefined): void {
  if (!key) return;
  try {
    window.localStorage.setItem(OWNER_KEY_STORAGE, key);
  } catch {
    /* same as above — no client-side persistence, cookie remains */
  }
}

// the SSE stream URL carrying the capability (EventSource cannot set
// request headers — the engine accepts the SAME opaque token as the
// stream route's `owner` query parameter)
export function streamUrl(id: string): string {
  const key = storedOwnerKey();
  return `/api/run/${id}/stream${key ? `?owner=${encodeURIComponent(key)}` : ""}`;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = "";
    try {
      detail = JSON.stringify(await res.json());
    } catch {
      /* body was not json — leave detail empty */
    }
    throw new Error(`${res.status} ${res.statusText} ${detail}`.trim());
  }
  return res.json() as Promise<T>;
}

// R447: every API call carries the persisted owner capability (the
// header is a no-op where the cookie already works — same key value).
async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  const key = storedOwnerKey();
  if (key && !headers.has(OWNER_HEADER)) headers.set(OWNER_HEADER, key);
  return fetch(path, { ...init, headers, cache: "no-store" });
}

// R395: the ask endpoint returns the answer INSIDE a 200 body even for
// honest refusals (NOT_IN_RECORD etc.) — only transport/protocol-level
// failures are HTTP errors. This keeps the honest states first-class.
export async function askRun(id: string, question: string): Promise<AskResponse> {
  return json<AskResponse>(
    await apiFetch(`/api/run/${id}/ask`, {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify({ question }),
    })
  );
}

export async function askInvention(slot: string, question: string): Promise<AskResponse> {
  return json<AskResponse>(
    await apiFetch(`/api/showcase/${slot}/ask`, {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify({ question }),
    })
  );
}

export async function getHealth(): Promise<HealthSummary | null> {
  try {
    return await json<HealthSummary>(await apiFetch("/api/health"));
  } catch {
    return null;
  }
}

export async function listSessions(): Promise<SessionRow[]> {
  const data = await json<{ sessions: SessionRow[]; owner_key?: string }>(
    await apiFetch("/api/sessions")
  );
  // R447: capture our own capability whenever the engine hands it back
  // (cookie-transport visitors converge to the header transport here)
  rememberOwnerKey(data.owner_key);
  return data.sessions ?? [];
}

export async function startRun(text: string): Promise<SessionRow> {
  const session = await json<SessionRow & { owner_key?: string }>(
    await apiFetch("/api/run", {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify({ text }),
    })
  );
  // R447: persist the capability the engine just issued for THIS run —
  // the embedded-iframe context cannot rely on the Set-Cookie
  rememberOwnerKey(session.owner_key);
  return session;
}

export async function getRunResult(id: string): Promise<SessionDetail> {
  return json<SessionDetail>(await apiFetch(`/api/run/${id}/result`));
}

export async function retryRun(id: string): Promise<unknown> {
  return json(await apiFetch(`/api/sessions/${id}/retry`, { method: "POST" }));
}

export async function listShowcase(): Promise<ShowcaseRow[]> {
  const data = await json<{ showcase: ShowcaseRow[] }>(
    await apiFetch("/api/showcase")
  );
  return data.showcase ?? [];
}

export async function getShowcase(slot: string): Promise<ShowcaseDetail> {
  return json<ShowcaseDetail>(await apiFetch(`/api/showcase/${slot}`));
}

export async function evaluateParam(
  slot: string,
  param_id: string,
  value: number
): Promise<{ ok: true; result: EvalResult } | { ok: false; refusal: Refusal }> {
  const res = await apiFetch(`/api/showcase/${slot}/evaluate`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ param_id, value }),
  });
  if (res.status === 409) {
    return { ok: false, refusal: (await res.json()) as Refusal };
  }
  return { ok: true, result: await json<EvalResult>(res) };
}

export async function getRealityLoop(
  slot: string
): Promise<RealityLoopRecord | null> {
  const res = await apiFetch(`/api/showcase/${slot}/reality-loop`);
  if (!res.ok) return null;
  return (await res.json()) as RealityLoopRecord;
}

// R414: the canonical run state (directive §4) — light live payload for
// phase progression and the four terminal outcomes.
export async function getRunState(id: string): Promise<RunStateObject> {
  return json<RunStateObject>(await apiFetch(`/api/run/${id}/state`));
}

// R414: the Canonical Invention Object (directive §12) — the ONE object
// the browser renders for a run's invention surface.
export async function getCIO(id: string): Promise<CIO> {
  return json<CIO>(await apiFetch(`/api/run/${id}/cio`));
}

// R419 section 11: the technical essay — the same 8 sections the
// package PDF renders, as structured JSON from the canonical state.
export async function getEssay(
  id: string
): Promise<EssayBody | null> {
  try {
    return json<EssayBody>(await apiFetch(`/api/run/${id}/essay`));
  } catch {
    return null; // honest absence — the argument panel still renders
  }
}

// R430.1 section 12: the persisted event history — the refresh-recovery
// source (the workspace hydrates from this, then appends live SSE
// science events).
export async function getEvents(id: string): Promise<EventsBody> {
  return json<EventsBody>(await apiFetch(`/api/run/${id}/events`));
}

// R430.1 sections 3-6: the Technology Dossier projection — exists from
// the first moment the investigation has a canonical state; the right
// pane renders it and NEVER re-derives state client-side.
export async function getDossier(id: string): Promise<DossierBody | null> {
  try {
    return await json<DossierBody>(await apiFetch(`/api/run/${id}/dossier`));
  } catch {
    return null; // honest absence — the investigation pane still works
  }
}
