"""Atualização da base: o que muda nos padrões quando entram vídeos novos.

`fotografar` guarda os padrões firmes e o radar; `comparar` diz o que entrou, saiu ou mudou entre
duas fotos. O histórico fica na tabela `mudancas`.
"""

import json
from datetime import UTC, datetime

from mpe import radar
from mpe.duvidas import GRUPO_DO_OBJETIVO, nome, padroes_firmes

ESQUEMA = "CREATE TABLE IF NOT EXISTS mudancas (quando TIMESTAMP, foto JSON, mudou JSON)"


def fotografar(df) -> dict:
    return {
        "posts": len(df),
        "firmes": {
            o: {p.atributo: [p.no_grupo, p.nos_outros] for p in padroes_firmes(df, o)}
            for o in GRUPO_DO_OBJETIVO
        },
        "radar": radar.tendencias(df),
    }


def comparar(antes: dict, depois: dict) -> list[str]:
    saida = []
    if antes["posts"] != depois["posts"]:
        saida.append(f"base: {antes['posts']} para {depois['posts']} vídeos")
    for objetivo, agora in depois["firmes"].items():
        velho = antes["firmes"].get(objetivo, {})
        saida += [f"{objetivo}: entrou {nome(a)}" for a in agora if a not in velho]
        saida += [f"{objetivo}: caiu {nome(a)}" for a in velho if a not in agora]
        saida += [
            f"{objetivo}: {nome(a)} foi de {velho[a][0]:.0%} x {velho[a][1]:.0%} "
            f"para {agora[a][0]:.0%} x {agora[a][1]:.0%}"
            for a in agora
            if a in velho
            and max(abs(x - y) for x, y in zip(agora[a], velho[a], strict=True)) >= 0.02
        ]
    for a, agora in depois["radar"].items():
        velho = antes["radar"].get(a, "sem_sinal")
        if velho != agora:
            saida.append(f"radar: {nome(a)} passou de {velho} para {agora}")
    return saida


def registrar(banco, foto: dict, mudou: list[str]):
    banco.execute(ESQUEMA)
    banco.execute(
        "INSERT INTO mudancas VALUES (?, ?, ?)",
        [datetime.now(UTC).replace(tzinfo=None), json.dumps(foto), json.dumps(mudou)],
    )
