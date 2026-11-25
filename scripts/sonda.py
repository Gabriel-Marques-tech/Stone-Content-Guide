"""Mede uma chamada crua com a rubrica completa, sem repetição, em vários modelos."""

import sys
import time

import httpx

from mpe.ambiente import chave
from mpe.gemini import URL, _limpar
from mpe.rubrica import INSTRUCAO, Rubrica

k = {"x-goog-api-key": chave("GEMINI_API_KEY")}
for modelo in sys.argv[1:]:
    corpo = {
        "contents": [{"parts": [{"file_data": {"file_uri": "https://www.youtube.com/watch?v=0G6tOJvnVhk"}}, {"text": INSTRUCAO.format(titulo="x", descricao="")}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json", "responseSchema": _limpar(Rubrica.model_json_schema())},
    }
    ini = time.time()
    try:
        r = httpx.post(URL.format(modelo=modelo), headers=k, json=corpo, timeout=150)
        print(modelo, r.status_code, f"{time.time()-ini:.0f}s", r.json().get("usageMetadata", {}).get("totalTokenCount") if r.is_success else r.text[:900], flush=True)
    except Exception as e:
        print(modelo, type(e).__name__, f"{time.time()-ini:.0f}s", flush=True)
