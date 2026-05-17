"""Engine de renderizacao de propostas via docxtpl.

Carrega o template Jinja2 (gerado por scripts/build_template.py), renderiza
com o contexto retornado por `data_mapper.form_to_context` e pos-processa o
.docx para converter '\\n' em <w:br/> dentro dos runs de texto (Word ignora
'\\n' literal — sem isso as quebras de linha que o usuario digita nas textareas
sumiriam no documento final).
"""
from __future__ import annotations

import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

from docxtpl import DocxTemplate

TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent
    / "resources"
    / "templates"
    / "PMRA_Template_Jinja.docx"
)

# <w:t [attrs]>texto</w:t> — texto nao contem '<' (ja escapado pelo docxtpl).
_T_RE = re.compile(r"<w:t([^>]*)>([^<]*)</w:t>", flags=re.DOTALL)

# Paragrafo completo: <w:p ...>...</w:p> ou self-closing <w:p .../>
_P_RE = re.compile(r"<w:p\b[^>]*>.*?</w:p>|<w:p\b[^>]*/>", flags=re.DOTALL)
# Texto dentro de runs de um paragrafo
_T_TEXT_RE = re.compile(r"<w:t[^>]*>([^<]*)</w:t>")

_DOCS_TO_PROCESS = (
    "word/document.xml",
    "word/header1.xml",
    "word/header2.xml",
    "word/header3.xml",
    "word/footer1.xml",
    "word/footer2.xml",
    "word/footer3.xml",
)


def _split_linebreaks(xml: str) -> str:
    def repl(m: re.Match[str]) -> str:
        attrs = m.group(1)
        text = m.group(2)
        if "\n" not in text:
            return m.group(0)
        if "xml:space" not in attrs:
            attrs = attrs + ' xml:space="preserve"'
        parts = text.split("\n")
        joiner = f"</w:t><w:br/><w:t{attrs}>"
        return f"<w:t{attrs}>" + joiner.join(parts) + "</w:t>"

    return _T_RE.sub(repl, xml)


def _is_empty_paragraph(p_xml: str) -> bool:
    """True se o paragrafo nao tem texto visivel (so pPr/pictures/etc.)."""
    texts = _T_TEXT_RE.findall(p_xml)
    return all(not t.strip() for t in texts)


def _collapse_empty_paragraphs(xml: str) -> str:
    """Colapsa sequencias de paragrafos vazios consecutivos para apenas 1.

    Os blocos {%p if %} do docxtpl removem o paragrafo que contem a tag, mas
    paragrafos vazios deixados ao redor (como espacamento visual durante a
    edicao do template) ficam no documento final, gerando duas/tres linhas em
    branco em vez de uma. Esta funcao normaliza para sempre 1 paragrafo vazio
    entre blocos de conteudo.
    """
    matches = list(_P_RE.finditer(xml))
    if not matches:
        return xml

    # Marca quais paragrafos remover: empty consecutivo apos outro empty
    skip = [False] * len(matches)
    prev_empty = False
    for i, m in enumerate(matches):
        if _is_empty_paragraph(m.group(0)):
            if prev_empty:
                skip[i] = True
            prev_empty = True
        else:
            prev_empty = False

    if not any(skip):
        return xml

    out = []
    last = 0
    for i, m in enumerate(matches):
        if skip[i]:
            out.append(xml[last:m.start()])
            last = m.end()
    out.append(xml[last:])
    return "".join(out)


_TBL_BORDERS_RE = re.compile(r"<w:tblBorders>(.*?)</w:tblBorders>", re.DOTALL)
_TBL_BOTTOM_RE = re.compile(r"<w:bottom[^/]*/>")


def _remove_table_outer_bottom_borders(xml: str) -> str:
    """Remove a borda inferior do <w:tblBorders> de cada tabela.

    Sem isso, a ultima linha aparenta ser mais grossa porque a borda
    inferior da CELULA (em tcBorders) e a borda inferior da TABELA
    (em tblBorders) se sobrepoem visualmente. A borda inferior das
    celulas da ultima linha continua desenhando o fim da tabela.
    """
    def repl(m: re.Match[str]) -> str:
        inner = _TBL_BOTTOM_RE.sub("", m.group(1))
        return f"<w:tblBorders>{inner}</w:tblBorders>"

    return _TBL_BORDERS_RE.sub(repl, xml)


def _post_process(docx_bytes: bytes) -> bytes:
    src = BytesIO(docx_bytes)
    dst = BytesIO()
    with zipfile.ZipFile(src, "r") as zin:
        with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename in _DOCS_TO_PROCESS:
                    try:
                        xml = data.decode("utf-8")
                    except UnicodeDecodeError:
                        zout.writestr(item, data)
                        continue
                    xml = _split_linebreaks(xml)
                    xml = _collapse_empty_paragraphs(xml)
                    xml = _remove_table_outer_bottom_borders(xml)
                    data = xml.encode("utf-8")
                zout.writestr(item, data)
    return dst.getvalue()


def render_proposal(context: dict[str, Any]) -> bytes:
    """Renderiza a proposta a partir do template Jinja2 e retorna os bytes do .docx."""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Template nao encontrado em {TEMPLATE_PATH}. "
            "Rode: python scripts/build_template.py"
        )
    doc = DocxTemplate(str(TEMPLATE_PATH))
    doc.render(context)
    buf = BytesIO()
    doc.save(buf)
    return _post_process(buf.getvalue())
