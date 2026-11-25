"""Rajada curta por modelo: quantas chamadas passam, em quanto tempo, e que cota estoura."""

import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import httpx

from mpe.ambiente import chave
from mpe.gemini import URL, _cotas, _limpar
from mpe.rubrica import INSTRUCAO, Rubrica

k = {"x-goog-api-key": chave("GEMINI_API_KEY")}
VIDS = ["0G6tOJvnVhk"]


def uma(args):
    modelo, v = args
    corpo = {
        "contents": [{"parts": [{"file_data": {"file_uri": f"https://www.youtube.com/watch?v={v}"}}, {"text": INSTRUCAO.format(titulo="", descricao="")}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json", "responseSchema": _limpar(Rubrica.model_json_schema())},
    }
    ini = time.time()
    try:
        r = httpx.post(URL.format(modelo=modelo), headers=k, json=corpo, timeout=100)
        extra = _cotas(r) if r.status_code == 429 else ("" if r.is_success else r.text[:120].replace("\n", " ")) if r.status_code != 503 else ""
        if r.is_success:
            try:
                Rubrica.model_validate_json(r.json()["candidates"][0]["content"]["parts"][0]["text"])
            except Exception as e:
                extra = "JSON inválido " + type(e).__name__
        return r.status_code, round(time.time() - ini), extra
    except Exception as e:
        return type(e).__name__, round(time.time() - ini), ""


for modelo in sys.argv[1:]:
    with ThreadPoolExecutor(8) as p:
        rs = list(p.map(uma, [(modelo, v) for v in VIDS]))
    print(modelo, dict(Counter(r[0] for r in rs)), "seg:", [r[1] for r in rs], {r[2] for r in rs if r[2]}, flush=True)
