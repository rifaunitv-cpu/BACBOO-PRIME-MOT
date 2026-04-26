# ============================================================
# app/services/scraper_bacbo.py
# Coleta resultado real do Bac Bo via API pública da Blaze
# SEM Playwright, SEM login, SEM dependências pesadas
# ============================================================

import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

# API pública da Blaze
URL = "https://blaze.bet.br/api/singleplayer-originals/originals/bac_bo/recent/1/simple"
TIMEOUT = 15

# ============================================================
# MAPEAMENTO CORRETO — Bac Bo Blaze
#   player  / jogador = AZUL      🔵
#   banker  / banca   = VERMELHO  🔴
#   tie     / empate  = BRANCO    ⚪
# ============================================================
MAPA_RESULTADO = {
    "player":  "azul",
    "banker":  "vermelho",
    "tie":     "branco",
    "jogador": "azul",
    "banca":   "vermelho",
    "empate":  "branco",
    "1":       "azul",
    "2":       "vermelho",
    "0":       "branco",
}


def coletar_resultado_bacbo(debug: bool = False) -> Optional[str]:
    """
    Consulta a API pública da Blaze e retorna o resultado
    mais recente do Bac Bo ao Vivo.

    Returns:
        "azul"     → Jogador venceu  🔵
        "vermelho" → Banca venceu    🔴
        "branco"   → Empate          ⚪
        None       → Falha na coleta (não usa fallback)
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://blaze.bet.br/",
        }

        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.get(URL, headers=headers)

        if debug:
            print(f"[DEBUG] Status: {response.status_code}")
            print(f"[DEBUG] Body: {response.text[:500]}")

        if response.status_code != 200:
            logger.warning(f"API Blaze retornou status {response.status_code}")
            return None

        data = response.json()

        # Pega a rodada mais recente
        if isinstance(data, list) and len(data) > 0:
            rodada = data[0]
        elif isinstance(data, dict):
            rodada = data
        else:
            logger.warning("Formato inesperado da API Blaze")
            return None

        if debug:
            print(f"[DEBUG] Rodada: {rodada}")

        # Tenta os campos mais comuns que a API pode retornar
        resultado_raw = (
            rodada.get("winner") or
            rodada.get("result") or
            rodada.get("color") or
            rodada.get("side") or
            rodada.get("outcome") or
            ""
        )

        resultado_raw = str(resultado_raw).lower().strip()
        valor = MAPA_RESULTADO.get(resultado_raw)

        if valor:
            logger.info(f"Resultado coletado da API Blaze: {valor} (raw='{resultado_raw}')")
            return valor

        logger.warning(f"Campo desconhecido: '{resultado_raw}' — rodada completa: {rodada}")
        return None

    except httpx.TimeoutException:
        logger.error(f"Timeout na API Blaze ({TIMEOUT}s)")
        return None
    except Exception as e:
        logger.error(f"Erro ao consultar API Blaze: {e}", exc_info=True)
        return None


# ------------------------------------------------------------------
# Teste direto
# ------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print("Coletando resultado real do Bac Bo via API Blaze...")
    r = coletar_resultado_bacbo(debug=True)
    print(f"\n>>> Resultado: {r}")
