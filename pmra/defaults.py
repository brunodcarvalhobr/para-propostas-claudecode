"""Defaults pre-preenchidos do formulario.

Espelha src/renderer/src/lib/defaults.ts. Valores da tabela de senioridade
refletem a politica comercial vigente da PMRA — alterar apenas com solicitacao
explicita.
"""
from __future__ import annotations

from .schema import (
    AcaoRow,
    AtoProcessualRow,
    Contratante,
    DespesaItem,
    Despesas,
    Disposicoes,
    Endereco,
    Escopo,
    HonorariosConsultiva,
    HonorariosConsultivaModalidades,
    HonorariosContenciosa,
    HonorariosContenciosaModalidades,
    ProposalForm,
    SenioridadeRow,
)

SENIORIDADE_DEFAULT: list[SenioridadeRow] = [
    SenioridadeRow(categoria="Sócio", valor="R$ 1.050,00"),
    SenioridadeRow(categoria="Associado Sênior", valor="R$ 850,00"),
    SenioridadeRow(categoria="Associado Pleno", valor="R$ 650,00"),
    SenioridadeRow(categoria="Associado Júnior", valor="R$ 450,00"),
    SenioridadeRow(categoria="Estagiário/Paralegal", valor="R$ 250,00"),
]

ATOS_PROCESSUAIS_DEFAULT: list[AtoProcessualRow] = [
    AtoProcessualRow(
        ato="Petição Inicial",
        descricao="Elaboração e protocolo da peça inaugural.",
        valor="",
    ),
    AtoProcessualRow(
        ato="Contestação",
        descricao="Elaboração e protocolo de defesa em processo judicial.",
        valor="",
    ),
    AtoProcessualRow(
        ato="Recurso Ordinário",
        descricao="Elaboração e protocolo de recurso ordinário na Justiça do Trabalho ou equivalente.",
        valor="",
    ),
    AtoProcessualRow(
        ato="Agravo",
        descricao="Elaboração e protocolo de agravo de instrumento ou agravo interno, conforme o caso.",
        valor="",
    ),
    AtoProcessualRow(
        ato="Apelação",
        descricao="Elaboração e protocolo de apelação cível em 1º grau de jurisdição.",
        valor="",
    ),
    AtoProcessualRow(
        ato="Recurso Especial / Extraordinário",
        descricao="Elaboração e protocolo de recursos excepcionais junto ao STJ e ao STF, inclusive agravos correlatos.",
        valor="",
    ),
    AtoProcessualRow(
        ato="Audiência",
        descricao="Comparecimento, acompanhamento e atuação em audiência.",
        valor="",
    ),
    AtoProcessualRow(
        ato="Diligência Externa",
        descricao="Realização de diligência presencial em cartório, órgão público ou unidade do Contratante.",
        valor="",
    ),
]

ACAO_LINHA_VAZIA = AcaoRow(natureza="", fase="", valor="")

DESPESAS_DEFAULT: list[DespesaItem] = [
    DespesaItem(
        categoria="Despesas Gerais",
        descricao="Deslocamento em veículo próprio: R$ 2,50 por km e estacionamento, táxi, transporte por aplicativo, hospedagem e alimentação;"
    ),
    DespesaItem(
        categoria="Despesas Específicas",
        descricao="Custas e emolumentos judiciais e administrativos, depósitos recursais, diligências externas simples (R$ 150,00 por diligência), serviços de correspondentes e demais despesas correlatas, apurados conforme necessidade."
    )
]


def proposal_form_default() -> ProposalForm:
    return ProposalForm(
        contratante=Contratante(
            tipo_pessoa="juridica",
            endereco=Endereco(),
        ),
        escopo=Escopo(modalidade="mista"),
        honorarios_consultiva=HonorariosConsultiva(
            modalidades=HonorariosConsultivaModalidades(),
            tabela_senioridade=[s.model_copy() for s in SENIORIDADE_DEFAULT],
        ),
        honorarios_contenciosa=HonorariosContenciosa(
            modalidades=HonorariosContenciosaModalidades(),
            tabela_acoes=[ACAO_LINHA_VAZIA.model_copy()],
            tabela_atos=[a.model_copy() for a in ATOS_PROCESSUAIS_DEFAULT],
            horas_extra_escopo_modo="senioridade",
            horas_extra_senioridade=[s.model_copy() for s in SENIORIDADE_DEFAULT],
        ),
        despesas=Despesas(
            tabela_despesas=[d.model_copy() for d in DESPESAS_DEFAULT],
            taxa_manutencao_processual="",
        ),
        disposicoes=Disposicoes(),
    )
