from playwright.sync_api import sync_playwright
import logging

logger = logging.getLogger(__name__)

def coletar_resultado():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto("https://tipminer.com/history/bac-bo", timeout=30000)

            page.wait_for_timeout(5000)  # espera carregar

            # 🔍 AJUSTE ESSE SELECTOR SE PRECISAR
            elementos = page.query_selector_all(".history-item")

            if not elementos:
                logger.error("❌ Nenhum resultado encontrado no scraping")
                browser.close()
                return None

            texto = elementos[0].inner_text().lower()

            browser.close()

            if "blue" in texto:
                return "azul"
            elif "red" in texto:
                return "vermelho"
            elif "tie" in texto:
                return "branco"

            return None

    except Exception as e:
        logger.error(f"❌ Erro scraping: {e}")
        return None
