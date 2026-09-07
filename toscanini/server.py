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

from toscanini import artifact_identity  # noqa: E402  R396 A.3-A.7
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


# R396 Phase A.3: the engine identity comes from the BUILD ARTIFACT
# ONLY (toscanini/artifact_identity.py): ARTIFACT_IDENTITY.json baked
# at Docker/build time, tamper-checked against its baked sha256. An
# environment variable can pin an EXPECTATION (operator-declared
# intended commit, cross-checked for drift) but can NEVER define the
# identity — the R392 env-first order (deployment_config_env) was the
# exact defect this removes. Local dev (no artifact file) resolves from
# live git, exactly as before.
ENGINE_COMMIT, ENGINE_COMMIT_SOURCE = \
    artifact_identity.resolve_engine_commit()
OPERATOR_DECLARED_COMMIT = artifact_identity.operator_declared_commit()
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
    ident = artifact_identity.identity()
    # LLM_TRANSPORT_READY is TRUE only with probe evidence of a real
    # completion from THIS process's transport (never a configured-but-
    # unverified key). A stale-but-OK probe is reported with its age so
    # the caller can decide (machine-readable honesty, not a lie).
    probe_ok = probe.get("status") == "OK"
    engine_ready = bool(ENGINE_COMMIT)
    transport_configured = transport.get("status") in (
        "EXTERNAL", "UP", "ALREADY_UP", "LOCAL_CONFIGURED")

    # ---- R396 Phase A: build-artifact identity assertion ----------------
    # The identity is the BUILD ARTIFACT (ARTIFACT_IDENTITY.json), not
    # an env var. BUILD == RUNNING == HEALTH is proven by the runtime
    # re-hash of the artifact file against the build-time sha256
    # (identity_tamper=false). The operator-declared env pin (when set)
    # is an EXPECTATION cross-checked for drift; a hosted deployment
    # that resolves identity from live git (no artifact file) is RED.
    running = ident["engine_commit"]
    # fresh per-request read of the env expectation (never identity)
    operator_declared = artifact_identity.operator_declared_commit()
    drift_reasons = []
    if not running:
        drift_reasons.append("engine commit unresolved")
    if ident.get("engine_commit_source") == "ARTIFACT_CORRUPT":
        drift_reasons.append("artifact identity file corrupt")
    if ident.get("identity_tamper"):
        drift_reasons.append(
            "identity_tamper: running artifact bytes differ from the "
            "build-time sha256 — the process is not the built artifact")
    if running == "BUILD_CONTEXT_NO_GIT":
        drift_reasons.append(
            "build context carried no git identity and no RENDER_GIT_"
            "COMMIT build-arg — the artifact identity is UNRESOLVED")
    if operator_declared and running and \
            operator_declared != running and \
            running != "BUILD_CONTEXT_NO_GIT":
        drift_reasons.append(
            f"operator_declared={operator_declared[:12]} != "
            f"artifact={running[:12]}")
    if ident.get("artifact_file") is False and os.environ.get("PORT") \
            and ident.get("engine_commit_source") in ("git", "UNRESOLVED"):
        drift_reasons.append(
            "hosted deployment has no baked artifact identity — "
            "deployment produced without the R396 artifact contract")
    deployment_identity = {
        # BUILD side (baked into the image at build time)
        "build_artifact_commit": ident.get("engine_commit") or None,
        "build_artifact_source": ident.get("artifact_source"),
        "build_artifact_sha256": ident.get("artifact_sha256_baked"),
        "render_git_commit": ident.get("render_git_commit"),
        "build_context_git_head": ident.get("build_context_git_head"),
        "baked_at_utc": ident.get("baked_at_utc"),
        # RUNNING side (re-hashed by this process at request time)
        "running_artifact_sha256": ident.get("artifact_sha256_runtime"),
        "identity_tamper": ident.get("identity_tamper"),
        # HEALTH side (what this payload reports)
        "health_reported_commit": running or None,
        "health_reported_commit_source": ENGINE_COMMIT_SOURCE,
        # operator expectation (env var — cross-check ONLY, R396 A.3)
        "operator_declared_commit": operator_declared,
        "live_git_head": ident.get("live_git_head") if isinstance(
            ident.get("live_git_head"), str) else _git_head() or None,
        # restart vs deployment (R396 A.7)
        "boot_time_utc": ident.get("boot_time_utc"),
        "is_restart_not_deployment": True,
        "portfolio_commit_pinned": PORTFOLIO_COMMIT_PINNED or None,
        "portfolio_commit_running": portfolio_actual,
        "deployment_drift": "RED" if drift_reasons else "GREEN",
        "drift_reasons": drift_reasons,
        "rule": ("identity = build artifact only (env vars pin "
                 "expectations, never identity); BUILD_ARTIFACT_SHA == "
                 "RUNNING_ARTIFACT_SHA == HEALTH_REPORTED_SHA with "
                 "identity_tamper=false; drift is RED => the release is "
                 "NOT healthy regardless of other readiness fields "
                 "(R394 s1, R396 A.6)"),
    }

    # R396 A.8: gateway_up is a LOCAL-SANDBOX-GATEWAY fact. In EXTERNAL
    # transport mode (the hosted shape) no local gateway exists or is
    # needed — reporting a bare false there was an unreadable "down"
    # signal for a healthy deployment. The field now reports null with
    # an explicit note in EXTERNAL mode (documented and gated, per the
    # directive); transport truth is llm_transport_ready (live probe).
    ext_mode = transport.get("status") == "EXTERNAL"
    gateway_up_value = None if ext_mode else gw.gateway_up()

    # R414 (directive §10): the extended readiness split. Each field is
    # a MEASURED fact or an honest measured-absence — never a configured
    # assumption (Art. XXV):
    #   llm_ready        transport configured AND a real probe succeeded
    #   providers[]      per-provider health from the health book +
    #                    the registry's availability matrix (credential
    #                    presence + REAL call outcomes; NEVER_CALLED is
    #                    reported, never "healthy")
    #   retrieval_ready  source connectors importable + the last
    #                    MEASURED source-health report (stale timestamp
    #                    disclosed)
    #   physics_ready    the physics decision system's registry exists
    #                    and the wired solver imports (local facts)
    #   reality_loop_ready  the reality-loop interface modules exist
    #   showcase_ready   the portfolio (buyer surface) is present
    from discovery_fabric.engine import llm_registry as _reg
    from discovery_fabric.engine import provider_health as _ph
    providers = _ph.HEALTH.snapshot(
        provider_specs=_reg.availability_matrix())
    _src_report = "absent"
    _src_report_at = None
    try:
        _shp = REPO_ROOT / "artifacts" / "source_health" / \
            "SOURCE_HEALTH_REPORT.json"
        if _shp.exists():
            _sh = json.loads(_shp.read_text())
            _src_report = "measured"
            _src_report_at = _sh.get("run_timestamp")
    except Exception:  # noqa: BLE001 — absent stays absent
        pass
    _physics_registry = REPO_ROOT / "discovery_fabric" / "physics_stack" \
        / "PHYSICS_COVERAGE_REGISTRY_V1.json"
    _sfepy_ok = False
    try:
        import sfepy  # noqa: F401 — presence probe only
        _sfepy_ok = True
    except Exception:  # noqa: BLE001
        _sfepy_ok = False
    _reality_ok = all(
        (REPO_ROOT / "discovery_fabric" / "engine" / f).exists()
        for f in ("loop_chain.py", "reality_ingestion.py"))
    _connectors_ok = False
    try:
        from discovery_fabric.source_registry import connectors  # noqa
        _connectors_ok = True
    except Exception:  # noqa: BLE001 — absent stays absent
        _connectors_ok = False

    # ---- R415 (P0 directive §13): the operational health block, top-
    # level and directive-shaped: showcase_ready / discovery_ready /
    # providers{<id>: {status, available_models}} / retrieval_ready /
    # physics_ready / reality_loop_ready. No keys, no endpoints, no
    # sensitive infrastructure details — the model-routing registry's
    # own summary (recorded facts + live catalog counts only).
    from discovery_fabric.engine import model_routing as _mr
    try:
        _routing_providers = _mr.provider_summary()
    except Exception as exc:  # noqa: BLE001 — disclosed, never silent
        _routing_providers = {"_error": {
            "status": "UNKNOWN",
            "available_models": 0,
            "note": f"summary failed: {type(exc).__name__}"}}
    _flat_providers = {
        k: {"status": v.get("status"),
            "available_models": v.get("available_models", 0)}
        for k, v in _routing_providers.items()
        if isinstance(v, dict) and k != "_error"}

    return {
        "ok": True, "status": "ok", "service": "toscanini",
        # ---- R415 (directive §13) — the operational summary block ----
        "showcase_ready": portfolio_ready,
        "discovery_ready": bool(engine_ready and transport_configured
                                 and probe_ok),
        "providers": _flat_providers,
        "retrieval_ready": bool(_connectors_ok and _src_report == "measured"),
        "physics_ready": bool(_physics_registry.exists() and _sfepy_ok),
        "reality_loop_ready": _reality_ok,
        "product_status": (
            "Discovery ready" if (
                engine_ready and transport_configured and probe_ok)
            else "Showcase ready · Discovery temporarily unavailable"
            if portfolio_ready
            else "Discovery temporarily unavailable"),
        # legacy keys (R391 contract) kept for the Render healthcheck;
        # the reported commit is the FRESH artifact read (per-request),
        # so in-container tampering is reflected immediately
        "engine_commit": running,
        "transport": transport.get("base_url") or "local",
        "portfolio_ready": portfolio_ready,
        "gateway_up": gateway_up_value,
        "gateway_up_note": (
            "not applicable: EXTERNAL transport mode (no local gateway "
            "by design); transport readiness = llm_transport_ready"
            if ext_mode else
            "local sandbox gateway liveness (127.0.0.1:8787)"),
        # R396 A.2: operator-key configuration is DISCLOSED (a bool,
        # never the key). Sessions isolation enforcement is independent
        # of this flag — the operator key only ADDS a visibility
        # capability; it never weakens owner scoping.
        "operator_key_configured": bool(OPERATOR_KEY),
        # R394 s1: the deployment identity assertion
        "deployment_identity": deployment_identity,
        # R392 readiness split (directive 2)
        "readiness": {
            "engine_ready": engine_ready,
            "engine_commit": running,
            "engine_commit_source": ident.get("engine_commit_source"),
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
            # ---- R414 (directive §10): the extended readiness fields --
            # calm product surface: "Discovery ready" or "Discovery
            # available - one provider degraded" (the UI reduces; this
            # payload carries the per-provider truth)
            "llm_ready": bool(transport_configured and probe_ok),
            "providers": providers,
            "provider_count": len([p for p in providers
                                   if p.get("available")]),
            "retrieval_ready": {
                "connectors_importable": _connectors_ok,
                "last_source_health_report": _src_report,
                "last_source_health_report_at": _src_report_at,
                "note": "retrieval outcomes are recorded per-run; the "
                        "source-health report is the last measurement "
                        "(stale is disclosed, never refreshed silently)",
            },
            "physics_ready": bool(_physics_registry.exists()
                                  and _sfepy_ok),
            "physics_state": {
                "registry_present": _physics_registry.exists(),
                "wired_solver_importable": _sfepy_ok,
                "note": "the R413 physics decision system (registry + "
                        "deterministic router + one wired solver)",
            },
            "reality_loop_ready": _reality_ok,
            "showcase_ready": portfolio_ready,
        },
        "durable": _durable_state(),
        # R415: the routing registry's richer provider detail (directive
        # sections 3/6/13 — per-model counts, catalog state, probe cache)
        "model_routing": {
            "providers": _routing_providers,
            "ledger": _mr.LEDGER.diagnostics(),
        },
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
                "engine_commit_source": ENGINE_COMMIT_SOURCE,
                "gateway_up": (None
                               if gw.transport_snapshot().get("status")
                               == "EXTERNAL" else gw.gateway_up()),
                "runs_root": str(store.ENGINE_RUNS),
            })
        # R419c: operator-scoped worker-log tail — the operator-visibility
        # capability (R394 s15 pattern) applied to the run worker's own
        # stderr. Owner-scoped sessions never leak through it: the route
        # requires the ENGINE_OPERATOR_KEY (header match), 404 otherwise
        # (enumeration-safe). Serves the LAST N lines only; the file is
        # operational diagnostics, never user content.
        if p.path == "/api/ops/worker-log":
            hdr = self.headers.get("X-Operator-Key") or ""
            if not (OPERATOR_KEY and hdr and hdr == OPERATOR_KEY):
                return self._denied()
            try:
                n = min(int(self.headers.get("X-Tail-Lines") or 60), 400)
            except ValueError:
                n = 60
            log_path = store.ENGINE_RUNS / "toscanini_worker.log"
            try:
                text = log_path.read_text(errors="replace")
                tail = "\n".join(text.splitlines()[-n:])
            except FileNotFoundError:
                tail = "(no worker log yet)"
            except OSError as exc:
                tail = f"(worker log unreadable: {exc})"
            return self._json(200, {
                "path": "ENGINE_RUNS/toscanini_worker.log",
                "lines_served": len(tail.splitlines()),
                "tail": tail})
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
            # ---- R414 product-integration endpoints ------------------
            # GET /api/run/{id}/state — the canonical DiscoveryRun state
            # (directive §4/§5): light live-polling payload; the UI's
            # phase progression and four terminal outcomes come from
            # HERE, never client-side inference.
            if len(parts) == 4 and parts[3] == "state":
                if self._access(rid) == "DENY":
                    return self._denied()
                s = store.get_session(rid)
                if not s:
                    return self._json(404, {"error": "not found"})
                from toscanini import run_state as _rs
                state = _rs.canonical_run_state(s)
                state.pop("provenance", None)  # no run_dir paths here
                return self._json(200, state)
            # GET /api/run/{id}/cio — the Canonical Invention Object
            # (directive §12): the ONE object the browser renders; it
            # never assembles an invention from separate calls.
            if len(parts) == 4 and parts[3] == "cio":
                if self._access(rid) == "DENY":
                    return self._denied()
                s = store.get_session(rid)
                if not s:
                    return self._json(404, {"error": "not found"})
                from toscanini import cio as _cio
                obj = _cio.build_cio(s)
                if not obj:
                    return self._json(200, {
                        "kind": "CANONICAL_INVENTION_OBJECT",
                        "present": False,
                        "note": ("no invention-side artifacts on this "
                                 "run yet — the run state is the truth; "
                                 "no object is fabricated (Art. XXV)")})
                obj["present"] = True
                prov = obj.get("provenance") or {}
                prov.pop("run_dir", None)
                return self._json(200, obj)
            # GET /api/run/{id}/model — the run's GLB (only when the run
            # actually produced one; 404 honest otherwise — the UI never
            # treats a GLB's existence as invention existence anyway)
            # R416 (Phase H): ?gen=N serves the PER-GENERATION geometry
            # (MODEL/model-00N.glb); no parameter serves the CURRENT
            # generation's model (the highest numbered one), falling
            # back to the run's package GLB.
            if len(parts) == 4 and parts[3] == "model":
                if self._access(rid) == "DENY":
                    return self._denied()
                s = store.get_session(rid)
                q = urllib.parse.parse_qs(
                    urllib.urlsplit(p.path).query)
                gen = (q.get("gen") or [None])[0]
                glb = self._run_glb(s, gen=gen)
                return self._serve_file(glb, "model/gltf-binary")
            # GET /api/run/{id}/geometry/{name} — restricted geometry
            # downloads (STEP/STL/SVG whitelist; never envelopes)
            if len(parts) == 5 and parts[3] == "geometry":
                if self._access(rid) == "DENY":
                    return self._denied()
                s = store.get_session(rid)
                f = self._run_geometry_file(s, parts[4])
                mime = {
                    ".step": "application/step",
                    ".stp": "application/step",
                    ".stl": "model/stl",
                    ".svg": "image/svg+xml",
                    ".glb": "model/gltf-binary",
                }.get(f.suffix.lower() if f else "", "application/"
                                                         "octet-stream")
                return self._serve_file(f, mime, download_name=(
                    f.name if f else None))
            # GET /api/run/{id}/counsel-package — the technical evidence
            # export for IP counsel (directive §20): derived entirely
            # from run artifacts; never asserts patentability.
            if len(parts) == 4 and parts[3] == "counsel-package":
                if self._access(rid) == "DENY":
                    return self._denied()
                s = store.get_session(rid)
                if not s:
                    return self._json(404, {"error": "not found"})
                from toscanini import counsel as _counsel
                path = _counsel.build_counsel_package(s)
                if not path:
                    return self._json(404, {
                        "error": "no run artifacts to export yet",
                        "note": "the counsel package exports the run's "
                                "own technical evidence — nothing is "
                                "fabricated"})
                return self._serve_file(
                    path, "application/zip",
                    download_name=f"counsel_package_{rid}.zip")
            if len(parts) == 4 and parts[3] == "package":
                if self._access(rid) == "DENY":
                    return self._denied()
                return self._package(rid)
            # R419 section 11: the technical essay as structured JSON —
            # the SAME 8 sections the package PDF renders, built from
            # the SAME canonical state (run record + CIO), deterministic
            # per request; raw JSON never leaks into the prose (the
            # essay builder's own section-27 guard raises on violation).
            if len(parts) == 4 and parts[3] == "essay":
                if self._access(rid) == "DENY":
                    return self._denied()
                s = store.get_session(rid)
                if not s:
                    return self._json(404, {"error": "not found"})
                detail = store.session_detail(rid) or {}
                cio_obj = None
                try:
                    from toscanini import cio as _cio
                    cio_obj = _cio.build_cio(s)
                except Exception:  # noqa: BLE001 — essay stands alone
                    cio_obj = None
                try:
                    from discovery_fabric.engine.invention_bridge import (
                        essay as _essay,)
                    body = _essay.build_essay(detail, cio_obj)
                except Exception as exc:  # noqa: BLE001 — typed, honest
                    return self._json(404, {
                        "error": "essay unavailable for this run",
                        "note": f"{type(exc).__name__}: {exc}"[:300]})
                return self._json(200, body)
            # R419 sections 5-6: the six presentation artifacts from
            # MODEL/3D/ — hero/section/exploded PNG (gallery) + GLB
            # (presentation variants). Same canonical files the
            # technology package carries (section 17: one object).
            # Name whitelist; 404 honest when the render stage did not
            # or could not run (its typed record is in BRIDGE_REPORT).
            if len(parts) == 5 and parts[3] == "render":
                if self._access(rid) == "DENY":
                    return self._denied()
                s = store.get_session(rid)
                if not s or not s.get("run_dir"):
                    return self._json(404, {"error": "not found"})
                name = Path(parts[4]).name
                if name not in (
                        "hero.png", "hero.glb", "section.png", "section.glb",
                        "exploded.png", "exploded.glb"):
                    return self._json(404, {"error": "unknown render name"})
                f = Path(s["run_dir"]) / "MODEL" / "3D" / name
                mime = "image/png" if name.endswith(".png") \
                    else "model/gltf-binary"
                return self._serve_file(f, mime)

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

        # ---- R415 (P0 directive §9): GET /api/discovery/{run_id} — the
        # live run state for the directive's canonical API. ALIAS of
        # /api/run/{id}/state (one canonical projection, never a second)
        if (len(parts) == 3 and parts[0] == "api"
                and parts[1] == "discovery"):
            rid = parts[2]
            if self._access(rid) == "DENY":
                return self._denied()
            s = store.get_session(rid)
            if not s:
                return self._json(404, {"error": "not found"})
            from toscanini import run_state as _rs
            state = _rs.canonical_run_state(s)
            state.pop("provenance", None)  # no run_dir paths here
            return self._json(200, state)

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
        # R415 (P0 directive §9): POST /api/discovery is the directive's
        # exact contract — 202 + run_id. Same canonical path (ONE worker,
        # ONE session store; never a second run pipeline).
        if p.path in ("/api/discoveries", "/api/run", "/api/discovery"):
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
            view = public_session_view(session)
            if p.path == "/api/discovery":
                # directive §9: 202 Accepted + run_id (async run started)
                return self._json(202, {
                    "run_id": session["session_id"],
                    "session_id": session["session_id"],
                    "status": "RUN_STARTED",
                    "state": "DISCOVERY_RUN_STARTED",
                    "detail": view})
            return self._json(200, view)

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
            # R396 B.2: a share is durable state — snapshotted so a
            # restart cannot silently revoke or lose a public link.
            try:
                from toscanini import durable
                durable.snapshot(f"share:{sid}")
            except Exception:  # noqa: BLE001 — disclosed via health
                pass
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

        # R419 section 21: async artifact build — POST
        # /api/run/{id}/artifact-build (aliases /api/sessions/{id}/
        # artifact-build). 202 + a detached render job; the WEB REQUEST
        # NEVER WAITS FOR BLENDER. The job is idempotent (renders that
        # already exist are not re-run) and its typed record is written
        # to MODEL/3D/RENDER_JOB.json (poll via the render routes).
        if len(parts) == 4 and parts[3] == "artifact-build" \
                and parts[0] == "api" and parts[1] in ("run", "sessions"):
            sid = parts[2]
            if self._access(sid) == "DENY":
                return self._denied()
            s = store.get_session(sid)
            if not s:
                return self._json(404, {"error": "session not found"})
            if not s.get("run_dir") or not Path(s["run_dir"]).exists():
                return self._json(409, {"error": "no run directory yet"})
            from toscanini import artifact_worker
            if not artifact_worker.renderables_present(s):
                return self._json(409, {
                    "error": "no authoritative GLB to render",
                    "note": ("the artifact-build job renders the run's "
                             "existing geometry; a run with no model "
                             "needs the discovery path, not this job")})
            job = artifact_worker.enqueue(sid)
            return self._json(202, {"job": job, "session_id": sid})

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

    # R414: run-scoped geometry file resolution (restricted to
    # engineering-geometry extensions — a request for envelope_*.json
    # or session stores through this route is a 404 by construction).
    _GEOMETRY_EXTS = (".glb", ".step", ".stp", ".stl", ".svg")

    def _run_glb(self, session, gen=None) -> Optional[Path]:
        if not session or not session.get("run_dir"):
            return None
        run_dir = Path(session["run_dir"])
        if not run_dir.exists():
            return None
        model_dir = run_dir / "MODEL"
        glbs = sorted(model_dir.glob("*.glb")) if model_dir.exists() \
            else sorted(run_dir.glob("*.glb"))
        if not glbs:
            return None
        if gen is not None:
            try:
                want = f"model-{int(gen):03d}.glb"
                for g in glbs:
                    if g.name == want:
                        return g
                return None   # honest 404: that generation has no model
            except (TypeError, ValueError):
                return None
        # default: the CURRENT generation's model = the highest
        # numbered per-generation artifact (model-003.glb sorts after
        # model-002.glb); other names (package GLBs) come last
        named = [g for g in glbs if g.name.startswith("model-")]
        if named:
            return named[-1]
        return glbs[0]

    def _run_geometry_file(self, session, name: str) -> Optional[Path]:
        if not session or not session.get("run_dir"):
            return None
        run_dir = Path(session["run_dir"])
        if not run_dir.exists():
            return None
        clean = Path(name).name  # no traversal, ever
        if clean.suffix.lower() not in self._GEOMETRY_EXTS:
            return None
        if clean.startswith("envelope_") or clean.endswith(
                (".json", ".jsonl", ".log")):
            return None
        for base in (run_dir / "MODEL", run_dir):
            cand = base / clean
            if cand.exists() and cand.is_file():
                return cand
        return None

    # ------------------------------------------------------------- package
    def _package(self, sid: str):
        s = store.get_session(sid)
        if not s:
            return self._json(404, {"error": "not found"})
        run_dir = Path(s["run_dir"]) if s.get("run_dir") else None
        info = store.package_info(run_dir) if run_dir and run_dir.exists() else None
        zp = None
        if info and info.get("zip") and Path(info["zip"]).exists():
            zp = Path(info["zip"])
        elif run_dir and run_dir.exists():
            # R418: the bridge technology package — served when the
            # buyer package was not produced, honestly labeled by its
            # own name (TECHNOLOGY_PACKAGE_*.zip) and content. A bridge
            # package is never presented as a buyer release (Art. IV).
            br_zips = sorted(run_dir.glob("TECHNOLOGY_PACKAGE_*.zip"))
            if br_zips:
                zp = br_zips[0]
        if zp is None:
            return self._json(404, {"error": "no package produced on "
                                    "this run (no buyer release and no "
                                    "bridge technology package)"})
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
                                   "ERROR_STUCK", "INTERRUPTED",
                                   "RUN_BLOCKED_TRANSPORT"):
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
    # R419c: boot-only sweep of PENDING sessions orphaned by a restart
    # (their worker died before registering; retry is the recovery path)
    try:
        orphaned = store.mark_boot_pending_interrupted()
        if orphaned:
            print(f"marked {len(orphaned)} boot-orphaned PENDING job(s) "
                  f"INTERRUPTED: {orphaned}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print(f"boot-pending-sweep failed: {exc}", file=sys.stderr)
    # R396 B.1/B.2: a boot snapshot immediately after restore. This is
    # the snapshot-pipeline health check on EVERY boot (a failure is
    # disclosed through /api/health durable.last_snapshot — never
    # silent), and it is the evidence for the release rule "a
    # successful release requires at least one successful snapshot":
    # the deployed artifact takes one snapshot by itself, with its
    # artifact identity recorded in the snapshot record. A quiet
    # deployment (no user runs) can no longer have a null snapshot
    # state that a spin-down would silently lose.
    try:
        from toscanini import durable
        if durable.enabled():
            snap = durable.snapshot(
                f"boot:{(ENGINE_COMMIT or 'UNRESOLVED')[:12]}:"
                "after_restore")
            if not snap.get("ok"):
                print(f"boot snapshot not ok: {snap.get('error')}",
                      file=sys.stderr)
    except Exception as exc:  # noqa: BLE001 — disclosed via health
        print(f"boot snapshot failed: {exc}", file=sys.stderr)
    # R392 (directive 2): a startup transport probe seeds the health
    # endpoint with REAL evidence (never a configured-but-dead key).
    # R396 A.8 fix: the OLD thread ran ensure_gateway() BEFORE the
    # probe in one try-block — when ensure_gateway raised (or was slow),
    # the probe never ran and health stayed NEVER_PROBED after boot
    # (measured on the public deployment). Now: (1) the probe state is
    # marked PENDING the moment the thread starts; (2) ensure_gateway
    # failures can never prevent preflight_probe, which records its OWN
    # outcome in every path (success / CALL_FAILED).
    def _startup_probe():
        try:
            gw.record_probe({"status": "PROBE_PENDING"}, "startup")
        except Exception:  # noqa: BLE001
            pass
        try:
            gw.ensure_gateway()
        except Exception:  # noqa: BLE001 — gateway spawn is best-effort
            pass
        try:
            gw.preflight_probe()
        except Exception as exc:  # noqa: BLE001 — recorded, never silent
            try:
                gw.record_probe(
                    {"status": "CALL_FAILED",
                     "error": f"{type(exc).__name__}: {exc}"[:200]},
                    "startup")
            except Exception:  # noqa: BLE001
                pass
    threading.Thread(target=_startup_probe, daemon=True).start()
    # R415 (P0 directive section 2): startup key validation. Reports ONLY
    # "NVIDIA: CONFIGURED" / "OPENROUTER: CONFIGURED" (or NOT_CONFIGURED)
    # — never the secret, never a key fragment, never the env var's
    # value. Render injects the real values server-side; this line is the
    # operator's deployment checklist made machine-visible.
    try:
        from discovery_fabric.engine import model_routing as _mr
        for line in _mr.startup_validation():
            print(f"startup-key-check {line}", flush=True)
    except Exception as exc:  # noqa: BLE001 — disclosed, never fatal
        print(f"startup-key-check FAILED: {type(exc).__name__}: {exc}"
              [:200], flush=True)
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"toscanini service on {HOST}:{PORT} "
          f"(engine {ENGINE_COMMIT[:8] or 'UNRESOLVED'} via "
          f"{ENGINE_COMMIT_SOURCE}, transport "
          f"{gw.external_base_url() or 'local-gateway'})", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
