import matplotlib

matplotlib.use("Agg")  # backend sem janela, necessário no Streamlit

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
from matplotlib.figure import Figure


def benford_esperado() -> pd.Series:
    probs = {d: np.log10(1 + 1 / d) for d in range(1, 10)}
    return pd.Series(probs, name="Benford Esperado")


def calcular_resultados(contagem: pd.Series, 
                    esperado: pd.Series) -> pd.DataFrame:
    n = contagem.sum()
    freq_obs = contagem / n if n else contagem * 0.0

    df = pd.DataFrame(
        {
            "Benford (%)": esperado * 100,
            "Observado (%)": freq_obs * 100,
            "Diferença (%)": (freq_obs - esperado) * 100,
            "Observado": contagem,
            "Esperado": esperado * n,
        }
    )
    df["Diferença"] = df["Esperado"] - df["Observado"]
    df["QQ"] = df["Diferença"] ** 2 / df["Esperado"]
    df.index.name = "primeiro_digito"
    return df


def calcular_benford(
    df: pd.DataFrame,
    col_digito: str = "primeiro_digito",
    col_total: str = "total_ocorrencias",
) -> pd.DataFrame:
    """Calcula os valores de Benford a partir do resultado da consulta SQL.

    O DataFrame deve conter a coluna do primeiro dígito e a coluna com a
    contagem de ocorrências (`total_ocorrencias`). Quando a consulta traz um
    identificador de entidade (ex.: `sgpartido`), a análise é feita
    separadamente para cada valor. Se `colunas_grupo` não for informado, são
    consideradas identificadoras todas as colunas que não são o dígito, o total
    nem `percentual_observado`.

    Retorna uma linha por (grupo, dígito de 1 a 9) com as colunas: Benford (%),
    Observado (%), Diferença (%), Observado, Esperado, Diferença e QQ
    (contribuição de cada dígito para o qui-quadrado).
    """

    ignoradas = {col_digito, col_total, "percentual_observado"}
    colunas_grupo = [c for c in df.columns if c not in ignoradas]

    esperado = benford_esperado()

    if not colunas_grupo:
        contagem = (
            df.groupby(col_digito)[col_total].sum().reindex(range(1, 10), fill_value=0)
        )
        return calcular_resultados(contagem, esperado).reset_index()

    resultados = []
    for agrupamento, df_grupo in df.groupby(colunas_grupo, sort=True, dropna=False):
        agrupamento = agrupamento if isinstance(agrupamento, tuple) else (agrupamento,)
        contagem = (
            df_grupo.groupby(col_digito)[col_total].sum().reindex(range(1, 10), fill_value=0)
        )
        resultado = calcular_resultados(contagem, esperado).reset_index()

        for col, valor in reversed(list(zip(colunas_grupo, agrupamento))):
            resultado.insert(0, col, valor)
        resultados.append(resultado)

    return pd.concat(resultados, ignore_index=True)


def qui_quadrado(
    df_benford: pd.DataFrame, 
    colunas_grupo: list[str] | None = None
) -> pd.DataFrame:
    """Soma o QQ por grupo e indica se excede o valor crítico%."""
    if colunas_grupo is None:
        colunas_grupo = \
        [
            c for c in df_benford.columns if c not in {
                "primeiro_digito",
                "total_ocorrencias",
                "percentual_observado",
                "Benford (%)",
                "Observado (%)",
                "Diferença (%)",
                "Observado",
                "Esperado",
                "Diferença",
                "QQ",
            }
        ]

    if colunas_grupo:
        total = df_benford.groupby(colunas_grupo, dropna=False).agg(
            N=("Observado", "sum"), QQ=("QQ", "sum")
        )
    else:
        total = pd.DataFrame(
            {"N": [df_benford["Observado"].sum()], 
             "QQ": [df_benford["QQ"].sum()]}
        )
    total["Crítico"] = 15.507
    total["Rejeita Benford"] = total["QQ"] > 15.507
    return total.reset_index() if colunas_grupo else total


def plotar_benford(df_benford: pd.DataFrame) -> list[Figure]:
    """Exibe esperado e observado em barras, um gráfico por grupo.

    Recebe o DataFrame retornado por calcular_benford e devolve as figuras
    para permitir salvar os gráficos com fig.savefig(...).
    """
    colunas_resultado = {
        "primeiro_digito", "Benford (%)", "Observado (%)", "Diferença (%)",
        "Observado", "Esperado", "Diferença", "QQ",
    }
    faltantes = colunas_resultado.difference(df_benford.columns)
    if faltantes:
        raise ValueError(f"Colunas ausentes no resultado de Benford: {sorted(faltantes)}")
    if df_benford.empty:
        raise ValueError("O resultado de Benford está vazio; não há dados para o gráfico.")

    colunas_grupo = [c for c in df_benford.columns if c not in colunas_resultado]
    grupos = (
        df_benford.groupby(colunas_grupo, sort=True, dropna=False)
        if colunas_grupo else [((), df_benford)]
    )
    figuras = []
    x = np.array(range(1, 10))
    largura = 0.38

    for chave, grupo in grupos:
        chave = chave if isinstance(chave, tuple) else (chave,)
        grupo = grupo.sort_values("primeiro_digito")
        if grupo["primeiro_digito"].tolist() != list(range(1, 10)):
            raise ValueError("Cada grupo deve conter exatamente uma linha por dígito de 1 a 9.")
        percentuais = grupo[["Benford (%)", "Observado (%)"]]
        if not np.isfinite(percentuais.to_numpy()).all() or not percentuais.ge(0).all().all():
            raise ValueError("As frequências devem ser percentuais finitos e não negativos.")
        n = grupo["Observado"].sum()
        if not np.isfinite(n) or n <= 0:
            raise ValueError("Cada grupo deve ter ao menos uma ocorrência observada.")

        fig, eixo = plt.subplots(figsize=(10, 6))
        barras_esp = eixo.bar(
            x - largura / 2, grupo["Benford (%)"].to_numpy(), largura,
            label="Esperado (Benford)", color="steelblue", alpha=0.85, zorder=3,
        )
        barras_obs = eixo.bar(
            x + largura / 2, grupo["Observado (%)"].to_numpy(), largura,
            label="Observado", color="coral", alpha=0.85, zorder=3,
        )
        for barras, cor in [(barras_esp, "steelblue"), (barras_obs, "coral")]:
            eixo.bar_label(
                barras, labels=[f"{barra.get_height():.1f}%" for barra in barras],
                padding=3, fontsize=8, color=cor,
            )

        entidade = ", ".join(f"{col} = {valor}" for col, valor in zip(colunas_grupo, chave))
        subtitulo = f"{entidade} | N = {n:,.0f}" if entidade else f"N = {n:,.0f}"
        eixo.set_title(
            f"Lei de Benford: Frequência Esperada vs. Observada\n{subtitulo}",
            fontsize=13, fontweight="bold",
        )
        eixo.set_xlabel("Primeiro Dígito", fontsize=12)
        eixo.set_ylabel("Frequência", fontsize=12)
        eixo.set_xticks(x)
        eixo.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=100))
        eixo.legend(fontsize=11)
        eixo.grid(axis="y", alpha=0.3, zorder=0)
        eixo.set_ylim(0, percentuais.max().max() * 1.2)
        fig.tight_layout()
        figuras.append(fig)

    return figuras
