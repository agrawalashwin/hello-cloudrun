# ─── Stage 1: build dependencies ─────────────────────────────────────────────
FROM python:3.11-slim AS builder

# Install pip dependencies in their own layer
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ─── Stage 2: build final image ──────────────────────────────────────────────
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy installed deps from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/

# Copy application code (including templates/)
COPY . .

# ─── DEBUG STEP: verify templates are present ─────────────────────────────────
# (remove this RUN once you confirm templates/ is in the build)
RUN ls -R /app

# ─── Runtime config ──────────────────────────────────────────────────────────
ENV PORT 8080
EXPOSE 8080

# Use Gunicorn for production
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:8080", "--workers", "2"]
