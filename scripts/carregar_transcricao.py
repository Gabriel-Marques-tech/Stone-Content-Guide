"""Carrega data/fala_transcricao.jsonl em categorias_transcricao. Pode rodar várias vezes.

Vídeo sem fala detectada fica de fora: sem fala, os campos de fala não têm o que ler.
"""

import json
from datetime import UTC, datetime

from mpe.ambiente import DADOS
from mpe.banco import abrir

banco, agora = abrir(), datetime.now(UTC).replace(tzinfo=None)
linhas = [json.loads(x) for x in (DADOS / "fala_transcricao.jsonl").read_text().splitlines() if x]
com_fala = [x for x in linhas if x["com_fala"]]
banco.executemany(
    "INSERT OR REPLACE INTO categorias_transcricao VALUES (?, ?, ?, ?)",
    [[x["id"], x["modelo"], json.dumps(x["rubrica"], ensure_ascii=False), agora] for x in com_fala],
)
total = banco.execute("SELECT count(*) FROM categorias_transcricao").fetchone()[0]
print(total, "posts lidos por transcrição;", len(linhas) - len(com_fala), "sem fala, de fora")
