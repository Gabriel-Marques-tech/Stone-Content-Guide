"""Avalia um rascunho de criativo. Uso: avaliar.py [engajamento|interesse] < rascunho.txt"""

import os
import sys

os.environ.setdefault("MPE_FEITA_MODELO", "deepseek/deepseek-v4.1-flash-1017")

from mpe.avaliador import avaliar  # noqa: E402
from mpe.banco import abrir  # noqa: E402
from mpe.consulta import base_completa  # noqa: E402
from mpe.feita import llm  # noqa: E402

objetivo = sys.argv[1] if len(sys.argv) > 1 else "engajamento"
a = avaliar(base_completa(abrir()), llm(), sys.stdin.read(), objetivo)
print(f"objetivo: {a.objetivo} | aderência: {a.aderencia:.0%} ({len(a.sinais)} sinais)")
for s in a.sinais:
    marca = "ok " if s.alinhado else "!! "
    exemplo = f" | ex.: {s.exemplo.link}" if s.exemplo and not s.alinhado else ""
    print(
        f"  {marca}{s.atributo}: grupo {s.no_grupo:.0%}, resto {s.no_resto:.0%}, "
        f"rascunho {'tem' if s.rascunho_tem else 'não tem'}{exemplo}"
    )
print("\nAjustes:")
for linha in a.ajustes:
    print(" -", linha)
print("\n" + a.aviso)
