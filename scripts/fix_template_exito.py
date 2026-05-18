"""Patch para corrigir template: tira a seção de êxito/horas extra de dentro do
condicional `not contenciosa.forma_por_escopo`. Sem isso, no modo multi-escopo
contencioso, êxito e horas extra deixam de renderizar.

Estrutura desejada:

  {%p if escopo.show_contenciosa and not contenciosa.forma_por_escopo %}
    [modalidades]
  {%p endif %}                                              <- novo, inserir antes do êxito
  {%p if escopo.show_contenciosa %}                         <- novo, envolver êxito + horas extra
    [êxito]
    [horas extra]
  {%p endif %}
  {%p if escopo.show_contenciosa and contenciosa.forma_por_escopo %}
    [loop por escopo]
  {%p endif %}                                              <- remover o `{%p endif %}` extra
"""
from __future__ import annotations

import os
import re
import zipfile
from pathlib import Path

TEMPLATE_PATH = Path("resources/templates/PMRA_Template_Jinja.docx")


def _make_tag_para(template_para: str, new_tag: str) -> str:
    return re.sub(r'<w:t>[^<]*</w:t>', f'<w:t>{new_tag}</w:t>', template_para, count=1)


def patch(xml: str) -> str:
    paras = re.findall(r'<w:p[ >].*?</w:p>', xml, re.DOTALL)

    # Localizar paragrafos por conteudo (mais robusto que indices)
    def find_para_with_text(text: str) -> int:
        for i, p in enumerate(paras):
            texts = re.findall(r'<w:t[^>]*>(.*?)</w:t>', p, re.DOTALL)
            if ''.join(texts).strip() == text:
                return i
        return -1

    # Achar o "{%p if contenciosa.show_exito %}" — primeiro endif do valor_projeto antes dele
    idx_exito_if = find_para_with_text('{%p if contenciosa.show_exito %}')
    if idx_exito_if < 0:
        raise RuntimeError("nao achou {%p if contenciosa.show_exito %}")

    # O para imediatamente antes deve ser o `{%p endif %}` do valor_projeto.
    # Após esse endif (que fecha apenas o `if show_valor_projeto`), inserir:
    #   {%p endif %}  → fecha o `not contenciosa.forma_por_escopo`
    #   {%p if escopo.show_contenciosa %}  → abre escopo para êxito + horas extra
    template_tag_para = paras[idx_exito_if]  # usar este como template

    extra_endif      = _make_tag_para(template_tag_para, '{%p endif %}')
    open_show_cont   = _make_tag_para(template_tag_para, '{%p if escopo.show_contenciosa %}')

    # Achar o `{%p endif %}` que está IMEDIATAMENTE antes do
    # `{%p if escopo.show_contenciosa and contenciosa.forma_por_escopo %}`
    idx_multi_open = find_para_with_text('{%p if escopo.show_contenciosa and contenciosa.forma_por_escopo %}')
    if idx_multi_open < 0:
        raise RuntimeError("nao achou bloco multi-contenciosa")

    # O para imediatamente antes do idx_multi_open deve ser o endif que vamos remover/mover.
    # Esse endif vai ficar AGORA fechando o novo `{%p if escopo.show_contenciosa %}` que
    # envolve o êxito e horas extra. Como o `{%p if escopo.show_contenciosa %}` é aberto
    # antes do êxito, este endif após o horas extra automaticamente o fecha. ✓
    # Logo: não removemos nada, apenas inserimos o `endif` + `if show_contenciosa` antes do êxito.

    # Aplicar: inserir antes do para_exito_if
    p_exito_if = paras[idx_exito_if]
    replacement = extra_endif + open_show_cont + p_exito_if
    new_xml = xml.replace(p_exito_if, replacement, 1)

    return new_xml


def main() -> None:
    with zipfile.ZipFile(TEMPLATE_PATH) as z:
        xml = z.read('word/document.xml').decode('utf-8')
        others = {n: z.read(n) for n in z.namelist() if n != 'word/document.xml'}

    new_xml = patch(xml)

    tmp = str(TEMPLATE_PATH) + '.tmp'
    with zipfile.ZipFile(tmp, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        zout.writestr('word/document.xml', new_xml.encode('utf-8'))
        for n, d in others.items():
            zout.writestr(n, d)
    os.replace(tmp, TEMPLATE_PATH)
    print(f"Patch aplicado: {TEMPLATE_PATH}")


if __name__ == '__main__':
    main()
