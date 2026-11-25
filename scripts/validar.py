"""`validar.py gerar` cria data/validacao.html (cega). `validar.py medir <csv>` mede o acordo."""

import html
import json
import sys
from typing import get_args

import pandas as pd

from mpe.ambiente import DADOS
from mpe.banco import abrir
from mpe.consulta import base_completa
from mpe.rubrica import Rubrica
from mpe.validacao import CAMPOS, concordancia, sortear

PAGINA = """<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Validação manual</title>
<style>body{font:15px system-ui;margin:0;background:#f5f5f4;color:#1c1917}header{position:sticky;top:0;
background:#fff;padding:10px 20px;border-bottom:1px solid #ddd;display:flex;gap:16px;align-items:center}
section{display:grid;grid-template-columns:320px 1fr;gap:24px;max-width:1000px;margin:20px auto;
background:#fff;padding:20px;border-radius:10px}iframe{width:320px;height:560px;border:0}
fieldset{border:0;padding:0;margin:0 0 10px}legend{font-weight:600}label{margin-right:12px;
white-space:nowrap;display:inline-block}small{color:#57534e}</style>
<header><b>Validação manual</b><span id="n"></span><button id="b">Baixar CSV</button></header>
<main id="m"></main><script>
const P=__POSTS__,C=__CAMPOS__,K='validacao-mpe';let S={};try{S=JSON.parse(localStorage[K]||'{}')}catch(e){}
const m=document.getElementById('m');
P.forEach((p,i)=>{const s=document.createElement('section');s.innerHTML=`<div><iframe loading="lazy"
src="https://www.youtube.com/embed/${p.id}"></iframe><br><a target="_blank"
href="https://www.youtube.com/shorts/${p.id}">abrir no YouTube</a></div><div><h3>${i+1}. ${p.titulo}</h3>`+
C.map(c=>`<fieldset><legend>${c.nome}</legend><small>${c.ajuda}</small><br>`+c.op.map(o=>`<label>
<input type="radio" name="${p.id}|${c.nome}" value="${o}" ${(S[p.id]||{})[c.nome]===o?'checked':''}> ${o}
</label>`).join('')+'</fieldset>').join('')+'</div>';m.append(s)});
function conta(){const f=P.filter(p=>C.every(c=>(S[p.id]||{})[c.nome])).length;
document.getElementById('n').textContent=`${f} de ${P.length} completos`}
m.onchange=e=>{const k=e.target.name.lastIndexOf('|'),id=e.target.name.slice(0,k),c=e.target.name.slice(k+1);
(S[id]??={})[c]=e.target.value;try{localStorage[K]=JSON.stringify(S)}catch(e){}conta()};
document.getElementById('b').onclick=()=>{const L=[['id',...C.map(c=>c.nome)].join(',')].concat(
P.map(p=>[p.id,...C.map(c=>(S[p.id]||{})[c.nome]||'')].join(',')));const a=document.createElement('a');
a.href=URL.createObjectURL(new Blob([L.join('\\n')],{type:'text/csv'}));a.download='validacao.csv';a.click()};
conta()</script></html>"""

df = base_completa(abrir())
if sys.argv[1] == "gerar":
    campos = []
    for c in CAMPOS:
        info = Rubrica.model_fields[c]
        opcoes = list(get_args(info.annotation)) or ["true", "false"]
        campos.append({"nome": c, "ajuda": info.description or "", "op": opcoes})
    # a mesma amostra que a IA anotou, para os dois serem comparáveis
    ia = DADOS / "validacao_ia.csv"
    if ia.exists():
        amostra = df.set_index("id", drop=False).loc[pd.read_csv(ia)["id"]]
    else:
        amostra = sortear(df)
    posts = [{"id": r.id, "titulo": html.escape(r.titulo)} for r in amostra.itertuples()]
    dados = json.dumps(posts, ensure_ascii=False).replace("</", "<\\/")
    pagina = PAGINA.replace("__POSTS__", dados).replace("__CAMPOS__", json.dumps(campos))
    (DADOS / "validacao.html").write_text(pagina)
    print(len(posts), "posts em", DADOS / "validacao.html")
else:
    humano = pd.read_csv(sys.argv[2], dtype=str, keep_default_na=False)
    r = concordancia(df[df["categorizado"]], humano)
    r.to_csv(DADOS / "concordancia.csv", index=False)
    print(r.round(2).to_string(index=False))
