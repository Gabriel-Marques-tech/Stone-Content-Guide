"""Carrega comentários e classes (data/comentarios*.jsonl) na tabela comentarios."""

import json

from mpe.ambiente import DADOS
from mpe.banco import abrir

classes = {}
for linha in (DADOS / "comentarios_classe.jsonl").read_text().splitlines():
    if linha.strip():
        x = json.loads(linha)
        classes[x["cid"]] = x["classe"]
linhas = [
    [c["cid"], v["id"], c["texto"], c["likes"], classes.get(c["cid"])]
    for v in map(json.loads, (DADOS / "comentarios.jsonl").read_text().splitlines())
    for c in v["comentarios"]
]
banco = abrir()
banco.executemany("INSERT OR REPLACE INTO comentarios VALUES (?, ?, ?, ?, ?)", linhas)
print(banco.execute("SELECT classe, count(*) FROM comentarios GROUP BY 1 ORDER BY 2 DESC").fetchall())
