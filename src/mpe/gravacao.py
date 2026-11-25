"""Análise de gravação: o vídeo gravado a partir de um roteiro, conferido contra o próprio roteiro.

Duas partes. A checagem técnica (formato, som, silêncio, cortes) é medida aqui, na hora, sem LLM. A
análise de conteúdo é escrita fora da plataforma, a partir de quadros e transcrição
(scripts/preparar_gravacao.py), e entra por `gravar_analise`, que só aceita o formato abaixo. A
tela diz quem analisou. É leitura do vídeo contra o roteiro: não prevê resultado.
"""

import json
import re
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from mpe.ambiente import DADOS

PASTA = DADOS / "gravacoes"
TIPOS = {"video/mp4": ".mp4", "video/quicktime": ".mov", "video/webm": ".webm"}
LIMITE = 300 * 1024 * 1024
ID = re.compile(r"grav-[0-9a-f]{12}")
DURACAO_MAXIMA_S = 180  # limite de um Short
SILENCIO_MAXIMO_S, VOLUME_MINIMO_DB, FOLGA_DURACAO = 0.7, -30.0, 0.35


class Medidas(BaseModel):
    duracao_s: float
    largura: int
    altura: int
    tem_audio: bool
    volume_db: float | None = None
    silencio_inicial_s: float | None = None
    cortes: int | None = Field(default=None, description="nulo se as imagens não abriram")


class Item(BaseModel):
    ok: bool
    texto: str


class NoTempo(BaseModel):
    t: float = Field(ge=0, description="segundo do vídeo")
    texto: str = Field(min_length=5, max_length=240)


class Melhoria(NoTempo):
    como: str = Field(min_length=5, max_length=240, description="o que fazer na regravação")


class QuadroLido(BaseModel):
    na_tela: str
    no_video: Literal["sim", "em_parte", "nao"]
    t: float | None = None
    observacao: str = Field(max_length=240)


class PadraoLido(BaseModel):
    atributo: str
    tem: bool
    onde: str = Field(max_length=200)


class Analise(BaseModel):
    resumo: str = Field(min_length=10, max_length=400)
    fortes: list[NoTempo] = Field(default=[], max_length=5)
    melhorias: list[Melhoria] = Field(min_length=1, max_length=5)
    quadros: list[QuadroLido] = []
    padroes: list[PadraoLido] = []
    analisado_por: str = Field(min_length=3, max_length=80)


def _rodar(comando: list[str]) -> str:
    feito = subprocess.run(comando, capture_output=True, text=True, timeout=180)  # noqa: S603
    return feito.stdout + feito.stderr


def medir(arquivo: Path) -> Medidas:
    """Metadados e medidas de som e corte. ValueError se o arquivo não for um vídeo."""
    bruto = subprocess.run(  # noqa: S603
        ["ffprobe", "-v", "error", "-of", "json", "-show_format", "-show_streams", str(arquivo)],  # noqa: S607
        capture_output=True, text=True, timeout=60,
    ).stdout  # fmt: skip
    info = json.loads(bruto or "{}")
    fluxos = info.get("streams", [])
    imagem = next((f for f in fluxos if f.get("codec_type") == "video"), None)
    duracao = float(info.get("format", {}).get("duration") or 0)
    if imagem is None or duracao <= 0:
        raise ValueError("Este arquivo não parece ser um vídeo.")
    largura, altura = int(imagem["width"]), int(imagem["height"])
    girado = [abs(int(d.get("rotation", 0))) for d in imagem.get("side_data_list", [])]
    if any(g in (90, 270) for g in girado):  # celular grava deitado e marca a rotação
        largura, altura = altura, largura
    som = any(f.get("codec_type") == "audio" for f in fluxos)
    m = Medidas(duracao_s=duracao, largura=largura, altura=altura, tem_audio=som)
    if som:
        s = _rodar(
            ["ffmpeg", "-i", str(arquivo), "-vn", "-af",
             "silencedetect=noise=-40dB:d=0.3,volumedetect", "-f", "null", "-"]
        )  # fmt: skip
        if v := re.search(r"mean_volume: (-?[\d.]+) dB", s):
            m.volume_db = float(v[1])
            inicio = re.search(r"silence_start: (-?[\d.]+)", s)
            fim = re.search(r"silence_end: ([\d.]+)", s)
            comeca_mudo = inicio and float(inicio[1]) <= 0.05
            m.silencio_inicial_s = (float(fim[1]) if fim else duracao) if comeca_mudo else 0.0
    s = _rodar(
        ["ffmpeg", "-i", str(arquivo), "-an", "-vf", "scale=240:-2,select='gt(scene,0.3)',showinfo",
         "-f", "null", "-"]
    )  # fmt: skip
    if re.search(r"frame=\s*\d+|muxing overhead", s) and "Error while decoding" not in s:
        m.cortes = len(re.findall(r"pts_time:", s))
    return m


def checar(m: Medidas, roteiro_s: int | None) -> list[Item]:
    proporcao = m.altura / m.largura
    itens = [
        Item(ok=proporcao >= 1.6, texto="Vídeo em pé (9:16)" if proporcao >= 1.6
             else f"O vídeo não está em pé: {m.largura} por {m.altura}. Grave na vertical."),
        Item(ok=m.duracao_s <= DURACAO_MAXIMA_S, texto=f"{m.duracao_s:.0f} s de duração"
             + ("" if m.duracao_s <= DURACAO_MAXIMA_S else ": passa do limite de 3 minutos")),
    ]  # fmt: skip
    if roteiro_s:
        perto = abs(m.duracao_s - roteiro_s) <= roteiro_s * FOLGA_DURACAO
        itens.append(
            Item(ok=perto, texto=f"O roteiro prevê {roteiro_s} s"
                 + ("" if perto else f", e o vídeo tem {m.duracao_s:.0f} s"))
        )  # fmt: skip
    if not m.tem_audio or m.volume_db is None:
        itens.append(Item(ok=False, texto="O vídeo está sem som"))
    else:
        alto = m.volume_db >= VOLUME_MINIMO_DB
        itens.append(Item(ok=alto, texto="Som com volume bom" if alto
                          else f"Som baixo ({m.volume_db:.0f} dB em média). Aproxime o microfone."))  # fmt: skip
        mudo = m.silencio_inicial_s or 0.0
        cedo = mudo <= SILENCIO_MAXIMO_S
        itens.append(Item(ok=cedo, texto="Começa falando na hora" if cedo
                          else f"Começa com {mudo:.1f} s de silêncio. Corte esse trecho."))  # fmt: skip
    return itens


def caminho(id_: str) -> Path | None:
    if not ID.fullmatch(id_):
        return None
    return next((p for e in TIPOS.values() if (p := PASTA / f"{id_}{e}").is_file()), None)


def registrar(temporario: Path, tipo: str, run_id: str, versao: int, criativo: dict) -> dict:
    """Mede o vídeo recebido e o põe na fila. Arquivo que não é vídeo é recusado e apagado."""
    try:
        medidas = medir(temporario)
    except (ValueError, KeyError, subprocess.SubprocessError) as e:
        temporario.unlink(missing_ok=True)
        raise ValueError("Este arquivo não parece ser um vídeo.") from e
    id_ = f"grav-{uuid.uuid4().hex[:12]}"
    cenas = criativo.get("cenas") or []
    fim = max((c["fim_s"] for c in cenas), default=None)
    destino = PASTA / f"{id_}{TIPOS[tipo]}"
    temporario.replace(destino)
    registro = {
        "id": id_, "run_id": run_id, "versao": versao, "criativo": criativo,
        "quando": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "arquivo": f"/gravacoes/{destino.name}", "medidas": medidas.model_dump(),
        "checagem": [i.model_dump() for i in checar(medidas, fim)],
    }  # fmt: skip
    (PASTA / f"{id_}.json").write_text(json.dumps(registro, ensure_ascii=False, indent=1))
    return ler(id_)


def ler(id_: str) -> dict:
    if not ID.fullmatch(id_) or not (PASTA / f"{id_}.json").is_file():
        raise ValueError("Gravação não encontrada.")
    registro = json.loads((PASTA / f"{id_}.json").read_text())
    feita = PASTA / f"{id_}.analise.json"
    registro["analise"] = json.loads(feita.read_text()) if feita.is_file() else None
    return registro


def listar(run_id: str | None = None) -> list[dict]:
    """Mais novas primeiro."""
    arquivos = [p for p in PASTA.glob("grav-*.json") if not p.name.endswith(".analise.json")]
    feitas = [ler(p.stem) for p in sorted(arquivos, key=lambda p: -p.stat().st_mtime)]
    return [g for g in feitas if run_id in (None, g["run_id"])]


def gravar_analise(id_: str, analise: dict) -> Analise:
    """Única porta de entrada da análise: confere o formato, os tempos e os padrões."""
    registro = ler(id_)
    a = Analise.model_validate(analise)
    fim = registro["medidas"]["duracao_s"]
    tempos = [x.t for x in [*a.fortes, *a.melhorias, *a.quadros] if x.t is not None]
    if fora := [t for t in tempos if t > fim]:
        raise ValueError(f"tempo depois do fim do vídeo ({fim:.1f} s): {fora}")
    cenas = {c["na_tela"] for c in registro["criativo"].get("cenas") or []}
    if cenas and (estranhos := [q.na_tela for q in a.quadros if q.na_tela not in cenas]):
        raise ValueError(f"quadro que não está no roteiro: {estranhos}")
    (PASTA / f"{id_}.analise.json").write_text(a.model_dump_json(indent=1))
    return a
