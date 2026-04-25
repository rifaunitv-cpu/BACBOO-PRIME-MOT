# ============================================================
# app/services/scheduler_service.py
# Automação do ciclo coleta → análise → envio.
#
# Usa APScheduler para executar o ciclo periodicamente.
# O intervalo é configurado via COLLECT_INTERVAL_SECONDS no .env
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

# Instância global do scheduler
_scheduler: BackgroundScheduler | None = None

# Estatísticas do scheduler (para o endpoint de status)
_stats = {
    "ciclos_executados": 0,
    "sinais_enviados": 0,
    "ultimo_ciclo": None,
    "erros": 0,
}


def _executar_ciclo() -> None:
    """
    Ciclo completo de automação:
      1. Coleta um novo resultado
      2. Analisa o histórico
      3. Se houver sinal, envia ao Telegram e atualiza o banco
    """
    global _stats

    logger.debug("Iniciando ciclo de automação...")
    db: Session = SessionLocal()

    try:
        # PASSO 1 — Coleta
        resultado = coletar_novo_resultado(db, fonte="simulado")
        logger.debug(f"Ciclo: resultado coletado → {resultado.resultado}")

        # PASSO 2 — Análise
        sinal = analisar_e_gerar_sinal(db)

        # PASSO 3 — Envio (se houver sinal)
        if sinal is not None:
            enviado = enviar_sinal(sinal)
            if enviado:
                sinal.enviado_telegram = True
                db.commit()
                _stats["sinais_enviados"] += 1
                logger.info(f"Sinal {sinal.id} enviado ao Telegram ✓")
            else:
                logger.warning(
                    f"Sinal {sinal.id} gerado mas NÃO enviado ao Telegram "
                    "(verifique TELEGRAM_TOKEN e TELEGRAM_CHAT_ID no .env)"
                )

        _stats["ciclos_executados"] += 1
        _stats["ultimo_ciclo"] = datetime.now(timezone.utc).isoformat()

    except Exception as e:
        logger.error(f"Erro no ciclo de automação: {e}", exc_info=True)
        _stats["erros"] += 1
    finally:
        db.close()


def _listener_jobs(event) -> None:
    """Ouve eventos do APScheduler para logging."""
    if event.exception:
        logger.error(f"Job {event.job_id} falhou com exceção: {event.exception}")
    else:
        logger.debug(f"Job {event.job_id} executado com sucesso.")


def iniciar_scheduler() -> None:
    """
    Inicializa e inicia o scheduler em background.
    Chamado no startup do FastAPI.
    """
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        logger.warning("Scheduler já está rodando. Ignorando chamada duplicada.")
        return

    _scheduler = BackgroundScheduler(timezone="UTC")

    # Registra o job principal
    _scheduler.add_job(
        func=_executar_ciclo,
        trigger=IntervalTrigger(seconds=settings.collect_interval_seconds),
        id="ciclo_principal",
        name="Ciclo: coleta → análise → Telegram",
        replace_existing=True,
        max_instances=1,          # Garante que apenas um ciclo rode por vez
        coalesce=True,             # Agrupa execuções perdidas em uma única
    )

    # Registra listener de eventos
    _scheduler.add_listener(_listener_jobs, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)

    _scheduler.start()
    logger.info(
        f"Scheduler iniciado. Ciclo a cada {settings.collect_interval_seconds}s."
    )


def parar_scheduler() -> None:
    """Para o scheduler. Chamado no shutdown do FastAPI."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler parado.")


def status_scheduler() -> dict:
    """Retorna o estado atual do scheduler e as estatísticas."""
    if _scheduler is None:
        return {"rodando": False, **_stats}

    return {
        "rodando": _scheduler.running,
        "intervalo_segundos": settings.collect_interval_seconds,
        **_stats,
    }
