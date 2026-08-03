#!/usr/bin/env python3
"""Bot de analise tecnica de compra/venda de criptomoedas.

Busca candles publicos da Binance, calcula indicadores tecnicos classicos
(medias moveis, RSI, MACD, Bandas de Bollinger) e gera um sinal de
COMPRAR / VENDER / AGUARDAR para cada ativo informado.

Isto e uma ferramenta de analise tecnica automatizada, NAO e recomendacao
financeira. Mercado de cripto e volatil; use por sua conta e risco e sempre
faca sua propria pesquisa (DYOR).

Exemplos:
    python bot.py BTCUSDT
    python bot.py BTCUSDT ETHUSDT SOLUSDT --interval 4h
    python bot.py BTCUSDT --interval 1h --watch --every 300
    python bot.py BTCUSDT --backtest --interval 1h --limit 500
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime

from data import fetch_ohlcv
from strategy import generate_signal, Signal
from backtest import run_backtest

ACTION_EMOJI = {"COMPRAR": "🟢", "VENDER": "🔴", "AGUARDAR": "🟡"}


def print_signal(signal: Signal) -> None:
    emoji = ACTION_EMOJI.get(signal.action, "")
    print(f"\n{emoji} {signal.symbol}  |  preco: {signal.price:.4f}  |  "
          f"score: {signal.score:+d}  |  sinal: {signal.action}")
    for reason in signal.reasons:
        print(f"   - {reason}")


def analyze(symbols: list[str], interval: str, limit: int) -> None:
    print(f"Analise tecnica ({interval}, {limit} candles) - {datetime.now().isoformat(timespec='seconds')}")
    for symbol in symbols:
        try:
            df = fetch_ohlcv(symbol, interval=interval, limit=limit)
            signal = generate_signal(symbol, df)
            print_signal(signal)
        except Exception as exc:  # noqa: BLE001 - reportar e seguir para o proximo simbolo
            print(f"\n[ERRO] {symbol}: {exc}")


def watch(symbols: list[str], interval: str, limit: int, every: int) -> None:
    print(f"Modo watch: analisando {symbols} a cada {every}s. Ctrl+C para parar.")
    try:
        while True:
            analyze(symbols, interval, limit)
            time.sleep(every)
    except KeyboardInterrupt:
        print("\nEncerrado pelo usuario.")


def backtest(symbols: list[str], interval: str, limit: int, capital: float) -> None:
    for symbol in symbols:
        try:
            df = fetch_ohlcv(symbol, interval=interval, limit=limit)
            result = run_backtest(df, initial_capital=capital)
        except Exception as exc:  # noqa: BLE001
            print(f"\n[ERRO] {symbol}: {exc}")
            continue

        print(f"\n=== Backtest {symbol} ({interval}, {result['num_candles']} candles) ===")
        print(f"Capital inicial:      {capital:.2f}")
        print(f"Estrategia final:     {result['final_equity']:.2f}  "
              f"({result['strategy_return_pct']:+.2f}%)")
        print(f"Buy & hold final:     {result['buy_hold_equity']:.2f}  "
              f"({result['buy_hold_return_pct']:+.2f}%)")
        print(f"Numero de trades:     {result['num_trades']}")
        for trade in result["trades"][-10:]:
            print(f"   {trade['time']}  {trade['action']:4s}  preco={trade['price']:.4f}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bot de analise de compra/venda de criptomoedas")
    parser.add_argument("symbols", nargs="+", help="Pares a analisar, ex: BTCUSDT ETHUSDT SOLUSDT")
    parser.add_argument("--interval", default="1h", help="Timeframe: 1m,5m,15m,1h,4h,1d... (default: 1h)")
    parser.add_argument("--limit", type=int, default=200, help="Numero de candles a buscar (default: 200)")
    parser.add_argument("--watch", action="store_true", help="Roda em loop continuo")
    parser.add_argument("--every", type=int, default=300, help="Intervalo em segundos no modo --watch (default: 300)")
    parser.add_argument("--backtest", action="store_true", help="Roda um backtest da estrategia em vez de analise ao vivo")
    parser.add_argument("--capital", type=float, default=1000.0, help="Capital inicial para o backtest (default: 1000)")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    symbols = [s.upper() for s in args.symbols]

    if args.backtest:
        backtest(symbols, args.interval, args.limit, args.capital)
    elif args.watch:
        watch(symbols, args.interval, args.limit, args.every)
    else:
        analyze(symbols, args.interval, args.limit)


if __name__ == "__main__":
    main()
