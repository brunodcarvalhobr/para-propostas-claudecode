"""Testes de pmra.br_docs, DVs de CPF/CNPJ (inclusive alfanumérico) e ViaCEP."""
from __future__ import annotations

import pytest

from pmra.br_docs import cnpj_dv_ok, cnpj_parse, cpf_dv_ok, titulo_pt, viacep_parse


class TestCpfDv:
    @pytest.mark.parametrize("cpf", ["111.444.777-35", "11144477735", "529.982.247-25"])
    def test_validos(self, cpf):
        assert cpf_dv_ok(cpf)

    @pytest.mark.parametrize(
        "cpf",
        [
            "111.444.777-36",   # DV errado
            "123.456.789-00",
            "111.111.111-11",   # repetido: passa no mod-11 mas é inválido na Receita
            "000.000.000-00",
            "1234567890",       # curto
            "",
        ],
    )
    def test_invalidos(self, cpf):
        assert not cpf_dv_ok(cpf)


class TestCnpjDv:
    @pytest.mark.parametrize(
        "cnpj",
        [
            "11.222.333/0001-81",   # numérico clássico
            "11222333000181",
            "12.ABC.345/01DE-35",   # exemplo oficial do CNPJ alfanumérico (Serpro)
            "12abc34501de35",       # minúsculas normalizadas
        ],
    )
    def test_validos(self, cnpj):
        assert cnpj_dv_ok(cnpj)

    @pytest.mark.parametrize(
        "cnpj",
        [
            "11.222.333/0001-82",   # DV errado
            "12.ABC.345/01DE-36",   # DV errado no alfanumérico
            "12.ABC.345/01DE-3A",   # DV com letra: DVs são sempre numéricos
            "00.000.000/0000-00",   # repetido
            "1122233300018",        # curto
            "",
        ],
    )
    def test_invalidos(self, cnpj):
        assert not cnpj_dv_ok(cnpj)


class TestCnpjParse:
    def test_payload_completo(self):
        payload = {
            "razao_social": "PETROLEO BRASILEIRO S A PETROBRAS",
            "descricao_tipo_de_logradouro": "AVENIDA",
            "logradouro": "REPUBLICA DO CHILE",
            "numero": "65",
            "bairro": "CENTRO",
            "municipio": "RIO DE JANEIRO",
            "uf": "rj",
            "cep": "20031-912",
            "ddd_telefone_1": "(21) 3224-4477",
            "email": "ATENDIMENTO@PETROBRAS.COM.BR",
        }
        out = cnpj_parse(payload)
        assert out["razao_social"] == "PETROLEO BRASILEIRO S A PETROBRAS"
        assert out["logradouro"] == "Avenida Republica do Chile"
        assert out["numero"] == "65"
        assert out["cidade"] == "Rio de Janeiro"
        assert out["uf"] == "RJ"
        assert out["cep"] == "20031912"
        assert out["telefone"] == "2132244477"
        assert out["email"] == "atendimento@petrobras.com.br"

    def test_sem_razao_social(self):
        assert cnpj_parse({"message": "CNPJ nao encontrado"}) is None
        assert cnpj_parse({}) is None
        assert cnpj_parse(None) is None


class TestTituloPt:
    @pytest.mark.parametrize(
        "entrada,esperado",
        [
            ("RIO DE JANEIRO", "Rio de Janeiro"),
            ("AVENIDA REPUBLICA DO CHILE", "Avenida Republica do Chile"),
            ("BELA VISTA", "Bela Vista"),
            ("centro", "Centro"),
            ("", ""),
        ],
    )
    def test_caixa(self, entrada, esperado):
        assert titulo_pt(entrada) == esperado


class TestViacepParse:
    def test_payload_completo(self):
        payload = {
            "logradouro": "Avenida Paulista",
            "bairro": "Bela Vista",
            "localidade": "São Paulo",
            "uf": "sp",
        }
        assert viacep_parse(payload) == {
            "logradouro": "Avenida Paulista",
            "bairro": "Bela Vista",
            "cidade": "São Paulo",
            "uf": "SP",
        }

    def test_cep_inexistente(self):
        assert viacep_parse({"erro": True}) is None

    def test_payload_vazio(self):
        assert viacep_parse({}) is None
        assert viacep_parse({"logradouro": "", "bairro": "", "localidade": "", "uf": ""}) is None
