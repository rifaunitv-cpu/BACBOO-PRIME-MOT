import re
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# NOVO PARSER (PEGA VALOR + HORA DO TITLE)
# ─────────────────────────────────────────────
def parse_rounds(soup):
    rounds = []

    elementos = soup.find_all("div", title=True)

    for el in elementos:
        title = el.get("title", "")

        match = re.search(r"(PLAYER|BANKER).*?(\d+).*?(\d{2}:\d{2})", title)

        if match:
            rounds.append({
                "lado": match.group(1),
                "value": int(match.group(2)),
                "time": match.group(3)
            })

    return rounds


# ─────────────────────────────────────────────
# FUNÇÃO PRINCIPAL (USADA PELO SISTEMA)
# ─────────────────────────────────────────────
def coletar_resultado_bacbo(debug: bool = False):
    try:
        html = fetch_page()  # ⚠️ já existe no seu código
        soup = BeautifulSoup(html, "lxml")

        rounds = parse_rounds(soup)

        if not rounds:
            if debug:
                print("❌ Nenhum resultado encontrado")
            return None

        # pega o mais recente
        ultimo = rounds[0]

        valor = ultimo["value"]
        horario = ultimo["time"]

        if debug:
            print(f"🎯 Último resultado: {valor} | Hora: {horario}")

        # lógica do seu sistema
        if valor == 7:
            return "branco"
        elif valor <= 6:
            return "azul"
        else:
            return "vermelho"

    except Exception as e:
        if debug:
            print(f"Erro no scraper: {e}")
        return None
