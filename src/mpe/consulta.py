"""Consultas à base: todo número que o agente mostra sai daqui, nunca do LLM."""

import json

import numpy as np
import pandas as pd

from mpe.ambiente import MODELO
from mpe.amostra import amostrar, carregar, ranquear
from mpe.comentarios import por_post
from mpe.contrato import Achado, Filtros, Referencia
from mpe.motor import matriz
from mpe.rubrica import CAMPOS_QUADROS, Rubrica

POUCOS = 30  # posts de alto desempenho no recorte: abaixo disso, sinaliza


def base_completa(banco) -> pd.DataFrame:
    """Posts ranqueados + amostra do motor + rubrica aberta em colunas + indicador de lead."""
    return _com_lead(banco, _com_rubrica(banco))


LEAD = ["intencao", "duvida", "relato", "reacao", "critica", "outro", "lidos", "interesse"]


def _com_lead(banco, df: pd.DataFrame) -> pd.DataFrame:
    """Comentários por classe em cada post. `lead`: tem ao menos um comentário de intenção."""
    tabelas = {t for (t,) in banco.execute("SHOW TABLES").fetchall()}
    classes = pd.DataFrame(columns=["id", "classe"])
    if "comentarios" in tabelas:
        classes = banco.execute(
            "SELECT post_id AS id, classe FROM comentarios WHERE classe IS NOT NULL"
        ).df()
    if classes.empty:
        return df.assign(**dict.fromkeys(LEAD, 0), lead=False, interessado=False)
    df = df.merge(por_post(classes)[["id", *LEAD]], on="id", how="left")
    df[LEAD] = df[LEAD].fillna(0).astype(int)
    return df.assign(lead=df["intencao"] >= 1, interessado=df["interesse"] >= 1)


def _com_rubrica(banco) -> pd.DataFrame:
    df = amostrar(ranquear(carregar(banco)))
    fala = _abrir(
        banco.execute(
            "SELECT post_id, rubrica FROM categorias WHERE modelo = ?", [MODELO]
        ).fetchall()
    )
    fala = _com_plano_b(banco, fala)
    quadros = _abrir(banco.execute("SELECT post_id, rubrica FROM categorias_quadros").fetchall())
    if fala.empty and quadros.empty:
        return df.assign(categorizado=False, com_fala=False)
    if quadros.empty:  # um avaliador só: o Gemini responde todos os campos
        df = df.merge(fala, on="id", how="left")
        df["categorizado"] = df["formato_video"].notna()
        return df.assign(com_fala=df["categorizado"])
    # Dois avaliadores, um por campo na base inteira: misturar os dois no mesmo campo criaria
    # diferença entre posts que é do avaliador, não do vídeo.
    de_fala = [c for c in Rubrica.model_fields if c not in CAMPOS_QUADROS]
    df = df.merge(quadros[["id", *CAMPOS_QUADROS]], on="id", how="left")
    df = df.merge(fala.reindex(columns=["id", *de_fala, "avaliador_fala"]), on="id", how="left")
    df["categorizado"] = df["formato_video"].notna()
    df["com_fala"] = df["tom"].notna()
    return df


def _com_plano_b(banco, fala: pd.DataFrame) -> pd.DataFrame:
    """Onde o Gemini não assistiu, entra a leitura por transcrição (Whisper + DeepSeek).

    Só no topo e só para descrever: `avaliador_fala` marca a origem, e a concordância entre os
    dois caminhos nos posts em comum está em scripts/concordancia_fala.py."""
    tabelas = {t for (t,) in banco.execute("SHOW TABLES").fetchall()}
    if "categorias_transcricao" not in tabelas:
        return fala
    extra = _abrir(banco.execute("SELECT post_id, rubrica FROM categorias_transcricao").fetchall())
    if extra.empty:
        return fala
    if not fala.empty:
        extra = extra[~extra["id"].isin(fala["id"])]
    fala = fala.assign(avaliador_fala="video") if not fala.empty else fala
    return pd.concat([fala, extra.assign(avaliador_fala="transcricao")], ignore_index=True)


def _abrir(linhas) -> pd.DataFrame:
    return pd.DataFrame([{"id": i, **json.loads(r)} for i, r in linhas])


def tamanho(inscritos: int) -> str:
    return "pequeno" if inscritos < 10_000 else "medio" if inscritos < 100_000 else "grande"


def filtrar(df: pd.DataFrame, segmento: str | None, filtros: Filtros) -> pd.DataFrame:
    if segmento:
        df = df[df["segmento"] == segmento]
    if filtros.tamanho_perfil:
        df = df[df["inscritos"].map(tamanho) == filtros.tamanho_perfil]
    if filtros.desde:
        df = df[df["publicado_em"] >= pd.Timestamp(filtros.desde)]
    if filtros.ate:
        df = df[df["publicado_em"] < pd.Timestamp(filtros.ate) + pd.Timedelta(days=1)]
    return df


VAZIAS = {
    "como", "para", "quais", "qual", "mais", "sobre", "posts", "post", "video", "videos", "vídeo",
    "vídeos", "short", "shorts", "conteudo", "conteúdo", "pequeno", "pequenos", "negocio",
    "negócio", "negocios", "negócios", "empreendedor", "empreendedores", "aparecem", "entre",
    "alto", "desempenho", "engajamento", "formato", "formatos", "criar", "fazer", "dono", "dona",
    "empresa", "empresas", "melhor", "melhores", "that", "with", "stone", "canal", "criativo",
    "criativos", "donos", "falando",
}  # fmt: skip
MIN_TEMA = 5  # posts de alto desempenho no tema: abaixo disso, o recorte temático não se sustenta


def _raizes(texto: str) -> set[str]:
    """Palavras sem plural simples, para 'maquininhas' casar com 'maquininha'."""
    return {p[:-1] if p.endswith("s") else p for p in _palavras(texto) - VAZIAS}


def por_tema(df: pd.DataFrame, termos: str, minimo: int = MIN_TEMA) -> tuple[pd.DataFrame, bool]:
    """Recorta os posts que falam do assunto do pedido (título, descrição e transcrição).

    Sem isso, toda pergunta recebia as frequências do topo inteiro. Devolve (recorte, usou_tema);
    se o tema tiver menos de `minimo` posts de alto desempenho, mantém o recorte original.
    """
    alvo = _raizes(termos)
    if not alvo or df.empty:
        return df, False
    texto = df["titulo"].fillna("")
    for coluna in ("descricao", "transcricao"):
        if coluna in df:
            texto = texto + " " + df[coluna].fillna("")
    do_tema = df[[bool(alvo & _raizes(t)) for t in texto]]
    if len(top_categorizado(do_tema)) < minimo:
        return df, False
    return do_tema, True


def top_categorizado(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["top_tapi"] & df["categorizado"]].reset_index(drop=True)


def achados(df: pd.DataFrame, vereditos: dict[str, str] | None = None, n: int = 12) -> list[Achado]:
    topo = top_categorizado(df)
    if topo.empty:
        return []
    x = matriz(topo)
    freq = x.mean().dropna().sort_values(ascending=False).head(n)
    return [
        Achado(
            atributo=a,
            frequencia_top=round(float(f), 3),
            n_top=int(x[a].notna().sum()),
            n_ocorrencias=int(x[a].sum()),
            status=(vereditos or {}).get(a, "nao_testada"),
        )
        for a, f in freq.items()
    ]


CATEGORIAS_MOSTRADAS = [
    "formato_video", "tipo_hook", "hook_primeiros_3s", "tema_principal", "tom", "tipo_cta",
    "elementos_top5",
]  # fmt: skip


def referencia(linha) -> Referencia:
    return Referencia(
        post_id=linha["id"],
        link=f"https://www.youtube.com/shorts/{linha['id']}",
        titulo=linha["titulo"],
        canal=linha["canal"],
        inscritos=int(linha["inscritos"]),
        engajamento=round(float(linha["engajamento"]), 5),
        posicao=int(linha["posicao"]),
        pedidos=int(linha.get("intencao", 0)),
        categorias={c: linha[c] for c in CATEGORIAS_MOSTRADAS},
    )


def _palavras(texto: str) -> set[str]:
    return {
        p for p in "".join(c if c.isalnum() else " " for c in texto.lower()).split() if len(p) > 3
    }


def referencias(
    df: pd.DataFrame,
    query: str,
    n: int = 6,
    max_por_perfil: int = 2,
    objetivo: str = "engajamento",
) -> list[Referencia]:
    """Posts do objetivo mais parecidos com o pedido, limitados por perfil: sem o limite, três
    canais pequenos tomariam a lista inteira (viés da métrica por seguidores).

    Objetivo contato: posts com comentário pedindo contato, e só depois os mais engajados."""
    topo = top_categorizado(df)
    if objetivo == "contato" and "lead" in df:
        topo = df[(df["top_tapi"] | df["lead"]) & df["categorizado"]].reset_index(drop=True)
    if "com_fala" in topo:  # referência de criativo precisa do gancho e da fala
        topo = topo[topo["com_fala"]]
    topo = topo.copy()
    if topo.empty:
        return []
    alvo = _raizes(query)
    corpo = topo["tema_principal"].fillna("") + " " + topo["transcricao"].fillna("")
    titulos = [_raizes(t) for t in topo["titulo"].fillna("")]
    textos = [a | _raizes(b) for a, b in zip(titulos, corpo, strict=True)]
    # palavra rara pesa mais que palavra comum; no título, o dobro
    peso = {p: np.log(1 + len(textos) / (1 + sum(p in t for t in textos))) for p in alvo}
    topo["_assunto"] = [
        sum(peso[p] * (2 if p in tit else 1) for p in alvo & t)
        for tit, t in zip(titulos, textos, strict=True)
    ]
    if objetivo == "contato" and "lead" in topo:
        topo["_assunto"] *= 1 + 0.6 * topo["lead"]
    topo = topo.sort_values(["_assunto", "engajamento"], ascending=False)
    topo = topo[topo.groupby("handle").cumcount() < max_por_perfil].head(n)
    return [referencia(linha) for _, linha in topo.iterrows()]


def perfis_em_destaque(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Criadores mais presentes no top, com tema e formato predominantes."""
    topo = top_categorizado(df)
    total = df.groupby("handle").size()

    def moda(s):
        return s.mode().iat[0]

    g = topo.groupby("handle").agg(
        canal=("canal", "first"),
        inscritos=("inscritos", "first"),
        no_top=("id", "size"),
        tema=("tema_principal", moda),
        formato=("formato_video", moda),
    )
    g["taxa_no_top"] = g["no_top"] / total.reindex(g.index)
    return g.sort_values("no_top", ascending=False).head(n).reset_index()


def _frequencias(df: pd.DataFrame, por_perfil: bool = False) -> pd.Series:
    x = matriz(df)
    if not por_perfil:
        return x.mean()
    # Peso igual por perfil: tira o domínio dos poucos canais que ocupam metade do topo.
    return x.groupby(df["handle"].to_numpy()).mean().mean()


# Campos de fala em que os dois caminhos (Gemini no vídeo, DeepSeek na transcrição) concordam pouco:
# kappa abaixo de 0,60 em 163 posts (scripts/concordancia_fala.py). Como o topo foi lido mais pela
# transcrição e o resto mais pelo vídeo, comparar esses campos mediria o avaliador, não o vídeo.
FALA_FRACA = {
    "tipo_hook", "tom", "criador_e_empreendedor_real", "usa_linguagem_regional",
    "promove_produto_proprio",
}  # fmt: skip


def _um_avaliador(df: pd.DataFrame, avaliador: str) -> pd.DataFrame:
    """Apaga os campos de fala dos posts lidos pelo outro avaliador.

    Medido em 169 posts lidos pelos dois: a transcrição marca oferta explícita em 44% e o vídeo em
    28%; chamada para ação, 62% e 47%. Misturar os dois numa comparação mede o avaliador."""
    if "avaliador_fala" not in df:
        return df
    de_fala = [c for c in Rubrica.model_fields if c not in CAMPOS_QUADROS and c in df]
    df = df.copy()
    df.loc[df["avaliador_fala"] != avaliador, de_fala] = None
    return df


def contraste(
    df: pd.DataFrame, grupo: str, minimo: float = 0.08, avaliador: str | None = None
) -> pd.DataFrame:
    """Frequência de cada característica nos posts com `grupo` verdadeiro e nos demais.

    Descritivo, como pede o TAPI. `por_perfil` dá o mesmo peso a cada perfil presente no grupo.
    Só entram diferenças de pelo menos `minimo`. Com `avaliador`, os campos de fala usam só os
    posts lidos por ele, dos dois lados."""
    if avaliador:
        df = _um_avaliador(df, avaliador)
    cat = df[df["categorizado"]]
    dentro, fora = cat[cat[grupo]], cat[~cat[grupo]]
    if dentro.empty or fora.empty:
        return pd.DataFrame(
            columns=["atributo", "grupo", "por_perfil", "resto", "n", "n_resto", "dif"]
        )
    t = pd.DataFrame(
        {
            "grupo": _frequencias(dentro),
            "por_perfil": _frequencias(dentro, por_perfil=True),
            "resto": _frequencias(fora),
            "n": matriz(dentro).notna().sum(),
            "n_resto": matriz(fora).notna().sum(),
        }
    ).dropna()
    t["dif"] = t["grupo"] - t["resto"]
    t = t[[a.split("=")[0] not in FALA_FRACA for a in t.index]]
    t = t[(t["dif"].abs() >= minimo) & (t["n"] >= 20)].sort_values("dif", ascending=False)
    return t.rename_axis("atributo").reset_index()


# Parte da base é vídeo do lojista para o cliente dele (corte de cabelo, pizza, lembrancinha), e não
# para o lojista, que é o público do TAPI. Esses canais engajam muito e ocupam boa parte do topo.
MAIORIA_OUTRO, MIN_POSTS_CANAL, MIN_CENARIO = 0.5, 20, 200


def canais_fora_do_publico(df: pd.DataFrame) -> list[str]:
    """Canais em que a maioria dos posts caiu no tema 'outro' (nenhum tema de negócio)."""
    g = df.groupby("handle")["tema_principal"].agg(n="size", outro=lambda s: s.eq("outro").mean())
    return g[(g["outro"] >= MAIORIA_OUTRO) & (g["n"] >= MIN_POSTS_CANAL)].index.tolist()


def _ranquear_de_novo(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    corte = int(np.ceil(len(df) * 0.1))
    df["top_tapi"] = df["engajamento"].rank(ascending=False, method="first") <= corte
    return df.reset_index(drop=True)


def cenarios(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """A base e dois recortes sem conteúdo fora do público, com o topo recalculado em cada um."""
    if "tema_principal" not in df:
        return {"base": df}
    recortes = {
        "sem_posts": df[df["tema_principal"] != "outro"],
        "sem_canais": df[~df["handle"].isin(canais_fora_do_publico(df))],
    }
    return {"base": df} | {
        n: _ranquear_de_novo(r) for n, r in recortes.items() if len(r) >= MIN_CENARIO
    }


def recorte(df: pd.DataFrame, coluna: str, minimo: int = 20) -> pd.DataFrame:
    """Por tema, formato ou segmento: quanto entra no topo, quanto recebe pedido e o que domina."""
    cat = df[df["categorizado"]]
    outra = "formato_video" if coluna != "formato_video" else "tema_principal"
    linhas = []
    for valor, g in cat.groupby(coluna):
        if len(g) < minimo:
            continue
        topo = g[g["top_tapi"]]
        linhas.append(
            {
                "valor": valor, "posts": len(g), "perfis": g["handle"].nunique(),
                "no_topo": len(topo), "taxa_topo": float(g["top_tapi"].mean()),
                "taxa_pedido": float(g["lead"].mean()) if "lead" in g else 0.0,
                "pedidos": int(g["lead"].sum()) if "lead" in g else 0,
                "domina": topo[outra].mode().iat[0] if len(topo) else None,
                "maior_canal": float(topo["handle"].value_counts(normalize=True).iat[0])
                if len(topo) else 0.0,
            }
        )  # fmt: skip
    colunas = ["valor", "posts", "perfis", "no_topo", "taxa_topo", "taxa_pedido", "pedidos"]
    return pd.DataFrame(linhas, columns=[*colunas, "domina", "maior_canal"]).sort_values(
        "posts", ascending=False
    )


# Avaliador de fala usado em cada comparação: o que cobre os dois lados dela.
# Topo contra resto: o vídeo (Gemini), que leu parte do topo e a amostra fora dele.
# Lead e interesse: a transcrição, que leu o topo e os posts com intenção; nesses, o lado
# "demais" dos campos de fala são posts do topo sem comentário de intenção.
AVALIADOR = {"top_tapi": "video", "lead": "transcricao", "interessado": "transcricao"}


def top_x_resto(df: pd.DataFrame, minimo: float = 0.08) -> pd.DataFrame:
    return contraste(df, "top_tapi", minimo, AVALIADOR["top_tapi"])


def lead_x_resto(df: pd.DataFrame, minimo: float = 0.08) -> pd.DataFrame:
    """O que aparece mais nos posts que receberam comentário com intenção de contato."""
    return contraste(df, "lead", minimo, AVALIADOR["lead"])


def interesse_x_resto(df: pd.DataFrame, minimo: float = 0.08) -> pd.DataFrame:
    """O que aparece mais nos posts com comentário de intenção ou de dúvida."""
    return contraste(df, "interessado", minimo, AVALIADOR["interessado"])


def canal_x_topo(df: pd.DataFrame, handle: str, minimo: float = 0.10) -> pd.DataFrame:
    """Onde um canal (a Stone) difere do topo, com peso igual por perfil do topo."""
    cat = df[df["categorizado"]]
    do_canal, topo = cat[cat["handle"] == handle], cat[cat["top_tapi"] & (cat["handle"] != handle)]
    if do_canal.empty or topo.empty:
        return pd.DataFrame(columns=["atributo", "canal", "topo", "dif"])
    # só campos que cobrem a base inteira: os de fala dependem de quais posts o Gemini assistiu
    t = pd.DataFrame({"canal": _frequencias(do_canal), "topo": _frequencias(topo, True)})
    cobertura = matriz(do_canal).notna().mean()
    t = t[cobertura.reindex(t.index) >= 0.9].dropna()
    t["dif"] = t["canal"] - t["topo"]
    t = t[t["dif"].abs() >= minimo].sort_values("dif")
    return t.rename_axis("atributo").reset_index()


# Recorte de Lee, Hosanagar e Nair (2018): conteúdo de marca informativo, de personalidade ou os
# dois. Só campos lidos na base inteira (quadros), para valer para todos os posts.
_PERSONALIDADE = {
    "formato_video": {"humor_esquete", "depoimento", "bastidores", "antes_depois", "trend"},
    "tema_principal": {"historia_de_empreendedor", "motivacao"},
}
_INFORMATIVO = {
    "formato_video": {"tutorial", "lista_dicas"},
    "tema_principal": {"financas", "ferramentas_maquininha", "gestao", "vendas"},
}


def tipo_conteudo(df: pd.DataFrame) -> pd.Series:
    """'informativo', 'personalidade', 'os_dois' ou 'nenhum' para cada post categorizado."""

    def algum(regras):
        return pd.concat([df[c].isin(v) for c, v in regras.items()], axis=1).any(axis=1)

    info = algum(_INFORMATIVO) | df["cita_regra_ou_lei"].eq(True)
    pers = algum(_PERSONALIDADE)
    tipo = pd.Series("nenhum", index=df.index)
    tipo[info & ~pers], tipo[pers & ~info], tipo[info & pers] = (
        "informativo", "personalidade", "os_dois",
    )  # fmt: skip
    return tipo.where(df["categorizado"])


def pedido_por_engajamento(df: pd.DataFrame) -> dict:
    """Pedido de contato nos 10% mais engajados e fora deles, com a taxa-base ao lado.

    Como o topo é 10% da base, 90% de qualquer coisa sem relação com ele cairia fora: dizer só
    "a maioria dos pedidos está fora do topo" inverte o sentido do dado."""
    topo, fora = df[df["top_tapi"]], df[~df["top_tapi"]]
    com = df[df["lidos"] > 0]
    ct, cf = com[com["top_tapi"]], com[~com["top_tapi"]]
    return {
        "topo": float(topo["lead"].mean()), "n_topo": int(topo["lead"].sum()),
        "fora": float(fora["lead"].mean()), "n_fora": int(fora["lead"].sum()),
        "topo_comentado": float(ct["lead"].mean()) if len(ct) else 0.0,
        "fora_comentado": float(cf["lead"].mean()) if len(cf) else 0.0,
    }  # fmt: skip


def _ic(valores: pd.Series) -> tuple[float, float]:
    """IC 95% da média, reamostrando perfis."""
    if valores.empty:
        return (float("nan"), float("nan"))
    rng, v = np.random.default_rng(0), valores.to_numpy()
    medias = rng.choice(v, (3000, len(v))).mean(axis=1)
    baixo, alto = np.percentile(medias, [2.5, 97.5])
    return (float(baixo), float(alto))


def desfechos_por_tipo(df: pd.DataFrame, min_posts: int = 5) -> pd.DataFrame:
    """Para cada tipo de conteúdo: quanto entra no topo, quanto gera interesse e intenção.

    As colunas `_perfil` dão o mesmo peso a cada perfil com pelo menos `min_posts` do tipo."""
    d = df[df["categorizado"]].assign(tipo=tipo_conteudo(df))
    linhas = []
    for tipo, g in d.groupby("tipo"):
        por_perfil = g.groupby("handle").agg(
            n=("id", "size"), top=("top_tapi", "mean"), inter=("interessado", "mean"),
            lead=("lead", "mean"),
        )  # fmt: skip
        p = por_perfil[por_perfil["n"] >= min_posts]
        linhas.append(
            {
                "tipo": tipo, "posts": len(g), "perfis": len(p),
                "no_topo": g["top_tapi"].mean(), "no_topo_perfil": p["top"].mean(),
                "interesse": g["interessado"].mean(), "interesse_perfil": p["inter"].mean(),
                "lead": g["lead"].mean(), "lead_perfil": p["lead"].mean(),
                "ic_topo": _ic(p["top"]), "ic_interesse": _ic(p["inter"]),
            }
        )  # fmt: skip
    return pd.DataFrame(linhas).sort_values("posts", ascending=False)
