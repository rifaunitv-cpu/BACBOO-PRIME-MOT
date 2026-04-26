# ============================================================
# app/services/coleta_service.py (FINAL CORRIGIDO)
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
# COLETA VIA SCRAPING (REAL)
# ============================================================

def _coletar_via_scraping() -> Optional[str]:
    """
    Coleta REAL via scraper.
    Retorna:
        "azul", "vermelho", "branco" ou None (se falhar)
    """
    try:
        # ✅ IMPORT CORRIGIDO
        from app.services.scraper_bacbo import coletar_resultado

        resultado = coletar_resultado()

        if resultado is None:
            logger.error("❌ Scraping retornou None")
            return None

        return resultado

    except Exception as e:
        logger.error(f"❌ Erro no scraping: {e}")
        return None


# ============================================================
# SIMULADO (SÓ TESTE MANUAL)
# ============================================================

def _coletar_simulado() -> str:
    import random
    return random.choices(
        ["azul", "vermelho", "branco"],
        weights=[0.46, 0.46, 0.08]
    )[0]


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

    """
    🔥 REGRAS IMPORTANTES:
    - NÃO salva se scraping falhar
    - NÃO usa fallback automático
    - NÃO duplica resultado
    """

    coletor = COLETORES.get(fonte)

    if coletor is None:
        logger.error(f"❌ Fonte inválida: {fonte}")
        return None

    try:
        valor = coletor()

        # 🚫 NÃO SALVA SE FALHAR
        if valor is None:
            logger.error("❌ Coleta falhou — NÃO salvando no banco")
            return None

        logger.debug(f"📊 Resultado coletado ({fonte}): {valor}")

    except Exception as e:
        logger.error(f"❌ Erro ao coletar: {e}")
        return None

    # ============================================================
    # 🚫 EVITA RESULTADO DUPLICADO
    # ============================================================

    ultimo = (
        db.query(Resultado)
        .order_by(Resultado.timestamp.desc())
        .first()
    )

    if ultimo and ultimo.resultado == valor:
        logger.info("⚠️ Resultado repetido — ignorando")
        return None

    # ============================================================
    # 💾 SALVAR NO BANCO
    # ============================================================

    novo = Resultado(
        resultado=valor,
        fonte="scraping_real" if fonte == "scraping" else "simulado",
        timestamp=datetime.now(timezone.utc),
    )

    db.add(novo)
    db.commit()
    db.refresh(novo)

    logger.info(f"✅ Resultado salvo → id={novo.id} valor='{novo.resultado}'")

    return novo


# ============================================================
# CONSULTAS
# ============================================================

def buscar_ultimos_resultados(
    db: Session,
    limite: int = 100
) -> list[Resultado]:

    return (
        db.query(Resultado)
        .order_by(Resultado.timestamp.desc())
        .limit(limite)
        .all()
    )


def contar_resultados(db: Session) -> int:
    return db.query(Resultado).count()
