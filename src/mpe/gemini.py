"""Gemini (AI Studio) com saída em JSON schema. Aceita um link público do YouTube como vídeo."""

import threading
import time

import httpx

from mpe.ambiente import MODELO, chave

URL = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"


class CotaEsgotada(RuntimeError):
    pass


def _cotas(resposta) -> str:
    """Quais limites estouraram: o 429 por minuto passa sozinho, o por dia não."""
    try:
        detalhes = resposta.json()["error"].get("details", [])
    except (ValueError, KeyError):
        return ""
    violacoes = [v for d in detalhes for v in d.get("violations", [])]
    return "; ".join(f"{v.get('quotaId')}={v.get('quotaValue')}" for v in violacoes)


def _limpar(schema: dict) -> dict:
    """O Gemini recusa algumas chaves do JSON schema do Pydantic."""
    fora = {"title", "default", "additionalProperties"}
    if isinstance(schema, dict):
        return {
            k: ({n: _limpar(p) for n, p in v.items()} if k == "properties" else _limpar(v))
            for k, v in schema.items()
            if k not in fora
        }
    return schema


class Gemini:
    def __init__(self, modelo: str | None = None, por_minuto: int = 12, cliente=None):
        self.modelo = modelo or MODELO
        self._chave = chave("GEMINI_API_KEY")
        self._intervalo = 60 / por_minuto
        self._proxima, self._trava = 0.0, threading.Lock()
        self._http = cliente or httpx.Client(timeout=180)

    def _aguardar_vez(self):
        with self._trava:
            agora = time.monotonic()
            espera = self._proxima - agora
            self._proxima = max(agora, self._proxima) + self._intervalo
        if espera > 0:
            time.sleep(espera)

    def json(self, texto: str, modelo_saida, video_url: str | None = None, temperatura=0.0):
        partes = [{"text": texto}]
        if video_url:
            partes.insert(0, {"file_data": {"file_uri": video_url}})
        corpo = {
            "contents": [{"parts": partes}],
            "generationConfig": {
                "temperature": temperatura,
                "responseMimeType": "application/json",
                "responseSchema": _limpar(modelo_saida.model_json_schema()),
            },
        }
        for _ in range(2):  # cada tentativa gasta cota, mesmo com 503
            self._aguardar_vez()
            r = self._http.post(
                URL.format(modelo=self.modelo),
                headers={"x-goog-api-key": self._chave},
                json=corpo,
            )
            if r.status_code == 429 or r.status_code >= 500:
                if "PerDay" in (cotas := _cotas(r)):
                    raise CotaEsgotada(cotas)
                time.sleep(20)
                continue
            if r.status_code >= 400:
                raise RuntimeError(f"Gemini {r.status_code}: {r.text[:300]}")
            candidatos = r.json().get("candidates") or []
            saida = "".join(
                p.get("text", "") for c in candidatos for p in c.get("content", {}).get("parts", [])
            )
            return modelo_saida.model_validate_json(saida)
        raise CotaEsgotada(f"Gemini {r.status_code}: {_cotas(r) or r.text[:120]}")
