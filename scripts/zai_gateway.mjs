#!/usr/bin/env node
/** zai_gateway.mjs — sandbox-local OpenAI-compatible LLM gateway.
 *
 * WHY THIS EXISTS (recorded 2026-08-30, R375 transport unblock):
 * The engine's only credentialed providers were NVIDIA (measured latency
 * collapse: 35 s .. >240 s variance on identical calls; tiny-call
 * timeouts re-verified 2026-08-30) and Mistral (401, re-verified).
 * The M1 campaign was transport-bound on this single path. The sandbox
 * provides a healthy LLM transport via the z-ai CLI (model glm-4-plus,
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
 *  not burned on a transient rate limit. */
function zaiComplete(messages, timeoutMs) {
  return new Promise((resolve, reject) => {
    const system = messages.filter(m => m.role === "system")
      .map(m => m.content).join("\n") || undefined;
    const user = messages.filter(m => m.role === "user")
      .map(m => m.content).join("\n\n");
    if (!user.trim()) return reject(new Error("no user content"));
    const attempt = (triesLeft, backoffs) => {
      const tmp = path.join(os.tmpdir(),
        `zai_gw_${crypto.randomBytes(6).toString("hex")}.json`);
      const args = ["chat", "--prompt", user, "-o", tmp];
      if (system) args.push("--system", system);
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
        if (code !== 0 && is429 && triesLeft > 0) {
          const wait = backoffs[0];
          logCall({
            ts: new Date().toISOString(), status: "RATE_LIMITED_RETRY",
            wait_s: wait, error: stderr.slice(0, 120),
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
          });
        } catch (e) {
          try { fs.unlinkSync(tmp); } catch (_) {}
          reject(new Error(`output parse failed: ${e.message}`));
        }
      });
    };
    attempt(3, [30, 60, 90]);
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
    const t0 = Date.now();
    try {
      const out = await zaiComplete(messages, 400_000);
      const entry = {
        ts: new Date().toISOString(),
        model: out.model,
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

server.listen(PORT, "127.0.0.1", () => {
  console.log(`[zai-gateway] listening on 127.0.0.1:${PORT}`);
  console.log(`[zai-gateway] call log: ${LOG}`);
});
