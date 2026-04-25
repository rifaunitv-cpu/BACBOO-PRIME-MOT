# 🚀 Sistema de Sinais

Sistema completo de coleta de dados de jogos, análise de padrões e geração de sinais com envio automático para o Telegram.

## Arquitetura

```
signal_system/
├── app/
│   ├── main.py               # Entrypoint FastAPI + lifecycle
│   ├── config.py             # Configurações centralizadas (Pydantic Settings)
│   ├── database/
│   │   ├── __init__.py
│   │   └── connection.py     # Engine SQLAlchemy + get_db
│   ├── models/
│   │   ├── __init__.py
│   │   ├── resultado.py      # ORM: tabela resultados
│   │   └── sinal.py          # ORM: tabela sinais
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── status_routes.py  # GET /
│   │   ├── dados_routes.py   # GET /dados, POST /dados/coletar
│   │   └── sinais_routes.py  # GET /sinais, POST /sinais/gerar
│   └── services/
│       ├── __init__.py
│       ├── coleta_service.py    # Coleta/simulação de dados
│       ├── analise_service.py   # Regra simples + Random Forest
│       ├── telegram_service.py  # Envio de mensagens ao Telegram
│       └── scheduler_service.py # Loop automático (APScheduler)
├── frontend/
│   └── index.html            # Painel de controle (HTML/JS puro)
├── migrations/
│   ├── env.py                # Configuração Alembic
│   ├── script.py.mako        # Template de migration
│   └── versions/
│       └── 001_inicial.py    # Migration inicial
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── requirements.txt
├── alembic.ini
└── .env.example
```

## Endpoints da API

| Método | Rota                    | Descrição                            |
|--------|-------------------------|--------------------------------------|
| GET    | `/`                     | Status da API e componentes          |
| GET    | `/dados`                | Últimos resultados coletados         |
| GET    | `/dados/estatisticas`   | Distribuição e streak atual          |
| POST   | `/dados/coletar`        | Força coleta manual                  |
| GET    | `/sinais`               | Lista sinais gerados                 |
| POST   | `/sinais/gerar`         | Força geração de sinal               |
| PATCH  | `/sinais/{id}/acerto`   | Registra acerto/erro do sinal        |
| GET    | `/sinais/taxa-acerto`   | Taxa de acerto histórica             |
| GET    | `/painel`               | Frontend HTML do painel              |
| GET    | `/docs`                 | Swagger UI (documentação interativa) |

---

## ▶ Rodando Localmente

### Pré-requisitos
- Docker + Docker Compose
- (Opcional) Python 3.11+ para desenvolvimento sem Docker

### 1. Clone e configure

```bash
git clone <seu-repo>
cd signal_system

# Cria o arquivo .env a partir do exemplo
cp .env.example .env

# Edite o .env com suas credenciais do Telegram (opcional para testes locais)
nano .env
```

### 2. Suba com Docker Compose

```bash
# Produção
docker compose up --build

# Desenvolvimento (inclui Adminer na porta 8080)
docker compose --profile dev up --build
```

### 3. Acesse

- **API:** http://localhost:8000
- **Painel:** http://localhost:8000/painel
- **Swagger:** http://localhost:8000/docs
- **Adminer (dev):** http://localhost:8080

---

## 🤖 Configurando o Bot do Telegram

### 1. Criar o bot
1. Abra o Telegram e procure `@BotFather`
2. Envie `/newbot` e siga as instruções
3. Copie o token no formato `123456789:AAFxxxxxxx`
4. Cole em `TELEGRAM_TOKEN` no seu `.env`

### 2. Obter o Chat ID
**Para grupo:**
1. Adicione seu bot ao grupo
2. Envie uma mensagem no grupo
3. Acesse: `https://api.telegram.org/bot<SEU_TOKEN>/getUpdates`
4. Copie o `chat.id` (número negativo para grupos)

**Para conversa direta:**
1. Inicie uma conversa com o bot
2. Acesse: `https://api.telegram.org/bot<SEU_TOKEN>/getUpdates`
3. Copie o `chat.id`

---

## ☁ Deploy no Railway

### Via GitHub (recomendado)

1. Faça push do projeto para um repositório GitHub
2. Acesse [railway.app](https://railway.app) e crie um novo projeto
3. Selecione "Deploy from GitHub repo"
4. Adicione um serviço PostgreSQL: **New → Database → PostgreSQL**
5. No serviço da app, vá em **Variables** e configure:

```
DATABASE_URL        = ${{Postgres.DATABASE_URL}}   # Railway injeta automaticamente
TELEGRAM_TOKEN      = seu_token
TELEGRAM_CHAT_ID    = seu_chat_id
APP_ENV             = production
COLLECT_INTERVAL_SECONDS = 30
SIGNAL_MIN_CONFIDENCE    = 60.0
```

6. Em **Settings**, configure:
   - **Start Command:** `./entrypoint.sh`
   - **Health Check Path:** `/`

### Via Railway CLI

```bash
npm install -g @railway/cli
railway login
railway init
railway add --plugin postgresql
railway up
railway variables set TELEGRAM_TOKEN=seu_token
railway variables set TELEGRAM_CHAT_ID=seu_chat_id
```

---

## ☁ Deploy no Render

### Web Service

1. Acesse [render.com](https://render.com) e crie um novo **Web Service**
2. Conecte seu repositório GitHub
3. Configure:
   - **Runtime:** Docker
   - **Dockerfile Path:** `./Dockerfile`
   - **Health Check Path:** `/`

### Banco de dados

1. Crie um novo **PostgreSQL** no Render (plano free disponível)
2. Copie a **Internal Database URL**

### Variáveis de ambiente no Render

```
DATABASE_URL        = <URL interna do PostgreSQL do Render>
TELEGRAM_TOKEN      = seu_token
TELEGRAM_CHAT_ID    = seu_chat_id
APP_ENV             = production
COLLECT_INTERVAL_SECONDS = 30
SIGNAL_MIN_CONFIDENCE    = 60.0
```

### render.yaml (deploy automático)

Crie na raiz do projeto:

```yaml
services:
  - type: web
    name: signal-system
    runtime: docker
    dockerfilePath: ./Dockerfile
    healthCheckPath: /
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: signal-db
          property: connectionString
      - key: TELEGRAM_TOKEN
        sync: false
      - key: TELEGRAM_CHAT_ID
        sync: false
      - key: APP_ENV
        value: production

databases:
  - name: signal-db
    plan: free
```

---

## 🔧 Desenvolvimento sem Docker

```bash
# Cria virtualenv
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Instala dependências
pip install -r requirements.txt

# Sobe PostgreSQL separadamente (ex: via Docker)
docker run -d \
  --name pg_dev \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=signal_db \
  -p 5432:5432 \
  postgres:15-alpine

# Configura .env apontando para localhost
echo "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/signal_db" > .env

# Roda a aplicação com hot-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Migrations com Alembic

```bash
# Gera nova migration
alembic revision --autogenerate -m "descricao da mudanca"

# Aplica migrations
alembic upgrade head

# Reverte última migration
alembic downgrade -1

# Ver histórico
alembic history
```

---

## ➕ Adicionando Nova Fonte de Dados

Para trocar o simulador por dados reais:

1. Abra `app/services/coleta_service.py`
2. Implemente a função `_coletar_de_minha_fonte() -> str`
3. Registre no dicionário `COLETORES`
4. Mude a chamada: `coletar_novo_resultado(db, fonte="minha_fonte")`

Exemplo com API externa:

```python
def _coletar_de_minha_api() -> str:
    import httpx
    resp = httpx.get("https://minha-api.com/resultado", timeout=5)
    resp.raise_for_status()
    return resp.json()["resultado"]  # "verde", "vermelho" ou "branco"

COLETORES = {
    "simulado": _simular_resultado,
    "minha_api": _coletar_de_minha_api,
}
```

---

## 📊 Algoritmos de Análise

### Regra Simples
- Detecta streak de 3+ resultados iguais → prediz alternância
- Detecta padrão ziguezague → prediz continuidade
- Detecta desequilíbrio acumulado → prediz compensação

### Random Forest (ML)
- Treinado automaticamente com histórico disponível
- Features: últimos 3 resultados, soma dos últimos 5/10, média, desvio, streak, alternância
- Mínimo de 30 amostras para treino
- Retreina sob demanda

---

## 🔒 Variáveis de Ambiente

| Variável                    | Padrão                               | Descrição                        |
|-----------------------------|--------------------------------------|----------------------------------|
| `DATABASE_URL`              | postgresql://postgres:postgres@db... | URL de conexão PostgreSQL        |
| `TELEGRAM_TOKEN`            | (obrigatório)                        | Token do bot do Telegram         |
| `TELEGRAM_CHAT_ID`          | (obrigatório)                        | ID do chat/grupo de destino      |
| `APP_ENV`                   | development                          | Ambiente (dev/production)        |
| `LOG_LEVEL`                 | INFO                                 | Nível de log                     |
| `COLLECT_INTERVAL_SECONDS`  | 30                                   | Intervalo entre coletas (seg)    |
| `SIGNAL_MIN_CONFIDENCE`     | 60.0                                 | Confiança mínima para envio (%)  |
| `FRONTEND_ORIGIN`           | *                                    | CORS origin                      |
