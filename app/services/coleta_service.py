# ============================================================
# coleta_service.py (CORRIGIDO)
# ============================================================

import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.models.resultado import Resultado

logger = logging.getLogger(__name__)


def coletar_novo_resultado(db: Session) -> Optional[Resultado]:

    from app.services.scraper_bacbo import coletar_resultado

    try:
        valor = coletar_resultado()

        if valor is None:
            logger.error("Scraping falhou — não salvando")
            return None

    except Exception as e:
        logger.error(f"Erro coleta: {e}")
        return None

    # evita duplicado
    ultimo = (
        db.query(Resultado)
        .order_by(Resultado.timestamp.desc())
        .first()
    )

    if ultimo and ultimo.resultado == valor:
        logger.info("Resultado repetido — ignorando")
        return None

    novo = Resultado(
        resultado=valor,
        fonte="scraping",
        timestamp=datetime.now(timezone.utc),
    )

    db.add(novo)
    db.commit()
    db.refresh(novo)

    logger.info(f"Resultado salvo: {valor}")

    return novo
