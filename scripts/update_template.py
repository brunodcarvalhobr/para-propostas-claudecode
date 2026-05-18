"""Script para atualizar PMRA_Template_Jinja.docx com suporte a múltiplos escopos.

Executa as seguintes modificações no template Word:
1. Seção de escopo consultivo: adiciona loop para múltiplos escopos
2. Seção de escopo contencioso: idem
3. Seção de honorários consultivos: adiciona bloco para forma_por_escopo
4. Seção de honorários contenciosos: idem
"""
from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

TEMPLATE_PATH = Path("resources/templates/PMRA_Template_Jinja.docx")
BACKUP_PATH = Path("resources/templates/PMRA_Template_Jinja.docx.bak")


def _extract_tag_para_xml(paras: list[str], index: int) -> str:
    """Retorna o XML de um parágrafo de tag (substituindo apenas o texto)."""
    return paras[index]


def _make_tag_para(template_para: str, new_tag_text: str) -> str:
    """Cria um novo parágrafo de tag substituindo o conteúdo <w:t> pelo novo texto."""
    return re.sub(r'<w:t>[^<]*</w:t>', f'<w:t>{new_tag_text}</w:t>', template_para, count=1)


def _make_title_para(template_para: str, new_text: str) -> str:
    """Cria um parágrafo de título (bold, sz=20) com novo texto em um único run."""
    # Pegar o pPr (formatação de parágrafo)
    ppr_match = re.search(r'<w:pPr>.*?</w:pPr>', template_para, re.DOTALL)
    ppr = ppr_match.group(0) if ppr_match else ''

    # Pegar o rPr do primeiro run (bold, sz=20)
    rpr_match = re.search(r'<w:rPr>.*?</w:rPr>', template_para, re.DOTALL)
    rpr = rpr_match.group(0) if rpr_match else ''

    # Pegar atributos do w:p
    p_attrs_match = re.match(r'<w:p([^>]*)>', template_para)
    p_attrs = p_attrs_match.group(1) if p_attrs_match else ''

    return (
        f'<w:p{p_attrs}>'
        f'{ppr}'
        f'<w:r><w:rPr><w:rFonts w:ascii="Arvo" w:hAnsi="Arvo"/><w:b/><w:bCs/>'
        f'<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
        f'<w:t>{new_text}</w:t></w:r>'
        f'</w:p>'
    )


def _make_content_para(template_para: str, new_text: str) -> str:
    """Cria um parágrafo de conteúdo (normal, sz=20) com novo texto."""
    ppr_match = re.search(r'<w:pPr>.*?</w:pPr>', template_para, re.DOTALL)
    ppr = ppr_match.group(0) if ppr_match else ''
    p_attrs_match = re.match(r'<w:p([^>]*)>', template_para)
    p_attrs = p_attrs_match.group(1) if p_attrs_match else ''

    return (
        f'<w:p{p_attrs}>'
        f'{ppr}'
        f'<w:r><w:rPr><w:rFonts w:ascii="Arvo" w:hAnsi="Arvo"/>'
        f'<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
        f'<w:t xml:space="preserve">{new_text}</w:t></w:r>'
        f'</w:p>'
    )


def update_template(xml: str) -> str:
    paras = re.findall(r'<w:p[ >].*?</w:p>', xml, re.DOTALL)

    # ── 1. Seção de escopo consultivo (paras 16-19)
    # Mudar {%p if escopo.show_consultiva %} → add "and not escopo.multi_consultiva"
    p16_original = paras[16]
    p16_modified = _make_tag_para(p16_original, '{%p if escopo.show_consultiva and not escopo.multi_consultiva %}')

    # Bloco a inserir após para 19 ({%p endif %})
    p16_tag_para = paras[16]  # Template para parágrafos de tag (sz=2)
    p17_title_para = paras[17]  # Template para parágrafos de título (bold sz=20)
    p18_content_para = paras[18]  # Template para conteúdo (sz=20)
    p19_end_para = paras[19]    # {%p endif %}

    multi_cons_block = [
        _make_tag_para(p16_tag_para, '{%p if escopo.show_consultiva and escopo.multi_consultiva %}'),
        _make_tag_para(p16_tag_para, '{%p for item in escopo.itens_consultivos %}'),
        _make_title_para(p17_title_para, 'Escopo Consultivo {{item.letra}}:'),
        _make_content_para(p18_content_para, '{{item.descricao}}'),
        _make_tag_para(p16_tag_para, '{%p endfor %}'),
        _make_tag_para(p16_tag_para, '{%p endif %}'),
    ]

    # ── 2. Seção de escopo contencioso (paras 26-29)
    p26_original = paras[26]
    p26_modified = _make_tag_para(p26_original, '{%p if escopo.show_contenciosa and not escopo.multi_contenciosa %}')
    p27_title_para = paras[27]  # "Escopo Contencioso:" (bold sz=20)
    p28_content_para = paras[28]  # {{escopo.atuacao_contenciosa}} (sz=20)

    multi_cont_block = [
        _make_tag_para(p16_tag_para, '{%p if escopo.show_contenciosa and escopo.multi_contenciosa %}'),
        _make_tag_para(p16_tag_para, '{%p for item in escopo.itens_contenciosos %}'),
        _make_title_para(p27_title_para, 'Escopo Contencioso {{item.letra}}:'),
        _make_content_para(p28_content_para, '{{item.descricao}}'),
        _make_tag_para(p16_tag_para, '{%p endfor %}'),
        _make_tag_para(p16_tag_para, '{%p endif %}'),
    ]

    # ── 3. Honorários consultivos (para 31): adicionar "and not consultiva.forma_por_escopo"
    p31_original = paras[31]
    p31_modified = _make_tag_para(p31_original, '{%p if escopo.show_consultiva and not consultiva.forma_por_escopo %}')

    # Bloco a inserir após para 82 (endif dos honorários consultivos)
    # Para honorários por escopo (forma_por_escopo=True), usar bloco simplificado
    # com texto em vez de tabelas (docxtpl não suporta tabelas dentro de {%p for %})
    hon_cons_multi_block = [
        _make_tag_para(p16_tag_para, '{%p if escopo.show_consultiva and consultiva.forma_por_escopo %}'),
        _make_tag_para(p16_tag_para, '{%p for hon in consultiva.itens %}'),
        _make_title_para(p17_title_para, 'Honor&#225;rios &#8212; Escopo Consultivo {{hon.letra}}'),
        _make_tag_para(p16_tag_para, '{%p if hon.show_hora_senioridade %}'),
        _make_content_para(p18_content_para, 'Os honor&#225;rios ser&#227;o apurados conforme tabela de senioridade: {{hon.tabela_senioridade_texto}}'),
        _make_tag_para(p16_tag_para, '{%p endif %}'),
        _make_tag_para(p16_tag_para, '{%p if hon.show_hora_fixa %}'),
        _make_content_para(p18_content_para, 'Os honor&#225;rios ser&#227;o apurados com base em valor hor&#225;rio &#250;nico de {{hon.hora_fixa_valor}} por hora.'),
        _make_tag_para(p16_tag_para, '{%p endif %}'),
        _make_tag_para(p16_tag_para, '{%p if hon.show_fixo_mensal %}'),
        _make_content_para(p18_content_para, 'Honor&#225;rios fixos mensais: {{hon.fixo_mensal_valor}} / Cap: {{hon.fixo_mensal_cap}} horas / Hora excedente: {{hon.fixo_mensal_excedente}}.'),
        _make_tag_para(p16_tag_para, '{%p endif %}'),
        _make_tag_para(p16_tag_para, '{%p if hon.show_valor_projeto %}'),
        _make_content_para(p18_content_para, 'Pre&#231;o global: {{hon.valor_projeto_total}}{% if hon.show_valor_projeto_cap %} / Cap: {{hon.valor_projeto_cap}} horas{% endif %}. {{hon.valor_projeto_forma_pagamento}}'),
        _make_tag_para(p16_tag_para, '{%p endif %}'),
        _make_tag_para(p16_tag_para, '{%p endfor %}'),
        _make_tag_para(p16_tag_para, '{%p endif %}'),
    ]

    # ── 4. Honorários contenciosos (para 84): adicionar "and not contenciosa.forma_por_escopo"
    p84_original = paras[84]
    p84_modified = _make_tag_para(p84_original, '{%p if escopo.show_contenciosa and not contenciosa.forma_por_escopo %}')

    # Bloco após para 180 (endif dos honorários contenciosos)
    hon_cont_multi_block = [
        _make_tag_para(p16_tag_para, '{%p if escopo.show_contenciosa and contenciosa.forma_por_escopo %}'),
        _make_tag_para(p16_tag_para, '{%p for hon in contenciosa.itens %}'),
        _make_title_para(p17_title_para, 'Honor&#225;rios &#8212; Escopo Contencioso {{hon.letra}}'),
        _make_tag_para(p16_tag_para, '{%p if hon.show_valor_acao %}'),
        _make_content_para(p18_content_para, 'Valor mensal por processo: {{hon.tabela_acoes_texto}}'),
        _make_tag_para(p16_tag_para, '{%p endif %}'),
        _make_tag_para(p16_tag_para, '{%p if hon.show_valor_ato %}'),
        _make_content_para(p18_content_para, 'Valor por ato processual: {{hon.tabela_atos_texto}}'),
        _make_tag_para(p16_tag_para, '{%p endif %}'),
        _make_tag_para(p16_tag_para, '{%p if hon.show_preco_mensal %}'),
        _make_content_para(p18_content_para, 'Pre&#231;o mensal fixo: {{hon.preco_mensal_valor}} / M&#225;ximo: {{hon.preco_mensal_maximo_acoes}} a&#231;&#245;es. {{hon.preco_mensal_criterio_excedentes}}'),
        _make_tag_para(p16_tag_para, '{%p endif %}'),
        _make_tag_para(p16_tag_para, '{%p if hon.show_valor_projeto %}'),
        _make_content_para(p18_content_para, 'Pre&#231;o global contencioso: {{hon.valor_projeto_total}} / Fases: {{hon.valor_projeto_fases_cobertas}}. {{hon.valor_projeto_forma_pagamento}}'),
        _make_tag_para(p16_tag_para, '{%p endif %}'),
        _make_tag_para(p16_tag_para, '{%p endfor %}'),
        _make_tag_para(p16_tag_para, '{%p endif %}'),
    ]

    # ── Aplicar modificações no XML
    # 1. Substituir para 16
    xml = xml.replace(p16_original, p16_modified, 1)

    # 2. Inserir multi_cons_block após para 19 ({%p endif %})
    p19 = paras[19]
    xml = xml.replace(p19, p19 + ''.join(multi_cons_block), 1)

    # 3. Substituir para 26
    xml = xml.replace(p26_original, p26_modified, 1)

    # 4. Inserir multi_cont_block após para 29 ({%p endif %})
    p29 = paras[29]
    xml = xml.replace(p29, p29 + ''.join(multi_cont_block), 1)

    # 5. Substituir para 31
    xml = xml.replace(p31_original, p31_modified, 1)

    # 6. Inserir hon_cons_multi_block após para 82 (endif dos honorários consultivos)
    p82 = paras[82]
    xml = xml.replace(p82, p82 + ''.join(hon_cons_multi_block), 1)

    # 7. Substituir para 84
    xml = xml.replace(p84_original, p84_modified, 1)

    # 8. Inserir hon_cont_multi_block após para 180
    p180 = paras[180]
    xml = xml.replace(p180, p180 + ''.join(hon_cont_multi_block), 1)

    return xml


def main() -> None:
    # Criar backup
    shutil.copy2(TEMPLATE_PATH, BACKUP_PATH)
    print(f"Backup criado: {BACKUP_PATH}")

    with zipfile.ZipFile(TEMPLATE_PATH) as z:
        xml = z.read('word/document.xml').decode('utf-8')
        # Ler todos os outros arquivos do zip
        other_files = {name: z.read(name) for name in z.namelist() if name != 'word/document.xml'}

    updated_xml = update_template(xml)

    # Reescrever o docx com o XML atualizado
    import tempfile, os
    tmp_path = str(TEMPLATE_PATH) + '.tmp'
    with zipfile.ZipFile(tmp_path, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        zout.writestr('word/document.xml', updated_xml.encode('utf-8'))
        for name, data in other_files.items():
            zout.writestr(name, data)

    os.replace(tmp_path, TEMPLATE_PATH)
    print(f"Template atualizado: {TEMPLATE_PATH}")

    # Verificar que as novas tags estão presentes
    checks = [
        'not escopo.multi_consultiva',
        'escopo.multi_consultiva',
        'for item in escopo.itens_consultivos',
        'not escopo.multi_contenciosa',
        'escopo.multi_contenciosa',
        'for item in escopo.itens_contenciosos',
        'not consultiva.forma_por_escopo',
        'for hon in consultiva.itens',
        'not contenciosa.forma_por_escopo',
        'for hon in contenciosa.itens',
    ]
    print("\nVerificações:")
    for check in checks:
        found = check in updated_xml
        status = "✓" if found else "✗"
        print(f"  {status} '{check}'")


if __name__ == '__main__':
    main()
