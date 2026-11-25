from datetime import timedelta

import pytest
from test_agente import base, rapido  # noqa: F401

from mpe import acompanhamento as ac
from mpe.comentarios import Lote

VIDEO = "abcDEF12345"
LINK = f"https://www.youtube.com/shorts/{VIDEO}?feature=share"


class YT:
    def __init__(self):
        self.views, self.textos, self.sumiu, self.duracao = 100, {"c1": "qual o preço?"}, False, 40

    def videos(self, ids):
        if self.sumiu:
            return []
        publicado = (ac.agora() - timedelta(days=2)).isoformat().replace("+00:00", "Z")
        return [
            {"id": ids[0], "canal_id": "UC1", "titulo": "t", "publicado_em": publicado,
             "duracao_s": self.duracao, "views": self.views, "likes": 5, "comentarios": 1}
        ]  # fmt: skip

    def canais(self, ids):
        return [{"titulo": "Canal", "inscritos": 1000}]

    def _get(self, recurso, **_):
        return {
            "items": [
                {"id": c, "snippet": {"topLevelComment": {"snippet": {
                    "textDisplay": t, "authorChannelId": {"value": "UC1" if c == "dono" else "x"}}}}}
                for c, t in self.textos.items()
            ]
        }  # fmt: skip


class LLM:
    def __init__(self, falha=False):
        self.falha, self.lidos = falha, 0

    def json(self, texto, modelo, temperatura=0.0):
        if self.falha:
            raise RuntimeError("fora")
        n = len(texto.split("ordem.\n\n")[1].splitlines())
        self.lidos += n
        return Lote(itens=[{"n": i, "classe": "intencao"} for i in range(1, n + 1)])


@pytest.fixture(autouse=True)
def pasta(tmp_path, monkeypatch):
    monkeypatch.setattr(ac, "PASTA", tmp_path / "acompanhados")


def novo(yt=None, llm=None):
    yt, llm = yt or YT(), llm or LLM()
    return ac.adicionar(LINK, "r1", 0, yt, lambda: llm), yt, llm


@pytest.mark.parametrize(
    "link", [LINK, f"youtu.be/{VIDEO}", f"https://m.youtube.com/watch?x=1&v={VIDEO}"]
)
def test_link_aceito(link):
    assert ac.id_do_link(link) == VIDEO


@pytest.mark.parametrize(
    "link", ["", "https://exemplo.com/shorts/abcDEF12345", "youtube.com/shorts/../../x", VIDEO]
)
def test_link_recusado(link):
    with pytest.raises(ValueError, match="link"):
        ac.id_do_link(link)


def test_conta_pedidos_sem_os_do_canal_e_nao_guarda_texto():
    yt = YT()
    yt.textos["dono"] = "me chama"
    r, _, _ = novo(yt)
    assert (r["medidas"][-1]["pedidos"], r["medidas"][-1]["lidos"]) == (1, 1)
    assert "preço" not in ac._arquivo(VIDEO).read_text()


def test_so_comentario_novo_vai_para_a_ia():
    _, yt, llm = novo()
    yt.textos["c2"], yt.views = "eu quero", 300
    r = ac.atualizar(VIDEO, yt, lambda: llm)
    assert llm.lidos == 2 and [m["views"] for m in r["medidas"]] == [100, 300]


def test_ia_fora_nao_perde_os_numeros_e_tenta_de_novo():
    r, yt, _ = novo(llm=LLM(falha=True))
    assert r["medidas"][-1]["views"] == 100 and r["erro"] and not r["classes"]
    r = ac.atualizar(VIDEO, yt, LLM)
    assert r["medidas"][-1]["pedidos"] == 1 and not r["erro"]


def test_agendador_so_le_o_que_venceu(monkeypatch):
    _, yt, llm = novo()
    assert ac.rodar_vencidos(yt, lambda: llm) == 0
    depois = ac.agora() + ac.INTERVALO
    monkeypatch.setattr(ac, "agora", lambda: depois)
    assert ac.rodar_vencidos(yt, lambda: llm) == 1
    ac.parar(VIDEO)
    monkeypatch.setattr(ac, "agora", lambda: depois + ac.INTERVALO)
    assert ac.rodar_vencidos(yt, lambda: llm) == 0


def test_para_de_ler_depois_do_prazo():
    r, _, _ = novo()
    assert not ac.vencido(r, ac.agora() + ac.ATE + timedelta(days=1))


def test_video_que_saiu_do_ar_para():
    _, yt, llm = novo()
    yt.sumiu = True
    r = ac.atualizar(VIDEO, yt, lambda: llm)
    assert not r["ativo"] and len(r["medidas"]) == 1


def test_recusa_video_longo_inexistente_ou_de_outro_roteiro():
    yt = YT()
    yt.duracao = 900
    with pytest.raises(ValueError, match="3 minutos"):
        novo(yt)
    yt.sumiu = True
    with pytest.raises(ValueError, match="público"):
        novo(yt)
    novo()
    with pytest.raises(ValueError, match="outro roteiro"):
        ac.adicionar(LINK, "r2", 0, YT(), LLM)


def test_video_novo_nao_e_comparado_com_a_base():
    r, _, _ = novo()
    frases = " ".join(ac.analisar(r, 0.5)["frases"])
    assert "Cedo para comparar" in frases and "corte" not in frases
    r["publicado_em"] = (ac.agora() - timedelta(days=30)).isoformat()
    assert "abaixo do corte" in " ".join(ac.analisar(r, 0.5)["frases"])


def canal_de(formato_do_melhor, posicao=0):
    df = base()
    df["handle"], df["engajamento"] = "@um", [1 / (i + 1) for i in range(len(df))]
    df.loc[posicao, "formato_video"] = formato_do_melhor
    return df


def test_vies_surge_so_com_algo_raro_num_dos_melhores():
    df = canal_de("humor_esquete")
    assert ac.vies(df, "0-0")["surge"] is True
    assert ac.vies(canal_de("lista_dicas"), "0-0")["surge"] in (True, False)
    fraco = canal_de("humor_esquete", posicao=len(df) - 1)
    assert ac.vies(fraco, fraco.iloc[-1]["id"])["surge"] is False


def test_vies_sem_dado_nao_afirma_nada():
    assert ac.vies(base(), "nao-existe")["surge"] is None
    assert ac.vies(base(), "0-0")["surge"] is None  # canal com poucos vídeos


def test_leitura_da_base_vira_a_primeira():
    df = base().assign(views=10, likes=2, comentarios=1, coletado_em="2026-11-23 13:48:41")
    r = ac.adicionar(LINK, "", 0, YT(), LLM, ac.leitura_da_base(df, "0-0"))
    assert [m["views"] for m in r["medidas"]] == [10, 100]
    assert ac.leitura_da_base(df, "fora") == []
