"""Descoberta de canais candidatos (100 unidades por consulta). Salva data/candidatos.json."""

import json

from mpe.ambiente import DADOS, chave
from mpe.youtube import YouTube

CONSULTAS = [
    "empreendedorismo pequenos negócios",
    "dicas para MEI microempreendedor",
    "finanças para pequenas empresas",
    "marketing para pequenos negócios",
    "como vender mais loja pequena",
    "gestão de pequenas empresas",
    "precificação produtos artesanato confeitaria",
    "gestão salão de beleza barbearia",
    "gestão de restaurante delivery lucro",
    "contador para MEI e simples nacional",
    "maquininha de cartão pequenos negócios",
    "Sebrae",
]

yt = YouTube(chave("YOUTUBE_API_KEY"))
origem: dict[str, list[str]] = {}
for consulta in CONSULTAS:
    for canal in yt.buscar_canais(consulta):
        origem.setdefault(canal, []).append(consulta)

ids, canais = list(origem), []
for i in range(0, len(ids), 50):
    canais += yt.canais(ids[i : i + 50])
for canal in canais:
    canal["consultas"] = origem[canal["id"]]
DADOS.mkdir(exist_ok=True)
(DADOS / "candidatos.json").write_text(json.dumps(canais, ensure_ascii=False, indent=1))
print(len(canais), "canais;", yt.unidades, "unidades")
