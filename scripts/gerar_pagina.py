"""Gera docs/painel.html: o relatório visual do projeto, lido do banco. Só leitura.

A plataforma interativa é `uv run mpe-app`; esta página é a versão parada, para enviar ou abrir
sem servidor.
"""

import json
from pathlib import Path

from mpe.ambiente import RAIZ
from mpe.consulta import base_completa
from mpe.painel import abrir_leitura, montar

MODELO = Path(__file__).with_name("pagina_modelo.html")
SAIDA = RAIZ / "docs" / "painel.html"

if __name__ == "__main__":
    banco = abrir_leitura()
    dados = json.dumps(montar(banco, base_completa(banco)), ensure_ascii=False, default=str)
    SAIDA.parent.mkdir(exist_ok=True)
    SAIDA.write_text(MODELO.read_text().replace("__DADOS__", dados.replace("</", "<\\/")))
    print("página em", SAIDA)
