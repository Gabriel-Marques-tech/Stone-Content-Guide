"""Carrega data/quadros_base.jsonl em categorias_quadros. Pode rodar várias vezes."""

import json
from datetime import UTC, datetime

from mpe.ambiente import DADOS
from mpe.banco import abrir

banco, agora = abrir(), datetime.now(UTC).replace(tzinfo=None)
linhas = [json.loads(x) for x in (DADOS / "quadros_base.jsonl").read_text().splitlines() if x]
banco.executemany(
    "INSERT OR REPLACE INTO categorias_quadros VALUES (?, ?, ?, ?)",
    [[x["id"], x["modelo"], json.dumps(x["rubrica"], ensure_ascii=False), agora] for x in linhas],
)
print(banco.execute("SELECT count(*) FROM categorias_quadros").fetchone()[0], "posts com quadros")
