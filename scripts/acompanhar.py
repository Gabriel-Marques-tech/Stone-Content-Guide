"""Lê os Shorts acompanhados com leitura vencida. Para o cron, se a plataforma não ficar no ar:

0 */6 * * * cd <projeto> && uv run python scripts/acompanhar.py
"""

from mpe import acompanhamento
from mpe.ambiente import chave
from mpe.feita import llm
from mpe.youtube import YouTube

print(acompanhamento.rodar_vencidos(YouTube(chave("YOUTUBE_API_KEY")), llm), "vídeos lidos")
