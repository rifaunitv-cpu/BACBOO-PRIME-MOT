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

# Dispara sinal quando o streak chega EXATAMENTE em 4 consecutivos
STREAK_EXATO = 4
CONFIANCA_STREAK = 100.0


def _calcular_streak_atual(serie: list[str]) -> tuple[str, int]:
    """
    Calcula o streak atual ignorando brancos.
    Branco não conta nem zera o streak de azul/vermelho.
    Retorna (cor_atual, contagem_consecutiva).
    """
    if not serie:
        return ("", 0)

    # Filtra brancos — branco não zera nem conta no streak
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
    # Garante dados frescos do banco
    db.expire_all()

    # Não gera novo sinal enquanto há um pendente de verificação
    pendente = (
        db.query(Sinal)
        .filter(Sinal.enviado_telegram == True)
        .filter(Sinal.acertou == None)  # noqa: E711
        .order_by(Sinal.timestamp.desc())
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

    if len(registros) < STREAK_EXATO:
        logger.debug("Histórico insuficiente para análise.")
        return None

    serie = [r.resultado.lower() for r in reversed(registros)]
    cor_atual, streak = _calcular_streak_atual(serie)

    logger.info(f"📊 Streak atual: {streak}x {cor_atual} | Total registros: {len(registros)}")

    # Só dispara quando o streak é EXATAMENTE 4
    if streak != STREAK_EXATO:
        logger.debug(f"Streak {streak} ≠ {STREAK_EXATO} — sem sinal.")
        return None

    # Define a entrada oposta ao streak:
    # 4x PLAYER (azul)    → entrar em BANKER (vermelho)
    # 4x BANKER (vermelho) → entrar em PLAYER (azul)
    if cor_atual == "azul":
        tipo = "entrada vermelho"
    elif cor_atual == "vermelho":
        tipo = "entrada azul"
    else:
        logger.debug("Streak de cor desconhecida — sem sinal.")
        return None

    # Evita duplicata para o mesmo streak ainda pendente
    ultimo_sinal = (
        db.query(Sinal)
        .order_by(Sinal.timestamp.desc())
        .first()
    )
    if ultimo_sinal and ultimo_sinal.tipo == tipo and ultimo_sinal.acertou is None:
        logger.debug(f"Sinal '{tipo}' já gerado para este streak — ignorando.")
        return None

    descricao = f"4x {cor_atual.upper()} consecutivos → {tipo.upper()}"
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
