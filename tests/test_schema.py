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


class TestContratanteAceitaQualquerCpfCnpj:
    # Gerador de propostas aceita CPF/CNPJ temporario/ficticio — sem validacao
    # de digito verificador (usuario pode estar testando ou usando placeholder).
    def test_cpf_qualquer_string(self):
        Contratante(tipo_pessoa="fisica", cpf="000.000.000-00")
        Contratante(tipo_pessoa="fisica", cpf="111.111.111-11")
        Contratante(tipo_pessoa="fisica", cpf="123.456.789-00")

    def test_cnpj_qualquer_string(self):
        Contratante(tipo_pessoa="juridica", cnpj="00.000.000/0000-00")
        Contratante(tipo_pessoa="juridica", cnpj="11.111.111/1111-11")
        Contratante(tipo_pessoa="juridica", cnpj="98.765.432/0001-99")

    def test_cpf_vazio_permitido(self):
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
