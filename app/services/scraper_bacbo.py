#!/usr/bin/env python3
"""
Bac Bo Live - TipMiner Scraper & Logger
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

logger = logging.getLogger("bacbo")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s",
    "%Y-%m-%d %H:%M:%S"
)

file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# ─────────────────────────────────────────────
#  Constantes
# ─────────────────────────────────────────────
URL = "https://www.tipminer.com/br/historico/blaze/bac-bo-ao-vivo"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

# ─────────────────────────────────────────────
#  Extração dos dados
# ─────────────────────────────────────────────

def fetch_page() -> str:
    resp = requests.get(URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def parse_rounds(soup: BeautifulSoup) -> list[dict]:
    rounds = []

    # MÉTODO 1 — direto do HTML
    elementos = soup.find_all(["div", "span"])

    for el in elementos:
        texto = el.get_text(strip=True)

        if texto.isdigit():
            valor = int(texto)

            if 2 <= valor <= 12:
                rounds.append({
                    "value": valor,
                    "time": None
                })

    # MÉTODO 2 — fallback
    if not rounds:
        textos = soup.get_text(" ", strip=True)
        numeros = re.findall(r"\b([2-9]|1[0-2])\b", textos)

        for n in numeros:
            rounds.append({
                "value": int(n),
                "time": None
            })

    return rounds


def build_payload(soup: BeautifulSoup) -> dict:
    rounds = parse_rounds(soup)

    return {
        "scraped_at": datetime.now().isoformat(),
        "date": str(date.today()),
        "source": URL,
        "rounds_count": len(rounds),
        "rounds": rounds[:50],
    }


def send_to_log(payload: dict) -> None:
    logger.info("=== BAC_BO_SNAPSHOT_START ===")
    logger.info("ROUNDS_CAPTURED: %d", payload["rounds_count"])

    if payload["rounds"]:
        values = [str(r["value"]) for r in payload["rounds"]]
        logger.info("ROUNDS: %s", " ".join(values))

    logger.info("JSON: %s", json.dumps(payload, ensure_ascii=False))
    logger.info("=== BAC_BO_SNAPSHOT_END ===")


def run_once() -> None:
    try:
        html = fetch_page()
        soup = BeautifulSoup(html, "lxml")
        payload = build_payload(soup)
        send_to_log(payload)
    except Exception as e:
        logger.error("Erro: %s", e)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", type=int, default=0)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    if args.output:
        logger.handlers.clear()

        file_handler = logging.FileHandler(args.output, encoding="utf-8")
        file_handler.setFormatter(formatter)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    if args.loop > 0:
        while True:
            run_once()
            time.sleep(args.loop)
    else:
        run_once()


# ============================================================
# 🔥 FUNÇÃO PRINCIPAL QUE O SISTEMA USA
# ============================================================

def coletar_resultado_bacbo(debug: bool = False):
    try:
        html = fetch_page()
        soup = BeautifulSoup(html, "lxml")

        rounds = parse_rounds(soup)

        if not rounds:
            if debug:
                print("❌ Nenhum resultado encontrado")
            return None

        # ✅ CORREÇÃO AQUI (ESSENCIAL)
        ultimo = rounds[0]["value"]

        if debug:
            print(f"Último valor: {ultimo}")

        if ultimo == 7:
            return "branco"
        elif ultimo <= 6:
            return "azul"
        else:
            return "vermelho"

    except Exception as e:
        if debug:
            print(f"Erro no scraper: {e}")
        return None


if __name__ == "__main__":
    main()
