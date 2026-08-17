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

# Etapa 2: geração de imagem/vídeo (provedor: Runway ML)
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY", "")
RUNWAY_BASE_URL = os.getenv("RUNWAY_BASE_URL", "https://api.dev.runwayml.com/v1")
RUNWAY_API_VERSION = os.getenv("RUNWAY_API_VERSION", "2024-11-06")
RUNWAY_MODEL_IMAGEM = os.getenv("RUNWAY_MODEL_IMAGEM", "gen4_image")
RUNWAY_MODEL_VIDEO = os.getenv("RUNWAY_MODEL_VIDEO", "gen4_turbo")
# Strings de ratio são específicas de cada modelo Runway e mudam de tempos em tempos —
# confirme os valores aceitos na doc atual da Runway antes de rodar em produção; dá pra
# sobrescrever aqui via .env sem tocar no código caso a API rejeite o valor padrão.
RUNWAY_RATIO_IMAGEM = os.getenv("RUNWAY_RATIO_IMAGEM", "1080:1920")
RUNWAY_RATIO_VIDEO = os.getenv("RUNWAY_RATIO_VIDEO", "1080:1920")
RUNWAY_POLL_INTERVALO_SEGUNDOS = int(os.getenv("RUNWAY_POLL_INTERVALO_SEGUNDOS", "5"))
RUNWAY_POLL_TIMEOUT_SEGUNDOS = int(os.getenv("RUNWAY_POLL_TIMEOUT_SEGUNDOS", "300"))

# "imagem": 1 imagem estática por cena (rápido/barato). "video": anima cada imagem em um clipe curto.
MIDIA_TIPO = os.getenv("MIDIA_TIPO", "imagem")

# Etapa 3: narração (provedor: ElevenLabs)
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_BASE_URL = os.getenv("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io/v1")
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

# Etapa 4: montagem final
FONTE_LEGENDA_PATH = os.getenv("FONTE_LEGENDA_PATH", "")
TAMANHO_FONTE_LEGENDA = int(os.getenv("TAMANHO_FONTE_LEGENDA", "72"))
MUSICA_FUNDO_DIR = BASE_DIR / "media" / "musica"
MUSICA_FUNDO_DIR.mkdir(parents=True, exist_ok=True)
MUSICA_FUNDO_VOLUME = float(os.getenv("MUSICA_FUNDO_VOLUME", "0.15"))
VIDEO_FPS = int(os.getenv("VIDEO_FPS", "30"))

# Etapa 5: postagem no TikTok
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")
TIKTOK_BASE_URL = os.getenv("TIKTOK_BASE_URL", "https://open.tiktokapis.com/v2")
# Privacidade do post: por segurança o padrão é privado (só você vê). Troque explicitamente
# para "PUBLIC_TO_EVERYONE" no .env quando quiser que o bot publique de fato em público.
TIKTOK_PRIVACY_LEVEL = os.getenv("TIKTOK_PRIVACY_LEVEL", "SELF_ONLY")
PASTA_POSTAGEM_MANUAL = Path(os.getenv("PASTA_POSTAGEM_MANUAL", str(MEDIA_FINAL_DIR)))
PASTA_POSTAGEM_MANUAL.mkdir(parents=True, exist_ok=True)
