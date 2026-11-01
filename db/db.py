import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


def criar_engine():
    load_dotenv("db.env", override=True)
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
    )
    return create_engine(url, connect_args={"connect_timeout": 10})


class DATABASE:
    def __init__(self, engine):
        self.engine = engine

    def buscar_usuario(self, nome_usuario: str) -> dict | None:
        query = text("""
            SELECT nome, usuario, senha_hash, is_admin
            FROM tb_clientes
            WHERE usuario = :usuario
              AND is_active = TRUE
              AND deletado = FALSE
        """)
        with self.engine.connect() as connection:
            resultado = connection.execute(query, {"usuario": nome_usuario})
            linha = resultado.mappings().first()
        return dict(linha) if linha else None

    def deletar_usuario(self, nome_usuario: str) -> int:
        query = text("UPDATE tb_clientes SET deletado = TRUE WHERE usuario = :usuario")
        with self.engine.connect() as connection:
            resultado = connection.execute(query, {"usuario": nome_usuario})
            connection.commit()
        return resultado.rowcount

    def select_query(self, query: str) -> pd.DataFrame:
        # O SQL vem da IA: a transação somente leitura impede alterações no banco
        with self.engine.connect() as connection:
            with connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                connection.execute(text("SET LOCAL statement_timeout = '30s'"))
                return pd.read_sql(text(query), connection)

    def inserir_dados(self, df: pd.DataFrame, nome_tabela: str) -> None:
        with self.engine.connect() as connection:
            df.to_sql(nome_tabela, connection, if_exists="append", index=False)
            connection.commit()
