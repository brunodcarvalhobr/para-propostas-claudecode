"""Validacao de documentos brasileiros e consulta de CEP.

Validacoes sao SUAVES por filosofia do app: nada bloqueia a geracao da
proposta (numeros temporarios/de teste sao permitidos); os resultados
alimentam avisos nao-bloqueantes na UI.
"""
from __future__ import annotations

import json
import re
import urllib.request
from functools import lru_cache

# Cloudflare (BrasilAPI) devolve 403 para o User-Agent padrao do urllib;
# um UA identificado resolve e e boa pratica com APIs publicas.
_HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PMRA-DocGen/2.0)"}


def _http_json(url: str, timeout: float) -> dict:
    req = urllib.request.Request(url, headers=_HTTP_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def cpf_dv_ok(cpf: str) -> bool:
    """True se o CPF (11 digitos, com ou sem mascara) tem DVs corretos.

    Sequencias de digito repetido (111.111.111-11 etc.) passam no calculo
    classico mas sao invalidas na Receita: rejeitadas explicitamente.
    """
    d = re.sub(r"\D", "", cpf)
    if len(d) != 11 or len(set(d)) == 1:
        return False
    for n_digits, pesos in ((9, range(10, 1, -1)), (10, range(11, 1, -1))):
        soma = sum(int(c) * p for c, p in zip(d[:n_digits], pesos))
        resto = (soma * 10) % 11
        if (0 if resto == 10 else resto) != int(d[n_digits]):
            return False
    return True


_CNPJ_PESOS_DV1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_CNPJ_PESOS_DV2 = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)


def cnpj_dv_ok(cnpj: str) -> bool:
    """True se o CNPJ (14 posicoes, com ou sem mascara) tem DVs corretos.

    Suporta o CNPJ alfanumerico (IN RFB nº 2.229/2024): cada caractere
    contribui com `ord(c) - 48` ('0'-'9' → 0-9, 'A'-'Z' → 17-42) e os 2
    DVs finais sao sempre numericos, mod-11 classico.
    """
    s = re.sub(r"[^0-9A-Za-z]", "", cnpj).upper()
    if len(s) != 14 or not s[12:].isdigit() or len(set(s)) == 1:
        return False
    if not re.fullmatch(r"[0-9A-Z]{12}\d{2}", s):
        return False
    valores = [ord(c) - 48 for c in s[:12]]
    for pesos, dv_esperado in ((_CNPJ_PESOS_DV1, s[12]), (_CNPJ_PESOS_DV2, s[13])):
        soma = sum(v * p for v, p in zip(valores, pesos))
        resto = soma % 11
        dv = 0 if resto < 2 else 11 - resto
        if dv != int(dv_esperado):
            return False
        valores.append(dv)
    return True


def viacep_parse(payload: dict) -> dict | None:
    """Normaliza a resposta do ViaCEP para os campos do formulario.

    Retorna None para CEP inexistente (payload {"erro": true}) ou payload
    sem conteudo util.
    """
    if not isinstance(payload, dict) or payload.get("erro"):
        return None
    campos = {
        "logradouro": (payload.get("logradouro") or "").strip(),
        "bairro": (payload.get("bairro") or "").strip(),
        "cidade": (payload.get("localidade") or "").strip(),
        "uf": (payload.get("uf") or "").strip().upper(),
    }
    return campos if any(campos.values()) else None


def cnpj_parse(payload: dict) -> dict | None:
    """Normaliza a resposta da BrasilAPI de CNPJ para os campos do formulario.

    Retorna None quando o payload nao traz razao social (CNPJ inexistente,
    erro da API, resposta de erro em JSON).
    """
    if not isinstance(payload, dict):
        return None
    razao = (payload.get("razao_social") or "").strip()
    if not razao:
        return None
    logradouro = " ".join(
        p for p in [
            (payload.get("descricao_tipo_de_logradouro") or "").strip(),
            (payload.get("logradouro") or "").strip(),
        ] if p
    )
    return {
        "razao_social": razao,
        "logradouro": logradouro,
        "numero": (payload.get("numero") or "").strip(),
        "bairro": (payload.get("bairro") or "").strip(),
        # A API devolve municipio em MAIUSCULAS; title() aproxima a escrita usual.
        "cidade": (payload.get("municipio") or "").strip().title(),
        "uf": (payload.get("uf") or "").strip().upper(),
        "cep": re.sub(r"\D", "", str(payload.get("cep") or ""))[:8],
        "telefone": re.sub(r"\D", "", str(payload.get("ddd_telefone_1") or ""))[:11],
        "email": (payload.get("email") or "").strip().lower(),
    }


@lru_cache(maxsize=128)
def cnpj_lookup(cnpj_digits: str, timeout: float = 4.0) -> dict | None:
    """Consulta dados cadastrais do CNPJ na BrasilAPI (fonte: Receita Federal).

    Apenas CNPJs 100% numericos: o cadastro alfanumerico ainda nao e coberto
    pela API publica. Falha em silencio (None): a consulta e conveniencia,
    nunca pre-requisito; sem rede o usuario apenas digita os dados.
    """
    if not re.fullmatch(r"\d{14}", cnpj_digits):
        return None
    for url in (
        f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_digits}",
        f"https://minhareceita.org/{cnpj_digits}",  # fallback, mesmos campos
    ):
        try:
            data = cnpj_parse(_http_json(url, timeout))
            if data:
                return data
        except Exception:
            continue
    return None


@lru_cache(maxsize=256)
def viacep_lookup(cep_digits: str, timeout: float = 3.0) -> dict | None:
    """Consulta o ViaCEP; None em erro de rede/timeout/CEP inexistente.

    Falha em silencio de proposito: a consulta e conveniencia, nunca
    pre-requisito — sem rede o usuario apenas digita o endereco.
    """
    if not re.fullmatch(r"\d{8}", cep_digits):
        return None
    try:
        return viacep_parse(_http_json(f"https://viacep.com.br/ws/{cep_digits}/json/", timeout))
    except Exception:
        return None
