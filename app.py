import streamlit as st

from db.db import DATABASE, criar_engine

st.set_page_config(page_title="Benford | Gastos dos Deputados", 
                   page_icon="📊", 
                   layout="wide")


@st.cache_resource
def conectar_banco() -> DATABASE:
    return DATABASE(criar_engine())


st.session_state["db"] = conectar_banco()
st.session_state.setdefault("usuario", None)

pagina_login = st.Page("paginas/login.py", 
                       title="Login", 
                       icon=":material/login:")

pagina_analise = st.Page("paginas/analise.py", 
                         title="Análise de Benford", 
                         icon=":material/bar_chart:")

if st.session_state["usuario"] is None:
    pagina = st.navigation([pagina_login], 
                           position="hidden")
else:
    with st.sidebar:
        st.write(f"Olá, **{st.session_state['usuario']['nome']}**")

        if st.button("Sair", 
                     icon=":material/logout:", 
                     width="stretch"):
            
            st.session_state["usuario"] = None
            st.rerun()

    pagina = st.navigation([pagina_analise])

pagina.run()
