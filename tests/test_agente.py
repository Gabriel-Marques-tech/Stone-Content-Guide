import json

import duckdb
import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from mpe import hipoteses, motor
from mpe.agente import executar
from mpe.consulta import achados, por_tema, referencias
from mpe.contrato import Criativo, Entrada
from mpe.motor import BOOLEANOS


@pytest.fixture(autouse=True)
def rapido(monkeypatch):
    monkeypatch.setattr(motor, "PERMUTACOES", 1000)


@pytest.fixture
def banco():
    return duckdb.connect(":memory:")


def base(efeito=0.5):
    rng = np.random.default_rng(3)
    linhas = []
    for h in range(24):
        for i in range(16):
            grupo = "top" if i < 8 else "resto"
            linha = {b: bool(rng.random() < 0.4) for b in BOOLEANOS}
            linha["passo_concreto"] = bool(rng.random() < 0.2 + efeito * (grupo == "top"))
            linhas.append(
                linha
                | {
                    "id": f"{h}-{i}", "handle": f"@{h}", "canal": f"Canal {h}",
                    "inscritos": 1000, "segmento": "varejo" if h % 2 else "geral",
                    "titulo": "como precificar", "transcricao": "lucro", "engajamento": 1 / (i + 1),
                    "posicao": i + 1, "top_tapi": i < 2, "categorizado": True, "par_motor": grupo,
                    "metade": "explora" if h < 12 else "confirma", "duracao_s": 40,
                    "publicado_em": pd.Timestamp("2026-01-01"), "formato_video": "lista_dicas",
                    "tipo_hook": "dor", "tema_principal": "financas", "tom": "informal",
                    "tipo_cta": "seguir", "hook_primeiros_3s": "x", "elementos_top5": ["a"],
                }
            )  # fmt: skip
    return pd.DataFrame(linhas)


class LLMFalso:
    def __init__(self, refs=None, atributos=None):
        self.refs, self.atributos, self.prompts = refs, atributos, []

    def json(self, texto, modelo, temperatura=0.0):
        self.prompts.append(texto)
        criativo = dict(gancho="g", roteiro="r", legenda="l", chamada_para_acao="c")
        respostas = {
            "_Interpretacao": {"segmento": None, "termos": "lucro"},
            "_Redacao": {"explicacao": "ok"},
            "_Criativos": {
                "explicacao": "ok",
                "criativos": [criativo | {"referencias": self.refs}],
            },
            "_Propostas": {
                "hipoteses": [
                    dict(
                        afirmacao=f"hipótese sobre {a}",
                        atributo=a,
                        direcao="mais",
                        justificativa="n",
                    )
                    for a in self.atributos or []
                ]
            },
        }
        return modelo.model_validate(respostas[modelo.__name__])


CINCO = ["passo_concreto", "tem_rosto", "prova_social", "tem_cta", "texto_na_tela"]


def test_criativo_com_referencia_real_passa_e_execucao_e_registrada(banco):
    df = base()
    ref = referencias(df, "lucro")[0].post_id
    s = executar(banco, LLMFalso([ref]), {"mode": "gerar_criativo", "query": "lucro"}, df)
    assert len(s.creatives) == 1 and s.confidence_flag == "ok"
    (etapas,) = banco.execute("SELECT etapas FROM execucoes").fetchone()
    assert [e["etapa"] for e in json.loads(etapas)][-1] == "verificar"


def test_criativo_que_cita_post_inventado_e_descartado(banco):
    s = executar(
        banco, LLMFalso(["inventado"]), {"mode": "gerar_criativo", "query": "lucro"}, base()
    )
    assert s.creatives == []


def test_recorte_pequeno_e_vazio_sao_sinalizados(banco):
    df = base()
    poucos = df[df["handle"].isin(["@0", "@1"])]
    entrada = {"mode": "analisar", "query": "lucro"}
    assert executar(banco, LLMFalso(), entrada, poucos).confidence_flag == "poucos_posts"
    vazio = executar(banco, LLMFalso(), entrada | {"segment": "beleza"}, df)
    assert vazio.confidence_flag == "sem_dados" and vazio.findings == []


def test_achados_saem_do_assunto_do_pedido_e_nao_do_topo_inteiro():
    df = base()
    df["tem_rosto"] = True
    maquininha = df["handle"].isin([f"@{h}" for h in range(6)])
    df.loc[maquininha, "titulo"] = "taxas das maquininhas"
    df.loc[maquininha, "tem_rosto"] = False
    do_tema, usou = por_tema(df, "maquininha taxa")
    assert usou and set(do_tema["handle"]) == {f"@{h}" for h in range(6)}
    assert "tem_rosto" not in {a.atributo for a in achados(do_tema) if a.frequencia_top > 0}
    # assunto com poucos posts no topo: mantém o recorte e avisa
    resto, usou = por_tema(df, "franquia")
    assert not usou and len(resto) == len(df)


def test_objetivo_contato_traz_quem_recebeu_pedido(banco):
    df = base()
    df["lead"] = df["id"].isin(["3-9", "4-9"])  # fora do topo, com pedido de contato
    df["intencao"] = df["lead"].astype(int) * 5
    ids = [r.post_id for r in referencias(df, "lucro", objetivo="contato")]
    assert ids[:2] == ["3-9", "4-9"] or ids[:2] == ["4-9", "3-9"]
    assert "3-9" not in [r.post_id for r in referencias(df, "lucro")]


def test_padrao_aplicado_vem_da_conferencia_e_nao_da_palavra_do_modelo(banco):
    from mpe.avaliador import _Leitura

    llm, original = LLMFalso(refs=["0-0"]), LLMFalso.json
    campos = {b: b == "passo_concreto" for b in BOOLEANOS}

    def json_(texto, modelo, temperatura=0.0):
        if modelo is _Leitura:
            return _Leitura(
                **campos, formato_video="talking_head", hook_primeiros_3s="x", tipo_hook="dor",
                forca_hook_0a10=5, tema_principal="financas", legenda_tamanho="curta",
                ritmo_cortes_0a10=5, tom="informal", clareza_mensagem_0a10=5, tipo_cta="seguir",
                elementos_top5=["a"], transcricao="x", duracao_estimada_s=40,
            )  # fmt: skip
        saida = original(llm, texto, modelo, temperatura)
        for c in getattr(saida, "criativos", []):
            c.padroes = ["inventado"]
        return saida

    llm.json = json_
    df = base()
    df["passo_concreto"] = df["top_tapi"]
    s = executar(banco, llm, {"mode": "gerar_criativo", "query": "lucro"}, df)
    assert s.creatives[0].padroes == ["passo_concreto"]


def test_roteiro_em_texto_sai_das_cenas():
    from mpe.agente import com_roteiro

    cenas = [{"inicio_s": 0, "fim_s": 4, "na_tela": "Sobrou quanto?", "cena": "Dona no balcão."}]
    c = Criativo(
        gancho="g", roteiro="x", legenda="l", chamada_para_acao="c", referencias=["a"], cenas=cenas
    )
    assert com_roteiro(c).roteiro == '0-4s: Dona no balcão. Texto na tela: "Sobrou quanto?".'
    antigo = c.model_copy(update={"cenas": []})
    assert com_roteiro(antigo).roteiro == "x"


def test_agente_registra_se_recortou_por_tema(banco):
    saida = executar(banco, LLMFalso(refs=["0-0"]), {"mode": "analisar", "query": "lucro"}, base())
    etapas = json.loads(banco.execute("SELECT etapas FROM execucoes").fetchone()[0])
    assert etapas[1]["recorte_por_tema"] is True and saida.findings


def test_referencias_limitam_posts_por_perfil():
    contagem = pd.Series([r.canal for r in referencias(base(), "lucro")]).value_counts()
    assert contagem.max() <= 2


def test_contrato_recusa_modo_desconhecido_e_criativo_sem_referencia():
    with pytest.raises(ValidationError):
        Entrada(mode="prever", query="abc")
    with pytest.raises(ValidationError):
        Criativo(gancho="g", roteiro="r", legenda="l", chamada_para_acao="c", referencias=[])


def test_ciclo_confirma_o_efeito_e_derruba_o_resto(banco):
    df = base()
    hipoteses.propor(banco, df, LLMFalso(atributos=CINCO))
    hs = {h.atributo: h for h in hipoteses.confirmar(banco, df)}
    assert hs["passo_concreto"].veredito == "sustentada"
    assert all(h.veredito != "sustentada" for a, h in hs.items() if a != "passo_concreto")
    assert hipoteses.aprovar(banco, hs["passo_concreto"].id).aprovada_por_humano
    with pytest.raises(ValueError, match="não foi sustentada"):
        hipoteses.aprovar(banco, hs["tem_rosto"].id)


def test_nao_aceita_segunda_leva_nem_atributo_fora_da_exploracao(banco):
    df = base()
    with pytest.raises(ValueError, match="fora da exploração"):
        hipoteses.propor(banco, df, LLMFalso(atributos=[*CINCO[:4], "nao_existe"]))
    hipoteses.propor(banco, df, LLMFalso(atributos=CINCO))
    with pytest.raises(ValueError, match="vagas são fixas"):
        hipoteses.propor(banco, df, LLMFalso(atributos=CINCO))


def test_confirmacao_nao_e_refeita(banco):
    df = base()
    hipoteses.propor(banco, df, LLMFalso(atributos=CINCO))
    antes = hipoteses.confirmar(banco, df)
    assert hipoteses.confirmar(banco, base(efeito=-0.1)) == antes


def test_proposta_nao_enxerga_a_metade_de_confirmacao(banco):
    df, llm = base(), LLMFalso(atributos=CINCO)
    so_explora = df[df["metade"] == "explora"]
    hipoteses.propor(banco, df, llm)
    outro = LLMFalso(atributos=CINCO)
    hipoteses.propor(duckdb.connect(":memory:"), so_explora, outro)
    assert llm.prompts == outro.prompts


def test_servidor_mcp_registra_as_ferramentas():
    import asyncio

    from mpe.mcp_servidor import criar

    nomes = {t.name for t in asyncio.run(criar().list_tools())}
    assert {"consultar", "propor_hipoteses", "confirmar_hipoteses", "aprovar_hipotese"} <= nomes


def test_avaliador_mede_aderencia_por_conta_e_nao_por_opiniao():
    from mpe.avaliador import _Leitura, avaliar

    df = base()
    df["duracao_s"] = 40
    df["com_fala"] = True
    df["passo_concreto"] = df["top_tapi"]  # o topo sempre tem; o resto nunca

    class Leitor:
        def __init__(self, passo):
            self.passo = passo

        def json(self, texto, modelo, temperatura=0.0):
            campos = {b: False for b in BOOLEANOS} | {"passo_concreto": self.passo}
            return _Leitura(
                **campos, formato_video="lista_dicas", hook_primeiros_3s="x", tipo_hook="dor",
                forca_hook_0a10=5, tema_principal="financas", legenda_tamanho="curta",
                ritmo_cortes_0a10=5, tom="informal", clareza_mensagem_0a10=5, tipo_cta="seguir",
                elementos_top5=["a"], transcricao="x", duracao_estimada_s=40,
            )  # fmt: skip

    com, sem = avaliar(df, Leitor(True), "roteiro"), avaliar(df, Leitor(False), "roteiro")
    sinal = next(s for s in sem.sinais if s.atributo == "passo_concreto")
    assert not sinal.alinhado and sinal.exemplo and com.aderencia > sem.aderencia
    assert any("passo_concreto" in a for a in sem.ajustes)
