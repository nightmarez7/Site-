"""Logica de geracao de sinal (COMPRAR / VENDER / AGUARDAR).

Combina 4 indicadores classicos de analise tecnica em um score de -4 a +4.
Isso NAO e recomendacao financeira, e apenas analise tecnica automatizada.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from indicators import add_all_indicators

BUY_THRESHOLD = 2
SELL_THRESHOLD = -2


@dataclass
class Signal:
    symbol: str
    price: float
    score: int
    action: str  # "COMPRAR" | "VENDER" | "AGUARDAR"
    reasons: list[str] = field(default_factory=list)
    indicators: dict = field(default_factory=dict)


def _trend_score(row, reasons: list[str]) -> int:
    if row["sma_fast"] > row["sma_slow"]:
        reasons.append("Tendencia de alta: media rapida (9) acima da media lenta (21)")
        return 1
    reasons.append("Tendencia de baixa: media rapida (9) abaixo da media lenta (21)")
    return -1


def _macd_score(row, reasons: list[str]) -> int:
    if row["macd"] > row["macd_signal"]:
        reasons.append("MACD acima da linha de sinal (momentum positivo)")
        return 1
    reasons.append("MACD abaixo da linha de sinal (momentum negativo)")
    return -1


def _rsi_score(row, reasons: list[str]) -> int:
    rsi_value = row["rsi"]
    if rsi_value < 30:
        reasons.append(f"RSI em sobrevenda ({rsi_value:.1f} < 30)")
        return 1
    if rsi_value > 70:
        reasons.append(f"RSI em sobrecompra ({rsi_value:.1f} > 70)")
        return -1
    reasons.append(f"RSI neutro ({rsi_value:.1f})")
    return 0


def _bollinger_score(row, reasons: list[str]) -> int:
    price = row["close"]
    if price <= row["bb_lower"]:
        reasons.append("Preco na banda inferior de Bollinger ou abaixo (possivel oversold)")
        return 1
    if price >= row["bb_upper"]:
        reasons.append("Preco na banda superior de Bollinger ou acima (possivel overbought)")
        return -1
    return 0


def generate_signal(symbol: str, df: pd.DataFrame) -> Signal:
    """Recebe OHLCV (coluna 'close' obrigatoria) e devolve um Signal com o sinal atual."""
    enriched = add_all_indicators(df)
    row = enriched.iloc[-1]

    if row[["sma_slow", "macd_signal", "rsi", "bb_lower"]].isna().any():
        raise ValueError(
            "Dados insuficientes para calcular todos os indicadores "
            "(peca mais candles, ex: limit>=60)"
        )

    reasons: list[str] = []
    score = (
        _trend_score(row, reasons)
        + _macd_score(row, reasons)
        + _rsi_score(row, reasons)
        + _bollinger_score(row, reasons)
    )

    if score >= BUY_THRESHOLD:
        action = "COMPRAR"
    elif score <= SELL_THRESHOLD:
        action = "VENDER"
    else:
        action = "AGUARDAR"

    return Signal(
        symbol=symbol.upper(),
        price=float(row["close"]),
        score=score,
        action=action,
        reasons=reasons,
        indicators={
            "sma_fast": round(float(row["sma_fast"]), 4),
            "sma_slow": round(float(row["sma_slow"]), 4),
            "rsi": round(float(row["rsi"]), 2),
            "macd": round(float(row["macd"]), 4),
            "macd_signal": round(float(row["macd_signal"]), 4),
            "bb_upper": round(float(row["bb_upper"]), 4),
            "bb_lower": round(float(row["bb_lower"]), 4),
        },
    )
