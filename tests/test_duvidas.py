from test_agente import base

from mpe.duvidas import leitura, montar, sinal


def test_diferenca_que_some_com_peso_igual_e_indefinida_e_nao_parecida():
    assert sinal(grupo=0.42, por_perfil=0.33, resto=0.31) == "indefinido"
    assert sinal(grupo=0.40, por_perfil=0.20, resto=0.30) == "indefinido"  # muda de lado
    assert sinal(grupo=0.32, por_perfil=0.45, resto=0.30) == "indefinido"  # só aparece por canal


def test_diferenca_que_se_mantem_vira_mais_ou_menos_e_a_pequena_e_parecida():
    assert sinal(grupo=0.83, por_perfil=0.81, resto=0.67) == "mais"
    assert sinal(grupo=0.40, por_perfil=0.50, resto=0.66) == "menos"
    assert sinal(grupo=0.26, por_perfil=0.28, resto=0.30) == "parecido"


def test_cada_desfecho_diz_quem_esta_na_comparacao():
    assert leitura("formato_video=tutorial", "lead") == "base inteira"
    assert "topo" in leitura("tem_cta", "lead")
    df = base().assign(lead=lambda d: d["top_tapi"], interessado=lambda d: d["top_tapi"])
    d = montar(df)[0]
    assert d["contato"]["n"] + d["contato"]["n_outros"] == len(df)
