#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scraper Bac Bo (TipMiner)
Pega resultado via HTML (PLAYER / BANKER / TIE)
"""

import requests
import re
from bs4 import BeautifulSoup

# 🔗 URL DO HISTÓRICO
URL = "https://www.tipminer.com/br/historico/blaze/bac-bo-ao-vivo"


# ============================================================
# FUNÇÃO PRINCIPAL (USADA PELO SISTEMA)
# ============================================================
def coletar_resultado_bacbo(debug: bool = False):
    try:
        response = requests.get(URL, timeout=10)

        if response.status_code != 200:
            if debug:
                print("Erro HTTP:", response.status_code)
            return None

        soup = BeautifulSoup(response.text, "lxml")

        # 🔥 pega todos elementos com title
        elementos = soup.find_all("div", title=True)

        if not elementos:
            if debug:
                print("Nenhum elemento com title encontrado")
            return None

        # 🔥 percorre até achar o primeiro válido (mais recente)
        for el in elementos:
            title = el.get("title", "")

            # Exemplo:
            # PLAYER - 7 - 14:37
            match = re.search(r"(PLAYER|BANKER|TIE)", title)

            if match:
                lado = match.group(1)

                if debug:
                    print(f"🎯 Encontrado: {title}")

                if lado == "PLAYER":
                    return "azul"

                elif lado == "BANKER":
                    return "vermelho"

                elif lado == "TIE":
                    return "branco"

        if debug:
            print("Nenhum resultado válido encontrado")

        return None

    except Exception as e:
        if debug:
            print(f"Erro no scraper: {e}")
        return None
