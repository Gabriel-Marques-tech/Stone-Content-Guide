"""Atualiza a base num comando só: métricas e vídeos novos, quadros, comentários e o que mudou.

    uv run python scripts/atualizar.py            # tudo
    uv run python scripts/atualizar.py --comparar # sem coletar: só refaz a foto e compara

Copia o banco antes (data/mpe-antes.duckdb) e desfaz sozinho se uma etapa falhar. Usa cota do
YouTube e crédito do LLM. A plataforma pode ficar no ar, mas pedidos feitos durante a atualização
esperam. A fala dos vídeos novos não entra aqui: depende do Whisper (scripts/transcrever_topo.py),
então vídeo novo conta nas comparações de quadros e só vira referência depois de transcrito.
"""

import shutil
import subprocess
import sys

from mpe import rotina
from mpe.ambiente import DADOS, chave
from mpe.banco import abrir
from mpe.canais import CANAIS
from mpe.coleta import coletar_canal
from mpe.consulta import base_completa
from mpe.youtube import YouTube

ETAPAS = [
    "extrair_quadros.py", "carregar_quadros.py", "coletar_comentarios.py",
    "classificar_comentarios.py", "carregar_comentarios.py",
]  # fmt: skip
ARQUIVO, COPIA = DADOS / "mpe.duckdb", DADOS / "mpe-antes.duckdb"


def foto() -> dict:
    with abrir() as banco:
        return rotina.fotografar(base_completa(banco))


def coletar() -> int:
    """Refaz a coleta de cada canal conhecido: métricas novas e vídeos que já têm 14 dias."""
    yt, falhas = YouTube(chave("YOUTUBE_API_KEY")), 0
    with abrir() as banco:
        conhecidos = {h for (h,) in banco.execute("SELECT handle FROM canais").fetchall()}
        for handle, perfil, segmento in CANAIS:
            if handle not in conhecidos:
                continue
            try:
                coletar_canal(banco, yt, handle, perfil, segmento)
            except Exception as erro:  # noqa: BLE001
                falhas += 1
                print(handle, "FALHOU", type(erro).__name__, flush=True)
                try:
                    banco.execute("ROLLBACK")
                except Exception:  # noqa: BLE001,S110  não havia transação aberta
                    pass
    print("coleta:", yt.unidades, "unidades,", falhas, "canais com falha", flush=True)
    return falhas


def main() -> int:
    antes = foto()
    if "--comparar" in sys.argv:
        print(*(rotina.comparar(antes, foto()) or ["nada mudou"]), sep="\n")
        return 0
    shutil.copy(ARQUIVO, COPIA)
    try:
        if coletar() > len(CANAIS) / 4:
            raise RuntimeError("canais demais falharam na coleta")
        for etapa in ETAPAS:
            print("==", etapa, flush=True)
            subprocess.run([sys.executable, f"scripts/{etapa}"], check=True)  # noqa: S603
        depois = foto()
        mudou = rotina.comparar(antes, depois)
        with abrir() as banco:
            rotina.registrar(banco, depois, mudou)
    except Exception as erro:  # noqa: BLE001
        shutil.copy(COPIA, ARQUIVO)
        print("DESFEITO:", erro)
        return 1
    print("== o que mudou")
    print(*(mudou or ["nada mudou nos padrões"]), sep="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
