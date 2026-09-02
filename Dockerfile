# Toscanini engine — hosted deployment image (R391).
#
# Python 3.12 + the pinned requirements.txt. The buyer-distribution
# portfolio repo is cloned as a SIBLING directory at container start:
# showcase serves the REAL packages from it (Art. XXXIX — the
# buyer-distribution repository is the authority; files are never
# re-rendered). GITHUB_TOKEN is a runtime secret (Render env var).
#
# Render contract: listen on $PORT (the server reads it — R391 change;
# default 8788 for local dev). Healthcheck: /api/health.
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Startup: clone the portfolio sibling (once), then serve.
# A failed clone degrades the showcase (404s) but never fabricates
# packages — the healthcheck reports portfolio readiness honestly.
CMD ["sh", "-c", "git config --global --add safe.directory /app; \
if [ ! -d ../portfolio/.git ]; then \
  git clone --depth 1 https://x-access-token:${GITHUB_TOKEN}@github.com/prateekm1007/technology-transfer-portfolio-15.git ../portfolio \
  || echo 'WARN: portfolio clone failed — showcase packages unavailable (fresh runs unaffected)'; \
fi; \
python -m toscanini.server"]
