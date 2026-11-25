"""Vídeo de exemplo de um criativo, gerado por um modelo de vídeo no gateway do Feita.

O pedido é assíncrono: `pedir` devolve o id, `situacao` consulta e, quando fica pronto, baixa o
MP4 para data/videos (o link do gateway expira em um dia). Cada vídeo tem um arquivo .json ao lado
com o criativo, o prompt e o custo: é o registro, sem tocar no banco.
"""

import json
import os
import re
from datetime import datetime

import httpx

from mpe.ambiente import DADOS
from mpe.feita import SEM_CREDITO, chaves
from mpe.gemini import CotaEsgotada

URL = "https://api.feita.ai/gateway/v1/videos"
MODELO = os.environ.get("MPE_VIDEO_MODELO", "google/veo-3.1-lite")
PASTA = DADOS / "videos"
SEGUNDOS = (4, 8)
CREDITOS_POR_SEGUNDO = 5  # medido em 23/11/2026: 4 s em 720p com áudio custaram 20 créditos
ID_VALIDO = re.compile(r"^[A-Za-z0-9_-]{8,80}$")
MODELO_PROMPT = """Vertical 9:16 smartphone video, authentic Brazilian small-business social media \
style, handheld camera, natural light. Scene: {cena}
A Brazilian small business owner looks at the camera and says, in Brazilian Portuguese: "{fala}"
No on-screen text, no subtitles, no captions, no logos."""


def fala_curta(gancho: str, palavras: int = 24) -> str:
    """A primeira frase do gancho, no tamanho que cabe em poucos segundos de fala."""
    frase = re.split(r"(?<=[.!?])\s", gancho.strip())[0]
    return " ".join(frase.split()[:palavras]).replace('"', "'")


def montar_prompt(gancho: str, roteiro: str) -> str:
    cena = " ".join(roteiro.split())[:500].replace('"', "'")
    return MODELO_PROMPT.format(cena=cena, fala=fala_curta(gancho))


def _falha(r, o_que: str) -> RuntimeError:
    """Erro legível: o gateway às vezes devolve uma página HTML inteira."""
    corpo = r.text.strip()
    detalhe = "" if corpo.startswith("<") else f": {corpo[:200]}"
    return RuntimeError(f"a Feita respondeu {r.status_code} ao {o_que}{detalhe}")


def _registro(id_: str):
    if not ID_VALIDO.match(id_):
        raise ValueError("identificador de vídeo inválido")
    return PASTA / f"{id_}.json"


def _gravar(dados: dict) -> dict:
    PASTA.mkdir(parents=True, exist_ok=True)
    _registro(dados["id"]).write_text(json.dumps(dados, ensure_ascii=False, indent=1))
    return dados


def _publico(dados: dict) -> dict:
    return {k: v for k, v in dados.items() if k != "conta"}


def pedir(gancho: str, roteiro: str, segundos: int = 8, cliente=None) -> dict:
    if segundos not in SEGUNDOS:
        raise ValueError(f"duração deve ser uma de {SEGUNDOS} segundos")
    if len(gancho.strip()) < 5:
        raise ValueError("o criativo precisa de um gancho")
    http, lista = cliente or httpx.Client(timeout=60), chaves()
    if not lista:
        raise RuntimeError("falta FEITA_API_KEYS no .env")
    prompt = montar_prompt(gancho, roteiro)
    corpo = {
        "model": MODELO,
        "prompt": prompt,
        "duration": segundos,
        "resolution": "720p",
        "aspect_ratio": "9:16",
        "generate_audio": True,
    }
    for conta, chave in enumerate(lista):
        r = http.post(URL, headers={"Authorization": f"Bearer {chave}"}, json=corpo)
        if r.status_code in SEM_CREDITO:
            continue
        if r.status_code >= 400:
            raise _falha(r, "pedir o vídeo")
        return _publico(
            _gravar(
                {
                    "id": r.json()["id"],
                    "status": "pending",
                    "gancho": gancho,
                    "roteiro": roteiro,
                    "prompt": prompt,
                    "segundos": segundos,
                    "modelo": MODELO,
                    "conta": conta,
                    "quando": datetime.now().strftime("%d/%m/%Y %H:%M"),
                }
            )
        )
    raise CotaEsgotada(f"créditos esgotados nas {len(lista)} contas do Feita")


def situacao(id_: str, cliente=None) -> dict:
    """Estado do pedido. Quando o gateway termina, baixa o MP4 e passa a responder do disco."""
    caminho = _registro(id_)
    if not caminho.exists():
        raise ValueError("vídeo não encontrado")
    dados = json.loads(caminho.read_text())
    if dados["status"] in ("completed", "failed"):
        return _publico(dados)
    http, chave = cliente or httpx.Client(timeout=120), chaves()[dados["conta"]]
    cabecalho = {"Authorization": f"Bearer {chave}"}
    r = http.get(f"{URL}/{id_}", headers=cabecalho)
    if r.status_code >= 400:
        raise _falha(r, "consultar o vídeo")
    resposta = r.json()
    estado = resposta.get("status", "pending")
    if estado == "completed":
        mp4 = http.get(f"{URL}/{id_}/content?index=0", headers=cabecalho, follow_redirects=True)
        if mp4.status_code >= 400:
            raise _falha(mp4, "baixar o vídeo")
        (PASTA / f"{id_}.mp4").write_bytes(mp4.content)
        dados |= {
            "status": "completed",
            "arquivo": f"/videos/{id_}.mp4",
            "creditos": resposta.get("usage", {}).get("credits"),
        }
        _gravar(dados)
    elif estado in ("failed", "cancelled", "expired"):
        erro = resposta.get("error") or estado
        dados |= {"status": "failed", "erro": str(erro)[:300]}
        _gravar(dados)
    return _publico(dados)


def lista() -> list[dict]:
    """Vídeos já pedidos, mais recentes primeiro."""
    if not PASTA.exists():
        return []
    arquivos = sorted(PASTA.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [_publico(json.loads(p.read_text())) for p in arquivos]
