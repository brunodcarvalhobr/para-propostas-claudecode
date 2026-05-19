"""Atualiza PMRA_Template_Jinja.docx para suporte a múltiplos escopos.

Operações (idempotente — parte sempre do backup .bak):
1. Restaura o backup do template original
2. Adiciona loops {%p for %} para múltiplos textos de escopo (consultivo/contencioso)
   - Justificação
   - Parágrafo em branco entre items
3. Adiciona loops para múltiplos blocos de honorários por escopo
   - Conteúdo via {{r hon.subdoc}} (subdocs construídos em template_engine.py)
   - Mantém tabelas (senioridade, ações, atos) com formatação original
4. Êxito e Horas Extra ficam SEMPRE renderizados quando há atuação contenciosa,
   independente de forma_por_escopo
"""
from __future__ import annotations

import os
import re
import shutil
import zipfile
from pathlib import Path

TEMPLATE_PATH = Path("resources/templates/PMRA_Template_Jinja.docx")
BACKUP_PATH = Path("resources/templates/PMRA_Template_Jinja.docx.bak")


def _make_tag_para(template_para: str, new_tag: str) -> str:
    """Cria novo parágrafo de tag substituindo o conteúdo <w:t> pelo novo texto."""
    return re.sub(r'<w:t>[^<]*</w:t>', f'<w:t>{new_tag}</w:t>', template_para, count=1)


def _make_title_para(template_para: str, new_text: str) -> str:
    """Cria parágrafo de título (bold sz=20, Arvo, justificado)."""
    ppr_match = re.search(r'<w:pPr>.*?</w:pPr>', template_para, re.DOTALL)
    ppr_inner = ''
    if ppr_match:
        # extrai conteúdo interno do pPr e adiciona w:jc justify
        inner = re.search(r'<w:pPr>(.*?)</w:pPr>', template_para, re.DOTALL).group(1)
        # remove jc existente (se houver) e adiciona justify
        inner = re.sub(r'<w:jc [^/]*/>', '', inner)
        ppr_inner = inner + '<w:jc w:val="both"/>'
    ppr = f'<w:pPr>{ppr_inner}</w:pPr>'

    p_attrs = re.match(r'<w:p([^>]*)>', template_para).group(1)
    return (
        f'<w:p{p_attrs}>{ppr}'
        f'<w:r><w:rPr><w:rFonts w:ascii="Arvo" w:hAnsi="Arvo"/><w:b/><w:bCs/>'
        f'<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
        f'<w:t xml:space="preserve">{new_text}</w:t></w:r>'
        f'</w:p>'
    )


def _make_section_heading_para(template_para: str, new_text: str) -> str:
    """Cria parágrafo de título de seção (bold + sublinhado, sz=20, Arvo)."""
    ppr_match = re.search(r'<w:pPr>(.*?)</w:pPr>', template_para, re.DOTALL)
    ppr_inner = ''
    if ppr_match:
        inner = ppr_match.group(1)
        inner = re.sub(r'<w:jc [^/]*/>', '', inner)
        ppr_inner = inner + '<w:jc w:val="both"/>'
    ppr = f'<w:pPr>{ppr_inner}</w:pPr>'

    p_attrs = re.match(r'<w:p([^>]*)>', template_para).group(1)
    return (
        f'<w:p{p_attrs}>{ppr}'
        f'<w:r><w:rPr><w:rFonts w:ascii="Arvo" w:hAnsi="Arvo"/><w:b/><w:bCs/>'
        f'<w:u w:val="single"/>'
        f'<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
        f'<w:t xml:space="preserve">{new_text}</w:t></w:r>'
        f'</w:p>'
    )


def _make_content_para(template_para: str, new_text: str) -> str:
    """Cria parágrafo de conteúdo normal (sz=20, Arvo, justificado)."""
    ppr_inner = ''
    ppr_match = re.search(r'<w:pPr>(.*?)</w:pPr>', template_para, re.DOTALL)
    if ppr_match:
        inner = ppr_match.group(1)
        inner = re.sub(r'<w:jc [^/]*/>', '', inner)
        ppr_inner = inner + '<w:jc w:val="both"/>'
    ppr = f'<w:pPr>{ppr_inner}</w:pPr>'

    p_attrs = re.match(r'<w:p([^>]*)>', template_para).group(1)
    return (
        f'<w:p{p_attrs}>{ppr}'
        f'<w:r><w:rPr><w:rFonts w:ascii="Arvo" w:hAnsi="Arvo"/>'
        f'<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
        f'<w:t xml:space="preserve">{new_text}</w:t></w:r>'
        f'</w:p>'
    )


def _make_blank_para(template_para: str) -> str:
    """Cria parágrafo em branco (espaço entre items dos loops)."""
    p_attrs = re.match(r'<w:p([^>]*)>', template_para).group(1)
    return (
        f'<w:p{p_attrs}>'
        f'<w:pPr><w:spacing w:line="276" w:lineRule="auto"/>'
        f'<w:rPr><w:rFonts w:ascii="Arvo" w:hAnsi="Arvo"/>'
        f'<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:pPr>'
        f'</w:p>'
    )


def update_template(xml: str) -> str:
    paras = re.findall(r'<w:p[ >].*?</w:p>', xml, re.DOTALL)

    # Templates de referência (parágrafos do .docx original)
    p_tag        = paras[16]   # parágrafo de tag: {%p if escopo.show_consultiva %}
    p_title      = paras[17]   # "Escopo Consultivo:" (bold sz=20)
    p_content    = paras[18]   # {{escopo.atuacao_consultiva}} (sz=20)
    p_title_cont = paras[27]   # "Escopo Contencioso:" (bold sz=20)
    p_content_cont = paras[28]

    # ── 1. Escopo consultivo (paras 16-19): modo legado + bloco multi
    p16_orig = paras[16]
    p16_new  = _make_tag_para(p16_orig, '{%p if escopo.show_consultiva and not escopo.multi_consultiva %}')

    multi_cons_block = [
        _make_tag_para(p_tag, '{%p if escopo.show_consultiva and escopo.multi_consultiva %}'),
        _make_tag_para(p_tag, '{%p for item in escopo.itens_consultivos %}'),
        _make_title_para(p_title,   'Escopo Consultivo {{item.letra}}:'),
        _make_blank_para(p_content),
        _make_content_para(p_content, '{{item.descricao}}'),
        _make_blank_para(p_content),
        _make_tag_para(p_tag, '{%p endfor %}'),
        _make_tag_para(p_tag, '{%p endif %}'),
    ]

    # ── 2. Escopo contencioso (paras 26-29): modo legado + bloco multi
    p26_orig = paras[26]
    p26_new  = _make_tag_para(p26_orig, '{%p if escopo.show_contenciosa and not escopo.multi_contenciosa %}')

    multi_cont_block = [
        _make_tag_para(p_tag, '{%p if escopo.show_contenciosa and escopo.multi_contenciosa %}'),
        _make_tag_para(p_tag, '{%p for item in escopo.itens_contenciosos %}'),
        _make_title_para(p_title_cont,   'Escopo Contencioso {{item.letra}}:'),
        _make_blank_para(p_content_cont),
        _make_content_para(p_content_cont, '{{item.descricao}}'),
        _make_blank_para(p_content_cont),
        _make_tag_para(p_tag, '{%p endfor %}'),
        _make_tag_para(p_tag, '{%p endif %}'),
    ]

    # ── 3. Honorários consultivos (para 31): envolver com not forma_por_escopo
    p31_orig = paras[31]
    p31_new  = _make_tag_para(p31_orig, '{%p if escopo.show_consultiva and not consultiva.forma_por_escopo %}')

    # Bloco multi para honorários consultivos: usa subdoc (construído em template_engine.py)
    hon_cons_multi = [
        _make_tag_para(p_tag, '{%p if escopo.show_consultiva and consultiva.forma_por_escopo %}'),
        _make_section_heading_para(p_title, 'Honorários Propostos para os Escopos Consultivos'),
        _make_blank_para(p_content),
        _make_tag_para(p_tag, '{%p for hon in consultiva.itens %}'),
        # {{p hon.subdoc}} renderiza o subdoc com conteúdo formatado + tabelas
        _make_tag_para(p_tag, '{{p hon.subdoc}}'),
        _make_tag_para(p_tag, '{%p endfor %}'),
        _make_tag_para(p_tag, '{%p endif %}'),
    ]

    # ── 4. Honorários contenciosos (para 84): envolver com not forma_por_escopo
    # Mas Êxito (para 147) e Horas Extra (para 158-179) devem ficar FORA do condicional.
    # Estratégia: o {%p endif %} original (para 180) fecha o show_contenciosa.
    # Vamos:
    #   - Trocar para 84 para "and not contenciosa.forma_por_escopo"
    #   - Inserir um {%p endif %} ANTES do {%p if contenciosa.show_exito %} (para 147)
    #   - Inserir um {%p if escopo.show_contenciosa %} APÓS o endif acima
    p84_orig = paras[84]
    p84_new  = _make_tag_para(p84_orig, '{%p if escopo.show_contenciosa and not contenciosa.forma_por_escopo %}')

    p147_orig = paras[147]  # {%p if contenciosa.show_exito %}
    extra_endif = _make_tag_para(p_tag, '{%p endif %}')
    open_exito  = _make_tag_para(p_tag, '{%p if escopo.show_contenciosa %}')

    # Bloco multi para honorários contenciosos (após para 180)
    hon_cont_multi = [
        _make_tag_para(p_tag, '{%p if escopo.show_contenciosa and contenciosa.forma_por_escopo %}'),
        _make_section_heading_para(p_title_cont, 'Honorários Propostos para os Escopos Contenciosos'),
        _make_blank_para(p_content_cont),
        _make_tag_para(p_tag, '{%p for hon in contenciosa.itens %}'),
        _make_tag_para(p_tag, '{{p hon.subdoc}}'),
        _make_tag_para(p_tag, '{%p endfor %}'),
        _make_tag_para(p_tag, '{%p endif %}'),
    ]

    # ── Aplicar todas as substituições (ordem importa: do final para o início para
    # não invalidar índices, mas como usamos .replace por conteúdo, ordem por
    # parágrafo único basta)

    # 1. Modificar para 16 e inserir bloco multi consultivo após para 19
    xml = xml.replace(p16_orig, p16_new, 1)
    p19 = paras[19]
    xml = xml.replace(p19, p19 + ''.join(multi_cons_block), 1)

    # 2. Modificar para 26 e inserir bloco multi contencioso após para 29
    xml = xml.replace(p26_orig, p26_new, 1)
    p29 = paras[29]
    xml = xml.replace(p29, p29 + ''.join(multi_cont_block), 1)

    # 3. Modificar para 31 e inserir bloco multi honorários consultivos após para 82
    xml = xml.replace(p31_orig, p31_new, 1)
    p82 = paras[82]
    xml = xml.replace(p82, p82 + ''.join(hon_cons_multi), 1)

    # 4. Modificar para 84
    xml = xml.replace(p84_orig, p84_new, 1)

    # 5. Inserir extra_endif + open_exito ANTES do para 147 (if show_exito)
    xml = xml.replace(p147_orig, extra_endif + open_exito + p147_orig, 1)

    # 6. Inserir bloco multi honorários contenciosos após para 180
    p180 = paras[180]
    xml = xml.replace(p180, p180 + ''.join(hon_cont_multi), 1)

    # 7. SLA heading: tornar dinâmico ({{escopo.sla_titulo}}) + parágrafo em branco após
    sla_heading_para = next((p for p in paras if 'Prazos de Entrega' in p), None)
    sla_desc_para    = next((p for p in paras if 'escopo.sla_descricao' in p), None)
    if sla_heading_para:
        sla_heading_new = _make_section_heading_para(sla_heading_para, '{{escopo.sla_titulo}}')
        xml = xml.replace(sla_heading_para, sla_heading_new, 1)
    if sla_desc_para:
        blank_before_sla = _make_blank_para(sla_desc_para)
        xml = xml.replace(sla_desc_para, blank_before_sla + sla_desc_para, 1)

    # 8. "Condições Específicas": parágrafo em branco entre título e descrição
    disp_desc_para = next((p for p in paras if 'disposicoes.descricao' in p), None)
    if disp_desc_para:
        blank_before_disp = _make_blank_para(disp_desc_para)
        xml = xml.replace(disp_desc_para, blank_before_disp + disp_desc_para, 1)

    return xml


def main() -> None:
    if not BACKUP_PATH.exists():
        # Cria backup se não existe (primeira execução pós-restauração)
        shutil.copy2(TEMPLATE_PATH, BACKUP_PATH)
        print(f"Backup criado: {BACKUP_PATH}")

    # Sempre parte do backup para ser idempotente
    shutil.copy2(BACKUP_PATH, TEMPLATE_PATH)
    print(f"Template restaurado do backup")

    with zipfile.ZipFile(TEMPLATE_PATH) as z:
        xml = z.read('word/document.xml').decode('utf-8')
        others = {n: z.read(n) for n in z.namelist() if n != 'word/document.xml'}

    new_xml = update_template(xml)

    tmp = str(TEMPLATE_PATH) + '.tmp'
    with zipfile.ZipFile(tmp, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        zout.writestr('word/document.xml', new_xml.encode('utf-8'))
        for n, d in others.items():
            zout.writestr(n, d)
    os.replace(tmp, TEMPLATE_PATH)
    print(f"Template atualizado: {TEMPLATE_PATH}")

    # Verificações
    checks = [
        'not escopo.multi_consultiva',
        'for item in escopo.itens_consultivos',
        'not escopo.multi_contenciosa',
        'for item in escopo.itens_contenciosos',
        'not consultiva.forma_por_escopo',
        'for hon in consultiva.itens',
        'not contenciosa.forma_por_escopo',
        'for hon in contenciosa.itens',
        '{{p hon.subdoc}}',
        '{%p if contenciosa.show_exito %}',
        'Honorários Propostos para os Escopos Consultivos',
        'Honorários Propostos para os Escopos Contenciosos',
        '{{escopo.sla_titulo}}',
    ]
    print("\nVerificações:")
    for c in checks:
        ok = c in new_xml
        print(f'  {"✓" if ok else "✗"}  {c}')


if __name__ == '__main__':
    main()
