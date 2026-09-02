// Job-API client. The frontend only ever speaks this API (R389 Phase 7):
//   POST /api/run {text}
//   GET  /api/run/{id}/result
//   GET  /api/run/{id}/stream      (SSE)
//   GET  /api/sessions
//   GET  /api/showcase[...]
//   POST /api/showcase/{slot}/evaluate
// All paths are same-origin — Next.js rewrites forward them to the engine
// service, so no CORS and no internal-module coupling.

import type {
  EvalResult,
  RealityLoopRecord,
  Refusal,
  SessionDetail,
  SessionRow,
  ShowcaseDetail,
  ShowcaseRow,
} from "./types";

const JSON_HEADERS = { "Content-Type": "application/json" };

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

export async function listSessions(): Promise<SessionRow[]> {
  const data = await json<{ sessions: SessionRow[] }>(
    await fetch("/api/sessions", { cache: "no-store" })
  );
  return data.sessions ?? [];
}

export async function startRun(text: string): Promise<SessionRow> {
  return json<SessionRow>(
    await fetch("/api/run", {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify({ text }),
    })
  );
}

export async function getRunResult(id: string): Promise<SessionDetail> {
  return json<SessionDetail>(
    await fetch(`/api/run/${id}/result`, { cache: "no-store" })
  );
}

export async function retryRun(id: string): Promise<unknown> {
  return json(await fetch(`/api/sessions/${id}/retry`, { method: "POST" }));
}

export async function listShowcase(): Promise<ShowcaseRow[]> {
  const data = await json<{ showcase: ShowcaseRow[] }>(
    await fetch("/api/showcase", { cache: "no-store" })
  );
  return data.showcase ?? [];
}

export async function getShowcase(slot: string): Promise<ShowcaseDetail> {
  return json<ShowcaseDetail>(
    await fetch(`/api/showcase/${slot}`, { cache: "no-store" })
  );
}

export async function evaluateParam(
  slot: string,
  param_id: string,
  value: number
): Promise<{ ok: true; result: EvalResult } | { ok: false; refusal: Refusal }> {
  const res = await fetch(`/api/showcase/${slot}/evaluate`, {
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
  const res = await fetch(`/api/showcase/${slot}/reality-loop`, {
    cache: "no-store",
  });
  if (!res.ok) return null;
  return (await res.json()) as RealityLoopRecord;
}
