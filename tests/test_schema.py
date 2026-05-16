import pytest
from pydantic import ValidationError

from pmra.schema import Contratante, Escopo


class TestContratanteCrossfield:
    def test_pf_zera_campos_pj(self):
        c = Contratante(
            tipo_pessoa="fisica",
            nome="Joao",
            cpf="111.444.777-35",
            razao_social="Lixo SA",
            cnpj="11.222.333/0001-81",
        )
        assert c.razao_social == ""
        assert c.cnpj == ""
        assert c.nome == "Joao"

    def test_pj_zera_campos_pf(self):
        c = Contratante(
            tipo_pessoa="juridica",
            nome="Lixo",
            cpf="111.444.777-35",
            razao_social="Acme",
            cnpj="11.222.333/0001-81",
        )
        assert c.nome == ""
        assert c.cpf == ""
        assert c.razao_social == "Acme"


class TestContratanteDocumentValidation:
    def test_pf_cpf_valido(self):
        Contratante(tipo_pessoa="fisica", cpf="111.444.777-35")

    def test_pf_cpf_invalido(self):
        with pytest.raises(ValidationError, match="CPF invalido"):
            Contratante(tipo_pessoa="fisica", cpf="111.444.777-36")

    def test_pj_cnpj_valido(self):
        Contratante(tipo_pessoa="juridica", cnpj="11.222.333/0001-81")

    def test_pj_cnpj_invalido(self):
        with pytest.raises(ValidationError, match="CNPJ invalido"):
            Contratante(tipo_pessoa="juridica", cnpj="11.222.333/0001-82")

    def test_cpf_vazio_permitido(self):
        # Form parcial deve ser aceito (defaults vazios)
        Contratante(tipo_pessoa="fisica")

    def test_cnpj_vazio_permitido(self):
        Contratante(tipo_pessoa="juridica")


class TestEscopoSlaContenciosa:
    def test_contenciosa_zera_sla(self):
        e = Escopo(modalidade="contenciosa", sla_ativo=True, sla_descricao="qualquer")
        assert e.sla_ativo is False
        assert e.sla_descricao == ""

    def test_consultiva_preserva_sla(self):
        e = Escopo(modalidade="consultiva", sla_ativo=True, sla_descricao="X")
        assert e.sla_ativo is True
        assert e.sla_descricao == "X"

    def test_mista_preserva_sla(self):
        e = Escopo(modalidade="mista", sla_ativo=True, sla_descricao="X")
        assert e.sla_ativo is True
        assert e.sla_descricao == "X"
