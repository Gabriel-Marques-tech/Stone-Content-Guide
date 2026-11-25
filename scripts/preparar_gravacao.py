"""Prepara uma gravação enviada para análise: folhas de quadros com o tempo e o áudio em 16 kHz.

    uv run --with pillow --with imageio-ffmpeg python scripts/preparar_gravacao.py            # a fila
    uv run --with pillow --with imageio-ffmpeg python scripts/preparar_gravacao.py grav-...   # uma

A análise escrita entra com:
    uv run python scripts/preparar_gravacao.py --gravar grav-... analise.json
"""

import json
import subprocess
import sys
from pathlib import Path

from mpe import gravacao


def preparar(g: dict):
    from imageio_ffmpeg import get_ffmpeg_exe
    from PIL import Image, ImageDraw

    ff, video = get_ffmpeg_exe(), gravacao.caminho(g["id"])
    pasta = gravacao.PASTA / g["id"]
    pasta.mkdir(exist_ok=True)
    passo = max(0.5, g["medidas"]["duracao_s"] / 60)
    subprocess.run([ff, "-v", "error", "-y", "-i", str(video), "-vf", f"fps=1/{passo},scale=-2:480",  # noqa: S603
                    str(pasta / "q%03d.jpg")], check=True)  # fmt: skip
    if g["medidas"]["tem_audio"]:
        subprocess.run([ff, "-v", "error", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000",  # noqa: S603
                        str(pasta / "audio.wav")], check=True)  # fmt: skip
    quadros = sorted(pasta.glob("q*.jpg"))
    for n in range(0, len(quadros), 12):
        imagens = [Image.open(q).convert("RGB") for q in quadros[n : n + 12]]
        largura, altura = imagens[0].size
        folha = Image.new("RGB", (largura * 6, altura * 2))
        for k, im in enumerate(imagens):
            ImageDraw.Draw(im).text((8, 8), f"{(n + k) * passo:.1f}s", fill="yellow", font_size=30)
            folha.paste(im, ((k % 6) * largura, (k // 6) * altura))
        folha.save(pasta / f"folha{n // 12}.png")
    print(g["id"], "|", g["criativo"]["gancho"], "|", pasta)


if sys.argv[1:2] == ["--gravar"]:
    print(gravacao.gravar_analise(sys.argv[2], json.loads(Path(sys.argv[3]).read_text())).resumo)
else:
    fila = [gravacao.ler(sys.argv[1])] if len(sys.argv) > 1 else gravacao.listar()
    for g in fila:
        if len(sys.argv) > 1 or g["analise"] is None:
            preparar(g)
