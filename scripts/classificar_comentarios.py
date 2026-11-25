"""Classifica os comentários coletados (data/comentarios.jsonl) pelo DeepSeek, em lotes.

Retomável: uma linha por comentário em data/comentarios_classe.jsonl.
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

os.environ.setdefault("MPE_FEITA_MODELO", "deepseek/deepseek-v4.1-flash-1017")

from mpe.ambiente import DADOS  # noqa: E402
from mpe.comentarios import classificar  # noqa: E402
from mpe.feita import Feita  # noqa: E402

LOTE = 40
saida = DADOS / "comentarios_classe.jsonl"
feitos = set()
if saida.exists():
    feitos = {json.loads(x)["cid"] for x in saida.read_text().splitlines() if x.strip()}
videos = [json.loads(x) for x in (DADOS / "comentarios.jsonl").read_text().splitlines() if x]
fila = [
    (v["id"], c["cid"], c["texto"])
    for v in videos
    for c in v["comentarios"]
    if c["cid"] not in feitos and c["texto"].strip()
]
lotes = [fila[i : i + LOTE] for i in range(0, len(fila), LOTE)]
print(len(feitos), "feitos;", len(fila), "na fila em", len(lotes), "lotes", flush=True)
llm = Feita(por_minuto=120)
ok = ruim = 0
with ThreadPoolExecutor(6) as pool, saida.open("a") as arquivo:
    futuros = {pool.submit(classificar, llm, [t for _, _, t in lote]): lote for lote in lotes}
    for f in as_completed(futuros):
        lote = futuros[f]
        try:
            classes = f.result()
        except Exception as e:  # noqa: BLE001
            ruim += 1
            print("falha", str(e)[:150], flush=True)
            continue
        for (post, cid, _), classe in zip(lote, classes, strict=True):
            if classe:
                linha = {"id": post, "cid": cid, "classe": classe}
                arquivo.write(json.dumps(linha, ensure_ascii=False) + "\n")
        arquivo.flush()
        ok += 1
print("fim", ok, "lotes ok", ruim, "falhas")
