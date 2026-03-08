# Dashboard Dockerfile for Railway
# Next.js 14 frontend with Three.js WebGL visualization

FROM node:20-alpine AS base

# ── Dependencies stage ──────────────────────────────────────────────────────
FROM base AS deps
WORKDIR /app

# Install dependencies based on the preferred package manager
COPY dashboard/package.json dashboard/package-lock.json* ./
RUN npm ci --legacy-peer-deps

# ── Builder stage ───────────────────────────────────────────────────────────
FROM base AS builder
WORKDIR /app

# Copy dependencies
COPY --from=deps /app/node_modules ./node_modules
COPY dashboard/ .

# Build-time environment variables
# NEXT_PUBLIC_API_URL must be set at build time for Next.js static generation
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_TELEMETRY_DISABLED=1

# Build the application
RUN npm run build

# ── Production runner stage ─────────────────────────────────────────────────
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy standalone output from builder
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Switch to non-root user
USER nextjs

# Expose port 3000 for the dashboard
EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000', (r) => r.statusCode === 200 ? process.exit(0) : process.exit(1))" || exit 1

# Start the Next.js server
CMD ["node", "server.js"]
