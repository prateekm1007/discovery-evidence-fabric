#!/usr/bin/env node
/** zai_gateway.mjs — sandbox-local OpenAI-compatible LLM gateway.
 *
 * WHY THIS EXISTS (recorded 2026-08-30, R375 transport unblock):
 * The engine's only credentialed providers were NVIDIA (measured latency
 * collapse: 35 s .. >240 s variance on identical calls; tiny-call
 * timeouts re-verified 2026-08-30) and Mistral (401, re-verified).
 * The M1 campaign was transport-bound on this single path. The sandbox
 * provides a healthy LLM transport via the z-ai CLI (embedded model,
 * verified live: READY probe, ~2 s). This gateway exposes that transport
 * as an OpenAI-compatible /v1/chat/completions endpoint on 127.0.0.1 so
 * the engine's llm_registry can use it as an ordinary provider.
 *
 * Contract (Constitution Art. XVIII — the LLM is untrusted):
 *  - Bearer-token auth (ZAI_GATEWAY_KEY); 401 otherwise.
 *  - Non-empty content or 500 (never a silent empty completion).
 *  - Every call appended to a JSONL log with prompt/content hashes for
 *    provenance (the registry additionally records its own hashes).
 *  - English-only directive is enforced by the registry, not here.
 *  - The gateway is INFRASTRUCTURE: it grants no epistemic authority to
 *    any model output (Art. XVIII); it is loop-local transport only.
 *
 * Art. XXVI disclosure: builder-operated transport. All epistemic gates
 * run unchanged in the engine.
 *
 * R6 FAST/LEAN hardening (owner directive 2026-11-11; measured basis
 * recorded in ENGINE_RUNS/r6_fresh_run1_*): the R6 fresh-run measurement
 * (commit b7fdb2ccc944, 7 DEV problems) showed the transport itself was
 * the dominant wall cost:
 *  (1) 429 storms — the upstream quota admits ~3-5 calls/60 s (measured
 *      live: every RATE_LIMITED_RETRY in the run window followed 3-5 OK
 *      calls in the prior 60 s); the old ladder slept 30+60+90 s per
 *      exhausted call (180 s of pure sleep per logical call, p02 burned
 *      110 gateway attempts in 300 s, 5/7 problems hit the hard timeout);
 *  (2) a wedged request (client request never completed per node's
 *      parser) blocked a caller FOREVER — the run's judge-calibration
 *      phase sat in HTTPResponse.readinto with no response and no log
 *      entry, rescued only by the engine's own 900 s socket budget.
 * Fixes, transport plumbing only (Art. X: one transport path unchanged;
 * Art. XXV: measured reality recorded over the older constants):
 *  - ADAPTIVE PACING (AIMD): call starts are globally serialized with a
 *    minimum interval that starts at PACING_START_S, doubles on each 429
 *    (capped PACING_MAX_S), and decays by 1 s per OK (floor PACING_START_S).
 *    Self-tunes to the provider's real quota instead of a hardcoded rate.
 *  - BOUNDED 429 LADDER: one retry after PACING_429_BACKOFF_S (20 s,
 *    measured quota window scale), then a typed failure to the caller —
 *    the engine's own retry ladder owns the remainder (never 180 s of
 *    gateway sleep per call).
 *  - REQUEST WATCHDOG: explicit server.requestTimeout/headersTimeout —
 *    a client request that never completes is destroyed in bounded time
 *    (the caller gets a reset and its own retry owns a fresh connection),
 *    so no caller can hang forever on a silent connection.
 *
 * Usage:
 *   ZAI_GATEWAY_KEY=<secret> node scripts/zai_gateway.mjs [port]
 *   (default port 8787; binds 127.0.0.1 only)
 */
import http from "node:http";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import os from "node:os";

const PORT = Number(process.argv[2] || process.env.ZAI_GATEWAY_PORT || 8787);
const KEY = process.env.ZAI_GATEWAY_KEY || "";
const LOG = process.env.ZAI_GATEWAY_LOG ||
  "/home/z/my-project/discovery-evidence-fabric/ENGINE_RUNS/zai_gateway_calls.jsonl";

if (!KEY) {
  console.error("[zai-gateway] refusing to start: ZAI_GATEWAY_KEY unset");
  process.exit(2);
}
fs.mkdirSync(path.dirname(LOG), { recursive: true });

const sha = (s) => crypto.createHash("sha256").update(s, "utf8").digest("hex");

function logCall(entry) {
  try { fs.appendFileSync(LOG, JSON.stringify(entry) + "\n"); } catch (_) {}
}

/** One completion through the z-ai CLI (bun script; robust resolution of
 *  the SDK across container layouts). Resolves {content, model, usage}.
 *  429-aware: the upstream GLM endpoint enforces a request quota whose
 *  window can exceed a minute (measured 2026-08-30: three candidates in
 *  one batch exhausted it). The gateway retries 429s with 30/60/90 s
 *  backoff BEFORE surfacing the error, so the engine's own retry budget
 *  (2 attempts, 2-4 s apart — tuned for network errors, not quotas) is
 *  not burned on a transient rate limit.
 *
 *  R458-C1 (model-capability benchmark, disclosed in place — Art. LXIV):
 *  the requested model id "glm-4-plus-thinking" maps to the z-ai CLI's
 *  OWN --thinking flag (the same serving model, reasoning mode on).
 *  This is transport plumbing for the CLI's own mode switch — NOT a new
 *  provider, NOT a second model authority: the served weights are the
 *  grant's single embedded model either way, and the mode is recorded
 *  verbatim in the gateway call log (model field) and the engine's
 *  routing ledger. Any other model id passes through unchanged (the
 *  CLI serves the grant's current model; the id is recorded, never
 *  silently rewritten). */
// R6 adaptive pacing (AIMD) — measured basis in the header. Pure function
// exported for the self-test; the state lives in `pacing` below.
export const PACING_START_S = 4;
export const PACING_MAX_S = 25;
export const PACING_429_BACKOFF_S = 20;
export function nextPacing(curS, is429) {
  if (is429) return Math.min(curS * 2, PACING_MAX_S);
  return Math.max(curS - 1, PACING_START_S);
}
const pacing = { intervalS: PACING_START_S, lastStartMs: 0 };

/** Serialize call STARTS atomically (audit P1-12): a FIFO queue of
 *  call slots. The old defect: the delay was computed BEFORE the slot
 *  was reserved — two concurrent callers each read the same stale
 *  lastStartMs, so caller B started `intervalS` after ITS OWN enqueue
 *  moment, not after caller A's start: overlapping starts, quota
 *  pressure. Now: a slot's start is computed against the PREVIOUS
 *  slot's reserved start (lastStartMs), and lastStartMs is written AT
 *  SCHEDULE TIME (atomic with the queue step), never at timer fire.
 *  Two concurrent callers can never schedule overlapping starts.
 *  A 429 that doubles intervalS takes effect from the NEXT slot on. */
const pacingQueue = [];
let pacingPump = false;
function _pumpPacing() {
  if (pacingPump || !pacingQueue.length) return;
  pacingPump = true;
  const resolve = pacingQueue.shift();
  const now = Date.now();
  const gap = pacing.intervalS * 1000 - (now - pacing.lastStartMs);
  const waitMs = gap > 0 ? gap : 0;
  pacing.lastStartMs = now + waitMs; // reserve the slot NOW
  setTimeout(() => {
    pacingPump = false;
    resolve(waitMs);
    _pumpPacing();
  }, waitMs);
}
function waitPacing() {
  return new Promise(resolve => {
    pacingQueue.push(resolve);
    _pumpPacing();
  });
}
/** Test hook (P1-12 concurrency test): schedule a FIFO slot without
 *  running a call; resolves the waited ms. */
export function reservePacingSlot() {
  return waitPacing();
}
/** Test hook: set the pacing interval for the queue. */
export function _withPacingIntervalForTest(intervalS) {
  pacing.intervalS = intervalS;
  return pacing;
}

function zaiComplete(messages, timeoutMs, thinkingMode = false) {
  return new Promise((resolve, reject) => {
    const system = messages.filter(m => m.role === "system")
      .map(m => m.content).join("\n") || undefined;
    const user = messages.filter(m => m.role === "user")
      .map(m => m.content).join("\n\n");
    if (!user.trim()) return reject(new Error("no user content"));
    const attempt = async (triesLeft, backoffs) => {
      const pacingWaitMs = await waitPacing();
      const tmp = path.join(os.tmpdir(),
        `zai_gw_${crypto.randomBytes(6).toString("hex")}.json`);
      const args = ["chat", "--prompt", user, "-o", tmp];
      if (system) args.push("--system", system);
      if (thinkingMode) args.push("--thinking");
      const t0 = Date.now();
      const child = spawn("z-ai", args, { stdio: ["ignore", "ignore", "pipe"] });
      let stderr = "";
      child.stderr.on("data", d => { stderr += d.toString(); });
      const timer = setTimeout(() => {
        child.kill("SIGKILL");
        reject(new Error(`z-ai CLI timeout after ${timeoutMs} ms`));
      }, timeoutMs);
      child.on("error", e => { clearTimeout(timer); reject(e); });
      child.on("close", code => {
        clearTimeout(timer);
        const is429 = /429|Too many requests/i.test(stderr);
        if (code !== 0 && is429) {
          // AIMD: every 429 doubles the pacing interval (the measured
          // quota is global — one 429 means every caller slows down).
          pacing.intervalS = nextPacing(pacing.intervalS, true);
        }
        if (code !== 0 && is429 && triesLeft > 0) {
          const wait = backoffs[0];
          logCall({
            ts: new Date().toISOString(), status: "RATE_LIMITED_RETRY",
            wait_s: wait, pacing_s: pacing.intervalS,
            error: stderr.slice(0, 120),
          });
          return setTimeout(() => attempt(triesLeft - 1, backoffs.slice(1)),
            wait * 1000);
        }
        if (code !== 0) {
          try { fs.unlinkSync(tmp); } catch (_) {}
          return reject(new Error(
            `z-ai CLI exit ${code}: ${stderr.slice(0, 300)}`));
        }
        try {
          const data = JSON.parse(fs.readFileSync(tmp, "utf8"));
          fs.unlinkSync(tmp);
          const content = data?.choices?.[0]?.message?.content || "";
          if (!content.trim()) {
            return reject(new Error(
              `empty content (finish_reason=${data?.choices?.[0]?.finish_reason})`));
          }
          resolve({
            content,
            model: data?.model || "zai-unknown",
            finish_reason: data?.choices?.[0]?.finish_reason || "stop",
            usage: data?.usage || null,
            latency_ms: Date.now() - t0,
            pacing_s: pacing.intervalS,
            pacing_wait_ms: pacingWaitMs,
          });
          // AIMD decay: a clean OK proves the current interval is safe.
          pacing.intervalS = nextPacing(pacing.intervalS, false);
        } catch (e) {
          try { fs.unlinkSync(tmp); } catch (_) {}
          reject(new Error(`output parse failed: ${e.message}`));
        }
      });
    };
    // R6: ONE bounded 429 retry (20 s — measured quota-window scale),
    // then a typed failure. The old 30/60/90 ladder burned 180 s of
    // gateway sleep per exhausted call and was the R6 measured dominant
    // wall cost (the header records the numbers).
    attempt(1, [PACING_429_BACKOFF_S]).catch(reject);
  });
}

const server = http.createServer(async (req, res) => {
  const json = (code, obj) => {
    res.writeHead(code, { "Content-Type": "application/json" });
    res.end(JSON.stringify(obj));
  };
  if (req.method === "GET" && req.url === "/healthz") {
    return json(200, { status: "ok", uptime_s: process.uptime() | 0 });
  }
  if (req.method !== "POST" || !req.url.startsWith("/v1/chat/completions")) {
    return json(404, { error: { message: "not found" } });
  }
  const auth = req.headers["authorization"] || "";
  if (auth !== `Bearer ${KEY}`) {
    return json(401, { error: { message: "bad gateway key" } });
  }
  let body = "";
  req.on("data", c => { body += c; });
  req.on("end", async () => {
    let payload;
    try { payload = JSON.parse(body); } catch {
      return json(400, { error: { message: "invalid JSON" } });
    }
    const messages = Array.isArray(payload?.messages) ? payload.messages : null;
    if (!messages || !messages.length) {
      return json(400, { error: { message: "messages required" } });
    }
    const promptText = messages.map(m => m.content).join("\n");
    // R458-C1: the requested model id selects the CLI's own thinking
    // mode (disclosed above); recorded verbatim in the call log.
    const requestedModel = String(payload?.model || "");
    const thinkingMode = requestedModel.endsWith("-thinking");
    const t0 = Date.now();
    try {
      const out = await zaiComplete(messages, 400_000, thinkingMode);
      const entry = {
        ts: new Date().toISOString(),
        model: out.model,
        requested_model: requestedModel,
        thinking_mode: thinkingMode,
        n_messages: messages.length,
        prompt_sha256: sha(promptText),
        content_sha256: sha(out.content),
        latency_ms: out.latency_ms,
        usage: out.usage,
        status: "OK",
      };
      logCall(entry);
      return json(200, {
        id: `zai-${crypto.randomBytes(8).toString("hex")}`,
        object: "chat.completion",
        created: Math.floor(Date.now() / 1000),
        model: out.model,
        choices: [{
          index: 0,
          message: { role: "assistant", content: out.content },
          finish_reason: out.finish_reason,
        }],
        usage: out.usage || { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 },
      });
    } catch (e) {
      logCall({
        ts: new Date().toISOString(),
        prompt_sha256: sha(promptText),
        latency_ms: Date.now() - t0,
        status: "ERROR",
        error: String(e.message || e).slice(0, 300),
      });
      return json(500, { error: { message: String(e.message || e).slice(0, 300) } });
    }
  });
});

// R6 request watchdog: a client request that never completes (wedged
// connection) is destroyed in bounded time — the caller receives a reset
// and its own retry ladder owns a fresh connection. Without this, one
// silent connection can hang a caller until ITS socket budget expires
// (measured R6: the judge-calibration phase sat ~15 min in readinto on a
// connection the gateway had accepted but never processed).
server.requestTimeout = 60_000;   // whole request (headers + body)
server.headersTimeout = 55_000;   // headers only (must be < requestTimeout)

server.listen(PORT, "127.0.0.1", () => {
  console.log(`[zai-gateway] listening on 127.0.0.1:${PORT}`);
  console.log(`[zai-gateway] call log: ${LOG}`);
  console.log(`[zai-gateway] R6 pacing: start=${PACING_START_S}s ` +
    `max=${PACING_MAX_S}s backoff=${PACING_429_BACKOFF_S}s (AIMD, ` +
    `one bounded 429 retry)`);
});
