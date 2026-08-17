"""Cliente da API da Kling AI para geração de imagem e vídeo (Etapa 2 do pipeline).

Fluxo assíncrono por tarefa: cria a tarefa via POST, espera por polling até
`task_status == "succeed"` e baixa o resultado para um arquivo local.
"""

from __future__ import annotations

import base64
import time
from pathlib import Path

import jwt
import requests

from scripts.config import (
    KLING_ACCESS_KEY,
    KLING_BASE_URL,
    KLING_MODEL_IMAGEM,
    KLING_MODEL_VIDEO,
    KLING_POLL_INTERVALO_SEGUNDOS,
    KLING_POLL_TIMEOUT_SEGUNDOS,
    KLING_SECRET_KEY,
)
from scripts.logger import get_logger
from scripts.retry import com_retry

logger = get_logger(__name__)


class KlingAPIError(RuntimeError):
    pass


def _gerar_token() -> str:
    if not KLING_ACCESS_KEY or not KLING_SECRET_KEY:
        raise KlingAPIError(
            "KLING_ACCESS_KEY / KLING_SECRET_KEY não configuradas. Defina-as no .env (veja .env.example)."
        )
    agora = int(time.time())
    payload = {"iss": KLING_ACCESS_KEY, "exp": agora + 1800, "nbf": agora - 5}
    return jwt.encode(
        payload, KLING_SECRET_KEY, algorithm="HS256", headers={"alg": "HS256", "typ": "JWT"}
    )


def _headers() -> dict:
    return {"Authorization": f"Bearer {_gerar_token()}", "Content-Type": "application/json"}


@com_retry(tentativas=4, espera_inicial=3.0, excecoes=(requests.RequestException, KlingAPIError))
def _post(caminho: str, payload: dict) -> dict:
    resp = requests.post(f"{KLING_BASE_URL}{caminho}", json=payload, headers=_headers(), timeout=30)
    if resp.status_code >= 400:
        raise KlingAPIError(f"Kling API retornou {resp.status_code} em {caminho}: {resp.text}")
    return resp.json()


@com_retry(tentativas=4, espera_inicial=3.0, excecoes=(requests.RequestException, KlingAPIError))
def _get(caminho: str) -> dict:
    resp = requests.get(f"{KLING_BASE_URL}{caminho}", headers=_headers(), timeout=30)
    if resp.status_code >= 400:
        raise KlingAPIError(f"Kling API retornou {resp.status_code} em {caminho}: {resp.text}")
    return resp.json()


def _aguardar_tarefa(caminho_consulta: str) -> dict:
    decorrido = 0
    while decorrido < KLING_POLL_TIMEOUT_SEGUNDOS:
        dados = _get(caminho_consulta)["data"]
        status = dados.get("task_status")
        if status == "succeed":
            return dados
        if status == "failed":
            raise KlingAPIError(f"Tarefa Kling falhou: {dados.get('task_status_msg')}")
        time.sleep(KLING_POLL_INTERVALO_SEGUNDOS)
        decorrido += KLING_POLL_INTERVALO_SEGUNDOS
    raise KlingAPIError(f"Timeout aguardando tarefa Kling em {caminho_consulta}")


def _baixar_arquivo(url: str, destino: Path) -> Path:
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(resp.content)
    return destino


def gerar_imagem(prompt: str, destino: Path, imagem_referencia: Path | None = None) -> Path:
    """Gera uma imagem a partir de um prompt textual.

    Quando `imagem_referencia` é informada, ela é enviada como condicionamento
    visual para manter a aparência do personagem consistente entre cenas/episódios.
    """
    payload: dict = {
        "model_name": KLING_MODEL_IMAGEM,
        "prompt": prompt,
        "n": 1,
        "aspect_ratio": "9:16",
    }
    if imagem_referencia is not None:
        payload["image"] = base64.b64encode(imagem_referencia.read_bytes()).decode("utf-8")
        payload["image_fidelity"] = 0.5

    criada = _post("/v1/images/generations", payload)
    task_id = criada["data"]["task_id"]
    logger.info("Tarefa de imagem Kling criada (%s): %s", task_id, destino.name)

    resultado = _aguardar_tarefa(f"/v1/images/generations/{task_id}")
    url_imagem = resultado["task_result"]["images"][0]["url"]
    return _baixar_arquivo(url_imagem, destino)


def gerar_video_a_partir_de_imagem(prompt: str, imagem_base: Path, destino: Path) -> Path:
    """Anima uma imagem estática (já consistente com o personagem) em um clipe de vídeo curto."""
    payload = {
        "model_name": KLING_MODEL_VIDEO,
        "image": base64.b64encode(imagem_base.read_bytes()).decode("utf-8"),
        "prompt": prompt,
        "aspect_ratio": "9:16",
        "duration": "5",
    }
    criada = _post("/v1/videos/image2video", payload)
    task_id = criada["data"]["task_id"]
    logger.info("Tarefa de vídeo Kling criada (%s): %s", task_id, destino.name)

    resultado = _aguardar_tarefa(f"/v1/videos/image2video/{task_id}")
    url_video = resultado["task_result"]["videos"][0]["url"]
    return _baixar_arquivo(url_video, destino)
