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
    try:
        html = fetch_page()  # já existe no seu código
        soup = BeautifulSoup(html, "lxml")

        rounds = parse_rounds(soup)

        if not rounds:
            if debug:
                print("❌ Nenhum resultado encontrado")
            return None

        # 🔥 pega o MAIS RECENTE
        ultimo = rounds[-1]

        lado = ultimo["lado"]
        horario = ultimo["time"]

        if debug:
            print(f"🎯 Resultado: {lado} | Hora: {horario}")

        # 🎨 CORES CORRETAS
        if lado == "PLAYER":
            return "azul"
        elif lado == "BANKER":
            return "vermelho"
        elif lado == "TIE":
            return "branco"

        return None

    except Exception as e:
        if debug:
            print(f"Erro no scraper: {e}")
        return None
