#!/bin/sh
# ============================================================
# entrypoint.sh
# Script de inicialização do container
# ============================================================

set -e

echo "============================================="
echo "  Sistema de Sinais — Iniciando container"
echo "============================================="

# Aguarda o PostgreSQL estar disponível antes de subir a app
# Usando Python puro para evitar dependência de ferramentas externas
echo "Aguardando banco de dados..."
python -c "
import time, os
from sqlalchemy import create_engine, text
db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/signal_db')
engine = create_engine(db_url)
for i in range(30):
    try:
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        print('Banco de dados disponível!')
        break
    except Exception as e:
        print(f'Tentativa {i+1}/30 — aguardando... ({e})')
        time.sleep(2)
else:
    print('ERRO: Banco de dados não disponível após 60s. Abortando.')
    exit(1)
"

echo "Iniciando servidor uvicorn..."
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 1 \
  --log-level info \
  --access-log
