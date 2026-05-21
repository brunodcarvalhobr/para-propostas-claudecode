"""Gate de autenticacao por senha unica via st.secrets.

Para ativar a senha em producao (Streamlit Community Cloud):
  Settings -> Secrets, adicione:
    APP_PASSWORD = "alguma-senha-forte"

Sem `APP_PASSWORD` configurado, o gate libera acesso (uso local sem senha).
"""
from __future__ import annotations

import hmac

import streamlit as st

_MAX_LOGIN_ATTEMPTS = 5


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

    st.title("DocGen by PMRA Legal Tech")
    st.caption("Acesso restrito. Informe a senha compartilhada da equipe.")

    attempts = st.session_state.get("login_attempts", 0)
    if attempts >= _MAX_LOGIN_ATTEMPTS:
        st.error("Número máximo de tentativas atingido. Recarregue a página para tentar novamente.")
        return False

    with st.form("login_form", clear_on_submit=False):
        pw = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")
        if submitted:
            if hmac.compare_digest(pw, expected):
                st.session_state["authenticated"] = True
                st.session_state.pop("login_attempts", None)
                st.rerun()
            else:
                st.session_state["login_attempts"] = attempts + 1
                st.error("Senha incorreta.")
    return False
