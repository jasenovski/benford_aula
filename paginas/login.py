import bcrypt
import streamlit as st
from db.db import DATABASE

db: DATABASE = st.session_state["db"]

_, centro, _ = st.columns([1, 1.2, 1])

with centro:
    st.title("📊 Lei de Benford")
    st.caption("Análise dos gastos da cota parlamentar dos deputados federais")

    with st.form("form_login"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar", type="primary", width="stretch")

    if entrar:
        dados_usuario = db.buscar_usuario(usuario.strip())
        senha_correta = dados_usuario is not None and bcrypt.checkpw(
            senha.encode("utf-8"), 
            dados_usuario["senha_hash"].encode("utf-8")
        )

        if senha_correta:
            st.session_state["usuario"] = {
                "nome": dados_usuario["nome"],
                "usuario": dados_usuario["usuario"],
            }
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos.")
