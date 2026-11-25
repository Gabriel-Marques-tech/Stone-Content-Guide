import time

from mpe.banco import abrir
from mpe.feita import llm
from mpe.rubrica import INSTRUCAO, Rubrica

b, g = abrir(), llm()
for id_, t, d in b.execute("SELECT p.id, p.titulo, p.descricao FROM posts p JOIN canais c ON c.id=p.canal_id WHERE c.handle IN ('@otiagojotta','@stone') ORDER BY p.views DESC LIMIT 2").fetchall():
    ini = time.time()
    r = g.json(INSTRUCAO.format(titulo=t, descricao=d[:500]), Rubrica, f"https://www.youtube.com/watch?v={id_}")
    print(id_, t, f"{time.time()-ini:.1f}s\n", r.model_dump_json(indent=1)[:2200])
