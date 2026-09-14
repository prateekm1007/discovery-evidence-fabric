# Toscanini engine — hosted deployment image (R391; R392 pinning +
# token-safe startup).
#
# Stage 1 builds the Next.js webapp as a static export (same-origin:
# all fetches are relative, so /api/* resolves to this engine — no
# proxy, no CORS; the same codebase also deploys to Vercel unchanged).
# Stage 2 is the Python engine: it serves the export AND the job API
# on $PORT, and acquires the buyer-distribution portfolio as a SIBLING
# at container start (Art. XXXIX — showcase serves the REAL packages;
# never re-rendered). GITHUB_TOKEN is a runtime secret supplied to git
# through a GIT_ASKPASS helper — never in a URL, argv, or the image.

# ---------- stage 1: webapp static export ----------
FROM node:20-alpine AS webapp-builder
WORKDIR /webapp
COPY TOSCANINI_UI/webapp/package.json TOSCANINI_UI/webapp/package-lock.json ./
RUN npm ci
COPY TOSCANINI_UI/webapp/ ./
# R393 (CEO directive 2): mechanical build assertion — the image build
# FAILS if the export is missing pages, CSS, or JS chunks, or if any page
# references a stylesheet/asset that does not exist. The R389→R392 defect
# (globals.css never imported → zero CSS in the export → the public
# deployment rendered as browser-default HTML) can never ship again.
RUN NEXT_OUTPUT=export npm run build && node verify-export.mjs

# ---------- stage 2: the engine ----------
FROM python:3.12-slim

# git: portfolio acquisition + durable runtime-state
# libGL/libGLU/X11 core: cadquery/OCP native geometry (the interactive
# 3D rebuild path) — python:3.12-slim lacks them; discovered by the R392
# live failure matrix (BUILD_ERROR libGL.so.1 on /api/showcase/*/evaluate).
#
# R456 (image slimming, audit §O.4/§J): the Blender 5.2.1 tarball
# download (383 MB) + its X11 link set (libxi6 libxfixes3 libsm6
# libice6 libxkbcommon0) are REMOVED from the production image — the
# Blender render path was archived as legacy in R441
# (r441_retired/blender_render.py; the Visual Compiler is the primary
# renderer), never chosen by any run since, and the tarball layer was
# the R419-family build-failure surface. The legacy path, if explicitly
# selected, fails closed with the typed RENDER_SKIPPED_NO_BLENDER
# state (render.py records the resolution trail — never a silent
# substitution). Chromium (the live renderer) installs its own apt
# dependency closure where used.
#
# R420: the temporary external build-diagnostics (webhook.site step
# posts, R419d) are REMOVED from the production Dockerfile — their
# purpose (identifying the failing step) was served and the root cause
# is documented above. Build observability now rests on the repository
# itself: this comment chain, the R419d-5/R419e commit trail, and the
# runtime /api/ops/worker-log + /api/ops/artifact-log routes. The
# canonical production image must not carry outbound diagnostic
# callbacks (operator R420 §6).
RUN set -ux; \
    if apt-get update >/tmp/aptu.log 2>&1 && apt-get install -y --no-install-recommends \
      git ca-certificates curl xz-utils \
      libgl1 libglu1-mesa libxext6 libx11-6 libxrender1 \
    >/tmp/apti.log 2>&1 \
    && rm -rf /var/lib/apt/lists/*; then \
      :; \
    else \
      _rc=$?; \
      echo "apt install failed rc=$_rc" >&2; \
      tail -c 2000 /tmp/apti.log 2>/dev/null >&2 || true; \
      exit 1; \
    fi

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=webapp-builder /webapp/out ./TOSCANINI_UI/webapp-export

# R396 Phase A.3/A.4: bake the ACTUAL git commit SHA into the build
# artifact. This is THE identity of the deployed engine — no runtime
# environment variable can define or change it. Sources, in priority
# order, each honestly labeled and never fabricated (Art. VI):
#   1. RENDER_GIT_COMMIT — Render provides the exact sha being built
#      (passed as a build-arg by the deploy step; see DEPLOYMENT_CONFIG)
#   2. git rev-parse HEAD — when the build context carries .git
#   3. BUILD_CONTEXT_NO_GIT — identity unresolved, health reports drift
#      RED (never a guessed or env-asserted commit)
# ARTIFACT_IDENTITY.sha256 (sha256 of the json bytes, computed HERE at
# build time) lets the running process prove it is still the built
# artifact (BUILD == RUNNING == HEALTH, R396 A.6); a runtime mismatch
# is reported as identity_tamper and drift RED.
ARG RENDER_GIT_COMMIT=""
RUN python3 - <<'PYEOF'
import hashlib, json, os, subprocess
commit = (os.environ.get("RENDER_GIT_COMMIT") or "").strip()
source = "render_git_commit"
ctx_head = ""
if os.path.isdir(".git"):
    try:
        ctx_head = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True,
            text=True, timeout=30).stdout.strip()
    except Exception:
        ctx_head = ""
if not commit:
    if ctx_head:
        commit, source = ctx_head, "build_context_git"
    else:
        commit, source = "BUILD_CONTEXT_NO_GIT", "build_context_no_git"
doc = {
    "engine_commit": commit,
    "source": source,
    "render_git_commit": (os.environ.get("RENDER_GIT_COMMIT") or "").strip() or None,
    "build_context_git_head": ctx_head or None,
    "baked_at_utc": subprocess.run(
        ["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], capture_output=True,
        text=True).stdout.strip(),
}
raw = json.dumps(doc, indent=1, sort_keys=True).encode() + b"\n"
open("ARTIFACT_IDENTITY.json", "wb").write(raw)
open("ARTIFACT_IDENTITY.sha256", "w").write(
    hashlib.sha256(raw).hexdigest() + "  ARTIFACT_IDENTITY.json\n")
# R392 compatibility: ENGINE_COMMIT.txt stays an echo of the SAME
# artifact-derived value (legacy consumers); it is never an independent
# identity source.
open("ENGINE_COMMIT.txt", "w").write(commit + "\n")
print(f"baked artifact identity: {commit} (source {source})")
PYEOF

# R392: startup = acquire the PINNED portfolio (token-safe), then serve.
# See toscanini/container-entrypoint.sh. A failed acquisition degrades
# the showcase (portfolio_ready=false) but never fabricates packages —
# the health endpoint reports readiness honestly.
RUN chmod +x /app/toscanini/container-entrypoint.sh
ENTRYPOINT ["/app/toscanini/container-entrypoint.sh"]
