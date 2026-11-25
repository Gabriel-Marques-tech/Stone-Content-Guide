"""Chaves e caminhos. As chaves vêm do .env local ou, na falta dele, do .env do Galaxies."""

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
ENV_GALAXIES = RAIZ.parent / "Galaxies" / ".env"
DADOS = Path(os.environ.get("MPE_DADOS", RAIZ / "data"))


def chave(nome: str) -> str:
    for arquivo in (RAIZ / ".env", ENV_GALAXIES):
        if arquivo.exists():
            load_dotenv(arquivo)
    valor = os.environ.get(nome)
    if not valor:
        raise RuntimeError(f"falta a variável {nome} no .env")
    return valor


# Um só avaliador para a base inteira: categorias de outro modelo são ignoradas nas consultas.
MODELO = os.environ.get("MPE_GEMINI", "gemini-3.5-flash-lite")
