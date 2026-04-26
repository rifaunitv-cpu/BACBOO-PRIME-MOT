# ============================================================
# scraper_bacbo.py
# ============================================================
from playwright.sync_api import sync_playwright
import logging

logger = logging.getLogger(__name__)


def coletar_resultado():
    """
    Retorna:
    - "azul"
    - "vermelho"
    - "branco"
    - None (se falhar)
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://tipminer.com/history/bac-bo", timeout=30000)
            page.wait_for_timeout(6000)
            conteudo = page.content().lower()
            browser.close()

            if "blue" in conteudo:
                return "azul"
            elif "red" in conteudo:
                return "vermelho"
            elif "tie" in conteudo:
                return "branco"
            return None

    except Exception as e:
        logger.error(f"Erro scraping: {e}")
        return None
