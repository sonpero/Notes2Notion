FROM node:20-alpine AS base

# Install dependencies only when needed
FROM base AS deps
WORKDIR /app

COPY package.json ./
RUN npm install

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Accept build arguments (defaults)
ARG API_HOST
ARG APP_ENV
ARG NOTION_CLIENT_ID
ARG NOTION_REDIRECT_URI

# Set environment variables for build time
ENV NEXT_PUBLIC_API_URL=${API_HOST}
ENV NEXT_PUBLIC_APP_ENV=${APP_ENV}
ENV NEXT_PUBLIC_NOTION_CLIENT_ID=${NOTION_CLIENT_ID}
ENV NEXT_PUBLIC_NOTION_REDIRECT_URI=${NOTION_REDIRECT_URI}

RUN npm run build

# Production image, copy all the files and run next
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public

# Set the correct permission for prerender cache
RUN mkdir .next
RUN chown nextjs:nodejs .next

# Automatically leverage output traces to reduce image size
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
