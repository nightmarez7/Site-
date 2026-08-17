"""Ponto de entrada do bot: roda o pipeline completo para 1 episódio por execução.

Uso:
    python main.py [--parte N]

Pipeline completo: roteiro -> imagem/vídeo por cena -> narração -> montagem
final -> postagem no TikTok (ou salvamento para postagem manual).
"""

from __future__ import annotations

import argparse
import sys

from scripts import fila
from scripts.geracao_midia import gerar_midia_do_roteiro
from scripts.logger import get_logger
from scripts.montagem import montar_video_final
from scripts.narracao import gerar_narracao_do_roteiro
from scripts.roteiro_generator import gerar_roteiro, salvar_roteiro
from scripts.tiktok_poster import publicar_ou_salvar

logger = get_logger("main")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera e publica um episódio de novelinha de IA.")
    parser.add_argument(
        "--parte",
        type=int,
        default=None,
        help="Força um número de parte específico (padrão: próximo da fila).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    logger.info("=== Início da execução do pipeline ===")

    # Etapa 1: roteiro
    try:
        roteiro = gerar_roteiro(numero_parte=args.parte)
        salvar_roteiro(roteiro)
    except Exception:
        logger.exception("Falha na Etapa 1 (geração de roteiro). Abortando execução.")
        return 1

    # Etapa 2: geração de imagem/vídeo por cena
    try:
        midias = gerar_midia_do_roteiro(roteiro)
        fila.atualizar_status(roteiro.numero_parte, "midia_gerada")
        logger.info("Etapa 2 concluída: %s arquivos de mídia gerados.", len(midias))
    except Exception:
        logger.exception("Falha na Etapa 2 (geração de imagem/vídeo). Abortando execução.")
        return 1

    # Etapa 3: narração/TTS
    try:
        narracoes = gerar_narracao_do_roteiro(roteiro)
        fila.atualizar_status(roteiro.numero_parte, "narracao_gerada")
        logger.info("Etapa 3 concluída: %s narrações geradas.", len(narracoes))
    except Exception:
        logger.exception("Falha na Etapa 3 (narração/TTS). Abortando execução.")
        return 1

    # Etapa 4: montagem final (moviepy/ffmpeg)
    try:
        caminho_video = montar_video_final(roteiro, midias, narracoes)
        fila.atualizar_status(roteiro.numero_parte, "video_montado")
        logger.info("Etapa 4 concluída: vídeo final em %s", caminho_video)
    except Exception:
        logger.exception("Falha na Etapa 4 (montagem final). Abortando execução.")
        return 1

    # Etapa 5: postagem no TikTok (ou salvamento para postagem manual)
    try:
        resultado_postagem = publicar_ou_salvar(roteiro, caminho_video)
        fila.atualizar_status(roteiro.numero_parte, resultado_postagem["status"])
        logger.info("Etapa 5 concluída: %s", resultado_postagem)
    except Exception:
        logger.exception("Falha na Etapa 5 (postagem no TikTok). O vídeo final continua em %s", caminho_video)
        return 1

    logger.info("=== Fim da execução: episódio %s pronto em %s ===", roteiro.numero_parte, caminho_video)
    return 0


if __name__ == "__main__":
    sys.exit(main())
