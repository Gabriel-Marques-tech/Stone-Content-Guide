"""Transcreve com Whisper local (faster-whisper small) o áudio dos Shorts listados.

Uso: python transcrever_topo.py ids.json pasta_de_saida
Grava pasta/<id>.json com [{t, texto}]; é o cache que scripts/extrair_transcricao.py lê.
Roda num ambiente com faster-whisper e yt-dlp (o do Galaxies: uv run --extra multimodal).
"""

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

ids, pasta = json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2])
pasta.mkdir(parents=True, exist_ok=True)
modelo = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=8)
ok = ruim = 0
for id_ in ids:
    destino = pasta / f"{id_}.json"
    if destino.exists():
        continue
    try:
        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / "a"
            subprocess.run(
                ["yt-dlp", "-q", "--no-warnings", "-f", "ba/b", "-o", str(audio),
                 f"https://www.youtube.com/shorts/{id_}"],
                check=True, timeout=180,
            )  # fmt: skip
            pcm = subprocess.run(
                ["ffmpeg", "-loglevel", "error", "-i", str(audio), "-f", "s16le", "-ac", "1",
                 "-ar", "16000", "-"],
                capture_output=True, check=True,
            ).stdout  # fmt: skip
        onda = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
        trechos, _ = modelo.transcribe(onda, language="pt", vad_filter=True)
        falas = [{"t": round(s.start, 1), "texto": s.text.strip()} for s in trechos]
        destino.write_text(json.dumps(falas, ensure_ascii=False))
        ok += 1
    except Exception as e:  # noqa: BLE001
        ruim += 1
        print("falha", id_, str(e)[:150], flush=True)
        time.sleep(5)
    if (ok + ruim) % 25 == 0:
        print(ok, "ok", ruim, "falhas", flush=True)
print("fim", ok, "ok", ruim, "falhas")
