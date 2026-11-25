import duckdb
from test_agente import LLMFalso, base

from mpe.agente import executar
from mpe.consulta import referencias
from mpe.playbook import concentracao, montar


def test_playbook_cita_post_real_e_nao_inventa_regra():
    banco, df = duckdb.connect(":memory:"), base()
    ref = referencias(df, "lucro")[0].post_id
    s = executar(banco, LLMFalso([ref]), {"mode": "gerar_criativo", "query": "lucro"}, df)
    texto = montar(banco, df, [("lucro", s)])
    assert f"shorts/{ref}" in texto and "Nenhuma hipótese registrada" in texto
    assert "## Regras aprovadas" not in texto and "| não testada |" not in texto


def test_milhar_com_ponto_sem_estragar_a_frase():
    df = base().assign(inscritos=12345)
    assert "12.345 no topo, 12.345 na base." in concentracao(df)
