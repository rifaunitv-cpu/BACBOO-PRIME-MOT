# ============================================================
# app/services/coleta_service.py
# ============================================================

import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.models.resultado import Resultado
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ------------------------------------------------------------------
# Coletores
# ------------------------------------------------------------------

def _coletar_via_scraping() -> str:
    from app.services.scraper_bacbo import coletar_resultado_bacbo
    return coletar_resultado_bacbo(debug=False)


def _coletar_simulado() -> str:
    import random
    return random.choices(
        ["verde", "vermelho", "branco"],
        weights=[0.46, 0.46, 0.08]
    )[0]


COLETORES = {
    "scraping": _coletar_via_scraping,
    "simulado": _coletar_simulado,
}

# ------------------------------------------------------------------
# Função principal — COM o parâmetro fonte
# ------------------------------------------------------------------

def coletar_novo_resultado(db: Session, fonte: str = "scraping") -> Resultado:
    """
    Coleta um novo resultado e persiste no banco.
    fonte: "scraping" (real via TipMiner) ou "simulado"
    """
    coletor = COLETORES.get(fonte, _coletar_simulado)

    try:
        valor = coletor()
        logger.debug(f"Resultado coletado via '{fonte}': {valor}")
    except Exception as e:
        logger.error(f"Erro ao coletar de '{fonte}': {e}. Usando simulado.")
        valor = _coletar_simulado()

    novo = Resultado(
        resultado=valor,
        fonte=fonte,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)

    logger.info(f"Resultado salvo → id={novo.id} valor='{novo.resultado}'")
    return novo


def buscar_ultimos_resultados(db: Session, limite: int = 100) -> list[Resultado]:
    return (
        db.query(Resultado)
        .order_by(Resultado.timestamp.desc())
        .limit(limite)
        .all()
    )


def contar_resultados(db: Session) -> int:
    return db.query(Resultado).count()
