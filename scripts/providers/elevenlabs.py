"""Cliente da API da ElevenLabs para narração (Etapa 3 do pipeline).

Diferente da Kling/Runway, o endpoint de text-to-speech da ElevenLabs é
síncrono: a chamada já retorna os bytes do áudio, sem fila de tarefa.
"""

from __future__ import annotations

from pathlib import Path

import requests

from scripts.config import ELEVENLABS_API_KEY, ELEVENLABS_BASE_URL, ELEVENLABS_MODEL
from scripts.logger import get_logger
from scripts.retry import com_retry

logger = get_logger(__name__)


class ElevenLabsAPIError(RuntimeError):
    pass


def _headers() -> dict:
    if not ELEVENLABS_API_KEY:
        raise ElevenLabsAPIError(
            "ELEVENLABS_API_KEY não configurada. Defina-a no .env (veja .env.example)."
        )
    return {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}


@com_retry(tentativas=4, espera_inicial=3.0, excecoes=(requests.RequestException, ElevenLabsAPIError))
def gerar_narracao(
    texto: str,
    voz_id: str,
    destino: Path,
    estabilidade: float = 0.5,
    exagero: float = 0.3,
    similaridade: float = 0.75,
) -> Path:
    """Gera o áudio de uma fala e salva em `destino` (mp3).

    `estabilidade` baixa e `exagero` alto deixam a voz mais expressiva/emocional —
    usados para variar a emoção de cada personagem entre cenas de drama.
    """
    payload = {
        "text": texto,
        "model_id": ELEVENLABS_MODEL,
        "voice_settings": {
            "stability": estabilidade,
            "similarity_boost": similaridade,
            "style": exagero,
            "use_speaker_boost": True,
        },
    }
    resp = requests.post(
        f"{ELEVENLABS_BASE_URL}/text-to-speech/{voz_id}",
        json=payload,
        headers=_headers(),
        timeout=60,
    )
    if resp.status_code >= 400:
        raise ElevenLabsAPIError(f"ElevenLabs API retornou {resp.status_code}: {resp.text}")

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(resp.content)
    logger.info("Narração gerada: %s", destino.name)
    return destino
