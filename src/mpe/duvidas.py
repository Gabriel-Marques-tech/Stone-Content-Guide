"""Dúvidas do time de conteúdo, respondidas com dois desfechos: engajamento e pedido de contato.

Cada dúvida é uma característica da rubrica. Para ela, a base responde duas coisas:
- engajamento: quanto a característica aparece nos 10% superiores e no resto;
- contato: quanto aparece nos posts com comentário de intenção (indicador de lead) e nos demais.
O público da base é o dono de pequeno negócio: os vídeos são feitos PARA ele. Por isso quem usa
a tela é o time da Stone, e não o lojista. São associações observadas, não causa nem garantia.
"""

from typing import Literal

import pandas as pd

from mpe.consulta import AVALIADOR, cenarios, contraste
from mpe.contrato import Padrao
from mpe.motor import matriz
from mpe.rubrica import CAMPOS_QUADROS

MIN_DIFERENCA = 0.08  # 8 pontos entre o grupo e os demais
MIN_FIRME = 0.05  # e pelo menos 5 com peso igual por perfil, na mesma direção

# "indefinido" não é "não muda": há diferença, mas ela some quando cada canal pesa igual.
Sinal = Literal["mais", "menos", "parecido", "indefinido"]

# (atributo, pergunta, assunto, grupo do desfecho de contato)
DUVIDAS = [
    ("tem_cta", "Vale pedir uma ação no fim do vídeo?", "o que se fala", "lead"),
    ("fala_direto_com_dono", "Vale falar direto com o dono do negócio?", "o que se fala", "lead"),
    ("oferta_ou_beneficio_explicito", "Vale dizer o que a pessoa ganha?", "o que se fala", "lead"),
    ("passo_concreto", "Vale ensinar um passo pra fazer hoje?", "o que se fala", "interessado"),
    ("exemplo_com_numeros", "Vale mostrar a conta com números?", "o que se fala", "interessado"),
    ("mostra_ambiente_real", "Vale gravar dentro de um negócio?", "como se grava", "lead"),
    ("formato_video=talking_head", "Vale só falar pra câmera?", "como se grava", "lead"),
    ("formato_video=tutorial", "Vale fazer tutorial?", "como se grava", "lead"),
    ("duracao_faixa=acima_60s", "Vale passar de um minuto?", "como se grava", "interessado"),
    ("tema_principal=financas", "Vale falar de finanças e imposto?", "do que se fala",
     "interessado"),
    ("cita_regra_ou_lei", "Vale explicar regra ou lei?", "do que se fala", "interessado"),
]  # fmt: skip

# Como dizer cada sinal do avaliador de roteiro para quem grava: (se falta, se sobra)
CONSELHOS = {
    "tem_cta": ("Peça uma ação no fim do vídeo", "Não precisa pedir ação no fim"),
    "fala_direto_com_dono": ("Fale direto com o dono do negócio", "Fale com todo mundo"),
    "oferta_ou_beneficio_explicito": ("Diga o que a pessoa ganha", "Não venda no vídeo"),
    "passo_concreto": ("Dê um passo que dá pra fazer hoje", "Menos passo a passo"),
    "exemplo_com_numeros": ("Mostre a conta com números", "Menos conta e número"),
    "mostra_ambiente_real": ("Grave dentro de um negócio", "Não precisa mostrar o negócio"),
    "cita_regra_ou_lei": ("Explique a regra ou a lei", "Sem juridiquês"),
    "cita_erro_ou_perda": ("Fale do erro ou do prejuízo", "Não foque em erro e prejuízo"),
    "tem_rosto": ("Apareça no vídeo", "Não precisa aparecer"),
    "texto_na_tela": ("Ponha texto na tela", "Menos texto na tela"),
    "prova_social": ("Mostre um cliente ou um resultado", "Menos depoimento"),
    "numero_no_gancho": ("Comece com um número", "Não comece com número"),
    "formato_video=talking_head": ("Fale para a câmera", "Não fique só falando pra câmera"),
    "formato_video=tutorial": ("Ensine passo a passo", "Não faça tutorial"),
    "formato_video=bastidores": ("Mostre os bastidores", "Menos bastidores"),
    "formato_video=depoimento": ("Traga um depoimento", "Menos depoimento"),
    "formato_video=lista_dicas": ("Faça uma lista de dicas", "Não faça lista de dicas"),
    "formato_video=humor_esquete": ("Use humor", "Menos esquete"),
    "tema_principal=financas": ("Fale de dinheiro e imposto", "Fuja de dinheiro e imposto"),
    "tema_principal=gestao": ("Fale de gestão do negócio", "Menos gestão"),
    "tema_principal=vendas": ("Fale de vendas", "Menos vendas"),
    "tema_principal=marketing": ("Fale de divulgação", "Menos divulgação"),
    "tema_principal=motivacao": ("Use motivação", "Menos motivação"),
    "tema_principal=ferramentas_maquininha": ("Fale de maquininha", "Menos ferramenta"),
    "tema_principal=historia_de_empreendedor": ("Conte a história de um negócio", "Menos história"),
    "tipo_cta=comentar": ("Peça para comentar", "Não peça comentário"),
    "tipo_cta=link_na_bio": ("Mande para o link", "Não mande para o link na bio"),
    "tipo_cta=seguir": ("Peça para seguir", "Não peça para seguir"),
    "tipo_cta=nenhum": ("Não peça nada no fim", "Peça uma ação no fim do vídeo"),
    "tipo_cta=outro": ("Peça uma ação diferente", "Use uma chamada mais comum"),
    "duracao_faixa=ate_30s": ("Faça em até 30 segundos", "Passe dos 30 segundos"),
    "duracao_faixa=31_60s": ("Fique entre 30 e 60 segundos", "Saia da faixa de 30 a 60 s"),
    "duracao_faixa=acima_60s": ("Passe de um minuto", "Fique abaixo de um minuto"),
}  # fmt: skip


# Nome de cada característica para quem lê o playbook e a plataforma
NOMES = {
    "oferta_ou_beneficio_explicito": "Diz o que a pessoa ganha", "tem_cta": "Pede uma ação",
    "fala_direto_com_dono": "Fala direto com o dono", "passo_concreto": "Ensina um passo concreto",
    "exemplo_com_numeros": "Mostra conta com números", "mostra_ambiente_real": "Negócio de verdade",
    "cita_regra_ou_lei": "Cita regra ou lei", "cita_erro_ou_perda": "Fala de erro ou prejuízo",
    "tem_rosto": "Tem rosto", "texto_na_tela": "Texto na tela", "prova_social": "Prova social",
    "numero_no_gancho": "Número no gancho", "criador_e_empreendedor_real": "Criador é empreendedor",
    "promove_produto_proprio": "Promove produto próprio", "tom=informal": "Tom informal",
    "usa_linguagem_regional": "Linguagem regional",
    "formato_video=talking_head": "Só rosto falando", "formato_video=tutorial": "Tutorial",
    "formato_video=bastidores": "Bastidores", "formato_video=depoimento": "Depoimento",
    "formato_video=lista_dicas": "Lista de dicas", "formato_video=humor_esquete": "Humor",
    "formato_video=trend": "Trend", "formato_video=antes_depois": "Antes e depois",
    "formato_video=outro": "Outro formato", "tema_principal=financas": "Tema: finanças",
    "tema_principal=gestao": "Tema: gestão", "tema_principal=vendas": "Tema: vendas",
    "tema_principal=marketing": "Tema: marketing", "tema_principal=outro": "Tema: fora de negócio",
    "tema_principal=motivacao": "Tema: motivação",
    "tema_principal=atendimento": "Tema: atendimento",
    "tema_principal=ferramentas_maquininha": "Tema: maquininha e ferramentas",
    "tema_principal=historia_de_empreendedor": "Tema: história de empreendedor",
    "tipo_cta=nenhum": "Não pede nada", "tipo_cta=comentar": "Pede comentário",
    "tipo_cta=link_na_bio": "Manda para o link", "tipo_cta=seguir": "Pede para seguir",
    "tipo_cta=outro": "Outra chamada", "duracao_faixa=ate_30s": "Até 30 s",
    "duracao_faixa=31_60s": "De 31 a 60 s", "duracao_faixa=acima_60s": "Mais de 60 s",
    "tipo_hook=curiosidade": "Gancho: curiosidade", "tipo_hook=pergunta": "Gancho: pergunta",
}  # fmt: skip


def nome(atributo: str) -> str:
    return NOMES.get(atributo, atributo)


def conselho(atributo: str, incluir: bool) -> str:
    par = CONSELHOS.get(atributo)
    return par[0 if incluir else 1] if par else f"{'Inclua' if incluir else 'Evite'}: {atributo}"


def sinal(grupo: float, por_perfil: float, resto: float) -> Sinal:
    """`mais`/`menos` só quando a diferença se mantém com peso igual por perfil."""
    bruta, firme = grupo - resto, por_perfil - resto
    if abs(bruta) < MIN_DIFERENCA:
        return "indefinido" if abs(firme) >= MIN_DIFERENCA else "parecido"
    if bruta * firme <= 0 or abs(firme) < MIN_FIRME:
        return "indefinido"
    return "mais" if bruta > 0 else "menos"


def leitura(atributo: str, grupo: str) -> str:
    """De onde saiu o campo: muda quem está na comparação, então aparece no comprovante."""
    campo = atributo.split("=")[0]
    if campo in CAMPOS_QUADROS or campo == "duracao_faixa":
        return "base inteira"
    if AVALIADOR[grupo] == "video":
        return "só vídeos assistidos com som"
    return "só vídeos transcritos; os outros são do topo de engajamento"


def _desfecho(tabela: pd.DataFrame, atributo: str, grupo: str) -> dict | None:
    linha = tabela[tabela["atributo"] == atributo]
    if linha.empty:
        return None
    r = linha.iloc[0]
    valores = {c: float(r[c]) for c in ("grupo", "por_perfil", "resto")}
    return {
        "sinal": sinal(**valores),
        **{c: round(v, 3) for c, v in valores.items()},
        "n": int(r["n"]), "n_outros": int(r["n_resto"]), "leitura": leitura(atributo, grupo),
    }  # fmt: skip


GRUPO_DO_OBJETIVO = {"engajamento": "top_tapi", "contato": "lead"}


def robustez(df: pd.DataFrame, grupo: str) -> list[dict]:
    """Cada característica com diferença firme em algum cenário, e se ela se mantém em todos.

    Os cenários tiram o conteúdo que não é voltado ao lojista (consulta.cenarios). `firme` pede a
    mesma direção e os mesmos cortes nos três; o que falha em um vira hipótese."""
    tabelas = {
        n: contraste(d, grupo, 0.0, AVALIADOR[grupo]).set_index("atributo")
        for n, d in cenarios(df).items()
    }
    saida = []
    for atributo in sorted(set().union(*(t.index for t in tabelas.values()))):
        por_cenario = {}
        for nome, t in tabelas.items():
            if atributo in t.index:
                r = t.loc[atributo]
                valores = {c: float(r[c]) for c in ("grupo", "por_perfil", "resto")}
                por_cenario[nome] = {
                    **valores, "n": int(r["n"]), "n_outros": int(r["n_resto"]),
                    "sinal": sinal(**valores),
                }  # fmt: skip
        sinais = {c["sinal"] for c in por_cenario.values()}
        if not sinais & {"mais", "menos"}:
            continue
        firme = len(por_cenario) == len(tabelas) and sinais in ({"mais"}, {"menos"})
        saida.append({"atributo": atributo, "firme": firme, "cenarios": por_cenario})
    return saida


def firmes(df: pd.DataFrame, grupo: str) -> set[str]:
    return {r["atributo"] for r in robustez(df, grupo) if r["firme"]}


def padroes_firmes(df: pd.DataFrame, objetivo: str, n: int = 6) -> list[Padrao]:
    """O que um criativo pode aplicar para o objetivo. Tema fica de fora: vem do pedido.

    Só entra o que é para fazer, e "não ficar só falando": o que aparece menos nos mais engajados
    (regra, conta, chamada, falar com o dono) descreve um topo cheio de canais que não falam com
    lojista, e como ordem de roteiro levaria a vídeo sem conteúdo para ele.
    Sai da base inteira, não do assunto: por assunto há posts de menos para comparar."""
    grupo = GRUPO_DO_OBJETIVO[objetivo]
    if grupo not in df:
        return []
    achados: dict[str, Padrao] = {}
    tabela = contraste(df, grupo, MIN_DIFERENCA, AVALIADOR[grupo])
    tabela = tabela[tabela["atributo"].isin(firmes(df, grupo))]
    tabela = tabela.assign(firme=(tabela["por_perfil"] - tabela["resto"]).abs().astype(float))
    for r in tabela.sort_values("firme", ascending=False).itertuples():
        s = sinal(r.grupo, r.por_perfil, r.resto)
        if s not in ("mais", "menos") or r.atributo not in CONSELHOS:
            continue
        if r.atributo.startswith("tema_principal"):
            continue
        incluir = s == "mais"
        if r.atributo == "tipo_cta=nenhum":
            continue
        if not incluir and r.atributo != "formato_video=talking_head":
            continue
        valores = [v if incluir else 1 - v for v in (float(r.por_perfil), float(r.resto))]
        texto = conselho(r.atributo, incluir)
        achados.setdefault(
            texto,
            Padrao(
                atributo=r.atributo, conselho=texto, no_grupo=round(valores[0], 3),
                nos_outros=round(valores[1], 3), n=int(r.n), n_outros=int(r.n_resto),
                leitura=leitura(r.atributo, grupo),
            ),
        )  # fmt: skip
    return list(achados.values())[:n]


FRASES = {
    "engajamento": {
        "mais": "Aparece mais nos vídeos mais engajados.",
        "menos": "Aparece menos nos vídeos mais engajados.",
        "parecido": "Engajamento: aparece parecido nos dois lados.",
        "indefinido": "Engajamento: ainda não dá pra dizer.",
    },
    "contato": {
        "mais": "Bom candidato quando o objetivo é contato.",
        "menos": "Aparece menos nos vídeos que recebem pedido de contato.",
        "parecido": "Contato: aparece parecido nos dois lados.",
        "indefinido": "Contato: ainda não dá pra dizer.",
    },
}


def montar(df: pd.DataFrame) -> list[dict]:
    """Uma entrada por dúvida, com os dois desfechos. Desfecho sem dado suficiente vem nulo."""
    tabelas = {g: contraste(df, g, 0.0, AVALIADOR[g]) for g in ("top_tapi", "lead", "interessado")}
    saida = []
    for atributo, pergunta, assunto, grupo in DUVIDAS:
        desfechos = {
            "engajamento": _desfecho(tabelas["top_tapi"], atributo, "top_tapi"),
            "contato": _desfecho(tabelas[grupo], atributo, grupo),
        }
        dica = " ".join(
            FRASES[nome][d["sinal"] if d else "indefinido"]
            for nome, d in reversed(desfechos.items())
        )
        saida.append(
            {
                "atributo": atributo, "pergunta": pergunta, "assunto": assunto, "dica": dica,
                **desfechos, "conta_duvida": grupo == "interessado",
            }
        )  # fmt: skip
    return saida


def resumo(df: pd.DataFrame) -> dict:
    """O que a tela diz sobre a base: tamanho, período e o achado central."""
    leads = df[df["lead"]]
    return {
        "videos": len(df), "canais": int(df["handle"].nunique()),
        "comentarios": int(df["lidos"].sum()), "pedidos": int(df["intencao"].sum()),
        "com_pedido": len(leads), "pedido_fora_do_topo": int((~leads["top_tapi"]).sum()),
        "de": df["publicado_em"].min().strftime("%m/%Y"),
        "ate": df["publicado_em"].max().strftime("%m/%Y"),
        "coleta": df["coletado_em"].max().strftime("%d/%m/%Y"),
    }  # fmt: skip


def exemplos(df: pd.DataFrame, atributo: str, n: int = 6) -> dict[str, list[dict]]:
    """Shorts reais que têm a característica: com pedido de contato e mais engajados."""
    cat = df[df["categorizado"]]
    x = matriz(cat)
    if atributo not in x:
        raise KeyError(atributo)
    com = cat[x[atributo] == 1]

    def lista(sub, ordem):
        sub = sub.sort_values(ordem, ascending=False)
        sub = sub[sub.groupby("handle").cumcount() < 2].head(n)
        return [
            {"id": r.id, "titulo": r.titulo, "canal": r.canal, "capa": r.thumbnail,
             "pedidos": int(r.intencao), "top": bool(r.top_tapi)}
            for r in sub.itertuples()
        ]  # fmt: skip

    return {
        "contato": lista(com[com["lead"]], "intencao"),
        "engajamento": lista(com[com["top_tapi"]], "engajamento"),
    }
