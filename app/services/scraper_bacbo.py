#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scraper Bac Bo (TipMiner)
Pega resultado via Playwright (JS renderizado)
Retorna: "azul" | "vermelho" | "branco" | None
"""

import asyncio
import re
from playwright.async_api import async_playwright

# 🔗 URL DO HISTÓRICO
URL = "https://www.tipminer.com/br/historico/blaze/bac-bo-ao-vivo"


# ============================================================
# FUNÇÃO INTERNA ASYNC
# ============================================================
async def _scrape() -> str | None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-setuid-sandbox",
            ],
        )
        page = await browser.new_page()

        try:
            await page.goto(URL, wait_until="networkidle", timeout=60000)

            # Aguarda pelo menos um resultado aparecer
            await page.wait_for_selector(
                'div[title*="PLAYER"], div[title*="BANKER"], div[title*="TIE"]',
                timeout=30000,
            )
            await asyncio.sleep(1)

            # Pega todos os divs com title
            cells = await page.query_selector_all("div[title]")

            for cell in cells:
                title = await cell.get_attribute("title") or ""

                match = re.search(r"(PLAYER|BANKER|TIE)", title)
                if match:
                    lado = match.group(1)

                    if lado == "PLAYER":
                        return "azul"
                    elif lado == "BANKER":
                        return "vermelho"
                    elif lado == "TIE":
                        return "branco"

        finally:
            await browser.close()

    return None


# ============================================================
# FUNÇÃO PRINCIPAL (USADA PELO SISTEMA) — mesma assinatura
# ============================================================
def coletar_resultado_bacbo(debug: bool = False) -> str | None:
    try:
        resultado = asyncio.run(_scrape())

        if debug:
            if resultado:
                print(f"🎯 Resultado: {resultado}")
            else:
                print("Nenhum resultado válido encontrado")

        return resultado

    except Exception as e:
        if debug:
            print(f"Erro no scraper: {e}")
        return None


# ============================================================
# TESTE DIRETO
# ============================================================
if __name__ == "__main__":
    resultado = coletar_resultado_bacbo(debug=True)
    print(f"Resultado final: {resultado}")
