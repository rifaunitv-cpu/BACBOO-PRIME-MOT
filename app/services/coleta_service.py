import logging
import importlib
import sys
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.resultado import Resultado

logger = logging.getLogger(__name__)


def coletar_novo_resultado(db: Session, fonte: str = "scraping") -> Optional[Resultado]:
    try:
        # força reload do módulo para evitar cache de import
        if 'app.services.scraper_bacbo' in sys.modules:
            del sys.modules['app.services.scraper_bacbo']
        _mod = importlib.import_module('app.services.scraper_bacbo')
        coletar_resultado = getattr(_mod, 'coletar_resultado')
        valor = coletar_resultado()
        if valor is None:
            logger.error("Scraping falhou — não salvando")
            return None
    except Exception as e:
        logger.error(f"❌ Erro ao coletar: {e}")
        return None

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
        fonte=fonte,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    logger.info(f"✅ Resultado salvo: {valor}")
    return novo


def buscar_ultimos_resultados(db: Session, limite: int = 50) -> List[Resultado]:
    return (
        db.query(Resultado)
        .order_by(Resultado.timestamp.desc())
        .limit(limite)
        .all()
    )


def contar_resultados(db: Session) -> int:
    return db.query(Resultado).count()
