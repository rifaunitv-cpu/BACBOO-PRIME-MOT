# ============================================================
# app/routes/status_routes.py
# Rota GET / — status geral da API
# ============================================================

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db, check_db_connection
from app.services.scheduler_service import status_scheduler
from app.services.telegram_service import testar_conexao
from app.config import get_settings

router = APIRouter(tags=["Status"])
logger = logging.getLogger(__name__)
settings = get_settings()


@router.get("/", summary="Status da API")
def get_status(db: Session = Depends(get_db)):
    """
    Endpoint de health-check da aplicação.
    Verifica banco de dados, scheduler e conexão com Telegram.
    """
    db_ok = check_db_connection()
    scheduler = status_scheduler()
    telegram = testar_conexao()

    return {
        "status": "ok" if db_ok else "degradado",
        "versao": "1.0.0",
        "ambiente": settings.app_env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "componentes": {
            "banco_de_dados": "ok" if db_ok else "erro",
            "scheduler": "rodando" if scheduler.get("rodando") else "parado",
            "telegram": "ok" if telegram.get("ok") else "não configurado",
        },
        "scheduler": scheduler,
        "telegram_bot": telegram,
    }
