# Dockerfile for the React + Vite frontend (development mode)
# ------------------------------------------------------------
# 1️⃣ Build stage – install deps and compile (optional for prod)
# 2️⃣ Runtime stage – serve with a lightweight web server (nginx) for production
# ------------------------------------------------------------
# ----------- Development (hot‑reload) -----------------------
#   If you only need to develop, you can skip the multi‑stage build
#   and run the container directly with `npm run dev`.
# ------------------------------------------------------------
# Use a lightweight Node image
FROM node:20-alpine AS base
WORKDIR /app

# Copy only package files first for cached layer
COPY package.json package-lock.json* ./

# Install dependencies (npm ci prefers a lockfile; falls back to install)
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# Copy the rest of the source code
COPY . .

# ------------------------------------------------------------
# Production stage – build static assets then serve via nginx
# ------------------------------------------------------------
FROM nginx:alpine AS production
COPY --from=base /app/dist /usr/share/nginx/html
# Optional custom nginx config (if you add one later)
# COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

# ------------------------------------------------------------
# Development stage – keep the node environment alive for hot reload
# ------------------------------------------------------------
FROM base AS development
# Vite dev server runs on 5173 by default; expose it
EXPOSE 5173
# Start the dev server; `--host` makes it listen on all interfaces so Docker can reach it
CMD ["npm", "run", "dev", "--", "--host"]
