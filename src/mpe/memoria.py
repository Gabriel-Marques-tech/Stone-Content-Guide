"""Memória de erros: o que os roteiros anteriores mais deixaram de fora vira aviso no próximo.

Não há tabela própria: a memória é o registro de execuções. Cada pedido guarda o que a segunda
leitura não achou no primeiro rascunho. Só entram os roteiros mais recentes, então o aviso some
quando o erro para de acontecer. Aprende a seguir os padrões medidos, não a gerar mais resultado.
"""

import json

from mpe.contrato import Padrao

JANELA = 40  # roteiros mais recentes do mesmo objetivo
MIN_ROTEIROS, MIN_FALTAS, MIN_TAXA = 10, 3, 0.10


def _faltas(saida: dict, etapas: list[dict]) -> list[tuple[set[str], set[str]]]:
    """(padrões conferidos, padrões que faltaram) em cada rascunho da execução."""
    conferidos = {p["atributo"] for p in saida.get("patterns") or []}
    verificar = next((e for e in etapas if e["etapa"] == "verificar"), {})
    if "faltas" in verificar:
        return [(conferidos, set(f)) for f in verificar["faltas"] if f is not None]
    # execução anterior à memória: o que sobrou no criativo; lista vazia pode ser leitura que falhou
    return [
        (conferidos, conferidos - set(c["padroes"]))
        for c in saida.get("creatives") or []
        if c.get("padroes")
    ]


def lembrar(banco, objetivo: str, padroes: list[Padrao]) -> list[dict]:
    """Erros repetidos, do mais ao menos frequente: {atributo, conselho, faltas, roteiros}."""
    if not banco.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'execucoes'"
    ).fetchone():
        return []
    linhas = banco.execute(
        "SELECT entrada, saida, etapas FROM execucoes ORDER BY quando DESC LIMIT 200"
    ).fetchall()
    roteiros: list[tuple[set[str], set[str]]] = []
    for entrada, saida, etapas in linhas:
        e = json.loads(entrada)
        if e["mode"] != "gerar_criativo" or e.get("objetivo", "engajamento") != objetivo:
            continue
        roteiros += _faltas(json.loads(saida), json.loads(etapas))
        if len(roteiros) >= JANELA:
            break
    avisos = []
    for p in padroes:
        vistos = [falta for conferidos, falta in roteiros[:JANELA] if p.atributo in conferidos]
        faltou = sum(p.atributo in f for f in vistos)
        if len(vistos) >= MIN_ROTEIROS and faltou >= MIN_FALTAS:
            if faltou / len(vistos) >= MIN_TAXA:
                avisos.append(
                    {"atributo": p.atributo, "conselho": p.conselho, "faltas": faltou,
                     "roteiros": len(vistos)}
                )  # fmt: skip
    return sorted(avisos, key=lambda a: -a["faltas"] / a["roteiros"])
