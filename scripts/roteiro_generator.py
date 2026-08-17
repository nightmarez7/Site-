"""Etapa 1 do pipeline: geração de roteiro de "novelinha de IA" via API da Anthropic.

Gera um capítulo curto (20-40s), em JSON estruturado, mantendo continuidade de
personagens e enredo entre episódios.
"""

from __future__ import annotations

import json
from pathlib import Path

import anthropic
from pydantic import BaseModel, Field, ValidationError

from scripts import fila
from scripts.config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    DURACAO_MAX_SEGUNDOS,
    DURACAO_MIN_SEGUNDOS,
    ROTEIROS_DIR,
)
from scripts.logger import get_logger
from scripts.personagens import Personagem, carregar_personagens, personagens_para_prompt
from scripts.retry import com_retry

logger = get_logger(__name__)

_NOME_FERRAMENTA = "gerar_roteiro"

_TOOL_SCHEMA = {
    "name": _NOME_FERRAMENTA,
    "description": "Registra o roteiro estruturado de um episódio de novelinha de IA para TikTok.",
    "input_schema": {
        "type": "object",
        "properties": {
            "numero_parte": {"type": "integer", "description": "Número do capítulo/parte."},
            "titulo": {"type": "string", "description": "Título curto e chamativo do episódio."},
            "gancho_inicial": {
                "type": "string",
                "description": "Frase/ação dos primeiros 2 segundos que prende a atenção.",
            },
            "reviravolta": {
                "type": "string",
                "description": "A virada de roteiro (no meio ou no final) que surpreende o espectador.",
            },
            "resumo_capitulo": {
                "type": "string",
                "description": "Resumo de 1-2 frases deste capítulo, usado como contexto para o próximo episódio.",
            },
            "cta_final": {
                "type": "string",
                "description": "Chamada para ação incentivando o espectador a voltar para a próxima parte.",
            },
            "hashtags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Hashtags relevantes para o TikTok, sem o caractere #.",
            },
            "cenas": {
                "type": "array",
                "description": "Sequência de cenas do episódio, em ordem.",
                "items": {
                    "type": "object",
                    "properties": {
                        "descricao_visual": {
                            "type": "string",
                            "description": "Prompt visual detalhado da cena (cenário, enquadramento, ação), reaproveitando a descrição visual fixa do personagem para manter consistência.",
                        },
                        "dialogo": {
                            "type": "string",
                            "description": "Fala do personagem nesta cena (vazio se for cena muda).",
                        },
                        "personagem": {
                            "type": "string",
                            "description": "Nome do personagem que fala/protagoniza a cena.",
                        },
                        "duracao_estimada": {
                            "type": "number",
                            "description": "Duração estimada da cena em segundos.",
                        },
                    },
                    "required": ["descricao_visual", "dialogo", "personagem", "duracao_estimada"],
                },
            },
        },
        "required": [
            "numero_parte",
            "titulo",
            "gancho_inicial",
            "reviravolta",
            "resumo_capitulo",
            "cta_final",
            "hashtags",
            "cenas",
        ],
    },
}


class Cena(BaseModel):
    descricao_visual: str
    dialogo: str
    personagem: str
    duracao_estimada: float


class Roteiro(BaseModel):
    numero_parte: int
    titulo: str
    gancho_inicial: str
    reviravolta: str
    resumo_capitulo: str
    cta_final: str
    hashtags: list[str]
    cenas: list[Cena] = Field(min_length=1)

    @property
    def duracao_total(self) -> float:
        return sum(c.duracao_estimada for c in self.cenas)


def _montar_system_prompt(personagens: list[Personagem]) -> str:
    return f"""Você é roteirista de "novelinhas de IA" para TikTok: dramas curtos, exagerados e viciantes, \
com personagens 3D estilo Pixar/Disney, em formato vertical 9:16.

ELENCO FIXO (mantenha a aparência e a personalidade de cada um EXATAMENTE como descrito abaixo em toda \
`descricao_visual` que envolva esse personagem, para garantir consistência visual entre cenas e episódios):
{personagens_para_prompt(personagens)}

REGRAS DO ROTEIRO:
- Duração total do episódio entre {DURACAO_MIN_SEGUNDOS} e {DURACAO_MAX_SEGUNDOS} segundos.
- Gancho forte nos primeiros 2 segundos (conflito, pergunta ou choque imediato).
- Reviravolta no meio ou no final do episódio.
- Formato de capítulo (ex.: "Parte 3") que termina em suspense, incentivando o espectador a voltar para a \
próxima parte.
- Diálogos curtos e diretos, estilo TikTok (nada de monólogos longos).
- Use APENAS os personagens do elenco fixo.
- Cada `descricao_visual` de cena deve incluir cenário, enquadramento e a aparência do personagem em cena.
- Responda chamando a ferramenta `{_NOME_FERRAMENTA}` com o roteiro completo em português do Brasil."""


def _montar_user_prompt(numero_parte: int, contexto_anterior: str | None) -> str:
    if contexto_anterior is None:
        return (
            f"Gere a Parte {numero_parte}, o episódio de estreia da novelinha. "
            "Apresente o conflito central que vai guiar os próximos capítulos."
        )
    return (
        f"Gere a Parte {numero_parte}, dando continuidade direta ao capítulo anterior.\n"
        f'Resumo do capítulo anterior: "{contexto_anterior}"\n'
        "Avance o conflito e termine com um novo gancho para a próxima parte."
    )


@com_retry(tentativas=4, espera_inicial=2.0, excecoes=(anthropic.APIError, anthropic.APIConnectionError))
def _chamar_claude(system_prompt: str, user_prompt: str) -> dict:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY não configurada. Defina-a no arquivo .env (veja .env.example)."
        )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    resposta = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        tools=[_TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": _NOME_FERRAMENTA},
    )

    for bloco in resposta.content:
        if bloco.type == "tool_use" and bloco.name == _NOME_FERRAMENTA:
            return bloco.input

    raise ValueError("Claude não retornou uma chamada da ferramenta esperada.")


def gerar_roteiro(numero_parte: int | None = None) -> Roteiro:
    personagens = carregar_personagens()
    numero_parte = numero_parte or fila.proximo_numero_parte()
    contexto_anterior = fila.contexto_capitulo_anterior()

    logger.info("Gerando roteiro da Parte %s...", numero_parte)

    system_prompt = _montar_system_prompt(personagens)
    user_prompt = _montar_user_prompt(numero_parte, contexto_anterior)

    bruto = _chamar_claude(system_prompt, user_prompt)

    try:
        roteiro = Roteiro.model_validate(bruto)
    except ValidationError:
        logger.exception("Roteiro retornado pelo Claude não passou na validação: %s", bruto)
        raise

    if roteiro.numero_parte != numero_parte:
        logger.warning(
            "Claude retornou numero_parte=%s, esperado %s. Corrigindo.",
            roteiro.numero_parte,
            numero_parte,
        )
        roteiro.numero_parte = numero_parte

    if not (DURACAO_MIN_SEGUNDOS <= roteiro.duracao_total <= DURACAO_MAX_SEGUNDOS):
        logger.warning(
            "Duração total do roteiro (%.1fs) fora da faixa recomendada (%s-%ss).",
            roteiro.duracao_total,
            DURACAO_MIN_SEGUNDOS,
            DURACAO_MAX_SEGUNDOS,
        )

    logger.info(
        "Roteiro '%s' (Parte %s) gerado com %s cenas, ~%.1fs.",
        roteiro.titulo,
        roteiro.numero_parte,
        len(roteiro.cenas),
        roteiro.duracao_total,
    )
    return roteiro


def salvar_roteiro(roteiro: Roteiro) -> Path:
    caminho = ROTEIROS_DIR / f"parte_{roteiro.numero_parte:03d}.json"
    caminho.write_text(
        json.dumps(roteiro.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    fila.registrar_episodio(
        numero_parte=roteiro.numero_parte,
        titulo=roteiro.titulo,
        resumo_capitulo=roteiro.resumo_capitulo,
        arquivo_roteiro=str(caminho.relative_to(ROTEIROS_DIR.parent.parent)),
    )
    logger.info("Roteiro salvo em %s", caminho)
    return caminho


def gerar_e_salvar_proximo_episodio() -> Path:
    roteiro = gerar_roteiro()
    return salvar_roteiro(roteiro)
