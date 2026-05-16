"""Validacao de documentos brasileiros (CPF e CNPJ) por digito verificador.

Funcoes puras, sem dependencia de Streamlit ou Pydantic — usadas tanto pelo
schema (Contratante) quanto pela UI para feedback ao usuario.
"""
from __future__ import annotations

import re


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _dv(digits: str, weights: list[int]) -> int:
    s = sum(int(d) * w for d, w in zip(digits, weights))
    r = s % 11
    return 0 if r < 2 else 11 - r


def is_valid_cpf(value: str) -> bool:
    d = _digits(value)
    if len(d) != 11 or d == d[0] * 11:
        return False
    dv1 = _dv(d[:9], list(range(10, 1, -1)))
    dv2 = _dv(d[:9] + str(dv1), list(range(11, 1, -1)))
    return d[9] == str(dv1) and d[10] == str(dv2)


def is_valid_cnpj(value: str) -> bool:
    d = _digits(value)
    if len(d) != 14 or d == d[0] * 14:
        return False
    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    w2 = [6] + w1
    dv1 = _dv(d[:12], w1)
    dv2 = _dv(d[:12] + str(dv1), w2)
    return d[12] == str(dv1) and d[13] == str(dv2)
