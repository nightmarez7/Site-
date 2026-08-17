"""Decorator simples de retry com backoff exponencial para chamadas de API externas."""

from __future__ import annotations

import functools
import time
from typing import Callable, TypeVar

from scripts.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def com_retry(
    tentativas: int = 4,
    espera_inicial: float = 2.0,
    fator_backoff: float = 2.0,
    excecoes: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Reexecuta a função decorada em caso de falha, com espera exponencial entre tentativas."""

    def decorador(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            espera = espera_inicial
            ultima_excecao: BaseException | None = None
            for tentativa in range(1, tentativas + 1):
                try:
                    return func(*args, **kwargs)
                except excecoes as exc:
                    ultima_excecao = exc
                    if tentativa == tentativas:
                        break
                    logger.warning(
                        "Tentativa %s/%s falhou em %s: %s. Retentando em %.1fs...",
                        tentativa,
                        tentativas,
                        func.__name__,
                        exc,
                        espera,
                    )
                    time.sleep(espera)
                    espera *= fator_backoff
            assert ultima_excecao is not None
            raise ultima_excecao

        return wrapper

    return decorador
