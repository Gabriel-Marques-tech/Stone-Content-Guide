"""Fecha a rubrica de fala nos 10% superiores (o que o TAPI pede), pelo Gemini direto. Retomável."""

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

from mpe.amostra import carregar, ranquear
from mpe.banco import abrir
from mpe.gemini import CotaEsgotada, Gemini
from mpe.rubrica import INSTRUCAO, Rubrica

limite = int(sys.argv[1]) if len(sys.argv) > 1 else None
banco, gemini = abrir(), Gemini()
ranking = ranquear(carregar(banco))
topo = ranking[ranking["top_tapi"]]
textos = topo.set_index("id")[["titulo", "descricao"]]
feitos = {
    i
    for (i,) in banco.execute(
        "SELECT post_id FROM categorias WHERE modelo = ?", [gemini.modelo]
    ).fetchall()
}
pendentes = [i for i in topo["id"] if i not in feitos][:limite]
print(len(topo), "no topo;", len(pendentes), "na fila", flush=True)


def categorizar(id_):
    t, d = textos.loc[id_]
    texto = INSTRUCAO.format(titulo=t, descricao=(d or "")[:500])
    return gemini.json(texto, Rubrica, f"https://www.youtube.com/watch?v={id_}")


ok = ruim = seguidas = 0
with ThreadPoolExecutor(4) as pool:
    futuros = {pool.submit(categorizar, i): i for i in pendentes}
    for f in as_completed(futuros):
        id_, agora = futuros[f], datetime.now(UTC).replace(tzinfo=None)
        if f.cancelled():
            continue
        try:
            r = f.result()
            banco.execute(
                "INSERT OR REPLACE INTO categorias VALUES (?, ?, ?, ?)",
                [id_, gemini.modelo, r.model_dump_json(), agora],
            )
            ok, seguidas = ok + 1, 0
        except Exception as erro:
            ruim, seguidas = ruim + 1, seguidas + 1
            banco.execute("INSERT INTO falhas VALUES (?, ?, ?)", [id_, str(erro)[:400], agora])
            print("falha", id_, str(erro)[:160].replace("\n", " "), flush=True)
            por_dia = isinstance(erro, CotaEsgotada) and "PerDay" in str(erro)
            if por_dia or seguidas >= 10:
                print("COTA ESGOTADA" if por_dia else "DISJUNTOR ABERTO", flush=True)
                for outro in futuros:
                    outro.cancel()
        if (ok + ruim) % 10 == 0:
            print(ok, "ok", ruim, "falhas", flush=True)
print("fim", ok, "ok", ruim, "falhas")
