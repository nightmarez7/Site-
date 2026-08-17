"""Logging compartilhado por todas as etapas do pipeline."""

from __future__ import annotations

import logging

from scripts.config import LOGS_DIR

_FORMATO = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def get_logger(nome: str) -> logging.Logger:
    logger = logging.getLogger(nome)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(_FORMATO))
    logger.addHandler(console)

    arquivo = logging.FileHandler(LOGS_DIR / "bot.log", encoding="utf-8")
    arquivo.setFormatter(logging.Formatter(_FORMATO))
    logger.addHandler(arquivo)

    logger.propagate = False
    return logger
