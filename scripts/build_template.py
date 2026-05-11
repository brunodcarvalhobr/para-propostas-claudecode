#!/usr/bin/env python3
"""
Converte resources/templates/PMRA_Escopo_Misto.docx (original PMRA) para
resources/templates/PMRA_Template_Jinja.docx (versao docxtpl/Jinja2) aplicando:

  1. Remocao das marcas {{#INSTRUCAO}}...{{/INSTRUCAO}} (todos os runs em
     vermelho EE0000 sao considerados instrucoes e sao removidos).
  2. Substituicao dos placeholders originais por tags Jinja2 estruturadas
     (snake_case via dotted paths) compativeis com docxtpl.
  3. Insercao de marcadores condicionais {%p if cond %}...{%p endif %} e de
     loops {%tr for it in items %}...{%tr endfor %} ao redor de secoes e
     linhas que dependem de escolhas do usuario (PF/PJ, SLA, modalidades,
     Exito, Disposicoes, etc.).

Uso:
    python3 scripts/build_template.py [--source PATH] [--dest PATH]

Sem argumentos, opera sobre os caminhos padrao do projeto.
"""
from __future__ import annotations

import argparse
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "resources" / "templates" / "PMRA_Escopo_Misto.docx"
DEFAULT_DEST = ROOT / "resources" / "templates" / "PMRA_Template_Jinja.docx"


# Paragrafo-marcador: contem apenas a tag Jinja2 docxtpl. {%p ... %} faz docxtpl
# remover o paragrafo inteiro depois de processar; {%tr ... %} dentro de uma
# celula faz docxtpl remover a linha de tabela inteira. Tamanho 2pt minimiza
# qualquer residuo visual antes da remocao.
def make_marker(content: str) -> str:
    return (
        '<w:p><w:pPr><w:rPr><w:sz w:val="2"/><w:szCs w:val="2"/></w:rPr></w:pPr>'
        '<w:r><w:rPr><w:sz w:val="2"/><w:szCs w:val="2"/></w:rPr>'
        f'<w:t xml:space="preserve">{content}</w:t></w:r></w:p>'
    )


def p_if(cond: str) -> str:
    return make_marker("{%p if " + cond + " %}")


def p_endif() -> str:
    return make_marker("{%p endif %}")


# IMPORTANTE: o pre-processamento do docxtpl encontra `{%tr X %}` numa <w:tr>
# e SUBSTITUI A LINHA INTEIRA por `{% X %}` (whole-row replacement). Logo,
# colocar `{%tr if`+`{%tr endif` em celulas da MESMA linha faz a linha sumir
# (os dois markers se autodestroem juntos). A solucao e inserir LINHAS-MARKER
# vazias antes e depois da linha alvo — docxtpl remove cada linha-marker e
# emite o `{%`/`%}` correspondente fora da linha, deixando a linha alvo
# envolta pela condicional/loop.


def _make_marker_row(template_row_xml: str, marker_content: str) -> str:
    """Cria uma <w:tr> mimetizando a estrutura de `template_row_xml` com o
    `marker_content` no primeiro <w:tc> (o resto vazio). docxtpl removera essa
    linha inteira ao processar o `{%tr ...%}` dentro dela, e o conteudo entre
    as marker-rows fica envolto pela condicional/loop."""
    trpr_m = re.search(r"<w:trPr\b.*?</w:trPr>", template_row_xml, flags=re.DOTALL)
    trpr = trpr_m.group(0) if trpr_m else ""
    cells = re.findall(r"<w:tc\b[^>]*>.*?</w:tc>", template_row_xml, flags=re.DOTALL)
    if not cells:
        return ""

    new_cells: list[str] = []
    for i, cell in enumerate(cells):
        tcpr_m = re.search(r"<w:tcPr\b.*?</w:tcPr>", cell, flags=re.DOTALL)
        tcpr = tcpr_m.group(0) if tcpr_m else ""
        if i == 0:
            content = (
                '<w:p><w:pPr><w:rPr><w:sz w:val="2"/><w:szCs w:val="2"/></w:rPr></w:pPr>'
                '<w:r><w:rPr><w:sz w:val="2"/><w:szCs w:val="2"/></w:rPr>'
                f'<w:t xml:space="preserve">{marker_content}</w:t></w:r></w:p>'
            )
        else:
            content = '<w:p><w:pPr><w:rPr><w:sz w:val="2"/></w:rPr></w:pPr></w:p>'
        new_cells.append(f"<w:tc>{tcpr}{content}</w:tc>")

    return f"<w:tr>{trpr}{''.join(new_cells)}</w:tr>"


def tr_if_row(template_row_xml: str, cond: str) -> str:
    return _make_marker_row(template_row_xml, "{%tr if " + cond + " %}")


def tr_endif_row(template_row_xml: str) -> str:
    return _make_marker_row(template_row_xml, "{%tr endif %}")


def tr_for_row(template_row_xml: str, var: str, iterable: str) -> str:
    return _make_marker_row(
        template_row_xml, "{%tr for " + var + " in " + iterable + " %}"
    )


def tr_endfor_row(template_row_xml: str) -> str:
    return _make_marker_row(template_row_xml, "{%tr endfor %}")


# -- Step 1: remover runs vermelhos (instrucoes do template) -----------------
_RUN_RE = re.compile(r'<w:r\b[^>]*>.*?</w:r>', re.DOTALL)
_TEXT_RE_INNER = re.compile(r'<w:t[^>]*>([^<]*)</w:t>')


def _strip_red_runs(para_xml: str) -> str:
    return _RUN_RE.sub(
        lambda m: '' if 'w:color w:val="EE0000"' in m.group(0) else m.group(0),
        para_xml,
    )


def remove_red_runs(xml: str) -> str:
    """Remove paragrafos de instrucao sem deixar linhas em branco no Word."""
    _PPR_COLOR_RE = re.compile(r'(<w:pPr\b.*?</w:pPr>)', re.DOTALL)

    def strip_ppr_red(ppr_xml: str) -> str:
        return re.sub(r'<w:color w:val="EE0000"/>', '', ppr_xml)

    def process_para(match: re.Match[str]) -> str:
        para = match.group(0)
        if 'w:color w:val="EE0000"' not in para:
            return para
        cleaned = _strip_red_runs(para)
        remaining = "".join(_TEXT_RE_INNER.findall(cleaned)).strip()
        if not remaining:
            return ""
        cleaned = _PPR_COLOR_RE.sub(lambda m: strip_ppr_red(m.group(0)), cleaned)
        return cleaned

    cleaned = re.sub(r'<w:p\b[^>]*>.*?</w:p>', process_para, xml, flags=re.DOTALL)
    cleaned = re.sub(r"\{\{#INSTRUCAO\}\}.*?\{\{/INSTRUCAO\}\}", "", cleaned, flags=re.DOTALL)
    return cleaned


# -- Step 2: substituir placeholders fixos ------------------------------------
PLACEHOLDER_REPLACEMENTS: list[tuple[str, str]] = [
    ("{{NOME OU RAZÃO SOCIAL}}", "{{meta.nome_ou_razao_social}}"),
    (
        "{{Inserir número}}",
        "{% if contratante.pf %}{{contratante.cpf}}{% endif %}"
        "{% if contratante.pj %}{{contratante.cnpj}}{% endif %}",
    ),
    (
        "{{Inserir logradouro, número, bairro, CEP, cidade e UF}}",
        "{{contratante.endereco_completo}}",
    ),
    ("{{Inserir nome do contato}}", "{{contratante.contato_nome}}"),
    ("{{Inserir telefone}}", "{{contratante.contatos_texto}}"),
    ("{{Inserir e-mail}}", ""),  # absorvido por contatos_texto
    (
        "{{Descrever as áreas, matérias e entregáveis consultivos abrangidos}}",
        "{{escopo.atuacao_consultiva}}",
    ),
    (
        "{{Descrever as matérias, foros, instâncias e atos processuais abrangidos}}",
        "{{escopo.atuacao_contenciosa}}",
    ),
    (
        "{{Descrever a forma de SLA por complexidade Baixa, Média ou Alta}}",
        "{{escopo.sla_descricao}}",
    ),
    ("{{Descrever}}", "{{disposicoes.descricao}}"),
]


def replace_placeholders(xml: str) -> str:
    for old, new in PLACEHOLDER_REPLACEMENTS:
        xml = xml.replace(old, new)
    xml = xml.replace("<w:t>Contato</w:t>", "<w:t>Responsável</w:t>")
    return xml


# -- Step 2.5: reinjetar tags perdidas ----------------------------------------
LOST_PLACEHOLDERS: list[tuple[str, str]] = [
    ("Contatos", "{{contratante.contatos_texto}}"),
]


# -- Step 3: substituicoes escalares posicionais ------------------------------
SCALAR_FIELD_REPLACEMENTS: list[tuple[str, str, str, int]] = [
    # (row_label, placeholder_original, target_jinja, occurrence_index)
    # Consultiva: Hora Fixa
    ("Valor por Hora",                   "{{R$ XXXX,XX}}", "{{consultiva.hora_fixa_valor}}",            0),
    # Consultiva: Fixo Mensal
    ("Valor Mensal",                     "{{R$ XXXX,XX}}", "{{consultiva.fixo_mensal_valor}}",          0),
    ("Cap de Horas",                     "{{R$ XXXX,XX}}", "{{consultiva.fixo_mensal_cap}}",            0),
    ("Valor da Hora Excedente",          "{{R$ XXXX,XX}}", "{{consultiva.fixo_mensal_excedente}}",      0),
    # Consultiva: Valor do Projeto
    ("Valor Total",                      "{{R$ XXXX,XX}}", "{{consultiva.valor_projeto_total}}",        0),
    ("Forma de pagamento",
     "{{Definir como será pago, se parcelado, ao final, por marcos de entrega, datas específicas ou periodicidade específica, ou ao final do projeto}}",
     "{{consultiva.valor_projeto_forma_pagamento}}",                                                    0),
    # Contenciosa: Preco Mensal
    ("Valor Mensal Fixo",                "{{R$ XXXX,XX}}", "{{contenciosa.preco_mensal_valor}}",        0),
    ("Número Máximo de Ações Cobertas",  "{{X}}",          "{{contenciosa.preco_mensal_maximo_acoes}}", 0),
    ("Número Máximo de Ações Cobertas",  "{{por extenso}}", "{{contenciosa.preco_mensal_maximo_acoes_extenso}}", 0),
    ("Critério para Ações Excedentes",   "{{Definir critério}}", "{{contenciosa.preco_mensal_criterio_excedentes}}", 0),
    # Contenciosa: Valor por Projeto (2a ocorrencia de "Valor Total" e "Forma de pagamento")
    ("Valor Total",                      "{{R$ XXXX,XX}}", "{{contenciosa.valor_projeto_total}}",       1),
    ("Ações e Fases Cobertas",           "{{Relação das ações e das respectivas fases}}",
     "{{contenciosa.valor_projeto_fases_cobertas}}",                                                    0),
    ("Forma de pagamento",
     "{{Definir como será pago, se parcelado, ao final, por marcos de entrega, datas específicas ou periodicidade específica, ou ao final do projeto}}",
     "{{contenciosa.valor_projeto_forma_pagamento}}",                                                   1),
    # Contenciosa: Honorarios de Exito
    ("Percentual sobre Êxito (%)",       "{{XX}}",         "{{contenciosa.exito_percentual}}",          0),
    # Horas Extra Escopo: Hora Fixa (2a ocorrencia de "Valor por Hora")
    ("Valor por Hora",                   "{{R$ XXXX,XX}}", "{{contenciosa.horas_extra_valor}}",         1),
    # Despesas
    ("Taxa de Manutenção Processual (Mensal/Por Processo)", "{{Inserir valor}}", "{{despesas.taxa_manutencao_processual}}", 0),
]


# -- Helpers de XML (parsing leve via regex) ---------------------------------
_PARA_RE = re.compile(r"<w:p\b[^>]*>.*?</w:p>", flags=re.DOTALL)
_TEXT_RE = re.compile(r"<w:t[^>]*>([^<]*)</w:t>")
_TBL_TAG_RE = re.compile(r"<w:tbl\b|</w:tbl>")


def _para_text(para_xml: str) -> str:
    return "".join(_TEXT_RE.findall(para_xml))


def _iter_paragraphs(xml: str):
    for m in _PARA_RE.finditer(xml):
        yield m.start(), m.end(), m.group(0), _para_text(m.group(0))


def _find_paragraph(xml: str, anchor: str, *, start: int = 0, predicate=None) -> tuple[int, int] | None:
    for s, e, _para, text in _iter_paragraphs(xml):
        if e <= start:
            continue
        if anchor in text and (predicate is None or predicate(text)):
            return s, e
    return None


def _enclosing_table_extent(xml: str, pos: int) -> tuple[int, int] | None:
    before = xml[:pos]
    n_open = before.count("<w:tbl")
    n_close = before.count("</w:tbl>")
    if n_open <= n_close:
        return None

    depth = 0
    tbl_start = -1
    for m in reversed(list(_TBL_TAG_RE.finditer(before))):
        tag = m.group()
        if tag == "</w:tbl>":
            depth += 1
        else:
            if depth == 0:
                tbl_start = m.start()
                break
            depth -= 1
    if tbl_start == -1:
        return None

    depth = 0
    for m in _TBL_TAG_RE.finditer(xml, tbl_start):
        if m.group().startswith("<w:tbl"):
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return (tbl_start, m.end())
    return None


def _before_enclosing_table(xml: str, pos: int) -> int:
    ext = _enclosing_table_extent(xml, pos)
    return ext[0] if ext else pos


def _after_enclosing_table(xml: str, pos: int) -> int:
    ext = _enclosing_table_extent(xml, pos)
    return ext[1] if ext else pos


# -- Step 4: substituir celulas com placeholders fragmentados em multiplos runs
def _replace_cell_with_placeholder(cell_xml: str, placeholder: str) -> str:
    run_m = re.search(r"<w:r\b[^>]*>([\s\S]*?)</w:r>", cell_xml)
    if not run_m:
        return cell_xml
    rpr_m = re.search(r"<w:rPr\b[\s\S]*?</w:rPr>", run_m.group(1))
    rpr = rpr_m.group(0) if rpr_m else ""

    p_m = re.search(r"<w:p\b([^>]*)>([\s\S]*?)</w:p>", cell_xml)
    if not p_m:
        return cell_xml
    p_attrs = p_m.group(1)
    ppr_m = re.search(r"<w:pPr\b[\s\S]*?</w:pPr>", p_m.group(2))
    ppr = ppr_m.group(0) if ppr_m else ""

    tc_open_m = re.match(r"<w:tc\b[^>]*>", cell_xml)
    if not tc_open_m:
        return cell_xml
    tc_open = tc_open_m.group(0)
    tcpr_m = re.search(r"<w:tcPr\b[\s\S]*?</w:tcPr>", cell_xml)
    tcpr = tcpr_m.group(0) if tcpr_m else ""

    new_para = (
        f"<w:p{p_attrs}>{ppr}<w:r>{rpr}"
        f'<w:t xml:space="preserve">{placeholder}</w:t></w:r></w:p>'
    )
    return f"{tc_open}{tcpr}{new_para}</w:tc>"


def replace_despesas_value_cells(xml: str) -> str:
    tbl_re = re.compile(r"<w:tbl\b[\s\S]*?</w:tbl>")
    row_re = re.compile(r"<w:tr\b[\s\S]*?</w:tr>")
    cell_re = re.compile(r"<w:tc\b[^>]*>[\s\S]*?</w:tc>")

    for tm in tbl_re.finditer(xml):
        tbl = tm.group(0)
        text = _para_text(tbl)
        if "Despesas Gerais" not in text or "Taxa de Manutenção" not in text:
            continue
        
        rows = list(row_re.finditer(tbl))
        
        row_gerais_idx = -1
        row_especificas_idx = -1
        for i, m in enumerate(rows):
            rtext = _para_text(m.group(0))
            if "Despesas Gerais" in rtext:
                row_gerais_idx = i
            elif "Despesas Específicas" in rtext:
                row_especificas_idx = i
                
        if row_gerais_idx == -1:
            continue
            
        gerais_row = rows[row_gerais_idx].group(0)
        cells = list(cell_re.finditer(gerais_row))
        if len(cells) < 2:
            continue
            
        new_first_cell = _replace_cell_with_placeholder(cells[0].group(0), "{{d.categoria}}")
        new_last_cell = _replace_cell_with_placeholder(cells[-1].group(0), "{{d.descricao}}")
        new_body_row = gerais_row[: cells[-1].start()] + new_last_cell + gerais_row[cells[-1].end():]
        new_body_row = new_body_row[: cells[0].start()] + new_first_cell + new_body_row[cells[0].end():]
        
        for_row = tr_for_row(new_body_row, "d", "despesas.tabela_despesas")
        endfor_row = tr_endfor_row(new_body_row)
        
        new_tbl = tbl[:rows[0].start()]
        for i, m in enumerate(rows):
            if i == row_gerais_idx:
                new_tbl += for_row + new_body_row + endfor_row
            elif i == row_especificas_idx:
                pass # remove from template, dynamic now
            else:
                new_tbl += m.group(0)
        new_tbl += tbl[rows[-1].end():]
        
        return xml[: tm.start()] + new_tbl + xml[tm.end():]
    return xml


# -- Step 5: tabelas dinamicas (loops) ---------------------------------------
def _wrap_data_rows_with_loop(
    xml: str, table_anchor: str, header_anchor: str, loop_var: str, iterable: str,
    field_replacements: list[tuple[str, str]],
) -> str:
    """Reconstroi a tabela: header + marker-row {%tr for loop_var in iterable%}
    + body-row (com `field_replacements` aplicados) + marker-row {%tr endfor%}.
    Descarta o resto. docxtpl removera as marker-rows e repetira a body-row uma
    vez por item do iteravel."""
    tbl_re = re.compile(r"<w:tbl\b.*?</w:tbl>", flags=re.DOTALL)
    row_re = re.compile(r"<w:tr\b.*?</w:tr>", flags=re.DOTALL)

    for tm in tbl_re.finditer(xml):
        tbl = tm.group(0)
        if header_anchor not in _para_text(tbl):
            continue
        if table_anchor not in _para_text(tbl):
            continue
        rows = list(row_re.finditer(tbl))
        if len(rows) < 2:
            print(f"  ! tabela com {header_anchor!r} tem menos de 2 rows")
            return xml

        body_row = rows[1].group(0)
        for placeholder, replacement in field_replacements:
            body_row = body_row.replace(placeholder, replacement)

        for_row = tr_for_row(body_row, loop_var, iterable)
        endfor_row = tr_endfor_row(body_row)

        header_row = rows[0].group(0)
        before_first_row = tbl[: rows[0].start()]
        after_last_row = tbl[rows[-1].end():]
        new_tbl = (
            before_first_row + header_row
            + for_row + body_row + endfor_row
            + after_last_row
        )

        return xml[: tm.start()] + new_tbl + xml[tm.end():]

    print(f"  ! tabela com header {header_anchor!r} e anchor {table_anchor!r} nao encontrada")
    return xml


def _convert_senioridade_to_loop(xml: str, loop_var: str, iterable: str, *, start_after: int = 0) -> tuple[str, int]:
    """Converte tabela de senioridade (Categoria | Valor por Hora) em loop com
    marker-rows separadas (mesma estrategia de _wrap_data_rows_with_loop)."""
    tbl_re = re.compile(r"<w:tbl\b[\s\S]*?</w:tbl>")
    row_re = re.compile(r"<w:tr\b[\s\S]*?</w:tr>")
    cell_re = re.compile(r"<w:tc\b[^>]*>[\s\S]*?</w:tc>")

    for tm in tbl_re.finditer(xml, start_after):
        tbl = tm.group(0)
        text = _para_text(tbl)
        if "Categoria" not in text or "Sócio" not in text or "Valor por Hora" not in text:
            continue
        rows = list(row_re.finditer(tbl))
        if len(rows) < 2:
            print(f"  ! tabela de senioridade tem menos de 2 rows")
            return xml, tm.end()

        body_row = rows[1].group(0)
        cells = list(cell_re.finditer(body_row))
        if len(cells) < 2:
            print("  ! row-template de senioridade tem menos de 2 celulas")
            return xml, tm.end()

        new_first_cell = _replace_cell_with_placeholder(cells[0].group(0), "{{" + loop_var + ".categoria}}")
        new_last_cell = _replace_cell_with_placeholder(cells[-1].group(0), "{{" + loop_var + ".valor}}")
        new_body_row = (
            body_row[: cells[-1].start()] + new_last_cell + body_row[cells[-1].end():]
        )
        new_body_row = (
            new_body_row[: cells[0].start()] + new_first_cell + new_body_row[cells[0].end():]
        )

        for_row = tr_for_row(new_body_row, loop_var, iterable)
        endfor_row = tr_endfor_row(new_body_row)

        header_row = rows[0].group(0)
        before_first_row = tbl[: rows[0].start()]
        after_last_row = tbl[rows[-1].end():]
        new_tbl = (
            before_first_row + header_row
            + for_row + new_body_row + endfor_row
            + after_last_row
        )

        new_xml = xml[: tm.start()] + new_tbl + xml[tm.end():]
        return new_xml, tm.start() + len(new_tbl)

    print(f"  ! tabela de senioridade nao encontrada apos posicao {start_after}")
    return xml, len(xml)


def transform_senioridade_tables(xml: str) -> str:
    xml, end_pos = _convert_senioridade_to_loop(xml, "s", "consultiva.tabela_senioridade")
    xml, _ = _convert_senioridade_to_loop(xml, "s", "contenciosa.horas_extra_senioridade", start_after=end_pos)
    return xml


def transform_loop_tables(xml: str) -> str:
    xml = _wrap_data_rows_with_loop(
        xml,
        table_anchor="{{Natureza}}",
        header_anchor="Natureza da Ação",
        loop_var="it",
        iterable="contenciosa.tabela_acoes",
        field_replacements=[
            ("{{Natureza}}",     "{{it.natureza}}"),
            ("{{Fase}}",         "{{it.fase}}"),
            ("{{R$ XXXX,XX}}",   "{{it.valor}}"),
        ],
    )
    xml = _wrap_data_rows_with_loop(
        xml,
        table_anchor="Petição Inicial",
        header_anchor="Ato Processual",
        loop_var="it",
        iterable="contenciosa.tabela_atos",
        field_replacements=[
            ("Petição Inicial",  "{{it.ato}}"),
            ("Elaboração e protocolo da peça inaugural.", "{{it.descricao}}"),
            ("{{R$ XXXX,XX}}",   "{{it.valor}}"),
        ],
    )
    return xml


def replace_scalar_fields(xml: str) -> str:
    row_re = re.compile(r"<w:tr\b[^>]*>.*?</w:tr>", flags=re.DOTALL)
    cell_re = re.compile(r"<w:tc\b[^>]*>.*?</w:tc>", flags=re.DOTALL)

    def first_cell_text(row_xml: str) -> str:
        cells = list(cell_re.finditer(row_xml))
        if not cells:
            return ""
        return _para_text(cells[0].group(0)).strip()

    for row_label, placeholder, replacement, occurrence in SCALAR_FIELD_REPLACEMENTS:
        matched_rows = [m for m in row_re.finditer(xml) if first_cell_text(m.group(0)) == row_label]
        if occurrence >= len(matched_rows):
            print(f"  ! linha #{occurrence} com label {row_label!r} nao encontrada (apenas {len(matched_rows)})")
            continue
        m = matched_rows[occurrence]
        row = m.group(0)
        if placeholder not in row:
            print(f"  ! placeholder {placeholder!r} nao esta na linha {row_label!r} #{occurrence}")
            continue
        new_row = row.replace(placeholder, replacement, 1)
        xml = xml[: m.start()] + new_row + xml[m.end():]

    return xml


def inject_lost_placeholders(xml: str) -> str:
    row_re = re.compile(r"<w:tr\b[^>]*>.*?</w:tr>", flags=re.DOTALL)
    cell_re = re.compile(r"<w:tc\b[^>]*>.*?</w:tc>", flags=re.DOTALL)

    def empty_cell(cell_xml: str) -> bool:
        return not _para_text(cell_xml).strip()

    for label, tag in LOST_PLACEHOLDERS:
        for m in row_re.finditer(xml):
            row = m.group(0)
            if label not in _para_text(row):
                continue
            cells = list(cell_re.finditer(row))
            empties = [c for c in cells if empty_cell(c.group(0))]
            if not empties:
                continue
            target = empties[0]
            new_para = (
                f'<w:p><w:pPr><w:snapToGrid w:val="0"/>'
                f'<w:rPr><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:pPr>'
                f'<w:r><w:rPr><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
                f'<w:t xml:space="preserve">{tag}</w:t></w:r></w:p>'
            )
            new_cell = target.group(0).replace("</w:tc>", new_para + "</w:tc>", 1)
            new_row = row[: target.start()] + new_cell + row[target.end():]
            xml = xml[: m.start()] + new_row + xml[m.end():]
            break
    return xml


# -- Step 6: condicionais (envoltorios de paragrafo / linha / range) ---------
def wrap_table_row_containing(xml: str, anchor: str, cond: str) -> str:
    """Insere uma marker-row com {%tr if cond %} ANTES da linha com `anchor`
    e outra com {%tr endif %} DEPOIS. docxtpl remove as marker-rows e envolve
    a linha-alvo com {% if cond %}...{% endif %}."""
    row_re = re.compile(r"<w:tr\b[^>]*>.*?</w:tr>", flags=re.DOTALL)

    for m in row_re.finditer(xml):
        row = m.group(0)
        if anchor not in _para_text(row):
            continue

        before = tr_if_row(row, cond)
        after = tr_endif_row(row)
        return xml[: m.start()] + before + row + after + xml[m.end():]

    print(f"  ! linha com {anchor!r} nao encontrada")
    return xml


def wrap_paragraph_containing(xml: str, anchor: str, cond: str, *, predicate=None) -> str:
    """Coloca {%p if cond %} antes e {%p endif %} depois do paragrafo com `anchor`."""
    found = _find_paragraph(xml, anchor, predicate=predicate)
    if not found:
        print(f"  ! paragrafo com {anchor!r} nao encontrado")
        return xml
    s, e = found
    return xml[:s] + p_if(cond) + xml[s:e] + p_endif() + xml[e:]


def wrap_range(
    xml: str,
    start_anchor: str,
    end_anchor: str,
    cond: str,
    *,
    inclusive_end: bool = True,
    start_predicate=None,
    end_predicate=None,
    search_start: int = 0,
) -> str:
    """Insere {%p if cond %}/{%p endif %} ao redor do range entre os ancoras."""
    start = _find_paragraph(xml, start_anchor, start=search_start, predicate=start_predicate)
    if not start:
        print(f"  ! anchor inicial nao encontrado: {start_anchor!r}")
        return xml
    end = _find_paragraph(xml, end_anchor, start=start[1], predicate=end_predicate)
    if not end:
        print(f"  ! anchor final nao encontrado: {end_anchor!r}")
        return xml

    open_pos = _before_enclosing_table(xml, start[0])
    if inclusive_end:
        close_pos = _after_enclosing_table(xml, end[1])
    else:
        close_pos = _before_enclosing_table(xml, end[0])

    return xml[:open_pos] + p_if(cond) + xml[open_pos:close_pos] + p_endif() + xml[close_pos:]


def add_conditionals(xml: str) -> str:
    # --- Linhas individuais ---
    xml = wrap_table_row_containing(xml, "Contatos", "contratante.contatos_texto")
    xml = wrap_table_row_containing(
        xml, "Taxa de Manutenção Processual", "despesas.show_taxa_manutencao"
    )

    # --- Identificacao do Contratante (PF/PJ) ---
    xml = wrap_paragraph_containing(
        xml, "Nome", "contratante.pf", predicate=lambda t: t.strip() == "Nome"
    )
    xml = wrap_paragraph_containing(
        xml, "Razão Social", "contratante.pj", predicate=lambda t: t.strip() == "Razão Social"
    )
    xml = wrap_paragraph_containing(
        xml, "CPF", "contratante.pf", predicate=lambda t: t.strip() == "CPF"
    )
    xml = wrap_paragraph_containing(
        xml, "CNPJ", "contratante.pj", predicate=lambda t: t.strip() == "CNPJ"
    )

    # --- SLA ---
    xml = wrap_range(
        xml, "SLA", "{{escopo.sla_descricao}}", "escopo.show_sla",
        start_predicate=lambda t: t.strip() == "SLA",
    )

    # --- Atuacao Consultiva / Contenciosa (linha + descricao) ---
    xml = wrap_range(
        xml, "Atuação Consultiva", "{{escopo.atuacao_consultiva}}", "escopo.show_consultiva",
    )
    xml = wrap_range(
        xml, "Atuação Contenciosa", "{{escopo.atuacao_contenciosa}}", "escopo.show_contenciosa",
    )

    # --- Secao 3 e 4 inteiras ---
    xml = wrap_range(
        xml,
        "HONORÁRIOS DA ATUAÇÃO CONSULTIVA",
        "HONORÁRIOS DE ASSESSORIA CONTENCIOSA",
        "escopo.show_consultiva",
        inclusive_end=False,
    )
    xml = wrap_range(
        xml,
        "HONORÁRIOS DE ASSESSORIA CONTENCIOSA",
        "DESPESAS APLICÁVEIS A ESTE ESCOPO",
        "escopo.show_contenciosa",
        inclusive_end=False,
    )

    # --- Disposicoes Especificas (secao 6 inteira) ---
    xml = wrap_range(
        xml,
        "DISPOSIÇÕES ESPECÍFICAS",
        "TERMOS E CONDIÇÕES",
        "disposicoes.show",
        inclusive_end=False,
    )

    # --- Modalidades de honorarios consultivos ---
    xml = wrap_range(
        xml,
        "Hora por Nível de Senioridade",
        "Hora Fixa (independente do executor)",
        "consultiva.show_hora_senioridade",
        inclusive_end=False,
    )
    xml = wrap_range(
        xml,
        "Hora Fixa (independente do executor)",
        "Fixo Mensal",
        "consultiva.show_hora_fixa",
        inclusive_end=False,
    )
    xml = wrap_range(
        xml,
        "Fixo Mensal",
        "Valor do Projeto",
        "consultiva.show_fixo_mensal",
        inclusive_end=False,
    )
    xml = wrap_range(
        xml,
        "Valor do Projeto",
        "{%p endif %}",
        "consultiva.show_valor_projeto",
        inclusive_end=False,
    )

    # --- Modalidades contenciosas ---
    xml = wrap_range(
        xml,
        "Valor por Ação",
        "Valor por Ato Processual",
        "contenciosa.show_valor_acao",
        inclusive_end=False,
    )
    xml = wrap_range(
        xml,
        "Valor por Ato Processual",
        "Preço Mensal",
        "contenciosa.show_valor_ato",
        inclusive_end=False,
    )
    xml = wrap_range(
        xml,
        "Preço Mensal",
        "Valor por Projeto",
        "contenciosa.show_preco_mensal",
        inclusive_end=False,
    )
    xml = wrap_range(
        xml,
        "Valor por Projeto",
        "Honorários de Êxito",
        "contenciosa.show_valor_projeto",
        inclusive_end=False,
    )

    # --- Honorarios de Exito ---
    xml = wrap_range(
        xml,
        "Honorários de Êxito",
        "Horas para Serviços Extra Escopo",
        "contenciosa.show_exito",
        inclusive_end=False,
    )

    # --- Horas Extra Escopo: Tabela por Senioridade ---
    xml = wrap_range(
        xml,
        "Aplicar-se-á a tabela abaixo, independentemente da modalidade principal",
        "Hora Fixa (independente do executor)",
        "contenciosa.show_extra_senioridade",
        inclusive_end=False,
    )

    # --- Horas Extra Escopo: Hora Fixa (2a ocorrencia) ---
    # Posicao do bloco show_extra_senioridade serve como search_start: assim
    # _find_paragraph pula a 1a ocorrencia de "Hora Fixa..." (consultiva) e
    # encontra a 2a (contenciosa). O end_anchor "{%p endif %}" cai no endif
    # de show_contenciosa que fecha a secao 4.
    sen_open_idx = xml.find("{%p if contenciosa.show_extra_senioridade %}")
    xml = wrap_range(
        xml,
        "Hora Fixa (independente do executor)",
        "{%p endif %}",
        "contenciosa.show_extra_hora_fixa",
        inclusive_end=False,
        search_start=sen_open_idx if sen_open_idx >= 0 else 0,
    )

    return xml


# -- Step 7: neutralizar placeholders restantes (impossiveis em Jinja2) ------
LEFTOVER_RE = re.compile(r"\{\{([^{}]+)\}\}")
VALID_JINJA_VAR = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")


def neutralize_leftover_placeholders(xml: str) -> str:
    def repl(m):
        content = m.group(1).strip()
        if VALID_JINJA_VAR.match(content):
            return m.group(0)
        # Drop braces, keep visible text como referencia para o usuario.
        return content
    return LEFTOVER_RE.sub(repl, xml)


# -- Pipeline ------------------------------------------------------------------
def transform_document_xml(xml: str) -> str:
    print("[1/8] Removendo runs de instrucao (cor EE0000)...")
    xml = remove_red_runs(xml)
    print("[2/8] Substituindo placeholders por tags Jinja2...")
    xml = replace_placeholders(xml)
    print("[3/8] Reinjetando placeholders perdidos...")
    xml = inject_lost_placeholders(xml)
    print("[4/8] Substituindo placeholders escalares posicionalmente...")
    xml = replace_scalar_fields(xml)
    print("[5/8] Conectando campos de Despesas Gerais/Especificas...")
    xml = replace_despesas_value_cells(xml)
    print("[6/8] Convertendo tabelas dinamicas em loops (Acoes, Atos)...")
    xml = transform_loop_tables(xml)
    print("[7/8] Convertendo tabelas de Senioridade em loops...")
    xml = transform_senioridade_tables(xml)
    print("[8/8] Inserindo marcadores condicionais...")
    xml = add_conditionals(xml)
    print("[*] Neutralizando placeholders mustache restantes...")
    xml = neutralize_leftover_placeholders(xml)
    return xml


def build_template(source: Path, dest: Path) -> None:
    if not source.exists():
        raise SystemExit(f"Template original nao encontrado em {source}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp.docx")

    with zipfile.ZipFile(source, "r") as zin:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "word/document.xml":
                    xml = data.decode("utf-8")
                    xml = transform_document_xml(xml)
                    data = xml.encode("utf-8")
                zout.writestr(item, data)

    shutil.move(str(tmp), str(dest))
    print(f"\nTemplate gerado em: {dest}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Converter PMRA Escopo Misto -> Template Jinja2 (docxtpl)")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    args = parser.parse_args()
    build_template(args.source, args.dest)


if __name__ == "__main__":
    main()
