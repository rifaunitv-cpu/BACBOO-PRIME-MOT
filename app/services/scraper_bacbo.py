#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scraper Bac Bo (TipMiner)
Pega o resultado MAIS RECENTE via Playwright (JS renderizado).
Retorna: "azul" | "vermelho" | "branco" | None
"""

import asyncio
import re
import concurrent.futures
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
            print("[SCRAPER] Acessando site...")

            # domcontentloaded — não espera requisições infinitas do site ao vivo
            await page.goto(URL, wait_until="domcontentloaded", timeout=30000)

            # Aguarda o JS renderizar os resultados
            await page.wait_for_selector(
                'div[title*="PLAYER"], div[title*="BANKER"], div[title*="TIE"]',
                timeout=20000,
            )
            await asyncio.sleep(1)

            cells = await page.query_selector_all("div[title]")
            print(f"[SCRAPER] div[title] encontrados: {len(cells)}")

            # Coleta TODOS os resultados válidos e pega o ÚLTIMO (mais recente)
            resultados_encontrados = []
            for cell in cells:
                title = await cell.get_attribute("title") or ""
                match = re.search(r"(PLAYER|BANKER|TIE)", title)
                if match:
                    lado = match.group(1)
                    if lado == "PLAYER":
                        resultados_encontrados.append("azul")
                    elif lado == "BANKER":
                        resultados_encontrados.append("vermelho")
                    elif lado == "TIE":
                        resultados_encontrados.append("branco")

            if not resultados_encontrados:
                print("[SCRAPER] ❌ Nenhum resultado válido encontrado")
                return None

            # O mais recente é o ÚLTIMO da lista (ordem cronológica do DOM)
            mais_recente = resultados_encontrados[-1]
            print(f"[SCRAPER] ✅ {len(resultados_encontrados)} resultados coletados — mais recente: {mais_recente}")
            return mais_recente

        except Exception as e:
            print(f"[SCRAPER] ❌ Exceção: {e}")
            return None

        finally:
            await browser.close()


def _run_scrape_in_thread() -> str | None:
    """
    Executa o scraper assíncrono em uma thread isolada com seu próprio event loop.
    Evita conflito com o event loop do Uvicorn/APScheduler.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_run_new_loop)
        return future.result(timeout=60)


def _run_new_loop() -> str | None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_scrape())
    finally:
        loop.close()


def coletar_resultado_bacbo(debug: bool = False) -> str | None:
    try:
        resultado = _run_scrape_in_thread()
        print(f"[SCRAPER] Resultado final: {resultado}")
        return resultado
    except Exception as e:
        print(f"[SCRAPER] Erro: {e}")
        return None


if __name__ == "__main__":
    r = coletar_resultado_bacbo(debug=True)
    print(f"Resultado: {r}")
