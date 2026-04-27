# ============================================================
# app/services/scheduler_service.py
# ============================================================

import logging
import time
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

from app.config import get_settings
from app.database.connection import SessionLocal
from app.services.coleta_service import coletar_novo_resultado
from app.services.analise_service import analisar_e_gerar_sinal
from app.services.telegram_service import enviar_sinal, verificar_resultado

logger = logging.getLogger(__name__)
settings = get_settings()

_scheduler: BackgroundScheduler | None = None

_stats = {
    "ciclos_executados": 0,
    "sinais_enviados": 0,
    "ultimo_ciclo": None,
    "erros": 0,
}

ultimo_scraping = 0


def _executar_ciclo() -> None:
    global _stats, ultimo_scraping

    logger.debug("Iniciando ciclo de automação...")

    # ✅ Nova sessão a cada ciclo — elimina cache do SQLAlchemy
    db = SessionLocal()

    try:
        # ===================================================
        # PASSO 1 — COLETA (a cada 30s)
        # ===================================================
        agora = time.time()

        if agora - ultimo_scraping > 30:
            coletar_novo_resultado(db, fonte="scraping")
            db.close()
            # ✅ Abre nova sessão limpa após gravar resultado
            db = SessionLocal()
            ultimo_scraping = agora
        else:
            logger.debug("Pulando scraping (aguardando intervalo)")

        # ===================================================
        # PASSO 2 — VERIFICAR RESULTADO PENDENTE
        # ===================================================
        verificar_resultado(db)
        db.close()
        db = SessionLocal()

        # ===================================================
        # PASSO 3 — ANÁLISE (sempre roda com sessão fresca)
        # ===================================================
        sinal = analisar_e_gerar_sinal(db)

        # ===================================================
        # PASSO 4 — ENVIO TELEGRAM
        # ===================================================
        if sinal:
            enviado = enviar_sinal(sinal)

            if enviado:
                sinal.enviado_telegram = True
                db.commit()
                _stats["sinais_enviados"] += 1
                logger.info(f"Sinal {sinal.id} enviado ao Telegram ✓")
            else:
                logger.warning(f"Sinal {sinal.id} NÃO enviado ao Telegram")

        _stats["ciclos_executados"] += 1
        _stats["ultimo_ciclo"] = datetime.now(timezone.utc).isoformat()

    except Exception as e:
        logger.error(f"Erro no ciclo de automação: {e}", exc_info=True)
        _stats["erros"] += 1

    finally:
        db.close()


def _listener_jobs(event) -> None:
    if event.exception:
        logger.error(f"Job {event.job_id} falhou: {event.exception}")
    else:
        logger.debug(f"Job {event.job_id} executado com sucesso.")


def iniciar_scheduler() -> None:
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        logger.warning("Scheduler já está rodando.")
        return

    _scheduler = BackgroundScheduler(timezone="UTC")

    _scheduler.add_job(
        func=_executar_ciclo,
        trigger=IntervalTrigger(seconds=settings.collect_interval_seconds),
        id="ciclo_principal",
        name="Coleta → Análise → Telegram → Resultado",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    _scheduler.add_listener(_listener_jobs, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)
    _scheduler.start()

    logger.info(f"Scheduler iniciado a cada {settings.collect_interval_seconds}s")


def parar_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler parado.")


def status_scheduler() -> dict:
    if _scheduler is None:
        return {"rodando": False, **_stats}

    return {
        "rodando": _scheduler.running,
        "intervalo_segundos": settings.collect_interval_seconds,
        **_stats,
    }
