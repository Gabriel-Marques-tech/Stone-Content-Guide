"""Concordância entre os dois caminhos da fala nos posts que ambos leram.

Gemini (assiste ao vídeo) contra Whisper + DeepSeek (transcrição e quadros). Mede acordo entre
modelos, não acerto. Grava data/concordancia_fala.csv.
"""

import json

import pandas as pd

from mpe.ambiente import DADOS, MODELO
from mpe.banco import abrir
from mpe.motor import BOOLEANOS, CATEGORICOS
from mpe.validacao import kappa

banco = abrir()
video = {
    i: json.loads(r)
    for i, r in banco.execute(
        "SELECT post_id, rubrica FROM categorias WHERE modelo = ?", [MODELO]
    ).fetchall()
}
linhas = [json.loads(x) for x in (DADOS / "fala_transcricao.jsonl").read_text().splitlines() if x]
texto = {x["id"]: x["rubrica"] for x in linhas if x["com_fala"]}
comuns = sorted(set(video) & set(texto))
tabela = []
for campo in [*CATEGORICOS, *BOOLEANOS]:
    a, b = [str(video[i][campo]) for i in comuns], [str(texto[i][campo]) for i in comuns]
    acordo = sum(x == y for x, y in zip(a, b, strict=True)) / len(comuns)
    tabela.append({"campo": campo, "n": len(comuns), "acordo": acordo, "kappa": kappa(a, b)})
r = pd.DataFrame(tabela).sort_values("kappa", ascending=False)
r.to_csv(DADOS / "concordancia_fala.csv", index=False)
print(r.round(2).to_string(index=False))
