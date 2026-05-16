import pytest
from pydantic import ValidationError

from pmra.schema import Contratante


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
