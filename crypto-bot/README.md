# Crypto Analysis Bot

Bot de analise tecnica para compra/venda de criptomoedas. Busca candles publicos
da Binance (sem necessidade de API key), calcula indicadores tecnicos classicos
e gera um sinal **COMPRAR / VENDER / AGUARDAR** para cada par informado.

> ⚠️ **Aviso:** isto e uma ferramenta de analise tecnica automatizada, **nao e
> recomendacao financeira**. Mercado de criptomoedas e altamente volatil.
> Use por sua conta e risco, valide com backtest antes de operar e nunca
> invista mais do que voce pode perder. Dados historicos nao garantem
> resultados futuros.

## Como funciona a estrategia

Para cada candle mais recente, o bot calcula 4 sinais e soma um score de -4 a +4:

| Indicador | Sinal de compra (+1) | Sinal de venda (-1) |
|---|---|---|
| Media movel (SMA 9 vs SMA 21) | rapida acima da lenta (tendencia de alta) | rapida abaixo da lenta |
| MACD (12,26,9) | MACD acima da linha de sinal | MACD abaixo da linha de sinal |
| RSI (14) | RSI < 30 (sobrevenda) | RSI > 70 (sobrecompra) |
| Bandas de Bollinger (20, 2σ) | preco <= banda inferior | preco >= banda superior |

- Score **>= +2** → `COMPRAR`
- Score **<= -2** → `VENDER`
- Caso contrario → `AGUARDAR`

## Instalacao

```bash
cd crypto-bot
python3 -m venv .venv && source .venv/bin/activate  # opcional
pip install -r requirements.txt
```

## Uso

Analise pontual de um ou mais pares:

```bash
python bot.py BTCUSDT
python bot.py BTCUSDT ETHUSDT SOLUSDT --interval 4h --limit 200
```

Modo continuo (analisa a cada N segundos ate Ctrl+C):

```bash
python bot.py BTCUSDT ETHUSDT --interval 15m --watch --every 300
```

Backtest da estrategia sobre dados historicos (compara com buy & hold):

```bash
python bot.py BTCUSDT --backtest --interval 1h --limit 500 --capital 1000
```

### Parametros

| Flag | Descricao | Default |
|---|---|---|
| `symbols` | Um ou mais pares da Binance, ex: `BTCUSDT ETHUSDT` | obrigatorio |
| `--interval` | Timeframe: `1m,5m,15m,1h,4h,1d,...` | `1h` |
| `--limit` | Numero de candles buscados (max 1000, API Binance) | `200` |
| `--watch` | Roda em loop continuo | desligado |
| `--every` | Segundos entre analises no modo `--watch` | `300` |
| `--backtest` | Roda um backtest em vez de analise ao vivo | desligado |
| `--capital` | Capital inicial simulado no backtest | `1000` |

## Estrutura

```
crypto-bot/
├── bot.py          # CLI principal
├── data.py         # busca de candles (Binance REST publica)
├── indicators.py   # SMA, EMA, RSI, MACD, Bandas de Bollinger
├── strategy.py      # regras de score -> COMPRAR/VENDER/AGUARDAR
├── backtest.py      # simulacao historica da estrategia vs buy&hold
└── requirements.txt
```

## Limitacoes conhecidas

- Usa apenas a API publica REST da Binance; pares indisponiveis la (ex: alguns
  tokens listados so em outras exchanges) nao funcionam sem adaptar `data.py`.
- A estrategia e puramente tecnica (preco/volume passados) — nao considera
  noticias, fundamentos on-chain, liquidez ou eventos macro.
- Backtest nao contabiliza taxas de corretagem, slippage nem impostos; retorno
  real de uma operacao ao vivo tende a ser pior que o simulado.
- Sem gestao de risco (stop loss, position sizing, take profit) — adicione
  antes de usar com dinheiro real.
