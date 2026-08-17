"""Fila/histórico de episódios em JSON: garante continuidade (numeração e resumo) entre execuções do bot."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from scripts.config import EPISODIOS_FILE


def _carregar() -> list[dict[str, Any]]:
    if not EPISODIOS_FILE.exists():
        return []
    return json.loads(EPISODIOS_FILE.read_text(encoding="utf-8"))


def _salvar(episodios: list[dict[str, Any]]) -> None:
    EPISODIOS_FILE.write_text(
        json.dumps(episodios, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def proximo_numero_parte() -> int:
    episodios = _carregar()
    if not episodios:
        return 1
    return max(ep["numero_parte"] for ep in episodios) + 1


def contexto_capitulo_anterior() -> str | None:
    """Resumo do último episódio registrado, usado para dar continuidade ao roteiro seguinte."""
    episodios = _carregar()
    if not episodios:
        return None
    ultimo = max(episodios, key=lambda ep: ep["numero_parte"])
    return ultimo.get("resumo_capitulo")


def atualizar_status(numero_parte: int, status: str) -> None:
    episodios = _carregar()
    for episodio in episodios:
        if episodio["numero_parte"] == numero_parte:
            episodio["status"] = status
            break
    _salvar(episodios)


def registrar_episodio(
    numero_parte: int,
    titulo: str,
    resumo_capitulo: str,
    arquivo_roteiro: str,
    status: str = "roteiro_gerado",
) -> None:
    episodios = _carregar()
    episodios.append(
        {
            "numero_parte": numero_parte,
            "titulo": titulo,
            "resumo_capitulo": resumo_capitulo,
            "arquivo_roteiro": arquivo_roteiro,
            "status": status,
            "criado_em": datetime.now(timezone.utc).isoformat(),
        }
    )
    _salvar(episodios)
