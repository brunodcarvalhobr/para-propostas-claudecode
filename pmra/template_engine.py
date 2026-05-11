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
