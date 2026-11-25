"""YouTube Data API v3: canais, uploads e vídeos. Adaptado do coletor do Galaxies."""

import re
import time

import httpx

BASE = "https://www.googleapis.com/youtube/v3"
_DURACAO = re.compile(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")
CUSTO = {"search": 100}  # os demais recursos usados custam 1 unidade


def duracao_em_segundos(iso: str) -> int:
    dias, horas, minutos, segundos = (int(g or 0) for g in _DURACAO.fullmatch(iso).groups())
    return ((dias * 24 + horas) * 60 + minutos) * 60 + segundos


class YouTube:
    def __init__(self, chave: str, cliente: httpx.Client | None = None):
        self._chave = chave
        self._http = cliente or httpx.Client(timeout=60)
        self.unidades = 0

    def _get(self, recurso: str, tentativas: int = 4, **params) -> dict:
        """Repete com espera crescente em erros transitórios (rede, 429, 5xx)."""
        for tentativa in range(tentativas):
            ultima = tentativa == tentativas - 1
            try:
                # A chave vai no cabeçalho: na URL, apareceria nas mensagens de erro.
                resposta = self._http.get(
                    f"{BASE}/{recurso}", params=params, headers={"X-goog-api-key": self._chave}
                )
                self.unidades += CUSTO.get(recurso, 1)
            except httpx.TransportError:
                if ultima:
                    raise
            else:
                transitorio = resposta.status_code == 429 or resposta.status_code >= 500
                if not transitorio or ultima:
                    resposta.raise_for_status()
                    return resposta.json()
            time.sleep(2**tentativa)
        raise AssertionError("inalcançável")

    def buscar_canais(self, consulta: str) -> list[str]:
        dados = self._get(
            "search",
            part="id",
            type="channel",
            q=consulta,
            regionCode="BR",
            relevanceLanguage="pt",
            maxResults=50,
        )
        return [i["id"]["channelId"] for i in dados.get("items", [])]

    def canal_por_handle(self, handle: str) -> dict | None:
        dados = self._get("channels", part="snippet,statistics,contentDetails", forHandle=handle)
        itens = dados.get("items", [])
        return self._canal(itens[0]) if itens else None

    def canais(self, ids: list[str]) -> list[dict]:
        """Até 50 ids por chamada."""
        dados = self._get("channels", part="snippet,statistics,contentDetails", id=",".join(ids))
        return [self._canal(i) for i in dados.get("items", [])]

    @staticmethod
    def _canal(item: dict) -> dict:
        estatisticas = item["statistics"]
        oculto = estatisticas.get("hiddenSubscriberCount", False)
        return {
            "id": item["id"],
            "handle": item["snippet"].get("customUrl"),
            "titulo": item["snippet"]["title"],
            "descricao": item["snippet"].get("description", ""),
            "pais": item["snippet"].get("country"),
            "inscritos": None if oculto else int(estatisticas.get("subscriberCount", 0)),
            "n_videos": int(estatisticas.get("videoCount", 0)),
            "playlist_uploads": item["contentDetails"]["relatedPlaylists"]["uploads"],
        }

    def pagina_de_uploads(self, playlist: str, token: str | None) -> tuple[list[str], str | None]:
        params = {"part": "contentDetails", "playlistId": playlist, "maxResults": 50}
        if token:
            params["pageToken"] = token
        dados = self._get("playlistItems", **params)
        return [i["contentDetails"]["videoId"] for i in dados.get("items", [])], dados.get(
            "nextPageToken"
        )

    def videos(self, ids: list[str]) -> list[dict]:
        if not ids:
            return []
        # maxHeight faz a API devolver as dimensões do player: é como sabemos se é vertical.
        dados = self._get(
            "videos",
            part="snippet,contentDetails,statistics,player",
            id=",".join(ids),
            maxHeight=1080,
        )
        return [self._video(i) for i in dados.get("items", []) if "duration" in i["contentDetails"]]

    @staticmethod
    def _video(item: dict) -> dict:
        estatisticas, player = item.get("statistics", {}), item.get("player", {})

        def numero(campo):
            valor = estatisticas.get(campo)
            return int(valor) if valor is not None else None

        snippet = item["snippet"]
        return {
            "id": item["id"],
            "canal_id": snippet["channelId"],
            "titulo": snippet["title"],
            "descricao": snippet.get("description", ""),
            "tags": snippet.get("tags", []),
            "idioma": snippet.get("defaultAudioLanguage"),
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
            "publicado_em": snippet["publishedAt"],
            "duracao_s": duracao_em_segundos(item["contentDetails"]["duration"]),
            "vertical": int(player.get("embedHeight", 0)) > int(player.get("embedWidth", 1)),
            "views": numero("viewCount"),
            "likes": numero("likeCount"),
            "comentarios": numero("commentCount"),
        }
