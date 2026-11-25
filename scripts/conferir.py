from mpe.banco import abrir

b = abrir()
b.execute("SET TimeZone='UTC'")
print(b.execute("""
SELECT c.handle, left(c.titulo,28) t, c.inscritos i, left(replace(c.descricao,chr(10),' '),60) d, count(p.id) n,
 min(p.publicado_em)::date de, max(p.publicado_em)::date ate, median(p.views)::int mv, sum((p.likes IS NULL)::int) ln
FROM canais c LEFT JOIN posts p ON p.canal_id=c.id GROUP BY ALL ORDER BY n DESC, i DESC""").df().to_string(index=False))
print(b.execute("""SELECT count(*), sum((likes IS NULL)::int), sum((comentarios IS NULL)::int), sum((views=0)::int),
 sum((coalesce(likes,0)+coalesce(comentarios,0)=0)::int) FROM posts""").fetchall())
print(b.execute("SELECT idioma, count(*) FROM posts GROUP BY 1 ORDER BY 2 DESC LIMIT 8").fetchall())
for h in ("@stone", "@infinitepay", "@nuvemshop", "@pagbank"):
    print(h, b.execute("SELECT left(p.titulo,60) FROM posts p JOIN canais c ON c.id=p.canal_id WHERE handle=? LIMIT 4", [h]).fetchall())
