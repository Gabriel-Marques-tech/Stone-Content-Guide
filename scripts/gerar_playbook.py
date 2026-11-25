"""Gera docs/playbook.md. Os números saem da base; o agente redige os criativos.

Com `--reusar`, os criativos vêm da última execução gravada de cada tema, sem chamar o LLM: serve
para atualizar tabelas e recomendações sem trocar os textos já revisados.
"""

import sys

from mpe.agente import Saida, executar
from mpe.ambiente import RAIZ
from mpe.banco import abrir
from mpe.consulta import base_completa
from mpe.feita import llm
from mpe.playbook import OBJETIVO, PEDIDO, TEMAS, montar

ULTIMA = """SELECT saida FROM execucoes WHERE json_extract_string(entrada, '$.query') = ?
            AND json_extract_string(entrada, '$.mode') = 'gerar_criativo'
            ORDER BY quando DESC LIMIT 1"""

reusar = "--reusar" in sys.argv
banco = abrir()
df = base_completa(banco)
modelo = None if reusar else llm()
criativos = []
for tema in TEMAS:
    pedido = PEDIDO.format(tema=tema)
    if reusar:
        linha = banco.execute(ULTIMA, [pedido]).fetchone()
        if linha is None:
            raise SystemExit(f"sem execução gravada para: {tema}. Rode sem --reusar.")
        saida = Saida.model_validate_json(linha[0])
    else:
        saida = executar(
            banco,
            modelo,
            {
                "mode": "gerar_criativo",
                "query": pedido,
                "objetivo": OBJETIVO.get(tema, "contato"),
            },
            df,
        )
    print(tema, len(saida.creatives), saida.confidence_flag)
    criativos.append((tema, saida))
docs = RAIZ / "docs"
docs.mkdir(exist_ok=True)
humano = docs / "recomendacoes-stone.md"  # escrito por gente, a partir das tabelas
texto = montar(banco, df, criativos, humano.read_text() if humano.exists() else "")
(docs / "playbook.md").write_text(texto)
