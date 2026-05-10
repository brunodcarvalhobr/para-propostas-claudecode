"""PMRA — Gerador de Propostas (Streamlit) — formulário em etapas."""
from __future__ import annotations

import re
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


# ── Constantes ────────────────────────────────────────────────────────────────

STEPS = [
    "Contratante",
    "Escopo e SLA",
    "Honorários",
    "Despesas e Disposições",
    "Gerar Proposta",
]


# ── Formatadores de documentos ─────────────────────────────────────────────────

def _digits(v: str, n: int) -> str:
    return re.sub(r"\D", "", str(v))[:n]


def _fmt_cpf(v: str) -> str:
    d = _digits(v, 11)
    if len(d) <= 3:
        return d
    if len(d) <= 6:
        return f"{d[:3]}.{d[3:]}"
    if len(d) <= 9:
        return f"{d[:3]}.{d[3:6]}.{d[6:]}"
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"


def _fmt_cnpj(v: str) -> str:
    d = _digits(v, 14)
    if len(d) <= 2:
        return d
    if len(d) <= 5:
        return f"{d[:2]}.{d[2:]}"
    if len(d) <= 8:
        return f"{d[:2]}.{d[2:5]}.{d[5:]}"
    if len(d) <= 12:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:]}"
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"


def _fmt_cep(v: str) -> str:
    d = _digits(v, 8)
    if len(d) <= 5:
        return d
    return f"{d[:5]}-{d[5:]}"


def _fmt_tel(v: str) -> str:
    d = _digits(v, 11)
    if len(d) <= 2:
        return d
    if len(d) <= 6:
        return f"({d[:2]}) {d[2:]}"
    if len(d) <= 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return f"({d[:2]}) {d[2:7]}-{d[7:]}"


# ── Inicialização de estado ────────────────────────────────────────────────────

def _init_state() -> None:
    defaults = proposal_form_default().model_dump()
    if "form" not in st.session_state:
        st.session_state.form = defaults
    if "step" not in st.session_state:
        st.session_state.step = 0
    if "generated_doc" not in st.session_state:
        st.session_state.generated_doc = None

    f = st.session_state.form
    # Tabelas em chaves dedicadas — inicializadas apenas uma vez
    if "tbl_contatos" not in st.session_state:
        st.session_state.tbl_contatos = f["contratante"]["contatos"] or [{"telefone": "", "email": ""}]
    if "tbl_sen_cons" not in st.session_state:
        st.session_state.tbl_sen_cons = f["honorarios_consultiva"]["tabela_senioridade"]
    if "tbl_acoes" not in st.session_state:
        st.session_state.tbl_acoes = f["honorarios_contenciosa"]["tabela_acoes"] or [{"natureza": "", "fase": "", "valor": ""}]
    if "tbl_atos" not in st.session_state:
        st.session_state.tbl_atos = f["honorarios_contenciosa"]["tabela_atos"]
    if "tbl_sen_extra" not in st.session_state:
        st.session_state.tbl_sen_extra = f["honorarios_contenciosa"]["horas_extra_senioridade"]


_init_state()
form: dict = st.session_state.form


# ── Navegação ──────────────────────────────────────────────────────────────────

def _apply_formats() -> None:
    """Aplica formatação de documentos ao sair da etapa Contratante.

    Também atualiza os keys do session_state dos widgets para que o valor
    formatado seja exibido quando o usuário retornar à etapa 1.
    """
    c = form["contratante"]
    if c["tipo_pessoa"] == "fisica":
        c["cpf"] = _fmt_cpf(c["cpf"])
        st.session_state["cpf_input"] = c["cpf"]
    else:
        c["cnpj"] = _fmt_cnpj(c["cnpj"])
        st.session_state["cnpj_input"] = c["cnpj"]
    c["endereco"]["cep"] = _fmt_cep(c["endereco"]["cep"])
    st.session_state["cep_input"] = c["endereco"]["cep"]
    # Formata telefones da tabela de contatos
    for row in st.session_state.tbl_contatos:
        row["telefone"] = _fmt_tel(row["telefone"])


def _go_next() -> None:
    if st.session_state.step == 0:
        _apply_formats()
    st.session_state.step = min(st.session_state.step + 1, len(STEPS) - 1)


def _go_prev() -> None:
    st.session_state.step = max(st.session_state.step - 1, 0)


def _go_to(n: int) -> None:
    if st.session_state.step == 0:
        _apply_formats()
    st.session_state.step = n


current: int = st.session_state.step


# ── Cabeçalho e indicador de etapas ───────────────────────────────────────────

st.markdown("## PMRA — Gerador de Propostas")
st.caption(
    "Preencha as etapas e clique em **Gerar proposta** na última etapa. "
    "Campos vazios aparecem como placeholders no .docx — revise antes de enviar."
)

# Indicador de progresso clicável
indicator_cols = st.columns(len(STEPS))
for i, (col, name) in enumerate(zip(indicator_cols, STEPS)):
    if i == current:
        col.button(
            f"{i + 1}. {name}",
            key=f"step_btn_{i}",
            use_container_width=True,
            type="primary",
            on_click=_go_to,
            args=(i,),
        )
    elif i < current:
        col.button(
            f"{i + 1}. {name} [ok]",
            key=f"step_btn_{i}",
            use_container_width=True,
            on_click=_go_to,
            args=(i,),
        )
    else:
        col.button(
            f"{i + 1}. {name}",
            key=f"step_btn_{i}",
            use_container_width=True,
            disabled=True,
        )

st.progress((current + 1) / len(STEPS))
st.divider()


# ── Helper: tabela editável com persistência estável ──────────────────────────

def _render_table(
    ss_key: str,
    columns: dict[str, str],
    min_row: dict | None = None,
    help_text: str = "",
) -> list[dict]:
    """Renderiza st.data_editor usando session_state dedicado.

    Salva o DataFrame completo (não deltas) para evitar dados somindo.
    """
    data: list[dict] = st.session_state.get(ss_key, [])
    if not data and min_row is not None:
        data = [min_row]

    df = pd.DataFrame(data if data else [{}])
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    df = df[list(columns.keys())].fillna("").astype(str)

    col_config = {k: st.column_config.TextColumn(v) for k, v in columns.items()}

    if help_text:
        st.caption(help_text)

    edited: pd.DataFrame = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config=col_config,
        hide_index=True,
    )

    records: list[dict] = edited.fillna("").astype(str).to_dict("records")
    st.session_state[ss_key] = records
    return records


# ── ETAPA 1: CONTRATANTE ───────────────────────────────────────────────────────

if current == 0:
    st.subheader("Identificação do contratante")

    form["contratante"]["tipo_pessoa"] = st.radio(
        "Tipo de pessoa",
        options=("fisica", "juridica"),
        format_func=lambda x: "Pessoa Física" if x == "fisica" else "Pessoa Jurídica",
        index=0 if form["contratante"]["tipo_pessoa"] == "fisica" else 1,
        horizontal=True,
        key="tipo_pessoa",
    )

    st.markdown("---")

    if form["contratante"]["tipo_pessoa"] == "fisica":
        c1, c2 = st.columns([2, 1])
        form["contratante"]["nome"] = c1.text_input(
            "Nome completo",
            value=form["contratante"]["nome"],
            key="nome_input",
        )
        form["contratante"]["cpf"] = c2.text_input(
            "CPF",
            value=form["contratante"]["cpf"],
            placeholder="000.000.000-00",
            key="cpf_input",
        )
    else:
        c1, c2 = st.columns([2, 1])
        form["contratante"]["razao_social"] = c1.text_input(
            "Razão Social",
            value=form["contratante"]["razao_social"],
            key="razao_social_input",
        )
        form["contratante"]["cnpj"] = c2.text_input(
            "CNPJ",
            value=form["contratante"]["cnpj"],
            placeholder="00.000.000/0000-00",
            key="cnpj_input",
        )

    st.markdown("**Endereço**")
    end = form["contratante"]["endereco"]

    c1, c2 = st.columns([3, 1])
    end["logradouro"] = c1.text_input("Logradouro", value=end["logradouro"], key="logradouro_input")
    end["numero"] = c2.text_input("Número", value=end["numero"], key="numero_input")

    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
    end["bairro"] = c1.text_input("Bairro", value=end["bairro"], key="bairro_input")
    end["cep"] = c2.text_input("CEP", value=end["cep"], placeholder="00000-000", key="cep_input")
    end["cidade"] = c3.text_input("Cidade", value=end["cidade"], key="cidade_input")
    end["uf"] = c4.selectbox(
        "UF",
        options=UF_OPTIONS,
        index=UF_OPTIONS.index(end["uf"]) if end["uf"] in UF_OPTIONS else 0,
        key="uf_input",
    )

    st.markdown("**Responsável e contatos**")
    form["contratante"]["contato_nome"] = st.text_input(
        "Nome do responsável",
        value=form["contratante"]["contato_nome"],
        key="contato_nome_input",
    )

    records_contatos = _render_table(
        "tbl_contatos",
        {"telefone": "Telefone", "email": "E-mail"},
        min_row={"telefone": "", "email": ""},
        help_text="Telefone: (31) 99999-0000 — formatado automaticamente ao avançar.",
    )
    form["contratante"]["contatos"] = records_contatos


# ── ETAPA 2: ESCOPO E SLA ──────────────────────────────────────────────────────

elif current == 1:
    st.subheader("Escopo da contratação e SLA")

    modalidades = ("consultiva", "contenciosa", "mista")
    form["escopo"]["modalidade"] = st.radio(
        "Modalidade de atuação",
        options=modalidades,
        format_func=lambda x: {
            "consultiva": "Consultiva",
            "contenciosa": "Contenciosa",
            "mista": "Mista (Consultiva + Contenciosa)",
        }[x],
        index=modalidades.index(form["escopo"]["modalidade"]),
        horizontal=True,
        key="modalidade_radio",
    )

    modal = form["escopo"]["modalidade"]

    st.markdown("---")

    if modal in ("consultiva", "mista"):
        st.markdown("**Atuação Consultiva**")
        form["escopo"]["atuacao_consultiva"] = st.text_area(
            "Áreas, matérias e entregáveis",
            value=form["escopo"]["atuacao_consultiva"],
            height=150,
            key="atuacao_consultiva_ta",
            placeholder="Ex: Consultoria societária, revisão de contratos, pareceres jurídicos.",
        )

    if modal in ("contenciosa", "mista"):
        st.markdown("**Atuação Contenciosa**")
        form["escopo"]["atuacao_contenciosa"] = st.text_area(
            "Matérias, foros, instâncias e atos processuais",
            value=form["escopo"]["atuacao_contenciosa"],
            height=150,
            key="atuacao_contenciosa_ta",
            placeholder="Ex: Defesa em processos trabalhistas — 1ª e 2ª instância — TRT MG.",
        )

    st.markdown("---")
    st.markdown("**SLA por complexidade**")
    form["escopo"]["sla_ativo"] = st.checkbox(
        "Definir prazos de resposta por complexidade?",
        value=form["escopo"]["sla_ativo"],
        key="sla_ativo_cb",
    )
    if form["escopo"]["sla_ativo"]:
        form["escopo"]["sla_descricao"] = st.text_area(
            "Descrição do SLA",
            value=form["escopo"]["sla_descricao"],
            height=120,
            key="sla_descricao_ta",
            placeholder="Baixa: 5 dias úteis\nMédia: 2 dias úteis\nAlta: 24 horas",
        )


# ── ETAPA 3: HONORÁRIOS ────────────────────────────────────────────────────────

elif current == 2:
    modal = form["escopo"]["modalidade"]
    show_consultiva = modal in ("consultiva", "mista")
    show_contenciosa = modal in ("contenciosa", "mista")

    # ── 3a. Consultiva
    if show_consultiva:
        st.subheader("Honorários — Atuação Consultiva")

        cm = form["honorarios_consultiva"]["modalidades"]
        st.markdown("**Modalidades de cobrança** (selecione uma ou mais)")
        c1, c2, c3, c4 = st.columns(4)
        cm["hora_senioridade"] = c1.checkbox("Hora por senioridade", value=cm["hora_senioridade"], key="cons_hs")
        cm["hora_fixa"] = c2.checkbox("Hora fixa", value=cm["hora_fixa"], key="cons_hf")
        cm["fixo_mensal"] = c3.checkbox("Fixo mensal", value=cm["fixo_mensal"], key="cons_fm")
        cm["valor_projeto"] = c4.checkbox("Valor do projeto", value=cm["valor_projeto"], key="cons_vp")

        if cm["hora_senioridade"]:
            st.markdown("**Tabela de senioridade — consultiva**")
            form["honorarios_consultiva"]["tabela_senioridade"] = _render_table(
                "tbl_sen_cons",
                {"categoria": "Categoria", "valor": "Valor por hora"},
                help_text="Ex de valor: R$ 1.050,00",
            )

        if cm["hora_fixa"]:
            form["honorarios_consultiva"]["hora_fixa_valor"] = st.text_input(
                "Valor por hora (independente do executor)",
                value=form["honorarios_consultiva"]["hora_fixa_valor"],
                placeholder="Ex: R$ 700,00",
                key="cons_hf_valor",
            )

        if cm["fixo_mensal"]:
            c1, c2, c3 = st.columns(3)
            form["honorarios_consultiva"]["fixo_mensal_valor"] = c1.text_input(
                "Valor mensal",
                value=form["honorarios_consultiva"]["fixo_mensal_valor"],
                placeholder="Ex: R$ 15.000,00",
                key="cons_fm_valor",
            )
            form["honorarios_consultiva"]["fixo_mensal_cap"] = c2.text_input(
                "Cap de horas inclusas",
                value=form["honorarios_consultiva"]["fixo_mensal_cap"],
                placeholder="Ex: 30 horas",
                key="cons_fm_cap",
            )
            form["honorarios_consultiva"]["fixo_mensal_excedente"] = c3.text_input(
                "Hora excedente",
                value=form["honorarios_consultiva"]["fixo_mensal_excedente"],
                placeholder="Ex: R$ 600,00",
                key="cons_fm_exc",
            )

        if cm["valor_projeto"]:
            form["honorarios_consultiva"]["valor_projeto_total"] = st.text_input(
                "Valor total do projeto",
                value=form["honorarios_consultiva"]["valor_projeto_total"],
                placeholder="Ex: R$ 50.000,00",
                key="cons_vp_total",
            )
            form["honorarios_consultiva"]["valor_projeto_forma_pagamento"] = st.text_area(
                "Forma de pagamento",
                value=form["honorarios_consultiva"]["valor_projeto_forma_pagamento"],
                height=80,
                key="cons_vp_forma",
            )

    # ── 3b. Contenciosa
    if show_contenciosa:
        if show_consultiva:
            st.divider()
        st.subheader("Honorários — Atuação Contenciosa")

        cm = form["honorarios_contenciosa"]["modalidades"]
        st.markdown("**Modalidades de cobrança** (selecione uma ou mais)")
        c1, c2, c3, c4 = st.columns(4)
        cm["valor_acao"] = c1.checkbox("Valor por ação", value=cm["valor_acao"], key="cont_va")
        cm["valor_ato_processual"] = c2.checkbox("Valor por ato processual", value=cm["valor_ato_processual"], key="cont_vap")
        cm["preco_mensal_massa"] = c3.checkbox("Preço mensal (massa)", value=cm["preco_mensal_massa"], key="cont_pm")
        cm["valor_projeto"] = c4.checkbox("Valor por projeto", value=cm["valor_projeto"], key="cont_vp")

        if cm["valor_acao"]:
            st.markdown("**Tabela — Valor por Ação**")
            form["honorarios_contenciosa"]["tabela_acoes"] = _render_table(
                "tbl_acoes",
                {"natureza": "Natureza da ação", "fase": "Fase processual", "valor": "Valor"},
                min_row={"natureza": "", "fase": "", "valor": ""},
                help_text="Ex: Trabalhista | Conhecimento | R$ 5.000,00",
            )

        if cm["valor_ato_processual"]:
            st.markdown("**Tabela — Atos Processuais**")
            form["honorarios_contenciosa"]["tabela_atos"] = _render_table(
                "tbl_atos",
                {"ato": "Ato processual", "descricao": "Descrição", "valor": "Valor"},
                help_text="Edite valores na coluna Valor. Linhas em branco são ignoradas.",
            )

        if cm["preco_mensal_massa"]:
            c1, c2 = st.columns(2)
            form["honorarios_contenciosa"]["preco_mensal_valor"] = c1.text_input(
                "Valor mensal fixo",
                value=form["honorarios_contenciosa"]["preco_mensal_valor"],
                placeholder="Ex: R$ 8.000,00",
                key="cont_pm_valor",
            )
            form["honorarios_contenciosa"]["preco_mensal_maximo_acoes"] = c2.text_input(
                "Nº máximo de ações cobertas",
                value=form["honorarios_contenciosa"]["preco_mensal_maximo_acoes"],
                placeholder="Ex: 20",
                key="cont_pm_max",
            )
            form["honorarios_contenciosa"]["preco_mensal_maximo_acoes_extenso"] = st.text_input(
                "Nº máximo por extenso",
                value=form["honorarios_contenciosa"]["preco_mensal_maximo_acoes_extenso"],
                placeholder="Ex: vinte",
                key="cont_pm_max_ext",
            )
            form["honorarios_contenciosa"]["preco_mensal_criterio_excedentes"] = st.text_area(
                "Critério para ações excedentes",
                value=form["honorarios_contenciosa"]["preco_mensal_criterio_excedentes"],
                height=80,
                key="cont_pm_crit",
            )

        if cm["valor_projeto"]:
            form["honorarios_contenciosa"]["valor_projeto_total"] = st.text_input(
                "Valor total do projeto — contencioso",
                value=form["honorarios_contenciosa"]["valor_projeto_total"],
                placeholder="Ex: R$ 30.000,00",
                key="cont_vp_total",
            )
            form["honorarios_contenciosa"]["valor_projeto_fases_cobertas"] = st.text_area(
                "Ações e fases cobertas",
                value=form["honorarios_contenciosa"]["valor_projeto_fases_cobertas"],
                height=80,
                key="cont_vp_fases",
            )
            form["honorarios_contenciosa"]["valor_projeto_forma_pagamento"] = st.text_area(
                "Forma de pagamento",
                value=form["honorarios_contenciosa"]["valor_projeto_forma_pagamento"],
                height=80,
                key="cont_vp_forma",
            )

        st.markdown("---")
        form["honorarios_contenciosa"]["exito_ativo"] = st.checkbox(
            "Cobrar honorários de êxito?",
            value=form["honorarios_contenciosa"]["exito_ativo"],
            key="cont_exito_cb",
        )
        if form["honorarios_contenciosa"]["exito_ativo"]:
            form["honorarios_contenciosa"]["exito_percentual"] = st.text_input(
                "Percentual de êxito (%)",
                value=form["honorarios_contenciosa"]["exito_percentual"],
                placeholder="Ex: 10",
                key="cont_exito_pct",
            )

        st.markdown("---")
        st.markdown("**Horas para serviços extra escopo**")
        modos = ("senioridade", "horaFixa")
        form["honorarios_contenciosa"]["horas_extra_escopo_modo"] = st.radio(
            "Modo de cobrança",
            options=modos,
            format_func=lambda x: "Tabela por senioridade" if x == "senioridade" else "Hora fixa (valor único)",
            index=modos.index(form["honorarios_contenciosa"]["horas_extra_escopo_modo"]),
            horizontal=True,
            key="horas_extra_modo_radio",
        )
        if form["honorarios_contenciosa"]["horas_extra_escopo_modo"] == "senioridade":
            form["honorarios_contenciosa"]["horas_extra_senioridade"] = _render_table(
                "tbl_sen_extra",
                {"categoria": "Categoria", "valor": "Valor por hora"},
            )
        else:
            form["honorarios_contenciosa"]["horas_extra_valor"] = st.text_input(
                "Valor por hora — extra escopo",
                value=form["honorarios_contenciosa"]["horas_extra_valor"],
                placeholder="Ex: R$ 500,00",
                key="cont_extra_valor",
            )


# ── ETAPA 4: DESPESAS E DISPOSIÇÕES ───────────────────────────────────────────

elif current == 3:
    st.subheader("Despesas e Disposições Específicas")

    st.markdown("**Despesas**")
    form["despesas"]["gerais_descricao"] = st.text_area(
        "Despesas gerais reembolsáveis",
        value=form["despesas"]["gerais_descricao"],
        height=100,
        key="desp_gerais_ta",
        placeholder="Ex: Deslocamentos, fotocópias, comunicações, registros.",
    )
    form["despesas"]["especificas_descricao"] = st.text_area(
        "Despesas específicas do caso",
        value=form["despesas"]["especificas_descricao"],
        height=100,
        key="desp_espec_ta",
        placeholder="Ex: Honorários periciais, guias de recolhimento, emolumentos.",
    )
    form["despesas"]["taxa_manutencao_processual"] = st.text_input(
        "Taxa de manutenção processual (deixe vazio para não cobrar)",
        value=form["despesas"]["taxa_manutencao_processual"],
        placeholder="Ex: R$ 50,00 por processo/mês",
        key="desp_taxa_input",
    )

    st.markdown("---")
    st.markdown("**Disposições específicas**")
    form["disposicoes"]["ativo"] = st.checkbox(
        "Incluir seção de disposições específicas no contrato?",
        value=form["disposicoes"]["ativo"],
        key="disp_ativo_cb",
    )
    if form["disposicoes"]["ativo"]:
        form["disposicoes"]["descricao"] = st.text_area(
            "Disposições",
            value=form["disposicoes"]["descricao"],
            height=140,
            key="disp_desc_ta",
            placeholder="Ex: Foro eleito: comarca de Belo Horizonte/MG.",
        )


# ── ETAPA 5: REVISAR E GERAR ───────────────────────────────────────────────────

elif current == 4:
    st.subheader("Revisar e Gerar Proposta")

    modal = form["escopo"]["modalidade"]
    tipo = form["contratante"]["tipo_pessoa"]
    nome_cliente = form["contratante"]["nome"] if tipo == "fisica" else form["contratante"]["razao_social"]
    doc_cliente = form["contratante"]["cpf"] if tipo == "fisica" else form["contratante"]["cnpj"]
    cidade = form["contratante"]["endereco"]["cidade"]
    uf = form["contratante"]["endereco"]["uf"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Contratante", nome_cliente or "—")
    c2.metric("Documento", doc_cliente or "—")
    c3.metric("Localidade", f"{cidade}/{uf}" if cidade else "—")
    c4.metric("Modalidade", modal.capitalize())

    st.markdown("---")

    gen_col, dl_col = st.columns([1, 2])

    if gen_col.button("Gerar proposta", type="primary", use_container_width=True):
        try:
            proposal = ProposalForm.model_validate(form)
            context = form_to_context(proposal)
            st.session_state.generated_doc = render_proposal(context)
            st.success("Proposta gerada com sucesso. Clique em **Baixar .docx** para salvar.")
        except Exception as e:
            st.error(f"Erro ao gerar proposta: {e}")
            st.code(traceback.format_exc())

    if st.session_state.generated_doc:
        safe_name = (
            "".join(c if c.isalnum() else "_" for c in (nome_cliente or "")).strip("_")
            or "PMRA_Proposta"
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"PMRA_Proposta_{safe_name}_{timestamp}.docx"
        dl_col.download_button(
            "Baixar .docx",
            data=st.session_state.generated_doc,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )


# ── Navegação: botões Anterior / Próximo ──────────────────────────────────────

st.divider()
nav_prev, _, nav_next = st.columns([1, 3, 1])

if current > 0:
    nav_prev.button(
        "Anterior",
        on_click=_go_prev,
        use_container_width=True,
        key="nav_prev",
    )

if current < len(STEPS) - 1:
    nav_next.button(
        "Proximo",
        on_click=_go_next,
        type="primary",
        use_container_width=True,
        key="nav_next",
    )
