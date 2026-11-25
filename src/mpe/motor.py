"""Motor de hipóteses: uma característica aparece mais no top do que no resto do MESMO perfil?

Regras fixas, que nem o agente nem quem opera muda:
1. O agente só vê a metade 'explora' dos perfis. O teste que vale é na metade 'confirma'.
2. Efeito = média, entre perfis, de (prevalência no top − prevalência no resto).
3. p-valor por permutação dos rótulos dentro de cada perfil, com Bonferroni pelo nº de vagas.
4. Cada hipótese é confirmada uma vez só e fica registrada, inclusive se cair.
O que sai é associação observada, não causa.
"""

from datetime import UTC, datetime
from typing import Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

VAGAS = 5
ALFA = 0.05 / VAGAS  # Bonferroni
EFEITO_MINIMO = 0.10  # 10 pontos percentuais: abaixo disso não muda uma decisão de conteúdo
MIN_POR_GRUPO = 3  # posts categorizados por grupo para o perfil contar
MIN_PERFIS = 8
MIN_OCORRENCIAS = 15
PERMUTACOES = 10_000

Veredito = Literal["sustentada", "nao_sustentada", "evidencia_insuficiente"]


class Teste(BaseModel):
    atributo: str
    efeito: float
    ic95: tuple[float, float]
    p: float
    prevalencia_top: float
    prevalencia_resto: float
    n_posts: int
    n_perfis: int
    ocorrencias: int


class Hipotese(BaseModel):
    id: str = Field(pattern=r"^H\d+$")
    afirmacao: str = Field(min_length=10)
    atributo: str
    direcao: Literal["mais", "menos"]
    justificativa: str
    exploracao: Teste | None = None
    confirmacao: Teste | None = None
    veredito: Veredito | None = None
    aprovada_por_humano: bool = False
    registrada_em: datetime = Field(default_factory=lambda: datetime.now(UTC))


BOOLEANOS = [
    "tem_rosto", "criador_e_empreendedor_real", "prova_social", "texto_na_tela",
    "usa_linguagem_regional", "tem_cta", "oferta_ou_beneficio_explicito", "numero_no_gancho",
    "passo_concreto", "exemplo_com_numeros", "cita_erro_ou_perda", "cita_regra_ou_lei",
    "fala_direto_com_dono", "mostra_ambiente_real", "promove_produto_proprio",
]  # fmt: skip
CATEGORICOS = ["formato_video", "tipo_hook", "tema_principal", "tom", "tipo_cta"]


def faixa_duracao(s: int) -> str:
    return "ate_30s" if s <= 30 else "31_60s" if s <= 60 else "acima_60s"


def _zero_um(valor) -> float:
    return np.nan if pd.isna(valor) else float(bool(valor))


def matriz(df: pd.DataFrame) -> pd.DataFrame:
    """Uma coluna 0/1 por atributo; vazio onde o avaliador daquele campo não viu o post.
    Notas 0 a 10 ficam fora: são pouco confiáveis entre pessoas."""
    x = pd.DataFrame({b: df[b].map(_zero_um) for b in BOOLEANOS}, index=df.index)
    duracao = df["duracao_s"].map(faixa_duracao).rename("duracao_faixa")
    for coluna in [df[c] for c in CATEGORICOS] + [duracao]:
        vazio = coluna.isna()
        for valor in sorted(coluna.dropna().unique()):
            x[f"{coluna.name}={valor}"] = (coluna == valor).astype(float).mask(vazio)
    return x


def perfis_validos(df: pd.DataFrame) -> list[str]:
    n = df.groupby(["handle", "par_motor"]).size().unstack(fill_value=0)
    if not {"top", "resto"} <= set(n.columns):
        return []
    return sorted(n.index[(n["top"] >= MIN_POR_GRUPO) & (n["resto"] >= MIN_POR_GRUPO)])


def _diferencas(x: np.ndarray, top: np.ndarray) -> np.ndarray:
    return x[top].mean(axis=0) - x[~top].mean(axis=0)


def testar(df: pd.DataFrame, atributos: list[str] | None = None, semente=0) -> list[Teste]:
    """Um Teste por atributo. `df`: linhas com par_motor ('top' ou 'resto') e a rubrica aberta.

    Cada atributo é testado só nos posts em que o avaliador do seu campo respondeu: campos de
    quadros cobrem a amostra inteira, campos de fala cobrem só o que o Gemini assistiu."""
    df = df[df["par_motor"].notna()].reset_index(drop=True)
    x_todos = matriz(df)
    colunas = atributos or list(x_todos.columns)
    for c in [c for c in colunas if c not in x_todos.columns]:
        origem = c.split("=")[0]  # categoria sem ocorrência: 0 onde o campo foi avaliado
        visto = df[origem].notna() if origem in df else pd.Series(True, index=df.index)
        x_todos[c] = pd.Series(0.0, index=df.index).where(visto)
    familias: dict[bytes, list[str]] = {}
    for c in colunas:
        familias.setdefault(x_todos[c].notna().to_numpy().tobytes(), []).append(c)
    feitos: dict[str, Teste] = {}
    for nomes in familias.values():
        visto = x_todos[nomes[0]].notna().to_numpy()
        feitos |= {t.atributo: t for t in _testar(df[visto], x_todos.loc[visto, nomes], semente)}
    if not feitos:
        return []
    return [feitos.get(c) or _sem_dados(c) for c in colunas]


def _sem_dados(atributo: str) -> Teste:
    return Teste(
        atributo=atributo, efeito=0.0, ic95=(0.0, 0.0), p=1.0, prevalencia_top=0.0,
        prevalencia_resto=0.0, n_posts=0, n_perfis=0, ocorrencias=0,
    )  # fmt: skip


def _testar(df: pd.DataFrame, x_df: pd.DataFrame, semente: int) -> list[Teste]:
    perfis = perfis_validos(df)
    if not perfis:
        return []
    dentro = df["handle"].isin(perfis).to_numpy()
    df, colunas, x = df[dentro].reset_index(drop=True), list(x_df.columns), x_df[dentro].to_numpy()
    top = (df["par_motor"] == "top").to_numpy()
    grupos = [np.flatnonzero((df["handle"] == h).to_numpy()) for h in perfis]
    por_perfil = np.array([_diferencas(x[g], top[g]) for g in grupos])
    efeito = por_perfil.mean(axis=0)

    rng = np.random.default_rng(semente)
    maiores = np.zeros(len(colunas))
    for inicio in range(0, PERMUTACOES, 500):
        lote = min(500, PERMUTACOES - inicio)
        soma = np.zeros((lote, len(colunas)))
        for g in grupos:
            n_top, n = int(top[g].sum()), len(g)
            escolhidos = np.argsort(rng.random((lote, n)), axis=1)[:, :n_top]
            total, parte = x[g].sum(axis=0), x[g][escolhidos].sum(axis=1)
            soma += parte / n_top - (total - parte) / (n - n_top)
        maiores += (np.abs(soma / len(grupos)) >= np.abs(efeito) - 1e-12).sum(axis=0)
    p = (maiores + 1) / (PERMUTACOES + 1)

    sorteio = rng.integers(0, len(grupos), (2000, len(grupos)))
    medias = por_perfil[sorteio].mean(axis=1)
    baixo, alto = np.percentile(medias, [2.5, 97.5], axis=0)
    return [
        Teste(
            atributo=c,
            efeito=float(efeito[j]),
            ic95=(float(baixo[j]), float(alto[j])),
            p=float(p[j]),
            prevalencia_top=float(x[top, j].mean()),
            prevalencia_resto=float(x[~top, j].mean()),
            n_posts=len(df),
            n_perfis=len(perfis),
            ocorrencias=int(x[:, j].sum()),
        )
        for j, c in enumerate(colunas)
    ]


def julgar(teste: Teste, direcao: str) -> Veredito:
    sinal = 1 if direcao == "mais" else -1
    if teste.n_perfis < MIN_PERFIS or teste.ocorrencias < MIN_OCORRENCIAS:
        return "evidencia_insuficiente"
    if teste.p < ALFA and teste.efeito * sinal > 0:
        return "sustentada"
    melhor_caso = max(sinal * teste.ic95[0], sinal * teste.ic95[1])
    return "nao_sustentada" if melhor_caso < EFEITO_MINIMO else "evidencia_insuficiente"


def embaralhar(df: pd.DataFrame, semente: int) -> pd.DataFrame:
    """Rótulos top/resto sorteados dentro de cada perfil: não sobra nada real para achar."""
    rng = np.random.default_rng(semente)
    copia = df.copy()
    copia["par_motor"] = copia.groupby("handle")["par_motor"].transform(
        lambda s: rng.permutation(s.to_numpy())
    )
    return copia


def falsos_positivos(df: pd.DataFrame, rodadas: int = 20) -> float:
    """Fração de testes com p < ALFA nos rótulos embaralhados. O esperado é perto de ALFA."""
    achados = [
        t.p < ALFA
        for i in range(rodadas)
        for t in testar(embaralhar(df, i), semente=i)
        if t.ocorrencias >= MIN_OCORRENCIAS
    ]
    return float(np.mean(achados)) if achados else float("nan")
