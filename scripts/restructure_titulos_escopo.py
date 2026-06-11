#!/usr/bin/env python3
"""Migracao v2.0.41 — titulos de escopo e horas extra opcionais.

Edita resources/templates/PMRA_Template_Jinja.docx (uma vez; idempotente por
assercao — falha se os anchors nao existirem mais):

1. Remove o <w:br/> embutido no paragrafo do titulo "{{escopo.titulo_secao}}"
   (gerava linha em branco dupla entre o titulo e o subtitulo do escopo).
2. Envolve os subtitulos "Escopo Consultivo:" / "Escopo Contencioso:" (caminho
   escopo unico) em condicionais novos — escondidos quando a proposta tem uma
   unica modalidade, evitando titulo redundante sob "Escopo de Trabalho".
3. Envolve o titulo "Horas para Servicos Extra Escopo" em condicional novo —
   escondido quando o usuario optar por nao definir valores de hora extra.
4. Renomeia "Valor por Ato Processual" -> "Valor por Ato" (titulo, header da
   tabela e prosa), cobrindo frentes contenciosas nao-processuais (Ouvidoria).

Apos rodar, regenerar o markers: python scripts/to_markers.py
"""
from __future__ import annotations

import sys
import zipfile
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "resources" / "templates" / "PMRA_Template_Jinja.docx"

_TAG_PARA = (
    '<w:p w14:paraId="{pid}" w14:textId="77777777" w:rsidR="004842D6" '
    'w:rsidRPr="00AC667A" w:rsidRDefault="004842D6" w:rsidP="00AC667A">'
    '<w:pPr><w:spacing w:line="276" w:lineRule="auto"/>'
    '<w:rPr><w:rFonts w:ascii="Arvo" w:hAnsi="Arvo"/><w:sz w:val="2"/><w:szCs w:val="2"/></w:rPr></w:pPr>'
    '<w:r w:rsidRPr="00AC667A"><w:rPr><w:rFonts w:ascii="Arvo" w:hAnsi="Arvo"/>'
    '<w:sz w:val="2"/><w:szCs w:val="2"/></w:rPr><w:t>{tag}</w:t></w:r></w:p>'
)

BR_RUN = (
    '<w:r w:rsidRPr="00AC667A"><w:rPr><w:rFonts w:ascii="Arvo" w:hAnsi="Arvo"/>'
    '<w:b/><w:bCs/><w:sz w:val="20"/><w:szCs w:val="20"/><w:u w:val="single"/></w:rPr>'
    '<w:br/></w:r></w:p>'
)


def _tag_para(pid: str, tag: str) -> str:
    return _TAG_PARA.format(pid=pid, tag=tag)


def _wrap_paragraph(xml: str, para_id: str, if_tag: str, endif_pid: str, if_pid: str,
                    endif_before_para_id: str | None = None) -> str:
    """Insere paragrafo {%p if %} antes do paragrafo `para_id` e {%p endif %}
    depois dele (ou antes de `endif_before_para_id`, se informado)."""
    anchor = f'<w:p w14:paraId="{para_id}"'
    assert xml.count(anchor) == 1, f"anchor {para_id} nao encontrado/unico"
    start = xml.index(anchor)
    if endif_before_para_id:
        end_anchor = f'<w:p w14:paraId="{endif_before_para_id}"'
        assert xml.count(end_anchor) == 1, f"anchor {endif_before_para_id} nao unico"
        end = xml.index(end_anchor)
    else:
        end = xml.index("</w:p>", start) + len("</w:p>")
    return (
        xml[:start]
        + _tag_para(if_pid, if_tag)
        + xml[start:end]
        + _tag_para(endif_pid, "{%p endif %}")
        + xml[end:]
    )


def main() -> None:
    src = TEMPLATE.read_bytes()
    buf_out = BytesIO()
    with zipfile.ZipFile(BytesIO(src), "r") as zin:
        xml = zin.read("word/document.xml").decode("utf-8")

        # 1. <w:br/> do titulo da secao
        anchor = "{{escopo.titulo_secao}}</w:t></w:r>" + BR_RUN
        assert xml.count(anchor) == 1, "anchor do <w:br/> do titulo nao encontrado"
        xml = xml.replace(anchor, "{{escopo.titulo_secao}}</w:t></w:r></w:p>", 1)

        # 2. subtitulos de escopo unico
        xml = _wrap_paragraph(
            xml, "113ACF51", "{%p if escopo.show_subtitulo_consultivo %}",
            if_pid="A1B20001", endif_pid="A1B20002",
        )
        xml = _wrap_paragraph(
            xml, "5366AFB4", "{%p if escopo.show_subtitulo_contencioso %}",
            if_pid="A1B20003", endif_pid="A1B20004",
        )

        # 3. titulo "Horas para Servicos Extra Escopo" (inclui o paragrafo em
        #    branco seguinte: endif entra antes do bloco show_extra_senioridade)
        xml = _wrap_paragraph(
            xml, "10E6322D", "{%p if contenciosa.show_horas_extra %}",
            if_pid="A1B20005", endif_pid="A1B20006",
            endif_before_para_id="57F4D2FB",
        )

        # 4. renomeacoes "Ato Processual" -> "Ato" (modalidade Valor por Ato)
        for old, new in (
            (">Valor por Ato Processual<", ">Valor por Ato<"),
            (">Ato Processual<", ">Ato<"),
            ("por ato processual efetivamente praticado", "por ato efetivamente praticado"),
        ):
            assert xml.count(old) == 1, f"esperava 1 ocorrencia de {old!r}, achei {xml.count(old)}"
            xml = xml.replace(old, new, 1)

        with zipfile.ZipFile(buf_out, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "word/document.xml":
                    data = xml.encode("utf-8")
                zout.writestr(item, data)

    TEMPLATE.write_bytes(buf_out.getvalue())
    print("Template migrado. Agora rode: python scripts/to_markers.py")


if __name__ == "__main__":
    main()
