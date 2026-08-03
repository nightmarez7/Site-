"""Envio de alertas para o Telegram via Bot API.

Como configurar:
1. Fale com @BotFather no Telegram, crie um bot e copie o token.
2. Descubra o chat_id: mande uma mensagem para o bot e acesse
   https://api.telegram.org/bot<TOKEN>/getUpdates para ler o "chat":{"id": ...}
3. Exporte as variaveis de ambiente (ou passe via CLI):
   export TELEGRAM_BOT_TOKEN="123456:ABC..."
   export TELEGRAM_CHAT_ID="987654321"
"""

from __future__ import annotations

import os

import requests

from strategy import Signal

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram_message(text: str, token: str | None = None, chat_id: str | None = None) -> None:
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise ValueError(
            "Configure TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID (env vars ou "
            "--telegram-token/--telegram-chat-id) para usar os alertas"
        )

    response = requests.post(
        TELEGRAM_API_URL.format(token=token),
        data={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        timeout=10,
    )
    response.raise_for_status()


def format_signal_message(signal: Signal) -> str:
    emoji = {"COMPRAR": "🟢", "VENDER": "🔴", "AGUARDAR": "🟡"}.get(signal.action, "")
    lines = [
        f"{emoji} *{signal.symbol}* — sinal: *{signal.action}* (score {signal.score:+d})",
        f"Preco: {signal.price:.4f}",
        "",
        *[f"- {reason}" for reason in signal.reasons],
    ]

    if signal.risk_plan:
        plan = signal.risk_plan
        lines += [
            "",
            "*Plano de risco:*",
            f"Stop-loss: {plan.stop_loss:.4f}",
            f"Take-profit: {plan.take_profit:.4f}",
            f"Tamanho sugerido: {plan.position_size:.6f} ({plan.position_value:.2f} na cotacao)",
            f"Capital arriscado: {plan.risk_amount:.2f}",
        ]

    lines += ["", "_Analise tecnica automatizada, nao e recomendacao financeira._"]
    return "\n".join(lines)


def send_signal_alert(signal: Signal, token: str | None = None, chat_id: str | None = None) -> None:
    send_telegram_message(format_signal_message(signal), token=token, chat_id=chat_id)
