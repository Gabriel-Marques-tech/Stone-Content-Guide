import json
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from test_agente import LLMFalso, banco, base, rapido  # noqa: F401

from mpe import memoria, radar
from mpe.agente import ESQUEMA, executar
from mpe.avaliador import _Leitura
from mpe.contrato import Padrao
from mpe.motor import BOOLEANOS

PEDIDO = {"mode": "gerar_criativo", "query": "lucro"}


def padrao(atributo="tem_cta"):
    return Padrao(
        atributo=atributo, conselho="Peça uma ação", no_grupo=0.8, nos_outros=0.6, n=50,
        n_outros=50, leitura="base inteira",
    )  # fmt: skip


def gravar(banco, faltas, objetivo="contato", n=1, dias=0):  # noqa: F811
    banco.execute(ESQUEMA)
    saida = {"patterns": [{"atributo": "tem_cta"}], "creatives": []}
    etapas = [{"etapa": "verificar", "faltas": faltas}]
    quando = datetime(2026, 11, 25) - timedelta(days=dias)
    for i in range(n):
        banco.execute(
            "INSERT INTO execucoes VALUES (?, ?, ?, ?, ?)",
            [f"{objetivo}{dias}{i}", quando + timedelta(seconds=i)]
            + [json.dumps({"mode": "gerar_criativo", "query": "x", "objetivo": objetivo})]
            + [json.dumps(saida), json.dumps(etapas)],
        )


def test_memoria_vazia_sem_execucoes(banco):  # noqa: F811
    assert memoria.lembrar(banco, "contato", [padrao()]) == []


def test_erro_repetido_vira_aviso_so_do_mesmo_objetivo(banco):  # noqa: F811
    gravar(banco, [["tem_cta"], []], n=6)
    (aviso,) = memoria.lembrar(banco, "contato", [padrao()])
    assert (aviso["faltas"], aviso["roteiros"]) == (6, 12)
    assert memoria.lembrar(banco, "engajamento", [padrao()]) == []


def test_poucos_erros_e_leitura_que_falhou_nao_viram_aviso(banco):  # noqa: F811
    gravar(banco, [["tem_cta"], []], n=1)
    gravar(banco, [[], None], n=12, dias=1)
    assert memoria.lembrar(banco, "contato", [padrao()]) == []


def test_aviso_some_quando_o_erro_para(banco):  # noqa: F811
    gravar(banco, [["tem_cta"], ["tem_cta"]], n=10, dias=5)
    assert memoria.lembrar(banco, "contato", [padrao()])
    gravar(banco, [[], []], n=25, dias=0)
    assert memoria.lembrar(banco, "contato", [padrao()]) == []


def base_temporal(inverte: bool):
    """Três períodos; com `inverte`, tutorial domina o topo no começo e some dele no fim."""
    rng, linhas = np.random.default_rng(1), []
    for i in range(1800):
        periodo, topo = i // 600, rng.random() < 0.1
        chance = {0: 0.9, 1: 0.5, 2: 0.1}[periodo] if inverte and topo else 0.4
        linhas.append(
            {b: False for b in BOOLEANOS}
            | {
                "id": str(i), "handle": f"@{i % 30}", "categorizado": True, "duracao_s": 40,
                "publicado_em": pd.Timestamp("2025-01-01") + pd.Timedelta(hours=6 * i),
                "engajamento": (1 if topo else 0) + rng.random() / 10, "top_tapi": topo,
                "formato_video": "tutorial" if rng.random() < chance else "lista_dicas",
                "tipo_hook": "dor", "tema_principal": "financas", "tom": "informal",
                "tipo_cta": "seguir",
            }
        )  # fmt: skip
    return pd.DataFrame(linhas)


def test_radar_ve_o_que_caiu():
    r = {x["atributo"]: x for x in radar.radar(base_temporal(True))}
    assert r["formato_video=tutorial"]["tendencia"] == "caindo"
    assert r["formato_video=lista_dicas"]["tendencia"] == "subindo"


def test_radar_nao_inventa_tendencia():
    assert {x["tendencia"] for x in radar.radar(base_temporal(False))} <= {
        "sem_sinal", "indicio_alta", "indicio_queda",
    }  # fmt: skip


def test_radar_sem_dado_suficiente_fica_calado():
    assert radar.radar(base()) == []


@pytest.mark.parametrize(
    ("medidas", "esperado"),
    [
        ([(0.2, 0.1, 0.3), (0.15, 0.02, 0.3)], "subindo"),
        ([(0.2, 0.1, 0.3), (0.15, -0.02, 0.3)], "indicio_alta"),
        ([(0.2, 0.1, 0.3), (-0.2, -0.3, -0.1)], "sem_sinal"),
        ([(-0.2, -0.3, -0.1), (-0.05, -0.1, 0.0)], "sem_sinal"),
        ([], "sem_sinal"),
    ],
)
def test_classificar(medidas, esperado):
    assert radar.classificar(medidas) == esperado


class LLMQueErra(LLMFalso):
    """O primeiro rascunho não aplica `passo_concreto`; a reescrita aplica se `acerta`."""

    def __init__(self, acerta):
        super().__init__(refs=["0-0"])
        self.acerta, self.revisoes = acerta, 0

    def json(self, texto, modelo, temperatura=0.0):
        if modelo.__name__ == "_Revisao":
            self.prompts.append(texto)
            self.revisoes += 1
            c = dict(gancho="novo", roteiro="r", legenda="l", chamada_para_acao="c")
            return modelo.model_validate({"criativo": c | {"referencias": ["inventado"]}})
        if modelo is _Leitura:
            tem = "Gancho: novo" in texto and self.acerta
            campos = {b: b == "passo_concreto" and tem for b in BOOLEANOS}
            return _Leitura(
                **campos, formato_video="tutorial", hook_primeiros_3s="x", tipo_hook="dor",
                forca_hook_0a10=5, tema_principal="financas", legenda_tamanho="curta",
                ritmo_cortes_0a10=5, tom="informal", clareza_mensagem_0a10=5, tipo_cta="seguir",
                elementos_top5=["a"], transcricao="x", duracao_estimada_s=40,
            )  # fmt: skip
        return super().json(texto, modelo, temperatura)


def base_com_padrao():
    df = base()
    df["passo_concreto"] = df["top_tapi"]
    return df


def test_revisao_troca_quando_melhora_e_nao_aceita_referencia_nova(banco):  # noqa: F811
    s = executar(banco, LLMQueErra(True), PEDIDO, base_com_padrao())
    assert s.revisions == 1 and s.creatives[0].gancho == "novo"
    assert "passo_concreto" in s.creatives[0].padroes
    assert s.creatives[0].referencias == ["0-0"]


def test_revisao_que_nao_melhora_mantem_o_original_e_roda_uma_vez(banco):  # noqa: F811
    llm = LLMQueErra(False)
    s = executar(banco, llm, PEDIDO, base_com_padrao())
    assert s.revisions == 0 and s.creatives[0].gancho == "g" and llm.revisoes == 1


def test_chaves_desligam(banco, monkeypatch):  # noqa: F811
    monkeypatch.setenv("MPE_REVISAR", "0")
    llm = LLMQueErra(True)
    assert executar(banco, llm, PEDIDO, base_com_padrao()).revisions == 0 and llm.revisoes == 0


def test_o_erro_gravado_chega_ao_proximo_pedido(banco, monkeypatch):  # noqa: F811
    monkeypatch.setenv("MPE_REVISAR", "0")
    df = base_com_padrao()
    for _ in range(10):
        executar(banco, LLMQueErra(False), PEDIDO, df)
    llm = LLMQueErra(False)
    s = executar(banco, llm, PEDIDO, df)
    assert any("faltou em 10 de 10" in x for x in s.lessons)
    assert any("faltou em 10 de 10" in p for p in llm.prompts)
    monkeypatch.setenv("MPE_APRENDE", "0")
    assert executar(banco, LLMQueErra(False), PEDIDO, df).lessons == []


def test_rotina_diz_o_que_entrou_caiu_e_mudou(banco):  # noqa: F811
    from mpe import rotina

    antes = {
        "posts": 10, "firmes": {"contato": {"tem_cta": [0.8, 0.6], "prova_social": [0.5, 0.3]}},
        "radar": {"formato_video=tutorial": "sem_sinal"},
    }  # fmt: skip
    depois = {
        "posts": 12, "firmes": {"contato": {"tem_cta": [0.7, 0.6], "tem_rosto": [0.5, 0.3]}},
        "radar": {"formato_video=tutorial": "caindo"},
    }  # fmt: skip
    mudou = rotina.comparar(antes, depois)
    assert "base: 10 para 12 vídeos" in mudou
    assert "contato: entrou Tem rosto" in mudou and "contato: caiu Prova social" in mudou
    assert any("Pede uma ação foi de 80%" in m for m in mudou)
    assert "radar: Tutorial passou de sem_sinal para caindo" in mudou
    assert rotina.comparar(depois, depois) == []
    rotina.registrar(banco, depois, mudou)
    assert banco.execute("SELECT count(*) FROM mudancas").fetchone()[0] == 1


def test_fotografar_a_base():
    from mpe import rotina

    f = rotina.fotografar(base_temporal(True))
    assert f["posts"] == 1800 and f["radar"]["formato_video=tutorial"] == "caindo"
