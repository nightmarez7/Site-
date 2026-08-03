#!/usr/bin/env python3
"""Bot de analise tecnica de compra/venda de criptomoedas.

Busca candles publicos da Binance, calcula indicadores tecnicos classicos
(medias moveis, RSI, MACD, Bandas de Bollinger, ATR) e gera um sinal de
COMPRAR / VENDER / AGUARDAR para cada ativo informado, com stop-loss,
take-profit e tamanho de posicao sugeridos (gestao de risco por ATR).
Opcionalmente envia os sinais como alerta no Telegram.

Isto e uma ferramenta de analise tecnica automatizada, NAO e recomendacao
financeira. Mercado de cripto e volatil; use por sua conta e risco e sempre
faca sua propria pesquisa (DYOR).

Exemplos:
    python bot.py BTCUSDT
    python bot.py BTCUSDT ETHUSDT SOLUSDT --interval 4h
    python bot.py BTCUSDT --capital 1000 --risk-pct 1 --rr 2
    python bot.py BTCUSDT --interval 1h --watch --every 300 --telegram
    python bot.py BTCUSDT --backtest --interval 1h --limit 500 --capital 1000
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime

from data import fetch_ohlcv
from strategy import generate_signal, Signal
from backtest import run_backtest
from telegram_alerts import send_signal_alert

ACTION_EMOJI = {"COMPRAR": "🟢", "VENDER": "🔴", "AGUARDAR": "🟡"}


def print_signal(signal: Signal) -> None:
    emoji = ACTION_EMOJI.get(signal.action, "")
    print(f"\n{emoji} {signal.symbol}  |  preco: {signal.price:.4f}  |  "
          f"score: {signal.score:+d}  |  sinal: {signal.action}")
    for reason in signal.reasons:
        print(f"   - {reason}")

    if signal.risk_plan:
        plan = signal.risk_plan
        print(f"   plano de risco: stop={plan.stop_loss:.4f}  "
              f"alvo={plan.take_profit:.4f}  "
              f"tamanho={plan.position_size:.6f} ({plan.position_value:.2f})  "
              f"capital arriscado={plan.risk_amount:.2f}")


def analyze(
    symbols: list[str],
    interval: str,
    limit: int,
    capital: float | None,
    risk_pct: float,
    atr_mult: float,
    rr: float,
    telegram: bool,
    telegram_token: str | None,
    telegram_chat_id: str | None,
) -> None:
    print(f"Analise tecnica ({interval}, {limit} candles) - {datetime.now().isoformat(timespec='seconds')}")
    for symbol in symbols:
        try:
            df = fetch_ohlcv(symbol, interval=interval, limit=limit)
            signal = generate_signal(
                symbol, df,
                capital=capital, risk_pct=risk_pct,
                atr_mult_stop=atr_mult, reward_risk_ratio=rr,
            )
            print_signal(signal)

            if telegram and signal.action in ("COMPRAR", "VENDER"):
                try:
                    send_signal_alert(signal, token=telegram_token, chat_id=telegram_chat_id)
                except Exception as exc:  # noqa: BLE001 - alerta nao deve derrubar a analise
                    print(f"   [AVISO] falha ao enviar alerta Telegram: {exc}")
        except Exception as exc:  # noqa: BLE001 - reportar e seguir para o proximo simbolo
            print(f"\n[ERRO] {symbol}: {exc}")


def watch(symbols: list[str], interval: str, limit: int, every: int, **analyze_kwargs) -> None:
    print(f"Modo watch: analisando {symbols} a cada {every}s. Ctrl+C para parar.")
    try:
        while True:
            analyze(symbols, interval, limit, **analyze_kwargs)
            time.sleep(every)
    except KeyboardInterrupt:
        print("\nEncerrado pelo usuario.")


def backtest(symbols: list[str], interval: str, limit: int, capital: float, risk_pct: float, atr_mult: float, rr: float) -> None:
    for symbol in symbols:
        try:
            df = fetch_ohlcv(symbol, interval=interval, limit=limit)
            result = run_backtest(
                df, initial_capital=capital,
                risk_pct=risk_pct, atr_mult_stop=atr_mult, reward_risk_ratio=rr,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"\n[ERRO] {symbol}: {exc}")
            continue

        print(f"\n=== Backtest {symbol} ({interval}, {result['num_candles']} candles) ===")
        print(f"Risco por trade: {risk_pct}%  |  stop: {atr_mult}x ATR  |  risco:retorno 1:{rr}")
        print(f"Capital inicial:      {capital:.2f}")
        print(f"Estrategia final:     {result['final_equity']:.2f}  "
              f"({result['strategy_return_pct']:+.2f}%)")
        print(f"Buy & hold final:     {result['buy_hold_equity']:.2f}  "
              f"({result['buy_hold_return_pct']:+.2f}%)")
        print(f"Numero de trades:     {result['num_trades']}")
        for trade in result["trades"][-10:]:
            print(f"   {trade['time']}  {trade['action']:20s}  preco={trade['price']:.4f}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bot de analise de compra/venda de criptomoedas")
    parser.add_argument("symbols", nargs="+", help="Pares a analisar, ex: BTCUSDT ETHUSDT SOLUSDT")
    parser.add_argument("--interval", default="1h", help="Timeframe: 1m,5m,15m,1h,4h,1d... (default: 1h)")
    parser.add_argument("--limit", type=int, default=200, help="Numero de candles a buscar (default: 200)")
    parser.add_argument("--watch", action="store_true", help="Roda em loop continuo")
    parser.add_argument("--every", type=int, default=300, help="Intervalo em segundos no modo --watch (default: 300)")
    parser.add_argument("--backtest", action="store_true", help="Roda um backtest da estrategia em vez de analise ao vivo")

    parser.add_argument("--capital", type=float, default=1000.0,
                         help="Capital disponivel, usado no backtest e para dimensionar posicao na analise ao vivo (default: 1000)")
    parser.add_argument("--risk-pct", type=float, default=1.0,
                         help="%% do capital arriscado por trade (default: 1.0)")
    parser.add_argument("--atr-mult", type=float, default=1.5,
                         help="Distancia do stop-loss em multiplos do ATR (default: 1.5)")
    parser.add_argument("--rr", type=float, default=2.0,
                         help="Relacao risco:retorno do take-profit (default: 2.0, ou seja 1:2)")

    parser.add_argument("--telegram", action="store_true",
                         help="Envia sinais de COMPRAR/VENDER como alerta no Telegram")
    parser.add_argument("--telegram-token", default=None,
                         help="Token do bot (ou defina a env var TELEGRAM_BOT_TOKEN)")
    parser.add_argument("--telegram-chat-id", default=None,
                         help="Chat ID de destino (ou defina a env var TELEGRAM_CHAT_ID)")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    symbols = [s.upper() for s in args.symbols]

    if args.backtest:
        backtest(symbols, args.interval, args.limit, args.capital, args.risk_pct, args.atr_mult, args.rr)
        return

    analyze_kwargs = dict(
        capital=args.capital,
        risk_pct=args.risk_pct,
        atr_mult=args.atr_mult,
        rr=args.rr,
        telegram=args.telegram,
        telegram_token=args.telegram_token,
        telegram_chat_id=args.telegram_chat_id,
    )

    if args.watch:
        watch(symbols, args.interval, args.limit, args.every, **analyze_kwargs)
    else:
        analyze(symbols, args.interval, args.limit, **analyze_kwargs)


if __name__ == "__main__":
    main()
