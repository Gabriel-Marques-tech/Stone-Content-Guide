"""Gateway do Feita (compatível com OpenAI): mesmos modelos, pagos com os créditos da conta.

Aceita várias chaves em FEITA_API_KEYS (separadas por vírgula). Quando os créditos de uma conta
acabam, passa para a próxima; quando acabam todas, levanta CotaEsgotada.
"""

import os
import threading
import time

import httpx

from mpe.ambiente import MODELO, chave
from mpe.gemini import CotaEsgotada

URL = "https://api.feita.ai/gateway/v1/chat/completions"
SEM_CREDITO = {401, 402, 403}
# O 503 "model_unavailable" volta na hora e não é cobrado, então vale insistir.
TENTATIVAS = 8


def chaves() -> list[str]:
    try:
        bruto = chave("FEITA_API_KEYS")
    except RuntimeError:
        bruto = os.environ.get("FEITA_API_KEY", "")
    return [c.strip() for c in bruto.split(",") if c.strip()]


class Feita:
    def __init__(
        self, modelo: str | None = None, por_minuto: int = 60, cliente=None, lista=None, pausa=6.0
    ):
        # `modelo` é o nome gravado na base, igual ao do Gemini direto; o gateway pede o prefixo.
        self.modelo = modelo or MODELO
        self._id = os.environ.get("MPE_FEITA_MODELO", f"google/{self.modelo}")
        self._chaves = lista if lista is not None else chaves()
        if not self._chaves:
            raise RuntimeError("falta FEITA_API_KEYS no .env")
        self._atual = 0
        self._pausa = pausa
        self._intervalo = 60 / por_minuto
        self._proxima, self._trava = 0.0, threading.Lock()
        self._http = cliente or httpx.Client(timeout=300)

    def _aguardar_vez(self):
        with self._trava:
            agora = time.monotonic()
            espera = self._proxima - agora
            self._proxima = max(agora, self._proxima) + self._intervalo
        if espera > 0:
            time.sleep(espera)

    def _trocar(self, usada: int):
        """Avança de conta só se outra thread ainda não avançou."""
        with self._trava:
            if self._atual == usada:
                self._atual += 1

    def json(self, texto: str, modelo_saida, video_url: str | None = None, temperatura=0.0):
        conteudo = [{"type": "text", "text": texto}]
        if video_url:
            # Medido em 23/11/2026: o gateway recusa `video_url`; o link só passa como arquivo.
            arquivo = {"filename": "video.mp4", "file_data": video_url}
            conteudo.insert(0, {"type": "file", "file": arquivo})
        corpo = {
            "model": self._id,
            "messages": [{"role": "user", "content": conteudo}],
            "temperature": temperatura,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": modelo_saida.__name__,
                    "schema": modelo_saida.model_json_schema(),
                },
            },
        }
        erro = "sem resposta"
        for _ in range(TENTATIVAS + len(self._chaves)):
            usada = self._atual
            if usada >= len(self._chaves):
                raise CotaEsgotada(f"créditos esgotados nas {len(self._chaves)} contas do Feita")
            self._aguardar_vez()
            r = self._http.post(
                URL, headers={"Authorization": f"Bearer {self._chaves[usada]}"}, json=corpo
            )
            if r.status_code in SEM_CREDITO:
                erro = f"Feita {r.status_code}: {r.text[:200]}"
                self._trocar(usada)
                continue
            if r.status_code == 429 or r.status_code >= 500:
                erro = f"Feita {r.status_code}: {r.text[:200]}"
                time.sleep(self._pausa)
                continue
            if r.status_code >= 400:
                raise RuntimeError(f"Feita {r.status_code}: {r.text[:300]}")
            dados = r.json()
            if "error" in dados:  # gateways deste tipo às vezes devolvem erro com HTTP 200
                erro = f"Feita: {str(dados['error'])[:200]}"
                time.sleep(self._pausa)
                continue
            return modelo_saida.model_validate_json(dados["choices"][0]["message"]["content"])
        raise RuntimeError(erro)


def llm():
    """Feita se houver chave no .env; senão, o Gemini direto."""
    if chaves():
        return Feita()
    from mpe.gemini import Gemini

    return Gemini()
