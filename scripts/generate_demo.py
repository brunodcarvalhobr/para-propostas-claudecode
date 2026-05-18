"""Gera proposta demo com 3 escopos distintos (A/B/C) por modalidade.

Cada escopo recebe uma forma de pagamento independente:
- Consultivo A: Hora por senioridade
- Consultivo B: Hora Média
- Consultivo C: Fixo Mensal/Cap
- Contencioso A: Valor Mensal Por Processo
- Contencioso B: Valor por ato processual
- Contencioso C: Preço Global
"""
from __future__ import annotations

from pathlib import Path

from pmra.data_mapper import form_to_context
from pmra.schema import (
    AcaoRow,
    AtoProcessualRow,
    Contato,
    Contratante,
    DespesaItem,
    Despesas,
    Disposicoes,
    Endereco,
    Escopo,
    EscopoConsultivoItem,
    EscopoContenciosoItem,
    HonorariosConsultiva,
    HonorariosConsultivaModalidades,
    HonorariosContenciosa,
    HonorariosContenciosaModalidades,
    ProposalForm,
    SenioridadeRow,
)
from pmra.template_engine import render_proposal


SENIORIDADE_DEMO = [
    SenioridadeRow(categoria="Sócio",                  valor="R$ 1.200,00"),
    SenioridadeRow(categoria="Associado Sênior",       valor="R$ 950,00"),
    SenioridadeRow(categoria="Associado Pleno",        valor="R$ 750,00"),
    SenioridadeRow(categoria="Associado Júnior",       valor="R$ 500,00"),
    SenioridadeRow(categoria="Estagiário/Paralegal",   valor="R$ 280,00"),
]


def _hon_cons_senioridade() -> HonorariosConsultiva:
    return HonorariosConsultiva(
        modalidades=HonorariosConsultivaModalidades(hora_senioridade=True),
        tabela_senioridade=[s.model_copy() for s in SENIORIDADE_DEMO],
    )


def _hon_cons_hora_media() -> HonorariosConsultiva:
    return HonorariosConsultiva(
        modalidades=HonorariosConsultivaModalidades(hora_fixa=True),
        hora_fixa_valor="R$ 700,00",
    )


def _hon_cons_fixo_mensal() -> HonorariosConsultiva:
    return HonorariosConsultiva(
        modalidades=HonorariosConsultivaModalidades(fixo_mensal=True),
        fixo_mensal_valor="R$ 18.500,00",
        fixo_mensal_cap="35 horas",
        fixo_mensal_excedente="R$ 650,00",
    )


def _hon_cont_valor_acao() -> HonorariosContenciosa:
    return HonorariosContenciosa(
        modalidades=HonorariosContenciosaModalidades(valor_acao=True),
        tabela_acoes=[
            AcaoRow(natureza="Trabalhista",     fase="Conhecimento", valor="R$ 5.500,00"),
            AcaoRow(natureza="Trabalhista",     fase="Execução",     valor="R$ 3.800,00"),
            AcaoRow(natureza="Cível",           fase="Conhecimento", valor="R$ 7.200,00"),
            AcaoRow(natureza="Tributária",      fase="Conhecimento", valor="R$ 9.500,00"),
        ],
    )


def _hon_cont_valor_ato() -> HonorariosContenciosa:
    return HonorariosContenciosa(
        modalidades=HonorariosContenciosaModalidades(valor_ato_processual=True),
        tabela_atos=[
            AtoProcessualRow(ato="Petição Inicial",         descricao="Elaboração e protocolo da peça inaugural.",                                                                       valor="R$ 2.500,00"),
            AtoProcessualRow(ato="Contestação",             descricao="Elaboração e protocolo de defesa em processo judicial.",                                                          valor="R$ 2.200,00"),
            AtoProcessualRow(ato="Recurso Ordinário",       descricao="Elaboração e protocolo de recurso ordinário na Justiça do Trabalho.",                                             valor="R$ 3.000,00"),
            AtoProcessualRow(ato="Agravo",                  descricao="Elaboração e protocolo de agravo de instrumento ou agravo interno.",                                              valor="R$ 1.800,00"),
            AtoProcessualRow(ato="Apelação",                descricao="Elaboração e protocolo de apelação cível em 1º grau de jurisdição.",                                              valor="R$ 3.500,00"),
            AtoProcessualRow(ato="Recurso Especial / Extraordinário", descricao="Elaboração e protocolo de recursos excepcionais ao STJ e STF, inclusive agravos correlatos.",            valor="R$ 6.500,00"),
            AtoProcessualRow(ato="Audiência",               descricao="Comparecimento, acompanhamento e atuação em audiência.",                                                          valor="R$ 1.500,00"),
            AtoProcessualRow(ato="Diligência Externa",      descricao="Realização de diligência presencial em cartório, órgão público ou unidade do Contratante.",                       valor="R$ 850,00"),
        ],
    )


def _hon_cont_preco_global() -> HonorariosContenciosa:
    return HonorariosContenciosa(
        modalidades=HonorariosContenciosaModalidades(valor_projeto=True),
        valor_projeto_total="R$ 85.000,00",
        valor_projeto_fases_cobertas="Conhecimento e Execução em primeira e segunda instâncias (TRT/TRF), incluindo embargos de declaração e demais incidentes.",
        valor_projeto_forma_pagamento="40% no ato da assinatura da proposta; 30% após sentença de primeiro grau; 30% após trânsito em julgado.",
    )


def build_demo_form() -> ProposalForm:
    return ProposalForm(
        contratante=Contratante(
            tipo_pessoa="juridica",
            razao_social="Empresa Demo Multi-Escopo Ltda.",
            cnpj="12.345.678/0001-90",
            endereco=Endereco(
                logradouro="Avenida Paulista",
                numero="1578",
                bairro="Bela Vista",
                cep="01310-200",
                cidade="São Paulo",
                uf="SP",
            ),
            contato_nome="Dra. Maria Helena Carvalho",
            contatos=[
                Contato(telefone="(11) 98765-4321", email="maria.carvalho@empresademo.com.br"),
                Contato(telefone="(11) 3456-7890",  email="juridico@empresademo.com.br"),
            ],
        ),
        escopo=Escopo(
            modalidade="mista",
            atuacao_consultiva="",
            atuacao_contenciosa="",
            sla_ativo=True,
            sla_descricao=(
                "Demandas de baixa complexidade: até 3 dias úteis;\n"
                "Demandas de média complexidade: até 5 dias úteis;\n"
                "Demandas de alta complexidade (ou em língua estrangeira): entre 5 e 10 dias úteis.\n"
                "Projetos de altíssima complexidade ou alto volume: prazo a definir em conjunto com o Contratante.\n"
                "Solicitações de urgência fora do SLA acima poderão ser atendidas mediante alinhamento entre as Partes e disponibilidade."
            ),
            escopos_consultivos=[
                EscopoConsultivoItem(
                    letra="A",
                    descricao=(
                        "Consultoria societária permanente: revisão e elaboração de atos societários "
                        "(atas, alterações contratuais, acordos de sócios), pareceres em operações de M&A, "
                        "due diligence jurídica, governança corporativa e compliance societário."
                    ),
                    honorarios=_hon_cons_senioridade(),
                ),
                EscopoConsultivoItem(
                    letra="B",
                    descricao=(
                        "Consultoria contratual: revisão, elaboração e negociação de contratos comerciais "
                        "(prestação de serviços, fornecimento, distribuição, franquia, licenciamento), "
                        "termos de uso, políticas de privacidade e adequação à LGPD."
                    ),
                    honorarios=_hon_cons_hora_media(),
                ),
                EscopoConsultivoItem(
                    letra="C",
                    descricao=(
                        "Consultoria trabalhista e regulatória: orientações em rotinas de RH, elaboração de "
                        "políticas internas, programas de integridade, treinamentos in company, pareceres "
                        "regulatórios (ANATEL, ANEEL, CVM) e acompanhamento de obrigações acessórias."
                    ),
                    honorarios=_hon_cons_fixo_mensal(),
                ),
            ],
            escopos_contenciosos=[
                EscopoContenciosoItem(
                    letra="A",
                    descricao=(
                        "Contencioso trabalhista de massa: defesa em reclamações trabalhistas em primeira "
                        "e segunda instâncias, fase de conhecimento e execução, em todos os TRTs do território "
                        "nacional, incluindo audiências e recursos."
                    ),
                    honorarios=_hon_cont_valor_acao(),
                ),
                EscopoContenciosoItem(
                    letra="B",
                    descricao=(
                        "Contencioso cível estratégico: defesa em ações cíveis de alta complexidade — "
                        "ações de cobrança, indenizatórias, ações coletivas — perante juízos cíveis estaduais "
                        "e federais, com atuação por ato processual."
                    ),
                    honorarios=_hon_cont_valor_ato(),
                ),
                EscopoContenciosoItem(
                    letra="C",
                    descricao=(
                        "Litígio tributário projeto-único: condução integral de mandado de segurança e "
                        "subsequente ação ordinária visando recuperação de créditos de PIS/COFINS sobre "
                        "ICMS, com acompanhamento em todas as instâncias até o STF."
                    ),
                    honorarios=_hon_cont_preco_global(),
                ),
            ],
            forma_pagamento_por_escopo_consultiva=True,
            forma_pagamento_por_escopo_contenciosa=True,
        ),
        honorarios_consultiva=HonorariosConsultiva(),
        honorarios_contenciosa=HonorariosContenciosa(
            exito_ativo=True,
            exito_percentual="15",
            horas_extra_escopo_modo="senioridade",
            horas_extra_senioridade=[s.model_copy() for s in SENIORIDADE_DEMO],
        ),
        despesas=Despesas(
            tabela_despesas=[
                DespesaItem(
                    categoria="Despesas Logísticas",
                    descricao="Deslocamento em veículo próprio: R$ 2,50 por km e estacionamento, táxi, transporte por aplicativo, hospedagem e alimentação.",
                ),
                DespesaItem(
                    categoria="Despesas Gerais",
                    descricao="Custas e emolumentos judiciais e administrativos, depósitos recursais, diligências externas simples (R$ 150,00 por diligência), serviços de correspondentes e demais despesas correlatas.",
                ),
                DespesaItem(
                    categoria="Despesas Periciais",
                    descricao="Honorários periciais e custos de assistente técnico, suportados conforme determinação judicial e prévia ciência ao Contratante.",
                ),
            ],
            taxa_manutencao_ativa=True,
            taxa_manutencao_processual="R$ 75,00 por processo/mês",
        ),
        disposicoes=Disposicoes(
            ativo=True,
            descricao=(
                "1. Cláusula de não solicitação de colaboradores: as Partes se comprometem a não contratar "
                "ou solicitar serviços de colaboradores da outra Parte durante a vigência deste contrato "
                "e pelo período de 12 (doze) meses após seu término.\n\n"
                "2. Confidencialidade reforçada: aplicar-se-á NDA específico para informações classificadas "
                "como estratégicas pelo Contratante, com prazo de confidencialidade de 5 (cinco) anos.\n\n"
                "3. Reajuste anual: os honorários previstos nesta proposta serão reajustados anualmente "
                "pelo IPCA-IBGE acumulado nos 12 meses anteriores, aplicado na data-base da assinatura."
            ),
        ),
    )


def main() -> None:
    form = build_demo_form()
    ctx = form_to_context(form)
    bytes_ = render_proposal(ctx)
    out = Path("Proposta_Demo_Multi_Escopo.docx")
    out.write_bytes(bytes_)
    print(f"Proposta gerada: {out.resolve()} ({len(bytes_):,} bytes)")


if __name__ == "__main__":
    main()
