"""Toscanini HTTP orchestration service (stdlib only; port 8788).

Endpoints (all consumed by the Next.js UI proxy — never by the browser
directly; keys and internals stay server-side):

  GET  /healthz
  GET  /api/engine                       engine commit + gateway status
  POST /api/discoveries  {text}          start a new discovery (worker subprocess)
  GET  /api/sessions                     conversation history
  GET  /api/sessions/<id>                full session detail (stages, result)
  GET  /api/sessions/<id>/events         SSE live stream (artifact-derived)
  POST /api/sessions/<id>/share          create read-only share link
  GET  /api/share/<share_id>             PUBLIC payload (six fields, no internals)
  GET  /api/sessions/<id>/package        buyer ZIP download (if produced)
  GET  /api/cemetery                     failed-candidate cemetery

Every streamed event is derived from a persisted artifact on disk (envelope
JSON, session record, final_state) — no fabricated progress (Art. IV/VI).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import threading
import urllib.parse
import uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from toscanini import gateway as gw  # noqa: E402
from toscanini import sessions as store  # noqa: E402
from toscanini import showcase as show  # noqa: E402

PORT = int(os.environ.get("PORT") or 8788)
# R391 (deployment): hosted engines (Render) set PORT and expect a
# 0.0.0.0 bind; local dev keeps the loopback default.
HOST = os.environ.get("ENGINE_HOST") or ("0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")


def _git_head() -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:  # noqa: BLE001
        return ""


# R392 (directive 3): the deployed engine is identified by an EXACT
# commit, resolved with its source labeled — never guessed (Art. VI):
#   1. ENGINE_COMMIT env (the explicit deployment configuration)
#   2. /app/ENGINE_COMMIT.txt (baked into the Docker image at build time
#      when .git is present in the build context)
#   3. live git (local dev)
def _resolve_engine_commit() -> tuple:
    env = (os.environ.get("ENGINE_COMMIT") or "").strip()
    if env:
        return env, "deployment_config_env"
    baked = REPO_ROOT / "ENGINE_COMMIT.txt"
    if baked.exists():
        v = baked.read_text().strip()
        if v and v != "BUILD_CONTEXT_NO_GIT":
            return v, "image_baked"
    head = _git_head()
    if head:
        return head, "git"
    return "", "UNRESOLVED"


ENGINE_COMMIT, ENGINE_COMMIT_SOURCE = _resolve_engine_commit()
PORTFOLIO_COMMIT_PINNED = (os.environ.get("PORTFOLIO_COMMIT") or "").strip()
# R394 s15: the operator key — callers presenting it see every session
# (enterprise operator path; set ENGINE_OPERATOR_KEY on the service).
OPERATOR_KEY = (os.environ.get("ENGINE_OPERATOR_KEY") or "").strip()
OWNER_COOKIE = "tosca_owner"

# R391 (deployment): same-origin static webapp. When the Docker image
# builds the Next.js export into TOSCANINI_UI/webapp-export/, the engine
# serves it — one public URL serves the whole product (pages + /api/*).
# Absent locally (dev uses `next dev`); never fabricated.
WEBAPP_EXPORT = REPO_ROOT / "TOSCANINI_UI" / "webapp-export"

_STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".txt": "text/plain; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".png": "image/png",
    ".woff2": "font/woff2",
}


def _health_payload() -> dict:
    """R392 directive 2: the honest, machine-readable readiness split.
    Built from REAL state — live git reads, the transport probe cache
    (a genuine completion), the durable store's own bookkeeping. Nothing
    here is derived from a summary (Art. XXIV).
    R394 s1 adds the DEPLOYMENT IDENTITY ASSERTION: the health endpoint
    must expose enough information to prove, without secrets, that
    DEPLOYED_ENGINE_COMMIT == INTENDED_ENGINE_COMMIT and that the
    running build matches the deployment record — with an explicit
    DEPLOYMENT_DRIFT verdict (GREEN / RED), never a silent mismatch."""
    portfolio_ready = bool(show.DOWNLOAD_ROOT.exists())
    portfolio_actual = show.portfolio_commit()
    transport = gw.transport_snapshot()
    probe = gw.last_probe()
    # LLM_TRANSPORT_READY is TRUE only with probe evidence of a real
    # completion from THIS process's transport (never a configured-but-
    # unverified key). A stale-but-OK probe is reported with its age so
    # the caller can decide (machine-readable honesty, not a lie).
    probe_ok = probe.get("status") == "OK"
    engine_ready = bool(ENGINE_COMMIT)
    transport_configured = transport.get("status") in (
        "EXTERNAL", "UP", "ALREADY_UP", "LOCAL_CONFIGURED")

    # ---- R394 s1: deployment identity assertion -----------------------
    live_head = _git_head()
    baked = REPO_ROOT / "ENGINE_COMMIT.txt"
    image_baked = ""
    if baked.exists():
        v = baked.read_text().strip()
        if v and v != "BUILD_CONTEXT_NO_GIT":
            image_baked = v
    # The INTENDED engine commit is the deployment configuration env
    # (ENGINE_COMMIT). The RUNNING identity is what this process
    # actually resolved. Drift is RED when the running resolution
    # disagrees with the intended pin, or when the image-baked commit
    # (when present) disagrees with the running commit.
    running = ENGINE_COMMIT
    drift_reasons = []
    if not running:
        drift_reasons.append("engine commit unresolved")
    if image_baked and running and image_baked != running:
        drift_reasons.append(
            f"image_baked={image_baked[:12]} != running={running[:12]}")
    if ENGINE_COMMIT_SOURCE == "git" and os.environ.get("PORT"):
        drift_reasons.append(
            "hosted deployment resolved engine commit from live git, "
            "not the deployment pin — set ENGINE_COMMIT (R392 pin contract)")
    deployment_identity = {
        "intended_engine_commit": (os.environ.get("ENGINE_COMMIT")
                                    or None),
        "running_engine_commit": running or None,
        "running_engine_commit_source": ENGINE_COMMIT_SOURCE,
        "image_baked_commit": image_baked or None,
        "live_git_head": live_head or None,
        "portfolio_commit_pinned": PORTFOLIO_COMMIT_PINNED or None,
        "portfolio_commit_running": portfolio_actual,
        "deployment_drift": "RED" if drift_reasons else "GREEN",
        "drift_reasons": drift_reasons,
        "rule": ("DEPLOYED_ENGINE_COMMIT == INTENDED_ENGINE_COMMIT and "
                 "RUNNING_BUILD_ID == DEPLOYMENT_RECORD; drift is RED "
                 "=> the release is NOT healthy regardless of other "
                 "readiness fields (R394 s1)"),
    }

    return {
        "ok": True, "status": "ok", "service": "toscanini",
        # legacy keys (R391 contract) kept for the Render healthcheck
        "engine_commit": ENGINE_COMMIT,
        "transport": transport.get("base_url") or "local",
        "portfolio_ready": portfolio_ready,
        "gateway_up": gw.gateway_up(),
        # R394 s1: the deployment identity assertion
        "deployment_identity": deployment_identity,
        # R392 readiness split (directive 2)
        "readiness": {
            "engine_ready": engine_ready,
            "engine_commit": ENGINE_COMMIT,
            "engine_commit_source": ENGINE_COMMIT_SOURCE,
            "deployment_drift": deployment_identity["deployment_drift"],
            "portfolio_ready": portfolio_ready,
            "portfolio_commit": portfolio_actual,
            "portfolio_commit_pinned": PORTFOLIO_COMMIT_PINNED or None,
            "portfolio_pin_match": (
                bool(PORTFOLIO_COMMIT_PINNED)
                and portfolio_actual == PORTFOLIO_COMMIT_PINNED)
                if (PORTFOLIO_COMMIT_PINNED and portfolio_actual) else None,
            "llm_transport_ready": bool(transport_configured and probe_ok),
            "llm_transport": {
                "mode": transport.get("status"),
                "provider": transport.get("provider"),
                "model": transport.get("model"),
                "base_url": transport.get("base_url"),
                "selection": transport.get("selection"),
                "last_probe": probe,
            },
            # discovery needs the engine + a verified-live LLM; the
            # portfolio (showcase) is reported separately above
            "discovery_ready": bool(engine_ready and transport_configured
                                     and probe_ok),
        },
        "durable": _durable_state(),
    }


def _durable_state() -> dict:
    try:
        from toscanini import durable
        return durable.state()
    except Exception as exc:  # noqa: BLE001 — disclosed, never silent
        return {"enabled": False,
                "error": f"{type(exc).__name__}: {exc}"[:200]}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------------ owner
    # R394 s15: opaque cookie-scoped ownership. The key is NOT an identity
    # — it is a capability token issued on first visit (httpOnly, no
    # personal data). Sessions created by a caller are owned by that
    # key; reads are scoped to owned + explicitly-public sessions. The
    # operator key (env, also acceptable via X-Operator-Key header)
    # grants full visibility for operations.
    def _owner_key(self) -> str:
        """Resolve the caller's owner key: cookie, else X-Operator-Key,
        else a fresh key (recorded so the response can set the cookie)."""
        cookie = self.headers.get("Cookie") or ""
        for part in cookie.split(";"):
            k, _, v = part.strip().partition("=")
            if k == OWNER_COOKIE and v:
                return v[:64]
        hdr = self.headers.get("X-Operator-Key") or ""
        if hdr and OPERATOR_KEY and hdr == OPERATOR_KEY:
            return OPERATOR_KEY
        new_key = uuid.uuid4().hex
        self._pending_owner_cookie = new_key
        return new_key

    def _access(self, session_id: str) -> Optional[str]:
        return store.session_access(session_id, self._owner_key_cached,
                                    OPERATOR_KEY)

    def _denied(self):
        # 404 (not 403): a denied caller learns nothing about whether
        # the session exists (enumeration-safe privacy)
        return self._json(404, {"error": "not found"})

    # ------------------------------------------------------------------ util
    def _json(self, code: int, payload) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if getattr(self, "_pending_owner_cookie", None):
            self.send_header(
                "Set-Cookie",
                f"{OWNER_COOKIE}={self._pending_owner_cookie}; HttpOnly; "
                "SameSite=Lax; Path=/; Max-Age=31536000")
            self._pending_owner_cookie = None
        self.end_headers()
        self.wfile.write(body)

    def _body_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n))
        except Exception:  # noqa: BLE001
            return {}

    def log_message(self, fmt, *args):  # quiet
        pass

    # ------------------------------------------------------------------ GET
    def do_GET(self):
        p = urllib.parse.urlparse(self.path)
        parts = [x for x in p.path.split("/") if x]
        # R394 s15: resolve the caller's owner capability ONCE per request
        # (before any handler that needs scoping).
        self._owner_key_cached = self._owner_key()

        if p.path == "/healthz" or p.path == "/api/health":
            # R391: /api/health is the deployment healthcheck alias.
            # R392 (directive 2): HONEST, machine-readable readiness — the
            # product is never reported ready when the LLM cannot produce
            # a completion. Four independent states:
            #   engine_ready      — server + exact engine commit resolved
            #   portfolio_ready   — buyer-distribution repo present (+commit)
            #   llm_transport     — provider configured AND a REAL live
            #                       completion succeeded (probe evidence;
            #                       ?probe=1 forces a fresh one)
            #   discovery_ready   — engine + transport verified live
            # "ok"/"status" stay 200-level (service is up) — readiness
            # carries the truth (Art. XXV: unknown stays unknown).
            force_probe = (p.query or "").strip().lower() in (
                "probe=1", "probe=true", "probe")
            if force_probe:
                gw.ensure_gateway()
                gw.preflight_probe()
            return self._json(200, _health_payload())
        if p.path == "/api/engine":
            return self._json(200, {
                "engine_commit": ENGINE_COMMIT,
                "gateway_up": gw.gateway_up(),
                "runs_root": str(store.ENGINE_RUNS),
            })
        if p.path == "/api/sessions":
            # failure recovery (CEO #8 + R392 directive 7): honest dead-
            # worker detection runs on every history read — interrupted/
            # stuck sessions surface as INTERRUPTED/ERROR_STUCK, never as
            # eternal spinners, never as success
            interrupted = store.mark_interrupted_sessions()
            stuck = store.mark_stuck_sessions()
            # R394 s15: OWNERSHIP — a caller sees ONLY their own sessions
            # plus explicitly public demo content. Measured defect this
            # closes (consultant claim 3, CONFIRMED_CURRENT): anonymous
            # /api/sessions returned all 32 users' problems with worker
            # pids and /app filesystem paths.
            sessions = store.list_sessions_visible_to(
                self._owner_key_cached, OPERATOR_KEY)
            # R394 (CEO directive 2/16): every history row carries the
            # user-facing state projection AND carries NO operational
            # internals (strip_operational_fields)
            from toscanini.user_state import public_session_view
            return self._json(200, {
                "sessions": [public_session_view(s) for s in sessions],
                "marked_stuck": stuck,
                "marked_interrupted": interrupted})
        if p.path == "/api/cemetery":
            return self._json(200, store.cemetery_summary())

        # ---- R389 Phase 7: the CEO's canonical job API naming. These are
        # ALIASES to the same handlers (one canonical production path —
        # never a second run path):
        #   POST /api/run              == POST /api/discoveries
        #   GET  /api/run/{id}/stream  == GET  /api/sessions/{id}/events
        #   GET  /api/run/{id}/result  == GET  /api/sessions/{id}
        if p.path == "/api/showcase":
            return self._json(200, {"showcase": show.list_showcase()})

        if len(parts) >= 3 and parts[0] == "api" and parts[1] == "run":
            rid = parts[2]
            if len(parts) == 4 and parts[3] == "stream":
                if self._access(rid) == "DENY":
                    return self._denied()
                return self._sse(rid)
            if len(parts) == 4 and parts[3] == "result":
                if self._access(rid) == "DENY":
                    return self._denied()
                detail = store.session_detail(rid)
                if detail:
                    from toscanini.user_state import public_session_view
                    return self._json(200, public_session_view(detail))
                return self._json(404, {"error": "not found"})
            if len(parts) == 4 and parts[3] == "package":
                if self._access(rid) == "DENY":
                    return self._denied()
                return self._package(rid)

        if len(parts) >= 3 and parts[0] == "api" and parts[1] == "showcase":
            slot = parts[2]
            if len(parts) == 3:
                detail = show.showcase_detail(slot)
                return self._json(200, detail) if detail \
                    else self._json(404, {"error": "no such showcase slot"})
            if len(parts) == 4 and parts[3] == "model":
                return self._serve_file(show.glb_path(slot),
                                        "model/gltf-binary")
            if len(parts) == 4 and parts[3] == "reality-loop":
                rl = show.reality_loop_record(slot)
                return self._json(200, rl) if rl \
                    else self._json(404, {
                        "error": "no reality-loop closure for this slot",
                        "note": "the R390 loop machinery exists; this "
                                "package has not yet been confronted "
                                "with a real observation"})
            if len(parts) == 4 and parts[3] == "package":
                return self._serve_file(show.package_zip(slot),
                                        "application/zip")
            if len(parts) == 5 and parts[3] == "preview":
                return self._serve_file(
                    show.preview_glb_path(slot, parts[4]),
                    "model/gltf-binary")
            # R395: first-class geometry downloads — STEP/STL/GLB from
            # the artifact panel (kind whitelist; 404 honest when absent)
            if len(parts) == 5 and parts[3] == "download":
                kind = parts[4]
                dpath = show.download_path(slot, kind)
                slot_dir = show._slot_dir(slot)
                return self._serve_file(
                    dpath, show.download_mime(kind),
                    download_name=(
                        f"{slot_dir.name}.{kind}" if dpath and slot_dir
                        else None))

        if len(parts) >= 3 and parts[0] == "api" and parts[1] == "sessions":
            sid = parts[2]
            if len(parts) == 3:
                if self._access(sid) == "DENY":
                    return self._denied()
                detail = store.session_detail(sid)
                if detail:
                    from toscanini.user_state import public_session_view
                    return self._json(200, public_session_view(detail))
                return self._json(404, {"error": "not found"})
            if len(parts) == 4 and parts[3] == "events":
                if self._access(sid) == "DENY":
                    return self._denied()
                return self._sse(sid)
            if len(parts) == 4 and parts[3] == "package":
                if self._access(sid) == "DENY":
                    return self._denied()
                return self._package(sid)

        if len(parts) == 3 and parts[0] == "api" and parts[1] == "share":
            payload = self._share_payload(parts[2])
            return self._json(200, payload) if payload else self._json(404, {"error": "not found"})

        # R391: same-origin static webapp (Render deployment shape).
        # API paths never fall through here — /api 404s stay honest JSON.
        if not p.path.startswith("/api"):
            if self._serve_static(p.path):
                return

        return self._json(404, {"error": "no such endpoint"})

    # ----------------------------------------------------------------- POST
    def do_POST(self):
        p = urllib.parse.urlparse(self.path)
        parts = [x for x in p.path.split("/") if x]
        # R394 s15: owner capability is resolved for POSTs too (run
        # creation binds ownership; ask/share/retry are owner-scoped).
        self._owner_key_cached = self._owner_key()

        # R389 Phase 7: /api/run is the CEO's canonical job API name for
        # the SAME discovery start path (one production loop, one worker).
        if p.path == "/api/discoveries" or p.path == "/api/run":
            body = self._body_json()
            text = (body.get("text") or "").strip()
            if len(text) < 15:
                return self._json(400, {"error": "problem description too short"})
            session = store.create_session(
                title=text.split("\n")[0][:120], user_text=text,
                owner_key=self._owner_key_cached)
            # R392 (directive 5): the job exists durably from the moment
            # it is accepted — an immediate restart cannot erase it.
            try:
                from toscanini import durable
                durable.snapshot(f"created:{session['session_id']}")
            except Exception:  # noqa: BLE001 — disclosed via health
                pass
            self._spawn_worker(session["session_id"])
            # R394 s15: the response carries the customer projection —
            # never the owner_key, worker identity, or filesystem paths
            from toscanini.user_state import public_session_view
            return self._json(200, public_session_view(session))

        # R395: conversational Q&A over a run's / invention's own
        # artifacts — honest refusals are 200-body states (the client
        # renders them as first-class answers), transport/protocol
        # failures are real HTTP errors.
        if len(parts) == 4 and parts[0] == "api" and parts[1] == "run" \
                and parts[3] == "ask":
            body = self._body_json()
            question = (body.get("question") or "").strip()
            if not question:
                return self._json(400, {"error": "question required"})
            if self._access(parts[2]) == "DENY":
                return self._denied()
            detail = store.session_detail(parts[2])
            if not detail:
                return self._json(404, {"error": "run not found"})
            from toscanini.user_state import public_session_view
            from toscanini import run_qa
            out = run_qa.answer_about_run(public_session_view(detail),
                                          question)
            code = 200 if out["status"] in (
                "ANSWERED", "NOT_IN_RECORD", "REFUSED_OVERCLAIM",
                "REFUSED", "BAD_QUESTION") else 503
            return self._json(code, out)

        if len(parts) == 4 and parts[0] == "api" and parts[1] == "showcase" \
                and parts[3] == "ask":
            body = self._body_json()
            question = (body.get("question") or "").strip()
            if not question:
                return self._json(400, {"error": "question required"})
            detail = show.showcase_detail(parts[2])
            if not detail:
                return self._json(404, {"error": "no such showcase slot"})
            reality = show.reality_loop_record(parts[2])
            from toscanini import run_qa
            out = run_qa.answer_about_invention(detail, reality, question)
            code = 200 if out["status"] in (
                "ANSWERED", "NOT_IN_RECORD", "REFUSED_OVERCLAIM",
                "REFUSED", "BAD_QUESTION") else 503
            return self._json(code, out)

        # R389 Phase 5: interactive parameter evaluation on a showcase
        # package — real geometry rebuild, honest envelope enforcement.
        # Route shape: /api/showcase/{slot}/evaluate  (4 segments).
        if len(parts) == 4 and parts[0] == "api" and parts[1] == "showcase" \
                and parts[3] == "evaluate":
            body = self._body_json()
            try:
                new_value = float(body.get("value"))
            except (TypeError, ValueError):
                return self._json(400, {"error": "value must be a number"})
            result, refusal = show.evaluate_parameter(
                parts[2], body.get("param_id") or "", new_value,
                reason=(body.get("reason") or "interactive product preview"))
            if result is None:
                # honest refusal (unbound parameter / outside declared
                # envelope) — surfaced, never silently clamped
                return self._json(409, refusal or
                                  {"error": "evaluation refused"})
            return self._json(200, result)

        if len(parts) == 4 and parts[0] == "api" and parts[1] == "sessions" \
                and parts[3] == "share":
            sid = parts[2]
            # R394 s15: publishing a public share is an OWNER action —
            # a caller cannot expose another user's run. The share
            # registry itself is unchanged (explicit, deliberate, and
            # now consent-scoped).
            if self._access(sid) not in ("OWNER", "PUBLIC"):
                return self._denied()
            share_id = store.create_share(sid)
            if not share_id:
                return self._json(404, {"error": "session not found"})
            return self._json(200, {"share_id": share_id})

        # failure recovery (CEO #8): re-enqueue an ERROR_* session through
        # the SAME serialized worker path. COMPLETE verdicts are NOT
        # retryable (append-only history — re-running is a new session).
        if len(parts) == 4 and parts[0] == "api" and parts[1] == "sessions" \
                and parts[3] == "retry":
            sid = parts[2]
            if self._access(sid) == "DENY":
                return self._denied()
            result = store.retry_session(sid)
            if result is None:
                return self._json(404, {"error": "session not found"})
            if "error" in result:
                return self._json(409, result)
            self._spawn_worker(sid)
            from toscanini.user_state import public_session_view
            return self._json(200, public_session_view(result))

        return self._json(404, {"error": "no such endpoint"})

    # ------------------------------------------------------------ spawn
    def _spawn_worker(self, session_id: str) -> None:
        """Start the serialized discovery worker (detached).

        Transport pinning (EXPLICIT operator overrides, logged by the
        engine and recorded in candidate provenance). The zai pin — the
        measured-healthy sandbox transport — is only the DEFAULT when the
        zai path is actually usable (key present or local gateway up);
        otherwise the pins stay unset and every call site's own selection
        policy decides (R392: the hosted engine resolves its public
        provider through the registry — recorded in each ledger, never
        silent). An explicit ENGINE_*_PROVIDER set by the deployment
        always wins (setdefault no-ops).
        """
        env = dict(os.environ)
        zai_usable = bool(
            os.environ.get("ZAI_API_KEY")
            or gw._load_env_keys().get("ZAI_API_KEY")
            or gw.gateway_up()
            or gw.external_base_url())
        if zai_usable:
            env.setdefault("ENGINE_SYNTHESIS_PROVIDER", "zai")
            env.setdefault("ENGINE_ATTACK_PROVIDER", "zai")
            env.setdefault("ENGINE_ENSEMBLE_PROVIDERS", "zai")
            env.setdefault("ENGINE_GRID_PROVIDERS", "zai")
        subprocess.Popen(
            [sys.executable, "-m", "toscanini.worker", session_id],
            cwd=str(REPO_ROOT), env=env,
            stdout=open(REPO_ROOT / "ENGINE_RUNS" / "toscanini_worker.log",
                        "ab"),
            stderr=subprocess.STDOUT,
            start_new_session=True)

    # ------------------------------------------------------------- file
    def _serve_file(self, path, mime: str, download_name=None):
        if not path or not Path(path).exists():
            return self._json(404, {"error": "file not available"})
        p = Path(path)
        data = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        if download_name:
            self.send_header("Content-Disposition",
                             f'attachment; filename="{download_name}"')
        self.end_headers()
        self.wfile.write(data)

    # ------------------------------------------------------------- package
    def _package(self, sid: str):
        s = store.get_session(sid)
        if not s:
            return self._json(404, {"error": "not found"})
        run_dir = Path(s["run_dir"]) if s.get("run_dir") else None
        info = store.package_info(run_dir) if run_dir and run_dir.exists() else None
        if not info or not info.get("zip") or not Path(info["zip"]).exists():
            return self._json(404, {"error": "no buyer package produced "
                                    "(no survivor reached the release gate)"})
        zp = Path(info["zip"])
        data = zp.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Disposition",
                         f'attachment; filename="{zp.name}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ---------------------------------------------------------------- share
    def _share_payload(self, share_id: str):
        sid = store.share_session(share_id)
        if not sid:
            return None
        d = store.session_detail(sid)
        if not d:
            return None
        inv = d.get("invention_specification") or {}
        evid = (d.get("evidence_pack") or {}).get("retrieval") or []
        engine_evidence = []
        engine_sources = []
        for st in d.get("stages") or []:
            if st.get("stage") == "RETRIEVE":
                engine_evidence = st.get("sample_titles") or []
                engine_sources = st.get("sources") or []
        sources_queried = (
            [r.get("source") for r in evid if r.get("source")]
            or engine_sources)
        inv_evidence = inv.get("evidence") or {}
        uncertainties = inv.get("uncertainties") or {}

        def _plain(field):
            v = field.get("value") if isinstance(field, dict) else field
            cls = field.get("epistemic_class") if isinstance(field, dict) else None
            return v, cls

        def _flat(v):
            """Flatten dict/array spec values into readable text (the share
            view is public prose, never raw engine objects)."""
            if isinstance(v, str):
                return v
            if isinstance(v, dict):
                parts = []
                for key in ("mechanism", "intervention", "expected_effect",
                            "description", "source_observation"):
                    if isinstance(v.get(key), str):
                        parts.append(v[key])
                return " ".join(parts) if parts else json.dumps(v, default=str)[:600]
            if isinstance(v, list):
                return " ".join(_flat(x) for x in v[:4] if x)
            return "" if v is None else str(v)[:600]

        mech_v, mech_c = _plain(inv.get("mechanism") or {})
        why_v, why_c = _plain(inv.get("causal_chain") or {})
        nov_v, nov_c = _plain(inv.get("novelty_hypothesis") or {})
        ke = (d.get("decisive_experiment") or {}).get("selected") or {}
        ke = {k: _flat(v) if not isinstance(v, (int, float, bool)) else v
              for k, v in (ke or {}).items()} if isinstance(ke, dict) else {}
        pkg = d.get("package") or {}
        fs = d.get("final_state") or {}
        return {
            "share_id": share_id,
            "created_at": d.get("created_at"),
            "problem": {
                "title": d.get("title"),
                "failure_mode": (d.get("problem_id") or "").replace("ui_", "").replace("_", " "),
                "domain": d.get("domain_hint"),
            },
            "invention": {
                "mechanism": _flat(mech_v), "epistemic_class": mech_c,
                "why_it_may_work": _flat(why_v),
                "novelty_hypothesis": _flat(nov_v),
                "status": fs.get("final_status"),
            },
            "evidence": {
                "sources_queried": sources_queried,
                "records": engine_evidence[:5],
            },
            "key_uncertainty": (
                _flat(uncertainties.get("value"))
                if isinstance(uncertainties, dict)
                else _flat(uncertainties)) or (
                f"prior art: {fs.get('prior_art_status')}"
                if fs.get("prior_art_status") else
                "Prior art unresolved — collision claims not yet inspected."),
            "next_experiment": ke,
            "package_availability": {
                "available": bool(pkg.get("zip")),
                "maturity": pkg.get("maturity"),
            },
        }

    # ------------------------------------------------------------- static
    def _serve_static(self, path: str) -> bool:
        """Serve the same-origin static webapp export (R391).

        Returns False when the export is absent (local dev) or the path
        is not a webapp path — callers then keep their normal behavior.
        Path traversal is structurally rejected: only normalized, resolved
        paths strictly inside WEBAPP_EXPORT are served."""
        if not WEBAPP_EXPORT.exists():
            return False
        clean = urllib.parse.urlparse(path).path
        if clean.startswith("/api/") or clean == "/api":
            return False
        rel = clean.strip("/")
        # page routes → their exported shells (query params carry state)
        if rel in ("", "run", "showcase"):
            rel = (rel + "/" if rel else "") + "index.html"
        if not rel or ".." in rel.split("/"):
            return False
        f = (WEBAPP_EXPORT / rel).resolve()
        try:
            f.relative_to(WEBAPP_EXPORT.resolve())
        except ValueError:
            return False
        if not f.is_file():
            # unknown non-API path → honest 404 page if exported
            f404 = WEBAPP_EXPORT / "404.html"
            if f404.is_file():
                self._send_static(f404, "text/html; charset=utf-8", 404)
                return True
            return False
        mime = _STATIC_TYPES.get(f.suffix.lower(),
                                 "application/octet-stream")
        cache = "public, max-age=31536000, immutable" \
            if rel.startswith("_next/") else "no-cache"
        self._send_static(f, mime, 200, cache)
        return True

    def _send_static(self, f: Path, mime: str, code: int,
                     cache: str = "no-cache") -> None:
        data = f.read_bytes()
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(data)

    # ------------------------------------------------------------------ SSE
    def _sse(self, sid: str):
        s = store.get_session(sid)
        if not s:
            return self._json(404, {"error": "not found"})
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        def send(event: str, data: dict) -> bool:
            try:
                self.wfile.write(
                    f"event: {event}\ndata: ".encode()
                    + json.dumps(data, ensure_ascii=False, default=str).encode()
                    + b"\n\n")
                self.wfile.flush()
                return True
            except (BrokenPipeError, ConnectionResetError):
                return False

        send("hello", {"session_id": sid})
        seen_stages: set = set()
        last_status = None
        start = time.time()
        while time.time() - start < 3600:
            cur = store.get_session(sid)
            if not cur:
                break
            if cur.get("status") != last_status:
                last_status = cur.get("status")
                send("phase", {"status": last_status,
                               "problem_id": cur.get("problem_id"),
                               "error": cur.get("error")})
                if last_status in ("COMPLETE", "ERROR_TRANSPORT",
                                   "ERROR_BUILD", "ERROR_RUN",
                                   "ERROR_STUCK", "INTERRUPTED"):
                    detail = store.session_detail(sid)
                    if detail:
                        from toscanini.user_state import user_state_view
                        send("final", {
                            "user_state_view": user_state_view(detail),
                            "final_status": detail.get("final_status"),
                            "package": detail.get("package"),
                            "stages": detail.get("stages"),
                            "cemetery_update": detail.get("cemetery_update"),
                            "error": detail.get("error"),
                        })
                    send("done", {"status": last_status})
                    return
            run_dir = cur.get("run_dir")
            if run_dir and Path(run_dir).exists():
                for digest in store.stage_summaries(Path(run_dir)):
                    if digest["stage"] not in seen_stages \
                            and digest.get("status") not in (None, "RUNNING"):
                        seen_stages.add(digest["stage"])
                        send("stage", digest)
            else:
                time.sleep(1.2)
                continue
            time.sleep(1.2)
        send("done", {"status": "STREAM_TIMEOUT"})


def main():
    store.seed_benchmark_sessions()
    # R392 (directive 5/7): after a restart, the durable record is
    # re-materialized FIRST (history survives), then jobs whose worker
    # died with the previous process are marked INTERRUPTED — never
    # COMPLETE, never silently still-RUNNING. Both outcomes are honest
    # and disclosed through /api/health.
    try:
        from toscanini import durable
        durable.restore()
    except Exception as exc:  # noqa: BLE001 — disclosed, never fatal
        print(f"durable restore failed: {type(exc).__name__}: {exc}",
              file=sys.stderr)
    try:
        interrupted = store.mark_interrupted_sessions()
        if interrupted:
            print(f"marked {len(interrupted)} interrupted job(s): "
                  f"{interrupted}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print(f"interrupted-sweep failed: {exc}", file=sys.stderr)
    # R392 (directive 2): a startup transport probe seeds the health
    # endpoint with REAL evidence (never a configured-but-dead key).
    # Background + best-effort: a slow/blocked provider delays nothing.
    def _startup_probe():
        try:
            gw.ensure_gateway()
            gw.preflight_probe()
        except Exception:  # noqa: BLE001 — last_probe records the failure
            pass
    threading.Thread(target=_startup_probe, daemon=True).start()
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"toscanini service on {HOST}:{PORT} "
          f"(engine {ENGINE_COMMIT[:8] or 'UNRESOLVED'} via "
          f"{ENGINE_COMMIT_SOURCE}, transport "
          f"{gw.external_base_url() or 'local-gateway'})", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
