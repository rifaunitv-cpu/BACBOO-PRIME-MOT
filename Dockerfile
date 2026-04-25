# ============================================================
# Dockerfile
# Imagem de produção para a aplicação FastAPI
# ============================================================

# Usa Python slim para imagem menor
FROM python:3.11-slim

# Define variáveis de ambiente do Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Cria usuário não-root para segurança
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Diretório de trabalho
WORKDIR /app

# Instala dependências do sistema necessárias para psycopg2 e scikit-learn
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python
# Copiado antes do código para aproveitar cache de camadas do Docker
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY app/ ./app/
COPY frontend/ ./frontend/

# Copia o script de entrypoint
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Muda para o usuário não-root
RUN chown -R appuser:appgroup /app
USER appuser

# Porta padrão da aplicação
EXPOSE 8000

# Healthcheck do Docker
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')"

# Entrypoint
ENTRYPOINT ["./entrypoint.sh"]
