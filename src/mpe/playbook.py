"""Playbook em Markdown: os números saem da base; o LLM só redige os criativos."""

import re

from mpe import hipoteses, motor
from mpe.consulta import (
    achados,
    canais_fora_do_publico,
    canal_x_topo,
    cenarios,
    desfechos_por_tipo,
    interesse_x_resto,
    lead_x_resto,
    pedido_por_engajamento,
    perfis_em_destaque,
    recorte,
    referencias,
    top_categorizado,
    top_x_resto,
)
from mpe.duvidas import GRUPO_DO_OBJETIVO, padroes_firmes, robustez
from mpe.duvidas import NOMES as NOME_ATRIBUTO
from mpe.duvidas import nome as rotulo_de

TEMAS = [
    "separar o dinheiro da empresa do pessoal",
    "como formar preço de venda com lucro",
    "vender mais no delivery sem perder margem",
    "taxa da maquininha",
    "atrair clientes para loja de bairro",
    "vender no Pix e conferir o dinheiro no fim do dia",
]
# O mesmo pedido da plataforma: os criativos do playbook são os que estão na tela.
PEDIDO = "Vídeo para donos de pequenos negócios sobre: {tema}"
OBJETIVO = {"taxa da maquininha": "engajamento"}  # os demais são para contato
CANAL_STONE = "@stone"
VEREDITO = {
    "sustentada": "sustentada",
    "nao_sustentada": "não sustentada",
    "evidencia_insuficiente": "evidência insuficiente",
    "nao_testada": "não testada",
}


def _pct(x: float) -> str:
    return f"{x:.0%}"


def _pct1(x: float) -> str:
    return f"{x:.1%}".replace(".", ",")


def _milhar(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def concentracao(df) -> str:
    topo = df[df["top_tapi"]]
    maiores = topo["handle"].value_counts().head(3)
    return (
        f"Os 3 perfis mais presentes ocupam {maiores.sum()} das {len(topo)} vagas "
        f"({_pct(maiores.sum() / len(topo))}). Mediana de inscritos: "
        f"{_milhar(topo['inscritos'].median())} no topo, "
        f"{_milhar(df['inscritos'].median())} na base."
    )


ROTULO = {"top_tapi": "engajamento", "lead": "contato"}
VALORES = {"outro": "Outro", "geral": "Geral", "alimentacao": "Alimentação", "varejo": "Varejo"}
VALORES |= {"beleza": "Beleza", "servicos": "Serviços"}


def _valor(coluna: str, valor: str | None) -> str:
    """Nome de um valor da rubrica ('financas' → 'finanças')."""
    if valor is None:
        return "sem post no topo"
    if rotulo := NOME_ATRIBUTO.get(f"{coluna}={valor}"):
        return rotulo.removeprefix("Tema: ")
    return VALORES.get(valor, valor)


def _celula(texto: str) -> str:
    return texto.replace("|", "/").strip()


def _robustez(df) -> list[str]:
    """Checagem: o que continua de pé sem o conteúdo que não é voltado ao lojista."""
    c = cenarios(df)
    if len(c) < 3:
        return []
    topo, fora = df[df["top_tapi"]], canais_fora_do_publico(df)
    L = ["", "## Checagem: o topo fala com o lojista?", ""]
    L += [
        f"Em parte. {_pct(topo['tema_principal'].eq('outro').mean())} dos posts do topo não tratam "
        "de nenhum tema de negócio: boa parte é vídeo do lojista para o cliente (corte de cabelo, "
        f"pizza, lembrancinha). {len(fora)} canais assim ({', '.join(fora)}) somam "
        f"{int(topo['handle'].isin(fora).sum())} das {len(topo)} vagas. Por isso cada comparação "
        "foi refeita duas vezes, com o topo recalculado: sem os posts de tema fora de negócio "
        f"({_milhar(len(c['sem_posts']))} posts) e sem esses canais "
        f"({_milhar(len(c['sem_canais']))}). **Firme** é o que passa nos três: 8 pontos de "
        "diferença e ao menos 5 com peso igual por canal, na mesma direção. Os valores são do "
        "grupo com peso igual por canal contra os demais.",
    ]
    for grupo, rotulo in ROTULO.items():
        if grupo not in df:
            continue
        L += ["", f"### Para {rotulo}", ""]
        L += ["| Característica | Base | Sem os posts | Sem os canais | Resultado |"]
        L.append("|---|---|---|---|---|")
        linhas = robustez(df, grupo)
        for r in sorted(linhas, key=lambda r: not r["firme"]):
            if r["cenarios"].get("base", {}).get("sinal") not in ("mais", "menos"):
                continue
            if r["atributo"] == "tema_principal=outro":
                continue
            celulas = [
                f"{_pct(x['por_perfil'])} contra {_pct(x['resto'])}" if x else "sem dado"
                for x in (r["cenarios"].get(n) for n in ("base", "sem_posts", "sem_canais"))
            ]
            veredito = "**firme**" if r["firme"] else "hipótese"
            L.append(f"| {rotulo_de(r['atributo'])} | {' | '.join(celulas)} | {veredito} |")
    L += [
        "",
        "Características de fala usam um só avaliador por comparação. No contato, os demais, "
        "nelas, são posts do topo de engajamento sem pedido.",
    ]
    return L


def _recortes(df) -> list[str]:
    L = ["", "## Recortes", ""]
    L += [
        "Quanto de cada grupo entra no topo e quanto recebe pedido de contato. *Maior canal* é a "
        "fatia do topo daquele grupo que vem de um canal só: acima da metade, o número é dele.",
    ]
    for coluna, titulo, outra in (
        ("tema_principal", "Por tema", "Formato mais comum no topo"),
        ("formato_video", "Por formato", "Tema mais comum no topo"),
        ("segmento", "Por segmento do empreendedor", "Formato mais comum no topo"),
    ):
        if coluna not in df:
            continue
        t = recorte(df, coluna)
        L += ["", f"### {titulo}", ""]
        L.append(f"| | Posts | Canais | Entra no topo | Maior canal | Recebe pedido | {outra} |")
        L.append("|---|---|---|---|---|---|---|")
        col = "formato_video" if coluna != "formato_video" else "tema_principal"
        for r in t.itertuples():
            L.append(
                f"| {_valor(coluna, r.valor)} | {_milhar(r.posts)} | {r.perfis} "
                f"| {_pct1(r.taxa_topo)} ({r.no_topo}) | {_pct(r.maior_canal)} "
                f"| {_pct1(r.taxa_pedido)} ({r.pedidos}) | {_valor(col, r.domina)} |"
            )
    return L


def _comparacoes(df) -> list[str]:
    L = ["", "## Topo contra o resto da base", ""]
    L += [
        "Descritivo: quanto cada característica aparece nos 10% superiores e no resto. A coluna "
        "do meio dá o mesmo peso a cada perfil do topo; quando ela se afasta da primeira, o "
        "número vem de poucos canais. Características de fala (chamada, passo concreto, fala "
        "direta com o dono) contam só os posts que o mesmo avaliador assistiu com som, dos dois "
        "lados. Tipo de gancho e tom ficam de fora: os avaliadores concordam pouco neles.",
        "",
        *_tabela_contraste(top_x_resto(df), "Topo"),
    ]
    stone = canal_x_topo(df, CANAL_STONE)
    if len(stone):
        n = int((df["handle"] == CANAL_STONE).sum())
        L += ["", "## O canal da Stone contra o topo", ""]
        L += [
            f"Os {n} Shorts do canal da Stone na base, comparados aos posts de alto desempenho "
            "dos outros perfis (peso igual por perfil). Só características lidas na base inteira.",
            "",
            "| Característica | Stone | Topo | Diferença |",
            "|---|---|---|---|",
        ]
        for r in stone.itertuples():
            L.append(
                f"| {rotulo_de(r.atributo)} | {_pct(r.canal)} | {_pct(r.topo)} "
                f"| {r.dif * 100:+.0f} pontos |"
            )
    return L


TIPOS = {
    "informativo": "Informativo (tutorial, dicas, finanças, gestão, vendas, regra)",
    "personalidade": "Personalidade (humor, depoimento, bastidores, história, motivação)",
    "os_dois": "Os dois juntos",
    "nenhum": "Nenhum dos dois",
}


def _tabela_contraste(tabela, nome: str) -> list[str]:
    L = [f"| Característica | {nome} | {nome}, peso igual por perfil | Demais | Posts |"]
    L.append("|---|---|---|---|---|")
    for r in tabela.itertuples():
        L.append(
            f"| {rotulo_de(r.atributo)} | {_pct(r.grupo)} | {_pct(r.por_perfil)} | {_pct(r.resto)} "
            f"| {int(r.n)} |"
        )
    return L


def _com_ic(media: float, ic: tuple[float, float]) -> str:
    return f"{_pct(media)} ({_pct(ic[0])} a {_pct(ic[1])})"


def _lead(df) -> list[str]:
    """Indicador de lead do TAPI: comentários com intenção de contato."""
    if "lead" not in df or not df["lead"].any():
        return []
    lidos, leads = int(df["lidos"].sum()), df[df["lead"]]
    interessados = df[df["interessado"]]
    t = pedido_por_engajamento(df)
    L = ["", "## Indicador de lead: quem recebe pedido de contato", ""]
    L += [
        f"Foram lidos {_milhar(lidos)} comentários (até 100 por vídeo, pela API oficial) e cada "
        "um recebeu uma classe. *Intenção*: quer comprar, contratar ou falar com o autor (pede "
        "preço, link, contato, material). *Dúvida*: pergunta sobre o assunto ou pede orientação "
        "para o próprio caso. As duas juntas são o *interesse*.",
        "",
        f"- Comentários de intenção: {int(df['intencao'].sum())}, em {len(leads)} posts de "
        f"{leads['handle'].nunique()} perfis.",
        f"- Comentários de dúvida: {int(df['duvida'].sum())}. Posts com interesse: "
        f"{len(interessados)}.",
        f"- **Engajamento e pedido de contato andam juntos:** {_pct1(t['topo'])} dos posts do topo "
        f"têm pedido ({t['n_topo']}), contra {_pct1(t['fora'])} dos demais ({t['n_fora']}). Parte "
        "disso é mecânica, porque a métrica conta comentários: só entre posts com comentário "
        f"lido, são {_pct1(t['topo_comentado'])} contra {_pct1(t['fora_comentado'])}.",
        "- Engajamento sozinho não basta: mesmo no topo, mais de 9 em cada 10 posts não têm "
        "pedido. As tabelas abaixo mostram em que os posts com pedido diferem dos outros.",
        "",
        "### O que aparece mais nos posts com comentário de intenção",
        "",
        "Nas características de fala (oferta, chamada, fala direta com o dono, passo concreto), "
        "os dois lados foram lidos pelo mesmo avaliador, e o lado *Demais* são posts do topo de "
        "engajamento sem comentário de intenção.",
        "",
        *_tabela_contraste(lead_x_resto(df), "Com intenção"),
        "",
        "### O que aparece mais nos posts com interesse (intenção ou dúvida)",
        "",
        *_tabela_contraste(interesse_x_resto(df), "Com interesse"),
        "",
        "### Posts que mais geraram intenção",
        "",
    ]
    for r in leads.sort_values("intencao", ascending=False).head(8).itertuples():
        onde = "no topo de engajamento" if r.top_tapi else "fora do topo de engajamento"
        L.append(
            f"- [{r.titulo}](https://www.youtube.com/shorts/{r.id}), {r.canal}: "
            f"{r.intencao} comentários de intenção, {onde}"
        )
    stone = df[df["handle"] == CANAL_STONE]
    if len(stone):
        L += [
            "",
            f"**Canal da Stone:** {len(stone)} Shorts na base, {int(stone['lidos'].sum())} "
            f"comentários lidos, {int(stone['intencao'].sum())} de intenção e "
            f"{int(stone['duvida'].sum())} de dúvida.",
        ]
    tipos = desfechos_por_tipo(df)
    L += ["", "### Informativo, personalidade ou os dois", ""]
    L += [
        "Recorte inspirado em Lee, Hosanagar e Nair (2018), com os campos lidos na base inteira. "
        "Percentuais com peso igual por perfil e intervalo de 95% por reamostragem de perfis. Os "
        "intervalos de entrada no topo se sobrepõem: nessa coluna a base não separa os tipos.",
        "",
        "| Tipo de conteúdo | Posts | Entra no topo de engajamento | Gera interesse "
        "| Gera intenção |",
        "|---|---|---|---|---|",
    ]
    for r in tipos.itertuples():
        L.append(
            f"| {TIPOS[r.tipo]} | {r.posts} | {_com_ic(r.no_topo_perfil, r.ic_topo)} "
            f"| {_com_ic(r.interesse_perfil, r.ic_interesse)} | {_pct1(r.lead_perfil)} |"
        )
    return L


def tela(df) -> dict:
    """O mesmo conteúdo do documento, para a página /playbook da plataforma."""
    topo, fora = df[df["top_tapi"]], canais_fora_do_publico(df)
    t = pedido_por_engajamento(df)
    objetivos = {}
    for objetivo, grupo in GRUPO_DO_OBJETIVO.items():
        caiu = []
        for r in robustez(df, grupo):
            c = r["cenarios"]
            sinal = c.get("base", {}).get("sinal")
            if r["firme"] or sinal not in ("mais", "menos") or "=outro" in r["atributo"]:
                continue
            pior = min(
                (x for n, x in c.items() if n != "base"),
                key=lambda x: abs(x["por_perfil"] - x["resto"]),
            )
            caiu.append(
                {
                    "nome": rotulo_de(r["atributo"]),
                    "antes": [c["base"]["por_perfil"], c["base"]["resto"]],
                    "depois": [pior["por_perfil"], pior["resto"]],
                }
            )
        objetivos[objetivo] = {
            "firmes": [p.model_dump() for p in padroes_firmes(df, objetivo)],
            "caiu": caiu,
        }
    recortes = {}
    for coluna in ("tema_principal", "formato_video", "segmento"):
        linhas = []
        for r in recorte(df, coluna).itertuples():
            g = df[(df[coluna] == r.valor) & df["categorizado"]].sort_values("posicao")
            linhas.append(
                {
                    "nome": _valor(coluna, r.valor), "posts": r.posts, "topo": r.taxa_topo,
                    "pedido": r.taxa_pedido, "pedidos": r.pedidos, "maior_canal": r.maior_canal,
                    "capa": g["id"].iat[0],
                }
            )  # fmt: skip
        recortes[coluna] = linhas
    perfis = []
    for p in perfis_em_destaque(df, 8).itertuples():
        g = topo[topo["handle"] == p.handle].sort_values("posicao")
        perfis.append(
            {
                "canal": _celula(p.canal), "inscritos": int(p.inscritos), "no_topo": int(p.no_top),
                "tema": _valor("tema_principal", p.tema), "capa": g["id"].iat[0],
                "formato": _valor("formato_video", p.formato), "fora": p.handle in fora,
            }
        )  # fmt: skip
    cat = df[df["categorizado"]]
    exemplos = [
        {"id": r.id, "titulo": r.titulo, "canal": r.canal, "pedidos": int(r.intencao)}
        for r in cat[cat["lead"]].sort_values("intencao", ascending=False).head(60)
        .drop_duplicates("handle").head(10).itertuples()
    ]  # fmt: skip
    return {
        "posts": len(df), "canais": int(df["handle"].nunique()), "topo": len(topo),
        "comentarios": int(df["lidos"].sum()), "pedidos": int(df["intencao"].sum()),
        "com_pedido": int(df["lead"].sum()), "no_topo": t["topo"], "fora_do_topo": t["fora"],
        "topo_fora_do_publico": float(topo["tema_principal"].eq("outro").mean()),
        "objetivos": objetivos, "recortes": recortes, "perfis": perfis, "exemplos": exemplos,
    }  # fmt: skip


def montar(banco, df, criativos: list, recomendacoes: str = "") -> str:
    """`criativos`: lista de (tema, Saida) já gerados pelo agente. `recomendacoes`: texto humano."""
    topo, hs = top_categorizado(df), hipoteses.ler(banco)
    n_topo = int(df["top_tapi"].sum())
    L = ["# Playbook de conteúdo para MPEs", ""]
    L += [
        f"Base: {_milhar(len(df))} Shorts de {df['handle'].nunique()} canais. "
        f"Alto desempenho: {n_topo} posts (10% superiores em (curtidas + comentários) ÷ "
        f"seguidores), dos quais {len(topo)} categorizados.",
        "",
        "Padrões observados, não causas: repetir uma característica não garante resultado.",
    ]
    if recomendacoes.strip():
        L += ["", "## Recomendações para a Stone", "", recomendacoes.strip()]
    L += _robustez(df)
    L += _recortes(df)
    L += ["", "## Viés do ranking", "", concentracao(df)]
    vereditos = hipoteses.vereditos(banco)
    L += ["", "## O que aparece no topo", ""]
    L += ["| Característica | Frequência no topo | Posts |", "|---|---|---|"]
    for a in achados(df, vereditos, n=20):
        testada = f" ({VEREDITO[a.status]})" if a.status != "nao_testada" else ""
        L.append(
            f"| {rotulo_de(a.atributo)}{testada} | {_pct(a.frequencia_top)} | {a.n_ocorrencias} |"
        )
    L += _comparacoes(df)
    L += _lead(df)
    L += ["", "## Hipóteses testadas", ""]
    if not hs:
        L.append(
            "Nenhuma hipótese registrada: o teste de confirmação dentro do mesmo perfil existe, "
            "roda uma única vez e não foi usado. Nada neste documento foi confirmado por ele."
        )
    for h in hs:
        L.append(
            f"- **{h.id}** {h.afirmacao} ({VEREDITO[h.veredito] if h.veredito else 'pendente'})"
        )
        if t := h.confirmacao:
            L.append(
                f"  - confirmação: efeito {t.efeito:+.1%} "
                f"(IC 95% {t.ic95[0]:+.1%} a {t.ic95[1]:+.1%}), p={t.p:.4f}, "
                f"corte {motor.ALFA}, {t.n_perfis} perfis, {t.n_posts} posts"
            )
    if aprovadas := [h for h in hs if h.aprovada_por_humano]:
        L += ["", "## Regras aprovadas", "", *[f"- {h.afirmacao}" for h in aprovadas]]
    L += ["", "## Perfis em destaque", "", "| Perfil | Inscritos | No topo | % dos seus posts "]
    L[-1] += "| Tema | Formato |"
    L.append("|---|---|---|---|---|---|")
    for p in perfis_em_destaque(df).itertuples() if len(topo) else []:
        L.append(
            f"| {_celula(p.canal)} | {_milhar(p.inscritos)} | {p.no_top} | {_pct(p.taxa_no_top)} "
            f"| {_valor('tema_principal', p.tema)} | {_valor('formato_video', p.formato)} |"
        )
    L += ["", "## Exemplos reais por formato", ""]
    for formato in topo["formato_video"].value_counts().index if len(topo) else []:
        for r in referencias(topo[topo["formato_video"] == formato], "", n=2, max_por_perfil=1):
            L.append(f"- **{_valor('formato_video', formato)}**: [{r.titulo}]({r.link}), {r.canal}")
    L += ["", "## Exemplos reais por tema", ""]
    for tema in topo["tema_principal"].value_counts().index if len(topo) else []:
        if tema != "outro":
            for r in referencias(topo[topo["tema_principal"] == tema], "", n=2, max_por_perfil=1):
                L.append(
                    f"- **{_valor('tema_principal', tema)}**: [{r.titulo}]({r.link}), {r.canal}"
                )
    L += ["", "## Criativos para o canal da Stone", ""]
    L += [
        "Os mesmos que estão na plataforma, cada um ligado aos Shorts reais que o inspiraram. São "
        "versões preliminares: o que está entre [colchetes] precisa existir antes de gravar.",
        "",
    ]
    for tema, saida in criativos:
        for c in saida.creatives[:1]:
            titulos = {r.post_id: r.titulo for r in saida.reference_posts}
            L += [f"### {tema[0].upper()}{tema[1:]}", "", f"**Gancho:** {c.gancho}", ""]
            if c.cenas:
                L += ["| Tempo | Na tela | Cena |", "|---|---|---|"]
                L += [f"| {x.inicio_s} a {x.fim_s} s | {x.na_tela} | {x.cena} |" for x in c.cenas]
                L.append("")
            else:
                L += [f"**Roteiro:** {c.roteiro}", ""]
            L += [f"**Legenda:** {c.legenda}", ""]
            L += [f"**Chamada para ação:** {c.chamada_para_acao}", ""]
            texto = " ".join([c.gancho, c.roteiro, c.legenda, c.chamada_para_acao])
            if faltam := sorted(set(re.findall(r"\[([^\]]+)\]", texto))):
                L += [f"**Precisa existir antes de gravar:** {', '.join(faltam)}.", ""]
            L += ["**Inspirado em:**", ""]
            L += [
                f"- [{titulos.get(i, i)}](https://www.youtube.com/shorts/{i})"
                for i in c.referencias
            ]
            L += ["", f"Execução {saida.run_id}.", ""]
    return "\n".join(L) + "\n"
