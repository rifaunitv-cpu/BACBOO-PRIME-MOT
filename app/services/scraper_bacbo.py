import re
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# PARSER (PEGA PLAYER / BANKER / TIE + HORA)
# ─────────────────────────────────────────────
def parse_rounds(soup):
    rounds = []

    elementos = soup.find_all("div", title=True)

    for el in elementos:
        title = el.get("title", "")

        # 🔥 PADRÃO CORRETO (AGORA COM BANKER)
        match = re.search(r"(PLAYER|BANKER|TIE)\s*-\s*\d+\s*-\s*(\d{2}:\d{2})", title)

        if match:
            rounds.append({
                "lado": match.group(1),
                "time": match.group(2)
            })

    return rounds


# ─────────────────────────────────────────────
# FUNÇÃO PRINCIPAL
# ─────────────────────────────────────────────
def coletar_resultado_bacbo(debug: bool = False):
  import requests

STREAM_URL = "https://www.tipminer.com/stream/rounds/BAC_BO/670c0a4411256f2d32d197b4/v2/live?k=3"

def coletar_resultado_bacbo(debug: bool = False):
    try:
        resp = requests.get(STREAM_URL, stream=True, timeout=10)

        for linha in resp.iter_lines():
            if linha:
                texto = linha.decode("utf-8")

                if "PLAYER" in texto or "BANKER" in texto or "TIE" in texto:

                    if debug:
                        print(f"🎯 RAW: {texto}")

                    if "PLAYER" in texto:
                        return "azul"
                    elif "BANKER" in texto:
                        return "vermelho"
                    elif "TIE" in texto:
                        return "branco"

        return None

    except Exception as e:
        if debug:
            print(f"Erro no scraper: {e}")
        return None
