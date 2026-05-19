"""Gerador de Propostas PMRA (Streamlit) — formulário em etapas."""
from __future__ import annotations

import html
import logging
import re
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from pmra.auth import check_password
from pmra.data_mapper import form_to_context, _fmt_money as _money_fmt
from pmra.defaults import proposal_form_default
from pmra.schema import (
    HonorariosConsultiva,
    HonorariosContenciosa,
    ProposalForm,
    UF_OPTIONS,
)
from pmra.template_engine import render_proposal

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).parent
APP_VERSION = "2.0.28"


@st.cache_data
def _load_text_asset(relative_path: str) -> str:
    """Le um asset de texto (CSS/SVG) com cache. Reduz overhead em cada rerun."""
    p = _ROOT / relative_path
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _subheader(icon: str, text: str) -> None:
    """Renderiza section header com ícone Material Symbols à esquerda."""
    st.markdown(
        f'<h2 class="pmra-section-hdr">'
        f'<span class="material-symbols-outlined pmra-section-icon">{icon}</span>'
        f'{html.escape(text)}'
        f'</h2>',
        unsafe_allow_html=True,
    )


def _info_note(text: str) -> None:
    """Renderiza nota explicativa com fundo azul claro.

    Substitui st.caption() para mensagens importantes/longas. Mantemos
    st.caption() apenas para hints curtos (ex.: "Ex: Sócio | R$ 1.050,00").
    """
    st.markdown(
        f'<div class="pmra-info-note"><span class="pmra-note-icon">ℹ</span><span>{text}</span></div>',
        unsafe_allow_html=True,
    )


# st.set_page_config DEVE ser o primeiro comando Streamlit — qualquer chamada
# a @st.cache_data ou outras APIs antes dele dispara
# StreamlitSetPageConfigMustBeFirstCommandError.
st.set_page_config(
    page_title="Gerador de Propostas PMRA",
    page_icon="static/pmra-touch-icon.png",
    layout="wide",
)

# Assets cacheados (chamados depois do set_page_config)
_LOGO_SVG = _load_text_asset("pmra-icon.svg")

# Force light mode: limpa preferencia de tema do usuario armazenada localmente
# e seta data-theme=light/light no root. Combinado com [theme] base=light no
# config.toml e [client] toolbarMode=minimal (esconde Settings), garante que
# o app NUNCA renderiza em dark, mesmo se OS/navegador estiver em dark.
# A chave aqui e SET 'light' explicitamente em vez de so limpar — sem
# preferencia salva, Streamlit cai no OS, que pode ser dark.
components.html("""
<script>
(function() {
  try {
    var parentWin = window.parent;
    var parentDoc = parentWin.document;

    // Tenta SET 'light' em chaves conhecidas de tema do Streamlit + limpa
    // qualquer outra que possa indicar dark mode armazenado
    try {
      var ls = parentWin.localStorage;
      // Set explicito light em chaves comuns que o Streamlit usa
      ls.setItem('stTheme', 'light');
      // Limpa qualquer outra chave de tema que possa estar conflitando
      for (var i = ls.length - 1; i >= 0; i--) {
        var k = ls.key(i);
        if (k && k !== 'stTheme' && (
            k.toLowerCase().indexOf('darkmode') >= 0 ||
            k.toLowerCase().indexOf('color-scheme') >= 0
        )) { ls.removeItem(k); }
      }
    } catch(e) {}

    // Forca color-scheme=light + data-theme=light no root
    function applyLight() {
      var html = parentDoc.documentElement;
      if (html) {
        html.style.colorScheme = 'light';
        html.setAttribute('data-theme', 'light');
      }
      if (parentDoc.body) {
        parentDoc.body.style.colorScheme = 'light';
      }
    }
    applyLight();

    // Reaplica se algo mudar (caso Streamlit tente re-setar dark)
    if (parentDoc.documentElement) {
      new parentWin.MutationObserver(applyLight).observe(
        parentDoc.documentElement,
        {attributes: true, attributeFilter: ['data-theme', 'class', 'style']}
      );
    }
  } catch(e) { console.warn('force-light failed:', e); }
})();
</script>
""", height=0)

if not check_password():
    st.stop()

# ── Estilos PMRA ───────────────────────────────────────────────────────────────

st.markdown(f"<style>{_load_text_asset('resources/static/styles.css')}</style>", unsafe_allow_html=True)

# Injeta apple-touch-icon no <head> para atalhos na tela inicial do celular
components.html("""
<script>
(function() {
  var d = window.parent.document;
  if (d.querySelector('link[rel="apple-touch-icon"]')) return;
  ['180x180', '192x192'].forEach(function(s) {
    var l = d.createElement('link');
    l.rel = 'apple-touch-icon';
    l.sizes = s;
    l.href = '/app/static/pmra-touch-icon.png';
    d.head.appendChild(l);
  });
})();
</script>
""", height=0)


# ── Máscara em tempo real (JS via iframe) ──────────────────────────────────────
# Esta funcao injeta um iframe com JS que aplica masks em tempo real nos campos
# do Step 0 (CPF/CNPJ/CEP/telefone). Sera chamada CONDICIONALMENTE so quando
# current == 0, para evitar overhead de ~50-100ms por rerun em outras etapas.

def _inject_input_masks() -> None:
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
    "Escopo",
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

    # Migracao para sessoes legadas: se form existe mas algum default novo
    # foi adicionado posteriormente (como sla_descricao), preenche com o
    # valor do default atual quando esta vazio. Garante que usuarios em
    # sessoes pre-deploy recebam os defaults novos automaticamente.
    if not st.session_state.form["escopo"].get("sla_descricao"):
        st.session_state.form["escopo"]["sla_descricao"] = defaults["escopo"]["sla_descricao"]
    _esc = st.session_state.form["escopo"]
    for _field, _default in (
        ("escopos_consultivos", []),
        ("escopos_contenciosos", []),
        ("forma_pagamento_por_escopo_consultiva", False),
        ("forma_pagamento_por_escopo_contenciosa", False),
    ):
        if _field not in _esc:
            _esc[_field] = _default

    f = st.session_state.form

    # Sync widget state com form para inputs que usam on_change callback.
    # Como esses widgets nao podem ter value= juntos com key= + callback
    # (Streamlit avisa do conflito), pre-populamos session_state aqui e o
    # widget usa apenas key=, sem value=. Apos cada interacao o callback
    # atualiza session_state[key] (formatado), que vira o valor do form.
    _INPUT_FORM_PATHS = (
        ("cpf_input",       ("contratante", "cpf")),
        ("cnpj_input",      ("contratante", "cnpj")),
        ("cep_input",       ("contratante", "endereco", "cep")),
        ("cons_hf_valor",   ("honorarios_consultiva", "hora_fixa_valor")),
        ("cons_fm_valor",   ("honorarios_consultiva", "fixo_mensal_valor")),
        ("cons_fm_exc",     ("honorarios_consultiva", "fixo_mensal_excedente")),
        ("cons_vp_total",   ("honorarios_consultiva", "valor_projeto_total")),
        ("cons_vp_cap",     ("honorarios_consultiva", "valor_projeto_cap")),
        ("cont_pm_valor",   ("honorarios_contenciosa", "preco_mensal_valor")),
        ("cont_vp_total",   ("honorarios_contenciosa", "valor_projeto_total")),
        ("cont_extra_valor",("honorarios_contenciosa", "horas_extra_valor")),
        ("desp_taxa_input", ("despesas", "taxa_manutencao_processual")),
    )
    for widget_key, path in _INPUT_FORM_PATHS:
        if widget_key not in st.session_state:
            v = f
            for p in path:
                v = v[p]
            st.session_state[widget_key] = v

    # ── REGRA OBRIGATÓRIA PARA TODO NOVO CHECKBOX ─────────────────────────────
    # Passar `value=` + `key=` juntos num st.checkbox causa lag/duplo-render:
    # o Streamlit trata o segundo clique como reset em vez de toggle.
    #
    # PADRÃO CORRETO — dois passos:
    #   1. Adicione a entrada aqui em _BOOL_FORM_PATHS:
    #        ("minha_key", ("caminho", "no", "form"))
    #   2. No widget, use APENAS `key=`, SEM `value=`:
    #        form["x"]["y"] = st.checkbox("Label", key="minha_key")
    #
    # NÃO FAÇA: st.checkbox("Label", value=form["x"]["y"], key="minha_key")
    # ──────────────────────────────────────────────────────────────────────────
    _BOOL_FORM_PATHS = (
        ("cons_hs",            ("honorarios_consultiva", "modalidades", "hora_senioridade")),
        ("cons_hf",            ("honorarios_consultiva", "modalidades", "hora_fixa")),
        ("cons_fm",            ("honorarios_consultiva", "modalidades", "fixo_mensal")),
        ("cons_vp",            ("honorarios_consultiva", "modalidades", "valor_projeto")),
        ("cont_va",            ("honorarios_contenciosa", "modalidades", "valor_acao")),
        ("cont_vap",           ("honorarios_contenciosa", "modalidades", "valor_ato_processual")),
        ("cont_pm",            ("honorarios_contenciosa", "modalidades", "preco_mensal_massa")),
        ("cont_vp",            ("honorarios_contenciosa", "modalidades", "valor_projeto")),
        ("cont_exito_cb",      ("honorarios_contenciosa", "exito_ativo")),
        ("cons_vp_cap_ativo",  ("honorarios_consultiva",  "valor_projeto_cap_ativo")),
        ("desp_taxa_ativa_cb", ("despesas", "taxa_manutencao_ativa")),
        ("sla_ativo_cb",       ("escopo", "sla_ativo")),
        ("disp_ativo_cb",      ("disposicoes", "ativo")),
    )
    for widget_key, path in _BOOL_FORM_PATHS:
        if widget_key not in st.session_state:
            v = f
            for p in path:
                v = v[p]
            st.session_state[widget_key] = bool(v)

    # Radios: o `key=` armazena a STRING da opção selecionada
    _RADIO_FORM_PATHS = (
        ("tipo_pessoa",            ("contratante", "tipo_pessoa")),
        ("modalidade_radio",       ("escopo", "modalidade")),
        ("horas_extra_modo_radio", ("honorarios_contenciosa", "horas_extra_escopo_modo")),
    )
    for widget_key, path in _RADIO_FORM_PATHS:
        if widget_key not in st.session_state:
            v = f
            for p in path:
                v = v[p]
            st.session_state[widget_key] = v

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

# (As injeções de iframe — input masks, scroll-to-top, sticky stepper —
# foram movidas para o FINAL deste arquivo, depois do footer. Cada iframe
# components.html ocupa ~26px no fluxo do DOM mesmo com height=0; se eles
# fossem injetados aqui ANTES do header, empurrariam todo o layout para
# baixo de forma inconsistente entre etapas — a etapa Contratante usa
# 1 iframe a mais (input masks), causando offset visível.)


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
        # Etapas futuras tambem clicaveis — usuario pode pular livre entre secoes.
        col.button(
            f"○ {name}",
            key=f"step_btn_{i}",
            use_container_width=True,
            on_click=_go_to,
            args=(i,),
        )

# (divider removido: sticky stepper ja tem border-bottom; evita gap vertical
# excessivo entre menu de etapas e conteudo)


# ── Constantes e helpers para múltiplos escopos ───────────────────────────────

_LETRAS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def _hon_cons_default() -> dict:
    return HonorariosConsultiva().model_dump()


def _hon_cont_default() -> dict:
    return HonorariosContenciosa().model_dump()


def _reletrar(lst: list[dict]) -> None:
    for i, item in enumerate(lst):
        item["letra"] = _LETRAS[i]


def _clear_escopo_widget_keys(prefix: str) -> None:
    for k in list(st.session_state.keys()):
        if k.startswith(prefix):
            del st.session_state[k]


def _to_multi_cons_cb() -> None:
    form = st.session_state.form
    texto = form["escopo"]["atuacao_consultiva"]
    form["escopo"]["escopos_consultivos"] = [
        {"letra": "A", "descricao": texto, "honorarios": _hon_cons_default()},
        {"letra": "B", "descricao": "", "honorarios": _hon_cons_default()},
    ]


def _add_escopo_cons_cb() -> None:
    form = st.session_state.form
    lst = form["escopo"]["escopos_consultivos"]
    lst.append({"letra": _LETRAS[len(lst)], "descricao": "", "honorarios": _hon_cons_default()})
    _reletrar(lst)


def _del_escopo_cons_cb(idx: int) -> None:
    _clear_escopo_widget_keys("escopo_cons_desc_")
    _clear_escopo_widget_keys("cons_")
    form = st.session_state.form
    lst = form["escopo"]["escopos_consultivos"]
    lst.pop(idx)
    if len(lst) == 1:
        form["escopo"]["atuacao_consultiva"] = lst[0]["descricao"]
        form["escopo"]["forma_pagamento_por_escopo_consultiva"] = False
        lst.clear()
    else:
        _reletrar(lst)


def _to_multi_cont_cb() -> None:
    form = st.session_state.form
    texto = form["escopo"]["atuacao_contenciosa"]
    form["escopo"]["escopos_contenciosos"] = [
        {"letra": "A", "descricao": texto, "honorarios": _hon_cont_default()},
        {"letra": "B", "descricao": "", "honorarios": _hon_cont_default()},
    ]


def _add_escopo_cont_cb() -> None:
    form = st.session_state.form
    lst = form["escopo"]["escopos_contenciosos"]
    lst.append({"letra": _LETRAS[len(lst)], "descricao": "", "honorarios": _hon_cont_default()})
    _reletrar(lst)


def _del_escopo_cont_cb(idx: int) -> None:
    _clear_escopo_widget_keys("escopo_cont_desc_")
    _clear_escopo_widget_keys("cont_")
    form = st.session_state.form
    lst = form["escopo"]["escopos_contenciosos"]
    lst.pop(idx)
    if len(lst) == 1:
        form["escopo"]["atuacao_contenciosa"] = lst[0]["descricao"]
        form["escopo"]["forma_pagamento_por_escopo_contenciosa"] = False
        lst.clear()
    else:
        _reletrar(lst)


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
    placeholders: dict[str, str] | None = None,
) -> list[dict]:
    """Renderiza tabela como linhas de inputs individuais com botão ✕ por linha.

    field_formatters: mapa campo → função que recebe o widget_key e formata
    o valor em session_state (chamada via on_change).
    placeholders: mapa campo → texto placeholder (aparece quando input vazio,
    serve de hint do conteudo esperado em mobile onde os headers somem).
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

    # Header compartilhado: um label .pmra-tbl-hdr por coluna no topo da tabela.
    # Cada input usa label_visibility="collapsed" — sem duplicacao no desktop e
    # alinhamento natural do X (todas colunas tem mesma altura).
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
            ph = (placeholders or {}).get(field, "")
            # Quando tem on_change callback que escreve em session_state[wk],
            # nao pode passar value= junto (Streamlit avisa). Pre-popula
            # session_state e cria widget so com key=.
            if fmt_fn is not None:
                if wk not in st.session_state:
                    st.session_state[wk] = row.get(field, "")
                if field in text_areas_list:
                    row_cols[j].text_area(
                        labels[j], key=wk, label_visibility="collapsed",
                        on_change=fmt_fn, args=(wk,), placeholder=ph,
                    )
                else:
                    row_cols[j].text_input(
                        labels[j], key=wk, label_visibility="collapsed",
                        on_change=fmt_fn, args=(wk,), placeholder=ph,
                    )
            else:
                if field in text_areas_list:
                    row_cols[j].text_area(
                        labels[j], value=row.get(field, ""), key=wk,
                        label_visibility="collapsed", placeholder=ph,
                    )
                else:
                    row_cols[j].text_input(
                        labels[j], value=row.get(field, ""), key=wk,
                        label_visibility="collapsed", placeholder=ph,
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


# ── Helpers de renderização de honorários (reutilizados em modo multi-escopo) ──

def _render_honorarios_consultiva(hon: dict, prefix: str) -> None:
    """Renderiza modalidades de honorários consultivos com widget keys prefixadas.

    hon: dict no formato form["honorarios_consultiva"] ou item["honorarios"].
    prefix: "cons" para modo único, "cons_0"/"cons_1"... para multi.
    """
    cm = hon["modalidades"]

    # Pré-popula booleans (padrão key-only para evitar duplo-render em checkboxes)
    for key, src, field in (
        (f"{prefix}_hs",          cm,  "hora_senioridade"),
        (f"{prefix}_hf",          cm,  "hora_fixa"),
        (f"{prefix}_fm",          cm,  "fixo_mensal"),
        (f"{prefix}_vp",          cm,  "valor_projeto"),
        (f"{prefix}_vp_cap_ativo", hon, "valor_projeto_cap_ativo"),
    ):
        if key not in st.session_state:
            st.session_state[key] = bool(src.get(field, False))

    # Pré-popula inputs com on_change
    for key, field in (
        (f"{prefix}_hf_valor", "hora_fixa_valor"),
        (f"{prefix}_fm_valor", "fixo_mensal_valor"),
        (f"{prefix}_fm_exc",   "fixo_mensal_excedente"),
        (f"{prefix}_vp_total", "valor_projeto_total"),
    ):
        if key not in st.session_state:
            st.session_state[key] = hon.get(field, "")

    st.markdown(
        '<div class="pmra-sub-hdr"><span class="material-symbols-outlined pmra-icon">tune</span>'
        "Modalidades de cobrança — selecione uma ou mais</div>",
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns(4)
    cm["hora_senioridade"] = c1.checkbox("Hora por senioridade", key=f"{prefix}_hs")
    cm["hora_fixa"]        = c2.checkbox("Hora Média",           key=f"{prefix}_hf")
    cm["fixo_mensal"]      = c3.checkbox("Fixo Mensal/Cap",      key=f"{prefix}_fm")
    cm["valor_projeto"]    = c4.checkbox("Preço Global",         key=f"{prefix}_vp")

    if cm["hora_senioridade"]:
        st.markdown(
            '<div class="pmra-sub-hdr"><span class="material-symbols-outlined pmra-icon">table_chart</span>'
            "Tabela de senioridade — consultiva</div>",
            unsafe_allow_html=True,
        )
        hon["tabela_senioridade"] = _render_rows(
            f"tbl_sen_{prefix}",
            {"categoria": "Categoria", "valor": "Valor por hora"},
            help_text="Ex: Sócio | R$ 1.050,00",
            col_widths=[3, 2],
            field_formatters={"valor": _on_money_change},
            placeholders={"categoria": "Categoria", "valor": "R$ 0,00"},
        )

    if cm["hora_fixa"]:
        hon["hora_fixa_valor"] = st.text_input(
            "Valor por hora (independente do executor)",
            placeholder="Ex: R$ 700,00",
            key=f"{prefix}_hf_valor",
            on_change=_on_money_change,
            args=(f"{prefix}_hf_valor",),
        )

    if cm["fixo_mensal"]:
        c1, c2, c3 = st.columns(3)
        hon["fixo_mensal_valor"] = c1.text_input(
            "Valor mensal",
            placeholder="Ex: R$ 15.000,00",
            key=f"{prefix}_fm_valor",
            on_change=_on_money_change,
            args=(f"{prefix}_fm_valor",),
        )
        hon["fixo_mensal_cap"] = c2.text_input(
            "Cap de horas inclusas",
            value=hon.get("fixo_mensal_cap", ""),
            placeholder="Ex: 30 horas",
            key=f"{prefix}_fm_cap",
        )
        hon["fixo_mensal_excedente"] = c3.text_input(
            "Hora excedente",
            placeholder="Ex: R$ 600,00",
            key=f"{prefix}_fm_exc",
            on_change=_on_money_change,
            args=(f"{prefix}_fm_exc",),
        )

    if cm["valor_projeto"]:
        hon["valor_projeto_total"] = st.text_input(
            "Preço global",
            placeholder="Ex: R$ 50.000,00",
            key=f"{prefix}_vp_total",
            on_change=_on_money_change,
            args=(f"{prefix}_vp_total",),
        )
        hon["valor_projeto_cap_ativo"] = st.checkbox(
            "Incluir cap de horas?",
            key=f"{prefix}_vp_cap_ativo",
        )
        if hon["valor_projeto_cap_ativo"]:
            hon["valor_projeto_cap"] = st.text_input(
                "Cap de horas",
                value=hon.get("valor_projeto_cap", ""),
                placeholder="Ex: 40",
                key=f"{prefix}_vp_cap",
            )
        hon["valor_projeto_forma_pagamento"] = st.text_area(
            "Forma ou prazos de pagamento",
            value=hon.get("valor_projeto_forma_pagamento", ""),
            height=80,
            key=f"{prefix}_vp_forma",
            placeholder="Ex: 50% no ato da assinatura da proposta e 50% ao final, parcelas mensais etc.",
        )


def _render_honorarios_contenciosa_modalidades(hon: dict, prefix: str) -> None:
    """Renderiza apenas as modalidades de honorários contenciosos (sem êxito/horas extra).

    hon: dict no formato form["honorarios_contenciosa"] ou item["honorarios"].
    prefix: "cont" para modo único, "cont_0"/"cont_1"... para multi.
    """
    cm = hon["modalidades"]

    for key, field in (
        (f"{prefix}_va",  "valor_acao"),
        (f"{prefix}_vap", "valor_ato_processual"),
        (f"{prefix}_pm",  "preco_mensal_massa"),
        (f"{prefix}_vp",  "valor_projeto"),
    ):
        if key not in st.session_state:
            st.session_state[key] = bool(cm.get(field, False))

    for key, field in (
        (f"{prefix}_pm_valor",   "preco_mensal_valor"),
        (f"{prefix}_vp_total",   "valor_projeto_total"),
    ):
        if key not in st.session_state:
            st.session_state[key] = hon.get(field, "")

    st.markdown(
        '<div class="pmra-sub-hdr"><span class="material-symbols-outlined pmra-icon">tune</span>'
        "Modalidades de cobrança — selecione uma ou mais</div>",
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns(4)
    cm["valor_acao"]            = c1.checkbox("Valor Mensal Por Processo",  key=f"{prefix}_va")
    cm["valor_ato_processual"]  = c2.checkbox("Valor por ato processual",   key=f"{prefix}_vap")
    cm["preco_mensal_massa"]    = c3.checkbox("Preço mensal",               key=f"{prefix}_pm")
    cm["valor_projeto"]         = c4.checkbox("Preço Global",               key=f"{prefix}_vp")

    if cm["valor_acao"]:
        st.markdown(
            '<div class="pmra-sub-hdr"><span class="material-symbols-outlined pmra-icon">table_chart</span>'
            "Tabela — Valor Mensal Por Processo</div>",
            unsafe_allow_html=True,
        )
        hon["tabela_acoes"] = _render_rows(
            f"tbl_acoes_{prefix}",
            {"natureza": "Natureza da ação", "fase": "Instâncias de Atuação", "valor": "Valor"},
            help_text="Ex: Trabalhista | Conhecimento | R$ 5.000,00",
            col_widths=[3, 3, 2],
            field_formatters={"valor": _on_money_change},
            placeholders={"natureza": "Natureza da ação", "fase": "Preencher", "valor": "R$ 0,00"},
        )

    if cm["valor_ato_processual"]:
        st.markdown(
            '<div class="pmra-sub-hdr"><span class="material-symbols-outlined pmra-icon">gavel</span>'
            "Tabela — Atos Processuais</div>",
            unsafe_allow_html=True,
        )
        _info_note(
            "Preencha o valor de cada ato (Ex: R$ 1.500,00). "
            "Linhas sem valor são ignoradas. Use o X para remover "
            "atos não aplicáveis ou acrescente novos ao seu critério."
        )
        hon["tabela_atos"] = _render_rows(
            f"tbl_atos_{prefix}",
            {"ato": "Ato processual", "descricao": "Descrição", "valor": "Valor"},
            help_text="",
            col_widths=[3, 4, 2],
            field_formatters={"valor": _on_money_change},
            placeholders={"ato": "Ato processual", "descricao": "Descrição", "valor": "R$ 0,00"},
        )

    if cm["preco_mensal_massa"]:
        c1, c2 = st.columns(2)
        hon["preco_mensal_valor"] = c1.text_input(
            "Valor mensal fixo",
            placeholder="Ex: R$ 8.000,00",
            key=f"{prefix}_pm_valor",
            on_change=_on_money_change,
            args=(f"{prefix}_pm_valor",),
        )
        hon["preco_mensal_maximo_acoes"] = c2.text_input(
            "Nº máximo de ações cobertas",
            value=hon.get("preco_mensal_maximo_acoes", ""),
            placeholder="Ex: 20",
            key=f"{prefix}_pm_max",
        )
        hon["preco_mensal_maximo_acoes_extenso"] = st.text_input(
            "Nº máximo por extenso",
            value=hon.get("preco_mensal_maximo_acoes_extenso", ""),
            placeholder="Ex: vinte",
            key=f"{prefix}_pm_max_ext",
        )
        hon["preco_mensal_criterio_excedentes"] = st.text_area(
            "Critério para ações excedentes",
            value=hon.get("preco_mensal_criterio_excedentes", ""),
            height=80,
            key=f"{prefix}_pm_crit",
        )

    if cm["valor_projeto"]:
        hon["valor_projeto_total"] = st.text_input(
            "Preço global — contencioso",
            placeholder="Ex: R$ 30.000,00",
            key=f"{prefix}_vp_total",
            on_change=_on_money_change,
            args=(f"{prefix}_vp_total",),
        )
        hon["valor_projeto_fases_cobertas"] = st.text_area(
            "Ações e fases cobertas",
            value=hon.get("valor_projeto_fases_cobertas", ""),
            height=80,
            key=f"{prefix}_vp_fases",
        )
        hon["valor_projeto_forma_pagamento"] = st.text_area(
            "Forma ou prazos de pagamento",
            value=hon.get("valor_projeto_forma_pagamento", ""),
            height=80,
            key=f"{prefix}_vp_forma",
            placeholder="Ex: 50% no ato da assinatura da proposta e 50% ao final, parcelas mensais etc.",
        )


def _step_honorarios() -> None:
    """Etapa 3 — Honorarios.

    NAO usar @st.fragment aqui: ao navegar entre etapas o fragment desmonta
    e widget keys podem perder vinculo com session_state, fazendo checkboxes
    aparecerem desmarcados ao voltar. Estado persistente e mais importante
    que o ganho marginal de performance do fragment.
    """
    form = st.session_state.form
    modal = form["escopo"]["modalidade"]
    show_consultiva = modal in ("consultiva", "mista")
    show_contenciosa = modal in ("contenciosa", "mista")

    # Defesa em camadas: se nao ha modalidade contenciosa, taxa de manutencao
    # processual (que foi movida para esta secao) nao se aplica.
    if not show_contenciosa:
        form["despesas"]["taxa_manutencao_ativa"] = False
        form["despesas"]["taxa_manutencao_processual"] = ""

    # ── 3a. Consultiva
    if show_consultiva:
        escopos_cons = form["escopo"]["escopos_consultivos"]
        multi_cons = len(escopos_cons) >= 2

        _subheader("payments", "Honorários — Atuação Consultiva")

        if multi_cons:
            if "fpce_cons" not in st.session_state:
                st.session_state["fpce_cons"] = form["escopo"]["forma_pagamento_por_escopo_consultiva"]
            forma_por_escopo_cons = st.checkbox(
                "Cada escopo consultivo terá sua própria forma de pagamento?",
                key="fpce_cons",
            )
            form["escopo"]["forma_pagamento_por_escopo_consultiva"] = forma_por_escopo_cons

            if forma_por_escopo_cons:
                for i, item in enumerate(escopos_cons):
                    _subheader("payments", f"Honorários — Escopo Consultivo {item['letra']}")
                    with st.container(border=True):
                        _render_honorarios_consultiva(item["honorarios"], f"cons_{i}")
            else:
                with st.container(border=True):
                    _render_honorarios_consultiva(form["honorarios_consultiva"], "cons")
        else:
            with st.container(border=True):
                _render_honorarios_consultiva(form["honorarios_consultiva"], "cons")

    # ── 3b. Contenciosa
    if show_contenciosa:
        escopos_cont = form["escopo"]["escopos_contenciosos"]
        multi_cont = len(escopos_cont) >= 2

        _subheader("gavel", "Honorários — Atuação Contenciosa")

        if multi_cont:
            if "fpce_cont" not in st.session_state:
                st.session_state["fpce_cont"] = form["escopo"]["forma_pagamento_por_escopo_contenciosa"]
            forma_por_escopo_cont = st.checkbox(
                "Cada escopo contencioso terá sua própria forma de pagamento?",
                key="fpce_cont",
            )
            form["escopo"]["forma_pagamento_por_escopo_contenciosa"] = forma_por_escopo_cont

            if forma_por_escopo_cont:
                for i, item in enumerate(escopos_cont):
                    _subheader("gavel", f"Honorários — Escopo Contencioso {item['letra']}")
                    with st.container(border=True):
                        _render_honorarios_contenciosa_modalidades(item["honorarios"], f"cont_{i}")
                cont_tem_modalidade = any(
                    any(v for v in item["honorarios"]["modalidades"].values())
                    for item in escopos_cont
                )
            else:
                with st.container(border=True):
                    _render_honorarios_contenciosa_modalidades(form["honorarios_contenciosa"], "cont")
                cm = form["honorarios_contenciosa"]["modalidades"]
                cont_tem_modalidade = any([
                    cm["valor_acao"], cm["valor_ato_processual"],
                    cm["preco_mensal_massa"], cm["valor_projeto"],
                ])
        else:
            with st.container(border=True):
                _render_honorarios_contenciosa_modalidades(form["honorarios_contenciosa"], "cont")
            cm = form["honorarios_contenciosa"]["modalidades"]
            cont_tem_modalidade = any([
                cm["valor_acao"], cm["valor_ato_processual"],
                cm["preco_mensal_massa"], cm["valor_projeto"],
            ])

        if cont_tem_modalidade:
            with st.container(border=True):
                form["honorarios_contenciosa"]["exito_ativo"] = st.checkbox(
                    "Cobrar honorários de êxito?",
                    key="cont_exito_cb",
                )
                if form["honorarios_contenciosa"]["exito_ativo"]:
                    _pct_raw = form["honorarios_contenciosa"]["exito_percentual"]
                    _pct_val = int(_pct_raw) if str(_pct_raw).strip().rstrip("%").isdigit() else None
                    _pct_input = st.number_input(
                        "Percentual de êxito",
                        min_value=1,
                        max_value=100,
                        value=_pct_val,
                        step=1,
                        placeholder="Ex: 10",
                        key="cont_exito_pct",
                    )
                    form["honorarios_contenciosa"]["exito_percentual"] = str(_pct_input) if _pct_input is not None else ""

                # Taxa de manutencao processual — checkbox com a mesma logica do Exito
                form["despesas"]["taxa_manutencao_ativa"] = st.checkbox(
                    "Cobrar taxa de manutenção processual?",
                    key="desp_taxa_ativa_cb",
                )
                if form["despesas"]["taxa_manutencao_ativa"]:
                    form["despesas"]["taxa_manutencao_processual"] = st.text_input(
                        "Valor da taxa",
                        placeholder="Ex: R$ 50,00 por processo/mês",
                        key="desp_taxa_input",
                        on_change=_on_money_change,
                        args=("desp_taxa_input",),
                    )
                else:
                    # Zera o valor quando desativado para nao vazar para o documento
                    form["despesas"]["taxa_manutencao_processual"] = ""

            # Horas para servicos extra escopo sempre aparece quando ha
            # modalidade contenciosa. Em proposta mista, mesmo que ja exista
            # valor de hora na consultiva, e necessario definir separadamente
            # para o escopo contencioso porque consultivo e contencioso sao
            # tratados como escopos independentes no documento final.
            with st.container(border=True):
                st.markdown('<div class="pmra-sub-hdr"><span class="material-symbols-outlined pmra-icon">schedule</span>Horas para serviços extra escopo</div>', unsafe_allow_html=True)
                _info_note("Obrigatório inserir ao menos uma das modalidades para serviços excedentes.")
                modos = ("senioridade", "horaFixa")
                form["honorarios_contenciosa"]["horas_extra_escopo_modo"] = st.radio(
                    "Modo de cobrança",
                    options=modos,
                    format_func=lambda x: "Tabela por senioridade" if x == "senioridade" else "Hora Média (valor único)",
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
                        placeholders={"categoria": "Categoria", "valor": "R$ 0,00"},
                    )
                else:
                    form["honorarios_contenciosa"]["horas_extra_valor"] = st.text_input(
                        "Valor por hora — extra escopo",
                        placeholder="Ex: R$ 500,00",
                        key="cont_extra_valor",
                        on_change=_on_money_change,
                        args=("cont_extra_valor",),
                    )
        else:
            # Sem modalidade contenciosa selecionada — Taxa de manutencao tambem nao
            # se aplica.
            form["despesas"]["taxa_manutencao_ativa"] = False
            form["despesas"]["taxa_manutencao_processual"] = ""


    # ── ETAPA 4: DESPESAS E DISPOSIÇÕES ───────────────────────────────────────────



# ── ETAPA 1: CONTRATANTE ───────────────────────────────────────────────────────

if current == 0:
    _subheader("manage_accounts", "Identificação do contratante")

    _info_note(
        "Todos os campos são opcionais. Caso algum campo não seja preenchido, "
        "ele não será exibido no documento final e o ajuste deverá ser manual. "
        "Sempre que possível, emita a proposta com todos os campos necessários "
        "preenchidos, em especial os campos de identificação do "
        "Contratante/Cliente, para facilitar as rotinas de Fluxo Comercial e "
        "Cadastro pelo time Financeiro do PMRA."
    )

    with st.container(border=True):
        st.markdown('<div class="pmra-sub-hdr"><span class="material-symbols-outlined pmra-icon">badge</span>Identificação</div>', unsafe_allow_html=True)
        form["contratante"]["tipo_pessoa"] = st.radio(
            "Tipo de pessoa",
            options=("fisica", "juridica"),
            format_func=lambda x: "Pessoa Física" if x == "fisica" else "Pessoa Jurídica",
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
                placeholder="00.000.000/0000-00",
                key="cnpj_input",
                on_change=_on_cnpj_change,
            )

    with st.container(border=True):
        st.markdown('<div class="pmra-sub-hdr"><span class="material-symbols-outlined pmra-icon">location_on</span>Endereço</div>', unsafe_allow_html=True)
        end = form["contratante"]["endereco"]

        c1, c2 = st.columns([3, 1])
        end["logradouro"] = c1.text_input("Logradouro", value=end["logradouro"], key="logradouro_input")
        end["numero"] = c2.text_input("Número/Complemento", value=end["numero"], key="numero_input")

        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
        end["bairro"] = c1.text_input("Bairro", value=end["bairro"], key="bairro_input")
        end["cep"] = c2.text_input("CEP", placeholder="00000-000", key="cep_input", on_change=_on_cep_change)
        end["cidade"] = c3.text_input("Cidade", value=end["cidade"], key="cidade_input")
        end["uf"] = c4.selectbox(
            "UF",
            options=UF_OPTIONS,
            index=UF_OPTIONS.index(end["uf"]) if end["uf"] in UF_OPTIONS else 0,
            key="uf_input",
        )

    with st.container(border=True):
        st.markdown('<div class="pmra-sub-hdr"><span class="material-symbols-outlined pmra-icon">contact_phone</span>Responsável e contatos</div>', unsafe_allow_html=True)
        form["contratante"]["contato_nome"] = st.text_input(
            "Nome do responsável",
            value=form["contratante"]["contato_nome"],
            key="contato_nome_input",
        )

        records_contatos = _render_rows(
            "tbl_contatos",
            {"telefone": "Telefone", "email": "E-mail"},
            col_widths=[2, 3],
            field_formatters={"telefone": _on_tel_change},
            placeholders={
                "telefone": "(31) 99999-0000",
                "email": "nome@empresa.com.br",
            },
        )
        form["contratante"]["contatos"] = records_contatos


# ── ETAPA 2: ESCOPO ───────────────────────────────────────────────────────────

elif current == 1:
    _subheader("description", "Escopo da contratação")

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
            horizontal=True,
            key="modalidade_radio",
        )

        modal = form["escopo"]["modalidade"]

        _NOTE_COMBINED = (
            "Escreva da forma como deverá constar na proposta. Assim, se o "
            "objeto contiver múltiplas etapas, fases, etc., a forma como "
            "preencher será visualizada no documento final. Você poderá "
            "fazer alterações e editar a formatação no Word manualmente "
            "após gerada a proposta, caso necessário. Caso a proposta tenha "
            "múltiplos escopos com formas de pagamento distintas, crie nova "
            "linha e insira a forma de pagamento adequada na próxima página, "
            "de forma que a forma de pagamento seja adequada ao escopo."
        )
        _info_note(_NOTE_COMBINED)

        if modal in ("consultiva", "mista"):
            st.markdown('<div class="pmra-sub-hdr"><span class="material-symbols-outlined pmra-icon">article</span>Atuação Consultiva</div>', unsafe_allow_html=True)

            escopos_cons = form["escopo"]["escopos_consultivos"]
            if escopos_cons:
                for i, item in enumerate(escopos_cons):
                    col_hdr, col_del = st.columns([11, 1])
                    col_hdr.markdown(
                        f'<div class="pmra-sub-hdr" style="margin-top:8px">'
                        f'<span class="material-symbols-outlined pmra-icon">article</span>'
                        f'Escopo {item["letra"]}</div>',
                        unsafe_allow_html=True,
                    )
                    col_del.button(
                        "✕",
                        key=f"escopo_cons_del_{i}",
                        on_click=_del_escopo_cons_cb,
                        args=(i,),
                        help="Remover escopo",
                        use_container_width=True,
                    )
                    desc_key = f"escopo_cons_desc_{i}"
                    if desc_key not in st.session_state:
                        st.session_state[desc_key] = item["descricao"]
                    st.text_area(
                        "Áreas, matérias e entregáveis",
                        height=150,
                        key=desc_key,
                        placeholder="Ex: Consultoria societária, revisão de contratos, pareceres jurídicos.",
                        label_visibility="collapsed",
                    )
                    escopos_cons[i]["descricao"] = st.session_state[desc_key]

                st.button(
                    "+ Adicionar escopo consultivo",
                    key="escopo_cons_add",
                    on_click=_add_escopo_cons_cb,
                )
            else:
                form["escopo"]["atuacao_consultiva"] = st.text_area(
                    "Áreas, matérias e entregáveis",
                    value=form["escopo"]["atuacao_consultiva"],
                    height=150,
                    key="atuacao_consultiva_ta",
                    placeholder="Ex: Consultoria societária, revisão de contratos, pareceres jurídicos.",
                )
                st.button(
                    "+ Adicionar segundo escopo consultivo",
                    key="escopo_cons_to_multi",
                    on_click=_to_multi_cons_cb,
                )

            # SLA aparece logo abaixo de Atuacao Consultiva (so faz sentido em escopo
            # consultivo ou misto). Quando contenciosa, este bloco nao renderiza e
            # o else abaixo zera os campos.
            st.markdown('<div class="pmra-sub-hdr"><span class="material-symbols-outlined pmra-icon">timer</span>SLA por Complexidade/Prazos de Entrega</div>', unsafe_allow_html=True)
            form["escopo"]["sla_ativo"] = st.checkbox(
                "Definir prazos de resposta por complexidade?",
                key="sla_ativo_cb",
            )
            if form["escopo"]["sla_ativo"]:
                _info_note(
                    "Abaixo a sugestão de SLA/Prazos de Atendimento pré-preenchido. "
                    "Ajuste conforme a necessidade da área ou conforme acordado com "
                    "o Cliente. Em caso de múltiplos escopos com SLA/Prazos de "
                    "Atendimento diferentes para cada escopo, liste todos no campo "
                    "abaixo separado por escopo."
                )
                form["escopo"]["sla_descricao"] = st.text_area(
                    "Descrição do SLA",
                    value=form["escopo"]["sla_descricao"],
                    height=160,
                    key="sla_descricao_ta_v2",
                )
        else:
            # Modal == contenciosa: SLA nao se aplica, zera por defesa em camadas
            # (alem do validator do schema).
            form["escopo"]["sla_ativo"] = False
            form["escopo"]["sla_descricao"] = ""

        if modal in ("contenciosa", "mista"):
            st.markdown('<div class="pmra-sub-hdr"><span class="material-symbols-outlined pmra-icon">gavel</span>Atuação Contenciosa</div>', unsafe_allow_html=True)

            escopos_cont = form["escopo"]["escopos_contenciosos"]
            if escopos_cont:
                for i, item in enumerate(escopos_cont):
                    col_hdr, col_del = st.columns([11, 1])
                    col_hdr.markdown(
                        f'<div class="pmra-sub-hdr" style="margin-top:8px">'
                        f'<span class="material-symbols-outlined pmra-icon">gavel</span>'
                        f'Escopo {item["letra"]}</div>',
                        unsafe_allow_html=True,
                    )
                    col_del.button(
                        "✕",
                        key=f"escopo_cont_del_{i}",
                        on_click=_del_escopo_cont_cb,
                        args=(i,),
                        help="Remover escopo",
                        use_container_width=True,
                    )
                    desc_key = f"escopo_cont_desc_{i}"
                    if desc_key not in st.session_state:
                        st.session_state[desc_key] = item["descricao"]
                    st.text_area(
                        "Matérias, foros, instâncias e atos processuais",
                        height=150,
                        key=desc_key,
                        placeholder="Ex: Defesa em processos trabalhistas — 1ª e 2ª instância — TRT MG.",
                        label_visibility="collapsed",
                    )
                    escopos_cont[i]["descricao"] = st.session_state[desc_key]

                st.button(
                    "+ Adicionar escopo contencioso",
                    key="escopo_cont_add",
                    on_click=_add_escopo_cont_cb,
                )
            else:
                form["escopo"]["atuacao_contenciosa"] = st.text_area(
                    "Matérias, foros, instâncias e atos processuais",
                    value=form["escopo"]["atuacao_contenciosa"],
                    height=150,
                    key="atuacao_contenciosa_ta",
                    placeholder="Ex: Defesa em processos trabalhistas — 1ª e 2ª instância — TRT MG.",
                )
                st.button(
                    "+ Adicionar segundo escopo contencioso",
                    key="escopo_cont_to_multi",
                    on_click=_to_multi_cont_cb,
                )


# ── ETAPA 3: HONORÁRIOS ────────────────────────────────────────────────────────

elif current == 2:
    _step_honorarios()

elif current == 3:
    _subheader("receipt_long", "Despesas e Disposições Específicas")

    with st.container(border=True):
        st.markdown('<div class="pmra-sub-hdr"><span class="material-symbols-outlined pmra-icon">receipt_long</span>Despesas previstas</div>', unsafe_allow_html=True)
        _info_note(
            "Adicione ou remova despesas conforme aplicável ao escopo. "
            "Caso a natureza do projeto seja apenas consultiva, remova "
            "Despesas Gerais (aplicáveis à atuação contenciosa). O texto "
            "preenchido já vem exibido na proposta por padrão; você pode "
            "inserir, alterar ou remover qualquer conteúdo. Para adicionar "
            "nova categoria de despesa, use o campo <strong>Adicionar</strong>."
        )
        form["despesas"]["tabela_despesas"] = _render_rows(
            "tbl_despesas",
            {"categoria": "Categoria (Ex: Despesas Logísticas)", "descricao": "Descrição"},
            help_text="",
            col_widths=[3, 6],
            text_areas=["categoria", "descricao"],
            placeholders={
                "categoria": "Categoria",
                "descricao": "Descrição da despesa",
            },
        )

    with st.container(border=True):
        st.markdown('<div class="pmra-sub-hdr"><span class="material-symbols-outlined pmra-icon">article</span>Disposições específicas</div>', unsafe_allow_html=True)
        _info_note(
            "Inclua aqui quaisquer outras disposições específicas que serão "
            "aplicáveis fora das condições gerais do Escritório. Elas "
            "prevalecerão sobre as condições gerais."
        )
        form["disposicoes"]["ativo"] = st.checkbox(
            "Incluir seção de disposições específicas no contrato?",
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
    _subheader("rate_review", "Revisar e Gerar Proposta")

    modal = form["escopo"]["modalidade"]
    tipo = form["contratante"]["tipo_pessoa"]
    nome_cliente = form["contratante"]["nome"] if tipo == "fisica" else form["contratante"]["razao_social"]
    doc_cliente = form["contratante"]["cpf"] if tipo == "fisica" else form["contratante"]["cnpj"]
    end = form["contratante"]["endereco"]
    cidade_uf = "/".join(p for p in [end["cidade"], end["uf"]] if p) or "—"

    def _esc(s: str) -> str:
        return html.escape(str(s)) if s else "—"

    # ── Card Contratante
    contratante_linhas = [
        "Pessoa Física" if tipo == "fisica" else "Pessoa Jurídica",
        _esc(nome_cliente),
        f"{'CPF' if tipo == 'fisica' else 'CNPJ'}: {_esc(doc_cliente)}",
        _esc(cidade_uf),
        f"Contato: {_esc(form['contratante']['contato_nome'])}",
    ]

    # ── Card Escopo e SLA
    modalidade_label = {"consultiva": "Consultiva", "contenciosa": "Contenciosa", "mista": "Mista"}[modal]
    escopo_linhas = [f"Modalidade: {modalidade_label}"]
    if modal in ("consultiva", "mista"):
        cons_texto = (form["escopo"]["atuacao_consultiva"] or "").strip()
        if cons_texto:
            escopo_linhas.append(f"Consultiva: {_esc(cons_texto[:80])}{'…' if len(cons_texto) > 80 else ''}")
    if modal in ("contenciosa", "mista"):
        cont_texto = (form["escopo"]["atuacao_contenciosa"] or "").strip()
        if cont_texto:
            escopo_linhas.append(f"Contenciosa: {_esc(cont_texto[:80])}{'…' if len(cont_texto) > 80 else ''}")
    if modal != "contenciosa":
        escopo_linhas.append(f"SLA: {'sim' if form['escopo']['sla_ativo'] else 'não'}")

    # ── Card Honorários
    mod_labels_cons = {
        "hora_senioridade": "Hora por senioridade",
        "hora_fixa": "Hora Média",
        "fixo_mensal": "Fixo Mensal/Cap",
        "valor_projeto": "Preço Global",
    }
    mod_labels_cont = {
        "valor_acao": "Valor Mensal Por Processo",
        "valor_ato_processual": "Valor por ato processual",
        "preco_mensal_massa": "Preço mensal",
        "valor_projeto": "Preço Global",
    }
    honorarios_linhas = []
    if modal in ("consultiva", "mista"):
        cons_mods = form["honorarios_consultiva"]["modalidades"]
        cons_selecionados = [lbl for k, lbl in mod_labels_cons.items() if cons_mods[k]]
        honorarios_linhas.append(
            f"Consultiva: {_esc(', '.join(cons_selecionados)) if cons_selecionados else 'nenhuma modalidade'}"
        )
    if modal in ("contenciosa", "mista"):
        cont_mods = form["honorarios_contenciosa"]["modalidades"]
        cont_selecionados = [lbl for k, lbl in mod_labels_cont.items() if cont_mods[k]]
        honorarios_linhas.append(
            f"Contenciosa: {_esc(', '.join(cont_selecionados)) if cont_selecionados else 'nenhuma modalidade'}"
        )
        exito = form["honorarios_contenciosa"]["exito_ativo"]
        pct = form["honorarios_contenciosa"]["exito_percentual"]
        honorarios_linhas.append(f"Êxito: {('sim — ' + _esc(pct) + '%') if exito and pct else ('sim' if exito else 'não')}")
        taxa_ativa = form["despesas"]["taxa_manutencao_ativa"]
        taxa_valor = form["despesas"]["taxa_manutencao_processual"]
        honorarios_linhas.append(
            f"Taxa manutenção: {(_esc(taxa_valor) if taxa_valor else 'sim') if taxa_ativa else 'não'}"
        )

    # ── Card Despesas
    despesas = form["despesas"]["tabela_despesas"] or []
    despesas_validas = [d for d in despesas if (d.get("categoria") or d.get("descricao"))]
    despesas_linhas = [f"{len(despesas_validas)} categoria(s) prevista(s)"]
    for d in despesas_validas[:3]:
        cat = (d.get("categoria") or "").strip() or "(sem nome)"
        despesas_linhas.append(f"• {_esc(cat)}")
    if len(despesas_validas) > 3:
        despesas_linhas.append(f"• … +{len(despesas_validas) - 3}")
    disp_ativo = form["disposicoes"]["ativo"]
    despesas_linhas.append(f"Disposições específicas: {'sim' if disp_ativo else 'não'}")

    cards = [
        ("Contratante", contratante_linhas),
        ("Escopo e SLA" if modal != "contenciosa" else "Escopo", escopo_linhas),
        ("Honorários", honorarios_linhas),
        ("Despesas", despesas_linhas),
    ]
    # Cada linha vira uma <div class="review-row"> — visual mais estruturado que
    # <br> entre strings (suporta hover/spacing/animacao por linha).
    cards_html = "\n".join(
        f"""<div class="review-card">
  <div class="review-label">{label}</div>
  <div class="review-summary">
    {''.join(f'<div class="review-row">{linha}</div>' for linha in linhas)}
  </div>
</div>"""
        for label, linhas in cards
    )
    st.markdown(f'<div class="review-grid">{cards_html}</div>', unsafe_allow_html=True)

    _info_note(
        "A proposta será gerada com base no preenchimento de todos os campos "
        "do formulário. Qualquer necessidade de alteração de conteúdo ou "
        "condição a partir deste ponto deverá ser feita manualmente no Word. "
        "A proposta deverá ser salva no seu dispositivo e "
        "<strong>não será arquivada</strong> neste gerador de propostas. "
        "Após finalizada, revise o documento com atenção e lembre-se de "
        "iniciar o Fluxo Comercial no Autojur. "
        "<br><br><strong>Importante: Não altere qualquer condição dos Termos "
        "Gerais sem aprovação da Diretoria.</strong>"
    )

    gen_col, dl_col = st.columns([1, 2])

    if gen_col.button("Gerar proposta", type="primary", use_container_width=True):
        try:
            proposal = ProposalForm.model_validate(form)
            context = form_to_context(proposal)
            with st.spinner("Gerando proposta…"):
                st.session_state.generated_doc = render_proposal(context)
            st.markdown(
                '<div class="pmra-success-card">'
                '<span class="material-symbols-outlined pmra-success-icon">task_alt</span>'
                '<div class="pmra-success-text">'
                '<div class="pmra-success-title">Proposta gerada com sucesso!</div>'
                '<div class="pmra-success-subtitle">'
                'Clique em <strong>Baixar .docx</strong> para salvar no seu dispositivo.'
                '</div></div></div>',
                unsafe_allow_html=True,
            )
        except Exception:
            logger.exception("Falha ao gerar proposta")
            st.markdown(
                '<div class="pmra-error-card">'
                '<span class="material-symbols-outlined pmra-error-icon">error</span>'
                '<div class="pmra-error-text">'
                '<div class="pmra-error-title">Não foi possível gerar a proposta</div>'
                '<div class="pmra-error-subtitle">'
                'Verifique os campos preenchidos e tente novamente. '
                'Se o problema persistir, contate o suporte.'
                '</div></div></div>',
                unsafe_allow_html=True,
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
# Mais espaco entre Anterior e Proximo (coluna central de gap)
_, nav_prev, _gap, nav_next, _ = st.columns([2, 1, 0.4, 1, 2])

if current > 0:
    nav_prev.button(
        "← Anterior",
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

st.markdown(f"""
<div class="pmra-footer">
    <div class="pmra-footer-left">Legal Tech | Desenvolvido por Bruno Carvalho</div>
    <div class="pmra-footer-right">PMRA &nbsp;·&nbsp; v{APP_VERSION}</div>
</div>
""", unsafe_allow_html=True)


# ── Iframes de JS (injetados no FINAL para não empurrarem o layout) ───────────

# Input masks: só na etapa Contratante (CPF/CNPJ/CEP/telefone).
if current == 0:
    _inject_input_masks()

# Scroll-to-top quando a etapa muda — JS clássico, smooth scroll.
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

# JS MÍNIMO: apenas marca o stepper com classe `.pmra-stepper-row` para o
# CSS de sticky pegar, e adiciona/remove `.pmra-stepper-scrolled` no scroll.
# NÃO usa MutationObserver, NÃO altera textContent de buttons, NÃO interage
# com inputs/checkboxes/radios — o MutationObserver no body causava
# interferência no estado dos seletores (precisava 2 cliques pra desmarcar).
components.html("""
<script>
(function() {
  const win = window.parent;
  const doc = win.document;
  const SCROLL_SEL = '[data-testid="stMain"]';

  function findStepper() {
    const blocks = doc.querySelectorAll('[data-testid="stMainBlockContainer"] [data-testid="stHorizontalBlock"]');
    for (const b of blocks) {
      if (b.querySelectorAll('button').length >= 4) {
        b.classList.add('pmra-stepper-row');
        return b;
      }
    }
    return null;
  }

  function onScroll() {
    const stepper = findStepper();
    if (!stepper) return;
    const sc = doc.querySelector(SCROLL_SEL);
    const y = (sc && sc.scrollTop) || win.scrollY || 0;
    if (y > 8) stepper.classList.add('pmra-stepper-scrolled');
    else stepper.classList.remove('pmra-stepper-scrolled');
  }

  // Re-init em cada rerun é OK: apenas tenta achar o stepper algumas vezes
  // (a cada 200ms até 10 tentativas) e adiciona o scroll listener UMA vez
  // globalmente (flag __pmraInit).
  let tries = 0;
  const initInterval = win.setInterval(() => {
    if (findStepper() || ++tries > 10) win.clearInterval(initInterval);
  }, 200);
  onScroll();

  if (win.__pmraInit) return;
  win.__pmraInit = true;
  win.addEventListener('scroll', onScroll, { passive: true });
  const sc = doc.querySelector(SCROLL_SEL);
  if (sc) sc.addEventListener('scroll', onScroll, { passive: true });
})();
</script>
""", height=0)
