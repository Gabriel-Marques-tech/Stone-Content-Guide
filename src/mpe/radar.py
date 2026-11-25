"""Radar: o que ganha e o que perde força com o tempo.

A base é cortada em três períodos com o mesmo número de posts e o topo é refeito dentro de cada um,
para o post antigo não competir com o novo. Em cada período: frequência no topo, com peso igual por
canal, menos a do resto. Só campos lidos na base inteira (quadros e duração).

Só é `subindo` ou `caindo` o que muda na mesma direção na base e sem os posts fora de negócio, com
o intervalo de 95% da mudança (reamostrando canais) longe do zero. Mudança grande sem essa certeza
é `indicio_alta` ou `indicio_queda`. É associação observada, não causa.
"""

from typing import Literal

import numpy as np
import pandas as pd

from mpe.consulta import cenarios
from mpe.motor import matriz
from mpe.rubrica import CAMPOS_QUADROS

PERIODOS = 3
MIN_MUDANCA = 0.08  # 8 pontos, o mesmo corte das comparações
MIN_POSTS, MIN_CANAIS, MIN_OCORRENCIAS = 40, 10, 20
REAMOSTRAS = 1000

Tendencia = Literal["subindo", "caindo", "indicio_alta", "indicio_queda", "sem_sinal"]


def _periodos(df: pd.DataFrame) -> list[pd.DataFrame]:
    d = df[df["categorizado"]].sort_values("publicado_em").reset_index(drop=True)
    saida = []
    for posicoes in np.array_split(np.arange(len(d)), PERIODOS):
        p = d.iloc[posicoes].reset_index(drop=True)
        corte = int(np.ceil(len(p) * 0.1))
        p["topo_periodo"] = p["engajamento"].rank(ascending=False, method="first") <= corte
        saida.append(p)
    return saida


def _colunas(x: pd.DataFrame) -> list[str]:
    return [
        c for c in x.columns
        if (c.split("=")[0] in CAMPOS_QUADROS or c.startswith("duracao_faixa"))
        and not c.startswith("tema_principal")
    ]  # fmt: skip


def _por_canal(p: pd.DataFrame, x: pd.DataFrame, colunas: list[str]):
    """Médias do topo por canal (uma linha por canal) e a média do resto."""
    topo = p["topo_periodo"].to_numpy()
    m = x.reindex(columns=colunas, fill_value=0.0)
    return m[topo].groupby(p["handle"][topo].to_numpy()).mean(), m[~topo].mean()


def _medir(df: pd.DataFrame, semente: int) -> pd.DataFrame:
    """Uma linha por característica: diferença em cada período e intervalo da mudança."""
    ps = _periodos(df)
    xs = [matriz(p) for p in ps]
    colunas = sorted(set().union(*(_colunas(x) for x in xs)))
    partes = [_por_canal(p, x, colunas) for p, x in zip(ps, xs, strict=True)]
    if any(p["topo_periodo"].sum() < MIN_POSTS for p in ps):
        return pd.DataFrame()
    if any(len(canais) < MIN_CANAIS for canais, _ in partes):
        return pd.DataFrame()
    difs = np.array([(canais.mean() - resto).to_numpy(float) for canais, resto in partes])
    rng = np.random.default_rng(semente)

    def medias(k: int) -> np.ndarray:
        v = partes[k][0].to_numpy(float)
        return v[rng.integers(0, len(v), (REAMOSTRAS, len(v)))].mean(axis=1)

    ponta = medias(PERIODOS - 1) - partes[-1][1].to_numpy(float)
    inicio = medias(0) - partes[0][1].to_numpy(float)
    baixo, alto = np.percentile(ponta - inicio, [2.5, 97.5], axis=0)
    total = sum(x.reindex(columns=colunas, fill_value=0.0).sum() for x in xs)
    t = pd.DataFrame(difs.T, index=colunas, columns=[f"p{i + 1}" for i in range(PERIODOS)])
    t["mudanca"], t["baixo"], t["alto"] = difs[-1] - difs[0], baixo, alto
    return t[total.reindex(t.index) >= MIN_OCORRENCIAS].dropna()


def classificar(medidas: list[tuple[float, float, float]]) -> Tendencia:
    """`medidas`: (mudança, baixo, alto) em cada recorte. Todos precisam concordar."""
    if not medidas or any(abs(m) < MIN_MUDANCA for m, _, _ in medidas):
        return "sem_sinal"
    if len({m > 0 for m, _, _ in medidas}) > 1:
        return "sem_sinal"
    sobe = medidas[0][0] > 0
    if all(b > 0 or a < 0 for _, b, a in medidas):
        return "subindo" if sobe else "caindo"
    return "indicio_alta" if sobe else "indicio_queda"


def radar(df: pd.DataFrame, semente: int = 0) -> list[dict]:
    """Uma linha por característica, da maior mudança para a menor. Vazio se faltar dado."""
    recortes = {n: d for n, d in cenarios(df).items() if n in ("base", "sem_posts")}
    tabelas = [_medir(d, semente) for d in recortes.values()]
    if not tabelas or any(t.empty for t in tabelas):
        return []
    base, saida = tabelas[0], []
    for atributo in base.index:
        if not all(atributo in t.index for t in tabelas):
            continue
        medidas = [tuple(t.loc[atributo, ["mudanca", "baixo", "alto"]]) for t in tabelas]
        r = base.loc[atributo]
        saida.append(
            {
                "atributo": atributo,
                "periodos": [round(float(r[f"p{i + 1}"]), 3) for i in range(PERIODOS)],
                "mudanca": round(float(r["mudanca"]), 3),
                "ic95": [round(float(r["baixo"]), 3), round(float(r["alto"]), 3)],
                "tendencia": classificar(medidas),
            }
        )
    return sorted(saida, key=lambda r: -abs(r["mudanca"]))


def datas(df: pd.DataFrame) -> list[tuple[str, str]]:
    return [
        (p["publicado_em"].min().strftime("%m/%Y"), p["publicado_em"].max().strftime("%m/%Y"))
        for p in _periodos(df)
    ]


def tendencias(df: pd.DataFrame) -> dict[str, Tendencia]:
    return {r["atributo"]: r["tendencia"] for r in radar(df)}
