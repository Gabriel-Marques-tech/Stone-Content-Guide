"""Vídeo de prévia (animação com voz) de cada criativo pronto, feito nesta máquina e sem créditos.

    uv run --no-project --with playwright --with edge-tts --with numpy --with httpx \
        --with imageio-ffmpeg python scripts/gerar_previa.py [trecho do gancho]

A plataforma precisa estar no ar (lê /api/execucoes). As falas vêm de scripts/narracoes.json,
escritas para a prévia a partir das cenas. Cada vídeo vai para data/videos com um .json ao lado,
no mesmo formato do registro da Feita e com tipo "previa".
"""

import asyncio
import base64
import hashlib
import json
import subprocess
import sys
import tempfile
import wave
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import edge_tts
import httpx
import numpy as np
from imageio_ffmpeg import get_ffmpeg_exe  # o ffmpeg do Fedora vem sem H.264
from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).parents[1]
PASTA = RAIZ / "data" / "videos"
FPS, TAXA = 25, 44100
RESPIRO = 0.42  # silêncio depois de cada fala


async def _voz(texto: str, voz: str, destino: Path) -> list[dict]:
    com = edge_tts.Communicate(texto, f"pt-BR-{voz}Neural", rate="+8%", boundary="WordBoundary")
    palavras, audio = [], b""
    async for x in com.stream():
        if x["type"] == "audio":
            audio += x["data"]
        else:
            t = x["offset"] / 1e7
            palavras.append({"p": x["text"], "t": t, "f": t + x["duration"] / 1e7})
    destino.write_bytes(audio)
    return palavras


def falar(texto: str, voz: str, destino: Path) -> list[dict]:
    """Gera a voz e devolve o tempo de cada palavra, com a pontuação do texto original."""
    # o Playwright já ocupa o laço desta thread; a voz roda em outra
    with ThreadPoolExecutor(1) as fora:
        palavras = fora.submit(asyncio.run, _voz(texto, voz, destino)).result()
    originais = texto.split()
    if len(originais) == len(palavras):
        for w, o in zip(palavras, originais, strict=True):
            w["p"] = o
    return palavras


def agrupar(palavras: list[dict], maximo: int = 4) -> list[dict]:
    """Legenda em blocos curtos; quebra na pontuação."""
    grupos, atual = [], []
    for w in palavras:
        atual.append(w)
        if len(atual) == maximo or w["p"][-1] in ".,?!:":
            grupos.append(atual)
            atual = []
    if atual:
        grupos.append(atual)
    # palavra sozinha fica com o bloco anterior, se a frase é a mesma
    juntos = grupos[:1]
    for g in grupos[1:]:
        if len(g) == 1 and juntos[-1][-1]["p"][-1] not in ".?!":
            juntos[-1] += g
        else:
            juntos.append(g)
    grupos = juntos
    saida = []
    for i, g in enumerate(grupos):
        fim = grupos[i + 1][0]["t"] - 0.05 if i + 1 < len(grupos) else g[-1]["f"] + 0.3
        saida.append({"palavras": g, "fim": fim})
    return saida


def ler_audio(caminho: Path) -> np.ndarray:
    cru = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(caminho), "-f", "s16le", "-ac", "1", "-ar", str(TAXA)]
        + ["-"],
        capture_output=True,
        check=True,
    ).stdout
    return np.frombuffer(cru, dtype=np.int16).astype(np.float32) / 32768


def trilha(segundos: float) -> np.ndarray:
    """Batida leve feita por síntese: bumbo, chimbal e baixo."""
    n = int(segundos * TAXA)
    som, passo, sorteio = np.zeros(n + TAXA), 60 / 104, np.random.default_rng(7)
    notas = [110.0, 110.0, 130.81, 98.0]
    for k in range(int(segundos / passo) + 1):
        i, t = int(k * passo * TAXA), np.arange(int(0.35 * TAXA)) / TAXA
        bumbo = np.sin(2 * np.pi * (45 * t + 8 * (1 - np.exp(-t * 28)))) * np.exp(-t * 11)
        som[i : i + len(t)] += bumbo[: len(som) - i] * 0.8
        baixo = np.sin(2 * np.pi * notas[(k // 4) % 4] * t) * np.exp(-t * 7)
        som[i : i + len(t)] += baixo * 0.35
        j, th = i + int(passo / 2 * TAXA), np.arange(int(0.06 * TAXA)) / TAXA
        if j + len(th) < len(som):
            som[j : j + len(th)] += sorteio.normal(size=len(th)) * np.exp(-th * 70) * 0.12
    return som[:n]


def gravar_wav(som: np.ndarray, destino: Path):
    with wave.open(str(destino), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        w.writeframes((np.clip(som, -1, 1) * 32767).astype(np.int16).tobytes())


def bonecos(roteiro: list[dict], pagina) -> dict:
    """Quadros do boneco 3D das cenas deste roteiro, quando já renderizados."""
    nomes = pagina.evaluate(
        "(cs) => { const v = new Set(); return cs.map((c) => qualDesenho(c, v)); }",
        [c["cena"] for c in roteiro],
    )
    saida = {}
    for n in set(nomes):
        quadros = sorted((RAIZ / "data" / "bonecos" / n).glob("*.webp"))
        if quadros:
            saida[n] = [
                "data:image/webp;base64," + base64.b64encode(q.read_bytes()).decode()
                for q in quadros
            ]
    return saida


def gerar(pagina, criativo: dict, narracao: dict, tmp: Path) -> dict:
    cenas, falas = criativo["cenas"], narracao["falas"]
    if len(cenas) != len(falas):
        raise ValueError(f"{len(falas)} falas para {len(cenas)} cenas: {criativo['gancho']}")
    t, roteiro, vozes = 0.0, [], []
    for i, (c, f) in enumerate(zip(cenas, falas, strict=True)):
        mp3 = tmp / f"{i}.mp3"
        palavras = falar(f, narracao["voz"], mp3)
        audio = ler_audio(mp3)
        util = np.flatnonzero(np.abs(audio) > 0.01)
        audio = audio[: util[-1] + int(0.1 * TAXA)]
        duracao = len(audio) / TAXA + RESPIRO + (0.9 if i == len(cenas) - 1 else 0)
        vozes.append((t, audio))
        na_tela = c["na_tela"].replace("[", "").replace("]", "")
        roteiro.append(
            {"na_tela": na_tela, "cena": c["cena"], "ini": t, "fim": t + duracao}
            | {"grupos": agrupar(palavras)}
        )
        t += duracao
    som = np.zeros(int(t * TAXA) + TAXA, dtype=np.float32)
    for ini, a in vozes:
        i = int((ini + 0.08) * TAXA)
        som[i : i + len(a)] += a * 0.95
    fundo = trilha((len(som) + 2) / TAXA)  # folga para o arredondamento
    som += (fundo * 0.085)[: len(som)]
    fim = int(0.8 * TAXA)
    corte = int(t * TAXA)
    som = som[:corte]
    som[-fim:] *= np.linspace(1, 0, fim)
    wav = tmp / "som.wav"
    gravar_wav(som, wav)

    id_ = "previa-" + hashlib.sha1(criativo["gancho"].encode()).hexdigest()[:12]
    saida = PASTA / f"{id_}.mp4"
    pagina.evaluate(
        """(r) => { r.cenas.forEach((c) => { c.grupos = c.grupos.map((g) =>
            Object.assign(g.palavras, {fim: g.fim})); }); iniciar(r); }""",
        {"cenas": roteiro, "bonecos": bonecos(roteiro, pagina)},
    )
    ff = subprocess.Popen(
        [get_ffmpeg_exe(), "-y", "-v", "error", "-f", "image2pipe", "-c:v", "mjpeg", "-r", str(FPS)]
        + ["-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", "fast", "-crf", "20"]
        + ["-vf", "scale=in_range=full:out_range=tv:out_color_matrix=bt709"]
        + ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
        + ["-color_range", "tv", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags"]
        + ["+faststart", "-g", str(FPS), "-shortest", str(saida)],
        stdin=subprocess.PIPE,
    )
    for k in range(int(t * FPS)):
        pagina.evaluate("ir", k / FPS)
        ff.stdin.write(pagina.screenshot(type="jpeg", quality=92))
    ff.stdin.close()
    if ff.wait():
        raise RuntimeError("o ffmpeg falhou")
    registro = {
        "id": id_,
        "tipo": "previa",
        "status": "completed",
        "gancho": criativo["gancho"],
        "roteiro": criativo["roteiro"],
        "segundos": round(t, 1),
        "modelo": "animação 3D local (Blender) + voz sintética (edge-tts)",
        "cortes": [[round(c["ini"], 2), round(c["fim"], 2)] for c in roteiro],
        "falas": falas,
        "quando": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "arquivo": f"/videos/{id_}.mp4",
        "creditos": 0,
    }
    (PASTA / f"{id_}.json").write_text(json.dumps(registro, ensure_ascii=False, indent=1))
    return registro


def main():
    filtro = " ".join(sys.argv[1:]).lower()
    narracoes = json.loads((RAIZ / "scripts" / "narracoes.json").read_text())
    execucoes = httpx.get("http://127.0.0.1:8010/api/execucoes", timeout=60).json()
    criativos = {}
    for x in execucoes:
        for c in x["saida"].get("creatives", []):
            if c["gancho"] in narracoes and len(c.get("cenas") or []) > 2:
                criativos.setdefault(c["gancho"], c)
    html = (RAIZ / "scripts" / "previa.html").read_text()
    desenhos = (RAIZ / "src" / "mpe" / "static" / "desenhos.js").read_text()
    PASTA.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        navegador = p.chromium.launch(channel="chrome")
        pagina = navegador.new_page(viewport={"width": 720, "height": 1280})
        pagina.set_content(html.replace("/*DESENHOS*/", desenhos), wait_until="networkidle")
        pagina.evaluate(
            """() => Promise.all([document.fonts.load('800 100px "Bricolage Grotesque"'),
            document.fonts.load('800 50px Figtree')])"""
        )
        for gancho, c in criativos.items():
            if filtro in gancho.lower():
                with tempfile.TemporaryDirectory() as tmp:
                    r = gerar(pagina, c, narracoes[gancho], Path(tmp))
                print(r["segundos"], "s", r["arquivo"], gancho, flush=True)
        navegador.close()


if __name__ == "__main__":
    main()
