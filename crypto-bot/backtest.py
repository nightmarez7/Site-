"""Backtest simples da estrategia definida em strategy.py sobre dados historicos.

Simula uma carteira long-only: entra 100% comprado quando o sinal vira COMPRAR,
zera a posicao quando o sinal vira VENDER, e compara o resultado com buy & hold.

Como os indicadores (SMA/EMA/RSI/MACD/Bollinger) usam apenas janelas retroativas
(rolling/ewm do pandas), calcular tudo de uma vez sobre o DataFrame nao introduz
look-ahead bias: o valor de cada linha depende somente de candles anteriores.
"""

from __future__ import annotations

from indicators import add_all_indicators
from strategy import (
    BUY_THRESHOLD,
    SELL_THRESHOLD,
    _bollinger_score,
    _macd_score,
    _rsi_score,
    _trend_score,
)


def _score_row(row) -> int:
    reasons: list[str] = []
    return (
        _trend_score(row, reasons)
        + _macd_score(row, reasons)
        + _rsi_score(row, reasons)
        + _bollinger_score(row, reasons)
    )


def run_backtest(df, initial_capital: float = 1000.0) -> dict:
    enriched = add_all_indicators(df).dropna().reset_index(drop=True)
    if enriched.empty:
        raise ValueError("Dados insuficientes para rodar o backtest")

    cash = initial_capital
    coins = 0.0
    position = 0  # 0 = fora do mercado, 1 = comprado
    trades: list[dict] = []
    equity_curve: list[float] = []

    for _, row in enriched.iterrows():
        score = _score_row(row)
        price = row["close"]

        if score >= BUY_THRESHOLD and position == 0:
            coins = cash / price
            cash = 0.0
            position = 1
            trades.append({"time": row["open_time"], "action": "BUY", "price": price})
        elif score <= SELL_THRESHOLD and position == 1:
            cash = coins * price
            coins = 0.0
            position = 0
            trades.append({"time": row["open_time"], "action": "SELL", "price": price})

        equity_curve.append(cash + coins * price)

    last_price = float(enriched.iloc[-1]["close"])
    first_price = float(enriched.iloc[0]["close"])
    final_equity = cash + coins * last_price
    buy_hold_equity = (initial_capital / first_price) * last_price

    return {
        "num_candles": len(enriched),
        "num_trades": len(trades),
        "trades": trades,
        "initial_capital": initial_capital,
        "final_equity": final_equity,
        "strategy_return_pct": (final_equity / initial_capital - 1) * 100,
        "buy_hold_equity": buy_hold_equity,
        "buy_hold_return_pct": (buy_hold_equity / initial_capital - 1) * 100,
        "equity_curve": equity_curve,
    }
