import json
import subprocess

import duckdb
import pytest
from starlette.testclient import TestClient

from mpe import app as plataforma
from mpe import gravacao
from mpe.agente import ESQUEMA
from mpe.banco import ESQUEMA as ESQUEMA_BANCO

CENAS = [
    {"inicio_s": 0, "fim_s": 2, "na_tela": "Olha isso", "cena": "a"},
    {"inicio_s": 2, "fim_s": 4, "na_tela": "Comenta aí", "cena": "b"},
]
CRIATIVO = {"gancho": "g", "cenas": CENAS, "referencias": ["x"]}
ANALISE = {
    "resumo": "Segue o roteiro, mas demora a começar.", "analisado_por": "Teste",
    "melhorias": [{"t": 1, "texto": "gancho tarde", "como": "comece pela pergunta"}],
    "quadros": [{"na_tela": "Olha isso", "no_video": "sim", "t": 0.5, "observacao": "ok"}],
}  # fmt: skip


def filmar(destino, tamanho="180x320", som="sine=frequency=440", s=4):
    entradas = ["-f", "lavfi", "-i", f"testsrc=size={tamanho}:rate=10:duration={s}"]
    if som:
        entradas += ["-f", "lavfi", "-i", f"{som}:duration={s}" if "=" in som else som, "-shortest"]
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", *entradas, "-c:v", "libvpx", "-c:a", "libopus",
         str(destino)], check=True,
    )  # fmt: skip
    return destino


@pytest.fixture
def pasta(tmp_path, monkeypatch):
    monkeypatch.setattr(gravacao, "PASTA", tmp_path / "gravacoes")
    gravacao.PASTA.mkdir()
    return gravacao.PASTA


@pytest.fixture
def cliente(pasta, tmp_path, monkeypatch):
    arquivo = tmp_path / "mpe.duckdb"
    with duckdb.connect(str(arquivo)) as con:
        con.execute(ESQUEMA_BANCO)
        con.execute(ESQUEMA)
        con.execute(
            "INSERT INTO execucoes VALUES ('r1', now(), '{}', ?, '[]')",
            [json.dumps({"creatives": [CRIATIVO]})],
        )
    monkeypatch.setattr(plataforma, "ARQUIVO", arquivo)
    return TestClient(plataforma.app)


def enviar(cliente, corpo, tipo="video/webm", alvo="run_id=r1&versao=0"):
    return cliente.post(f"/api/gravacao?{alvo}", content=corpo, headers={"Content-Type": tipo})


def test_medir_e_checar(tmp_path):
    m = gravacao.medir(filmar(tmp_path / "a.webm"))
    assert m.tem_audio and m.altura > m.largura and 3.5 < m.duracao_s < 4.5
    assert all(i.ok for i in gravacao.checar(m, 4))
    deitado = gravacao.medir(filmar(tmp_path / "b.webm", "320x180", som=None))
    ruins = " ".join(i.texto for i in gravacao.checar(deitado, 60) if not i.ok)
    assert "não está em pé" in ruins and "sem som" in ruins and "prevê 60 s" in ruins


def test_enviar_mede_guarda_e_serve(cliente, pasta, tmp_path):
    video = filmar(tmp_path / "a.webm").read_bytes()
    g = enviar(cliente, video).json()
    assert g["analise"] is None and g["criativo"]["gancho"] == "g"
    assert len(cliente.get("/api/gravacoes?run_id=r1").json()["gravacoes"]) == 1
    assert cliente.get("/api/gravacoes?run_id=outro").json()["gravacoes"] == []
    assert cliente.get(g["arquivo"]).content == video
    assert not list(pasta.glob("*.parte"))


def test_recusas_nao_deixam_arquivo(cliente, pasta, tmp_path, monkeypatch):
    video = filmar(tmp_path / "a.webm").read_bytes()
    assert enviar(cliente, video, "text/plain").status_code == 415
    assert enviar(cliente, b"nao sou um video").status_code == 409
    assert enviar(cliente, video, alvo="run_id=nada&versao=0").status_code == 409
    assert enviar(cliente, video, alvo="run_id=r1&versao=7").status_code == 409
    assert enviar(cliente, video, alvo="run_id=r1&versao=-1").status_code == 400
    monkeypatch.setattr(gravacao, "LIMITE", 10)
    assert enviar(cliente, video).status_code == 413
    assert list(pasta.iterdir()) == []


def test_nome_estranho_nao_sai_da_pasta(cliente, pasta):
    (pasta / "segredo.json").write_text("{}")
    for nome in ("segredo.json", "..%2Fmpe.duckdb", "grav-000000000000.mp4"):
        assert cliente.get(f"/gravacoes/{nome}").status_code == 404
    with pytest.raises(ValueError):
        gravacao.ler("../x")


def test_analise_so_entra_no_formato(cliente, tmp_path):
    id_ = enviar(cliente, filmar(tmp_path / "a.webm").read_bytes()).json()["id"]
    gravacao.gravar_analise(id_, ANALISE)
    feita = cliente.get("/api/gravacoes").json()["gravacoes"][0]["analise"]
    assert feita["analisado_por"] == "Teste"
    tarde = {**ANALISE, "melhorias": [{"t": 99, "texto": "depois do fim", "como": "corte aqui"}]}
    with pytest.raises(ValueError, match="depois do fim"):
        gravacao.gravar_analise(id_, tarde)
    outro = {**ANALISE, "quadros": [{"na_tela": "inventado", "no_video": "sim", "observacao": ""}]}
    with pytest.raises(ValueError, match="não está no roteiro"):
        gravacao.gravar_analise(id_, outro)


def test_conta_corte_seco(tmp_path):
    destino = tmp_path / "c.webm"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=red:size=180x320:rate=10:d=2",
         "-f", "lavfi", "-i", "testsrc=size=180x320:rate=10:duration=2", "-filter_complex",
         "[0:v][1:v]concat=n=2:v=1[v]", "-map", "[v]", "-c:v", "libvpx", str(destino)], check=True,
    )  # fmt: skip
    assert gravacao.medir(destino).cortes == 1
