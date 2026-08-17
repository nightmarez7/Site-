"""Etapa 4 do pipeline: montagem final do episódio (moviepy/ffmpeg).

Para cada cena, monta um clipe (imagem estática ou vídeo gerado) com a
narração sincronizada e a legenda queimada por cima (estilo TikTok), depois
concatena tudo, mixa uma música de fundo opcional e exporta o MP4 vertical.
"""

from __future__ import annotations

import random
import textwrap
from pathlib import Path

import numpy as np
from PIL import Image as _PILImage

# moviepy 1.0.3's resize.py calls the Pillow constant PIL.Image.ANTIALIAS, removed in
# Pillow 10+ (renamed to LANCZOS) — restore the alias before moviepy uses it.
if not hasattr(_PILImage, "ANTIALIAS"):
    _PILImage.ANTIALIAS = _PILImage.LANCZOS

from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    afx,
    concatenate_videoclips,
)
from PIL import Image, ImageDraw, ImageFont

from scripts.config import (
    ALTURA_VIDEO,
    FONTE_LEGENDA_PATH,
    LARGURA_VIDEO,
    MEDIA_FINAL_DIR,
    MUSICA_FUNDO_DIR,
    MUSICA_FUNDO_VOLUME,
    TAMANHO_FONTE_LEGENDA,
    VIDEO_FPS,
)
from scripts.geracao_midia import MidiaCena
from scripts.logger import get_logger
from scripts.narracao import NarracaoCena
from scripts.roteiro_generator import Roteiro

logger = get_logger(__name__)

_FONTES_CANDIDATAS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:\\Windows\\Fonts\\arialbd.ttf",
]

_DURACAO_MINIMA_CENA = 1.5


def _carregar_fonte(tamanho: int) -> ImageFont.FreeTypeFont:
    caminhos = [FONTE_LEGENDA_PATH] if FONTE_LEGENDA_PATH else []
    caminhos += _FONTES_CANDIDATAS
    for caminho in caminhos:
        if caminho and Path(caminho).exists():
            return ImageFont.truetype(caminho, tamanho)
    logger.warning(
        "Nenhuma fonte TTF encontrada (defina FONTE_LEGENDA_PATH no .env); "
        "usando fonte padrão do Pillow, a legenda vai ficar pequena/feia."
    )
    return ImageFont.load_default()


def _gerar_overlay_legenda(texto: str) -> np.ndarray:
    """Renderiza a legenda como PNG transparente (texto branco, contorno preto), estilo TikTok."""
    img = Image.new("RGBA", (LARGURA_VIDEO, ALTURA_VIDEO), (0, 0, 0, 0))
    if not texto.strip():
        return np.array(img)

    draw = ImageDraw.Draw(img)
    fonte = _carregar_fonte(TAMANHO_FONTE_LEGENDA)

    linhas = textwrap.wrap(texto, width=22)
    altura_linha = TAMANHO_FONTE_LEGENDA * 1.25
    altura_bloco = altura_linha * len(linhas)
    y = ALTURA_VIDEO - altura_bloco - 260  # terço inferior, acima da área de UI do TikTok

    contorno = max(2, TAMANHO_FONTE_LEGENDA // 18)
    for linha in linhas:
        bbox = draw.textbbox((0, 0), linha, font=fonte, stroke_width=contorno)
        largura_linha = bbox[2] - bbox[0]
        x = (LARGURA_VIDEO - largura_linha) / 2
        draw.text(
            (x, y),
            linha,
            font=fonte,
            fill="white",
            stroke_width=contorno,
            stroke_fill="black",
        )
        y += altura_linha

    return np.array(img)


def _escolher_musica_fundo() -> Path | None:
    faixas = list(MUSICA_FUNDO_DIR.glob("*.mp3")) + list(MUSICA_FUNDO_DIR.glob("*.wav"))
    if not faixas:
        logger.info(
            "Nenhuma música de fundo em %s — exportando sem trilha. "
            "Coloque um mp3/wav de banco livre de direitos nessa pasta para ativar.",
            MUSICA_FUNDO_DIR,
        )
        return None
    return random.choice(faixas)


def _montar_clipe_da_cena(dialogo: str, midia: MidiaCena, narracao: NarracaoCena, duracao_padrao: float):
    audio_clip = AudioFileClip(str(narracao.caminho)) if narracao.caminho else None
    duracao = max(audio_clip.duration if audio_clip else duracao_padrao, _DURACAO_MINIMA_CENA)

    if midia.tipo == "video":
        clipe_base = VideoFileClip(str(midia.caminho))
        clipe_base = clipe_base.loop(duration=duracao) if clipe_base.duration < duracao else clipe_base.subclip(0, duracao)
    else:
        clipe_base = ImageClip(str(midia.caminho)).set_duration(duracao)

    clipe_base = clipe_base.resize(newsize=(LARGURA_VIDEO, ALTURA_VIDEO)).set_position("center")

    legenda = ImageClip(_gerar_overlay_legenda(dialogo)).set_duration(duracao).set_position("center")

    cena_final = CompositeVideoClip([clipe_base, legenda], size=(LARGURA_VIDEO, ALTURA_VIDEO))
    if audio_clip:
        cena_final = cena_final.set_audio(audio_clip)
    return cena_final


def montar_video_final(
    roteiro: Roteiro, midias: list[MidiaCena], narracoes: list[NarracaoCena]
) -> Path:
    if not (len(roteiro.cenas) == len(midias) == len(narracoes)):
        raise ValueError("Roteiro, mídias e narrações precisam ter o mesmo número de cenas.")

    clipes = [
        _montar_clipe_da_cena(cena.dialogo, midia, narracao, cena.duracao_estimada)
        for cena, midia, narracao in zip(roteiro.cenas, midias, narracoes)
    ]
    video_final = concatenate_videoclips(clipes, method="compose")

    caminho_musica = _escolher_musica_fundo()
    if caminho_musica:
        musica = AudioFileClip(str(caminho_musica)).fx(afx.audio_loop, duration=video_final.duration)
        musica = musica.volumex(MUSICA_FUNDO_VOLUME)
        audio_final = (
            CompositeAudioClip([video_final.audio, musica]) if video_final.audio else musica
        )
        video_final = video_final.set_audio(audio_final)

    caminho_saida = MEDIA_FINAL_DIR / f"parte_{roteiro.numero_parte:03d}.mp4"
    video_final.write_videofile(
        str(caminho_saida),
        fps=VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        logger=None,
    )
    logger.info("Vídeo final exportado: %s (%.1fs)", caminho_saida, video_final.duration)
    return caminho_saida
