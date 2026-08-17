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

PERSONAGENS_FILE = DATA_DIR / "personagens.json"
EPISODIOS_FILE = DATA_DIR / "episodios.json"

for _dir in (DATA_DIR, ROTEIROS_DIR, LOGS_DIR, MEDIA_RAW_DIR, MEDIA_FINAL_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

DURACAO_MIN_SEGUNDOS = 20
DURACAO_MAX_SEGUNDOS = 40
