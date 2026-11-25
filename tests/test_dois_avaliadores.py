"""Campos de quadros vêm do DeepSeek na base toda; campos de fala, do Gemini onde ele assistiu."""

import json
from datetime import datetime

import pytest
from test_motor import base

from mpe import motor
from mpe.ambiente import MODELO
from mpe.banco import abrir
from mpe.consulta import achados, base_completa
from mpe.rubrica import CAMPOS_QUADROS

AGORA = datetime(2026, 11, 23)
RUBRICA = {
    "formato_video": "tutorial", "hook_primeiros_3s": "x", "tipo_hook": "dor",
    "forca_hook_0a10": 5, "tema_principal": "financas", "tem_rosto": True,
    "criador_e_empreendedor_real": False, "prova_social": False, "texto_na_tela": True,
    "legenda_tamanho": "curta", "ritmo_cortes_0a10": 5, "tom": "informal",
    "usa_linguagem_regional": False, "clareza_mensagem_0a10": 5, "tem_cta": True,
    "tipo_cta": "seguir", "oferta_ou_beneficio_explicito": False, "elementos_top5": ["a"],
    "transcricao": "fala", "numero_no_gancho": False, "passo_concreto": True,
    "exemplo_com_numeros": False, "cita_erro_ou_perda": False, "cita_regra_ou_lei": False,
    "fala_direto_com_dono": True, "mostra_ambiente_real": False, "promove_produto_proprio": False,
}  # fmt: skip


@pytest.fixture
def banco(tmp_path):
    b = abrir(tmp_path / "t.duckdb")
    b.execute(
        "INSERT INTO canais VALUES ('c', '@c', 'Canal', '', 1000, 'criador', 'geral', ?)", [AGORA]
    )
    for i, likes in (("a", 50), ("b", 5)):
        b.execute(
            "INSERT INTO posts VALUES (?, 'c', 't', '', '[]', 'pt', '', ?, 40, 100, ?, 1, ?)",
            [i, AGORA, likes, AGORA],
        )
    return b


def gravar(banco, tabela, post, modelo, **troca):
    rubrica = json.dumps(RUBRICA | troca)
    banco.execute(f"INSERT INTO {tabela} VALUES (?, ?, ?, ?)", [post, modelo, rubrica, AGORA])


def test_cada_campo_vem_do_seu_avaliador(banco):
    gravar(banco, "categorias", "a", MODELO, tem_rosto=True, tom="tecnico")
    gravar(banco, "categorias_quadros", "a", "quadros", tem_rosto=False, tom="humoristico")
    gravar(banco, "categorias_quadros", "b", "quadros", tem_rosto=True)
    df = base_completa(banco).set_index("id")
    assert not df.loc["a", "tem_rosto"]  # quadros vencem no campo visual, mesmo com Gemini
    assert df.loc["a", "tom"] == "tecnico"  # fala fica com o Gemini
    assert df["categorizado"].all()
    assert df["com_fala"].to_dict() == {"a": True, "b": False}
    assert df.loc["b", ["tom", "passo_concreto"]].isna().all()


def test_sem_quadros_o_gemini_responde_tudo(banco):
    gravar(banco, "categorias", "a", MODELO)
    df = base_completa(banco).set_index("id")
    assert df["categorizado"].to_dict() == df["com_fala"].to_dict() == {"a": True, "b": False}


def test_achado_conta_so_os_posts_que_o_avaliador_viu(banco):
    gravar(banco, "categorias", "a", MODELO)
    gravar(banco, "categorias_quadros", "a", "quadros")
    gravar(banco, "categorias_quadros", "b", "quadros")
    df = base_completa(banco).assign(top_tapi=True)
    por_nome = {a.atributo: a for a in achados(df, n=99)}
    assert por_nome["tem_rosto"].n_top == 2
    assert por_nome["passo_concreto"].n_top == 1


def test_motor_testa_cada_atributo_onde_ha_resposta(monkeypatch):
    monkeypatch.setattr(motor, "PERMUTACOES", 500)
    df = base(0.4)
    de_fala = [c for c in [*motor.BOOLEANOS, *motor.CATEGORICOS] if c not in CAMPOS_QUADROS]
    df[de_fala] = df[de_fala].astype(object)
    df.loc[df["handle"].isin([f"@{h}" for h in range(12, 24)]), de_fala] = None
    fala, visual, vazio = motor.testar(df, ["numero_no_gancho", "tem_rosto", "tom=inexistente"])
    assert (fala.n_perfis, visual.n_perfis) == (12, 24)
    assert (fala.n_posts, visual.n_posts) == (192, 384)
    assert fala.efeito > 0.2 and vazio.ocorrencias == 0 and vazio.n_perfis == 12


def test_atributo_sem_nenhum_post_fica_sem_evidencia(monkeypatch):
    monkeypatch.setattr(motor, "PERMUTACOES", 500)
    df = base()
    df["numero_no_gancho"] = None
    sem, com = motor.testar(df, ["numero_no_gancho", "tem_rosto"])
    assert sem.n_perfis == 0 and motor.julgar(sem, "mais") == "evidencia_insuficiente"
    assert com.n_perfis == 24
