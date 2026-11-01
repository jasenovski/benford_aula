import os

import sqlparse
from dotenv import load_dotenv
from google import genai
from google.genai import types

MODELO = "gemini-3.5-flash"

# Configuração "deterministico" do notebook: melhor para SQL previsível
CONFIG_IA = {
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8196,
}

SCHEMA_TABELA_GASTOS = """
Tabela: tb_gastos_deputados (CEAP - Cota para Exercício da Atividade Parlamentar)

Colunas disponíveis:
- txnomeparlamentar (TEXT)    : Nome completo do deputado/parlamentar
- nulegislatura    (INTEGER)  : Ano da legislatura (ex: 2023, 2024)
- sguf             (TEXT)     : Sigla do estado (SP, RJ, MG, BA...)
- sgpartido        (TEXT)     : Sigla do partido (PT, PL, MDB, PSOL, PSDB...)
- codlegislatura   (INTEGER)  : Código da legislatura (ex: 57 = 57ª legislatura)
- txtdescricao     (TEXT)     : Categoria do gasto. Valores mais comuns:
    'COMBUSTÍVEIS E LUBRIFICANTES.',
    'MANUTENÇÃO DE ESCRITÓRIO DE APOIO À ATIVIDADE PARLAMENTAR',
    'PASSAGEM AÉREA - SIGEPA', 'PASSAGEM AÉREA - RPA',
    'TELEFONIA', 'SERVIÇOS POSTAIS',
    'DIVULGAÇÃO DA ATIVIDADE PARLAMENTAR.',
    'CONSULTORIA, PESQUISA E TRABALHOS TÉCNICOS.',
    'FORNECIMENTO DE ALIMENTAÇÃO DO PARLAMENTAR',
    'HOSPEDAGEM, EXCETO DO PARLAMENTAR NO DISTRITO FEDERAL.',
    'LOCAÇÃO OU FRETAMENTO DE AERONAVES',
    'LOCAÇÃO OU FRETAMENTO DE VEÍCULOS AUTOMOTORES'
- txtfornecedor    (TEXT)     : Nome do fornecedor/empresa
- vlrdocumento     (NUMERIC)  : Valor bruto do documento (valor do gasto)
- vlrliquido       (NUMERIC)  : Valor líquido do gasto
- nummes           (INTEGER)  : Mês do gasto (1-12)
- numano           (INTEGER)  : Ano do gasto (ex: 2023, 2024, 2025)
- urldocumento     (TEXT)     : URL para download do documento/nota fiscal em PDF (pode ser nulo)
"""

PROMPT_SISTEMA_GERAR_SQL = f"""
Você é um especialista em análise de dados de gastos de parlamentares
brasileiros e em SQL para PostgreSQL. Você vai precisar atuar na tabela
abaixo:

{SCHEMA_TABELA_GASTOS}

Sua tarefa é interpretar perguntas em linguagem natural e gerar uma
query SQL completa e pronta para execução, chamando a função 
'consultar_gastos_deputados' com o parâmetro 'sql'.

Diretrizes para geração do SQL:
1. Gere sempre uma query PostgreSQL válida e completa.
2. Use WITH (CTE) quando precisar de múltiplos estágios.
3. Use ILIKE %valor% para buscas parciais de texto (case-insensitive)
4. Use IN (...) para filtrar múltiplos valores de uma mesma coluna
5. Use SUM, AVG, COUNT conforme a pergunta exigir.
6. O resultado final deve estar ordenado de forma relevante para visualização.
7. Use LIMIT apenas quando o usuário pedir explicitamente um top-N.
8. Retorne apenas as colunas necessárias para o gráfico.
9. Os filtros, agrupamentos e contagens devem estar no SQL. A comparação com
   Benford e a geração dos gráficos serão feitas em Python.
10. Quando a pergunta solicitar gráficos SEPARADOS por entidade (ex: um gráfico por
    deputado, um gráfico por partido), inclua obrigatoriamente a coluna identificadora
    (ex: txnomeparlamentar, sgpartido) no SELECT e no GROUP BY, para que cada gráfico
    possa filtrar apenas seus próprios dados.

A tabela resultante necessariamente deve ter as colunas 
'primeiro_digito' (inteiro de 1 a 9), 
'total_ocorrencias' (contagem por dígito) e 
'percentual_observado' (percentual de 0 a 100, dentro de cada grupo).

Além das colunas de agregação/filtragem conforme solicitado pelo usuário.
"""

FORMATO_RESPOSTA_GERAR_SQL = types.Schema(
    type=types.Type.STRING,
    description="Query SQL completa e válida no formato PostgreSQL "
    "gerada a partir do prompt.",
)


def criar_cliente() -> genai.Client:
    load_dotenv("ai.env", override=True)
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def gerar_sql(
    cliente: genai.Client,
    prompt_usuario: str,
    modelo: str = MODELO,
    configuracao: dict[str, float | int] | None = None,
) -> str:
    response = cliente.models.generate_content(
        model=modelo,
        contents=[prompt_usuario],
        config=types.GenerateContentConfig(
            system_instruction=PROMPT_SISTEMA_GERAR_SQL,
            response_mime_type="application/json",
            response_schema=FORMATO_RESPOSTA_GERAR_SQL,
            **(CONFIG_IA if configuracao is None else configuracao),
        ),
    )
    sql = response.parsed
    comandos = sqlparse.parse(sql or "")
    if len(comandos) != 1 or comandos[0].get_type() != "SELECT":
        raise ValueError("A IA não retornou uma consulta SELECT válida.")
    return sqlparse.format(sql, reindent=True, keyword_case="upper",
                           indent_width=4, strip_whitespace=True)
