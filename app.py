"""DocGen by PMRA Legal Tech (Streamlit) — formulário em etapas."""
from __future__ import annotations

import html
import logging
import os
import re
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from pmra.auth import check_password
from pmra.data_mapper import form_to_context, _fmt_money as _money_fmt
from pmra.defaults import proposal_form_default
from pmra.schema import ProposalForm, UF_OPTIONS
from pmra.template_engine import render_proposal

logger = logging.getLogger(__name__)

# Lê o SVG do logo uma vez no carregamento do módulo
_SVG_PATH = os.path.join(os.path.dirname(__file__), "pmra-icon.svg")
_LOGO_SVG: str = ""
if os.path.exists(_SVG_PATH):
    with open(_SVG_PATH, "r", encoding="utf-8") as _f:
        _LOGO_SVG = _f.read()


st.set_page_config(
    page_title="DocGen by PMRA Legal Tech",
    page_icon="⚖️",
    layout="wide",
)

if not check_password():
    st.stop()

# ── Estilos PMRA ───────────────────────────────────────────────────────────────

_STYLES_CSS = (Path(__file__).parent / "resources" / "static" / "styles.css").read_text(encoding="utf-8")
st.markdown(f"<style>{_STYLES_CSS}</style>", unsafe_allow_html=True)


# ── Máscara em tempo real (JS via iframe) ──────────────────────────────────────

components.html("""
<script>
(function () {
  function digits(v, n) { return (v || '').replace(/\D/g, '').slice(0, n); }

  function fmtCpf(v) {
    const d = digits(v, 11);
    if (d.length <= 3) return d;
    if (d.length <= 6) return d.slice(0,3)+'.'+d.slice(3);
    if (d.length <= 9) return d.slice(0,3)+'.'+d.slice(3,6)+'.'+d.slice(6);
    return d.slice(0,3)+'.'+d.slice(3,6)+'.'+d.slice(6,9)+'-'+d.slice(9);
  }
  function fmtCnpj(v) {
    const d = digits(v, 14);
    if (d.length <= 2) return d;
    if (d.length <= 5) return d.slice(0,2)+'.'+d.slice(2);
    if (d.length <= 8) return d.slice(0,2)+'.'+d.slice(2,5)+'.'+d.slice(5);
    if (d.length <= 12) return d.slice(0,2)+'.'+d.slice(2,5)+'.'+d.slice(5,8)+'/'+d.slice(8);
    return d.slice(0,2)+'.'+d.slice(2,5)+'.'+d.slice(5,8)+'/'+d.slice(8,12)+'-'+d.slice(12);
  }
  function fmtCep(v) {
    const d = digits(v, 8);
    if (d.length <= 5) return d;
    return d.slice(0,5)+'-'+d.slice(5);
  }
  function fmtTel(v) {
    const d = digits(v, 11);
    if (d.length <= 2) return d;
    if (d.length <= 6) return '('+d.slice(0,2)+') '+d.slice(2);
    if (d.length <= 10) return '('+d.slice(0,2)+') '+d.slice(2,6)+'-'+d.slice(6);
    return '('+d.slice(0,2)+') '+d.slice(2,7)+'-'+d.slice(7);
  }

  const LABEL_MASKS = {
    'CPF': fmtCpf, 'CNPJ': fmtCnpj, 'CEP': fmtCep, 'Telefone': fmtTel,
  };

  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;

  function applyMask(input, maskFn) {
    if (input._pmraMasked) return;
    input._pmraMasked = true;
    input.addEventListener('input', function (e) {
      if (e._pmra) return;
      const raw = this.value;
      const pos = this.selectionStart;
      const digitsBeforeCursor = raw.slice(0, pos).replace(/\D/g, '').length;
      const fmt = maskFn(raw);
      if (fmt === raw) return;
      setter.call(this, fmt);
      const ev = new Event('input', { bubbles: true });
      ev._pmra = true;
      this.dispatchEvent(ev);
      // Reposiciona cursor contando dígitos
      let dc = 0, np = fmt.length;
      for (let i = 0; i < fmt.length; i++) {
        if (/\d/.test(fmt[i])) dc++;
        if (dc >= digitsBeforeCursor) { np = i + 1; break; }
      }
      this.setSelectionRange(np, np);
    });
  }

  function setupMasks() {
    const doc = window.parent.document;
    doc.querySelectorAll('[data-testid="stTextInput"]').forEach(function (wrap) {
      const label = wrap.querySelector('label');
      const input = wrap.querySelector('input');
      if (!label || !input) return;
      const maskFn = LABEL_MASKS[label.textContent.trim()];
      if (maskFn) applyMask(input, maskFn);
    });
  }

  let debounce;
  const obs = new MutationObserver(function () {
    clearTimeout(debounce);
    debounce = setTimeout(setupMasks, 120);
  });

  function start() {
    setupMasks();
    obs.observe(window.parent.document.body, { childList: true, subtree: true });
  }

  if (window.parent.document.readyState === 'loading') {
    window.parent.document.addEventListener('DOMContentLoaded', function () { setTimeout(start, 400); });
  } else {
    setTimeout(start, 400);
  }
})();
</script>
""", height=0)

# ── Constantes ────────────────────────────────────────────────────────────────

STEPS = [
    "Contratante",
    "Escopo e SLA",
    "Honorários",
    "Despesas",
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


# Callbacks on_change para aplicar máscara ao sair do campo
def _on_cpf_change() -> None:
    st.session_state["cpf_input"] = _fmt_cpf(st.session_state.get("cpf_input", ""))

def _on_cnpj_change() -> None:
    st.session_state["cnpj_input"] = _fmt_cnpj(st.session_state.get("cnpj_input", ""))

def _on_cep_change() -> None:
    st.session_state["cep_input"] = _fmt_cep(st.session_state.get("cep_input", ""))

def _on_tel_change(wk: str) -> None:
    st.session_state[wk] = _fmt_tel(st.session_state.get(wk, ""))

def _on_money_change(wk: str) -> None:
    st.session_state[wk] = _money_fmt(st.session_state.get(wk, ""))


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
    if "tbl_despesas" not in st.session_state:
        st.session_state.tbl_despesas = f["despesas"]["tabela_despesas"]


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
    # Formata telefones da tabela de contatos e atualiza os widget keys
    for i, row in enumerate(st.session_state.tbl_contatos):
        row["telefone"] = _fmt_tel(row["telefone"])
        wk = f"tbl_contatos__telefone__{i}"
        if wk in st.session_state:
            st.session_state[wk] = row["telefone"]


def _go_next() -> None:
    if st.session_state.step == 0:
        _apply_formats()
    st.session_state.step = min(st.session_state.step + 1, len(STEPS) - 1)
    st.session_state.scroll_to_top = True


def _go_prev() -> None:
    st.session_state.step = max(st.session_state.step - 1, 0)
    st.session_state.scroll_to_top = True


def _go_to(n: int) -> None:
    if st.session_state.step == 0:
        _apply_formats()
    st.session_state.step = n
    st.session_state.scroll_to_top = True


current: int = st.session_state.step

if st.session_state.get("scroll_to_top", False):
    components.html("""
    <script>
        const win = window.parent;
        win.scrollTo({top: 0, behavior: 'smooth'});
        const selectors = ['.stApp', '.main', '[data-testid="stAppViewContainer"]', '[data-testid="stMain"]'];
        selectors.forEach(sel => {
            const el = win.document.querySelector(sel);
            if (el) el.scrollTo({top: 0, behavior: 'smooth'});
        });
    </script>
    """, height=0)
    st.session_state.scroll_to_top = False


# ── Cabeçalho com logo ────────────────────────────────────────────────────────

_logo_html = f'<div class="pmra-header"><div class="pmra-header-left">'
if _LOGO_SVG:
    _logo_html += f'{_LOGO_SVG}'
else:
    _logo_html += f'<div style="width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg,#f97316,#ea580c);display:flex;align-items:center;justify-content:center;"><span style="font-family:var(--font-display);font-style:italic;color:white;font-size:14px;font-weight:500;letter-spacing:-0.02em">PM</span></div>'

_logo_html += """
  <div class="pmra-header-divider"></div>
  <div class="pmra-header-text">
    <h1>Gerador de Propostas</h1>
  </div>
</div></div>"""
st.markdown(_logo_html, unsafe_allow_html=True)

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
            f"✓ {name}",
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

st.divider()


# ── Helper: tabela editável row-by-row ────────────────────────────────────────

def _sync_rows(ss_key: str, col_keys: list[str]) -> list[dict]:
    """Lê os widgets de texto e persiste na session_state."""
    rows: list[dict] = st.session_state.get(ss_key, [])
    synced = []
    for i, row in enumerate(rows):
        new_row = {}
        for field in col_keys:
            wk = f"{ss_key}__{field}__{i}"
            new_row[field] = st.session_state.get(wk, row.get(field, ""))
        synced.append(new_row)
    st.session_state[ss_key] = synced
    return synced


def _clear_row_widgets(ss_key: str, col_keys: list[str], n_rows: int) -> None:
    """Remove as chaves de widget de todas as linhas (força re-render limpo)."""
    for i in range(n_rows):
        for field in col_keys:
            k = f"{ss_key}__{field}__{i}"
            if k in st.session_state:
                del st.session_state[k]


def _add_row_cb(ss_key: str, col_keys: list[str]) -> None:
    synced = _sync_rows(ss_key, col_keys)
    _clear_row_widgets(ss_key, col_keys, len(synced))
    synced.append({f: "" for f in col_keys})
    st.session_state[ss_key] = synced


def _del_row_cb(ss_key: str, col_keys: list[str], idx: int) -> None:
    synced = _sync_rows(ss_key, col_keys)
    _clear_row_widgets(ss_key, col_keys, len(synced))
    if 0 <= idx < len(synced):
        synced.pop(idx)
    if not synced:
        synced = [{f: "" for f in col_keys}]
    st.session_state[ss_key] = synced


def _render_rows(
    ss_key: str,
    columns: dict[str, str],
    help_text: str = "",
    col_widths: list[int] | None = None,
    field_formatters: dict[str, callable] | None = None,
    text_areas: list[str] | None = None,
) -> list[dict]:
    """Renderiza tabela como linhas de inputs individuais com botão ✕ por linha.

    field_formatters: mapa campo → função que recebe o widget_key e formata
    o valor em session_state (chamada via on_change).
    """
    rows: list[dict] = st.session_state.get(ss_key, [])
    if not rows:
        rows = [{f: "" for f in columns}]
        st.session_state[ss_key] = rows

    col_keys = list(columns.keys())
    labels = list(columns.values())
    n_cols = len(col_keys)
    widths = (col_widths or [3] * n_cols) + [1]
    formatters = field_formatters or {}

    if help_text:
        st.caption(help_text)

    # Cabeçalho
    header = st.columns(widths)
    for j, label in enumerate(labels):
        header[j].markdown(f'<div class="pmra-tbl-hdr">{label}</div>', unsafe_allow_html=True)

    text_areas_list = text_areas or []
    # Linhas de dados
    for i, row in enumerate(rows):
        row_cols = st.columns(widths)
        for j, field in enumerate(col_keys):
            wk = f"{ss_key}__{field}__{i}"
            fmt_fn = formatters.get(field)
            if field in text_areas_list:
                row_cols[j].text_area(
                    labels[j],
                    value=row.get(field, ""),
                    key=wk,
                    label_visibility="collapsed",
                    on_change=fmt_fn,
                    args=(wk,) if fmt_fn else None,
                )
            else:
                row_cols[j].text_input(
                    labels[j],
                    value=row.get(field, ""),
                    key=wk,
                    label_visibility="collapsed",
                    on_change=fmt_fn,
                    args=(wk,) if fmt_fn else None,
                )
        row_cols[-1].button(
            "✕",
            key=f"{ss_key}__del__{i}",
            on_click=_del_row_cb,
            args=(ss_key, col_keys, i),
            use_container_width=True,
            help="Remover linha",
            disabled=len(rows) == 1,
        )

    st.button(
        "+ Adicionar linha",
        key=f"{ss_key}__add",
        on_click=_add_row_cb,
        args=(ss_key, col_keys),
    )

    return _sync_rows(ss_key, col_keys)


# ── ETAPA 1: CONTRATANTE ───────────────────────────────────────────────────────

if current == 0:
    st.subheader("Identificação do contratante")

    with st.container(border=True):
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
                on_change=_on_cpf_change,
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
                on_change=_on_cnpj_change,
            )

    with st.container(border=True):
        st.markdown('<div class="pmra-sub-hdr">Endereço</div>', unsafe_allow_html=True)
        end = form["contratante"]["endereco"]

        c1, c2 = st.columns([3, 1])
        end["logradouro"] = c1.text_input("Logradouro", value=end["logradouro"], key="logradouro_input")
        end["numero"] = c2.text_input("Número/Complemento", value=end["numero"], key="numero_input")

        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
        end["bairro"] = c1.text_input("Bairro", value=end["bairro"], key="bairro_input")
        end["cep"] = c2.text_input("CEP", value=end["cep"], placeholder="00000-000", key="cep_input", on_change=_on_cep_change)
        end["cidade"] = c3.text_input("Cidade", value=end["cidade"], key="cidade_input")
        end["uf"] = c4.selectbox(
            "UF",
            options=UF_OPTIONS,
            index=UF_OPTIONS.index(end["uf"]) if end["uf"] in UF_OPTIONS else 0,
            key="uf_input",
        )

    with st.container(border=True):
        st.markdown('<div class="pmra-sub-hdr">Responsável e contatos</div>', unsafe_allow_html=True)
        form["contratante"]["contato_nome"] = st.text_input(
            "Nome do responsável",
            value=form["contratante"]["contato_nome"],
            key="contato_nome_input",
        )

        records_contatos = _render_rows(
            "tbl_contatos",
            {"telefone": "Telefone", "email": "E-mail"},
            help_text="Telefone: (31) 99999-0000 — formatado ao sair do campo.",
            col_widths=[2, 3],
            field_formatters={"telefone": _on_tel_change},
        )
        form["contratante"]["contatos"] = records_contatos


# ── ETAPA 2: ESCOPO E SLA ──────────────────────────────────────────────────────

elif current == 1:
    st.subheader("Escopo da contratação e SLA")

    with st.container(border=True):
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

        if modal in ("consultiva", "mista"):
            st.markdown('<div class="pmra-sub-hdr">Atuação Consultiva</div>', unsafe_allow_html=True)
            form["escopo"]["atuacao_consultiva"] = st.text_area(
                "Áreas, matérias e entregáveis",
                value=form["escopo"]["atuacao_consultiva"],
                height=150,
                key="atuacao_consultiva_ta",
                placeholder="Ex: Consultoria societária, revisão de contratos, pareceres jurídicos.",
            )

        if modal in ("contenciosa", "mista"):
            st.markdown('<div class="pmra-sub-hdr">Atuação Contenciosa</div>', unsafe_allow_html=True)
            form["escopo"]["atuacao_contenciosa"] = st.text_area(
                "Matérias, foros, instâncias e atos processuais",
                value=form["escopo"]["atuacao_contenciosa"],
                height=150,
                key="atuacao_contenciosa_ta",
                placeholder="Ex: Defesa em processos trabalhistas — 1ª e 2ª instância — TRT MG.",
            )

    with st.container(border=True):
        st.markdown('<div class="pmra-sub-hdr">SLA por complexidade</div>', unsafe_allow_html=True)
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

        with st.container(border=True):
            cm = form["honorarios_consultiva"]["modalidades"]
            st.markdown('<div class="pmra-sub-hdr">Modalidades de cobrança — selecione uma ou mais</div>', unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns(4)
            cm["hora_senioridade"] = c1.checkbox("Hora por senioridade", value=cm["hora_senioridade"], key="cons_hs")
            cm["hora_fixa"] = c2.checkbox("Hora Média", value=cm["hora_fixa"], key="cons_hf")
            cm["fixo_mensal"] = c3.checkbox("Fixo Mensal/Cap", value=cm["fixo_mensal"], key="cons_fm")
            cm["valor_projeto"] = c4.checkbox("Preço Global", value=cm["valor_projeto"], key="cons_vp")

            if cm["hora_senioridade"]:
                st.markdown('<div class="pmra-sub-hdr">Tabela de senioridade — consultiva</div>', unsafe_allow_html=True)
                form["honorarios_consultiva"]["tabela_senioridade"] = _render_rows(
                    "tbl_sen_cons",
                    {"categoria": "Categoria", "valor": "Valor por hora"},
                    help_text="Ex: Sócio | R$ 1.050,00",
                    col_widths=[3, 2],
                    field_formatters={"valor": _on_money_change},
                )

            if cm["hora_fixa"]:
                form["honorarios_consultiva"]["hora_fixa_valor"] = st.text_input(
                    "Valor por hora (independente do executor)",
                    value=form["honorarios_consultiva"]["hora_fixa_valor"],
                    placeholder="Ex: R$ 700,00",
                    key="cons_hf_valor",
                    on_change=_on_money_change,
                    args=("cons_hf_valor",),
                )

            if cm["fixo_mensal"]:
                c1, c2, c3 = st.columns(3)
                form["honorarios_consultiva"]["fixo_mensal_valor"] = c1.text_input(
                    "Valor mensal",
                    value=form["honorarios_consultiva"]["fixo_mensal_valor"],
                    placeholder="Ex: R$ 15.000,00",
                    key="cons_fm_valor",
                    on_change=_on_money_change,
                    args=("cons_fm_valor",),
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
                    on_change=_on_money_change,
                    args=("cons_fm_exc",),
                )

            if cm["valor_projeto"]:
                form["honorarios_consultiva"]["valor_projeto_total"] = st.text_input(
                    "Preço global",
                    value=form["honorarios_consultiva"]["valor_projeto_total"],
                    placeholder="Ex: R$ 50.000,00",
                    key="cons_vp_total",
                    on_change=_on_money_change,
                    args=("cons_vp_total",),
                )
                form["honorarios_consultiva"]["valor_projeto_forma_pagamento"] = st.text_area(
                    "Forma de pagamento",
                    value=form["honorarios_consultiva"]["valor_projeto_forma_pagamento"],
                    height=80,
                    key="cons_vp_forma",
                )

    # ── 3b. Contenciosa
    if show_contenciosa:
        st.subheader("Honorários — Atuação Contenciosa")

        with st.container(border=True):
            cm = form["honorarios_contenciosa"]["modalidades"]
            st.markdown('<div class="pmra-sub-hdr">Modalidades de cobrança — selecione uma ou mais</div>', unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns(4)
            cm["valor_acao"] = c1.checkbox("Valor Mensal Por Processo", value=cm["valor_acao"], key="cont_va")
            cm["valor_ato_processual"] = c2.checkbox("Valor por ato processual", value=cm["valor_ato_processual"], key="cont_vap")
            cm["preco_mensal_massa"] = c3.checkbox("Preço mensal", value=cm["preco_mensal_massa"], key="cont_pm")
            cm["valor_projeto"] = c4.checkbox("Preço Global", value=cm["valor_projeto"], key="cont_vp")

            if cm["valor_acao"]:
                st.markdown('<div class="pmra-sub-hdr">Tabela — Valor Mensal Por Processo</div>', unsafe_allow_html=True)
                form["honorarios_contenciosa"]["tabela_acoes"] = _render_rows(
                    "tbl_acoes",
                    {"natureza": "Natureza da ação", "fase": "Fase processual", "valor": "Valor"},
                    help_text="Ex: Trabalhista | Conhecimento | R$ 5.000,00",
                    col_widths=[3, 3, 2],
                    field_formatters={"valor": _on_money_change},
                )

            if cm["valor_ato_processual"]:
                st.markdown('<div class="pmra-sub-hdr">Tabela — Atos Processuais</div>', unsafe_allow_html=True)
                form["honorarios_contenciosa"]["tabela_atos"] = _render_rows(
                    "tbl_atos",
                    {"ato": "Ato processual", "descricao": "Descrição", "valor": "Valor"},
                    help_text="Preencha o valor de cada ato (Ex: R$ 1.500,00). Linhas sem valor são ignoradas.",
                    col_widths=[3, 4, 2],
                    field_formatters={"valor": _on_money_change},
                )

            if cm["preco_mensal_massa"]:
                c1, c2 = st.columns(2)
                form["honorarios_contenciosa"]["preco_mensal_valor"] = c1.text_input(
                    "Valor mensal fixo",
                    value=form["honorarios_contenciosa"]["preco_mensal_valor"],
                    placeholder="Ex: R$ 8.000,00",
                    key="cont_pm_valor",
                    on_change=_on_money_change,
                    args=("cont_pm_valor",),
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
                    "Preço global — contencioso",
                    value=form["honorarios_contenciosa"]["valor_projeto_total"],
                    placeholder="Ex: R$ 30.000,00",
                    key="cont_vp_total",
                    on_change=_on_money_change,
                    args=("cont_vp_total",),
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

        cont_tem_modalidade = any([
            cm["valor_acao"], cm["valor_ato_processual"],
            cm["preco_mensal_massa"], cm["valor_projeto"],
        ])

        if cont_tem_modalidade:
            with st.container(border=True):
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

            with st.container(border=True):
                st.markdown('<div class="pmra-sub-hdr">Horas para serviços extra escopo</div>', unsafe_allow_html=True)
            modos = ("senioridade", "horaFixa")
            form["honorarios_contenciosa"]["horas_extra_escopo_modo"] = st.radio(
                "Modo de cobrança",
                options=modos,
                format_func=lambda x: "Tabela por senioridade" if x == "senioridade" else "Hora Média (valor único)",
                index=modos.index(form["honorarios_contenciosa"]["horas_extra_escopo_modo"]),
                horizontal=True,
                key="horas_extra_modo_radio",
            )
            if form["honorarios_contenciosa"]["horas_extra_escopo_modo"] == "senioridade":
                form["honorarios_contenciosa"]["horas_extra_senioridade"] = _render_rows(
                    "tbl_sen_extra",
                    {"categoria": "Categoria", "valor": "Valor por hora"},
                    help_text="Ex: Sócio | R$ 1.050,00",
                    col_widths=[3, 2],
                    field_formatters={"valor": _on_money_change},
                )
            else:
                form["honorarios_contenciosa"]["horas_extra_valor"] = st.text_input(
                    "Valor por hora — extra escopo",
                    value=form["honorarios_contenciosa"]["horas_extra_valor"],
                    placeholder="Ex: R$ 500,00",
                    key="cont_extra_valor",
                    on_change=_on_money_change,
                    args=("cont_extra_valor",),
                )


# ── ETAPA 4: DESPESAS E DISPOSIÇÕES ───────────────────────────────────────────

elif current == 3:
    st.subheader("Despesas e Disposições Específicas")

    with st.container(border=True):
        st.markdown('<div class="pmra-sub-hdr">Despesas previstas</div>', unsafe_allow_html=True)
        form["despesas"]["tabela_despesas"] = _render_rows(
            "tbl_despesas",
            {"categoria": "Categoria (Ex: Despesas Logísticas)", "descricao": "Descrição"},
            help_text="Adicione ou remova despesas conforme aplicável ao escopo.",
            col_widths=[3, 6],
            text_areas=["categoria", "descricao"],
        )

        st.markdown('<div class="pmra-sub-hdr">Taxa de manutenção processual</div>', unsafe_allow_html=True)
        form["despesas"]["taxa_manutencao_processual"] = st.text_input(
            "Taxa de manutenção processual (deixe vazio para não cobrar)",
            value=form["despesas"]["taxa_manutencao_processual"],
            placeholder="Ex: R$ 50,00 por processo/mês",
            key="desp_taxa_input",
            on_change=_on_money_change,
            args=("desp_taxa_input",),
        )

    with st.container(border=True):
        st.markdown('<div class="pmra-sub-hdr">Disposições específicas</div>', unsafe_allow_html=True)
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

    localidade = f"{cidade}/{uf}" if cidade else "—"
    review_nome = html.escape(nome_cliente or "—")
    review_doc = html.escape(doc_cliente or "—")
    review_localidade = html.escape(localidade)
    review_modal = html.escape(modal.capitalize())
    st.markdown(f"""
<div class="review-grid">
  <div class="review-card">
    <div class="review-label">Contratante</div>
    <div class="review-value">{review_nome}</div>
  </div>
  <div class="review-card">
    <div class="review-label">Documento</div>
    <div class="review-value">{review_doc}</div>
  </div>
  <div class="review-card">
    <div class="review-label">Localidade</div>
    <div class="review-value">{review_localidade}</div>
  </div>
  <div class="review-card">
    <div class="review-label">Modalidade</div>
    <div class="review-value">{review_modal}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    gen_col, dl_col = st.columns([1, 2])

    if gen_col.button("Gerar proposta", type="primary", use_container_width=True):
        try:
            proposal = ProposalForm.model_validate(form)
            context = form_to_context(proposal)
            with st.spinner("Gerando proposta…"):
                st.session_state.generated_doc = render_proposal(context)
            st.success("Proposta gerada com sucesso. Clique em **Baixar .docx** para salvar.")
        except Exception:
            logger.exception("Falha ao gerar proposta")
            st.error(
                "Não foi possível gerar a proposta. Verifique os campos preenchidos "
                "e tente novamente. Se o problema persistir, contate o suporte."
            )

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
_, nav_prev, nav_next, _ = st.columns([2, 1, 1, 2])

if current > 0:
    nav_prev.button(
        "Anterior",
        on_click=_go_prev,
        use_container_width=True,
        key="nav_prev",
    )

if current < len(STEPS) - 1:
    nav_next.button(
        "Próximo →",
        on_click=_go_next,
        type="primary",
        use_container_width=True,
        key="nav_next",
    )

st.markdown("""
<div class="pmra-footer">
    <div class="pmra-footer-left">O nosso negócio é fazer direito</div>
    <div class="pmra-footer-right">PMRA Propostas · v0.1.0</div>
</div>
""", unsafe_allow_html=True)
