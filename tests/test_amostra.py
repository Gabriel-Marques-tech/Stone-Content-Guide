import pandas as pd

from mpe.amostra import POR_GRUPO, amostrar, fila, ranquear


def base(canais=4, n=30):
    return pd.DataFrame(
        [
            {
                "id": f"{c}-{i}", "handle": f"@{c}", "segmento": "geral",
                "likes": i, "comentarios": 0, "inscritos": 100 * (c + 1),
            }
            for c in range(canais)
            for i in range(n)
        ]
    )  # fmt: skip


def test_ranking_normaliza_e_marca_dez_por_cento():
    r = ranquear(base())
    assert r["top_tapi"].sum() == 12
    assert r.iloc[0]["id"] == "0-29"
    assert r.iloc[0]["engajamento"] == 0.29


def test_ranking_descarta_metricas_ocultas():
    b = base()
    b.loc[0, "likes"] = None
    assert "0-0" not in set(ranquear(b)["id"])


def test_amostra_pareia_dentro_do_perfil_e_divide_perfis():
    a = amostrar(ranquear(base()))
    for _, g in a.groupby("handle"):
        assert (g["par_motor"] == "top").sum() == POR_GRUPO
        assert (g["par_motor"] == "resto").sum() == POR_GRUPO
        topo = g.loc[g["par_motor"] == "top", "likes"].min()
        assert g.loc[g["par_motor"] == "resto", "likes"].max() < topo
        assert g["metade"].nunique() == 1
    assert a.drop_duplicates("handle")["metade"].value_counts().to_dict() == {
        "explora": 2, "confirma": 2,
    }  # fmt: skip


def test_amostra_e_fila_sao_reprodutiveis_e_sem_repeticao():
    a, b = amostrar(ranquear(base())), amostrar(ranquear(base()))
    assert a.equals(b)
    f = fila(a)
    assert f == fila(b) and len(f) == len(set(f))


def test_fila_por_perfil_fecha_um_perfil_por_vez_comecando_pelo_mais_adiantado():
    from mpe.amostra import fila_por_perfil

    a = amostrar(ranquear(base()))
    motor = a[a["par_motor"].notna()]
    adiantado = motor[motor["handle"] == "@2"]
    feitos = set(adiantado["id"][:10])
    f = fila_por_perfil(a, feitos)
    assert len(f) == len(set(f)) and set(f) >= set(fila(a)) - feitos
    assert set(f[:6]) == set(adiantado["id"]) - feitos
    bloco = a.set_index("id").loc[f[6 : 6 + 2 * POR_GRUPO]]
    assert bloco["handle"].nunique() == 1
    assert bloco["metade"].iloc[0] != adiantado["metade"].iloc[0]
    assert list(bloco["par_motor"][:4]) == ["resto", "top", "resto", "top"]
