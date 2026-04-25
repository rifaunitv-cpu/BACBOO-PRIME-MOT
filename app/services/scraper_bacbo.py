# ============================================================
# scraper_bacbo.py
# Coleta o resultado mais recente do Bac Bo ao Vivo (TipMiner)
# Requer: pip install playwright
#         playwright install chromium
# ============================================================

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Mapeamento de classes/textos do site → valores do sistema
MAPA_RESULTADO = {
    # Classes de cor que o TipMiner usa para cada resultado
    "player":  "vermelho",   # Player  → vermelho
    "banker":  "azul",       # Banker  → azul
    "tie":     "branco",     # Tie     → branco
    # Fallbacks por texto visível
    "p":       "vermelho",
    "b":       "azul",
    "t":       "branco",
}

FALLBACK_PADRAO = "vermelho"
URL = "https://www.tipminer.com/br/historico/blaze/bac-bo-ao-vivo"
TIMEOUT_MS = 20_000   # 20 segundos


def coletar_resultado_bacbo(debug: bool = False) -> str:
    """
    Acessa o TipMiner via Playwright, aguarda os resultados do Bac Bo
    carregarem e retorna o resultado mais recente como string.

    Returns:
        "vermelho"  → Player venceu
        "azul"      → Banker venceu
        "branco"    → Tie (empate)
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        logger.error(
            "Playwright não instalado. "
            "Rode: pip install playwright && playwright install chromium"
        )
        return FALLBACK_PADRAO

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
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

            page.goto(URL, wait_until="domcontentloaded", timeout=TIMEOUT_MS)

            # Estratégia 1 — aguarda células com classe contendo "cell" e cor
            resultado = _estrategia_cell_classes(page, debug)
            if resultado:
                return resultado

            # Estratégia 2 — aguarda por texto P / B / T em spans/divs
            resultado = _estrategia_texto_pbt(page, debug)
            if resultado:
                return resultado

            # Estratégia 3 — varre todos os elementos visíveis buscando padrões
            resultado = _estrategia_varredura_geral(page, debug)
            if resultado:
                return resultado

            logger.warning("Nenhuma estratégia extraiu o resultado. Usando fallback.")
            return FALLBACK_PADRAO

        except PWTimeout:
            logger.error(f"Timeout ({TIMEOUT_MS}ms) ao carregar {URL}")
            return FALLBACK_PADRAO
        except Exception as e:
            logger.error(f"Erro inesperado no scraper: {e}", exc_info=True)
            return FALLBACK_PADRAO
        finally:
            context.close()
            browser.close()


# ------------------------------------------------------------------
# Estratégia 1 — Células com classe contendo "player" / "banker" / "tie"
# Padrão típico do TipMiner: div com classe bg-cell-player, bg-cell-banker, etc.
# ------------------------------------------------------------------
def _estrategia_cell_classes(page, debug: bool) -> Optional[str]:
    try:
        # Aguarda qualquer elemento com essas classes aparecer
        seletores = [
            "[class*='player']",
            "[class*='banker']",
            "[class*='tie']",
            "[class*='Player']",
            "[class*='Banker']",
            "[class*='Tie']",
        ]

        # Tenta aguardar pelo primeiro seletor que apareça
        achou = False
        for sel in seletores:
            try:
                page.wait_for_selector(sel, timeout=8_000)
                achou = True
                break
            except Exception:
                continue

        if not achou:
            return None

        # Pega o PRIMEIRO elemento de resultado (mais recente)
        # Testa cada variação de classe
        for palavra in ["player", "banker", "tie", "Player", "Banker", "Tie"]:
            elementos = page.query_selector_all(f"[class*='{palavra}']")
            # Filtra apenas elementos visíveis que parecem ser células de resultado
            for el in elementos:
                try:
                    if not el.is_visible():
                        continue
                    classe = el.get_attribute("class") or ""
                    # Ignora elementos de UI (botões, headers, labels)
                    tag = el.evaluate("e => e.tagName.toLowerCase()")
                    if tag in ("button", "a", "nav", "header", "footer", "label"):
                        continue
                    # Ignora se tem muito texto (provavelmente não é célula)
                    texto = (el.inner_text() or "").strip()
                    if len(texto) > 10:
                        continue

                    resultado = _classe_para_resultado(classe)
                    if resultado:
                        if debug:
                            print(f"[DEBUG] Estratégia 1 → classe='{classe}' → {resultado}")
                        return resultado
                except Exception:
                    continue

        return None

    except Exception as e:
        logger.debug(f"Estratégia 1 falhou: {e}")
        return None


# ------------------------------------------------------------------
# Estratégia 2 — Texto "P", "B", "T" dentro de células pequenas
# ------------------------------------------------------------------
def _estrategia_texto_pbt(page, debug: bool) -> Optional[str]:
    try:
        page.wait_for_selector("div, span", timeout=5_000)

        # Busca todos os elementos com texto curto
        elementos = page.query_selector_all("div, span, td, li")

        resultados_encontrados = []
        for el in elementos:
            try:
                if not el.is_visible():
                    continue
                texto = (el.inner_text() or "").strip().upper()
                if texto not in ("P", "B", "T", "PLAYER", "BANKER", "TIE"):
                    continue

                # Verifica tamanho do elemento (células são pequenas)
                box = el.bounding_box()
                if box and box["width"] > 80:
                    continue

                classe = el.get_attribute("class") or ""
                mapa = {
                    "P": "vermelho", "PLAYER": "vermelho",
                    "B": "azul",    "BANKER": "azul",
                    "T": "branco",  "TIE":    "branco",
                }
                resultado = mapa.get(texto)
                if resultado:
                    resultados_encontrados.append(resultado)
            except Exception:
                continue

        if resultados_encontrados:
            primeiro = resultados_encontrados[0]
            if debug:
                print(f"[DEBUG] Estratégia 2 → encontrou {len(resultados_encontrados)} células, primeiro={primeiro}")
            return primeiro

        return None

    except Exception as e:
        logger.debug(f"Estratégia 2 falhou: {e}")
        return None


# ------------------------------------------------------------------
# Estratégia 3 — Varredura geral por atributos data-* e aria-*
# ------------------------------------------------------------------
def _estrategia_varredura_geral(page, debug: bool) -> Optional[str]:
    try:
        # Tenta extrair via JavaScript — inspeciona todos os elementos
        resultado_js = page.evaluate("""
            () => {
                const keywords = ['player', 'banker', 'tie', 'Player', 'Banker', 'Tie'];
                const allEls = document.querySelectorAll('*');

                for (const el of allEls) {
                    const cls = el.className || '';
                    if (typeof cls !== 'string') continue;

                    // Verifica classe
                    for (const kw of keywords) {
                        if (cls.includes(kw)) {
                            // Ignora elementos não visuais de resultado
                            const tag = el.tagName.toLowerCase();
                            if (['button','a','nav','header','footer','script','style'].includes(tag)) continue;

                            const rect = el.getBoundingClientRect();
                            if (rect.width === 0 || rect.height === 0) continue;
                            if (rect.width > 100 || rect.height > 100) continue;

                            return kw.toLowerCase();
                        }
                    }

                    // Verifica data-attributes
                    for (const attr of el.attributes) {
                        const val = attr.value.toLowerCase();
                        if (val === 'player' || val.includes('player')) return 'player';
                        if (val === 'banker' || val.includes('banker')) return 'banker';
                        if (val === 'tie'    || val.includes('tie'))    return 'tie';
                    }
                }
                return null;
            }
        """)

        if resultado_js:
            resultado = MAPA_RESULTADO.get(resultado_js.lower())
            if resultado:
                if debug:
                    print(f"[DEBUG] Estratégia 3 (JS) → raw='{resultado_js}' → {resultado}")
                return resultado

        return None

    except Exception as e:
        logger.debug(f"Estratégia 3 falhou: {e}")
        return None


# ------------------------------------------------------------------
# Helper — converte string de classe CSS para resultado
# ------------------------------------------------------------------
def _classe_para_resultado(classe: str) -> Optional[str]:
    """
    Analisa a string de classes CSS e retorna o resultado correspondente.
    Ex: "bg-cell-player rounded-md" → "vermelho"
    """
    classe_lower = classe.lower()

    if "player" in classe_lower:
        return "vermelho"
    if "banker" in classe_lower:
        return "azul"
    if "tie" in classe_lower:
        return "branco"

    # Fallback por cores explícitas que o TipMiner pode usar
    # (red/blue/green costumam ser usados em vez de player/banker/tie)
    padroes_cor = {
        r"\bred\b":   "vermelho",
        r"\bblue\b":  "azul",
        r"\bgreen\b": "branco",   # TipMiner usa verde para tie às vezes
        r"text-red":  "vermelho",
        r"text-blue": "azul",
        r"bg-red":    "vermelho",
        r"bg-blue":   "azul",
    }
    for padrao, valor in padroes_cor.items():
        if re.search(padrao, classe_lower):
            return valor

    return None


# ------------------------------------------------------------------
# Execução direta para teste
# ------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print("Coletando resultado do Bac Bo ao Vivo...")
    resultado = coletar_resultado_bacbo(debug=True)
    print(f"\nResultado: {resultado}")
