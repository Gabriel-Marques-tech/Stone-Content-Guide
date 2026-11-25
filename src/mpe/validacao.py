"""Validação manual: sorteio cego de posts e concordância entre modelo e humano."""

import numpy as np
import pandas as pd

CAMPOS = [
    "formato_video", "tipo_hook", "tema_principal", "tom", "tem_rosto", "texto_na_tela", "tem_cta",
    "numero_no_gancho", "passo_concreto", "mostra_ambiente_real", "promove_produto_proprio",
]  # fmt: skip


def sortear(df: pd.DataFrame, n: int = 50, semente: int = 7) -> pd.DataFrame:
    """Posts categorizados da amostra, no máximo 2 por perfil enquanto houver perfis."""
    completos = df["categorizado"] & df.get("com_fala", True)  # os dois avaliadores no mesmo post
    feitos = df[completos].sample(frac=1, random_state=semente)
    ordem = feitos.groupby("handle").cumcount()
    return feitos.assign(_o=ordem).sort_values("_o", kind="stable").head(n).drop(columns="_o")


def kappa(a, b) -> float:
    a, b = pd.Series(a).astype(str).to_numpy(), pd.Series(b).astype(str).to_numpy()
    valores = np.unique(np.concatenate([a, b]))
    observado = (a == b).mean()
    esperado = sum((a == v).mean() * (b == v).mean() for v in valores)
    return float("nan") if esperado == 1 else float((observado - esperado) / (1 - esperado))


def concordancia(modelo: pd.DataFrame, humano: pd.DataFrame) -> pd.DataFrame:
    """Os dois com coluna id. Campo em branco na validação humana fica de fora."""
    juntos = modelo.merge(humano, on="id", suffixes=("_m", "_h"))
    linhas = []
    for c in CAMPOS:
        m = juntos[f"{c}_m"].astype(str).str.lower()
        h = juntos[f"{c}_h"].astype(str).str.lower()
        ok = ~h.isin(["", "nan", "none"])
        linhas.append(
            {"campo": c, "n": int(ok.sum()), "acordo": float((m[ok] == h[ok]).mean()),
             "kappa": kappa(m[ok], h[ok])}
        )  # fmt: skip
    return pd.DataFrame(linhas)
