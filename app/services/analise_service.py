# ============================================================
# analise_service.py (SEM BUG)
# ============================================================

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from app.models.resultado import Resultado
from app.models.sinal import Sinal

logger = logging.getLogger(__name__)

STREAK_MINIMO = 4


def _tem_sinal_pendente(db: Session):
    return db.query(Sinal).filter(
        Sinal.enviado_telegram == True,
        Sinal.acertou.is_(None)
    ).first()


def analisar_e_gerar_sinal(db: Session) -> Optional[Sinal]:

    # bloqueio
    if _tem_sinal_pendente(db):
        logger.info("Sinal pendente — bloqueando")
        return None

    registros = (
        db.query(Resultado)
        .order_by(Resultado.timestamp.desc())
        .limit(20)
        .all()
    )

    if len(registros) < STREAK_MINIMO:
        return None

    serie = [r.resultado for r in reversed(registros) if r.resultado != "branco"]

    if len(serie) < STREAK_MINIMO:
        return None

    ultimo = serie[-1]

    streak = 0
    for r in reversed(serie):
        if r == ultimo:
            streak += 1
        else:
            break

    if streak < STREAK_MINIMO:
        return None

    # inversão
    if ultimo == "vermelho":
        tipo = "entrada azul"
    else:
        tipo = "entrada vermelho"

    descricao = f"{streak}x {ultimo}"

    # evita duplicado
    ultimo_sinal = db.query(Sinal).order_by(Sinal.timestamp.desc()).first()
    if ultimo_sinal and ultimo_sinal.descricao == descricao and ultimo_sinal.acertou is None:
        return None

    novo = Sinal(
        tipo=tipo,
        confianca=100,
        algoritmo="streak",
        descricao=descricao,
        enviado_telegram=False,
        gale=0,
        acertou=None,
        timestamp=datetime.now(timezone.utc),
    )

    db.add(novo)
    db.commit()
    db.refresh(novo)

    logger.info(f"Sinal gerado: {descricao}")

    return novo


# ============================================================
# ATUALIZA RESULTADO (GALE)
# ============================================================

def atualizar_sinal(db: Session, resultado: str):

    sinal = _tem_sinal_pendente(db)

    if not sinal:
        return

    entrada = "azul" if "azul" in sinal.tipo else "vermelho"

    if resultado == entrada:
        sinal.acertou = True
        logger.info("WIN")
    else:
        if sinal.gale < 2:
            sinal.gale += 1
            logger.info(f"GALE {sinal.gale}")
        else:
            sinal.acertou = False
            logger.info("LOSS")

    db.commit()
