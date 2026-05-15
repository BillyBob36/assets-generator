FROM python:3.11-slim

# System deps for Pillow (libjpeg, zlib, etc. are already in slim; we just need build tools occasionally)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cache deps separately
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY app.py materials.py generate_previews.py ./
COPY static ./static

# uvicorn binds to 0.0.0.0:8000; Coolify maps Traefik to this port via PORTS_EXPOSES=8000.
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/config >/dev/null || exit 1

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
