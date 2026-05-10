"""Gate de autenticacao por senha unica via st.secrets.

Para ativar a senha em producao (Streamlit Community Cloud):
  Settings -> Secrets, adicione:
    APP_PASSWORD = "alguma-senha-forte"

Sem `APP_PASSWORD` configurado, o gate libera acesso (uso local sem senha).
"""
from __future__ import annotations

import streamlit as st


def check_password() -> bool:
    """Retorna True se o usuario esta autenticado (ou se nao ha senha configurada)."""
    expected = ""
    try:
        expected = st.secrets.get("APP_PASSWORD", "")
    except Exception:
        # st.secrets pode levantar se nao houver arquivo de secrets — tratamos como sem senha.
        expected = ""

    if not expected:
        return True

    if st.session_state.get("authenticated", False):
        return True

    st.title("PMRA — Gerador de Propostas")
    st.caption("Acesso restrito. Informe a senha compartilhada da equipe.")

    with st.form("login_form", clear_on_submit=False):
        pw = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")
        if submitted:
            if pw == expected:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Senha incorreta.")
    return False
