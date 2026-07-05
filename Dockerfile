# ═══════════════════════════════════════════════════════════════════════
# NARAD — Multi-stage Dockerfile for Google Cloud Run
# Stage 1: Build React frontend
# Stage 2: Python backend serving API + static frontend
# ═══════════════════════════════════════════════════════════════════════

# ── Stage 1: Frontend build ─────────────────────────────────────────────
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install --silent
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python backend ─────────────────────────────────────────────
FROM python:3.12-slim AS backend

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend into a static directory
COPY --from=frontend-build /app/frontend/dist ./static

# Serve static files via FastAPI (append to main.py behavior through env flag)
ENV SERVE_STATIC=true
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

CMD ["python3", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
