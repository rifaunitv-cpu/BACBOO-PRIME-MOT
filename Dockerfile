# ============================================================
# Dockerfile (PLAYWRIGHT ESTÁVEL - PRODUÇÃO)
# ============================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 👤 usuário seguro
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# ============================================================
# 🔥 DEPENDÊNCIAS DO SISTEMA (OBRIGATÓRIO PRA PLAYWRIGHT)
# ============================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    wget \
    curl \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2t64 \
    libpangocairo-1.0-0 \
    libx11-xcb1 \
    libxfixes3 \
    libxcb1 \
    libxext6 \
    libxi6 \
    libglib2.0-0 \
    libgtk-3-0 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    libwayland-client0 \
    libwayland-server0 \
    libjpeg62-turbo \
    libpng16-16 \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# 📦 PYTHON
# ============================================================
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install playwright

# ============================================================
# 🔥 PLAYWRIGHT
# ============================================================
RUN mkdir -p /ms-playwright && \
    playwright install --with-deps chromium && \
    chmod -R 755 /ms-playwright

# ============================================================
# 📁 CÓDIGO
# ============================================================
# bust-cache-v4
COPY app/ ./app/
COPY frontend/ ./frontend/

# ============================================================
# 📜 ENTRYPOINT
# ============================================================
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# ============================================================
# 🔐 PERMISSÕES
# ============================================================
RUN chown -R appuser:appgroup /app
USER appuser

# ============================================================
# 🌐 PORTA
# ============================================================
EXPOSE 8000

# ============================================================
# ❤️ HEALTHCHECK
# ============================================================
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')"

# ============================================================
# 🚀 START
# ============================================================
ENTRYPOINT ["./entrypoint.sh"]
