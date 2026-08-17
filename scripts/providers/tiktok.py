"""Cliente da TikTok Content Posting API (Direct Post) para publicar vídeos (Etapa 5).

Fluxo: inicia o upload (`/post/publish/video/init/`), envia o arquivo via PUT
para a `upload_url` retornada, e consulta o status (`/post/publish/status/fetch/`)
até a publicação ser processada. Requer um app aprovado no TikTok for Developers
com o escopo `video.publish`.
"""

from __future__ import annotations

import time
from pathlib import Path

import requests

from scripts.config import (
    TIKTOK_ACCESS_TOKEN,
    TIKTOK_BASE_URL,
    TIKTOK_PRIVACY_LEVEL,
)
from scripts.logger import get_logger
from scripts.retry import com_retry

logger = get_logger(__name__)

_POLL_INTERVALO_SEGUNDOS = 5
_POLL_TIMEOUT_SEGUNDOS = 120


class TikTokAPIError(RuntimeError):
    pass


def _headers() -> dict:
    if not TIKTOK_ACCESS_TOKEN:
        raise TikTokAPIError("TIKTOK_ACCESS_TOKEN não configurado.")
    return {"Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}", "Content-Type": "application/json"}


@com_retry(tentativas=3, espera_inicial=3.0, excecoes=(requests.RequestException, TikTokAPIError))
def _iniciar_publicacao(tamanho_video: int, legenda_completa: str) -> dict:
    payload = {
        "post_info": {
            "title": legenda_completa,
            "privacy_level": TIKTOK_PRIVACY_LEVEL,
            "disable_duplicate_check": True,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": tamanho_video,
            "chunk_size": tamanho_video,
            "total_chunk_count": 1,
        },
    }
    resp = requests.post(
        f"{TIKTOK_BASE_URL}/post/publish/video/init/", json=payload, headers=_headers(), timeout=30
    )
    if resp.status_code >= 400:
        raise TikTokAPIError(f"TikTok API retornou {resp.status_code} ao iniciar: {resp.text}")
    dados = resp.json()
    if dados.get("error", {}).get("code") not in (None, "ok"):
        raise TikTokAPIError(f"TikTok API recusou a publicação: {dados['error']}")
    return dados["data"]


@com_retry(tentativas=3, espera_inicial=3.0, excecoes=(requests.RequestException, TikTokAPIError))
def _enviar_video(upload_url: str, caminho_video: Path) -> None:
    tamanho = caminho_video.stat().st_size
    conteudo = caminho_video.read_bytes()
    headers = {
        "Content-Type": "video/mp4",
        "Content-Range": f"bytes 0-{tamanho - 1}/{tamanho}",
    }
    resp = requests.put(upload_url, data=conteudo, headers=headers, timeout=180)
    if resp.status_code >= 400:
        raise TikTokAPIError(f"Falha no upload do vídeo ({resp.status_code}): {resp.text}")


def _aguardar_processamento(publish_id: str) -> str:
    decorrido = 0
    while decorrido < _POLL_TIMEOUT_SEGUNDOS:
        resp = requests.post(
            f"{TIKTOK_BASE_URL}/post/publish/status/fetch/",
            json={"publish_id": publish_id},
            headers=_headers(),
            timeout=30,
        )
        if resp.status_code >= 400:
            raise TikTokAPIError(f"TikTok API retornou {resp.status_code} ao checar status: {resp.text}")
        status = resp.json()["data"]["status"]
        if status in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"):
            return status
        if status == "FAILED":
            raise TikTokAPIError(f"Publicação falhou no lado do TikTok: {resp.json()}")
        time.sleep(_POLL_INTERVALO_SEGUNDOS)
        decorrido += _POLL_INTERVALO_SEGUNDOS
    raise TikTokAPIError(f"Timeout aguardando processamento da publicação {publish_id}")


def publicar_video(caminho_video: Path, legenda_completa: str) -> dict:
    """Publica o vídeo via Direct Post. Retorna {publish_id, status}."""
    tamanho = caminho_video.stat().st_size
    dados_init = _iniciar_publicacao(tamanho, legenda_completa)
    publish_id = dados_init["publish_id"]
    logger.info("Publicação iniciada no TikTok: %s", publish_id)

    _enviar_video(dados_init["upload_url"], caminho_video)
    logger.info("Upload do vídeo concluído, aguardando processamento...")

    status = _aguardar_processamento(publish_id)
    logger.info("Publicação no TikTok concluída: %s (%s)", publish_id, status)
    return {"publish_id": publish_id, "status": status}
