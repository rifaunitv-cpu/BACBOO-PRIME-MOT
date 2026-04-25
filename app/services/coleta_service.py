# ============================================================
# COLETA REAL BACBO (TIPMINER) - VERSÃO CORRIGIDA
# ============================================================

import logging
from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models.resultado import Resultado

logger = logging.getLogger(__name__)

URL = "https://www.tipminer.com/br/historico/blaze/bac-bo-ao-vivo"

# ------------------------------------------------------------------
# SCRAPING REAL (TIPMINER)
# ------------------------------------------------------------------

def _coletar_via_scraping() -> Optional[str]:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "pt-BR,pt;q=0.9"
        }

        response = requests.get(URL, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # pega células do resultado
        elementos = soup.select("div[class*='bg-cell-']")

        if not elementos:
            logger.warning("Nenhum resultado encontrado no site")
            return None

        el = elementos[0]
        classes = el.get("class", [])

        if any("player" in c for c in classes):
            return "vermelho"

        if any("banker" in c for c in classes):
            return "azul"

        if any("tie" in c for c in classes):
            return "branco"

        logger.warning(f"Classe desconhecida: {classes}")
        return None

    except Exception as e:
        logger.error(f"Erro no scraping: {e}")
        return None


# ------------------------------------------------------------------
# FUNÇÃO PRINCIPAL
# ------------------------------------------------------------------

def coletar_novo_resultado(db: Session) -> Optional[Resultado]:
    valor = _coletar_via_scraping()

    if not valor:
        return None

    # 🔥 EVITA DUPLICAR RESULTADO
    ultimo = (
        db.query(Resultado)
        .order_by(Resultado.timestamp.desc())
        .first()
    )

    if ultimo and ultimo.resultado == valor:
        logger.info("Resultado repetido, ignorando...")
        return None

    novo = Resultado(
        resultado=valor,
        fonte="tipminer",
        timestamp=datetime.now(timezone.utc),
    )

    db.add(novo)
    db.commit()
    db.refresh(novo)

    logger.info(f"Resultado salvo: {valor}")

    return novo


# ------------------------------------------------------------------
# CONSULTAS
# ------------------------------------------------------------------

def buscar_ultimos_resultados(db: Session, limite: int = 100):
    return (
        db.query(Resultado)
        .order_by(Resultado.timestamp.desc())
        .limit(limite)
        .all()
    )


def contar_resultados(db: Session) -> int:
    return db.query(Resultado).count()
