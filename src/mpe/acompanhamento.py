"""Acompanha o Short publicado a partir de um roteiro: lê, de tempos em tempos, o que é público.

Cada leitura guarda visualizações, curtidas, comentários e inscritos (API oficial do YouTube) e
classifica os comentários novos, para contar pedidos de contato. O agendador roda junto com a
plataforma (`ligar`) ou por fora (scripts/acompanhar.py). Guarda só a classe de cada comentário,
não o texto. Mostra o que aconteceu com o vídeo: não diz que o roteiro foi a causa.
"""

import json
import logging
import re
import threading
from datetime import UTC, datetime, timedelta

import httpx
import pandas as pd

from mpe.ambiente import DADOS
from mpe.coleta import DURACAO_MAXIMA_S, IDADE_MINIMA
from mpe.comentarios import classificar
from mpe.duvidas import GRUPO_DO_OBJETIVO, nome, padroes_firmes
from mpe.motor import matriz
from mpe.rubrica import CAMPOS_QUADROS

PASTA = DADOS / "acompanhados"
INTERVALO = timedelta(hours=6)  # entre leituras do mesmo vídeo: 3 unidades de cota cada uma
ATE = timedelta(days=60)  # depois disso o agendador para de ler
VOLTA_S = 600  # de quanto em quanto o agendador procura vídeo com leitura vencida
LOTE = 40
MIN_CANAL, TOPO_DO_CANAL, RARO = 20, 0.9, 0.25  # quando um vídeo sugere um viés novo
TRAVA = threading.RLock()
ID = re.compile(r"[A-Za-z0-9_-]{11}")
LINK = re.compile(
    r"^(?:https?://)?(?:www\.|m\.)?(?:youtube\.com/(?:shorts/|watch\?(?:.*&)?v=)|youtu\.be/)"
    r"([A-Za-z0-9_-]{11})(?:[?&/#].*)?$"
)
log = logging.getLogger(__name__)


def agora() -> datetime:
    return datetime.now(UTC)


def id_do_link(link: str) -> str:
    achado = LINK.match(link.strip())
    if not achado:
        raise ValueError("Cole o link de um Short do YouTube.")
    return achado[1]


def comentarios(yt, id_: str, canal_id: str) -> dict[str, str]:
    """Até 100 comentários (id e texto), sem os do próprio canal. Vazio se estiverem fechados."""
    try:
        dados = yt._get(
            "commentThreads", part="snippet", videoId=id_, maxResults=100, order="time",
            textFormat="plainText",
        )  # fmt: skip
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403 and "commentsDisabled" in e.response.text:
            return {}
        raise
    saida = {}
    for t in dados.get("items", []):
        c = t["snippet"]["topLevelComment"]["snippet"]
        if (c.get("authorChannelId") or {}).get("value") != canal_id and c["textDisplay"].strip():
            saida[t["id"]] = c["textDisplay"][:500]
    return saida


def _arquivo(id_: str):
    if not ID.fullmatch(id_):
        raise ValueError("Vídeo não encontrado.")
    return PASTA / f"{id_}.json"


def ler(id_: str) -> dict:
    arquivo = _arquivo(id_)
    if not arquivo.is_file():
        raise ValueError("Vídeo não encontrado.")
    return json.loads(arquivo.read_text())


def _salvar(r: dict):
    PASTA.mkdir(parents=True, exist_ok=True)
    parte = _arquivo(r["id"]).with_suffix(".parte")
    parte.write_text(json.dumps(r, ensure_ascii=False, indent=1))
    parte.replace(_arquivo(r["id"]))


def listar(run_id: str | None = None) -> list[dict]:
    feitos = [json.loads(p.read_text()) for p in PASTA.glob("*.json")]
    feitos = [r for r in feitos if run_id in (None, r["run_id"])]
    return sorted(feitos, key=lambda r: r["desde"], reverse=True)


def adicionar(link: str, run_id: str, versao: int, yt, llm, historico=()) -> dict:
    id_ = id_do_link(link)
    with TRAVA:
        if _arquivo(id_).is_file():
            r = ler(id_)
            if run_id and (r["run_id"], r["versao"]) != (run_id, versao):
                raise ValueError("Este vídeo já é acompanhado em outro roteiro.")
            r["ativo"] = True
            _salvar(r)
            return atualizar(id_, yt, llm)
        achados = yt.videos([id_])
        if not achados:
            raise ValueError("Não achei este vídeo. Ele precisa estar público.")
        v = achados[0]
        if v["duracao_s"] > DURACAO_MAXIMA_S:
            raise ValueError("Este vídeo não é um Short: passa de 3 minutos.")
        _salvar(
            {
                "id": id_, "run_id": run_id, "versao": versao, "titulo": v["titulo"],
                "canal_id": v["canal_id"], "canal": "", "publicado_em": v["publicado_em"],
                "desde": agora().isoformat(), "ativo": True, "medidas": list(historico), "classes": {},
                "erro": "",
            }
        )  # fmt: skip
        return atualizar(id_, yt, llm)


def atualizar(id_: str, yt, llm) -> dict:
    """Uma leitura. Se a classificação falhar, os números entram e os comentários ficam para
    a próxima."""
    with TRAVA:
        r = ler(id_)
        achados = yt.videos([id_])
        if not achados:
            r["ativo"], r["erro"] = False, "O vídeo saiu do ar ou ficou privado."
            _salvar(r)
            return r
        v, r["erro"] = achados[0], ""
        canal = next(iter(yt.canais([r["canal_id"]])), None) or {}
        r["canal"] = canal.get("titulo", r["canal"])
        try:
            textos = comentarios(yt, id_, r["canal_id"])
            novos = [(c, t) for c, t in textos.items() if c not in r["classes"]]
            for i in range(0, len(novos), LOTE):
                lote = novos[i : i + LOTE]
                classes = classificar(llm(), [t for _, t in lote])
                r["classes"] |= {
                    c: k for (c, _), k in zip(lote, classes, strict=True) if k
                }  # fmt: skip
        except Exception:  # noqa: BLE001  os números não dependem da IA
            log.exception("comentários de %s", id_)
            r["erro"] = "Os números entraram, mas os comentários não foram lidos desta vez."
        r["medidas"].append(
            {
                "quando": agora().isoformat(), "views": v["views"], "likes": v["likes"],
                "comentarios": v["comentarios"], "inscritos": canal.get("inscritos"),
                "pedidos": sum(k == "intencao" for k in r["classes"].values()),
                "lidos": len(r["classes"]),
            }
        )  # fmt: skip
        _salvar(r)
        return r


def parar(id_: str) -> dict:
    with TRAVA:
        r = ler(id_)
        r["ativo"] = False
        _salvar(r)
        return r


def vencido(r: dict, quando: datetime | None = None) -> bool:
    quando = quando or agora()
    if not r["ativo"] or quando - datetime.fromisoformat(r["desde"]) > ATE:
        return False
    if not r["medidas"]:
        return True
    return quando - datetime.fromisoformat(r["medidas"][-1]["quando"]) >= INTERVALO


def _milhar(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def analisar(r: dict, corte_topo: float | None = None) -> dict:
    """O que as leituras dizem, em frases. `corte_topo`: menor engajamento entre os 10% do topo."""
    if not r["medidas"]:
        return {"frases": [], "idade_dias": 0, "proxima": None}
    m, frases = r["medidas"][-1], []
    quando = datetime.fromisoformat(m["quando"])
    idade = quando - datetime.fromisoformat(r["publicado_em"].replace("Z", "+00:00"))
    if len(r["medidas"]) > 1 and m["views"] is not None:
        a = r["medidas"][-2]
        horas = (quando - datetime.fromisoformat(a["quando"])).total_seconds() / 3600
        if a["views"] is not None and horas >= 1:
            ganho = m["views"] - a["views"]
            sinal = "+" if ganho > 0 else "-"
            frases.append(
                f"{sinal}{_milhar(abs(ganho))} visualizações em {horas:.0f} h."
                if ganho
                else f"Sem visualizações novas nas últimas {horas:.0f} h."
            )
    if m["lidos"]:
        frases.append(
            f"Pedem preço, link ou contato: {m['pedidos']} de {m['lidos']} comentários lidos."
        )
    else:
        frases.append("Ainda sem comentários lidos: não dá para falar de pedido de contato.")
    partes = (m["likes"], m["comentarios"], m["inscritos"])
    if None not in partes and m["inscritos"]:
        engajamento = (m["likes"] + m["comentarios"]) / m["inscritos"]
        texto = f"Engajamento de {engajamento:.2%}".replace(".", ",") + " dos inscritos"
        if idade < IDADE_MINIMA:
            frases.append(f"{texto}. Cedo para comparar: a base só tem vídeos com 14 dias ou mais.")
        elif corte_topo is not None:
            corte = f"{corte_topo:.2%}".replace(".", ",")
            onde = "acima" if engajamento >= corte_topo else "abaixo"
            frases.append(f"{texto}, {onde} do corte dos 10% do topo da base ({corte}).")
    proxima = (quando + INTERVALO).isoformat() if r["ativo"] else None
    return {"frases": frases, "idade_dias": max(0, idade.days), "proxima": proxima}


def leitura_da_base(df: pd.DataFrame, id_: str) -> list[dict]:
    """Se o vídeo já está na base, a coleta vira a primeira leitura."""
    achado = df[df["id"] == id_]
    if achado.empty:
        return []
    v = achado.iloc[0]
    numero = {c: None if pd.isna(v[c]) else int(v[c]) for c in ("views", "likes", "comentarios")}
    quando = pd.Timestamp(v["coletado_em"]).tz_localize("UTC").isoformat()
    inscritos = None if pd.isna(v["inscritos"]) else int(v["inscritos"])
    return [{"quando": quando, **numero, "inscritos": inscritos, "pedidos": 0, "lidos": 0}]


def firmes_de(df: pd.DataFrame) -> set[str]:
    return {p.atributo for o in GRUPO_DO_OBJETIVO for p in padroes_firmes(df, o)}


def vies(df: pd.DataFrame, id_: str, firmes: set[str] | None = None) -> dict:
    """Este vídeo sugere algo que os padrões firmes ainda não dizem?

    Sugere (indício) se está entre os 10% melhores do próprio canal e faz algo raro nele que não é
    padrão firme. Um vídeo só nunca vira regra: no máximo, uma hipótese para testar."""
    achado = df[(df["id"] == id_) & df["categorizado"]]
    if achado.empty:
        texto = "As características dele ainda não foram lidas: entra na próxima atualização."
        return {"surge": None, "titulo": "Ainda não dá para dizer", "texto": texto}
    handle = achado.iloc[0]["handle"]
    canal = df[(df["handle"] == handle) & df["categorizado"]].reset_index(drop=True)
    if len(canal) < MIN_CANAL:
        texto = f"O canal tem só {len(canal)} vídeos lidos, pouco para comparar."
        return {"surge": None, "titulo": "Ainda não dá para dizer", "texto": texto}
    i = int(canal.index[canal["id"] == id_][0])
    posicao = int(canal["engajamento"].rank(ascending=False, method="min")[i])
    onde = f"{posicao}º de {len(canal)} vídeos do canal em engajamento"
    if posicao > len(canal) * (1 - TOPO_DO_CANAL):
        texto = f"É o {onde}, fora dos 10% melhores. Nada a recomendar a partir dele."
        return {"surge": False, "titulo": "Não surge viés novo", "texto": texto}
    x = matriz(canal)
    tem = [
        c for c in x.columns
        if c.split("=")[0] in CAMPOS_QUADROS and not c.startswith("tema_principal")
        and x.loc[i, c] == 1
    ]  # fmt: skip
    firmes = firmes_de(df) if firmes is None else firmes
    raros = [c for c in tem if c not in firmes and x[c].mean() <= RARO]
    segue = [nome(c) for c in tem if c in firmes and c != "formato_video=talking_head"]
    confirma = f" Também segue um padrão que já temos: {', '.join(segue).lower()}." if segue else ""
    if not raros:
        texto = f"É o {onde}, mas não faz nada raro no canal além do que já recomendamos.{confirma}"
        return {"surge": False, "titulo": "Não surge viés novo", "texto": texto}
    ditos = " e ".join(f"{nome(c).lower()} ({x[c].mean():.0%} dos vídeos do canal)" for c in raros)
    texto = f"É o {onde} e faz algo raro nele: {ditos}.{confirma}"
    return {"surge": True, "titulo": "Surge um indício novo", "texto": texto}


def rodar_vencidos(yt, llm) -> int:
    """Uma passada do agendador. Falha de um vídeo não para os outros."""
    feitos = 0
    for r in listar():
        if not vencido(r):
            continue
        try:
            atualizar(r["id"], yt, llm)
            feitos += 1
        except Exception:  # noqa: BLE001
            log.exception("acompanhamento de %s", r["id"])
    return feitos


def ligar(yt, llm) -> threading.Event:
    """Agendador dentro da plataforma. `yt` e `llm` são funções: só abrem quando há o que ler."""
    fim = threading.Event()

    def laco():
        while not fim.is_set():
            try:
                if any(vencido(r) for r in listar()):
                    rodar_vencidos(yt(), llm)
            except Exception:  # noqa: BLE001  o agendador não pode cair
                log.exception("agendador")
            fim.wait(VOLTA_S)

    threading.Thread(target=laco, daemon=True, name="acompanhamento").start()
    return fim
