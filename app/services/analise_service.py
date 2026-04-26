# ============================================================
# app/services/analise_service.py (CORRIGIDO)
# ============================================================

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.resultado import Resultado
from app.models.sinal import Sinal

logger = logging.getLogger(__name__)

# Quantos consecutivos iguais disparam o sinal
STREAK_MINIMO = 4

# Confiança fixa
CONFIANCA_STREAK = 100.0


# ============================================================
# STREAK
# ============================================================

def _calcular_streak_atual(serie: list[str]) -> tuple[str, int]:
    """
    Recebe lista de resultados do mais antigo ao mais recente.
    Ignora branco.
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


# ============================================================
# BLOQUEIO DE SINAL
# ============================================================

def _tem_sinal_pendente(db: Session) -> Optional[Sinal]:
    return (
        db.query(Sinal)
        .filter(Sinal.enviado_telegram == True)
        .filter(Sinal.acertou.is_(None))
        .order_by(Sinal.timestamp.desc())
        .first()
    )


def _ultimo_sinal(db: Session) -> Optional[Sinal]:
    return (
        db.query(Sinal)
        .order_by(Sinal.timestamp.desc())
        .first()
    )


# ============================================================
# ANÁLISE PRINCIPAL
# ============================================================

def analisar_e_gerar_sinal(db: Session) -> Optional[Sinal]:

    # 🚫 BLOQUEIO 1 — não gerar se tem sinal ativo
    if _tem_sinal_pendente(db):
        logger.info("⚠️ Sinal pendente — bloqueando nova entrada")
        return None

    # Histórico
    registros = (
        db.query(Resultado)
        .order_by(Resultado.timestamp.desc())
        .limit(50)
        .all()
    )

    if len(registros) < STREAK_MINIMO:
        logger.debug("Histórico insuficiente.")
        return None

    # Ordem correta
    serie = [r.resultado.lower() for r in reversed(registros)]

    cor_atual, streak = _calcular_streak_atual(serie)

    logger.info(f"📊 Streak atual: {streak}x {cor_atual}")

    if streak < STREAK_MINIMO:
        return None

    # 🎯 Entrada contrária
    if cor_atual in ("verde", "azul"):
        tipo = "entrada vermelho"
    elif cor_atual == "vermelho":
        tipo = "entrada azul"
    else:
        return None

    descricao = f"{streak} {cor_atual}(s) consecutivos → {tipo}"

    # 🚫 BLOQUEIO 2 — evitar sinal repetido
    ultimo = _ultimo_sinal(db)
    if ultimo and ultimo.descricao == descricao and ultimo.acertou is None:
        logger.info("⚠️ Mesmo sinal já ativo — ignorando duplicado")
        return None

    logger.info(f"🚀 Sinal gerado: {descricao}")

    novo = Sinal(
        tipo=tipo,
        confianca=CONFIANCA_STREAK,
        algoritmo="regra_streak",
        descricao=descricao,
        enviado_telegram=False,
        gale=0,
        acertou=None,
        timestamp=datetime.now(timezone.utc),
    )

    db.add(novo)
    db.commit()
    db.refresh(novo)

    return novo


# ============================================================
# RESULTADO / GALE
# ============================================================

def atualizar_resultado_sinal(db: Session, resultado: str):
    """
    Atualiza o sinal ativo com base no resultado.
    """

    sinal = _tem_sinal_pendente(db)

    if not sinal:
        return

    entrada = "azul" if "azul" in sinal.tipo else "vermelho"

    if resultado == entrada:
        # ✅ WIN
        sinal.acertou = True
        logger.info("✅ WIN")
    else:
        # ❌ LOSS → GALE
        if sinal.gale < 2:
            sinal.gale += 1
            logger.info(f"⚠️ GALE {sinal.gale}")
        else:
            sinal.acertou = False
            logger.info("❌ LOSS FINAL")

    db.commit()


# ============================================================
# TAXA DE ACERTO
# ============================================================

def calcular_taxa_acerto(db: Session) -> dict:
    sinais = db.query(Sinal).filter(Sinal.acertou.isnot(None)).all()

    if not sinais:
        return {
            "total_verificados": 0,
            "acertos": 0,
            "erros": 0,
            "taxa_acerto": 0.0
        }

    acertos = sum(1 for s in sinais if s.acertou is True)
    taxa = (acertos / len(sinais)) * 100.0

    return {
        "total_verificados": len(sinais),
        "acertos": acertos,
        "erros": len(sinais) - acertos,
        "taxa_acerto": round(taxa, 2),
    }
