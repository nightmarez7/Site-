"""Ponto de entrada do bot: roda o pipeline completo para 1 episódio por execução.

Uso:
    python main.py [--parte N]

Hoje só a Etapa 1 (geração de roteiro) está implementada. As demais etapas
(imagem/vídeo, narração, montagem, postagem) entram nos próximos passos e
serão encadeadas aqui mesmo.
"""

from __future__ import annotations

import argparse
import sys

from scripts.logger import get_logger
from scripts.roteiro_generator import gerar_roteiro, salvar_roteiro

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
        caminho_roteiro = salvar_roteiro(roteiro)
    except Exception:
        logger.exception("Falha na Etapa 1 (geração de roteiro). Abortando execução.")
        return 1

    # Etapa 2: geração de imagem/vídeo por cena — TODO
    logger.info("Etapa 2 (imagem/vídeo) ainda não implementada.")

    # Etapa 3: narração/TTS — TODO
    logger.info("Etapa 3 (narração/TTS) ainda não implementada.")

    # Etapa 4: montagem final (moviepy/ffmpeg) — TODO
    logger.info("Etapa 4 (montagem final) ainda não implementada.")

    # Etapa 5: postagem no TikTok — TODO
    logger.info("Etapa 5 (postagem no TikTok) ainda não implementada.")

    logger.info("=== Fim da execução: roteiro pronto em %s ===", caminho_roteiro)
    return 0


if __name__ == "__main__":
    sys.exit(main())
