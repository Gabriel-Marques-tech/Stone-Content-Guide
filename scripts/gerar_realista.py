"""Abertura realista de exemplo: uma pessoa gerada por IA falando o gancho, sem gastar créditos.

    uv run --no-project --with gradio_client --with edge-tts python scripts/gerar_realista.py \
        "<gancho exato>" [clipe.mp4 já pronto]

Foto: data/moldes/dono-loja.png (Z-Image Turbo). Movimento e lábios: demo pública do Wan2.2-S2V no
Hugging Face, que tem fila (uns 10 min). No produto, quem faz isso é a Feita (src/mpe/video.py).
"""

import asyncio
import hashlib
import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import edge_tts
from gradio_client import Client, handle_file

RAIZ = Path(__file__).parents[1]
PASTA = RAIZ / "data" / "videos"
FOTO = RAIZ / "data" / "moldes" / "dono-loja.png"


def main():
    gancho = sys.argv[1]
    narracao = json.loads((RAIZ / "scripts" / "narracoes.json").read_text())[gancho]
    fala, voz = narracao["falas"][0], f"pt-BR-{narracao['voz']}Neural"
    if len(sys.argv) > 2:
        clipe = sys.argv[2]
    else:
        mp3 = Path(tempfile.mkdtemp()) / "fala.mp3"
        asyncio.run(edge_tts.Communicate(fala, voz, rate="+6%").save(str(mp3)))
        demo = Client("Wan-AI/Wan2.2-S2V", token=False, verbose=False)
        r = demo.predict(
            ref_img=handle_file(str(FOTO)),
            audio=handle_file(str(mp3)),
            resolution="480P",
            api_name="/predict",
        )
        clipe = r["video"] if isinstance(r, dict) else r
    id_ = "realista-" + hashlib.sha1(gancho.encode()).hexdigest()[:12]
    shutil.copy(clipe, PASTA / f"{id_}.mp4")
    registro = {
        "id": id_,
        "tipo": "realista",
        "status": "completed",
        "gancho": gancho,
        "modelo": "Z-Image Turbo + Wan2.2-S2V (demo pública) + voz edge-tts",
        "falas": [fala],
        "quando": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "arquivo": f"/videos/{id_}.mp4",
        "creditos": 0,
    }
    (PASTA / f"{id_}.json").write_text(json.dumps(registro, ensure_ascii=False, indent=1))
    print(id_, gancho)


if __name__ == "__main__":
    main()
