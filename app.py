"""DocGen by PMRA Legal Tech (Streamlit) — formulário em etapas."""
from __future__ import annotations

import os
import re
import traceback
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

from pmra.auth import check_password
from pmra.data_mapper import form_to_context, _fmt_money as _money_fmt
from pmra.defaults import proposal_form_default
from pmra.schema import ProposalForm, UF_OPTIONS
from pmra.template_engine import render_proposal

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

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;1,9..144,400&family=Inter:wght@400;500;600&display=swap');

:root {
  --color-ink: #0a0a0a;
  --color-ink-600: #404040;
  --color-ink-400: #737373;
  --color-ink-200: #d4d4d4;
  --color-ink-100: #e5e5e5;
  --color-paper: #faf9f7;
  --color-paper-50: #fdfcfa;
  --color-paper-100: #f5f3ee;
  --color-paper-200: #ebe7df;
  --color-ember-200: #fde68a;
  --color-ember-300: #fbbf24;
  --color-ember-400: #fb923c;
  --color-ember-500: #f97316;
  --color-ember-600: #ea580c;
  --color-ember-700: #c2410c;
  --color-glass-white: rgba(255,255,255,0.55);
  --color-glass-strong: rgba(255,255,255,0.78);
  --color-glass-border: rgba(255,255,255,0.7);
  
  --shadow-glass:
    0 1px 0 0 rgba(255,255,255,0.9) inset,
    0 0 0 0.5px rgba(0,0,0,0.04),
    0 14px 40px -16px rgba(15,15,20,0.18),
    0 4px 14px -8px rgba(249,115,22,0.08);

  --shadow-input:
    0 1px 0 0 rgba(255,255,255,0.9) inset,
    0 0 0 0.5px rgba(0,0,0,0.06);

  --shadow-button:
    0 1px 0 0 rgba(255,255,255,0.4) inset,
    0 6px 18px -6px rgba(249,115,22,0.5),
    0 2px 6px -2px rgba(234,88,12,0.4);

  --ease-out-soft: cubic-bezier(0.22, 1, 0.36, 1);
  
  --font-display: 'Fraunces', ui-serif, Georgia, serif;
  --font-sans: 'Inter', ui-sans-serif, system-ui, sans-serif;
}

/* Base text */
html, body, [class*="css"] {
    font-family: var(--font-sans);
    -webkit-font-smoothing: antialiased;
    font-feature-settings: 'cv11', 'ss01', 'ss03';
    color: var(--color-ink);
}

/* Ambient Background Blobs (for Streamlit app container) */
.stApp {
    background-color: var(--color-paper) !important;
    background-image: 
        radial-gradient(circle at 80% 20%, rgba(249,115,22,0.15) 0%, transparent 40%),
        radial-gradient(circle at 20% 80%, rgba(251,191,36,0.15) 0%, transparent 40%),
        radial-gradient(ellipse at 50% 50%, rgba(199,210,254,0.12) 0%, transparent 60%);
    background-attachment: fixed;
}

/* Header */
.pmra-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 28px;
    background: rgba(253, 252, 250, 0.80);
    backdrop-filter: blur(48px);
    -webkit-backdrop-filter: blur(48px);
    border-bottom: 0.5px solid rgba(0,0,0,0.06);
    margin-bottom: 32px;
    margin-top: -60px; /* pull up into st margin */
    position: sticky;
    top: 0;
    z-index: 30;
    border-radius: 0 0 16px 16px;
}
.pmra-header-left {
    display: flex;
    align-items: center;
    gap: 14px;
}
.pmra-header-left svg { height: 32px; width: auto; border-radius: 8px; }
.pmra-header-divider {
    width: 1px;
    height: 24px;
    background: rgba(0,0,0,0.08);
}
.pmra-header-text h1 {
    font-family: var(--font-display);
    font-size: 14.5px;
    font-weight: 400;
    margin: 0;
    letter-spacing: -0.005em;
    color: var(--color-ink-600);
}

/* Container override for glassmorphism */
div[data-testid="stVerticalBlock"] > div[style*="border"] {
    background: var(--color-glass-white) !important;
    backdrop-filter: blur(24px) saturate(180%);
    -webkit-backdrop-filter: blur(24px) saturate(180%);
    border: 0.5px solid var(--color-glass-border) !important;
    box-shadow: var(--shadow-glass) !important;
    border-radius: 18px !important;
    padding: 32px !important;
    transition: all 220ms var(--ease-out-soft);
}

/* Buttons */
button[kind="primary"],
[data-testid="baseButton-primary"] {
    background: linear-gradient(to bottom, #fb923c, #ea580c) !important;
    border: none !important;
    color: #FFFFFF !important;
    font-weight: 500 !important;
    border-radius: 12px !important;
    box-shadow: var(--shadow-button) !important;
    transition: all 220ms var(--ease-out-soft) !important;
}
button[kind="primary"]:hover,
[data-testid="baseButton-primary"]:hover {
    background: linear-gradient(to bottom, #fb923c, #ea580c) !important;
    filter: brightness(1.06);
    box-shadow: 0 1px 0 0 rgba(255,255,255,0.5) inset, 0 8px 22px -6px rgba(249,115,22,0.6), 0 3px 8px -2px rgba(234,88,12,0.45) !important;
    transform: translateY(-1px) !important;
}

[data-testid="baseButton-secondary"] {
    background: rgba(255,255,255,0.7) !important;
    backdrop-filter: blur(12px) saturate(160%) !important;
    border: 0.5px solid rgba(0,0,0,0.08) !important;
    border-radius: 12px !important;
    color: var(--color-ink) !important;
    box-shadow: var(--shadow-input) !important;
    font-weight: 500 !important;
}
[data-testid="baseButton-secondary"]:hover {
    background: rgba(255,255,255,0.9) !important;
    border-color: rgba(0,0,0,0.14) !important;
}

/* Step Buttons uniform height */
[data-testid="stBaseButton-secondary"] > button,
[data-testid="stBaseButton-primary"] > button {
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    height: 40px !important;
    min-height: 40px !important;
    border-radius: 999px !important;
}

/* Input fields */
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"], [data-baseweb="base-input"] {
    background: rgba(255,255,255,0.7) !important;
    backdrop-filter: blur(12px) saturate(160%) !important;
    border: 0.5px solid rgba(0,0,0,0.08) !important;
    border-radius: 12px !important;
    box-shadow: var(--shadow-input) !important;
    transition: all 220ms var(--ease-out-soft) !important;
}
[data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within, [data-baseweb="select"]:focus-within {
    border-color: rgba(249,115,22,0.55) !important;
    box-shadow: 0 1px 0 0 rgba(255,255,255,0.9) inset, 0 0 0 3px rgba(249,115,22,0.16) !important;
}

/* Headings */
h1, h2, h3, .pmra-sub-hdr {
    font-family: var(--font-display) !important;
    color: var(--color-ink) !important;
}
h2 {
    font-size: 26px !important;
    line-height: 1.1 !important;
    letter-spacing: -0.01em !important;
    margin-bottom: 24px !important;
}
h3 {
    font-size: 18px !important;
    line-height: 1.2 !important;
    letter-spacing: -0.005em !important;
    margin-top: 16px !important;
    margin-bottom: 16px !important;
}

/* Labels */
label {
    font-family: var(--font-sans) !important;
    font-size: 11.5px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    color: var(--color-ink-600) !important;
    font-weight: 500 !important;
}

/* Selection */
::selection {
    background: rgba(249,115,22,0.18);
    color: var(--color-ink);
}

/* Scrollbar */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: rgba(64,64,64,0.18);
    border-radius: 999px;
    border: 2px solid transparent;
    background-clip: content-box;
}
::-webkit-scrollbar-thumb:hover { background: rgba(64,64,64,0.32); background-clip: content-box; }

/* Subheaders within cards */
.pmra-sub-hdr {
    font-family: var(--font-sans) !important;
    font-size: 10.5px;
    font-weight: 500;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--color-ember-600);
    margin-top: 24px;
    margin-bottom: 16px;
}

/* Progress Bar container override */
[data-testid="stProgressBar"] > div > div {
    background-color: var(--color-ember-500) !important;
}

/* Width constraint */
div[data-testid="stMainBlockContainer"] {
    max-width: 896px !important;
    margin: 0 auto !important;
    padding: 32px 28px !important;
}

/* Table Headers */
.pmra-tbl-hdr {
    font-family: var(--font-sans) !important;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--color-ink-400);
    margin-bottom: 8px;
}

/* Divider */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(to right, transparent, rgba(0,0,0,0.10), transparent) !important;
    margin: 32px 0 !important;
}

/* Compact clear row buttons */
[data-testid$="__del"] > div > button {
    padding-top: 0.3rem !important;
    padding-bottom: 0.3rem !important;
    font-size: 0.8rem !important;
    color: var(--color-ink-400) !important;
    border-color: rgba(0,0,0,0.10) !important;
    background: transparent !important;
    box-shadow: none !important;
}
[data-testid$="__del"] > div > button:hover {
    color: var(--color-danger-600) !important;
    border-color: var(--color-danger-600) !important;
    background: rgba(239, 68, 68, 0.1) !important;
}

/* Review Cards */
.review-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}
.review-card {
    background: var(--color-glass-white);
    backdrop-filter: blur(24px) saturate(180%);
    -webkit-backdrop-filter: blur(24px) saturate(180%);
    border: 0.5px solid var(--color-glass-border);
    box-shadow: var(--shadow-glass);
    border-radius: 18px;
    padding: 20px 24px;
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.review-label {
    font-family: var(--font-sans);
    font-size: 10.5px;
    font-weight: 500;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--color-ember-600);
}
.review-value {
    font-family: var(--font-display);
    font-size: 18px;
    line-height: 1.2;
    letter-spacing: -0.005em;
    color: var(--color-ink);
}

/* Footer style */
.pmra-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 28px;
    background: rgba(253, 252, 250, 0.60);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border-top: 0.5px solid rgba(0,0,0,0.05);
    font-size: 11px;
    color: var(--color-ink-400);
    margin-top: 64px;
    border-radius: 16px 16px 0 0;
}
.pmra-footer-left {
    font-family: var(--font-display);
    font-style: italic;
    letter-spacing: 0.005em;
}
.pmra-footer-right {
    font-variant-numeric: tabular-nums;
}
</style>
""", unsafe_allow_html=True)

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
    
    // Inject and initialize MS Teams SDK in the parent document
    const parentDoc = window.parent.document;
    if (!parentDoc.getElementById('teams-sdk-script')) {
      const tsScript = parentDoc.createElement('script');
      tsScript.id = 'teams-sdk-script';
      tsScript.src = 'https://res.cdn.office.net/teams-js/2.11.0/js/MicrosoftTeams.min.js';
      tsScript.onload = function() {
        if (window.parent.microsoftTeams) {
          window.parent.microsoftTeams.app.initialize().then(function() {
            console.log("MS Teams SDK initialized successfully.");
          }).catch(function(e) {
            console.log("Teams initialization failed (or not running in Teams):", e);
          });
        }
      };
      parentDoc.head.appendChild(tsScript);
    }
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
            cm["hora_fixa"] = c2.checkbox("Hora fixa", value=cm["hora_fixa"], key="cons_hf")
            cm["fixo_mensal"] = c3.checkbox("Fixo mensal", value=cm["fixo_mensal"], key="cons_fm")
            cm["valor_projeto"] = c4.checkbox("Valor do projeto", value=cm["valor_projeto"], key="cons_vp")

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
                    "Valor total do projeto",
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
            cm["valor_acao"] = c1.checkbox("Valor por ação", value=cm["valor_acao"], key="cont_va")
            cm["valor_ato_processual"] = c2.checkbox("Valor por ato processual", value=cm["valor_ato_processual"], key="cont_vap")
            cm["preco_mensal_massa"] = c3.checkbox("Preço mensal", value=cm["preco_mensal_massa"], key="cont_pm")
            cm["valor_projeto"] = c4.checkbox("Valor por projeto", value=cm["valor_projeto"], key="cont_vp")

            if cm["valor_acao"]:
                st.markdown('<div class="pmra-sub-hdr">Tabela — Valor por Ação</div>', unsafe_allow_html=True)
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
                    "Valor total do projeto — contencioso",
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
                format_func=lambda x: "Tabela por senioridade" if x == "senioridade" else "Hora fixa (valor único)",
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
            {"categoria": "Categoria (Ex: Despesas Gerais)", "descricao": "Descrição"},
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

    localidade = f"{cidade}/{uf}" if cidade else "—"
    st.markdown(f"""
<div class="review-grid">
  <div class="review-card">
    <div class="review-label">Contratante</div>
    <div class="review-value">{nome_cliente or "—"}</div>
  </div>
  <div class="review-card">
    <div class="review-label">Documento</div>
    <div class="review-value">{doc_cliente or "—"}</div>
  </div>
  <div class="review-card">
    <div class="review-label">Localidade</div>
    <div class="review-value">{localidade}</div>
  </div>
  <div class="review-card">
    <div class="review-label">Modalidade</div>
    <div class="review-value">{modal.capitalize()}</div>
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
