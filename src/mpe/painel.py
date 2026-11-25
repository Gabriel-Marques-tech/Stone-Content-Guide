"""Dados da versão visual (página e plataforma). Todo número sai daqui, lido do banco.

Mostra só a metade 'explora' dos perfis. A metade 'confirma' aparece apenas dentro de hipóteses já
confirmadas, para a interface não quebrar a regra de travar as hipóteses antes do teste.
"""

import json
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from mpe import desfechos, hipoteses, motor
from mpe.ambiente import DADOS
from mpe.rubrica import CAMPOS_QUADROS, Rubrica

N_CALOR = 8  # atributos no mapa de calor
N_VITRINE = 12


def abrir_leitura():
    """Só leitura. Se a categorização estiver gravando, lê uma cópia do arquivo."""
    origem = DADOS / "mpe.duckdb"
    try:
        return duckdb.connect(str(origem), read_only=True)
    except duckdb.IOException:
        copia = Path(tempfile.mkdtemp()) / "mpe.duckdb"
        shutil.copy(origem, copia)
        return duckdb.connect(str(copia), read_only=True)


def tabelas(banco) -> set[str]:
    return {t for (t,) in banco.execute("SHOW TABLES").fetchall()}


def avaliador(atributo: str) -> str:
    campo = atributo.split("=")[0]
    if campo == "duracao_faixa":
        return "metadados"
    return "quadros" if campo in CAMPOS_QUADROS else "fala"


def teste(t: motor.Teste) -> dict:
    return {**t.model_dump(), "avaliador": avaliador(t.atributo)}


def calor(explora, atributos: list[str]) -> dict:
    """Diferença top − resto de cada perfil da metade 'explora', nos atributos escolhidos."""
    perfis = motor.perfis_validos(explora)
    x = motor.matriz(explora)
    linhas = []
    for h in perfis:
        do_perfil = explora["handle"] == h
        top = do_perfil & (explora["par_motor"] == "top")
        resto = do_perfil & (explora["par_motor"] == "resto")
        dif = x.loc[top, atributos].mean() - x.loc[resto, atributos].mean()
        linhas.append(
            {
                "handle": h,
                "canal": explora.loc[do_perfil, "canal"].iloc[0],
                "valores": [None if np.isnan(v) else round(float(v), 3) for v in dif],
            }
        )
    return {"atributos": atributos, "perfis": linhas}


def _texto(valor):
    return valor if isinstance(valor, str) else None


def cartao(r) -> dict:
    """Um post no formato curto usado em listas e vitrines."""
    return {
        "id": r.id,
        "titulo": r.titulo,
        "canal": r.canal,
        "handle": r.handle,
        "segmento": r.segmento,
        "inscritos": int(r.inscritos),
        "engajamento": float(r.engajamento),
        "posicao": int(r.posicao),
        "top": bool(r.top_tapi),
        "capa": r.thumbnail,
        "formato": _texto(r.formato_video),
        "tema": _texto(r.tema_principal),
        "duracao_s": int(r.duracao_s),
        "com_fala": bool(r.com_fala),
    }


def detalhe(df: pd.DataFrame, post_id: str) -> dict | None:
    """Um post com a rubrica inteira (só os campos que algum avaliador respondeu)."""
    linhas = df[df["id"] == post_id]
    if linhas.empty:
        return None
    r = linhas.iloc[0]
    rubrica = {}
    for campo in Rubrica.model_fields:
        valor = r.get(campo)
        if isinstance(valor, list | np.ndarray):
            rubrica[campo] = [str(v) for v in valor]
        elif valor is not None and not pd.isna(valor):
            rubrica[campo] = valor.item() if hasattr(valor, "item") else valor
    return {
        **cartao(r),
        "views": int(r["views"]),
        "likes": int(r["likes"]),
        "comentarios": int(r["comentarios"]),
        "publicado_em": str(r["publicado_em"])[:10],
        "par_motor": _texto(r["par_motor"]),
        "rubrica": rubrica,
        "de_quadros": [c for c in rubrica if c in CAMPOS_QUADROS],
    }


def execucoes(banco, limite: int = 30) -> list[dict]:
    if "execucoes" not in tabelas(banco):
        return []
    linhas = banco.execute(
        "SELECT run_id, quando, entrada, saida, etapas FROM execucoes ORDER BY quando DESC LIMIT ?",
        [limite],
    ).fetchall()
    return [
        {
            "run_id": i,
            "quando": q.replace(tzinfo=UTC).astimezone().strftime("%d/%m %H:%M"),
            "entrada": json.loads(e),
            "saida": json.loads(s),
            "etapas": json.loads(t),
        }
        for i, q, e, s, t in linhas
    ]


def criativos(feitas: list[dict], n: int = 6) -> list[dict]:
    saida = []
    for x in feitas:
        links = {r["post_id"]: r for r in x["saida"]["reference_posts"]}
        for c in x["saida"]["creatives"]:
            saida.append(
                {
                    **c,
                    "pedido": x["entrada"]["query"],
                    "sinal": x["saida"]["confidence_flag"],
                    "run_id": x["run_id"],
                    "refs": [
                        {"id": i, "canal": links[i]["canal"], "titulo": links[i]["titulo"]}
                        for i in c["referencias"]
                        if i in links
                    ],
                }
            )
    return saida[:n]


def montar(banco, df: pd.DataFrame, auditoria: bool = True) -> dict:
    explora = hipoteses.metade(df, "explora")
    testes = [
        t
        for t in hipoteses.explorar(df)
        if t.n_perfis >= motor.MIN_PERFIS and t.ocorrencias >= motor.MIN_OCORRENCIAS
    ]
    por_tamanho = sorted(testes, key=lambda t: -abs(t.efeito))

    topo = df[df["top_tapi"]]
    por_perfil = topo.groupby(["handle", "canal", "inscritos"]).size().sort_values(ascending=False)

    registradas = []
    if "hipoteses" in tabelas(banco):
        linhas = banco.execute("SELECT corpo FROM hipoteses ORDER BY id").fetchall()
        registradas = [json.loads(c) for (c,) in linhas]

    regras = {
        "vagas": motor.VAGAS,
        "alfa": motor.ALFA,
        "efeito_minimo": motor.EFEITO_MINIMO,
        "min_perfis": motor.MIN_PERFIS,
        "permutacoes": motor.PERMUTACOES,
        "perfis_explora": len(motor.perfis_validos(explora)),
        "perfis_confirma": len(motor.perfis_validos(hipoteses.metade(df, "confirma"))),
    }
    if auditoria:
        # Rótulos sorteados dentro de cada perfil: não revela nada da metade reservada.
        regras["falsos_positivos"] = motor.falsos_positivos(
            df[df["categorizado"] & df["par_motor"].notna()]
        )

    def valores(coluna):
        return sorted(v for v in df[coluna].dropna().unique() if isinstance(v, str))

    return {
        "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "base": {
            "posts": banco.execute("SELECT count(*) FROM posts").fetchone()[0],
            "com_metricas": len(df),
            "canais": int(df["handle"].nunique()),
            "top": int(df["top_tapi"].sum()),
            "quadros": int(df["categorizado"].sum()),
            "fala": int(df["com_fala"].sum()),
            "fila_fala": int((df["top_tapi"] | df["par_motor"].notna()).sum()),
            "segmentos": {k: int(v) for k, v in df.groupby("segmento").size().items()},
        },
        "opcoes": {
            "segmentos": valores("segmento"),
            "formatos": valores("formato_video"),
            "temas": valores("tema_principal"),
        },
        "concentracao": [
            {"handle": h, "canal": c, "inscritos": int(i), "no_top": int(n)}
            for (h, c, i), n in por_perfil.items()
        ],
        "regras": regras,
        "exploracao": [teste(t) for t in por_tamanho],
        "crencas": desfechos.consultar(df),
        "posts_explora": int((df["metade"] == "explora").sum()),
        "calor": calor(explora, [t.atributo for t in por_tamanho[:N_CALOR]]),
        "hipoteses": registradas,
        "vitrine": [cartao(r) for r in topo.sort_values("posicao").head(N_VITRINE).itertuples()],
        "criativos": criativos(execucoes(banco, 20)),
    }
