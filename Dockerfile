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
RUN NEXT_OUTPUT=export npm run build

# ---------- stage 2: the engine ----------
FROM python:3.12-slim

# git: portfolio acquisition + durable runtime-state
# libGL/libGLU/X11: cadquery/OCP native geometry (the interactive 3D
# rebuild path) — python:3.12-slim lacks them; discovered by the R392
# live failure matrix (BUILD_ERROR libGL.so.1 on /api/showcase/*/evaluate)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      git ca-certificates \
      libgl1 libglu1-mesa libxext6 libx11-6 libxrender1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=webapp-builder /webapp/out ./TOSCANINI_UI/webapp-export

# R392 (directive 3): bake the EXACT engine commit into the image when
# the build context carries .git; otherwise ENGINE_COMMIT.txt records
# that fact and the runtime env (deployment configuration) supplies the
# pin. Never fabricated, source labeled (Art. VI).
RUN if [ -d .git ]; then git rev-parse HEAD > /app/ENGINE_COMMIT.txt; \
    else echo BUILD_CONTEXT_NO_GIT > /app/ENGINE_COMMIT.txt; fi

# R392: startup = acquire the PINNED portfolio (token-safe), then serve.
# See toscanini/container-entrypoint.sh. A failed acquisition degrades
# the showcase (portfolio_ready=false) but never fabricates packages —
# the health endpoint reports readiness honestly.
RUN chmod +x /app/toscanini/container-entrypoint.sh
ENTRYPOINT ["/app/toscanini/container-entrypoint.sh"]
