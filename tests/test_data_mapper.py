import pytest

from pmra.data_mapper import _fmt_money, form_to_context, montar_contatos, montar_endereco
from pmra.defaults import proposal_form_default
from pmra.schema import Contato, Endereco


class TestFmtMoney:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("500", "R$ 500,00"),
            ("1050", "R$ 1.050,00"),
            ("1.050,50", "R$ 1.050,50"),
            ("R$ 1.050,00", "R$ 1.050,00"),
            ("1500000", "R$ 1.500.000,00"),
            ("1.500.000,75", "R$ 1.500.000,75"),
            # Sem vírgula: ponto + 3 dígitos = milhar; ponto + 1-2 dígitos = decimal
            # (regressão: "700.50" virava R$ 70.050,00)
            ("1.050", "R$ 1.050,00"),
            ("1.500.000", "R$ 1.500.000,00"),
            ("700.50", "R$ 700,50"),
            ("10.5", "R$ 10,50"),
            ("1.234.56", "R$ 1.234,56"),
        ],
    )
    def test_numeric(self, raw, expected):
        assert _fmt_money(raw) == expected

    @pytest.mark.parametrize("raw", ["", "   ", "nan", "None"])
    def test_empty(self, raw):
        assert _fmt_money(raw) == ""

    @pytest.mark.parametrize(
        "raw",
        [
            "1500 reais",
            "valor a combinar",
            "R$ 50,00 por processo/mes",
            "30 horas",
        ],
    )
    def test_freeform_text_preserved(self, raw):
        # Texto livre nao deve ser reformatado
        assert _fmt_money(raw) == raw


class TestMontarEndereco:
    def test_completo(self):
        e = Endereco(
            logradouro="Av. Paulista", numero="1000", bairro="Bela Vista",
            cep="01310-100", cidade="Sao Paulo", uf="SP",
        )
        assert montar_endereco(e) == (
            "Av. Paulista, n. 1000, Bairro Bela Vista, CEP 01310-100, Sao Paulo/SP"
        )

    def test_prefixos_nao_duplicam(self):
        e = Endereco(
            logradouro="Rua Y", numero="nº 100", bairro="Bairro Centro",
            cep="CEP 30130-000", cidade="Belo Horizonte", uf="MG",
        )
        assert montar_endereco(e) == (
            "Rua Y, nº 100, Bairro Centro, CEP 30130-000, Belo Horizonte/MG"
        )

    def test_numero_sem_digito_fica_como_esta(self):
        e = Endereco(logradouro="Rua Z", numero="S/N")
        assert montar_endereco(e) == "Rua Z, S/N"

    def test_sem_numero(self):
        e = Endereco(logradouro="Rua X", bairro="Centro", cidade="BH", uf="MG")
        assert "Rua X" in montar_endereco(e)
        assert "Centro" in montar_endereco(e)

    def test_vazio(self):
        assert montar_endereco(Endereco()) == ""

    def test_so_cidade_uf(self):
        e = Endereco(cidade="Rio", uf="RJ")
        assert montar_endereco(e) == "Rio/RJ"


class TestMontarContatos:
    def test_um_contato_completo(self):
        out = montar_contatos([Contato(telefone="(11) 9999-9999", email="a@b.com")])
        assert "Telefone: (11) 9999-9999" in out
        assert "E-mail: a@b.com" in out

    def test_multiplos_contatos(self):
        out = montar_contatos([
            Contato(telefone="111", email="a@b.com"),
            Contato(telefone="222", email="c@d.com"),
        ])
        assert out.count("\n") == 1  # 2 linhas

    def test_so_telefone(self):
        out = montar_contatos([Contato(telefone="(11) 1234-5678")])
        assert out == "Telefone: (11) 1234-5678"

    def test_so_email(self):
        out = montar_contatos([Contato(email="x@y.com")])
        assert out == "E-mail: x@y.com"

    def test_contatos_vazios_filtrados(self):
        out = montar_contatos([Contato(), Contato(email="a@b.com"), Contato()])
        assert out == "E-mail: a@b.com"


class TestFormToContext:
    def test_pf_oculta_pj(self):
        f = proposal_form_default()
        f.contratante.tipo_pessoa = "fisica"
        f.contratante.nome = "Joao"
        f.contratante.cpf = "111.444.777-35"
        ctx = form_to_context(f)
        assert ctx["contratante"]["pf"] is True
        assert ctx["contratante"]["pj"] is False

    def test_pj_oculta_pf(self):
        f = proposal_form_default()
        f.contratante.tipo_pessoa = "juridica"
        f.contratante.razao_social = "Acme"
        f.contratante.cnpj = "11.222.333/0001-81"
        ctx = form_to_context(f)
        assert ctx["contratante"]["pj"] is True
        assert ctx["contratante"]["pf"] is False

    def test_modalidade_consultiva(self):
        f = proposal_form_default()
        f.escopo.modalidade = "consultiva"
        ctx = form_to_context(f)
        assert ctx["escopo"]["show_consultiva"] is True
        assert ctx["escopo"]["show_contenciosa"] is False

    def test_modalidade_contenciosa(self):
        f = proposal_form_default()
        f.escopo.modalidade = "contenciosa"
        ctx = form_to_context(f)
        assert ctx["escopo"]["show_consultiva"] is False
        assert ctx["escopo"]["show_contenciosa"] is True

    def test_modalidade_mista(self):
        f = proposal_form_default()
        f.escopo.modalidade = "mista"
        ctx = form_to_context(f)
        assert ctx["escopo"]["show_consultiva"] is True
        assert ctx["escopo"]["show_contenciosa"] is True

    def test_exito_so_aparece_em_contenciosa(self):
        f = proposal_form_default()
        f.escopo.modalidade = "consultiva"
        f.honorarios_contenciosa.exito_ativo = True
        ctx = form_to_context(f)
        # Em modalidade consultiva, exito nao deve aparecer mesmo ativo
        assert ctx["contenciosa"]["show_exito"] is False

    def test_meta_nome_ou_razao_social_pf_richtext_bold_upper(self):
        # Renderizado como RichText (negrito + caixa alta). O cross-field validator
        # do schema ja limpa razao_social quando PF, entao o RichText so contera o
        # nome em uppercase.
        f = proposal_form_default()
        f.contratante.tipo_pessoa = "fisica"
        f.contratante.nome = "Joao da Silva"
        ctx = form_to_context(f)
        rendered = str(ctx["meta"]["nome_ou_razao_social"])
        assert "JOAO DA SILVA" in rendered
        # docxtpl RichText embute negrito como <w:b/> no XML do run
        assert "<w:b/>" in rendered


class TestFilterEmptyRows:
    """Linhas vazias nao devem aparecer no documento final."""

    def test_acoes_sem_valor_sao_ignoradas(self):
        from pmra.schema import AcaoRow
        f = proposal_form_default()
        f.escopo.modalidade = "contenciosa"
        f.honorarios_contenciosa.modalidades.valor_acao = True
        f.honorarios_contenciosa.tabela_acoes = [
            AcaoRow(natureza="Trabalhista", fase="Conhecimento", valor="5000"),
            AcaoRow(natureza="Civel", fase="Recurso", valor=""),  # sem valor — deve ser filtrado
        ]
        ctx = form_to_context(f)
        rows = ctx["contenciosa"]["tabela_acoes"]
        assert len(rows) == 1
        assert rows[0]["natureza"] == "Trabalhista"

    def test_atos_sem_valor_sao_ignorados(self):
        from pmra.schema import AtoProcessualRow
        f = proposal_form_default()
        f.escopo.modalidade = "contenciosa"
        f.honorarios_contenciosa.modalidades.valor_ato_processual = True
        f.honorarios_contenciosa.tabela_atos = [
            AtoProcessualRow(ato="Peticao", descricao="Inicial", valor="1000"),
            AtoProcessualRow(ato="Contestacao", descricao="Defesa", valor=""),
        ]
        ctx = form_to_context(f)
        rows = ctx["contenciosa"]["tabela_atos"]
        assert len(rows) == 1

    def test_senioridade_totalmente_vazia_filtrada(self):
        from pmra.schema import SenioridadeRow
        f = proposal_form_default()
        f.honorarios_consultiva.tabela_senioridade = [
            SenioridadeRow(categoria="Socio", valor="1050"),
            SenioridadeRow(categoria="", valor=""),  # totalmente vazia
        ]
        ctx = form_to_context(f)
        assert len(ctx["consultiva"]["tabela_senioridade"]) == 1

    def test_despesas_totalmente_vazia_filtrada(self):
        from pmra.schema import DespesaItem
        f = proposal_form_default()
        f.despesas.tabela_despesas = [
            DespesaItem(categoria="Logisticas", descricao="Combustivel"),
            DespesaItem(categoria="", descricao=""),
        ]
        ctx = form_to_context(f)
        assert len(ctx["despesas"]["tabela_despesas"]) == 1
