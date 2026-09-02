# Toscanini engine — hosted deployment image (R391).
#
# Stage 1 builds the Next.js webapp as a static export (same-origin:
# all fetches are relative, so /api/* resolves to this engine — no
# proxy, no CORS; the same codebase also deploys to Vercel unchanged).
# Stage 2 is the Python engine: it serves the export AND the job API
# on $PORT, and clones the buyer-distribution portfolio as a SIBLING
# at container start (Art. XXXIX — showcase serves the REAL packages;
# never re-rendered). GITHUB_TOKEN is a runtime secret.

# ---------- stage 1: webapp static export ----------
FROM node:20-alpine AS webapp-builder
WORKDIR /webapp
COPY TOSCANINI_UI/webapp/package.json TOSCANINI_UI/webapp/package-lock.json ./
RUN npm ci
COPY TOSCANINI_UI/webapp/ ./
RUN NEXT_OUTPUT=export npm run build

# ---------- stage 2: the engine ----------
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=webapp-builder /webapp/out ./TOSCANINI_UI/webapp-export

# Startup: clone the portfolio sibling (once), then serve.
# A failed clone degrades the showcase (404s) but never fabricates
# packages — the healthcheck reports portfolio readiness honestly.
CMD ["sh", "-c", "git config --global --add safe.directory /app; \
if [ ! -d ../portfolio/.git ]; then \
  git clone --depth 1 https://x-access-token:${GITHUB_TOKEN}@github.com/prateekm1007/technology-transfer-portfolio-15.git ../portfolio \
  || echo 'WARN: portfolio clone failed — showcase packages unavailable (fresh runs unaffected)'; \
fi; \
python -m toscanini.server"]
