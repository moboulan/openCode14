# ────────────────────────────────────────────────────
# Stage 1: Build React app
# ────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (cache layer)
COPY package.json package-lock.json* ./
RUN npm ci --prefer-offline 2>/dev/null || npm install

# Copy source and build
COPY . .
RUN npm run build

# ────────────────────────────────────────────────────
# Stage 2: Production Nginx image
# ────────────────────────────────────────────────────
FROM nginx:1.25-alpine AS runtime

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config with API proxying
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Security: remove setuid/setgid binaries
RUN find / -perm /6000 -type f -exec chmod a-s {} + 2>/dev/null || true

# Non-root: grant nginx user write access to runtime directories
RUN chown -R nginx:nginx /usr/share/nginx/html \
	&& chown -R nginx:nginx /var/cache/nginx \
	&& chown -R nginx:nginx /var/log/nginx \
	&& touch /var/run/nginx.pid \
	&& chown nginx:nginx /var/run/nginx.pid

USER nginx

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
	CMD wget -q --spider http://localhost:8080/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
