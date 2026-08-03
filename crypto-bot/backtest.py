"""Backtest da estrategia definida em strategy.py sobre dados historicos,
incluindo gestao de risco (stop-loss/take-profit por ATR e position sizing).

Simula uma carteira long-only: entra na posicao dimensionada por
`risk.build_risk_plan` quando o sinal vira COMPRAR, e sai quando o
stop-loss, o take-profit ou um sinal de VENDER e atingido primeiro.
Compara o resultado final com buy & hold (alocar tudo no ativo desde o
primeiro candle).

Como os indicadores (SMA/EMA/RSI/MACD/Bollinger/ATR) usam apenas janelas
retroativas (rolling/ewm do pandas), calcular tudo de uma vez sobre o
DataFrame nao introduz look-ahead bias: o valor de cada linha depende
somente de candles anteriores.
"""

from __future__ import annotations

from indicators import add_all_indicators
from risk import build_risk_plan
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


def run_backtest(
    df,
    initial_capital: float = 1000.0,
    risk_pct: float = 1.0,
    atr_mult_stop: float = 1.5,
    reward_risk_ratio: float = 2.0,
) -> dict:
    enriched = add_all_indicators(df).dropna().reset_index(drop=True)
    if enriched.empty:
        raise ValueError("Dados insuficientes para rodar o backtest")

    cash = initial_capital
    coins = 0.0
    position = 0  # 0 = fora do mercado, 1 = comprado
    stop_loss = None
    take_profit = None
    trades: list[dict] = []
    equity_curve: list[float] = []

    for _, row in enriched.iterrows():
        price = float(row["close"])

        if position == 1:
            exit_price = None
            exit_reason = None
            if row["low"] <= stop_loss:
                exit_price, exit_reason = stop_loss, "SELL (stop-loss)"
            elif row["high"] >= take_profit:
                exit_price, exit_reason = take_profit, "SELL (take-profit)"
            elif _score_row(row) <= SELL_THRESHOLD:
                exit_price, exit_reason = price, "SELL (sinal)"

            if exit_price is not None:
                cash += coins * exit_price
                coins = 0.0
                position = 0
                stop_loss = take_profit = None
                trades.append({"time": row["open_time"], "action": exit_reason, "price": exit_price})

        if position == 0 and _score_row(row) >= BUY_THRESHOLD and row["atr"] > 0:
            plan = build_risk_plan(
                capital=cash,
                entry_price=price,
                atr=float(row["atr"]),
                risk_pct=risk_pct,
                atr_mult_stop=atr_mult_stop,
                reward_risk_ratio=reward_risk_ratio,
            )
            coins = plan.position_size
            cash -= plan.position_value
            position = 1
            stop_loss = plan.stop_loss
            take_profit = plan.take_profit
            trades.append({
                "time": row["open_time"],
                "action": "BUY",
                "price": price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
            })

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
