# ============================================================
# app/services/scheduler_service.py
# Automação do ciclo coleta → análise → envio.
# ============================================================

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.connection import SessionLocal
from app.services.coleta_service import coletar_novo_resultado
from app.services.analise_service import analisar_e_gerar_sinal
from app.services.telegram_service import enviar_sinal

logger = logging.getLogger(__name__)
settings = get_settings()

_scheduler: BackgroundScheduler | None = None

_stats = {
    "ciclos_executados": 0,
    "sinais_enviados": 0,
    "ultimo_ciclo": None,
    "erros": 0,
}


def _executar_ciclo() -> None:
    global _stats

    logger.debug("Iniciando ciclo de automação...")
    db: Session = SessionLocal()

    try:
        # ===================================================
        # PASSO 1 — COLETA REAL (SCRAPING)
        # ===================================================
        resultado = coletar_novo_resultado(db, fonte="scraping")

        if not resultado:
            logger.warning("Nenhum resultado coletado (falha ou repetido)")
            return

        logger.debug(f"Ciclo: resultado coletado → {resultado.resultado}")

        # ===================================================
        # PASSO 2 — ANÁLISE
        # ===================================================
        sinal = analisar_e_gerar_sinal(db)

        # ===================================================
        # PASSO 3 — ENVIO TELEGRAM
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
        name="Coleta → Análise → Telegram",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    _scheduler.add_listener(_listener_jobs, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)

    _scheduler.start()

    logger.info(
        f"Scheduler iniciado a cada {settings.collect_interval_seconds}s"
    )


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
