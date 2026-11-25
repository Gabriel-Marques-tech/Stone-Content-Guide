"""Contrato da ferramenta (TAPI, seção 7). Entradas e saídas validadas com Pydantic."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from mpe.motor import Veredito

Segmento = Literal["geral", "alimentacao", "varejo", "beleza"]
Objetivo = Literal["engajamento", "contato"]
TamanhoPerfil = Literal["pequeno", "medio", "grande"]


class Filtros(BaseModel):
    plataforma: Literal["youtube_shorts"] = "youtube_shorts"
    desde: date | None = None
    ate: date | None = None
    tamanho_perfil: TamanhoPerfil | None = None


class Entrada(BaseModel):
    mode: Literal["analisar", "recomendar", "gerar_criativo"]
    query: str = Field(min_length=3, max_length=500)
    segment: Segmento | None = None
    objetivo: Objetivo = "engajamento"
    filters: Filtros = Filtros()


class Achado(BaseModel):
    atributo: str
    frequencia_top: float = Field(description="fração dos posts de alto desempenho com o atributo")
    n_top: int = Field(description="posts de alto desempenho categorizados no recorte")
    n_ocorrencias: int
    status: Veredito | Literal["nao_testada"] = "nao_testada"


class Referencia(BaseModel):
    post_id: str
    link: str
    titulo: str
    canal: str
    inscritos: int
    engajamento: float = Field(description="(curtidas + comentários) ÷ seguidores")
    posicao: int
    pedidos: int = Field(default=0, description="comentários pedindo contato")
    categorias: dict


class Padrao(BaseModel):
    """Padrão firme do objetivo: a diferença se mantém com peso igual por canal. Sai da base."""

    atributo: str
    conselho: str
    no_grupo: float = Field(description="fração no grupo do objetivo, com peso igual por canal")
    nos_outros: float
    n: int
    n_outros: int
    leitura: str
    tendencia: str = Field(default="sem_sinal", description="do radar; indício não é regra")


class Cena(BaseModel):
    inicio_s: int = Field(ge=0, le=180)
    fim_s: int = Field(ge=1, le=180)
    na_tela: str = Field(description="texto que o público lê na tela, de 2 a 6 palavras")
    cena: str = Field(description="o que se vê e o que se fala, em até 20 palavras, sem rótulo")


class Criativo(BaseModel):
    gancho: str
    roteiro: str = Field(description="uma linha com a ideia do vídeo")
    cenas: list[Cena] = []
    legenda: str
    chamada_para_acao: str
    referencias: list[str] = Field(min_length=1, description="post_ids que inspiraram o criativo")
    padroes: list[str] = Field(
        default=[], description="atributos dos padrões firmes que o roteiro aplica de fato"
    )


class Saida(BaseModel):
    findings: list[Achado]
    reference_posts: list[Referencia]
    creatives: list[Criativo] = []
    confidence_flag: Literal["ok", "poucos_posts", "sem_dados"]
    explanation: str
    patterns: list[Padrao] = []
    scope: str = Field(default="", description="de quantos posts saíram as frequências")
    lessons: list[str] = Field(default=[], description="erros repetidos lembrados neste pedido")
    trends: list[str] = Field(default=[], description="o que o radar marcou, dito ao agente")
    revisions: int = Field(default=0, description="criativos que melhoraram na revisão")
    run_id: str = ""
