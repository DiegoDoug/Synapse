# syntax=docker/dockerfile:1.7
# Multi-stage build for the Synapse React/Vite frontend (Stage 8).
# Stage 1 builds the static bundle; stage 2 serves it with nginx. The final
# image ships only the compiled assets — no Node, no source, no dev deps.

# ---- Stage 1: build ---------------------------------------------------------
FROM node:22-slim AS build

WORKDIR /app

# Install deps first (cached unless the lockfile changes). `npm ci` is
# reproducible and installs devDependencies needed for the build (tsc, vite).
COPY package.json package-lock.json ./
RUN npm ci

# Build the production bundle (tsc -b && vite build -> /app/dist).
COPY . .
RUN npm run build

# ---- Stage 2: serve ---------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

# SPA-aware static config (history fallback, asset caching, gzip).
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Ship only the compiled assets.
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
