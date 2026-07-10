# WPAIPublisher — Next.js console + pytest for Railway
# Dashboard MUST be:
#   Root Directory  = (empty / blank)
#   Dockerfile Path = Dockerfile
#   Config file     = /railway.toml
#
# Do NOT set Root Directory to "web" — COPY paths assume repo root.

FROM node:22-bookworm-slim AS deps
WORKDIR /app
# package.json は必須。lock は任意（無い場合は npm install）
COPY web/package.json ./
COPY web/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY web/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-bookworm-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
ENV WPAI_ROOT=/workspace
ENV PYTHON_BIN=python3
ENV PYTHONIOENCODING=utf-8
ENV PYTHONUTF8=1
ENV PIP_BREAK_SYSTEM_PACKAGES=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV PLAYWRIGHT_NO_SANDBOX=1

RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 python3-pip python3-venv php-cli \
  && rm -rf /var/lib/apt/lists/* \
  && ln -sf /usr/bin/python3 /usr/local/bin/python

RUN addgroup --system nodejs && adduser --system --ingroup nodejs nextjs

COPY --from=build --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=build --chown=nextjs:nodejs /app/public ./public

# Python + visual regression workspace
WORKDIR /workspace
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Playwright / pixelmatch（ルート package.json）
COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci --omit=dev; else npm install --omit=dev; fi \
  && npx playwright install-deps chromium \
  && npx playwright install chromium \
  && chown -R nextjs:nodejs /workspace/node_modules /ms-playwright

COPY --chown=nextjs:nodejs wpaipublish.py pytest.ini ./
COPY --chown=nextjs:nodejs scripts ./scripts
COPY --chown=nextjs:nodejs tests ./tests
COPY --chown=nextjs:nodejs intake/example ./intake/example
COPY --chown=nextjs:nodejs intake/samples ./intake/samples
RUN mkdir -p /workspace/output/test-results /output/test-results \
    /workspace/intake/incoming /workspace/intake/uploads \
    /workspace/deployments /workspace/staging \
  && python3 scripts/test/run_tests.py run \
  && cp -a /workspace/output/test-results/. /output/test-results/ \
  && chown -R nextjs:nodejs /workspace /output

WORKDIR /app
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
