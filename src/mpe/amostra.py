"""Ranking do TAPI e amostra do motor. Puro: recebe e devolve DataFrames.

- top_tapi: 10% superiores da base em (curtidas + comentários) ÷ seguidores.
- par_motor: em cada perfil, os 8 de maior engajamento ('top') e 8 sorteados do resto. Dentro de
  um perfil o divisor é constante, então a ordem é a mesma da métrica do TAPI.
- metade: perfis sorteados entre 'explora' e 'confirma', estratificados por segmento.
"""

import numpy as np
import pandas as pd

MIN_POSTS = 20
POR_GRUPO = 8
SEMENTE = 20261123


def carregar(banco) -> pd.DataFrame:
    return banco.execute(
        """
        SELECT p.*, c.handle, c.titulo AS canal, c.inscritos, c.perfil, c.segmento
        FROM posts p JOIN canais c ON c.id = p.canal_id
        """
    ).df()


def ranquear(posts: pd.DataFrame, fracao: float = 0.10) -> pd.DataFrame:
    """Só entram posts com curtidas, comentários e inscritos públicos."""
    df = posts.dropna(subset=["likes", "comentarios", "inscritos"]).copy()
    df = df[df["inscritos"] > 0]
    df["engajamento"] = (df["likes"] + df["comentarios"]) / df["inscritos"]
    df = df.sort_values(["engajamento", "id"], ascending=[False, True]).reset_index(drop=True)
    n_top = int(np.ceil(len(df) * fracao))
    df["posicao"] = np.arange(1, len(df) + 1)
    df["top_tapi"] = df["posicao"] <= n_top
    return df


def amostrar(ranking: pd.DataFrame, semente: int = SEMENTE) -> pd.DataFrame:
    rng = np.random.default_rng(semente)
    df = ranking.copy()
    df["par_motor"], df["metade"] = None, None
    contagem = df.groupby("handle")["id"].size()
    perfis = sorted(contagem[contagem >= MIN_POSTS].index)
    for handle in perfis:
        do_canal = df[df["handle"] == handle].sort_values(
            ["engajamento", "id"], ascending=[False, True]
        )
        topo, resto = do_canal.index[:POR_GRUPO], do_canal.index[POR_GRUPO:]
        df.loc[topo, "par_motor"] = "top"
        df.loc[rng.choice(resto, POR_GRUPO, replace=False), "par_motor"] = "resto"
    lado = 0  # continua alternando entre segmentos: as metades diferem em no máximo 1 perfil
    segmentos = df[df["handle"].isin(perfis)].drop_duplicates("handle").set_index("handle")
    for _, grupo in segmentos.groupby("segmento"):
        for handle in rng.permutation(sorted(grupo.index)):
            df.loc[df["handle"] == handle, "metade"] = ("explora", "confirma")[lado % 2]
            lado += 1
    return df


def fila(amostra: pd.DataFrame, semente: int = SEMENTE) -> list[str]:
    """Intercala top do TAPI e pares do motor: se a cota acabar, os dois ficam parciais."""
    rng = np.random.default_rng(semente)
    tapi = list(rng.permutation(amostra.loc[amostra["top_tapi"], "id"]))
    motor = list(rng.permutation(amostra.loc[amostra["par_motor"].notna(), "id"]))
    vistos, ordem = set(), []
    for i in range(max(len(tapi), len(motor))):
        for lista in (tapi, motor):
            if i < len(lista) and lista[i] not in vistos:
                vistos.add(lista[i])
                ordem.append(str(lista[i]))
    return ordem


def fila_por_perfil(amostra: pd.DataFrame, feitos: set[str], semente: int = SEMENTE) -> list[str]:
    """Fila para cota curta: fecha um perfil do motor por vez, depois segue a fila normal.

    Um perfil só entra no teste com top e resto avaliados, então espalhar poucas chamadas por
    todos os perfis não rende nada. A ordem usa só o que falta avaliar, nunca a resposta.
    """
    motor = amostra[amostra["par_motor"].notna() & ~amostra["id"].isin(feitos)]
    falta = motor.groupby("handle").size()
    lados = [
        sorted(motor.loc[motor["metade"] == m, "handle"].unique(), key=lambda h: (falta[h], h))
        for m in ("explora", "confirma")
    ]
    lados.sort(key=lambda lado: falta[lado[0]] if lado else 0)  # o mais adiantado abre a fila
    ordem = []
    for i in range(max(map(len, lados), default=0)):
        for lado in lados:
            if i < len(lado):
                do_perfil = motor[motor["handle"] == lado[i]].sort_values("id")
                vez = do_perfil.groupby("par_motor").cumcount()
                ordem += list(do_perfil.assign(vez=vez).sort_values(["vez", "par_motor"])["id"])
    vistos = set(ordem)
    return [*map(str, ordem), *(i for i in fila(amostra, semente) if i not in vistos)]
