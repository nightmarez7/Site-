"""Cliente da API da Runway ML para geração de imagem e vídeo (Etapa 2 do pipeline).

Fluxo assíncrono por tarefa: cria a tarefa via POST, espera por polling em
GET /tasks/{id} até `status == "SUCCEEDED"` e baixa o resultado.
"""

from __future__ import annotations

import base64
import time
from pathlib import Path

import requests

from scripts.config import (
    RUNWAY_API_KEY,
    RUNWAY_API_VERSION,
    RUNWAY_BASE_URL,
    RUNWAY_MODEL_IMAGEM,
    RUNWAY_MODEL_VIDEO,
    RUNWAY_POLL_INTERVALO_SEGUNDOS,
    RUNWAY_POLL_TIMEOUT_SEGUNDOS,
    RUNWAY_RATIO_IMAGEM,
    RUNWAY_RATIO_VIDEO,
)
from scripts.logger import get_logger
from scripts.retry import com_retry

logger = get_logger(__name__)


class RunwayAPIError(RuntimeError):
    pass


def _headers() -> dict:
    if not RUNWAY_API_KEY:
        raise RunwayAPIError("RUNWAY_API_KEY não configurada. Defina-a no .env (veja .env.example).")
    return {
        "Authorization": f"Bearer {RUNWAY_API_KEY}",
        "Content-Type": "application/json",
        "X-Runway-Version": RUNWAY_API_VERSION,
    }


def _data_uri(caminho_imagem: Path) -> str:
    conteudo = base64.b64encode(caminho_imagem.read_bytes()).decode("utf-8")
    return f"data:image/png;base64,{conteudo}"


@com_retry(tentativas=4, espera_inicial=3.0, excecoes=(requests.RequestException, RunwayAPIError))
def _post(caminho: str, payload: dict) -> dict:
    resp = requests.post(f"{RUNWAY_BASE_URL}{caminho}", json=payload, headers=_headers(), timeout=30)
    if resp.status_code >= 400:
        raise RunwayAPIError(f"Runway API retornou {resp.status_code} em {caminho}: {resp.text}")
    return resp.json()


@com_retry(tentativas=4, espera_inicial=3.0, excecoes=(requests.RequestException, RunwayAPIError))
def _get(caminho: str) -> dict:
    resp = requests.get(f"{RUNWAY_BASE_URL}{caminho}", headers=_headers(), timeout=30)
    if resp.status_code >= 400:
        raise RunwayAPIError(f"Runway API retornou {resp.status_code} em {caminho}: {resp.text}")
    return resp.json()


def _aguardar_tarefa(task_id: str) -> dict:
    decorrido = 0
    while decorrido < RUNWAY_POLL_TIMEOUT_SEGUNDOS:
        dados = _get(f"/tasks/{task_id}")
        status = dados.get("status")
        if status == "SUCCEEDED":
            return dados
        if status in ("FAILED", "CANCELLED"):
            raise RunwayAPIError(f"Tarefa Runway {status.lower()}: {dados.get('failure') or dados}")
        time.sleep(RUNWAY_POLL_INTERVALO_SEGUNDOS)
        decorrido += RUNWAY_POLL_INTERVALO_SEGUNDOS
    raise RunwayAPIError(f"Timeout aguardando tarefa Runway {task_id}")


def _baixar_arquivo(url: str, destino: Path) -> Path:
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(resp.content)
    return destino


def gerar_imagem(prompt: str, destino: Path, imagem_referencia: Path | None = None) -> Path:
    """Gera uma imagem a partir de um prompt textual.

    Quando `imagem_referencia` é informada, ela é enviada como imagem de referência
    (`referenceImages`, recurso "References" do Gen-4) e citada no prompt como `@personagem`,
    para manter a aparência do personagem consistente entre cenas/episódios.
    """
    payload: dict = {
        "model": RUNWAY_MODEL_IMAGEM,
        "promptText": prompt,
        "ratio": RUNWAY_RATIO_IMAGEM,
    }
    if imagem_referencia is not None:
        payload["promptText"] = f"@personagem {prompt}"
        payload["referenceImages"] = [{"uri": _data_uri(imagem_referencia), "tag": "personagem"}]

    criada = _post("/text_to_image", payload)
    task_id = criada["id"]
    logger.info("Tarefa de imagem Runway criada (%s): %s", task_id, destino.name)

    resultado = _aguardar_tarefa(task_id)
    url_imagem = resultado["output"][0]
    return _baixar_arquivo(url_imagem, destino)


def gerar_video_a_partir_de_imagem(prompt: str, imagem_base: Path, destino: Path) -> Path:
    """Anima uma imagem estática (já consistente com o personagem) em um clipe de vídeo curto."""
    payload = {
        "model": RUNWAY_MODEL_VIDEO,
        "promptImage": _data_uri(imagem_base),
        "promptText": prompt,
        "ratio": RUNWAY_RATIO_VIDEO,
        "duration": 5,
    }
    criada = _post("/image_to_video", payload)
    task_id = criada["id"]
    logger.info("Tarefa de vídeo Runway criada (%s): %s", task_id, destino.name)

    resultado = _aguardar_tarefa(task_id)
    url_video = resultado["output"][0]
    return _baixar_arquivo(url_video, destino)
