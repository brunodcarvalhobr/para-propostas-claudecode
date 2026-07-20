"""Testes do template_engine — regra de justificacao do texto do formulario.

Regra: TODO texto livre do formulario sai justificado, inclusive multilinha
(Enter). O esticamento da linha antes da quebra manual e suprimido pela flag
de compatibilidade doNotExpandShiftReturn injetada em word/settings.xml.

- `_justify_form_paragraphs` (pre-render) forca w:jc=both nos paragrafos de
  texto do formulario.
- `_ensure_do_not_expand_shift_return` (pos-render) garante a flag no
  settings.xml de todo documento gerado.
"""
from __future__ import annotations

import re
import zipfile
from io import BytesIO

import pytest

from pmra.data_mapper import form_to_context
from pmra.defaults import proposal_form_default
from pmra.schema import (
    AcaoRow,
    Contato,
    Endereco,
    EscopoConsultivoItem,
    HonorariosConsultiva,
    HonorariosConsultivaModalidades,
)
from pmra.template_engine import render_proposal

_P_RE = re.compile(r"<w:p\b[^>]*>.*?</w:p>", flags=re.DOTALL)
_JC_RE = re.compile(r'<w:jc w:val="([^"]+)"/>')
_T_RE = re.compile(r"<w:t[^>]*>([^<]*)</w:t>")


def _document_xml(data: bytes) -> str:
    with zipfile.ZipFile(BytesIO(data)) as zf:
        return zf.read("word/document.xml").decode("utf-8")


def _jc_of_paragraph_containing(xml: str, marker: str) -> str | None:
    """Alinhamento (w:jc/@w:val) do 1o paragrafo cujo texto contem `marker`.

    Retorna None se o paragrafo existe mas nao tem <w:jc> (heranca = esquerda),
    e levanta se o marcador nao aparece em nenhum paragrafo.
    """
    for m in _P_RE.finditer(xml):
        p = m.group(0)
        if marker in "".join(_T_RE.findall(p)):
            jc = _JC_RE.search(p)
            return jc.group(1) if jc else None
    raise AssertionError(f"marcador {marker!r} nao encontrado em nenhum paragrafo")


def _render_mista() -> str:
    form = proposal_form_default()
    form.contratante.tipo_pessoa = "juridica"
    form.contratante.razao_social = "Acme Industria S.A."
    form.contratante.cnpj = "11.222.333/0001-81"
    form.contratante.endereco = Endereco(
        logradouro="Av. Paulista", numero="1000", bairro="Bela Vista",
        cep="01310-100", cidade="Sao Paulo", uf="SP",
    )
    form.contratante.contato_nome = "Maria Souza"
    form.contratante.contatos = [Contato(telefone="(11) 3000-1000", email="maria@acme.com")]
    form.escopo.modalidade = "mista"
    form.escopo.atuacao_consultiva = "MARCA_CONSULTIVO descricao do escopo consultivo."
    form.escopo.atuacao_contenciosa = "MARCA_CONTENCIOSO defesa em processos."
    form.escopo.sla_ativo = True
    form.escopo.sla_descricao = "MARCA_SLA Baixa: 5 dias"
    form.honorarios_consultiva.modalidades.valor_projeto = True
    form.honorarios_consultiva.valor_projeto_total = "R$ 100.000,00"
    form.honorarios_consultiva.valor_projeto_forma_pagamento = "MARCA_FORMA_CONS 3 parcelas."
    form.honorarios_contenciosa.modalidades.preco_mensal_massa = True
    form.honorarios_contenciosa.preco_mensal_valor = "R$ 8.000,00"
    form.honorarios_contenciosa.preco_mensal_maximo_acoes = "20"
    form.honorarios_contenciosa.preco_mensal_maximo_acoes_extenso = "vinte"
    form.honorarios_contenciosa.preco_mensal_criterio_excedentes = "MARCA_CRITERIO por ato."
    form.honorarios_contenciosa.modalidades.valor_projeto = True
    form.honorarios_contenciosa.valor_projeto_total = "R$ 50.000,00"
    form.honorarios_contenciosa.valor_projeto_fases_cobertas = "MARCA_FASES conhecimento e recursal."
    form.honorarios_contenciosa.valor_projeto_forma_pagamento = "MARCA_FORMA_CONT entrada e saldo."
    form.disposicoes.ativo = True
    form.disposicoes.descricao = "MARCA_DISP Foro eleito comarca de SP."
    return _document_xml(render_proposal(form_to_context(form)))


def _render_multilinha_bytes() -> bytes:
    """Mesma proposta, mas com texto MULTILINHA (Enter) nos campos livres."""
    form = proposal_form_default()
    form.contratante.tipo_pessoa = "juridica"
    form.contratante.razao_social = "Acme Industria S.A."
    form.contratante.cnpj = "11.222.333/0001-81"
    form.contratante.endereco = Endereco(
        logradouro="Av. Paulista", numero="1000", bairro="Bela Vista",
        cep="01310-100", cidade="Sao Paulo", uf="SP",
    )
    # Dois contatos => contatos_texto recebe '\n' (multilinha).
    form.contratante.contatos = [
        Contato(telefone="(11) 3000-1000", email="MARCA_CONTATO_A@acme.com"),
        Contato(telefone="(11) 3000-1001", email="MARCA_CONTATO_B@acme.com"),
    ]
    form.escopo.modalidade = "mista"
    form.escopo.atuacao_consultiva = "MARCA_CONSULTIVO_ML primeiro paragrafo.\nSegundo paragrafo apos Enter."
    form.escopo.atuacao_contenciosa = "MARCA_CONTENCIOSO_ML defesa.\nOutra linha."
    form.escopo.sla_ativo = True
    form.escopo.sla_descricao = "MARCA_SLA_ML baixa: 3 dias;\nmedia: 5 dias;\nalta: 10 dias."
    form.honorarios_consultiva.modalidades.hora_fixa = True
    form.honorarios_consultiva.hora_fixa_valor = "R$ 700,00"
    form.honorarios_contenciosa.modalidades.preco_mensal_massa = True
    form.honorarios_contenciosa.preco_mensal_valor = "R$ 8.000,00"
    form.disposicoes.ativo = True
    form.disposicoes.descricao = "MARCA_DISP_ML clausula um.\n\nMARCA_DISP_ML2 clausula dois."
    return render_proposal(form_to_context(form))


class TestJustificacaoTextoFormulario:
    @pytest.fixture(scope="class")
    def xml(self) -> str:
        return _render_mista()

    @pytest.mark.parametrize(
        "marker",
        [
            "MARCA_CONSULTIVO",   # Escopo Consultivo — o bug originalmente reportado
            "MARCA_CONTENCIOSO",
            "MARCA_SLA",
            "MARCA_FORMA_CONS",
            "MARCA_CRITERIO",
            "MARCA_FASES",
            "MARCA_FORMA_CONT",
            "MARCA_DISP",
            "Av. Paulista",       # endereco_completo
            "maria@acme.com",     # contatos_texto
        ],
    )
    def test_texto_do_formulario_sai_justificado(self, xml, marker):
        assert _jc_of_paragraph_containing(xml, marker) == "both", (
            f"texto do formulario {marker!r} deveria estar justificado (w:jc=both)"
        )

    def test_itens_multi_escopo_consultivo_justificados(self):
        """Descricoes de escopos consultivos multiplos tambem saem justificadas."""
        form = proposal_form_default()
        form.contratante.tipo_pessoa = "juridica"
        form.contratante.razao_social = "Acme S.A."
        form.contratante.cnpj = "11.222.333/0001-81"
        form.escopo.modalidade = "consultiva"
        form.escopo.escopos_consultivos = [
            EscopoConsultivoItem(
                letra="A",
                descricao="MARCA_ESCOPO_A primeira frente de trabalho.",
                honorarios=HonorariosConsultiva(
                    modalidades=HonorariosConsultivaModalidades(hora_fixa=True),
                    hora_fixa_valor="R$ 700,00",
                ),
            ),
            EscopoConsultivoItem(
                letra="B",
                descricao="MARCA_ESCOPO_B segunda frente de trabalho.",
                honorarios=HonorariosConsultiva(
                    modalidades=HonorariosConsultivaModalidades(hora_fixa=True),
                    hora_fixa_valor="R$ 800,00",
                ),
            ),
        ]
        xml = _document_xml(render_proposal(form_to_context(form)))
        assert _jc_of_paragraph_containing(xml, "MARCA_ESCOPO_A") == "both"
        assert _jc_of_paragraph_containing(xml, "MARCA_ESCOPO_B") == "both"


class TestTextoMultilinhaJustificado:
    """Texto com quebra de linha (Enter) TAMBEM sai justificado.

    O esticamento da linha pre-quebra e suprimido por doNotExpandShiftReturn
    no settings.xml — sem a flag, justificar multilinha deformava o texto
    (motivo do antigo _left_align_multiline, removido).
    """

    @pytest.fixture(scope="class")
    def docx_bytes(self) -> bytes:
        return _render_multilinha_bytes()

    @pytest.fixture(scope="class")
    def xml(self, docx_bytes) -> str:
        return _document_xml(docx_bytes)

    @pytest.mark.parametrize(
        "marker",
        [
            "MARCA_CONSULTIVO_ML",   # Escopo Consultivo com 2 paragrafos
            "MARCA_CONTENCIOSO_ML",
            "MARCA_SLA_ML",          # SLA em lista
            "MARCA_DISP_ML",         # Disposicoes com paragrafos separados
            "MARCA_CONTATO_A",       # contatos_texto com 2 contatos => multilinha
        ],
    )
    def test_texto_multilinha_justificado(self, xml, marker):
        assert _jc_of_paragraph_containing(xml, marker) == "both", (
            f"texto multilinha {marker!r} deveria sair justificado (w:jc=both)"
        )

    def test_settings_tem_do_not_expand_shift_return(self, docx_bytes):
        """A flag que evita o esticamento da linha pre-quebra esta presente."""
        with zipfile.ZipFile(BytesIO(docx_bytes)) as zf:
            settings = zf.read("word/settings.xml").decode("utf-8")
        assert "doNotExpandShiftReturn" in settings

    def test_consultivo_continuo_segue_justificado(self):
        """Sanidade: o caminho de texto corrido permanece justificado."""
        cont_xml = _render_mista()
        assert _jc_of_paragraph_containing(cont_xml, "MARCA_CONSULTIVO") == "both"


class TestHonorarioInlinePorEscopo:
    """Multi-escopo c/ forma por escopo: honorário fica logo ABAIXO do seu escopo."""

    def _render(self) -> str:
        form = proposal_form_default()
        form.contratante.tipo_pessoa = "juridica"
        form.contratante.razao_social = "Acme S.A."
        form.contratante.cnpj = "11.222.333/0001-81"
        form.escopo.modalidade = "consultiva"
        form.escopo.escopos_consultivos = [
            EscopoConsultivoItem(
                letra="A",
                descricao="INLINE_A_DESC descricao do escopo A.",
                honorarios=HonorariosConsultiva(
                    modalidades=HonorariosConsultivaModalidades(valor_projeto=True),
                    valor_projeto_total="R$ 10.000,00",
                    valor_projeto_forma_pagamento="INLINE_A_HON parcela unica.",
                ),
            ),
            EscopoConsultivoItem(
                letra="B",
                descricao="INLINE_B_DESC descricao do escopo B.",
                honorarios=HonorariosConsultiva(
                    modalidades=HonorariosConsultivaModalidades(valor_projeto=True),
                    valor_projeto_total="R$ 20.000,00",
                    valor_projeto_forma_pagamento="INLINE_B_HON em duas parcelas.",
                ),
            ),
        ]
        form.escopo.forma_pagamento_por_escopo_consultiva = True
        return _document_xml(render_proposal(form_to_context(form)))

    def test_ordem_descricao_seguida_do_honorario(self):
        xml = self._render()
        pos = {k: xml.index(k) for k in ("INLINE_A_DESC", "INLINE_A_HON", "INLINE_B_DESC", "INLINE_B_HON")}
        assert pos["INLINE_A_DESC"] < pos["INLINE_A_HON"] < pos["INLINE_B_DESC"] < pos["INLINE_B_HON"], (
            f"ordem incorreta: {pos}; esperado descA < honA < descB < honB"
        )

    def test_secao_renomeada_e_sem_secao_separada_de_honorarios(self):
        xml = self._render()
        assert "Escopo de Trabalho e Honorários" in xml
        assert "Honorários Propostos para os Escopos Consultivos" not in xml
        # subtítulo por escopo permanece
        assert "Honorários — Escopo Consultivo A" in xml
        assert "Honorários — Escopo Consultivo B" in xml


def _texto_visivel(xml: str) -> str:
    return "".join(_T_RE.findall(xml))


def _render_contenciosa_unica(horas_extra_modo: str = "horaFixa") -> str:
    """Proposta de modalidade unica contenciosa, escopo unico."""
    form = proposal_form_default()
    form.contratante.tipo_pessoa = "juridica"
    form.contratante.razao_social = "Banco Exemplo S.A."
    form.contratante.cnpj = "11.222.333/0001-81"
    form.escopo.modalidade = "contenciosa"
    form.escopo.atuacao_contenciosa = "MARCA_CONT_UNICA defesa em processos."
    form.honorarios_contenciosa.modalidades.valor_ato_processual = True
    form.honorarios_contenciosa.horas_extra_escopo_modo = horas_extra_modo
    if horas_extra_modo == "horaFixa":
        form.honorarios_contenciosa.horas_extra_valor = "R$ 500,00"
    return _document_xml(render_proposal(form_to_context(form)))


class TestTitulosEscopoUnico:
    """Modalidade unica + escopo unico: sem subtitulo redundante sob o titulo."""

    def test_contenciosa_unica_sem_subtitulo(self):
        texto = _texto_visivel(_render_contenciosa_unica())
        assert "Escopo de Trabalho" in texto
        assert "Escopo Contencioso:" not in texto
        assert "MARCA_CONT_UNICA" in texto

    def test_mista_mantem_subtitulos(self):
        texto = _texto_visivel(_render_mista())
        assert "Escopo Consultivo:" in texto
        assert "Escopo Contencioso:" in texto

    def test_titulo_sem_quebra_embutida(self):
        """O <w:br/> que dobrava o espacamento apos o titulo foi removido."""
        xml = _render_contenciosa_unica()
        for m in _P_RE.finditer(xml):
            p = m.group(0)
            if "Escopo de Trabalho" in "".join(_T_RE.findall(p)):
                assert "<w:br/>" not in p, "titulo da secao nao deve conter <w:br/>"
                return
        raise AssertionError("titulo 'Escopo de Trabalho' nao encontrado")


class TestHorasExtraOpcional:
    """Modo 'nenhuma' esconde a secao inteira de horas extra escopo."""

    def test_modo_nenhuma_esconde_secao(self):
        texto = _texto_visivel(_render_contenciosa_unica(horas_extra_modo="nenhuma"))
        assert "Horas para Serviços Extra Escopo" not in texto

    def test_modo_hora_fixa_mantem_secao(self):
        texto = _texto_visivel(_render_contenciosa_unica(horas_extra_modo="horaFixa"))
        assert "Horas para Serviços Extra Escopo" in texto


class TestValorPorAto:
    """Titulo da modalidade renomeado: cobre frentes nao-processuais (Ouvidoria)."""

    def test_titulo_sem_processual(self):
        texto = _texto_visivel(_render_contenciosa_unica())
        assert "Valor por Ato Processual" not in texto
        assert "Valor por Ato" in texto


# Celula de tabela sem cruzar fronteira de <w:tc> (tabelas podem aninhar).
_TC_RE = re.compile(r"<w:tc>(?:(?!</?w:tc[ >]).)*?</w:tc>", flags=re.DOTALL)


class TestCelulaSempreComParagrafo:
    """Regressao: _collapse_empty_paragraphs removia o unico <w:p> de uma
    celula quando a celula anterior tambem terminava em paragrafo vazio
    (ex.: linha de acao com so o Valor preenchido), gerando <w:tc> sem
    paragrafo, XML invalido que o Word abre como documento corrompido."""

    def _assert_toda_celula_tem_paragrafo(self, xml: str) -> None:
        sem_p = [m.group(0) for m in _TC_RE.finditer(xml) if "<w:p" not in m.group(0)]
        assert not sem_p, f"{len(sem_p)} celula(s) de tabela sem <w:p>: XML invalido para o Word"

    def test_linha_de_acao_so_com_valor(self):
        form = proposal_form_default()
        form.contratante.tipo_pessoa = "juridica"
        form.contratante.razao_social = "Acme S.A."
        form.contratante.cnpj = "11.222.333/0001-81"
        form.escopo.modalidade = "contenciosa"
        form.escopo.atuacao_contenciosa = "Defesa em processos."
        form.honorarios_contenciosa.modalidades.valor_acao = True
        form.honorarios_contenciosa.tabela_acoes = [
            AcaoRow(natureza="Trabalhista", fase="Conhecimento", valor="R$ 5.000,00"),
            AcaoRow(natureza="", fase="", valor="R$ 3.000,00"),  # 2 celulas adjacentes vazias
        ]
        self._assert_toda_celula_tem_paragrafo(_document_xml(render_proposal(form_to_context(form))))

    def test_cenario_misto_completo(self):
        """Sanidade: proposta mista padrao tambem sai com todas as celulas validas."""
        self._assert_toda_celula_tem_paragrafo(_render_mista())
