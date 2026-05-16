#!/usr/bin/env python3
"""Converte PMRA_Template_Markers.docx (com markers humanos) -> PMRA_Template_Jinja.docx.

Operacao inversa de to_markers.py. Cada marker [X] vira a tag Jinja correspondente
(ver scripts/markers_map.py).
"""
from __future__ import annotations

import re
import sys
import zipfile
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.markers_map import build_full_map  # noqa: E402

SRC = ROOT / "resources" / "templates" / "PMRA_Template_Markers.docx"
DST = ROOT / "resources" / "templates" / "PMRA_Template_Jinja.docx"

DOCS_TO_PROCESS = (
    "word/document.xml",
    "word/header1.xml", "word/header2.xml", "word/header3.xml",
    "word/footer1.xml", "word/footer2.xml", "word/footer3.xml",
)

# Markers reconhecidos: regex simples para detectar [QUALQUER_COISA]
MARKER_RE = re.compile(r"\[[A-Z_]+\]")


def main() -> None:
    # Inverte o mapa: marker -> jinja_tag
    forward = build_full_map()
    reverse = {marker: tag for tag, marker in forward.items()}

    src_bytes = SRC.read_bytes()
    src_buf = BytesIO(src_bytes)
    dst_buf = BytesIO()

    total = 0
    unknown_markers: set[str] = set()

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
                    # Substitui markers por tags Jinja. Markers ordenados por
                    # comprimento decrescente para evitar partial match.
                    for marker in sorted(reverse, key=len, reverse=True):
                        count = text.count(marker)
                        if count:
                            text = text.replace(marker, reverse[marker])
                            total += count
                    # Detecta markers que ficaram sem mapeamento (typos do usuario)
                    for found in MARKER_RE.findall(text):
                        unknown_markers.add(found)
                    data = text.encode("utf-8")
                zout.writestr(item, data)

    if unknown_markers:
        print(f"ERRO: {len(unknown_markers)} marker(s) desconhecido(s) — typo ou marker novo nao mapeado:")
        for m in sorted(unknown_markers):
            print(f"  {m}")
        sys.exit(1)

    DST.write_bytes(dst_buf.getvalue())
    print(f"  {total} markers convertidos para tags Jinja")
    print(f"  -> {DST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
