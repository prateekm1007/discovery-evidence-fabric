// v9-supervisor: keeps the v9 one-shot process alive as a supervised
// child (the sandbox reaper kills detached/orphaned processes; a
// mini-service's child tree is the sanctioned long-lived path).
// HTTP :3040 /healthz -> { childAlive, restarts, cmd, startedAt }.
// /start -> (re)spawn the run command. The child is spawned ONCE per
// explicit /start; auto-restart only on premature exit (counted +
// logged - a restart breaks the attestation window, so restarts are
// disclosed evidence, never silent).
import { spawn } from "child_process";

const PORT = 3040;
const REPO = "/home/z/fabric-r53";
const CMD = process.env.SUPERVISED_CMD || "echo no-cmd-set";

let child: any = null;
let restarts = 0;
let startedAt: string | null = null;
let lastExit: any = null;

function health() {
  return {
    childAlive: !!(child && child.exitCode === null && child.killed === false),
    pid: child?.pid ?? null,
    restarts, startedAt, lastExit, cmd: CMD,
  };
}

function launch() {
  if (child && child.exitCode === null) return health();
  startedAt = new Date().toISOString();
  // R67s2 fix-forward: this spawn previously FORCED
  // ZAI_GATEWAY_UPSTREAM="xkiro" — a stale falsification-era value
  // that contradicted the registered route (agnes-3.0-flash via
  // ZAI_GATEWAY_UPSTREAM=agnes, 132b97947/d0c18d940). Caught as a
  // dormant hazard during the R67s2 key-rotation work (no supervised
  // run had fired through it). Now the upstream INHERITS the caller's
  // env (no silent override); the run command sets it explicitly.
  child = spawn("bash", ["-lc", CMD], {
    cwd: REPO,
    env: { ...process.env },
    stdio: ["ignore", "inherit", "inherit"],
  });
  child.on("exit", (code: number, sig: string) => {
    lastExit = { code, sig, at: new Date().toISOString() };
    if (sig === "SIGKILL" || sig === "SIGTERM") {
      restarts += 1;
      console.log(`[supervisor] child killed (${sig}); restart #${restarts}`);
      setTimeout(launch, 3000);
    }
  });
  return health();
}

Bun.serve({
  port: PORT,
  fetch(req) {
    const url = new URL(req.url);
    if (url.pathname === "/healthz") return Response.json(health());
    if (url.pathname === "/start") return Response.json(launch());
    return new Response("v9-supervisor\n");
  },
});
console.log(`[supervisor] listening on ${PORT}; cmd=${CMD}`);
