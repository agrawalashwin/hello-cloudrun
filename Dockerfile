# ─── Stage 1: install dependencies ────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install Python deps into the default location (/usr/local)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ─── Stage 2: assemble final image ───────────────────────────────────────────
FROM python:3.11-slim

# 1) Copy everything pip installed (both libs and executables)
COPY --from=builder /usr/local /usr/local

# 2) Copy your app code (including templates/ and static/)
WORKDIR /app
COPY . .

# 3) Expose the port Cloud Run will use
ENV PORT 8080
EXPOSE 8080

# 4) Launch with Gunicorn (now actually present in /usr/local/bin)
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:8080", "--workers", "2"]
