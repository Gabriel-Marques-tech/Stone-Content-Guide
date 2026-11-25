"""Transforma os quadros do boneco 3D em vídeo com fundo transparente para a tela e para a prévia.

Os quadros saem do Blender como módulo (Python 3.11):
    uv venv --python 3.11 v && uv pip install --python v/bin/python bpy
    v/bin/python scripts/boneco/cenas.py final [nomes]
Depois:
    uv run --no-project --with pillow --with imageio-ffmpeg \\
        python scripts/boneco/montar.py <pasta q>
"""

import subprocess
import sys
import tempfile
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe
from PIL import Image, ImageChops

RAIZ = Path(__file__).parents[2]
QUADROS = 36


def esmaecer(im: Image.Image) -> Image.Image:
    """A área renderizada acaba em 86% da altura: apaga a sombra aos poucos antes disso."""
    ini, fim = int(im.height * 0.775), int(im.height * 0.858)
    rampa = [255 if y < ini else max(0, 255 * (fim - y) // (fim - ini)) for y in range(im.height)]
    mascara = Image.new("L", (1, im.height))
    mascara.putdata(rampa)
    im.putalpha(ImageChops.multiply(im.getchannel("A"), mascara.resize(im.size)))
    return im


for pasta in sorted(Path(sys.argv[1]).iterdir()):
    pngs = sorted(pasta.glob("*.png"))
    if len(pngs) != QUADROS:
        print("incompleto", pasta.name, len(pngs))
        continue
    destino = RAIZ / "data" / "bonecos" / pasta.name
    destino.mkdir(parents=True, exist_ok=True)
    limpos = Path(tempfile.mkdtemp())
    for p in pngs:
        im = esmaecer(Image.open(p).convert("RGBA"))
        im.save(destino / f"{p.stem}.webp", quality=88)
        im.save(limpos / p.name)
    video = RAIZ / "src" / "mpe" / "static" / f"boneco-{pasta.name}.webm"
    subprocess.run(
        [get_ffmpeg_exe(), "-y", "-v", "error", "-framerate", "12", "-i", str(limpos / "%03d.png")]
        + ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-crf", "26", "-b:v", "0"]
        + ["-auto-alt-ref", "0", str(video)],
        check=True,
    )
    print(pasta.name, video.stat().st_size // 1024, "KB")
