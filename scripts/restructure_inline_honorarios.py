#!/usr/bin/env python3
"""Reestrutura o template para intercalar honorários sob cada escopo (multi).

Antes: descrições dos escopos numa seção e "Honorários Propostos para os
Escopos …" noutra, distantes. Depois (quando há forma de pagamento por escopo):
cada honorário aparece logo abaixo da descrição do seu escopo, dentro do loop.

Edições no word/document.xml (todas em parágrafos cujo texto é uma tag Jinja em
run único — confirmado por inspeção):

  1. Dentro do loop de escopos consultivos/contenciosos, antes do {%p endfor %},
     insere:  {%p if <modal>.forma_por_escopo %} / {{p item.subdoc}} / {%p endif %}
  2. Remove os blocos "Honorários Propostos para os Escopos Consultivos/Contenciosos"
     (heading + loop) da seção de honorários — agora renderizados inline acima.
  3. Renomeia o heading "Escopo de Trabalho" para a tag {{escopo.titulo_secao}}.

Idempotente: se o template já tem {{escopo.titulo_secao}}, não faz nada.
Uso: python scripts/restructure_inline_honorarios.py
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "resources" / "templates" / "PMRA_Template_Jinja.docx"


def _ptext(p) -> str:
    return "".join(t.text or "" for t in p.iter(qn("w:t")))


def _set_ptext(p, new: str) -> None:
    wts = list(p.iter(qn("w:t")))
    wts[0].text = new
    for extra in wts[1:]:
        extra.text = ""


def migrate(path: Path) -> bool:
    doc = Document(str(path))
    body = doc.element.body
    paras = [el for el in body if el.tag == qn("w:p")]
    texts = [_ptext(p) for p in paras]

    if "{{escopo.titulo_secao}}" in texts:
        print("Template já reestruturado — nada a fazer.")
        return False

    def find(text: str):
        return paras[texts.index(text)]

    def next_after(start_text: str, target_text: str):
        si = texts.index(start_text)
        for j in range(si + 1, len(paras)):
            if texts[j] == target_text:
                return paras[j]
        raise ValueError(f"{target_text!r} após {start_text!r} não encontrado")

    head          = find("Escopo de Trabalho")
    cons_endfor   = next_after("{%p for item in escopo.itens_consultivos %}", "{%p endfor %}")
    cont_endfor   = next_after("{%p for item in escopo.itens_contenciosos %}", "{%p endfor %}")
    cons_forma_if = find("{%p if escopo.show_consultiva and consultiva.forma_por_escopo %}")
    cont_forma_if = find("{%p if escopo.show_contenciosa and contenciosa.forma_por_escopo %}")
    cons_forma_endif = next_after("{%p if escopo.show_consultiva and consultiva.forma_por_escopo %}", "{%p endif %}")
    cont_forma_endif = next_after("{%p if escopo.show_contenciosa and contenciosa.forma_por_escopo %}", "{%p endif %}")
    subdoc_src    = find("{{p hon.subdoc}}")

    def clone(src, text):
        el = copy.deepcopy(src)
        _set_ptext(el, text)
        return el

    # 1. insere bloco condicional de honorário dentro de cada loop de escopo
    for el in (clone(cons_forma_if, "{%p if consultiva.forma_por_escopo %}"),
               clone(subdoc_src, "{{p item.subdoc}}"),
               clone(cons_forma_endif, "{%p endif %}")):
        cons_endfor.addprevious(el)
    for el in (clone(cont_forma_if, "{%p if contenciosa.forma_por_escopo %}"),
               clone(subdoc_src, "{{p item.subdoc}}"),
               clone(cont_forma_endif, "{%p endif %}")):
        cont_endfor.addprevious(el)

    # 2. remove os blocos de honorários por-escopo da seção separada
    def delete_inclusive(start_el, end_el):
        children = list(body)
        si, ei = children.index(start_el), children.index(end_el)
        for el in children[si:ei + 1]:
            body.remove(el)

    delete_inclusive(cons_forma_if, cons_forma_endif)
    delete_inclusive(cont_forma_if, cont_forma_endif)

    # 3. heading dinâmico
    _set_ptext(head, "{{escopo.titulo_secao}}")

    doc.save(str(path))
    return True


def verify(path: Path) -> None:
    doc = Document(str(path))
    paras = [el for el in doc.element.body if el.tag == qn("w:p")]
    texts = [_ptext(p) for p in paras]
    checks = {
        "heading dinâmico":        "{{escopo.titulo_secao}}" in texts,
        "sem 'Propostos … Consultivos'": "Honorários Propostos para os Escopos Consultivos" not in texts,
        "sem 'Propostos … Contenciosos'": "Honorários Propostos para os Escopos Contenciosos" not in texts,
        "item.subdoc inserido (2x)": texts.count("{{p item.subdoc}}") == 2,
        "if forma consultiva inline": "{%p if consultiva.forma_por_escopo %}" in texts,
        "if forma contenciosa inline": "{%p if contenciosa.forma_por_escopo %}" in texts,
    }
    for label, ok in checks.items():
        print(f"  {'OK' if ok else 'XX'}  {label}")
    if not all(checks.values()):
        sys.exit("Verificação falhou.")


def main() -> None:
    changed = migrate(TEMPLATE)
    if changed:
        print(f"Template reestruturado: {TEMPLATE}")
    verify(TEMPLATE)
    print("Verificação OK.")


if __name__ == "__main__":
    main()
