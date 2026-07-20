"""Gate de autenticacao por senha unica via st.secrets.

Para ativar a senha em producao (Streamlit Community Cloud):
  Settings -> Secrets, adicione:
    APP_PASSWORD = "alguma-senha-forte"

Sem `APP_PASSWORD` configurado, o gate libera acesso (uso local sem senha).
"""
from __future__ import annotations

import hmac
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent
_STYLES_PATH = _ROOT / "resources" / "static" / "styles.css"
_LOGO_PATH = _ROOT / "pmra-icon.svg"


@st.cache_data
def _read_css() -> str:
    return _STYLES_PATH.read_text(encoding="utf-8") if _STYLES_PATH.exists() else ""


@st.cache_data
def _read_logo() -> str:
    return _LOGO_PATH.read_text(encoding="utf-8") if _LOGO_PATH.exists() else ""


def _load_design_system() -> None:
    """Injeta o mesmo CSS do formulario na tela de login.

    auth.py executa antes de app.py injetar o style global, por isso o CSS
    precisa ser carregado aqui tambem para a tela ter a mesma identidade visual.
    Cache evita re-leitura do disco em cada rerun.
    """
    css = _read_css()
    if css:
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


_MAX_LOGIN_ATTEMPTS = 5

# Caminhos padrao onde o Streamlit procura secrets (local e Community Cloud).
_SECRETS_FILES = (
    Path.home() / ".streamlit" / "secrets.toml",
    _ROOT / ".streamlit" / "secrets.toml",
)


def _read_expected_password() -> str:
    """Le APP_PASSWORD sem disparar o banner "No secrets found" do Streamlit.

    Tocar em st.secrets sem nenhum secrets.toml faz o Streamlit renderizar
    um erro DENTRO do app com os caminhos internos do servidor (uso local
    sem senha). Checar a existencia dos arquivos antes evita o vazamento.
    """
    if not any(p.exists() for p in _SECRETS_FILES):
        return ""
    try:
        return st.secrets.get("APP_PASSWORD", "")
    except Exception:
        # st.secrets pode levantar em arquivo malformado — tratamos como sem senha.
        return ""


def check_password() -> bool:
    """Retorna True se o usuario esta autenticado (ou se nao ha senha configurada)."""
    expected = _read_expected_password()

    if not expected:
        return True

    if st.session_state.get("authenticated", False):
        return True

    _load_design_system()
    logo_svg = _read_logo()

    # HTML em uma linha por elemento (sem indentacao) para evitar que o parser
    # markdown do Streamlit interprete whitespace antes do texto como margem.
    # Usa <div> em vez de <h1>/<p> para evitar estilos default do Streamlit
    # em headings/paragrafos que podem aplicar padding/margin assimetrico.
    login_html = (
        '<div class="pmra-login">'
        f'<div class="pmra-login-logo">{logo_svg}</div>'
        '<div class="pmra-login-title">Gerador de Propostas PMRA</div>'
        '<div class="pmra-login-subtitle">Desenvolvido pelo Legal Tech PMRA</div>'
        '<div class="pmra-login-message">'
        'Acesso restrito. Informe a senha mestra para acesso ao app. '
        'Não compartilhe a senha com pessoas não autorizadas ou fora da organização.'
        '</div>'
        '</div>'
    )
    st.markdown(login_html, unsafe_allow_html=True)

    # Form centralizado abaixo do card de boas-vindas
    _, col, _ = st.columns([1, 2, 1])
    with col:
        attempts = st.session_state.get("login_attempts", 0)
        if attempts >= _MAX_LOGIN_ATTEMPTS:
            st.error("Número máximo de tentativas atingido. Recarregue a página para tentar novamente.")
            return False

        with st.form("login_form", clear_on_submit=False):
            pw = st.text_input("Senha", type="password", key="login_pw")
            submitted = st.form_submit_button(
                "Entrar", type="primary", use_container_width=True
            )
            if submitted:
                if hmac.compare_digest(pw, expected):
                    st.session_state["authenticated"] = True
                    st.session_state.pop("login_attempts", None)
                    st.rerun()
                else:
                    st.session_state["login_attempts"] = attempts + 1
                    st.error("Senha incorreta.")
    return False
