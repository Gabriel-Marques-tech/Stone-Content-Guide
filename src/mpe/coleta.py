"""Coleta de Shorts: canal → uploads → vídeos. Cada canal é gravado inteiro ou não é gravado."""

import json
from datetime import UTC, datetime, timedelta

DURACAO_MAXIMA_S = 180  # desde out/2024 o YouTube aceita Shorts de até 3 minutos
IDADE_MINIMA = timedelta(days=14)
JANELA = timedelta(days=730)
MAXIMO_POR_CANAL = 120  # os mais recentes: impede que canais muito ativos dominem a base


def coletar_canal(banco, yt, handle: str, perfil: str, segmento: str) -> int | None:
    """Número de Shorts gravados; None se o canal não existir."""
    canal = yt.canal_por_handle(handle)
    if canal is None:
        return None
    agora = datetime.now(UTC)
    shorts, token = [], None
    while len(shorts) < MAXIMO_POR_CANAL:
        ids, token = yt.pagina_de_uploads(canal["playlist_uploads"], token)
        datas = []
        for v in yt.videos(ids):
            data = datetime.fromisoformat(v["publicado_em"])
            datas.append(data)
            if not agora - JANELA <= data <= agora - IDADE_MINIMA:
                continue
            if v["vertical"] and 0 < v["duracao_s"] <= DURACAO_MAXIMA_S:
                shorts.append(v)
        if token is None or (datas and max(datas) < agora - JANELA):
            break
    shorts = sorted(shorts, key=lambda v: v["publicado_em"], reverse=True)[:MAXIMO_POR_CANAL]
    utc = agora.replace(tzinfo=None)
    banco.execute("BEGIN")
    banco.execute(
        "INSERT OR REPLACE INTO canais VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [canal["id"], handle, canal["titulo"], canal["descricao"], canal["inscritos"]]
        + [perfil, segmento, utc],
    )
    for v in shorts:
        data = datetime.fromisoformat(v["publicado_em"]).astimezone(UTC).replace(tzinfo=None)
        banco.execute(
            "INSERT OR REPLACE INTO posts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [v["id"], v["canal_id"], v["titulo"], v["descricao"], json.dumps(v["tags"])]
            + [v["idioma"], v["thumbnail"], data, v["duracao_s"], v["views"], v["likes"]]
            + [v["comentarios"], utc],
        )
    banco.execute("COMMIT")
    return len(shorts)
