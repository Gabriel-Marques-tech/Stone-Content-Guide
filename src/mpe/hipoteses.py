"""Ciclo do agente-pesquisador: explorar → propor → registrar → confirmar → aprovar."""

from pydantic import BaseModel, Field

from mpe.motor import VAGAS, Hipotese, julgar, testar

ESQUEMA = "CREATE TABLE IF NOT EXISTS hipoteses (id VARCHAR PRIMARY KEY, corpo JSON)"


class _Proposta(BaseModel):
    afirmacao: str = Field(min_length=10, max_length=200)
    atributo: str
    direcao: str = Field(pattern="^(mais|menos)$")
    justificativa: str = Field(max_length=400)


class _Propostas(BaseModel):
    hipoteses: list[_Proposta] = Field(min_length=VAGAS, max_length=VAGAS)


def ler(banco) -> list[Hipotese]:
    banco.execute(ESQUEMA)
    linhas = banco.execute("SELECT corpo FROM hipoteses ORDER BY id").fetchall()
    return [Hipotese.model_validate_json(c) for (c,) in linhas]


def _salvar(banco, h: Hipotese):
    banco.execute(ESQUEMA)
    banco.execute("INSERT OR REPLACE INTO hipoteses VALUES (?, ?)", [h.id, h.model_dump_json()])


def metade(df, nome: str):
    return df[(df["metade"] == nome) & df["categorizado"] & df["par_motor"].notna()]


def explorar(df):
    """Só a metade 'explora'. É tudo o que o agente vê antes de propor."""
    return sorted(testar(metade(df, "explora")), key=lambda t: t.p)


INSTRUCAO = """Você é pesquisador de conteúdo para micro e pequenos empreendedores (MPEs).
Abaixo, a EXPLORAÇÃO em metade dos perfis: para cada atributo, a diferença média (dentro do mesmo
perfil) entre posts de alto engajamento e o resto, com p-valor sem correção.
Proponha {n} hipóteses, cada uma sobre um atributo diferente da lista, para confirmar em outros
perfis. Prefira efeitos grandes em atributos que um criador consegue mudar no próximo vídeo, e
evite dois atributos que medem quase a mesma coisa. 'direcao' diz se o atributo aparece mais ou
menos no alto engajamento. A justificativa deve citar os números. Não fale em causa.

{tabela}"""


def registrar(banco, propostas: list[dict], df) -> list[Hipotese]:
    """Trava as hipóteses antes do teste. Recusa uma segunda leva: as vagas são fixas."""
    if ler(banco):
        raise ValueError("já há hipóteses registradas: as vagas são fixas (Bonferroni)")
    if len(propostas) != VAGAS:
        raise ValueError(f"são exatamente {VAGAS} hipóteses")
    explorados = {t.atributo: t for t in explorar(df)}
    nomes = [p["atributo"] for p in propostas]
    if repetidos := {n for n in nomes if nomes.count(n) > 1}:
        raise ValueError(f"atributos repetidos: {sorted(repetidos)}")
    if fora := [n for n in nomes if n not in explorados]:
        raise ValueError(f"atributos fora da exploração: {fora}")
    novas = [
        Hipotese(id=f"H{i}", exploracao=explorados[p["atributo"]], **p)
        for i, p in enumerate(propostas, 1)
    ]
    for h in novas:
        _salvar(banco, h)
    return novas


def propor(banco, df, llm) -> list[Hipotese]:
    if ler(banco):
        raise ValueError("já há hipóteses registradas: as vagas são fixas (Bonferroni)")
    tabela = "\n".join(
        f"- {t.atributo}: top {t.prevalencia_top:.0%}, resto {t.prevalencia_resto:.0%}, "
        f"efeito {t.efeito:+.1%}, p={t.p:.3f}, n={t.ocorrencias}"
        for t in explorar(df)
        if t.ocorrencias >= 15
    )
    saida = llm.json(INSTRUCAO.format(n=VAGAS, tabela=tabela), _Propostas)
    return registrar(banco, [p.model_dump() for p in saida.hipoteses], df)


def confirmar(banco, df) -> list[Hipotese]:
    """Testa cada hipótese na metade 'confirma', uma única vez."""
    pendentes = [h for h in ler(banco) if h.veredito is None]
    if not pendentes:
        return ler(banco)
    testes = testar(metade(df, "confirma"), [h.atributo for h in pendentes])
    if not testes:
        raise ValueError("a metade 'confirma' ainda não tem posts categorizados suficientes")
    for h, t in zip(pendentes, testes, strict=True):
        h.confirmacao, h.veredito = t, julgar(t, h.direcao)
        _salvar(banco, h)
    return ler(banco)


def aprovar(banco, id_: str) -> Hipotese:
    """Ato humano: só o que foi sustentado pode virar regra do playbook."""
    h = next((h for h in ler(banco) if h.id == id_), None)
    if h is None:
        raise ValueError(f"hipótese {id_} não existe")
    if h.veredito != "sustentada":
        raise ValueError(f"{id_} não foi sustentada ({h.veredito}): não pode ser aprovada")
    h.aprovada_por_humano = True
    _salvar(banco, h)
    return h


def vereditos(banco) -> dict[str, str]:
    return {h.atributo: h.veredito for h in ler(banco) if h.veredito}
