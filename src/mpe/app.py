"""Plataforma web local: perguntar ao agente, navegar pela base e operar o ciclo de hipóteses.

Um processo, uma conexão por vez. Se a categorização estiver gravando no banco, as leituras usam
uma cópia e as escritas devolvem 503 com uma mensagem legível.
"""

import os
import shutil
import tempfile
import threading
from contextlib import contextmanager
from functools import cache
from pathlib import Path

import duckdb
import uvicorn
from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route

from mpe import avaliador, desfechos, duvidas, hipoteses, motor, painel, playbook, video
from mpe.agente import executar
from mpe.ambiente import DADOS, RAIZ
from mpe.banco import ESQUEMA
from mpe.consulta import base_completa
from mpe.contrato import Entrada
from mpe.feita import llm
from mpe.gemini import CotaEsgotada

PAGINA = Path(__file__).with_name("app.html")  # tela anterior, em /antigo
INICIO = Path(__file__).with_name("criar.html")
MAQUININHA = Path(__file__).with_name("inicio.html")  # tela anterior, em /maquininha
ESTATICOS = PAGINA.with_name("static")
ARQUIVO = DADOS / "mpe.duckdb"
TRAVA = threading.Lock()
POR_PAGINA = 48
_memoria: dict = {}


class Ocupado(Exception):
    pass


@contextmanager
def banco(escrita: bool = False):
    with TRAVA:
        try:
            con = duckdb.connect(str(ARQUIVO))
            con.execute(ESQUEMA)
        except duckdb.IOException:
            if escrita:
                raise Ocupado from None
            copia = Path(tempfile.mkdtemp()) / "mpe.duckdb"
            shutil.copy(ARQUIVO, copia)
            con = duckdb.connect(str(copia), read_only=True)
        try:
            yield con
        finally:
            con.close()


def _versao() -> float:
    wal = ARQUIVO.with_suffix(".duckdb.wal")
    return ARQUIVO.stat().st_mtime + (wal.stat().st_mtime if wal.exists() else 0)


def dados() -> dict:
    """Base aberta e resumo do painel, recalculados só quando o arquivo do banco muda."""
    global _memoria
    versao = _versao()
    if _memoria.get("versao") != versao:
        with banco() as con:
            df = base_completa(con)
            resumo = painel.montar(con, df, auditoria=False)
        # dicionário novo, em vez de limpar o antigo: outro pedido pode estar no meio dele
        _memoria = {"versao": versao, "df": df, "painel": resumo}
    return _memoria


@cache
def modelo():
    return llm()


def erro(mensagem: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"erro": mensagem}, status_code=status)


def protegido(funcao):
    def rota(request: Request):
        try:
            return funcao(request)
        except Ocupado:
            return erro("O banco está ocupado pela categorização. Tente de novo em instantes.", 503)
        except CotaEsgotada as e:
            return erro(f"O modelo de linguagem está sem cota ou crédito: {e}", 503)
        except ValidationError as e:
            return erro("; ".join(x["msg"] for x in e.errors()))
        except ValueError as e:
            return erro(str(e), 409)
        except RuntimeError as e:
            return erro(f"O serviço de IA falhou: {str(e)[:200]}. Tente de novo.", 502)

    return rota


def inicio(request: Request):
    return FileResponse(INICIO)


def maquininha(request: Request):
    return FileResponse(MAQUININHA)


def antigo(request: Request):
    return FileResponse(PAGINA)


@protegido
def api_duvidas(request: Request):
    """Dúvidas da maquininha, cada uma com o desfecho de engajamento e o de contato."""
    m = dados()
    if "duvidas" not in m:
        df = m["df"]
        m["duvidas"] = {"duvidas": duvidas.montar(df), **duvidas.resumo(df)}
    return JSONResponse(m["duvidas"])


@protegido
def api_exemplos(request: Request):
    try:
        return JSONResponse(
            duvidas.exemplos(dados()["df"], request.query_params.get("atributo", ""))
        )
    except KeyError:
        return erro("Característica desconhecida.", 404)


TEMAS_NOME = {
    "financas": "Finanças",
    "ferramentas_maquininha": "Maquininha",
    "vendas": "Vendas",
    "marketing": "Divulgação",
    "gestao": "Gestão",
    "historia_de_empreendedor": "Histórias de quem empreende",
    "atendimento": "Atendimento",
    "motivacao": "Motivação",
}


@protegido
def api_vitrine(request: Request):
    """Capas de vídeos reais para a abertura e os assuntos da base, com contagem."""
    df = dados()["df"]
    fala_com_dono = df["fala_direto_com_dono"].fillna(False).astype(bool)
    topo = df[df["top_tapi"] & df["com_fala"] & fala_com_dono].sort_values("posicao")
    topo = topo[topo.groupby("handle").cumcount() < 3]
    temas = []
    for tema, nome in TEMAS_NOME.items():
        g = df[df["tema_principal"] == tema].sort_values("posicao")
        if len(g):
            capas = g[g.groupby("handle").cumcount() < 1]["id"].head(3).tolist()
            temas.append({"tema": tema, "nome": nome, "videos": int(len(g)), "capas": capas})
    return JSONResponse({"capas": topo["id"].head(36).tolist(), "temas": temas, "videos": len(df)})


def api_avaliar(corpo: dict):
    """Confere um roteiro contra o que aparece nos vídeos com pedido de contato ou engajados."""
    rascunho = str(corpo.get("rascunho", "")).strip()
    if len(rascunho) < 20:
        return erro("Escreva um pouco mais sobre o que você vai falar e mostrar.")
    objetivo = "interesse" if corpo.get("objetivo") != "engajamento" else "engajamento"
    a = avaliador.avaliar(dados()["df"], modelo(), rascunho, objetivo)
    unicos: dict[str, dict] = {}  # dois campos podem dar o mesmo conselho: vale o primeiro
    for s in a.sinais:
        incluir = s.no_grupo > s.no_resto
        # conselho de evitar: quem o segue são os vídeos SEM a característica
        valores = [v if incluir else 1 - v for v in (s.no_grupo, s.no_resto)]
        unicos.setdefault(
            duvidas.conselho(s.atributo, incluir),
            {
                "alinhado": s.alinhado,
                "no_grupo": round(valores[0], 3),
                "nos_outros": round(valores[1], 3),
                "exemplo": s.exemplo.model_dump(mode="json") if s.exemplo else None,
            },
        )
    sinais = [{"texto": t, **v} for t, v in unicos.items()]
    tem = sum(s["alinhado"] for s in sinais)
    return JSONResponse({"objetivo": objetivo, "tem": tem, "de": len(sinais), "sinais": sinais})


def estatico(request: Request):
    """Imagens da interface (pasta static, sem subpastas)."""
    arquivo = PAGINA.with_name("static") / Path(request.path_params["nome"]).name
    return FileResponse(arquivo) if arquivo.is_file() else erro("Arquivo não encontrado.", 404)


def prototipo(request: Request):
    """Descartável: variantes da tela inicial em estudo (?variant=A|B|C)."""
    return FileResponse(PAGINA.with_name("prototipo.html"))


@protegido
def api_painel(request: Request):
    return JSONResponse(dados()["painel"])


@protegido
def api_auditoria(request: Request):
    """Teste do embaralhamento: lento, então é pedido à parte e guardado."""
    m = dados()
    if "auditoria" not in m:
        df = m["df"]
        amostra = df[df["categorizado"] & df["par_motor"].notna()]
        m["auditoria"] = {"falsos_positivos": motor.falsos_positivos(amostra), "alfa": motor.ALFA}
    return JSONResponse(m["auditoria"])


@protegido
def api_posts(request: Request):
    q, df = request.query_params, dados()["df"]
    for parametro, coluna in [
        ("segmento", "segmento"),
        ("formato", "formato_video"),
        ("tema", "tema_principal"),
        ("perfil", "handle"),
    ]:
        if q.get(parametro):
            df = df[df[coluna] == q[parametro]]
    if q.get("atributo"):  # só os posts em que a característica foi lida como presente
        m = dados()
        if "matriz" not in m:
            m["matriz"] = desfechos.caracteristicas(m["df"])
        if q["atributo"] not in m["matriz"]:
            return erro("Característica desconhecida.", 404)
        df = df[m["matriz"].loc[df.index, q["atributo"]] == 1]
    if q.get("top") == "1":
        df = df[df["top_tapi"]]
    if q.get("resto") == "1":
        df = df[~df["top_tapi"]]
    if q.get("fala") == "1":
        df = df[df["com_fala"]]
    if q.get("busca"):
        termo = q["busca"].lower()
        alvo = (df["titulo"] + " " + df["canal"]).str.lower()
        df = df[alvo.str.contains(termo, regex=False)]
    ordem = {"recentes": ("publicado_em", False), "views": ("views", False)}
    coluna, crescente = ordem.get(q.get("ordem", ""), ("posicao", True))
    df = df.sort_values(coluna, ascending=crescente)
    pagina = max(0, int(q.get("pagina", 0)))
    corte = df.iloc[pagina * POR_PAGINA : (pagina + 1) * POR_PAGINA]
    return JSONResponse(
        {
            "total": len(df),
            "no_top": int(df["top_tapi"].sum()),
            "por_pagina": POR_PAGINA,
            "posts": [painel.cartao(r) for r in corte.itertuples()],
        }
    )


@protegido
def api_post(request: Request):
    post = painel.detalhe(dados()["df"], request.path_params["id"])
    return JSONResponse(post) if post else erro("Post não encontrado.", 404)


def pagina_playbook(request: Request):
    return FileResponse(PAGINA.with_name("playbook.html"))


def validacao(request: Request):
    """Página das 50 validações: servida daqui porque o YouTube não toca em arquivo local."""
    arquivo = DADOS / "validacao.html"
    if not arquivo.is_file():
        return erro("Gere a página com scripts/validar.py gerar.", 404)
    return FileResponse(arquivo)


def documento_playbook(request: Request):
    arquivo = RAIZ / "docs" / "playbook.md"
    if not arquivo.is_file():
        return erro("O playbook ainda não foi gerado.", 404)
    return FileResponse(
        arquivo, media_type="text/markdown; charset=utf-8", filename="playbook-stone.md"
    )


@protegido
def api_playbook(request: Request):
    m = dados()
    if "playbook" not in m:
        m["playbook"] = playbook.tela(m["df"])
    return JSONResponse(m["playbook"])


@protegido
def api_execucoes(request: Request):
    """Execuções gravadas. Padrão que deixou de ser firme some da tela, mesmo nas antigas."""
    m = dados()
    if "firmes" not in m:
        m["firmes"] = {
            o: {p.atributo for p in duvidas.padroes_firmes(m["df"], o)}
            for o in duvidas.GRUPO_DO_OBJETIVO
        }
    with banco() as con:
        feitas = painel.execucoes(con, 100)
    for x in feitas:
        validos = m["firmes"].get(x["entrada"].get("objetivo") or "engajamento", set())
        padroes = x["saida"].get("patterns") or []
        x["saida"]["patterns"] = [p for p in padroes if p["atributo"] in validos]
    return JSONResponse(feitas)


async def _corpo(request: Request) -> dict:
    try:
        return await request.json()
    except ValueError:
        return {}


def api_consultar(corpo: dict):
    entrada = Entrada.model_validate(corpo)
    with banco(escrita=True) as con:
        saida = executar(con, modelo(), entrada, _memoria.get("df"))
        feitas = painel.execucoes(con, 1)
    return JSONResponse({**saida.model_dump(mode="json"), "etapas": feitas[0]["etapas"]})


def _hipoteses(con) -> JSONResponse:
    return JSONResponse([h.model_dump(mode="json") for h in hipoteses.ler(con)])


def api_propor(corpo: dict):
    if corpo.get("confirmo") != "travar":
        return erro("Propor trava as vagas para sempre. Envie confirmo='travar'.")
    with banco(escrita=True) as con:
        hipoteses.propor(con, base_completa(con), modelo())
        return _hipoteses(con)


def api_confirmar(corpo: dict):
    if corpo.get("confirmo") != "testar":
        return erro("O teste de confirmação roda uma única vez. Envie confirmo='testar'.")
    with banco(escrita=True) as con:
        hipoteses.confirmar(con, base_completa(con))
        return _hipoteses(con)


def api_aprovar(corpo: dict):
    with banco(escrita=True) as con:
        hipoteses.aprovar(con, str(corpo.get("id", "")))
        return _hipoteses(con)


def api_video_pedir(corpo: dict):
    """Gasta créditos do Feita: só roda com a duração escolhida pelo usuário na tela."""
    feito = video.pedir(
        str(corpo.get("gancho", "")), str(corpo.get("roteiro", "")), int(corpo.get("segundos", 8))
    )
    return JSONResponse(feito)


@protegido
def api_video(request: Request):
    return JSONResponse(video.situacao(request.path_params["id"]))


@protegido
def api_videos(request: Request):
    return JSONResponse(
        {
            "videos": video.lista(),
            "creditos_por_segundo": video.CREDITOS_POR_SEGUNDO,
            "bonecos": sorted(p.stem[7:] for p in ESTATICOS.glob("boneco-*.webm")),
        }
    )


def api_molde(request: Request):
    """Quais cenas 3D dos moldes já existem em data/moldes (arquivos cena-<nome>.mp4)."""
    pasta = video.PASTA.with_name("moldes")
    return JSONResponse({"cenas": sorted(p.stem[5:] for p in pasta.glob("cena-*.mp4"))})


def arquivo_molde(request: Request):
    arquivo = video.PASTA.with_name("moldes") / Path(request.path_params["nome"]).name
    if arquivo.suffix != ".mp4" or not arquivo.is_file():
        return erro("Cena não encontrada.", 404)
    return FileResponse(arquivo, media_type="video/mp4")


def arquivo_video(request: Request):
    arquivo = video.PASTA / Path(request.path_params["nome"]).name
    if arquivo.suffix != ".mp4" or not arquivo.is_file():
        return erro("Vídeo não encontrado.", 404)
    return FileResponse(arquivo, media_type="video/mp4")


def acao(funcao):
    """Rota POST: lê o JSON e roda a função (que usa o banco) fora do laço de eventos."""

    def trabalho(corpo: dict):
        dados()  # garante a base em memória antes de abrir o banco para escrita
        return funcao(corpo)

    seguro = protegido(trabalho)

    async def rota(request: Request):
        return await run_in_threadpool(seguro, await _corpo(request))

    return rota


rotas = [
    Route("/", inicio),
    Route("/maquininha", maquininha),
    Route("/antigo", antigo),
    Route("/prototipo", prototipo),
    Route("/api/duvidas", api_duvidas),
    Route("/api/exemplos", api_exemplos),
    Route("/playbook", pagina_playbook),
    Route("/playbook.md", documento_playbook),
    Route("/validacao", validacao),
    Route("/api/playbook", api_playbook),
    Route("/api/vitrine", api_vitrine),
    Route("/api/avaliar", acao(api_avaliar), methods=["POST"]),
    Route("/static/{nome}", estatico),
    Route("/api/painel", api_painel),
    Route("/api/auditoria", api_auditoria),
    Route("/api/posts", api_posts),
    Route("/api/posts/{id}", api_post),
    Route("/api/execucoes", api_execucoes),
    Route("/api/consultar", acao(api_consultar), methods=["POST"]),
    Route("/api/video", acao(api_video_pedir), methods=["POST"]),
    Route("/api/video/{id}", api_video),
    Route("/api/videos", api_videos),
    Route("/videos/{nome}", arquivo_video),
    Route("/api/molde", api_molde),
    Route("/moldes/{nome}", arquivo_molde),
    Route("/api/hipoteses/propor", acao(api_propor), methods=["POST"]),
    Route("/api/hipoteses/confirmar", acao(api_confirmar), methods=["POST"]),
    Route("/api/hipoteses/aprovar", acao(api_aprovar), methods=["POST"]),
]
app = Starlette(routes=rotas)


def main():
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("MPE_PORTA", "8010")))


if __name__ == "__main__":
    main()
