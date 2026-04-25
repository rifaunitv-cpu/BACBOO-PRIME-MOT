# ============================================================
# app/services/scraper_bacbo.py
# Coleta resultado real do Bac Bo ao Vivo via TipMiner
# ============================================================

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

URL = "https://www.tipminer.com/br/historico/blaze/bac-bo-ao-vivo"
TIMEOUT_MS = 25_000
FALLBACK = "vermelho"


def coletar_resultado_bacbo(debug: bool = False) -> str:
    """
    Acessa o TipMiner com Playwright e retorna o resultado
    mais recente do Bac Bo ao Vivo.

    Returns:
        "vermelho" → Player venceu
        "azul"     → Banker venceu
        "branco"   → Tie
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        logger.error("Playwright não instalado. Rode: pip install playwright && playwright install chromium")
        return FALLBACK

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="pt-BR",
        )
        page = context.new_page()

        try:
            if debug:
                print(f"[DEBUG] Acessando {URL}")

            page.goto(URL, wait_until="networkidle", timeout=TIMEOUT_MS)

            # Aguarda a página estabilizar
            page.wait_for_timeout(2000)

            # Tenta cada estratégia em ordem
            for estrategia in [
                _por_classe_player_banker,
                _por_texto_pbt,
                _por_varredura_js,
                _por_cor_background,
            ]:
                resultado = estrategia(page, debug)
                if resultado:
                    logger.info(f"Resultado coletado do TipMiner: {resultado}")
                    return resultado

            logger.warning("Nenhuma estratégia funcionou — usando fallback")
            return FALLBACK

        except PWTimeout:
            logger.error(f"Timeout ao carregar TipMiner ({TIMEOUT_MS}ms)")
            return FALLBACK
        except Exception as e:
            logger.error(f"Erro no scraper TipMiner: {e}", exc_info=True)
            return FALLBACK
        finally:
            context.close()
            browser.close()


# ------------------------------------------------------------------
# Estratégia 1 — classes com "player" / "banker" / "tie"
# ------------------------------------------------------------------
def _por_classe_player_banker(page, debug: bool) -> Optional[str]:
    try:
        resultado = page.evaluate("""
            () => {
                // Pega TODOS os elementos da página
                const todos = Array.from(document.querySelectorAll('*'));

                // Filtra elementos pequenos que parecem células de resultado
                const celulas = todos.filter(el => {
                    const cls = (el.className || '').toString().toLowerCase();
                    const temPalavra = cls.includes('player') || cls.includes('banker') || cls.includes('tie');
                    if (!temPalavra) return false;

                    // Ignora tags de layout/texto
                    const tag = el.tagName.toLowerCase();
                    if (['button','a','nav','header','footer','script','style','p','h1','h2','h3','h4','h5','section'].includes(tag)) return false;

                    // Célula deve ser pequena (resultado visual)
                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) return false;
                    if (rect.width > 120 || rect.height > 120) return false;

                    return true;
                });

                if (celulas.length === 0) return null;

                // Pega a primeira (mais recente — TipMiner lista do mais novo ao mais antigo)
                const cls = (celulas[0].className || '').toString().toLowerCase();
                if (cls.includes('player')) return 'player';
                if (cls.includes('banker')) return 'banker';
                if (cls.includes('tie'))    return 'tie';
                return null;
            }
        """)

        if resultado:
            mapa = {"player": "vermelho", "banker": "azul", "tie": "branco"}
            valor = mapa.get(resultado)
            if debug:
                print(f"[DEBUG] Estratégia 1 → raw='{resultado}' → {valor}")
            return valor
        return None
    except Exception as e:
        logger.debug(f"Estratégia 1 falhou: {e}")
        return None


# ------------------------------------------------------------------
# Estratégia 2 — texto "P", "B", "T" em células pequenas
# ------------------------------------------------------------------
def _por_texto_pbt(page, debug: bool) -> Optional[str]:
    try:
        resultado = page.evaluate("""
            () => {
                const mapa = {
                    'P': 'player', 'PLAYER': 'player',
                    'B': 'banker', 'BANKER': 'banker',
                    'T': 'tie',    'TIE':    'tie',
                };

                const todos = Array.from(document.querySelectorAll('div, span, td, li'));

                for (const el of todos) {
                    const texto = (el.innerText || '').trim().toUpperCase();
                    if (!mapa[texto]) continue;

                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) continue;
                    // Célula pequena
                    if (rect.width > 60 || rect.height > 60) continue;

                    return mapa[texto];
                }
                return null;
            }
        """)

        if resultado:
            mapa = {"player": "vermelho", "banker": "azul", "tie": "branco"}
            valor = mapa.get(resultado)
            if debug:
                print(f"[DEBUG] Estratégia 2 → raw='{resultado}' → {valor}")
            return valor
        return None
    except Exception as e:
        logger.debug(f"Estratégia 2 falhou: {e}")
        return None


# ------------------------------------------------------------------
# Estratégia 3 — varredura por data-attributes e aria-labels
# ------------------------------------------------------------------
def _por_varredura_js(page, debug: bool) -> Optional[str]:
    try:
        resultado = page.evaluate("""
            () => {
                const palavras = ['player', 'banker', 'tie'];
                const todos = Array.from(document.querySelectorAll('*'));

                for (const el of todos) {
                    // Verifica todos os atributos
                    for (const attr of el.attributes) {
                        const val = attr.value.toLowerCase();
                        for (const p of palavras) {
                            if (val === p) return p;
                        }
                    }
                }

                // Tenta pegar pelo innerHTML de containers de histórico
                const containers = document.querySelectorAll(
                    '[class*="histor"], [class*="result"], [class*="grid"], [class*="list"], [class*="table"]'
                );
                for (const c of containers) {
                    const html = c.innerHTML.toLowerCase();
                    // Procura padrões como class="...player..." no HTML interno
                    const matchP = html.match(/class="[^"]*player[^"]*"/);
                    const matchB = html.match(/class="[^"]*banker[^"]*"/);
                    const matchT = html.match(/class="[^"]*tie[^"]*"/);

                    // Qual aparece PRIMEIRO no HTML (= resultado mais recente)
                    const posP = matchP ? html.indexOf(matchP[0]) : Infinity;
                    const posB = matchB ? html.indexOf(matchB[0]) : Infinity;
                    const posT = matchT ? html.indexOf(matchT[0]) : Infinity;

                    const minPos = Math.min(posP, posB, posT);
                    if (minPos === Infinity) continue;

                    if (minPos === posP) return 'player';
                    if (minPos === posB) return 'banker';
                    if (minPos === posT) return 'tie';
                }

                return null;
            }
        """)

        if resultado:
            mapa = {"player": "vermelho", "banker": "azul", "tie": "branco"}
            valor = mapa.get(resultado)
            if debug:
                print(f"[DEBUG] Estratégia 3 → raw='{resultado}' → {valor}")
            return valor
        return None
    except Exception as e:
        logger.debug(f"Estratégia 3 falhou: {e}")
        return None


# ------------------------------------------------------------------
# Estratégia 4 — cor de background (red/blue/green computada pelo browser)
# ------------------------------------------------------------------
def _por_cor_background(page, debug: bool) -> Optional[str]:
    try:
        resultado = page.evaluate("""
            () => {
                const todos = Array.from(document.querySelectorAll('div, span, td'));

                for (const el of todos) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) continue;
                    // Célula pequena e quadrada (típico de resultado)
                    if (rect.width > 50 || rect.height > 50) continue;
                    if (Math.abs(rect.width - rect.height) > 15) continue;

                    const bg = window.getComputedStyle(el).backgroundColor;
                    // bg vem como "rgb(R, G, B)"
                    const match = bg.match(/rgb\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)/);
                    if (!match) continue;

                    const [, r, g, b] = match.map(Number);

                    // Vermelho dominante → Player
                    if (r > 150 && g < 100 && b < 100) return 'player';
                    // Azul dominante → Banker
                    if (b > 150 && r < 100 && g < 100) return 'banker';
                    // Verde dominante → Tie
                    if (g > 150 && r < 100 && b < 100) return 'tie';
                }

                return null;
            }
        """)

        if resultado:
            mapa = {"player": "vermelho", "banker": "azul", "tie": "branco"}
            valor = mapa.get(resultado)
            if debug:
                print(f"[DEBUG] Estratégia 4 (cor) → raw='{resultado}' → {valor}")
            return valor
        return None
    except Exception as e:
        logger.debug(f"Estratégia 4 falhou: {e}")
        return None


# ------------------------------------------------------------------
# Teste direto
# ------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print("Coletando resultado real do Bac Bo...")
    r = coletar_resultado_bacbo(debug=True)
    print(f"\n>>> Resultado: {r}")
