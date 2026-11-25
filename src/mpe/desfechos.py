"""Consulta de crenças em dois desfechos: alcance (views) e reação (curtidas por view).

Curtidas + comentários somam os dois e escondem o que acontece: vídeo curto alcança mais gente e
recebe menos reação, vídeo longo faz o contrário, e a soma fica parada. Aqui cada característica é
comparada dentro do mesmo perfil, com todos os posts do perfil, uma vez para cada desfecho.

É exploração: roda só na metade 'explora' dos perfis e não substitui o teste único do motor.
"""

import re

import numpy as np
import pandas as pd

from mpe.motor import matriz

MIN_POR_GRUPO = 5  # posts com e sem a característica para o perfil contar
MIN_PERFIS = 8
EFEITO_MINIMO = 0.10  # 10% a mais ou a menos: abaixo disso não muda uma decisão de conteúdo
REAMOSTRAS = 3000
DESFECHOS = ("alcance", "reacao")

_EMOJI = re.compile(r"[\U0001F300-\U0001FAFF☀-➿]")
_CAIXA_ALTA = re.compile(r"\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{4,}\b")
_VOCE = re.compile(r"\b(?:você|voce|seu|sua|teu|tua)\b")
_COMO = re.compile(r"\bcomo\b|passo a passo|aprenda|dica")


def caracteristicas(df: pd.DataFrame) -> pd.DataFrame:
    """A matriz do motor mais o que se lê do título e do horário, que existe para todo post."""
    x = matriz(df)
    titulo = df["titulo"].fillna("")
    sem_tags = titulo.str.replace(r"#\S+", "", regex=True).str.strip()
    hora = pd.to_datetime(df["publicado_em"])
    extras = {
        "titulo_pergunta": titulo.str.contains(r"\?"),
        "titulo_numero": sem_tags.str.contains(r"\d"),
        "titulo_emoji": titulo.map(lambda s: bool(_EMOJI.search(s))),
        "titulo_caixa_alta": sem_tags.map(lambda s: bool(_CAIXA_ALTA.search(s))),
        "titulo_fala_com_voce": titulo.str.lower().map(lambda s: bool(_VOCE.search(s))),
        "titulo_ensina": titulo.str.lower().map(lambda s: bool(_COMO.search(s))),
        "titulo_curto": sem_tags.str.len() < 40,
        "titulo_3_hashtags": titulo.str.count("#") >= 3,
        "postado_fim_de_semana": hora.dt.day_of_week >= 5,
        "postado_a_noite": ((hora.dt.hour - 3) % 24).between(18, 23),  # horário de Brasília
    }
    return x.assign(**{nome: serie.astype(float) for nome, serie in extras.items()})


def _desfechos(df: pd.DataFrame) -> pd.DataFrame:
    interacoes = df["likes"] + df["comentarios"]
    return pd.DataFrame(
        {
            "alcance": np.log1p(df["views"]),
            "reacao": np.log((interacoes + 1) / (df["views"] + 1)),
        },
        index=df.index,
    )


def veredito(efeito: float, baixo: float, alto: float) -> str:
    """sobe, cai, tanto (intervalo inteiro dentro de ±10%) ou incerto (o intervalo não decide)."""
    piso, teto = np.log(1 - EFEITO_MINIMO), np.log(1 + EFEITO_MINIMO)
    if baixo > 0 and efeito >= teto:
        return "sobe"
    if alto < 0 and efeito <= piso:
        return "cai"
    if baixo > piso and alto < teto:
        return "tanto"
    return "incerto"


def _comparar(x: pd.Series, y: pd.Series, perfis: pd.Series, rng) -> dict | None:
    diferencas = []
    for _, indices in perfis.groupby(perfis).groups.items():
        xi, yi = x.loc[indices], y.loc[indices]
        com, sem = yi[xi == 1], yi[xi == 0]
        if len(com) >= MIN_POR_GRUPO and len(sem) >= MIN_POR_GRUPO:
            diferencas.append(com.mean() - sem.mean())
    if len(diferencas) < MIN_PERFIS:
        return None
    d = np.array(diferencas)
    medias = d[rng.integers(0, len(d), (REAMOSTRAS, len(d)))].mean(axis=1)
    baixo, alto = np.percentile(medias, [2.5, 97.5])
    return {
        "efeito": float(np.expm1(d.mean())),  # variação relativa: +0,56 = 56% a mais
        "ic95": [float(np.expm1(baixo)), float(np.expm1(alto))],
        "veredito": veredito(d.mean(), baixo, alto),
        "n_perfis": len(d),
        "sobe_em": int((d > 0).sum()),
    }


def consultar(df: pd.DataFrame, semente: int = 0) -> list[dict]:
    """Uma linha por característica com dado suficiente, com o resultado nos dois desfechos."""
    explora = df[df["metade"] == "explora"]
    if explora.empty:
        return []
    x, y, rng = caracteristicas(explora), _desfechos(explora), np.random.default_rng(semente)
    saida = []
    for nome in x.columns:
        visto = x[nome].notna()
        resultados = {
            d: _comparar(x.loc[visto, nome], y.loc[visto, d], explora.loc[visto, "handle"], rng)
            for d in DESFECHOS
        }
        if all(resultados.values()):
            saida.append(
                {"atributo": nome, "presenca": float(x.loc[visto, nome].mean()), **resultados}
            )
    return saida
