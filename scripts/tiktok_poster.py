"""Etapa 5 do pipeline: publica o episódio no TikTok, com fallback manual.

Se as credenciais do TikTok não estiverem configuradas (app ainda não aprovado
no TikTok for Developers) ou a publicação falhar, o vídeo já pronto é mantido
em `PASTA_POSTAGEM_MANUAL` com um arquivo de legenda ao lado, pronto para
postagem manual.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from scripts.config import PASTA_POSTAGEM_MANUAL, TIKTOK_ACCESS_TOKEN
from scripts.logger import get_logger
from scripts.providers.tiktok import TikTokAPIError, publicar_video
from scripts.roteiro_generator import Roteiro

logger = get_logger(__name__)


def _montar_legenda(roteiro: Roteiro) -> str:
    tags = " ".join(f"#{h}" for h in roteiro.hashtags)
    return f"{roteiro.titulo}\n\n{roteiro.cta_final}\n\n{tags}"


def _salvar_para_postagem_manual(caminho_video: Path, legenda: str, motivo: str) -> dict:
    destino_video = PASTA_POSTAGEM_MANUAL / caminho_video.name
    if destino_video.resolve() != caminho_video.resolve():
        shutil.copy2(caminho_video, destino_video)

    destino_legenda = destino_video.with_suffix(".txt")
    destino_legenda.write_text(legenda, encoding="utf-8")

    logger.info("Postagem manual: vídeo em %s, legenda em %s (%s)", destino_video, destino_legenda, motivo)
    return {"status": "aguardando_postagem_manual", "video": str(destino_video), "motivo": motivo}


def publicar_ou_salvar(roteiro: Roteiro, caminho_video: Path) -> dict:
    legenda = _montar_legenda(roteiro)

    if not TIKTOK_ACCESS_TOKEN:
        return _salvar_para_postagem_manual(
            caminho_video, legenda, "TIKTOK_ACCESS_TOKEN não configurado (app ainda não aprovado)"
        )

    try:
        resultado = publicar_video(caminho_video, legenda)
        return {"status": "publicado", **resultado}
    except TikTokAPIError:
        logger.exception("Falha ao publicar no TikTok, salvando para postagem manual.")
        return _salvar_para_postagem_manual(caminho_video, legenda, "falha na API do TikTok")
