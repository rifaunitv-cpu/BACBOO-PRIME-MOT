# ============================================================
# app/main.py
# ============================================================
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import get_settings, setup_logging
from app.database.connection import create_tables
from app.services.scheduler_service import iniciar_scheduler, parar_scheduler
from app.routes import status_routes, dados_routes, sinais_routes

settings = get_settings()
setup_logging(settings)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("  Sistema de Sinais — iniciando...")
    logger.info(f"  Ambiente: {settings.app_env}")
    logger.info(f"  Intervalo de coleta: {settings.collect_interval_seconds}s")
    logger.info("=" * 60)
    create_tables()
    iniciar_scheduler()
    logger.info("Aplicação pronta para receber requisições.")
    yield
    logger.info("Encerrando aplicação...")
    parar_scheduler()
    logger.info("Scheduler parado. Até logo!")


app = FastAPI(
    title="Sistema de Sinais",
    description="API para coleta de dados de jogos, análise de padrões e geração automática de sinais com envio ao Telegram.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(status_routes.router)
app.include_router(dados_routes.router)
app.include_router(sinais_routes.router)



FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/painel", include_in_schema=False)
    def painel():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
