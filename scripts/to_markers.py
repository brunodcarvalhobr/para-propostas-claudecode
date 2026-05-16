#!/usr/bin/env python3
"""Converte PMRA_Template_Jinja.docx -> PMRA_Template_Markers.docx.

Substitui cada tag Jinja por um marker humano-legivel (ver scripts/markers_map.py).
Operacao reversivel via scripts/build_from_markers.py.
"""
from __future__ import annotations

import sys
import zipfile
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.markers_map import build_full_map  # noqa: E402

SRC = ROOT / "resources" / "templates" / "PMRA_Template_Jinja.docx"
DST = ROOT / "resources" / "templates" / "PMRA_Template_Markers.docx"

# Mesmos arquivos que o engine pos-processa
DOCS_TO_PROCESS = (
    "word/document.xml",
    "word/header1.xml", "word/header2.xml", "word/header3.xml",
    "word/footer1.xml", "word/footer2.xml", "word/footer3.xml",
)


def main() -> None:
    mapping = build_full_map()
    src_bytes = SRC.read_bytes()

    src_buf = BytesIO(src_bytes)
    dst_buf = BytesIO()

    total_replacements = 0
    unmapped_jinja: list[str] = []

    with zipfile.ZipFile(src_buf, "r") as zin:
        with zipfile.ZipFile(dst_buf, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename in DOCS_TO_PROCESS:
                    try:
                        text = data.decode("utf-8")
                    except UnicodeDecodeError:
                        zout.writestr(item, data)
                        continue
                    for jinja_tag, marker in mapping.items():
                        count = text.count(jinja_tag)
                        if count:
                            text = text.replace(jinja_tag, marker)
                            total_replacements += count
                    # Detecta tags Jinja remanescentes (nao mapeadas)
                    import re
                    for pat in (r"\{\{[^}]+\}\}", r"\{%[^%]+%\}"):
                        unmapped_jinja.extend(re.findall(pat, text))
                    data = text.encode("utf-8")
                zout.writestr(item, data)

    DST.write_bytes(dst_buf.getvalue())
    print(f"  {total_replacements} tags Jinja convertidas para markers")
    if unmapped_jinja:
        print(f"  AVISO: {len(unmapped_jinja)} tags Jinja sem marker correspondente:")
        for tag in sorted(set(unmapped_jinja)):
            print(f"    {tag}")
        sys.exit(1)
    print(f"  -> {DST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
