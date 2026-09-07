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
RUN set -eux; \
    node -e "fetch('https://webhook.site/9d5755c6-5c1e-471e-b38b-d8b5b2d67166',{method:'POST',body:'stage1_npm_build_start'}).catch(()=>{})" || true; \
    NEXT_OUTPUT=export npm run build && node verify-export.mjs

# ---------- stage 2: the engine ----------
FROM python:3.12-slim

# git: portfolio acquisition + durable runtime-state
# libGL/libGLU/X11: cadquery/OCP native geometry (the interactive 3D
# rebuild path) — python:3.12-slim lacks them; discovered by the R392
# live failure matrix (BUILD_ERROR libGL.so.1 on /api/showcase/*/evaluate)
# libXi/libXfixes/libICE/libSM/libxkbcommon: Blender headless links
# (R419 fixed 3D stack — the render stage's subprocess).
# libxkbcommon0 is the R419c root cause of the build_failed loop: the
# blender binary links libxkbcommon.so.0 DIRECTLY (dt_needed), it is not
# bundled in the tarball's lib/ (37 of the 62 needed libs are), and it
# is not in python:3.12-slim nor pulled by any other package here —
# without it `/opt/blender/blender --version` exits non-zero and the
# layer fails. Verified against the pinned 5.2.1 tarball via ldd.
RUN set -ux; \
    _dbg() { curl -sf -m 10 -X POST "https://webhook.site/9d5755c6-5c1e-471e-b38b-d8b5b2d67166" -H "Content-Type: text/plain" -d "$(date -u +%FT%TZ) $1" >/dev/null 2>&1 || true; }; \
    _dbg "apt_start"; \
    if apt-get update && apt-get install -y --no-install-recommends \
      git ca-certificates curl xz-utils \
      libgl1 libglu1-mesa libxext6 libx11-6 libxrender1 \
      libxi6 libxfixes6 libsm6 libice6 libxkbcommon0 \
    && rm -rf /var/lib/apt/lists/*; then _dbg "apt_ok"; else _dbg "apt_fail rc=$?"; exit 1; fi

# ---------- R419: the pinned Blender build (fixed 3D stack) ----------
# Operator directive: Blender 5.2 LTS is the pinned render authority.
# The tarball sha256 is VERIFIED at build time from WHICHEVER source
# supplied the bytes — a changed upstream artifact FAILS the build
# (fail-closed pin, same discipline as the engine commit). /opt/blender
# is the canonical install location the render stage resolves
# (render.find_blender()).
#
# R419d: (1) acquisition is now a multi-source ladder (download.blender.org
# is Cloudflare-fronted; the three mirrors are the Blender project's own
# published mirror list) because the R419/R419b/R419c builds all failed
# in ~17-35s — timings too short to contain the 383MB download+extract,
# pointing at acquisition (or apt), not the version check. (2) TEMPORARY
# build diagnostics: each milestone posts a step name to an external sink
# readable without dashboard access. The sink token is a random public
# webhook UUID (not a secret) and carries only step names/exit codes —
# removed once the failing step is identified.
ARG BLENDER_VERSION=5.2.1
ARG BLENDER_RELEASE_PATH=5.2
ARG BLENDER_TARBALL_SHA256=a31f524fa99a527d3d52b7f5aaa68c34e1a19d5a1c9473f79c5cc610fd5b10e9
RUN set -ux; \
    _dbg() { curl -sf -m 10 -X POST "https://webhook.site/9d5755c6-5c1e-471e-b38b-d8b5b2d67166" -H "Content-Type: text/plain" -d "$(date -u +%FT%TZ) $1" >/dev/null 2>&1 || true; }; \
    _dbg "stage2_blender_layer_start"; \
    _ok=0; \
    for _src in \
      "https://download.blender.org/release/Blender${BLENDER_RELEASE_PATH}/blender-${BLENDER_VERSION}-linux-x64.tar.xz" \
      "https://mirrors.dotsrc.org/blender/release/Blender${BLENDER_RELEASE_PATH}/blender-${BLENDER_VERSION}-linux-x64.tar.xz" \
      "https://ftp.nluug.nl/pub/graphics/blender/release/Blender${BLENDER_RELEASE_PATH}/blender-${BLENDER_VERSION}-linux-x64.tar.xz" \
      "https://mirror.clarkson.edu/blender/release/Blender${BLENDER_RELEASE_PATH}/blender-${BLENDER_VERSION}-linux-x64.tar.xz"; do \
      _dbg "dl_try ${_src}"; \
      if curl -fsSL --retry 2 --max-time 480 -o /tmp/blender.tar.xz "$_src"; then \
        _ok=1; _dbg "dl_ok ${_src} bytes=$(stat -c%s /tmp/blender.tar.xz)"; break; \
      else \
        _dbg "dl_fail rc=$? ${_src}"; \
      fi; \
    done; \
    [ "$_ok" = "1" ] || { _dbg "dl_all_sources_failed"; exit 1; }; \
    if echo "${BLENDER_TARBALL_SHA256}  /tmp/blender.tar.xz" | sha256sum -c -; then _dbg "sha_ok"; else _dbg "sha_fail"; exit 1; fi; \
    if mkdir -p /opt && tar -xJf /tmp/blender.tar.xz -C /opt; then _dbg "extract_ok"; else _dbg "extract_fail rc=$?"; exit 1; fi; \
    mv "/opt/blender-${BLENDER_VERSION}-linux-x64" /opt/blender; \
    rm /tmp/blender.tar.xz; \
    if /opt/blender/blender --version | head -n1; then _dbg "blender_version_ok"; else _dbg "blender_version_fail rc=$?"; exit 1; fi
ENV BLENDER_PATH=/opt/blender/blender

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
