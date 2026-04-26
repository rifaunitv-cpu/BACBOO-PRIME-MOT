# ============================================================
# app/services/coleta_service.py (FINAL 100%)
# ============================================================

import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.models.resultado import Resultado
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ============================================================
# SCRAPING REAL
# ============================================================

def _coletar_via_scraping() -> Optional[str]:
    try:
        from app.services.scraper_bacbo import coletar_resultado

        # ✅ SEM debug
        resultado = coletar_resultado()

        if resultado is None:
            logger.error("❌ Scraping retornou None")
            return None

        return resultado

    except Exception as e:
        logger.error(f"❌ Erro no scraping: {e}")
        return None


# ============================================================
# SIMULADO (MANUAL)
# ============================================================

def _coletar_simulado() -> str:
    import random
    return random.choice(["azul", "vermelho", "branco"])


COLETORES = {
    "scraping": _coletar_via_scraping,
    "simulado": _coletar_simulado,
}


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def coletar_novo_resultado(
    db: Session,
    fonte: str = "scraping"
) -> Optional[Resultado]:

    coletor = COLETORES.get(fonte)

    if coletor is None:
        logger.error(f"❌ Fonte inválida: {fonte}")
        return None

    try:
        valor = coletor()

        if valor is None:
            logger.error("❌ Coleta falhou — NÃO salvando")
            return None

    except Exception as e:
        logger.error(f"❌ Erro na coleta: {e}")
        return None

    # 🚫 evita duplicado
    ultimo = (
        db.query(Resultado)
        .order_by(Resultado.timestamp.desc())
        .first()
    )

    if ultimo and ultimo.resultado == valor:
        logger.info("⚠️ Resultado repetido — ignorando")
        return None

    novo = Resultado(
        resultado=valor,
        fonte="scraping_real",
        timestamp=datetime.now(timezone.utc),
    )

    db.add(novo)
    db.commit()
    db.refresh(novo)

    logger.info(f"✅ Resultado salvo → {valor}")

    return novo


# ============================================================
# CONSULTAS
# ============================================================

def buscar_ultimos_resultados(db: Session, limite: int = 100):
    return (
        db.query(Resultado)
        .order_by(Resultado.timestamp.desc())
        .limit(limite)
        .all()
    )


def contar_resultados(db: Session) -> int:
    return db.query(Resultado).count()
