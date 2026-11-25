from mpe.ambiente import chave
from mpe.banco import abrir
from mpe.canais import CANAIS
from mpe.coleta import coletar_canal
from mpe.youtube import YouTube

banco, yt = abrir(), YouTube(chave("YOUTUBE_API_KEY"))
feitos = {h for (h,) in banco.execute("SELECT handle FROM canais").fetchall()}
for handle, perfil, segmento in CANAIS:
    if handle in feitos:
        continue
    try:
        n = coletar_canal(banco, yt, handle, perfil, segmento)
    except Exception as erro:
        print(handle, "FALHOU", type(erro).__name__, erro)
        continue
    print(handle, "não existe" if n is None else n, flush=True)
print("total", banco.execute("SELECT COUNT(*) FROM posts").fetchone()[0], "|", yt.unidades, "un.")
