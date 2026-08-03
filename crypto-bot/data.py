"""Cliente de dados de mercado. Usa a API publica da Binance (sem necessidade de API key)
para obter candles (OHLCV) de qualquer par, ex: BTCUSDT, ETHUSDT, SOLUSDT.
"""

from __future__ import annotations

import pandas as pd
import requests

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"

# Colunas retornadas pela API de klines da Binance, nesta ordem.
_KLINE_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_asset_volume",
    "num_trades",
    "taker_buy_base",
    "taker_buy_quote",
    "ignore",
]

_NUMERIC_COLUMNS = ["open", "high", "low", "close", "volume"]


def fetch_ohlcv(symbol: str, interval: str = "1h", limit: int = 500) -> pd.DataFrame:
    """Busca candles OHLCV para `symbol` (ex: BTCUSDT) no intervalo dado
    (1m, 5m, 15m, 1h, 4h, 1d, ...). Retorna um DataFrame ordenado por tempo crescente.
    """
    if not (1 <= limit <= 1000):
        raise ValueError("limit deve estar entre 1 e 1000 (limite da API da Binance)")

    params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
    response = requests.get(BINANCE_KLINES_URL, params=params, timeout=15)

    if response.status_code == 400:
        raise ValueError(
            f"Par '{symbol}' ou intervalo '{interval}' invalido para a Binance: {response.text}"
        )
    response.raise_for_status()

    raw = response.json()
    df = pd.DataFrame(raw, columns=_KLINE_COLUMNS)
    df[_NUMERIC_COLUMNS] = df[_NUMERIC_COLUMNS].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")

    return df[["open_time", "open", "high", "low", "close", "volume", "close_time"]]


def fetch_current_price(symbol: str) -> float:
    """Preco atual (ultimo trade) de um par, ex: BTCUSDT."""
    resp = requests.get(
        "https://api.binance.com/api/v3/ticker/price",
        params={"symbol": symbol.upper()},
        timeout=15,
    )
    resp.raise_for_status()
    return float(resp.json()["price"])
