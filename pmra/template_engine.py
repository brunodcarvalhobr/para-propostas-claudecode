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

from html import escape as _xml_escape

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docxtpl import DocxTemplate

_W_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

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


_DO_NOT_EXPAND_SHIFT_RETURN = "<w:doNotExpandShiftReturn/>"


def _ensure_do_not_expand_shift_return(settings_xml: str) -> str:
    """Garante a flag de compatibilidade doNotExpandShiftReturn em settings.xml.

    Sem ela, o Word estica horrivelmente a linha que termina em quebra manual
    (<w:br/>, o Enter do formulario) dentro de paragrafo justificado. Com ela,
    texto multilinha sai justificado como o texto corrido: linhas curtas antes
    da quebra ficam naturalmente a esquerda e linhas longas justificam.
    Substitui o antigo _left_align_multiline, que desfazia a justificacao.
    """
    if "doNotExpandShiftReturn" in settings_xml:
        return settings_xml
    if "<w:compat>" in settings_xml:
        return settings_xml.replace("<w:compat>", "<w:compat>" + _DO_NOT_EXPAND_SHIFT_RETURN, 1)
    return settings_xml.replace(
        "</w:settings>",
        "<w:compat>" + _DO_NOT_EXPAND_SHIFT_RETURN + "</w:compat></w:settings>",
        1,
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
                elif item.filename == "word/settings.xml":
                    try:
                        data = _ensure_do_not_expand_shift_return(
                            data.decode("utf-8")
                        ).encode("utf-8")
                    except UnicodeDecodeError:
                        pass
                zout.writestr(item, data)
    return dst.getvalue()


_BORDER_COLOR = "1A3557"  # azul escuro do template
_HEADER_FILL  = "FAE2D5"  # bege/rosa do header
_FIRSTCOL_FILL = "FFF9F4"  # creme claro da primeira coluna

_TC_BORDERS = (
    f'<w:tcBorders>'
    f'<w:top w:val="single" w:sz="4" w:space="0" w:color="{_BORDER_COLOR}"/>'
    f'<w:left w:val="single" w:sz="4" w:space="0" w:color="{_BORDER_COLOR}"/>'
    f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="{_BORDER_COLOR}"/>'
    f'<w:right w:val="single" w:sz="4" w:space="0" w:color="{_BORDER_COLOR}"/>'
    f'</w:tcBorders>'
)
_TC_MAR = (
    '<w:tcMar>'
    '<w:top w:w="100" w:type="dxa"/><w:left w:w="120" w:type="dxa"/>'
    '<w:bottom w:w="100" w:type="dxa"/><w:right w:w="120" w:type="dxa"/>'
    '</w:tcMar>'
)


def _subdoc_append(sd, xml_block: str) -> None:
    """Insere bloco XML (w:p ou w:tbl) no body do subdoc, antes do sectPr."""
    elem = parse_xml(xml_block)
    body = sd.subdocx.element.body
    # sectPr deve ficar SEMPRE no fim do body — inserimos antes dele
    sectpr = body.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sectPr')
    if sectpr is not None:
        sectpr.addprevious(elem)
    else:
        body.append(elem)


def _para_xml(text: str, *, bold: bool = False, justify: bool = True) -> str:
    """Parágrafo Arvo sz=10pt; bold opcional, justificado por padrão."""
    jc = '<w:jc w:val="both"/>' if justify else ""
    rpr_bold = "<w:b/><w:bCs/>" if bold else ""
    return (
        f'<w:p {_W_NS}>'
        f'<w:pPr><w:spacing w:line="276" w:lineRule="auto"/>{jc}'
        f'<w:rPr><w:rFonts w:ascii="Arvo" w:hAnsi="Arvo"/>{rpr_bold}'
        f'<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:pPr>'
        f'<w:r><w:rPr><w:rFonts w:ascii="Arvo" w:hAnsi="Arvo"/>{rpr_bold}'
        f'<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
        f'<w:t xml:space="preserve">{_xml_escape(text)}</w:t></w:r>'
        f'</w:p>'
    )


def _blank_para_xml() -> str:
    return (
        f'<w:p {_W_NS}>'
        f'<w:pPr><w:spacing w:line="276" w:lineRule="auto"/>'
        f'<w:rPr><w:rFonts w:ascii="Arvo" w:hAnsi="Arvo"/>'
        f'<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:pPr>'
        f'</w:p>'
    )


def _table_xml(headers: list[str], rows: list[list[str]], col_widths_dxa: list[int]) -> str:
    """Tabela com estilo idêntico ao template (header bege, 1ª coluna creme, bordas azul-escuro)."""
    total_w = sum(col_widths_dxa)

    tbl_pr = (
        '<w:tblPr>'
        f'<w:tblW w:w="{total_w}" w:type="dxa"/>'
        '<w:tblBorders>'
        f'<w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        f'<w:left w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        f'<w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        f'<w:insideV w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        '</w:tblBorders>'
        '<w:tblCellMar><w:left w:w="10" w:type="dxa"/><w:right w:w="10" w:type="dxa"/></w:tblCellMar>'
        '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>'
        '</w:tblPr>'
    )
    tbl_grid = '<w:tblGrid>' + ''.join(f'<w:gridCol w:w="{w}"/>' for w in col_widths_dxa) + '</w:tblGrid>'

    # Header row (fundo bege, texto centralizado bold)
    hdr_cells: list[str] = []
    for i, h in enumerate(headers):
        hdr_cells.append(
            f'<w:tc>'
            f'<w:tcPr>'
            f'<w:tcW w:w="{col_widths_dxa[i]}" w:type="dxa"/>'
            f'{_TC_BORDERS}'
            f'<w:shd w:val="clear" w:color="auto" w:fill="{_HEADER_FILL}"/>'
            f'{_TC_MAR}'
            f'</w:tcPr>'
            f'<w:p>'
            f'<w:pPr><w:spacing w:line="276" w:lineRule="auto"/><w:jc w:val="center"/>'
            f'<w:rPr><w:rFonts w:ascii="Arvo" w:hAnsi="Arvo"/><w:b/><w:bCs/>'
            f'<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:pPr>'
            f'<w:r><w:rPr><w:rFonts w:ascii="Arvo" w:hAnsi="Arvo"/><w:b/><w:bCs/>'
            f'<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
            f'<w:t xml:space="preserve">{_xml_escape(h)}</w:t></w:r>'
            f'</w:p></w:tc>'
        )
    header_row = f'<w:tr>{"".join(hdr_cells)}</w:tr>'

    # Data rows (1ª coluna com fundo creme, demais transparentes; texto normal)
    data_rows: list[str] = []
    for row in rows:
        cells: list[str] = []
        for i, val in enumerate(row):
            shd = f'<w:shd w:val="clear" w:color="auto" w:fill="{_FIRSTCOL_FILL}"/>' if i == 0 else ''
            jc = '<w:jc w:val="both"/>'
            cells.append(
                f'<w:tc>'
                f'<w:tcPr>'
                f'<w:tcW w:w="{col_widths_dxa[i]}" w:type="dxa"/>'
                f'{_TC_BORDERS}'
                f'{shd}'
                f'{_TC_MAR}'
                f'</w:tcPr>'
                f'<w:p>'
                f'<w:pPr><w:spacing w:line="276" w:lineRule="auto"/>{jc}'
                f'<w:rPr><w:rFonts w:ascii="Arvo" w:hAnsi="Arvo"/>'
                f'<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:pPr>'
                f'<w:r><w:rPr><w:rFonts w:ascii="Arvo" w:hAnsi="Arvo"/>'
                f'<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
                f'<w:t xml:space="preserve">{_xml_escape(str(val))}</w:t></w:r>'
                f'</w:p></w:tc>'
            )
        data_rows.append(f'<w:tr>{"".join(cells)}</w:tr>')

    return f'<w:tbl {_W_NS}>{tbl_pr}{tbl_grid}{header_row}{"".join(data_rows)}</w:tbl>'


def _kv_table_xml(rows: list[tuple[str, str]], col_widths_dxa: list[int]) -> str:
    """Tabela 'label/valor' vertical (sem header bege).

    Cada linha é (label_bold_creme, valor). Usada para Fixo Mensal, Preço Global, etc.
    """
    total_w = sum(col_widths_dxa)
    tbl_pr = (
        '<w:tblPr>'
        f'<w:tblW w:w="{total_w}" w:type="dxa"/>'
        '<w:tblBorders>'
        f'<w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        f'<w:left w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        f'<w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        f'<w:insideV w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        '</w:tblBorders>'
        '<w:tblCellMar><w:left w:w="10" w:type="dxa"/><w:right w:w="10" w:type="dxa"/></w:tblCellMar>'
        '<w:tblLook w:val="04A0" w:firstRow="0" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>'
        '</w:tblPr>'
    )
    tbl_grid = '<w:tblGrid>' + ''.join(f'<w:gridCol w:w="{w}"/>' for w in col_widths_dxa) + '</w:tblGrid>'

    tr_parts: list[str] = []
    for label, valor in rows:
        # célula label (bold + fundo creme)
        c1 = (
            f'<w:tc>'
            f'<w:tcPr>'
            f'<w:tcW w:w="{col_widths_dxa[0]}" w:type="dxa"/>'
            f'{_TC_BORDERS}'
            f'<w:shd w:val="clear" w:color="auto" w:fill="{_FIRSTCOL_FILL}"/>'
            f'{_TC_MAR}'
            f'</w:tcPr>'
            f'<w:p><w:pPr><w:spacing w:line="276" w:lineRule="auto"/>'
            f'<w:rPr><w:rFonts w:ascii="Arvo" w:hAnsi="Arvo"/><w:b/><w:bCs/>'
            f'<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:pPr>'
            f'<w:r><w:rPr><w:rFonts w:ascii="Arvo" w:hAnsi="Arvo"/><w:b/><w:bCs/>'
            f'<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
            f'<w:t xml:space="preserve">{_xml_escape(label)}</w:t></w:r>'
            f'</w:p></w:tc>'
        )
        # célula valor (texto normal, justificado, sem fundo)
        c2 = (
            f'<w:tc>'
            f'<w:tcPr>'
            f'<w:tcW w:w="{col_widths_dxa[1]}" w:type="dxa"/>'
            f'{_TC_BORDERS}'
            f'{_TC_MAR}'
            f'</w:tcPr>'
            f'<w:p><w:pPr><w:spacing w:line="276" w:lineRule="auto"/><w:jc w:val="both"/>'
            f'<w:rPr><w:rFonts w:ascii="Arvo" w:hAnsi="Arvo"/>'
            f'<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:pPr>'
            f'<w:r><w:rPr><w:rFonts w:ascii="Arvo" w:hAnsi="Arvo"/>'
            f'<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
            f'<w:t xml:space="preserve">{_xml_escape(str(valor))}</w:t></w:r>'
            f'</w:p></w:tc>'
        )
        tr_parts.append(f'<w:tr>{c1}{c2}</w:tr>')

    return f'<w:tbl {_W_NS}>{tbl_pr}{tbl_grid}{"".join(tr_parts)}</w:tbl>'


def _build_consultiva_subdoc(doc: DocxTemplate, hon: dict[str, Any]):
    """Subdoc com bloco completo de honorários consultivos para um escopo.

    Replica fielmente todas as 3 tabelas do template original consultivo:
    - Senioridade (header bege + linhas creme)
    - Fixo Mensal (label/valor vertical)
    - Preço Global (label/valor vertical)
    """
    sd = doc.new_subdoc()
    letra = hon.get("letra", "")
    _subdoc_append(sd, _para_xml(f"Honorários — Escopo Consultivo {letra}", bold=True, justify=False))
    _subdoc_append(sd, _blank_para_xml())

    if hon.get("show_hora_senioridade"):
        _subdoc_append(sd, _para_xml(
            "Os honorários serão apurados conforme a tabela de senioridade abaixo, "
            "com base em relatório mensal de horas executadas."
        ))
        _subdoc_append(sd, _blank_para_xml())
        rows = [[r.get("categoria", ""), r.get("valor", "")] for r in hon.get("tabela_senioridade", [])]
        if rows:
            _subdoc_append(sd, _table_xml(["Categoria", "Valor por Hora (R$)"], rows, [3208, 6426]))

    if hon.get("show_hora_fixa"):
        _subdoc_append(sd, _para_xml(
            f"Os honorários serão apurados com base em valor horário único, aplicável indistintamente "
            f"a qualquer profissional alocado na prestação dos serviços consultivos, ao valor de "
            f"{hon.get('hora_fixa_valor', '')} por hora."
        ))

    if hon.get("show_fixo_mensal"):
        _subdoc_append(sd, _para_xml(
            "Os honorários serão fixados em valor mensal pré-estabelecido, abrangendo um cap "
            "de horas inclusas. Horas excedentes ao cap serão cobradas separadamente."
        ))
        _subdoc_append(sd, _blank_para_xml())
        _subdoc_append(sd, _kv_table_xml([
            ("Valor Mensal",          hon.get("fixo_mensal_valor", "")),
            ("Cap de Horas",          f"{hon.get('fixo_mensal_cap', '')} horas" if hon.get("fixo_mensal_cap") else ""),
            ("Valor da Hora Excedente", hon.get("fixo_mensal_excedente", "")),
        ], [3256, 6378]))

    if hon.get("show_valor_projeto"):
        _subdoc_append(sd, _para_xml(
            "Os honorários serão fixados em valor global fechado, correspondente ao conjunto de "
            "entregas delimitadas no Escopo, conforme abaixo."
        ))
        _subdoc_append(sd, _blank_para_xml())
        kv_rows: list[tuple[str, str]] = [("Valor Total", hon.get("valor_projeto_total", ""))]
        if hon.get("show_valor_projeto_cap"):
            kv_rows.append(("Cap de Horas", f"{hon.get('valor_projeto_cap', '')} horas"))
        kv_rows.append(("Cronograma de pagamento", hon.get("valor_projeto_forma_pagamento", "")))
        _subdoc_append(sd, _kv_table_xml(kv_rows, [3256, 6378]))

    _subdoc_append(sd, _blank_para_xml())
    return sd


def _build_contenciosa_subdoc(doc: DocxTemplate, hon: dict[str, Any]):
    """Subdoc com bloco completo de honorários contenciosos para um escopo.

    Replica fielmente todas as 4 tabelas do template original contencioso:
    - Ações (header bege + linhas creme)
    - Atos Processuais (header bege + linhas creme)
    - Preço Mensal (label/valor vertical)
    - Preço Global (label/valor vertical)
    """
    sd = doc.new_subdoc()
    letra = hon.get("letra", "")
    _subdoc_append(sd, _para_xml(f"Honorários — Escopo Contencioso {letra}", bold=True, justify=False))
    _subdoc_append(sd, _blank_para_xml())

    if hon.get("show_valor_acao"):
        _subdoc_append(sd, _para_xml(
            "Os honorários serão apurados conforme valor mensal por processo em curso, conforme "
            "a natureza da ação e fase processual coberta pela atuação, nos termos abaixo."
        ))
        _subdoc_append(sd, _blank_para_xml())
        rows = [
            [r.get("natureza", ""), r.get("fase", ""), r.get("valor", "")]
            for r in hon.get("tabela_acoes", [])
        ]
        if rows:
            _subdoc_append(sd, _table_xml(
                ["Natureza da Ação", "Instâncias de Atuação", "Valor por Ação (R$)"],
                rows, [3400, 3400, 2834]
            ))

    if hon.get("show_valor_ato"):
        _subdoc_append(sd, _para_xml(
            "Os honorários serão apurados por ato efetivamente praticado pelo "
            "Contratado, conforme os valores abaixo."
        ))
        _subdoc_append(sd, _blank_para_xml())
        rows = [
            [r.get("ato", ""), r.get("descricao", ""), r.get("valor", "")]
            for r in hon.get("tabela_atos", [])
        ]
        if rows:
            _subdoc_append(sd, _table_xml(
                ["Ato", "Descrição", "Valor (R$)"], rows, [2800, 4334, 2500]
            ))

    if hon.get("show_preco_mensal"):
        _subdoc_append(sd, _para_xml(
            "Os honorários serão fixados em valor mensal fixo, abrangendo um número máximo de "
            "ações cobertas. Ações excedentes serão cobradas conforme critério específico."
        ))
        _subdoc_append(sd, _blank_para_xml())
        maximo = hon.get("preco_mensal_maximo_acoes", "")
        ext = hon.get("preco_mensal_maximo_acoes_extenso", "")
        maximo_txt = f"{maximo} ({ext}) ações" if maximo and ext else f"{maximo} ações" if maximo else ""
        _subdoc_append(sd, _kv_table_xml([
            ("Valor Mensal Fixo",                hon.get("preco_mensal_valor", "")),
            ("Número Máximo de Ações Cobertas",  maximo_txt),
            ("Critério para Ações Excedentes",   hon.get("preco_mensal_criterio_excedentes", "")),
        ], [3256, 6378]))

    if hon.get("show_valor_projeto"):
        _subdoc_append(sd, _para_xml(
            "Os honorários serão fixados em valor global fechado para a condução integral do "
            "escopo delimitado, distribuído conforme o cronograma de pagamento abaixo."
        ))
        _subdoc_append(sd, _blank_para_xml())
        _subdoc_append(sd, _kv_table_xml([
            ("Valor Total",              hon.get("valor_projeto_total", "")),
            ("Ações e Fases Cobertas",   hon.get("valor_projeto_fases_cobertas", "")),
            ("Cronograma de pagamento",  hon.get("valor_projeto_forma_pagamento", "")),
        ], [3256, 6378]))

    _subdoc_append(sd, _blank_para_xml())
    return sd


def _enrich_subdocs(doc: DocxTemplate, context: dict[str, Any]) -> None:
    """Anexa o subdoc de honorários (com tabelas) ao item de escopo correspondente.

    O honorário de cada escopo é renderizado logo abaixo da sua descrição, dentro
    do loop de escopos do template (`{{p item.subdoc}}`). Por isso o subdoc é
    anexado ao item de `escopo.itens_*` (descrições), não ao de `*.itens`. As duas
    listas são paralelas (mesma ordem, vindas de `escopos_*`), então casam por
    índice. `*.itens` só é populado quando há forma de pagamento por escopo.
    """
    escopo = context.get("escopo", {})
    pares = (
        (context.get("consultiva", {}).get("itens", []),
         escopo.get("itens_consultivos", []), _build_consultiva_subdoc),
        (context.get("contenciosa", {}).get("itens", []),
         escopo.get("itens_contenciosos", []), _build_contenciosa_subdoc),
    )
    for hon_itens, desc_itens, build in pares:
        for i, hon in enumerate(hon_itens):
            sd = build(doc, hon)
            if i < len(desc_itens):
                desc_itens[i]["subdoc"] = sd


# Folhas (nomes de campo) das tags Jinja de texto LIVRE digitado no formulario.
# Sao os unicos campos cujo conteudo e prosa do usuario e deve sair justificado.
# Valores monetarios, nomes e demais dados curtos ficam de fora de proposito.
_FORM_TEXT_LEAVES = (
    "atuacao_consultiva",
    "atuacao_contenciosa",
    "sla_descricao",
    "descricao",                        # disposicoes + itens de escopo/despesas (loops)
    "endereco_completo",
    "contatos_texto",
    "valor_projeto_forma_pagamento",    # consultiva + contenciosa
    "valor_projeto_fases_cobertas",
    "preco_mensal_criterio_excedentes",
)
# Casa uma tag de saida {{ ... <folha> ... }} (com ou sem caminho/pontos/espacos).
_FORM_TEXT_TAG_RE = re.compile(
    r"\{\{[^{}]*\b(?:" + "|".join(_FORM_TEXT_LEAVES) + r")\b[^{}]*\}\}"
)


def _justify_form_paragraphs(doc: DocxTemplate) -> None:
    """Forca alinhamento justificado nos paragrafos do template que carregam
    tags de texto livre do formulario.

    O template define <w:jc w:val="both"/> em alguns desses paragrafos, mas
    nao em todos — Escopo Consultivo/Contencioso, SLA, Disposicoes, endereco e
    contatos herdavam o alinhamento a esquerda. Aplicado ANTES do render porque
    docxtpl serializa o estado atual de doc.docx (get_xml -> body); o jc inserido
    aqui persiste no documento final. Idempotente para paragrafos ja justificados.
    """
    body = doc.get_docx().element.body
    for p in body.iter(qn("w:p")):
        text = "".join(t.text or "" for t in p.iter(qn("w:t")))
        if "{{" not in text or not _FORM_TEXT_TAG_RE.search(text):
            continue
        Paragraph(p, None).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY


def render_proposal(context: dict[str, Any]) -> bytes:
    """Renderiza a proposta a partir do template Jinja2 e retorna os bytes do .docx."""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Template nao encontrado em {TEMPLATE_PATH}. "
            "Rode: python scripts/build_template.py"
        )
    doc = DocxTemplate(str(TEMPLATE_PATH))
    _enrich_subdocs(doc, context)
    _justify_form_paragraphs(doc)
    doc.render(context)
    buf = BytesIO()
    doc.save(buf)
    return _post_process(buf.getvalue())
