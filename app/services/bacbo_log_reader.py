#!/usr/bin/env python3
"""
Bac Bo Log Reader
Lê o arquivo de log gerado pelo bacbo_scraper.py e exibe relatório.

Uso:
    python bacbo_log_reader.py                        # lê bacbo_data.log
    python bacbo_log_reader.py --file meu.log         # log customizado
    python bacbo_log_reader.py --tail                 # monitora em tempo real
"""

import json
import re
import argparse
import time
import sys
from collections import Counter
from datetime import datetime


def parse_log(filepath: str) -> list[dict]:
    """Extrai todos os JSON_PAYLOAD do arquivo de log."""
    snapshots = []
    try:
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                if "JSON_PAYLOAD:" in line:
                    _, _, raw = line.partition("JSON_PAYLOAD: ")
                    try:
                        snapshots.append(json.loads(raw.strip()))
                    except json.JSONDecodeError:
                        pass
    except FileNotFoundError:
        print(f"[ERRO] Arquivo não encontrado: {filepath}")
        sys.exit(1)
    return snapshots


def display_report(snapshots: list[dict]) -> None:
    if not snapshots:
        print("Nenhum snapshot encontrado no log.")
        return

    latest = snapshots[-1]
    print("\n" + "═" * 60)
    print("   BAC BO – RELATÓRIO DO LOG")
    print("═" * 60)
    print(f"  Total de snapshots no log : {len(snapshots)}")
    print(f"  Último snapshot           : {latest.get('scraped_at', '?')}")
    print(f"  Data de referência        : {latest.get('date', '?')}")
    print(f"  Rodadas capturadas        : {latest.get('rounds_count', 0)}")

    # ── Estatísticas de cores ──────────────────────────────
    cs = latest.get("color_stats", {})
    if cs:
        print("\n  ┌─ CONTAGEM DE CORES ─────────────────────────────┐")
        for k, v in cs.items():
            bar_len = int(v.get("pct", 0) / 2)
            bar = "█" * bar_len
            print(f"  │  {k.upper():<8} {v.get('count'):>4}x  {v.get('pct'):>5.1f}%  {bar}")
        print("  └──────────────────────────────────────────────────┘")

    # ── Máximas de sequência ───────────────────────────────
    st = latest.get("max_streaks", {})
    if st:
        print("\n  ┌─ MÁXIMAS DE SEQUÊNCIA ──────────────────────────┐")
        for k, v in st.items():
            print(f"  │  {k.upper():<8} {v} seguidos")
        print("  └──────────────────────────────────────────────────┘")

    # ── Breakdown por hora ─────────────────────────────────
    hourly = latest.get("hourly_breakdown", [])
    if hourly:
        print("\n  ┌─ CORES POR HORA ────────────────────────────────┐")
        print(f"  │  {'HORA':<6}  {'EMP':>4}  {'JOG':>4}  {'BAN':>4}  DOMINANTE")
        print("  │  " + "─" * 44)
        for h in hourly:
            dom = max(
                [("JOGADOR", h["jogador"]), ("BANCA", h["banca"]), ("EMPATE", h["empate"])],
                key=lambda x: x[1]
            )[0]
            print(f"  │  {h['hour']:<6}  {h['empate']:>4}  {h['jogador']:>4}  {h['banca']:>4}  {dom}")
        print("  └──────────────────────────────────────────────────┘")

    # ── Últimas rodadas ────────────────────────────────────
    rounds = latest.get("rounds", [])
    if rounds:
        vals = [r["value"] for r in rounds]
        freq = Counter(vals)
        print("\n  ┌─ FREQUÊNCIA DOS VALORES (últimas rodadas) ───────┐")
        for num in sorted(freq.keys()):
            bar = "▪" * freq[num]
            print(f"  │  [{num:>2}]  {freq[num]:>3}x  {bar}")
        print("  └──────────────────────────────────────────────────┘")

        # Últimos 20 valores
        recentes = " → ".join(str(v) for v in vals[-20:])
        print(f"\n  Últimos 20 resultados:\n  {recentes}")

    print("\n" + "═" * 60 + "\n")


def tail_mode(filepath: str, interval: int = 10) -> None:
    """Monitora o log em tempo real, atualizando a cada N segundos."""
    print(f"Monitorando {filepath} (atualiza a cada {interval}s)... Ctrl+C para parar.")
    last_count = 0
    while True:
        snapshots = parse_log(filepath)
        if len(snapshots) != last_count:
            last_count = len(snapshots)
            display_report(snapshots)
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bac Bo Log Reader")
    parser.add_argument("--file", default="bacbo_data.log", help="Arquivo de log")
    parser.add_argument("--tail", action="store_true", help="Modo tempo real")
    parser.add_argument("--interval", type=int, default=10, help="Intervalo do tail (s)")
    args = parser.parse_args()

    if args.tail:
        tail_mode(args.file, args.interval)
    else:
        snapshots = parse_log(args.file)
        display_report(snapshots)


if __name__ == "__main__":
    main()
