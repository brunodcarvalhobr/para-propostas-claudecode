from pmra.validators import is_valid_cnpj, is_valid_cpf


class TestCPF:
    def test_valid_formatted(self):
        assert is_valid_cpf("111.444.777-35")

    def test_valid_unformatted(self):
        assert is_valid_cpf("11144477735")

    def test_invalid_check_digit(self):
        assert not is_valid_cpf("111.444.777-36")

    def test_invalid_all_same_digits(self):
        assert not is_valid_cpf("111.111.111-11")
        assert not is_valid_cpf("000.000.000-00")

    def test_invalid_length(self):
        assert not is_valid_cpf("123")
        assert not is_valid_cpf("123456789012")

    def test_empty(self):
        assert not is_valid_cpf("")


class TestCNPJ:
    def test_valid_formatted(self):
        assert is_valid_cnpj("11.222.333/0001-81")

    def test_valid_unformatted(self):
        assert is_valid_cnpj("11222333000181")

    def test_invalid_check_digit(self):
        assert not is_valid_cnpj("11.222.333/0001-82")

    def test_invalid_all_same_digits(self):
        assert not is_valid_cnpj("11.111.111/1111-11")

    def test_invalid_length(self):
        assert not is_valid_cnpj("12345678")

    def test_empty(self):
        assert not is_valid_cnpj("")
