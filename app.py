"""PMRA — Gerador de Propostas (Streamlit).

Form unico em pagina, com secoes em st.expander. Estado persistente em
st.session_state. Ao clicar em "Gerar proposta", o form e validado via
Pydantic, mapeado para o contexto do template e renderizado com docxtpl.
"""
from __future__ import annotations

import traceback
from datetime import datetime

import pandas as pd
import streamlit as st

from pmra.auth import check_password
from pmra.data_mapper import form_to_context
from pmra.defaults import proposal_form_default
from pmra.schema import ProposalForm, UF_OPTIONS
from pmra.template_engine import render_proposal


st.set_page_config(
    page_title="PMRA — Gerador de Propostas",
    page_icon="⚖️",
    layout="wide",
)

if not check_password():
    st.stop()


# ---------- estado ----------
if "form" not in st.session_state:
    st.session_state.form = proposal_form_default().model_dump()
if "generated_doc" not in st.session_state:
    st.session_state.generated_doc = None

form = st.session_state.form


# ---------- helpers ----------
def _df_to_records(df: pd.DataFrame, fallback: list[dict]) -> list[dict]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return fallback
    return df.fillna("").astype(str).to_dict("records")


# ---------- UI ----------
st.title("PMRA — Gerador de Propostas")
st.caption(
    "Preencha o formulário e clique em **Gerar proposta** ao final. "
    "O .docx ficará disponível para download. Campos vazios podem aparecer "
    "como placeholders no documento — revise antes de enviar."
)

# === 1. CONTRATANTE ===
with st.expander("1. Identificação do contratante", expanded=True):
    form["contratante"]["tipo_pessoa"] = st.radio(
        "Tipo de pessoa",
        options=("fisica", "juridica"),
        format_func=lambda x: "Pessoa Física" if x == "fisica" else "Pessoa Jurídica",
        index=0 if form["contratante"]["tipo_pessoa"] == "fisica" else 1,
        horizontal=True,
        key="tipo_pessoa",
    )

    if form["contratante"]["tipo_pessoa"] == "fisica":
        c1, c2 = st.columns([2, 1])
        form["contratante"]["nome"] = c1.text_input("Nome", value=form["contratante"]["nome"])
        form["contratante"]["cpf"] = c2.text_input("CPF", value=form["contratante"]["cpf"])
    else:
        c1, c2 = st.columns([2, 1])
        form["contratante"]["razao_social"] = c1.text_input(
            "Razão Social", value=form["contratante"]["razao_social"]
        )
        form["contratante"]["cnpj"] = c2.text_input("CNPJ", value=form["contratante"]["cnpj"])

    st.markdown("**Endereço**")
    end = form["contratante"]["endereco"]
    c1, c2 = st.columns([3, 1])
    end["logradouro"] = c1.text_input("Logradouro", value=end["logradouro"])
    end["numero"] = c2.text_input("Número", value=end["numero"])
    c1, c2 = st.columns([2, 1])
    end["bairro"] = c1.text_input("Bairro", value=end["bairro"])
    end["cep"] = c2.text_input("CEP", value=end["cep"])
    c1, c2 = st.columns([3, 1])
    end["cidade"] = c1.text_input("Cidade", value=end["cidade"])
    end["uf"] = c2.selectbox(
        "UF",
        options=UF_OPTIONS,
        index=UF_OPTIONS.index(end["uf"]) if end["uf"] in UF_OPTIONS else 0,
    )

    st.markdown("**Responsável e contatos**")
    form["contratante"]["contato_nome"] = st.text_input(
        "Nome do responsável", value=form["contratante"]["contato_nome"]
    )

    contatos_initial = form["contratante"]["contatos"] or [{"telefone": "", "email": ""}]
    contatos_df = pd.DataFrame(contatos_initial)
    edited_contatos = st.data_editor(
        contatos_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "telefone": st.column_config.TextColumn("Telefone"),
            "email": st.column_config.TextColumn("E-mail"),
        },
        key="contatos_editor",
    )
    form["contratante"]["contatos"] = _df_to_records(
        edited_contatos, [{"telefone": "", "email": ""}]
    )

# === 2. ESCOPO ===
with st.expander("2. Escopo da contratação", expanded=True):
    modalidades = ("consultiva", "contenciosa", "mista")
    form["escopo"]["modalidade"] = st.radio(
        "Modalidade",
        options=modalidades,
        format_func=str.capitalize,
        index=modalidades.index(form["escopo"]["modalidade"]),
        horizontal=True,
        key="modalidade",
    )

    show_consultiva = form["escopo"]["modalidade"] in ("consultiva", "mista")
    show_contenciosa = form["escopo"]["modalidade"] in ("contenciosa", "mista")

    if show_consultiva:
        form["escopo"]["atuacao_consultiva"] = st.text_area(
            "Atuação consultiva — áreas, matérias e entregáveis",
            value=form["escopo"]["atuacao_consultiva"],
            height=120,
        )
    if show_contenciosa:
        form["escopo"]["atuacao_contenciosa"] = st.text_area(
            "Atuação contenciosa — matérias, foros, instâncias e atos processuais",
            value=form["escopo"]["atuacao_contenciosa"],
            height=120,
        )

    form["escopo"]["sla_ativo"] = st.checkbox(
        "Definir SLA por complexidade?", value=form["escopo"]["sla_ativo"]
    )
    if form["escopo"]["sla_ativo"]:
        form["escopo"]["sla_descricao"] = st.text_area(
            "SLA — descrição por complexidade (Baixa, Média, Alta)",
            value=form["escopo"]["sla_descricao"],
            height=100,
        )

# === 3. HONORÁRIOS CONSULTIVOS ===
if show_consultiva:
    with st.expander("3. Honorários — Atuação Consultiva", expanded=False):
        cm = form["honorarios_consultiva"]["modalidades"]
        st.markdown("**Modalidades aplicáveis** (marque uma ou mais)")
        c1, c2, c3, c4 = st.columns(4)
        cm["hora_senioridade"] = c1.checkbox(
            "Hora por senioridade", value=cm["hora_senioridade"], key="cons_hs"
        )
        cm["hora_fixa"] = c2.checkbox("Hora fixa", value=cm["hora_fixa"], key="cons_hf")
        cm["fixo_mensal"] = c3.checkbox(
            "Fixo mensal", value=cm["fixo_mensal"], key="cons_fm"
        )
        cm["valor_projeto"] = c4.checkbox(
            "Valor do projeto", value=cm["valor_projeto"], key="cons_vp"
        )

        if cm["hora_senioridade"]:
            st.markdown("**Tabela por senioridade — consultiva**")
            sen_df = pd.DataFrame(form["honorarios_consultiva"]["tabela_senioridade"])
            edited_sen = st.data_editor(
                sen_df,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "categoria": st.column_config.TextColumn("Categoria"),
                    "valor": st.column_config.TextColumn("Valor por hora"),
                },
                key="sen_consultiva",
            )
            form["honorarios_consultiva"]["tabela_senioridade"] = _df_to_records(
                edited_sen, []
            )

        if cm["hora_fixa"]:
            form["honorarios_consultiva"]["hora_fixa_valor"] = st.text_input(
                "Valor por hora (independente do executor) — consultiva",
                value=form["honorarios_consultiva"]["hora_fixa_valor"],
                key="cons_hf_valor",
            )

        if cm["fixo_mensal"]:
            c1, c2, c3 = st.columns(3)
            form["honorarios_consultiva"]["fixo_mensal_valor"] = c1.text_input(
                "Valor mensal", value=form["honorarios_consultiva"]["fixo_mensal_valor"]
            )
            form["honorarios_consultiva"]["fixo_mensal_cap"] = c2.text_input(
                "Cap de horas", value=form["honorarios_consultiva"]["fixo_mensal_cap"]
            )
            form["honorarios_consultiva"]["fixo_mensal_excedente"] = c3.text_input(
                "Valor da hora excedente",
                value=form["honorarios_consultiva"]["fixo_mensal_excedente"],
            )

        if cm["valor_projeto"]:
            form["honorarios_consultiva"]["valor_projeto_total"] = st.text_input(
                "Valor total do projeto — consultivo",
                value=form["honorarios_consultiva"]["valor_projeto_total"],
                key="cons_vp_total",
            )
            form["honorarios_consultiva"]["valor_projeto_forma_pagamento"] = st.text_area(
                "Forma de pagamento — consultivo",
                value=form["honorarios_consultiva"]["valor_projeto_forma_pagamento"],
                height=80,
                key="cons_vp_forma",
            )

# === 4. HONORÁRIOS CONTENCIOSOS ===
if show_contenciosa:
    with st.expander("4. Honorários — Atuação Contenciosa", expanded=False):
        cm = form["honorarios_contenciosa"]["modalidades"]
        st.markdown("**Modalidades aplicáveis** (marque uma ou mais)")
        c1, c2, c3, c4 = st.columns(4)
        cm["valor_acao"] = c1.checkbox(
            "Valor por ação", value=cm["valor_acao"], key="cont_va"
        )
        cm["valor_ato_processual"] = c2.checkbox(
            "Valor por ato processual", value=cm["valor_ato_processual"], key="cont_vap"
        )
        cm["preco_mensal_massa"] = c3.checkbox(
            "Preço mensal (massa)", value=cm["preco_mensal_massa"], key="cont_pm"
        )
        cm["valor_projeto"] = c4.checkbox(
            "Valor por projeto", value=cm["valor_projeto"], key="cont_vp"
        )

        if cm["valor_acao"]:
            st.markdown("**Tabela — Valor por Ação**")
            acoes_df = pd.DataFrame(
                form["honorarios_contenciosa"]["tabela_acoes"]
                or [{"natureza": "", "fase": "", "valor": ""}]
            )
            edited_acoes = st.data_editor(
                acoes_df,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "natureza": st.column_config.TextColumn("Natureza da ação"),
                    "fase": st.column_config.TextColumn("Fase"),
                    "valor": st.column_config.TextColumn("Valor"),
                },
                key="acoes_editor",
            )
            form["honorarios_contenciosa"]["tabela_acoes"] = _df_to_records(
                edited_acoes, [{"natureza": "", "fase": "", "valor": ""}]
            )

        if cm["valor_ato_processual"]:
            st.markdown("**Tabela — Atos Processuais**")
            atos_df = pd.DataFrame(form["honorarios_contenciosa"]["tabela_atos"])
            edited_atos = st.data_editor(
                atos_df,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "ato": st.column_config.TextColumn("Ato processual"),
                    "descricao": st.column_config.TextColumn("Descrição", width="large"),
                    "valor": st.column_config.TextColumn("Valor"),
                },
                key="atos_editor",
            )
            form["honorarios_contenciosa"]["tabela_atos"] = _df_to_records(edited_atos, [])

        if cm["preco_mensal_massa"]:
            c1, c2 = st.columns(2)
            form["honorarios_contenciosa"]["preco_mensal_valor"] = c1.text_input(
                "Valor mensal fixo",
                value=form["honorarios_contenciosa"]["preco_mensal_valor"],
            )
            form["honorarios_contenciosa"]["preco_mensal_maximo_acoes"] = c2.text_input(
                "Número máximo de ações cobertas",
                value=form["honorarios_contenciosa"]["preco_mensal_maximo_acoes"],
            )
            form["honorarios_contenciosa"]["preco_mensal_maximo_acoes_extenso"] = (
                st.text_input(
                    "Número máximo (por extenso)",
                    value=form["honorarios_contenciosa"]["preco_mensal_maximo_acoes_extenso"],
                )
            )
            form["honorarios_contenciosa"]["preco_mensal_criterio_excedentes"] = (
                st.text_area(
                    "Critério para ações excedentes",
                    value=form["honorarios_contenciosa"]["preco_mensal_criterio_excedentes"],
                    height=80,
                )
            )

        if cm["valor_projeto"]:
            form["honorarios_contenciosa"]["valor_projeto_total"] = st.text_input(
                "Valor total do projeto — contencioso",
                value=form["honorarios_contenciosa"]["valor_projeto_total"],
                key="cont_vp_total",
            )
            form["honorarios_contenciosa"]["valor_projeto_fases_cobertas"] = st.text_area(
                "Ações e fases cobertas",
                value=form["honorarios_contenciosa"]["valor_projeto_fases_cobertas"],
                height=80,
            )
            form["honorarios_contenciosa"]["valor_projeto_forma_pagamento"] = st.text_area(
                "Forma de pagamento — contencioso",
                value=form["honorarios_contenciosa"]["valor_projeto_forma_pagamento"],
                height=80,
                key="cont_vp_forma",
            )

        st.markdown("---")
        form["honorarios_contenciosa"]["exito_ativo"] = st.checkbox(
            "Cobrar honorários de êxito?",
            value=form["honorarios_contenciosa"]["exito_ativo"],
        )
        if form["honorarios_contenciosa"]["exito_ativo"]:
            form["honorarios_contenciosa"]["exito_percentual"] = st.text_input(
                "Percentual sobre êxito (%)",
                value=form["honorarios_contenciosa"]["exito_percentual"],
            )

        st.markdown("---")
        st.markdown("**Horas para serviços extra escopo**")
        modos = ("senioridade", "horaFixa")
        form["honorarios_contenciosa"]["horas_extra_escopo_modo"] = st.radio(
            "Modo",
            options=modos,
            format_func=lambda x: "Tabela por senioridade" if x == "senioridade" else "Hora fixa",
            index=modos.index(form["honorarios_contenciosa"]["horas_extra_escopo_modo"]),
            horizontal=True,
            key="horas_extra_modo",
        )
        if form["honorarios_contenciosa"]["horas_extra_escopo_modo"] == "senioridade":
            sen_df2 = pd.DataFrame(form["honorarios_contenciosa"]["horas_extra_senioridade"])
            edited_sen2 = st.data_editor(
                sen_df2,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "categoria": st.column_config.TextColumn("Categoria"),
                    "valor": st.column_config.TextColumn("Valor por hora"),
                },
                key="sen_extra",
            )
            form["honorarios_contenciosa"]["horas_extra_senioridade"] = _df_to_records(
                edited_sen2, []
            )
        else:
            form["honorarios_contenciosa"]["horas_extra_valor"] = st.text_input(
                "Valor por hora (independente do executor) — extra escopo",
                value=form["honorarios_contenciosa"]["horas_extra_valor"],
                key="cont_extra_valor",
            )

# === 5. DESPESAS ===
with st.expander("5. Despesas", expanded=False):
    form["despesas"]["gerais_descricao"] = st.text_area(
        "Despesas gerais",
        value=form["despesas"]["gerais_descricao"],
        height=80,
    )
    form["despesas"]["especificas_descricao"] = st.text_area(
        "Despesas específicas",
        value=form["despesas"]["especificas_descricao"],
        height=100,
    )
    form["despesas"]["taxa_manutencao_processual"] = st.text_input(
        "Taxa de manutenção processual (deixe em branco para não cobrar)",
        value=form["despesas"]["taxa_manutencao_processual"],
    )

# === 6. DISPOSIÇÕES ESPECÍFICAS ===
with st.expander("6. Disposições específicas", expanded=False):
    form["disposicoes"]["ativo"] = st.checkbox(
        "Incluir seção de disposições específicas?",
        value=form["disposicoes"]["ativo"],
    )
    if form["disposicoes"]["ativo"]:
        form["disposicoes"]["descricao"] = st.text_area(
            "Disposições",
            value=form["disposicoes"]["descricao"],
            height=120,
        )

st.divider()

# === GERAR ===
gen_col, dl_col = st.columns([1, 2])
if gen_col.button("Gerar proposta", type="primary", use_container_width=True):
    try:
        proposal = ProposalForm.model_validate(form)
        context = form_to_context(proposal)
        st.session_state.generated_doc = render_proposal(context)
        st.success("Proposta gerada. Clique em **Baixar .docx** para salvar.")
    except Exception as e:
        st.error(f"Erro ao gerar proposta: {e}")
        st.code(traceback.format_exc())

if st.session_state.generated_doc:
    cliente = (
        form["contratante"]["nome"]
        if form["contratante"]["tipo_pessoa"] == "fisica"
        else form["contratante"]["razao_social"]
    )
    safe_name = "".join(c if c.isalnum() else "_" for c in cliente).strip("_") or "PMRA_Proposta"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"PMRA_Proposta_{safe_name}_{timestamp}.docx"
    dl_col.download_button(
        "Baixar .docx",
        data=st.session_state.generated_doc,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True,
    )
