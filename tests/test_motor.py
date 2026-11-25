import numpy as np
import pandas as pd
import pytest

from mpe import motor
from mpe.motor import BOOLEANOS, CATEGORICOS, falsos_positivos, julgar, matriz


@pytest.fixture(autouse=True)
def rapido(monkeypatch):
    monkeypatch.setattr(motor, "PERMUTACOES", 1000)


def base(efeito=0.0, perfis=24, semente=1):
    rng = np.random.default_rng(semente)
    linhas = []
    for h in range(perfis):
        for grupo in ("top", "resto"):
            for _ in range(8):
                linha = {b: rng.random() < 0.4 for b in BOOLEANOS}
                linha["numero_no_gancho"] = rng.random() < 0.3 + efeito * (grupo == "top")
                linha |= {c: rng.choice(["a", "b"]) for c in CATEGORICOS}
                linhas.append(linha | {"handle": f"@{h}", "par_motor": grupo, "duracao_s": 40})
    return pd.DataFrame(linhas)


def test_acha_efeito_plantado():
    (t,) = motor.testar(base(0.4), ["numero_no_gancho"])
    assert t.p < motor.ALFA and t.efeito > 0.2
    assert julgar(t, "mais") == "sustentada"
    assert julgar(t, "menos") == "nao_sustentada"


def test_rotulos_embaralhados_quase_nao_geram_achado():
    assert falsos_positivos(base(0.4), rodadas=8) < 0.05


def test_diferenca_entre_perfis_nao_vira_efeito():
    """Um perfil que sempre usa o atributo não pode criar efeito: a comparação é interna."""
    df = base()
    df["prova_social"] = df["handle"].isin([f"@{i}" for i in range(12)])
    (t,) = motor.testar(df, ["prova_social"])
    assert t.efeito == 0 and t.p == 1


def test_poucos_perfis_e_evidencia_insuficiente():
    (t,) = motor.testar(base(0.6, perfis=4), ["numero_no_gancho"])
    assert julgar(t, "mais") == "evidencia_insuficiente"


def test_intervalo_largo_nao_e_rejeicao():
    t = motor.Teste(
        atributo="x", efeito=0.06, ic95=(-0.05, 0.17), p=0.3, prevalencia_top=0.4,
        prevalencia_resto=0.34, n_posts=300, n_perfis=20, ocorrencias=90,
    )  # fmt: skip
    assert julgar(t, "mais") == "evidencia_insuficiente"


def test_perfil_sem_categorizacao_suficiente_fica_fora():
    df = base(perfis=10)
    df = df.drop(df[(df["handle"] == "@0") & (df["par_motor"] == "top")].index[2:])
    (t,) = motor.testar(df, ["tem_rosto"])
    assert t.n_perfis == 9


def test_atributo_ausente_nao_quebra():
    (t,) = motor.testar(base(), ["tema_principal=inexistente"])
    assert t.ocorrencias == 0 and julgar(t, "mais") == "evidencia_insuficiente"


def test_matriz_so_tem_zero_e_um_e_nenhuma_nota():
    x = matriz(base())
    assert set(np.unique(x)) <= {0.0, 1.0}
    assert not any("0a10" in c for c in x.columns)
