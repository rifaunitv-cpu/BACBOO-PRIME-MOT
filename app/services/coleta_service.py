#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scraper Bac Bo (TipMiner) — versão DEBUG
"""

import asyncio
import re
from playwright.async_api import async_playwright

URL = "https://www.tipminer.com/br/historico/blaze/bac-bo-ao-vivo"


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

        # Simula navegador real para evitar bloqueio
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="pt-BR",
        )
        page = await context.new_page()

        try:
            print(f"[SCRAPER] Acessando {URL} ...")
            await page.goto(URL, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(3)

            # DEBUG: mostra o título da página
            titulo = await page.title()
            print(f"[SCRAPER] Título da página: {titulo}")

            # DEBUG: tenta achar qualquer div com title
            all_titles = await page.query_selector_all("div[title]")
            print(f"[SCRAPER] Total de div[title] encontrados: {len(all_titles)}")

            # Mostra os primeiros 5 titles para diagnóstico
            for i, el in enumerate(all_titles[:5]):
                t = await el.get_attribute("title") or ""
                print(f"[SCRAPER] title[{i}]: {t}")

            # Tenta achar resultado
            for cell in all_titles:
                title = await cell.get_attribute("title") or ""
                match = re.search(r"(PLAYER|BANKER|TIE)", title)
                if match:
                    lado = match.group(1)
                    print(f"[SCRAPER] ✅ Resultado encontrado: {lado} — {title}")
                    if lado == "PLAYER":
                        return "azul"
                    elif lado == "BANKER":
                        return "vermelho"
                    elif lado == "TIE":
                        return "branco"

            print("[SCRAPER] ❌ Nenhum resultado válido encontrado")

        except Exception as e:
            print(f"[SCRAPER] ❌ Exceção: {e}")

        finally:
            await browser.close()

    return None


def coletar_resultado_bacbo(debug: bool = False) -> str | None:
    try:
        resultado = asyncio.run(_scrape())
        print(f"[SCRAPER] Resultado final: {resultado}")
        return resultado
    except Exception as e:
        print(f"[SCRAPER] Erro no asyncio.run: {e}")
        return None


if __name__ == "__main__":
    r = coletar_resultado_bacbo(debug=True)
    print(f"Resultado: {r}")
