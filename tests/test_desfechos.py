"""A consulta em dois desfechos acha um efeito plantado e não inventa onde não há."""

import numpy as np
import pandas as pd

from mpe import desfechos


def _base(efeito_views: float, perfis: int = 12, posts: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(1)
    linhas = []
    for p in range(perfis):
        for i in range(posts):
            curto = i % 2 == 0
            views = np.exp(rng.normal(7 + (efeito_views if curto else 0), 0.5))
            linhas.append(
                {
                    "handle": f"@p{p}",
                    "metade": "explora",
                    "titulo": "um título",
                    "duracao_s": 20 if curto else 50,
                    "publicado_em": "2026-10-01 12:00:00",
                    "views": int(views),
                    "likes": int(views * 0.02),
                    "comentarios": 1,
                }
            )
    df = pd.DataFrame(linhas)
    for campo in desfechos.matriz.__globals__["BOOLEANOS"]:
        df[campo] = False
    for campo in desfechos.matriz.__globals__["CATEGORICOS"]:
        df[campo] = "outro"
    return df


def _curto(resultado):
    return next(r for r in resultado if r["atributo"] == "duracao_faixa=ate_30s")


def test_acha_o_efeito_plantado_no_alcance():
    alcance = _curto(desfechos.consultar(_base(efeito_views=0.5)))["alcance"]
    assert alcance["veredito"] == "sobe"
    assert 0.4 < alcance["efeito"] < 0.9  # exp(0,5) - 1 = 0,65
    assert alcance["sobe_em"] == alcance["n_perfis"] == 12


def test_sem_efeito_nao_vira_sobe_nem_cai():
    assert _curto(desfechos.consultar(_base(efeito_views=0.0)))["alcance"]["veredito"] in (
        "tanto",
        "incerto",
    )


def test_veredito_separa_tanto_faz_de_incerto():
    assert desfechos.veredito(0.0, -0.03, 0.03) == "tanto"
    assert desfechos.veredito(0.05, -0.2, 0.3) == "incerto"
    assert desfechos.veredito(-0.4, -0.6, -0.2) == "cai"
