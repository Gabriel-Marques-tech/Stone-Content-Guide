"""Versão pública da plataforma: as mesmas telas, com roteiros e prévias já prontos.

    uv run python scripts/exportar_vitrine.py <url da plataforma> <pasta de saída>

Não leva chave, banco nem gravações, e nada nela cria, grava ou gasta crédito.
"""

import json
import shutil
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).parents[1]
ORIGEM, SAIDA = sys.argv[1].rstrip("/"), Path(sys.argv[2])
FORA = {"etapas"}  # registro interno da execução

PONTE = """<script>
// versão pública: lê os dados prontos e recusa qualquer ação que criaria ou gastaria algo
window.PUBLICA = true;
(() => {
  const original = window.fetch;
  const recusa = "Versão pública: criar e incluir ficam desligados aqui. Veja os prontos abaixo.";
  window.fetch = (url, o) => {
    const m = String(url).match(/^\\/api\\/([a-z]+)/);
    if (!m) return original(url, o);
    if (o && o.method === "POST")
      return Promise.resolve(Response.json({erro: recusa}, {status: 503}));
    return original("/dados/" + m[1] + ".json");
  };
})();
</script>
"""
AVISO = (
    '<p style="color:#B7C4BD;margin:14px 0 0;max-width:46ch">Versão pública: abra um dos roteiros '
    "prontos abaixo. Criar roteiro novo roda na versão da equipe.</p>"
)


def ler(caminho: str) -> bytes:
    with urllib.request.urlopen(ORIGEM + caminho, timeout=120) as r:  # noqa: S310
        return r.read()


def mostrados(execucoes: list[dict]) -> list[dict]:
    """O mesmo filtro da tela inicial: o mais recente de cada pedido, em cenas e conferido."""
    vistos, saida = set(), []
    for x in execucoes:
        s, e = x["saida"], x["entrada"]
        chave = (e["query"].strip().lower(), e.get("objetivo"))
        criativos = s["creatives"]
        if e["mode"] != "gerar_criativo" or not criativos or not s.get("patterns"):
            continue
        if len(criativos[0].get("cenas") or []) <= 2 or chave in vistos:
            continue
        vistos.add(chave)
        saida.append({k: v for k, v in x.items() if k not in FORA})
    return saida


def parados(dados: dict) -> dict:
    """Nesta versão ninguém lê de novo: some a hora da próxima leitura."""
    return {"videos": [{**v, "proxima": None} for v in dados["videos"]]}


def main():
    shutil.rmtree(SAIDA / "dados", ignore_errors=True)
    shutil.rmtree(SAIDA / "videos", ignore_errors=True)
    for pasta in ("dados", "videos", "static"):
        (SAIDA / pasta).mkdir(parents=True, exist_ok=True)
    videos = json.loads(ler("/api/videos"))
    prontos = {v["gancho"] for v in videos["videos"] if v["status"] == "completed"}
    feitos = [
        x for x in mostrados(json.loads(ler("/api/execucoes")))
        if any(c["gancho"] in prontos for c in x["saida"]["creatives"])
    ]  # fmt: skip
    ganchos = {c["gancho"] for x in feitos for c in x["saida"]["creatives"]}
    videos["videos"] = [
        v for v in videos["videos"] if v["gancho"] in ganchos and v["status"] == "completed"
    ]
    for v in videos["videos"]:
        (SAIDA / v["arquivo"].lstrip("/")).write_bytes(ler(v["arquivo"]))
    dados = {
        "execucoes": feitos, "videos": videos, "gravacoes": {"gravacoes": []},
        "acompanhados": parados(json.loads(ler("/api/acompanhados"))),
        "vitrine": json.loads(ler("/api/vitrine")), "playbook": json.loads(ler("/api/playbook")),
    }  # fmt: skip
    for nome, conteudo in dados.items():
        (SAIDA / "dados" / f"{nome}.json").write_text(json.dumps(conteudo, ensure_ascii=False))
    (SAIDA / "playbook-stone.md").write_bytes(ler("/playbook.md"))
    for arquivo in (RAIZ / "src/mpe/static").glob("*"):
        if arquivo.suffix in {".webm", ".js"}:
            shutil.copy(arquivo, SAIDA / "static" / arquivo.name)
    for nome, destino in (("criar", "index"), ("playbook", "playbook"), ("acompanhar",) * 2):
        html = (RAIZ / f"src/mpe/{nome}.html").read_text()
        html = html.replace("<body>", "<body>\n" + PONTE, 1).replace(
            'href="/playbook.md"', 'href="/playbook-stone.md" download'
        )
        if nome == "criar":
            html = html.replace("</form>", "</form>" + AVISO, 1)
        esconder = "<style>.anl,#gera{display:none!important}</style></head>"
        html = html.replace("</head>", esconder, 1)
        (SAIDA / f"{destino}.html").write_text(html)
    (SAIDA / "vercel.json").write_text('{ "cleanUrls": true }\n')
    print(len(feitos), "roteiros;", len(videos["videos"]), "prévias")


if __name__ == "__main__":
    main()
