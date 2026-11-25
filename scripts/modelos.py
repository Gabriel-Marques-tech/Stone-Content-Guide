import time

import httpx

from mpe.ambiente import chave
from mpe.gemini import URL

k = {"x-goog-api-key": chave("GEMINI_API_KEY")}
nomes = [m["name"].split("/")[1] for m in httpx.get("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200", headers=k).json()["models"] if "generateContent" in m["supportedGenerationMethods"] and "flash" in m["name"] and not any(x in m["name"] for x in ("image", "tts", "audio", "live"))]
print(nomes)
corpo = {"contents": [{"parts": [{"file_data": {"file_uri": "https://www.youtube.com/watch?v=0G6tOJvnVhk"}}, {"text": "Resuma em uma frase."}]}]}
for n in nomes:
    ini = time.time()
    try:
        r = httpx.post(URL.format(modelo=n), headers=k, json=corpo, timeout=90)
        print(n, r.status_code, f"{time.time()-ini:.0f}s", "" if r.is_success else r.text[:170].replace("\n", " "))
    except Exception as e:
        print(n, type(e).__name__)
