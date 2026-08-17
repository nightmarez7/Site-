"""Configuração central do bot: paths e variáveis de ambiente."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
ROTEIROS_DIR = DATA_DIR / "roteiros"
LOGS_DIR = DATA_DIR / "logs"
MEDIA_RAW_DIR = BASE_DIR / "media" / "raw"
MEDIA_FINAL_DIR = BASE_DIR / "media" / "final"
MEDIA_RAW_PERSONAGENS_DIR = MEDIA_RAW_DIR / "personagens"

PERSONAGENS_FILE = DATA_DIR / "personagens.json"
EPISODIOS_FILE = DATA_DIR / "episodios.json"

for _dir in (
    DATA_DIR,
    ROTEIROS_DIR,
    LOGS_DIR,
    MEDIA_RAW_DIR,
    MEDIA_FINAL_DIR,
    MEDIA_RAW_PERSONAGENS_DIR,
):
    _dir.mkdir(parents=True, exist_ok=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

DURACAO_MIN_SEGUNDOS = 20
DURACAO_MAX_SEGUNDOS = 40

LARGURA_VIDEO = 1080
ALTURA_VIDEO = 1920

# Etapa 2: geração de imagem/vídeo (provedor: Kling AI)
KLING_ACCESS_KEY = os.getenv("KLING_ACCESS_KEY", "")
KLING_SECRET_KEY = os.getenv("KLING_SECRET_KEY", "")
# Endpoint internacional documentado pela Kling em 2025; confirme na sua conta antes de rodar em
# produção, pois provedores de geração de mídia mudam host/versão de API com frequência.
KLING_BASE_URL = os.getenv("KLING_BASE_URL", "https://api-singapore.klingai.com")
KLING_MODEL_IMAGEM = os.getenv("KLING_MODEL_IMAGEM", "kling-v1-5")
KLING_MODEL_VIDEO = os.getenv("KLING_MODEL_VIDEO", "kling-v1-6")
KLING_POLL_INTERVALO_SEGUNDOS = int(os.getenv("KLING_POLL_INTERVALO_SEGUNDOS", "5"))
KLING_POLL_TIMEOUT_SEGUNDOS = int(os.getenv("KLING_POLL_TIMEOUT_SEGUNDOS", "300"))

# "imagem": 1 imagem estática por cena (rápido/barato). "video": anima cada imagem em um clipe curto.
MIDIA_TIPO = os.getenv("MIDIA_TIPO", "imagem")
