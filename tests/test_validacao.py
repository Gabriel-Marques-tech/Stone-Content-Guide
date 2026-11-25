import pandas as pd
import pytest

from mpe.validacao import CAMPOS, concordancia, kappa, sortear


def test_kappa_acordo_total_e_acaso():
    assert kappa([1, 0, 1, 0], [1, 0, 1, 0]) == 1
    assert kappa([1, 1, 0, 0], [1, 0, 1, 0]) == pytest.approx(0)


def test_concordancia_ignora_campo_em_branco_e_caixa():
    modelo = pd.DataFrame([{"id": i, **{c: True for c in CAMPOS}} for i in "ab"])
    humano = pd.DataFrame([{"id": i, **{c: "true" for c in CAMPOS}} for i in "ab"])
    humano.loc[1, "tem_cta"] = ""
    r = concordancia(modelo, humano).set_index("campo")
    assert r.loc["tem_cta", "n"] == 1 and r.loc["tem_rosto", "acordo"] == 1


def test_sorteio_espalha_perfis():
    df = pd.DataFrame(
        [{"id": f"{h}{i}", "handle": h, "categorizado": True} for h in "abcde" for i in range(20)]
    )
    assert sortear(df, 10)["handle"].value_counts().max() == 2
