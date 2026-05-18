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

from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
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


_SZ_RE = re.compile(r'<w:sz w:val="(\d+)"/>')
_SZCS_RE = re.compile(r'<w:szCs w:val="(\d+)"/>')
_RPR_RE = re.compile(r"<w:rPr>.*?</w:rPr>", re.DOTALL)


def _force_font_size_10(xml: str) -> str:
    """Normaliza todas as fontes do documento para 10pt (val=20 em half-points).

    Preserva val=2 (paragrafos espacadores invisiveis de 1pt).
    Adiciona tamanho explicito em runs que herdariam o default do estilo
    Word (11pt), como ocorre com runs de RichText sem size declarado.
    """
    def _keep2(val: str) -> str:
        return val if val == "2" else "20"

    xml = _SZ_RE.sub(lambda m: f'<w:sz w:val="{_keep2(m.group(1))}"/>', xml)
    xml = _SZCS_RE.sub(lambda m: f'<w:szCs w:val="{_keep2(m.group(1))}"/>', xml)

    def _fix_rpr(m: re.Match[str]) -> str:
        rpr = m.group(0)
        if "<w:sz " not in rpr:
            return rpr.replace("</w:rPr>", '<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>')
        return rpr

    xml = _RPR_RE.sub(_fix_rpr, xml)
    xml = xml.replace("<w:rPr/>", '<w:rPr><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>')
    return xml


_TBL_BORDERS_RE = re.compile(r"<w:tblBorders>(.*?)</w:tblBorders>", re.DOTALL)
# So pega <w:bottom> com w:val NAO sendo nil/none. Preserva
# <w:bottom w:val="nil"/> e <w:bottom w:val="none"/> (declaracoes
# explicitas de "sem borda" em tabelas invisiveis como assinaturas/
# testemunhas — remove-las faz Word cair no default visivel).
_TBL_BOTTOM_VISIBLE_RE = re.compile(
    r'<w:bottom(?![^/]*w:val="(?:nil|none)")[^/]*/>'
)


def _remove_table_outer_bottom_borders(xml: str) -> str:
    """Remove a borda inferior VISIVEL do <w:tblBorders> de cada tabela.

    Sem isso, a ultima linha aparenta ser mais grossa porque a borda
    inferior da CELULA (em tcBorders) e a borda inferior da TABELA
    (em tblBorders) se sobrepoem visualmente. A borda inferior das
    celulas da ultima linha continua desenhando o fim da tabela.

    Tabelas com w:val="nil"/"none" (assinaturas, testemunhas) ficam
    intactas — sem isso, Word substitui pelo default visivel.
    """
    def repl(m: re.Match[str]) -> str:
        inner = _TBL_BOTTOM_VISIBLE_RE.sub("", m.group(1))
        return f"<w:tblBorders>{inner}</w:tblBorders>"

    return _TBL_BORDERS_RE.sub(repl, xml)


_PARA_ID_RE = re.compile(r'w14:paraId="([0-9A-Fa-f]+)"')


def _dedupe_para_ids(xml: str) -> str:
    """Garante que cada w14:paraId é único no documento.

    Loops {%p for %} no docxtpl duplicam parágrafos preservando o mesmo
    paraId, e Subdocs inseridos via {{p }} também trazem IDs próprios que
    podem colidir. paraIds duplicados quebram o Word ("Erro ao abrir o
    arquivo"). Reescrevemos as ocorrências duplicadas para IDs únicos.
    """
    seen: set[str] = set()
    counter = [0]

    def _next_id() -> str:
        counter[0] += 1
        return f"{counter[0]:08X}"

    def repl(m: re.Match[str]) -> str:
        pid = m.group(1).upper()
        if pid in seen:
            new_pid = _next_id()
            while new_pid in seen:
                new_pid = _next_id()
            seen.add(new_pid)
            return f'w14:paraId="{new_pid}"'
        seen.add(pid)
        return m.group(0)

    return _PARA_ID_RE.sub(repl, xml)


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
                    xml = _force_font_size_10(xml)
                    xml = _dedupe_para_ids(xml)
                    data = xml.encode("utf-8")
                zout.writestr(item, data)
    return dst.getvalue()


def _add_styled_paragraph(sd, text: str, *, bold: bool = False, justify: bool = True):
    """Adiciona parágrafo Arvo sz=10pt, opcionalmente bold e justificado."""
    p = sd.add_paragraph()
    if justify:
        p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
    run = p.add_run(text)
    run.font.name = "Arvo"
    run.font.size = Pt(10)
    if bold:
        run.font.bold = True
    return p


def _add_blank_paragraph(sd):
    """Espaçador entre blocos no subdoc."""
    p = sd.add_paragraph()
    run = p.add_run("")
    run.font.name = "Arvo"
    run.font.size = Pt(10)
    return p


def _apply_borders(table) -> None:
    """Aplica bordas single sz=4 em todos os lados (igual às tabelas do template)."""
    tblPr = table._tbl.tblPr
    tblBorders = OxmlElement("w:tblBorders")
    for name in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement(f"w:{name}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), "4")
        b.set(qn("w:space"), "0")
        b.set(qn("w:color"), "auto")
        tblBorders.append(b)
    tblPr.append(tblBorders)


def _set_cell_text(cell, text: str, *, bold: bool = False) -> None:
    """Substitui o texto da célula preservando estilo Arvo sz=10."""
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
    run = p.add_run(text)
    run.font.name = "Arvo"
    run.font.size = Pt(10)
    if bold:
        run.font.bold = True


def _add_bordered_table(sd, headers: list[str], rows: list[list[str]]):
    """Cria tabela bordada com header em bold."""
    table = sd.add_table(rows=len(rows) + 1, cols=len(headers))
    _apply_borders(table)
    for j, h in enumerate(headers):
        _set_cell_text(table.rows[0].cells[j], h, bold=True)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            _set_cell_text(table.rows[i + 1].cells[j], str(val))
    return table


def _build_consultiva_subdoc(doc: DocxTemplate, hon: dict[str, Any]):
    """Subdoc com bloco completo de honorários consultivos para um escopo."""
    sd = doc.new_subdoc()
    letra = hon.get("letra", "")
    _add_styled_paragraph(sd, f"Honorários — Escopo Consultivo {letra}", bold=True, justify=False)

    if hon.get("show_hora_senioridade"):
        _add_styled_paragraph(
            sd,
            "Os honorários serão apurados conforme a tabela de senioridade abaixo, "
            "com base em relatório mensal de horas executadas.",
        )
        rows = [[r.get("categoria", ""), r.get("valor", "")] for r in hon.get("tabela_senioridade", [])]
        if rows:
            _add_bordered_table(sd, ["Categoria", "Valor por hora"], rows)

    if hon.get("show_hora_fixa"):
        _add_styled_paragraph(
            sd,
            f"Os honorários serão apurados com base em valor horário único, aplicável indistintamente "
            f"a qualquer profissional alocado na prestação dos serviços consultivos, ao valor de "
            f"{hon.get('hora_fixa_valor', '')} por hora.",
        )

    if hon.get("show_fixo_mensal"):
        _add_styled_paragraph(
            sd,
            f"Honorários fixos mensais de {hon.get('fixo_mensal_valor', '')}, abrangendo até "
            f"{hon.get('fixo_mensal_cap', '')} de trabalho consultivo por mês. Horas excedentes "
            f"ao cap serão cobradas a {hon.get('fixo_mensal_excedente', '')} por hora.",
        )

    if hon.get("show_valor_projeto"):
        txt = (
            "Os honorários serão fixados em valor global fechado, correspondente ao conjunto de "
            f"entregas delimitadas no Escopo: {hon.get('valor_projeto_total', '')}"
        )
        if hon.get("show_valor_projeto_cap"):
            txt += f", com cap de {hon.get('valor_projeto_cap', '')} horas"
        txt += "."
        _add_styled_paragraph(sd, txt)
        if hon.get("valor_projeto_forma_pagamento"):
            _add_styled_paragraph(sd, f"Forma de pagamento: {hon.get('valor_projeto_forma_pagamento', '')}")

    _add_blank_paragraph(sd)
    return sd


def _build_contenciosa_subdoc(doc: DocxTemplate, hon: dict[str, Any]):
    """Subdoc com bloco completo de honorários contenciosos para um escopo."""
    sd = doc.new_subdoc()
    letra = hon.get("letra", "")
    _add_styled_paragraph(sd, f"Honorários — Escopo Contencioso {letra}", bold=True, justify=False)

    if hon.get("show_valor_acao"):
        _add_styled_paragraph(
            sd,
            "Os honorários serão apurados em valor mensal por processo, conforme natureza e fase, "
            "de acordo com a tabela abaixo:",
        )
        rows = [
            [r.get("natureza", ""), r.get("fase", ""), r.get("valor", "")]
            for r in hon.get("tabela_acoes", [])
        ]
        if rows:
            _add_bordered_table(sd, ["Natureza da ação", "Instâncias de Atuação", "Valor"], rows)

    if hon.get("show_valor_ato"):
        _add_styled_paragraph(
            sd,
            "Os honorários serão apurados por ato processual efetivamente praticado, conforme tabela:",
        )
        rows = [
            [r.get("ato", ""), r.get("descricao", ""), r.get("valor", "")]
            for r in hon.get("tabela_atos", [])
        ]
        if rows:
            _add_bordered_table(sd, ["Ato processual", "Descrição", "Valor"], rows)

    if hon.get("show_preco_mensal"):
        _add_styled_paragraph(
            sd,
            f"Preço mensal fixo de {hon.get('preco_mensal_valor', '')} para até "
            f"{hon.get('preco_mensal_maximo_acoes', '')} "
            f"({hon.get('preco_mensal_maximo_acoes_extenso', '')}) ações em curso.",
        )
        if hon.get("preco_mensal_criterio_excedentes"):
            _add_styled_paragraph(
                sd,
                f"Critério para ações excedentes: {hon.get('preco_mensal_criterio_excedentes', '')}",
            )

    if hon.get("show_valor_projeto"):
        _add_styled_paragraph(
            sd,
            f"Preço global para a condução integral do escopo delimitado: "
            f"{hon.get('valor_projeto_total', '')}.",
        )
        if hon.get("valor_projeto_fases_cobertas"):
            _add_styled_paragraph(sd, f"Ações e fases cobertas: {hon.get('valor_projeto_fases_cobertas', '')}")
        if hon.get("valor_projeto_forma_pagamento"):
            _add_styled_paragraph(sd, f"Forma de pagamento: {hon.get('valor_projeto_forma_pagamento', '')}")

    _add_blank_paragraph(sd)
    return sd


def _enrich_subdocs(doc: DocxTemplate, context: dict[str, Any]) -> None:
    """Anexa subdocs (com tabelas) aos itens de honorários por escopo."""
    for item in context.get("consultiva", {}).get("itens", []):
        item["subdoc"] = _build_consultiva_subdoc(doc, item)
    for item in context.get("contenciosa", {}).get("itens", []):
        item["subdoc"] = _build_contenciosa_subdoc(doc, item)


def render_proposal(context: dict[str, Any]) -> bytes:
    """Renderiza a proposta a partir do template Jinja2 e retorna os bytes do .docx."""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Template nao encontrado em {TEMPLATE_PATH}. "
            "Rode: python scripts/build_template.py"
        )
    doc = DocxTemplate(str(TEMPLATE_PATH))
    _enrich_subdocs(doc, context)
    doc.render(context)
    buf = BytesIO()
    doc.save(buf)
    return _post_process(buf.getvalue())
