"""Carregamento e validação do elenco fixo, usado para manter continuidade visual/narrativa entre episódios."""

from __future__ import annotations

import json

from pydantic import BaseModel

from scripts.config import PERSONAGENS_FILE


class Personagem(BaseModel):
    id: str
    nome: str
    papel: str
    descricao_visual: str
    personalidade: str
    voz_estilo: str
    cor_legenda: str


def carregar_personagens() -> list[Personagem]:
    dados = json.loads(PERSONAGENS_FILE.read_text(encoding="utf-8"))
    return [Personagem.model_validate(item) for item in dados]


def personagens_para_prompt(personagens: list[Personagem]) -> str:
    """Formata o elenco em texto para injetar no prompt do Claude, garantindo consistência visual."""
    linhas = []
    for p in personagens:
        linhas.append(
            f"- {p.nome} ({p.papel}): aparência = \"{p.descricao_visual}\"; "
            f"personalidade = {p.personalidade}; voz = {p.voz_estilo}"
        )
    return "\n".join(linhas)
