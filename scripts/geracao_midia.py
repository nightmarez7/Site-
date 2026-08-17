"""Etapa 2 do pipeline: geração de imagem/vídeo por cena, com consistência de personagem.

Para cada personagem, gera (e cacheia em disco) uma imagem de referência a partir
da `descricao_visual` fixa. Toda cena desse personagem usa essa referência como
condicionamento visual na chamada à Kling, para manter a aparência consistente
entre cenas e entre episódios.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from scripts.config import ALTURA_VIDEO, LARGURA_VIDEO, MEDIA_RAW_DIR, MEDIA_RAW_PERSONAGENS_DIR, MIDIA_TIPO
from scripts.logger import get_logger
from scripts.personagens import Personagem, carregar_personagens
from scripts.providers import kling
from scripts.roteiro_generator import Roteiro

logger = get_logger(__name__)


@dataclass
class MidiaCena:
    indice: int
    personagem: str
    tipo: str  # "imagem" ou "video"
    caminho: Path


def _redimensionar(caminho: Path) -> None:
    with Image.open(caminho) as img:
        if img.size != (LARGURA_VIDEO, ALTURA_VIDEO):
            img.convert("RGB").resize((LARGURA_VIDEO, ALTURA_VIDEO), Image.LANCZOS).save(caminho)


def _obter_ou_gerar_referencia(personagem: Personagem) -> Path:
    caminho = MEDIA_RAW_PERSONAGENS_DIR / f"{personagem.id}.png"
    if caminho.exists():
        logger.info("Usando referência visual existente de %s: %s", personagem.nome, caminho)
        return caminho

    logger.info("Gerando imagem de referência para %s...", personagem.nome)
    prompt = (
        f"{personagem.descricao_visual}, personagem 3D estilo Pixar/Disney, "
        "corpo inteiro, fundo neutro, iluminação de estúdio, pose neutra de referência de personagem"
    )
    kling.gerar_imagem(prompt, caminho)
    _redimensionar(caminho)
    return caminho


def _mapa_personagens(roteiro: Roteiro) -> dict[str, Personagem]:
    elenco = {p.nome: p for p in carregar_personagens()}
    faltando = {cena.personagem for cena in roteiro.cenas} - elenco.keys()
    if faltando:
        raise ValueError(f"Roteiro cita personagens fora do elenco fixo: {faltando}")
    return elenco


def gerar_midia_do_roteiro(roteiro: Roteiro) -> list[MidiaCena]:
    elenco = _mapa_personagens(roteiro)
    pasta_episodio = MEDIA_RAW_DIR / f"parte_{roteiro.numero_parte:03d}"
    pasta_episodio.mkdir(parents=True, exist_ok=True)

    resultado: list[MidiaCena] = []
    for indice, cena in enumerate(roteiro.cenas, start=1):
        personagem = elenco[cena.personagem]
        referencia = _obter_ou_gerar_referencia(personagem)
        prompt_cena = f"{cena.descricao_visual}. Personagem: {personagem.descricao_visual}."

        if MIDIA_TIPO == "video":
            caminho_base = pasta_episodio / f"cena_{indice:02d}_base.png"
            kling.gerar_imagem(prompt_cena, caminho_base, imagem_referencia=referencia)
            _redimensionar(caminho_base)

            caminho_video = pasta_episodio / f"cena_{indice:02d}.mp4"
            kling.gerar_video_a_partir_de_imagem(prompt_cena, caminho_base, caminho_video)
            midia = MidiaCena(indice, personagem.nome, "video", caminho_video)
        else:
            caminho_imagem = pasta_episodio / f"cena_{indice:02d}.png"
            kling.gerar_imagem(prompt_cena, caminho_imagem, imagem_referencia=referencia)
            _redimensionar(caminho_imagem)
            midia = MidiaCena(indice, personagem.nome, "imagem", caminho_imagem)

        resultado.append(midia)
        logger.info(
            "Cena %s/%s (%s) pronta: %s", indice, len(roteiro.cenas), personagem.nome, midia.caminho
        )

    return resultado
