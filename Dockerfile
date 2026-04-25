# ============================================================
# Dockerfile (COM PLAYWRIGHT PRONTO)
# ============================================================

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# 🔥 DEPENDÊNCIAS DO SISTEMA (COMPATÍVEL COM PLAYWRIGHT)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    wget \
    curl \
    gnupg \
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
    libasound2 \
    libpangocairo-1.0-0 \
    libx11-xcb1 \
    libxfixes3 \
    libxcb1 \
    libxext6 \
    libxi6 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 📦 DEPENDÊNCIAS PYTHON
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 🔥 INSTALA NAVEGADOR DO PLAYWRIGHT
RUN playwright install chromium

# 📁 CÓDIGO
COPY app/ ./app/
COPY frontend/ ./frontend/

# 📜 ENTRYPOINT
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# 🔐 PERMISSÃO
RUN chown -R appuser:appgroup /app
USER appuser

# 🌐 PORTA
EXPOSE 8000

# ❤️ HEALTHCHECK
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')"

# 🚀 START
ENTRYPOINT ["./entrypoint.sh"]
