# ============================================================
# app/services/analise_service.py
# ============================================================

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.resultado import Resultado
from app.models.sinal import Sinal

logger = logging.getLogger(__name__)

# Streak mínimo para disparar sinal (4 consecutivos)
STREAK_MINIMO = 4
CONFIANCA_STREAK = 100.0


def _calcular_streak_atual(serie: list[str]) -> tuple[str, int]:
    """
    Recebe lista do mais antigo ao mais recente.
    Retorna (valor_atual, quantidade_consecutiva).
    Ignora 'branco' na contagem.
    """
    if not serie:
        return ("", 0)

    sem_branco = [r for r in serie if r != "branco"]
    if not sem_branco:
        return ("", 0)

    ultimo = sem_branco[-1]
    streak = 0
    for r in reversed(sem_branco):
        if r == ultimo:
            streak += 1
        else:
            break

    return (ultimo, streak)


def analisar_e_gerar_sinal(db: Session) -> Optional[Sinal]:
    """
    Regra:
      - 4+ azuis consecutivos  → entra VERMELHO
      - 4+ vermelhos consecutivos → entra AZUL
    Ignora branco na contagem.
    Não gera sinal se já existe um pendente (acertou=None).
    Não gera sinal duplicado para o mesmo streak já sinalizado.
    """

    # Não gera novo sinal enquanto tem um pendente
    pendente = (
        db.query(Sinal)
        .filter(Sinal.enviado_telegram == True)
        .filter(Sinal.acertou == None)  # noqa: E711
        .first()
    )
    if pendente:
        logger.debug("Sinal pendente ainda não verificado — aguardando resultado.")
        return None

    # Busca histórico recente
    registros = (
        db.query(Resultado)
        .order_by(Resultado.timestamp.desc())
        .limit(50)
        .all()
    )

    if len(registros) < STREAK_MINIMO:
        logger.debug("Histórico insuficiente para análise.")
        return None

    # Do mais antigo ao mais recente
    serie = [r.resultado.lower() for r in reversed(registros)]

    cor_atual, streak = _calcular_streak_atual(serie)

    logger.debug(f"Streak atual: {streak}x {cor_atual}")

    if streak < STREAK_MINIMO:
        logger.debug(f"Streak {streak} abaixo do mínimo ({STREAK_MINIMO}) — sem sinal.")
        return None

    # Define entrada contrária ao streak
    if cor_atual in ("verde", "azul"):
        tipo = "entrada vermelho"
    elif cor_atual == "vermelho":
        tipo = "entrada azul"
    else:
        logger.debug("Streak de brancos — sem sinal.")
        return None

    # ✅ CORREÇÃO: evita gerar sinal duplicado para o mesmo streak
    # Verifica se o último sinal já foi gerado com esse mesmo tipo
    ultimo_sinal = (
        db.query(Sinal)
        .order_by(Sinal.timestamp.desc())
        .first()
    )
    if ultimo_sinal and ultimo_sinal.tipo == tipo:
        logger.debug(f"Sinal '{tipo}' já foi gerado para este streak — ignorando duplicata.")
        return None

    descricao = f"{streak} {cor_atual}(s) consecutivos → {tipo}"
    logger.info(f"🎯 Sinal detectado: {descricao}")

    novo = Sinal(
        tipo=tipo,
        confianca=CONFIANCA_STREAK,
        algoritmo="regra_streak",
        descricao=descricao,
        enviado_telegram=False,
        gale=0,
        timestamp=datetime.now(timezone.utc),
    )

    db.add(novo)
    db.commit()
    db.refresh(novo)

    return novo


# ============================================================
# TAXA DE ACERTO
# ============================================================

def calcular_taxa_acerto(db: Session) -> dict:
    sinais = db.query(Sinal).filter(Sinal.acertou.isnot(None)).all()

    if not sinais:
        return {"total_verificados": 0, "acertos": 0, "erros": 0, "taxa_acerto": 0.0}

    acertos = sum(1 for s in sinais if s.acertou is True)
    taxa = (acertos / len(sinais)) * 100.0

    return {
        "total_verificados": len(sinais),
        "acertos": acertos,
        "erros": len(sinais) - acertos,
        "taxa_acerto": round(taxa, 2),
    }
