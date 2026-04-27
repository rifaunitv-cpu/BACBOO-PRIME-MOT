#!/usr/bin/env python3
"""
Bac Bo Live - TipMiner Scraper & Logger
Extrai dados de https://www.tipminer.com/br/historico/blaze/bac-bo-ao-vivo
e envia para arquivo de log estruturado.

Uso:
    pip install requests beautifulsoup4 lxml
    python bacbo_scraper.py                    # roda uma vez
    python bacbo_scraper.py --loop 60          # roda a cada 60 segundos
    python bacbo_scraper.py --output meu.log   # log personalizado
"""

import requests
from bs4 import BeautifulSoup
import json
import logging
import argparse
import time
import re
from datetime import datetime, date

# ─────────────────────────────────────────────
#  Configuração de logging
# ─────────────────────────────────────────────
LOG_FILE = "bacbo_data.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("bacbo")

# ─────────────────────────────────────────────
#  Constantes
# ─────────────────────────────────────────────
URL = "https://www.tipminer.com/br/historico/blaze/bac-bo-ao-vivo"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}


# ─────────────────────────────────────────────
#  Extração dos dados
# ─────────────────────────────────────────────

def fetch_page() -> str:
    """Baixa o HTML da página."""
    resp = requests.get(URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def parse_rounds(soup: BeautifulSoup) -> list[dict]:
    """
    Extrai as rodadas visíveis na timeline inferior (valor + horário).
    Cada item tem: value (int), time (str).
    """
    rounds = []

    # Timeline: divs com valor + horário
    # O site renderiza cada rodada como dois elementos próximos:
    # um com o número e outro com o horário (HH:MM)
    # Tentamos múltiplos seletores para robustez.

    # Seletor 1: lista de resultados na coluna lateral
    items = soup.select("div[class*='result'], span[class*='result']")

    # Seletor 2: tabela principal (grid de números)
    if not items:
        items = soup.find_all(string=re.compile(r"^\d{1,2}$"))

    # Fallback: pega todos os textos numéricos de 2 a 12 (faixa válida do Bac Bo)
    time_pattern = re.compile(r"^\d{2}:\d{2}$")
    value_pattern = re.compile(r"^\d{1,2}$")

    # Estratégia mais robusta: varrer todos os elementos de texto
    all_texts = [t.strip() for t in soup.stripped_strings]

    i = 0
    while i < len(all_texts):
        val = all_texts[i]
        if value_pattern.match(val) and 2 <= int(val) <= 12:
            # Verifica se o próximo token é um horário
            hora = None
            if i + 1 < len(all_texts) and time_pattern.match(all_texts[i + 1]):
                hora = all_texts[i + 1]
                i += 2
            else:
                i += 1

            rounds.append({
                "value": int(val),
                "time": hora,
            })
        else:
            i += 1

    return rounds


def parse_color_stats(soup: BeautifulSoup) -> dict:
    """
    Extrai contagem de Banca / Empate / Jogador e percentuais.
    """
    stats = {}
    text = soup.get_text(" ", strip=True)

    patterns = {
        "banca":   r"(\d+)\s*[•·]\s*([\d.]+)%\s*[•·]\s*Banca",
        "empate":  r"(\d+)\s*[•·]\s*([\d.]+)%\s*[•·]\s*Empate",
        "jogador": r"(\d+)\s*[•·]\s*([\d.]+)%\s*[•·]\s*Jogador",
    }

    for key, pat in patterns.items():
        m = re.search(pat, text)
        if m:
            stats[key] = {"count": int(m.group(1)), "pct": float(m.group(2))}

    return stats


def parse_hourly(soup: BeautifulSoup) -> list[dict]:
    """
    Extrai tabela 'Cores por hora': hora, empate, jogador, banca.
    """
    hourly = []
    text = soup.get_text(" ", strip=True)

    # Padrão: "HH:00  <empate>  <jogador>  <banca>"
    pat = re.compile(r"(\d{2}):00\s+(\d+)\s+(\d+)\s+(\d+)")
    for m in pat.finditer(text):
        h, emp, jog, ban = m.groups()
        e, j, b = int(emp), int(jog), int(ban)
        if e + j + b == 0:
            continue  # hora vazia
        hourly.append({
            "hour": f"{h}:00",
            "empate": e,
            "jogador": j,
            "banca": b,
        })

    return hourly


def parse_streaks(soup: BeautifulSoup) -> dict:
    """
    Extrai máximas de sequências (banca/empate/jogador seguidos).
    """
    streaks = {}
    text = soup.get_text(" ", strip=True)

    for key in ("banca", "empate", "jogador"):
        m = re.search(rf"(\d+)\s+{key}\s+seguidos", text, re.IGNORECASE)
        if m:
            streaks[key] = int(m.group(1))

    return streaks


# ─────────────────────────────────────────────
#  Montagem do payload e envio para log
# ─────────────────────────────────────────────

def build_payload(soup: BeautifulSoup) -> dict:
    rounds  = parse_rounds(soup)
    colors  = parse_color_stats(soup)
    hourly  = parse_hourly(soup)
    streaks = parse_streaks(soup)

    return {
        "scraped_at": datetime.now().isoformat(),
        "date": str(date.today()),
        "source": URL,
        "rounds_count": len(rounds),
        "rounds": rounds[:50],           # primeiras 50 para não inflar o log
        "color_stats": colors,
        "hourly_breakdown": hourly,
        "max_streaks": streaks,
    }


def send_to_log(payload: dict) -> None:
    """Serializa o payload como JSON e grava no logger."""
    logger.info("=== BAC_BO_SNAPSHOT_START ===")
    logger.info("SOURCE: %s", payload["source"])
    logger.info("SCRAPED_AT: %s", payload["scraped_at"])
    logger.info("ROUNDS_CAPTURED: %d", payload["rounds_count"])

    if payload["color_stats"]:
        cs = payload["color_stats"]
        for k, v in cs.items():
            logger.info("COLOR | %s: count=%s  pct=%s%%", k.upper(), v.get("count"), v.get("pct"))

    if payload["max_streaks"]:
        for k, v in payload["max_streaks"].items():
            logger.info("STREAK_MAX | %s: %d seguidos", k.upper(), v)

    if payload["hourly_breakdown"]:
        for h in payload["hourly_breakdown"]:
            logger.info(
                "HOURLY | %s  empate=%d  jogador=%d  banca=%d",
                h["hour"], h["empate"], h["jogador"], h["banca"],
            )

    if payload["rounds"]:
        values = [str(r["value"]) for r in payload["rounds"]]
        logger.info("ROUNDS (last 50): %s", " ".join(values))

    # Grava JSON completo numa linha para fácil parse posterior
    logger.info("JSON_PAYLOAD: %s", json.dumps(payload, ensure_ascii=False))
    logger.info("=== BAC_BO_SNAPSHOT_END ===")


# ─────────────────────────────────────────────
#  Ponto de entrada
# ─────────────────────────────────────────────

def run_once() -> None:
    logger.info("Iniciando coleta do TipMiner Bac Bo...")
    try:
        html = fetch_page()
        soup = BeautifulSoup(html, "lxml")
        payload = build_payload(soup)
        send_to_log(payload)
        logger.info("Coleta concluída. Rodadas capturadas: %d", payload["rounds_count"])
    except requests.RequestException as e:
        logger.error("Erro de rede: %s", e)
    except Exception as e:
        logger.exception("Erro inesperado: %s", e)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bac Bo TipMiner Scraper")
    parser.add_argument(
        "--loop", type=int, default=0, metavar="SEGUNDOS",
        help="Se > 0, repete a coleta a cada N segundos (ex: --loop 60)"
    )
    parser.add_argument(
        "--output", type=str, default=LOG_FILE,
        help="Arquivo de log de saída (padrão: bacbo_data.log)"
    )
    args = parser.parse_args()

    # Reaplica log file se customizado
    global LOG_FILE
    LOG_FILE = args.output
    for h in logger.handlers:
        if isinstance(h, logging.FileHandler):
            h.baseFilename = args.output

    if args.loop > 0:
        logger.info("Modo loop: coletando a cada %d segundos. Ctrl+C para parar.", args.loop)
        while True:
            run_once()
            logger.info("Aguardando %ds para próxima coleta...", args.loop)
            time.sleep(args.loop)
    else:
        run_once()


if __name__ == "__main__":
    main()
