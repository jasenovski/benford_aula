import matplotlib.pyplot as plt
import streamlit as st
from db.db import DATABASE
from funcoes.benford import calcular_benford, plotar_benford, qui_quadrado
from funcoes.ia import CONFIG_IA, MODELO, criar_cliente, gerar_sql


@st.cache_resource
def conectar_ia():
    return criar_cliente()


db: DATABASE = st.session_state["db"]

st.title("Análise de Benford")
st.caption("Descreva quais gastos dos deputados você quer comparar com a Lei de Benford.")

with st.sidebar:
    with st.expander("Parâmetros da IA"):
        modelos_disponiveis = [MODELO, "gemini-2.5-flash", "gemini-2.5-pro"]
        modelo = st.selectbox(
            "Modelo",
            options=modelos_disponiveis,
            index=modelos_disponiveis.index(MODELO),
        )
        configuracao_ia = {
            "temperature": st.slider(
                "Temperature",
                min_value=0.0,
                max_value=2.0,
                value=float(CONFIG_IA["temperature"]),
                step=0.1,
            ),
            "top_p": st.slider(
                "Top-p",
                min_value=0.0,
                max_value=1.0,
                value=float(CONFIG_IA["top_p"]),
                step=0.05,
            ),
            "top_k": st.number_input(
                "Top-k",
                min_value=1,
                value=int(CONFIG_IA["top_k"]),
                step=1,
            ),
            "max_output_tokens": st.number_input(
                "Máximo de tokens de saída",
                min_value=1,
                value=int(CONFIG_IA["max_output_tokens"]),
                step=1,
            ),
        }

with st.form("form_prompt"):
    prompt_usuario = st.text_area(
        "O que você quer analisar?",
        placeholder="Ex.: Quero ver a análise de Benford dos gastos de 2025 do PL e do PT, "
        "com um gráfico para cada partido.",
        height=100,
    )
    analisar = st.form_submit_button("Analisar", 
                                     type="primary", 
                                     icon=":material/search:")

if analisar and not prompt_usuario.strip():
    st.warning("Digite o que você quer analisar.")

elif analisar:
    try:
        with st.spinner("Gerando a consulta e calculando os resultados..."):
            sql = gerar_sql(
                conectar_ia(),
                prompt_usuario,
                modelo=modelo,
                configuracao=configuracao_ia,
            )
            df_dados = db.select_query(sql)
            df_benford = calcular_benford(df_dados)
            df_resumo = qui_quadrado(df_benford)
            figuras = plotar_benford(df_benford)
    except Exception as erro:
        st.error(f"Não foi possível fazer a análise: {erro}")
        st.stop()

    st.subheader("Resumo do teste qui-quadrado")
    st.caption("Se o QQ for maior que o valor crítico (15,507), os dados não seguem a Lei de Benford.")
    st.dataframe(df_resumo.round(2), hide_index=True)

    aba_graficos, aba_tabela, aba_dados, aba_sql = st.tabs(
        ["Gráficos", "Tabela de Benford", "Dados da consulta", "SQL gerado"]
    )

    with aba_graficos:
        colunas = st.columns(2)
        for i, figura in enumerate(figuras):
            with colunas[i % 2]:
                st.pyplot(figura)
            plt.close(figura)

    with aba_tabela:
        st.dataframe(df_benford.round(2), hide_index=True)

    with aba_dados:
        st.dataframe(df_dados, hide_index=True)

    with aba_sql:
        st.code(sql, language="sql")
