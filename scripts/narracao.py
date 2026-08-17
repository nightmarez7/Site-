"""Etapa 3 do pipeline: narração/diálogo de cada cena via TTS (ElevenLabs).

Cada personagem tem voz e configuração de emoção fixas (data/personagens.json),
mantendo a voz consistente entre cenas e episódios. Cenas com `dialogo` vazio
(cenas mudas) não geram áudio.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.config import MEDIA_RAW_DIR
from scripts.logger import get_logger
from scripts.personagens import Personagem, carregar_personagens
from scripts.providers import elevenlabs
from scripts.roteiro_generator import Roteiro

logger = get_logger(__name__)


@dataclass
class NarracaoCena:
    indice: int
    personagem: str
    caminho: Path | None  # None quando a cena não tem diálogo


def gerar_narracao_do_roteiro(roteiro: Roteiro) -> list[NarracaoCena]:
    elenco = {p.nome: p for p in carregar_personagens()}
    faltando = {cena.personagem for cena in roteiro.cenas} - elenco.keys()
    if faltando:
        raise ValueError(f"Roteiro cita personagens fora do elenco fixo: {faltando}")

    pasta_episodio = MEDIA_RAW_DIR / f"parte_{roteiro.numero_parte:03d}"
    pasta_episodio.mkdir(parents=True, exist_ok=True)

    resultado: list[NarracaoCena] = []
    for indice, cena in enumerate(roteiro.cenas, start=1):
        if not cena.dialogo.strip():
            logger.info("Cena %s (%s) sem diálogo, pulando narração.", indice, cena.personagem)
            resultado.append(NarracaoCena(indice, cena.personagem, None))
            continue

        personagem: Personagem = elenco[cena.personagem]
        caminho = pasta_episodio / f"cena_{indice:02d}.mp3"
        elevenlabs.gerar_narracao(
            texto=cena.dialogo,
            voz_id=personagem.voz_id,
            destino=caminho,
            estabilidade=personagem.voz_estabilidade,
            exagero=personagem.voz_exagero,
            similaridade=personagem.voz_similaridade,
        )
        resultado.append(NarracaoCena(indice, cena.personagem, caminho))

    return resultado
