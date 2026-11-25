"""Coleta até 100 comentários (os mais relevantes) de cada Short que tem comentário.

API oficial (commentThreads, 1 unidade por vídeo). Comentário do próprio canal fica de fora.
Retomável: uma linha por vídeo em data/comentarios.jsonl. Não escreve no banco.
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from mpe.ambiente import DADOS, chave
from mpe.amostra import carregar, ranquear
from mpe.banco import abrir
from mpe.youtube import BASE

saida = DADOS / "comentarios.jsonl"
feitos = set()
if saida.exists():
    feitos = {json.loads(x)["id"] for x in saida.read_text().splitlines() if x.strip()}
banco = abrir()
base = ranquear(carregar(banco))
banco.close()
alvo = base[(base["comentarios"] >= 1) & ~base["id"].isin(feitos)]
pendentes = list(zip(alvo["id"], alvo["canal_id"], strict=True))
print(len(feitos), "feitos;", len(pendentes), "na fila", flush=True)
http, cabecalho = httpx.Client(timeout=60), {"X-goog-api-key": chave("YOUTUBE_API_KEY")}


def buscar(id_, canal_id):
    r = http.get(
        f"{BASE}/commentThreads",
        headers=cabecalho,
        params={
            "part": "snippet", "videoId": id_, "maxResults": 100, "order": "relevance",
            "textFormat": "plainText",
        },
    )  # fmt: skip
    if r.status_code == 403 and "commentsDisabled" in r.text:
        return id_, []
    r.raise_for_status()
    itens = []
    for t in r.json().get("items", []):
        c = t["snippet"]["topLevelComment"]["snippet"]
        if (c.get("authorChannelId") or {}).get("value") == canal_id:
            continue
        itens.append(
            {"cid": t["id"], "texto": c["textDisplay"][:500], "likes": c.get("likeCount", 0)}
        )
    return id_, itens


ok = ruim = 0
with ThreadPoolExecutor(6) as pool, saida.open("a") as arquivo:
    futuros = [pool.submit(buscar, i, c) for i, c in pendentes]
    for f in as_completed(futuros):
        try:
            id_, itens = f.result()
        except Exception as e:  # noqa: BLE001
            ruim += 1
            print("falha", str(e)[:120], flush=True)
            continue
        arquivo.write(json.dumps({"id": id_, "comentarios": itens}, ensure_ascii=False) + "\n")
        ok += 1
print("fim", ok, "ok", ruim, "falhas")
