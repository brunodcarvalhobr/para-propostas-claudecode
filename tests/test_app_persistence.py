"""Regressão: persistência dos campos ao navegar entre etapas (via AppTest).

Bug: ao digitar um campo e clicar "Próximo" no mesmo rerun, o corpo da etapa
anterior não re-renderiza, o valor não chega ao `form` e o Streamlit descarta a
chave do widget — ao voltar, o campo aparecia vazio. Corrigido por (a) reatribuir
as chaves de input a si mesmas a cada rerun (impede o descarte) e (b) `_apply_formats`
ler a chave do widget (não o `form` defasado).
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = Path(__file__).resolve().parent.parent / "app.py"


def _fresh() -> "AppTest":
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    return at


def test_campo_texto_persiste_digitar_e_avancar():
    """Cenário do bug: digitar + Próximo no MESMO rerun, depois voltar."""
    at = _fresh()
    at.text_input(key="razao_social_input").set_value("ACME PERSISTE SA")
    at.button(key="nav_next").click()
    at.run()  # processa o texto + o clique juntos
    at.button(key="nav_prev").click().run()
    assert at.text_input(key="razao_social_input").value == "ACME PERSISTE SA"
    assert at.session_state.form["contratante"]["razao_social"] == "ACME PERSISTE SA"


def test_campo_mascarado_persiste_ao_navegar():
    """CNPJ (campo só-key + máscara) sai pela _apply_formats — deve persistir formatado."""
    at = _fresh()
    at.text_input(key="cnpj_input").set_value("11222333000181")
    at.button(key="nav_next").click()
    at.run()
    at.button(key="nav_prev").click().run()
    assert at.text_input(key="cnpj_input").value == "11.222.333/0001-81"


def test_cnpj_alfanumerico_mesma_mascara():
    """CNPJ alfanumérico (IN RFB 2.229/2024): letras nas 12 primeiras posições,
    DVs numéricos, mesma máscara, maiúsculas normalizadas."""
    at = _fresh()
    at.text_input(key="cnpj_input").set_value("12abc34501de35")
    at.button(key="nav_next").click()
    at.run()
    at.button(key="nav_prev").click().run()
    assert at.text_input(key="cnpj_input").value == "12.ABC.345/01DE-35"


def test_textarea_escopo_persiste_via_stepper():
    at = _fresh()
    at.button(key="step_btn_1").click().run()
    at.text_area(key="atuacao_consultiva_ta").set_value("Consultoria persistente.")
    at.button(key="step_btn_2").click()
    at.run()
    at.button(key="step_btn_1").click().run()
    assert at.text_area(key="atuacao_consultiva_ta").value == "Consultoria persistente."


def test_honorario_modalidade_e_valor_persistem():
    at = _fresh()
    at.button(key="step_btn_2").click().run()
    at.checkbox(key="cons_hf").set_value(True).run()
    at.text_input(key="cons_hf_valor").set_value("700")
    at.button(key="step_btn_3").click()
    at.run()
    at.button(key="step_btn_2").click().run()
    assert at.checkbox(key="cons_hf").value is True
    assert at.text_input(key="cons_hf_valor").value == "R$ 700,00"
