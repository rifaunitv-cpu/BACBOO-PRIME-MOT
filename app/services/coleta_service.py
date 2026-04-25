# ============================================================
# COLETA REAL BACBO (TIPMINER)
# ============================================================

import logging
from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models.resultado import Resultado

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# SCRAPING REAL (TIPMINER)
# ------------------------------------------------------------------

def _coletar_via_scraping() -> str:
    url = "https://www.tipminer.com/br/historico/blaze/bac-bo-ao-vivo"

    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")

    elementos = soup.select("div[class*='bg-cell-']")

    if not elementos:
        raise Exception("Nenhum resultado encontrado")

    el = elementos[0]  # último resultado
    classes = el.get("class", [])

    if any("bg-cell-player" in c for c in classes):
        return "vermelho"
    elif any("bg-cell-banker" in c for c in classes):
        return "azul"
    elif any("bg-cell-tie" in c for c in classes):
        return "branco"

    raise Exception("Resultado desconhecido")


# ------------------------------------------------------------------
# FUNÇÃO PRINCIPAL
# ------------------------------------------------------------------

def coletar_novo_resultado(db: Session) -> Resultado:
    try:
        valor = _coletar_via_scraping()
        fonte = "tipminer"
        logger.info(f"[REAL] Resultado coletado: {valor}")

    except Exception as e:
        logger.error(f"Erro no scraping: {e}")
        return None

    novo = Resultado(
        resultado=valor,
        fonte=fonte,
        timestamp=datetime.now(timezone.utc),
    )

    db.add(novo)
    db.commit()
    db.refresh(novo)

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
