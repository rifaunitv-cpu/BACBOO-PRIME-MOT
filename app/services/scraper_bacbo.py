import requests

# 🔥 URL DO STREAM (TEMPO REAL)
STREAM_URL = "https://www.tipminer.com/stream/rounds/BAC_BO/670c0a4411256f2d32d197b4/v2/live?k=3"


# ============================================================
# FUNÇÃO PRINCIPAL (USADA PELO SISTEMA)
# ============================================================
def coletar_resultado_bacbo(debug: bool = False):
    try:
        resp = requests.get(STREAM_URL, stream=True, timeout=10)

        for linha in resp.iter_lines():
            if not linha:
                continue

            texto = linha.decode("utf-8")

            # 🔥 DEBUG PRA VER O QUE TÁ CHEGANDO
            if debug:
                print("RAW:", texto)

            # 🔥 FILTRO CORRETO
            if "PLAYER" in texto:
                if debug:
                    print("🎯 Resultado: AZUL (PLAYER)")
                return "azul"

            elif "BANKER" in texto:
                if debug:
                    print("🎯 Resultado: VERMELHO (BANKER)")
                return "vermelho"

            elif "TIE" in texto:
                if debug:
                    print("🎯 Resultado: BRANCO (TIE)")
                return "branco"

        return None

    except Exception as e:
        if debug:
            print(f"Erro no scraper: {e}")
        return None
