"""Banco DuckDB do projeto: um arquivo, um processo por vez."""

import duckdb

from mpe.ambiente import DADOS

ESQUEMA = """
CREATE TABLE IF NOT EXISTS canais (
    id VARCHAR PRIMARY KEY, handle VARCHAR, titulo VARCHAR, descricao VARCHAR, inscritos BIGINT,
    perfil VARCHAR, segmento VARCHAR, coletado_em TIMESTAMP
);
CREATE TABLE IF NOT EXISTS posts (
    id VARCHAR PRIMARY KEY, canal_id VARCHAR, titulo VARCHAR, descricao VARCHAR, tags JSON,
    idioma VARCHAR, thumbnail VARCHAR, publicado_em TIMESTAMP, duracao_s INTEGER, views BIGINT,
    likes BIGINT, comentarios BIGINT, coletado_em TIMESTAMP
);
CREATE TABLE IF NOT EXISTS categorias (
    post_id VARCHAR PRIMARY KEY, modelo VARCHAR, rubrica JSON, criado_em TIMESTAMP
);
CREATE TABLE IF NOT EXISTS categorias_quadros (
    post_id VARCHAR PRIMARY KEY, modelo VARCHAR, rubrica JSON, criado_em TIMESTAMP
);
CREATE TABLE IF NOT EXISTS categorias_transcricao (
    post_id VARCHAR PRIMARY KEY, modelo VARCHAR, rubrica JSON, criado_em TIMESTAMP
);
CREATE TABLE IF NOT EXISTS comentarios (
    comentario_id VARCHAR PRIMARY KEY, post_id VARCHAR, texto VARCHAR, likes BIGINT, classe VARCHAR
);
CREATE TABLE IF NOT EXISTS falhas (post_id VARCHAR, erro VARCHAR, quando TIMESTAMP);
"""


def abrir(caminho=None) -> duckdb.DuckDBPyConnection:
    DADOS.mkdir(exist_ok=True)
    banco = duckdb.connect(str(caminho or DADOS / "mpe.duckdb"))
    banco.execute(ESQUEMA)
    return banco
