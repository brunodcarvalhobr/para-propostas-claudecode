"""Testes do template_engine — regra de justificacao do texto do formulario.

Regra: texto livre do formulario sai justificado QUANDO e texto corrido (sem
quebras). Se o usuario aperta Enter (gera '\\n'), o paragrafo volta a alinhar a
esquerda — caso contrario o Word estica horrivelmente a linha antes da quebra.

- `_justify_form_paragraphs` (pre-render) forca w:jc=both nos paragrafos de
  texto do formulario.
- `_left_align_multiline` (pos-render) remove o w:jc=both dos paragrafos cujo
  texto contem '\\n'.
"""
from __future__ import annotations

import re
import zipfile
from io import BytesIO

import pytest

from pmra.data_mapper import form_to_context
from pmra.defaults import proposal_form_default
from pmra.schema import (
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


def _render_multilinha() -> str:
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
    return _document_xml(render_proposal(form_to_context(form)))


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


class TestTextoMultilinhaAlinhadoEsquerda:
    """Texto com quebra de linha (Enter) NAO deve ser justificado."""

    @pytest.fixture(scope="class")
    def xml(self) -> str:
        return _render_multilinha()

    @pytest.mark.parametrize(
        "marker",
        [
            "MARCA_CONSULTIVO_ML",   # Escopo Consultivo com 2 paragrafos
            "MARCA_CONTENCIOSO_ML",
            "MARCA_SLA_ML",          # SLA em lista (caso do print do usuario)
            "MARCA_DISP_ML",         # Disposicoes com paragrafos separados
            "MARCA_CONTATO_A",       # contatos_texto com 2 contatos => multilinha
        ],
    )
    def test_texto_multilinha_nao_justificado(self, xml, marker):
        jc = _jc_of_paragraph_containing(xml, marker)
        assert jc != "both", (
            f"texto multilinha {marker!r} foi justificado (w:jc={jc}); "
            f"deveria ficar alinhado a esquerda para nao esticar as linhas"
        )

    def test_consultivo_continuo_ainda_justifica(self, xml):
        """Sanidade: o caso multilinha nao deve afetar o caminho de texto corrido."""
        cont_xml = _render_mista()
        assert _jc_of_paragraph_containing(cont_xml, "MARCA_CONSULTIVO") == "both"
