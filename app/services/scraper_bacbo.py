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
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    ),
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

    time_pattern = re.compile(r"^\d{2}:\d{2}$")
    value_pattern = re.compile(r"^\d{1,2}$")

    all_texts = [t.strip() for t in soup.stripped_strings]

    i = 0
    while i < len(all_texts):
        val = all_texts[i]

        if value_pattern.match(val) and 2 <= int(val) <= 12:
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
    hourly = []
    text = soup.get_text(" ", strip=True)

    pat = re.compile(r"(\d{2}):00\s+(\d+)\s+(\d+)\s+(\d+)")
    for m in pat.finditer(text):
        h, emp, jog, ban = m.groups()
        e, j, b = int(emp), int(jog), int(ban)

        if e + j + b == 0:
            continue

        hourly.append({
            "hour": f"{h}:00",
            "empate": e,
            "jogador": j,
            "banca": b,
        })

    return hourly


def parse_streaks(soup: BeautifulSoup) -> dict:
    streaks = {}
    text = soup.get_text(" ", strip=True)

    for key in ("banca", "empate", "jogador"):
        m = re.search(rf"(\d+)\s+{key}\s+seguidos", text, re.IGNORECASE)
        if m:
            streaks[key] = int(m.group(1))

    return streaks


def build_payload(soup: BeautifulSoup) -> dict:
    return {
        "scraped_at": datetime.now().isoformat(),
        "date": str(date.today()),
        "source": URL,
        "rounds_count": len(parse_rounds(soup)),
        "rounds": parse_rounds(soup)[:50],
        "color_stats": parse_color_stats(soup),
        "hourly_breakdown": parse_hourly(soup),
        "max_streaks": parse_streaks(soup),
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

    # ✅ CORREÇÃO AQUI (SEM GLOBAL)
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


if __name__ == "__main__":
    main()
