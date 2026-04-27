#!/usr/bin/env python3
"""
Bac Bo Live - TipMiner Scraper & Logger (VERSÃO API ESTÁVEL)
"""

import requests
import json
import logging
import argparse
import time
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
#  Configuração API
# ─────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

GAME_ID = "0194b476-0e88-740c-a957-87be3bc3aa55"


# ─────────────────────────────────────────────
#  Função API (NOVA)
# ─────────────────────────────────────────────

def fetch_api() -> dict:
    hoje = datetime.now().strftime("%Y-%m-%d")

    url = f"https://www.tipminer.com/api/v3/types-per-hour/bac_bo/{GAME_ID}/{hoje}?timezone=America/Sao_Paulo"

    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()

    return resp.json()


def parse_rounds_api(data: dict) -> list[dict]:
    rounds = []

    resultados = data.get("data", [])

    for r in resultados:
        valor = r.get("value")

        if valor is not None:
            rounds.append({
                "value": int(valor),
                "time": r.get("time")
            })

    return rounds


def build_payload(data: dict) -> dict:
    rounds = parse_rounds_api(data)

    return {
        "scraped_at": datetime.now().isoformat(),
        "date": str(date.today()),
        "source": "tipminer_api",
        "rounds_count": len(rounds),
        "rounds": rounds[-50:],  # últimos 50
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
        data = fetch_api()
        payload = build_payload(data)
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
# 🔥 FUNÇÃO PRINCIPAL QUE O SISTEMA USA (100% CORRIGIDA)
# ============================================================

def coletar_resultado_bacbo(debug: bool = False):
    try:
        data = fetch_api()

        resultados = data.get("data", [])

        if not resultados:
            if debug:
                print("❌ Nenhum resultado na API")
            return None

        # 🟢 MAIS RECENTE
        ultimo = resultados[-1]

        valor = ultimo.get("value")

        if valor is None:
            return None

        if debug:
            print(f"Valor bruto: {valor}")

        # 🎯 REGRA
        if valor == 7:
            return "branco"
        elif valor <= 6:
            return "azul"
        else:
            return "vermelho"

    except Exception as e:
        if debug:
            print(f"Erro no scraper: {e}")
        return None


if __name__ == "__main__":
    main()
