"""Gera proposta demo preenchida com todos os campos possíveis.

Estrutura mista com 3 escopos consultivos (A/B/C) e 3 contenciosos (A/B/C),
cada um com forma de pagamento distinta. Tabelas com linhas extras de teste.

Cobertura por modalidade:
- Consultivo A: Hora por Senioridade (tabela)
- Consultivo B: Fixo Mensal com Cap (valor + cap + excedente)
- Consultivo C: Preço Global (total + cap_ativo + cap + forma_pagamento)
- Contencioso A: Valor por Ato Processual (tabela rica)
- Contencioso B: Preço Fixo Mensal com Cap (valor + máximo + extenso + critério)
- Contencioso C: Preço Global (total + fases + forma_pagamento)

Top-level: SLA ativo, Êxito ativo, Horas Extra por Senioridade, Taxa de
manutenção processual, Disposições Específicas, todos os contatos e
endereço completo.
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
    SenioridadeRow(categoria="Of Counsel",             valor="R$ 1.050,00"),
    SenioridadeRow(categoria="Associado Sênior",       valor="R$ 950,00"),
    SenioridadeRow(categoria="Associado Pleno",        valor="R$ 750,00"),
    SenioridadeRow(categoria="Associado Júnior",       valor="R$ 500,00"),
    SenioridadeRow(categoria="Consultor Especialista", valor="R$ 850,00"),
    SenioridadeRow(categoria="Estagiário/Paralegal",   valor="R$ 280,00"),
]


def _hon_cons_senioridade() -> HonorariosConsultiva:
    return HonorariosConsultiva(
        modalidades=HonorariosConsultivaModalidades(hora_senioridade=True),
        tabela_senioridade=[s.model_copy() for s in SENIORIDADE_DEMO],
    )


def _hon_cons_fixo_mensal() -> HonorariosConsultiva:
    return HonorariosConsultiva(
        modalidades=HonorariosConsultivaModalidades(fixo_mensal=True),
        fixo_mensal_valor="R$ 18.500,00",
        fixo_mensal_cap="35 horas",
        fixo_mensal_excedente="R$ 650,00",
    )


def _hon_cons_valor_projeto() -> HonorariosConsultiva:
    return HonorariosConsultiva(
        modalidades=HonorariosConsultivaModalidades(valor_projeto=True),
        valor_projeto_total="R$ 120.000,00",
        valor_projeto_cap_ativo=True,
        valor_projeto_cap="180 horas",
        valor_projeto_forma_pagamento=(
            "30% no ato da assinatura da proposta; 40% após entrega do parecer "
            "consolidado; 30% após validação final pelo Contratante. Pagamento "
            "via boleto bancário, vencimento em 15 dias após emissão da NF."
        ),
    )


def _hon_cont_valor_ato() -> HonorariosContenciosa:
    return HonorariosContenciosa(
        modalidades=HonorariosContenciosaModalidades(valor_ato_processual=True),
        tabela_atos=[
            AtoProcessualRow(ato="Petição Inicial",                     descricao="Elaboração e protocolo da peça inaugural.",                                                                       valor="R$ 2.500,00"),
            AtoProcessualRow(ato="Contestação",                         descricao="Elaboração e protocolo de defesa em processo judicial.",                                                          valor="R$ 2.200,00"),
            AtoProcessualRow(ato="Réplica",                             descricao="Elaboração e protocolo de réplica à contestação, com impugnação a documentos juntados pelo réu.",                  valor="R$ 1.400,00"),
            AtoProcessualRow(ato="Recurso Ordinário",                   descricao="Elaboração e protocolo de recurso ordinário na Justiça do Trabalho.",                                             valor="R$ 3.000,00"),
            AtoProcessualRow(ato="Agravo",                              descricao="Elaboração e protocolo de agravo de instrumento ou agravo interno.",                                              valor="R$ 1.800,00"),
            AtoProcessualRow(ato="Apelação",                            descricao="Elaboração e protocolo de apelação cível em 1º grau de jurisdição.",                                              valor="R$ 3.500,00"),
            AtoProcessualRow(ato="Embargos de Declaração",              descricao="Elaboração e protocolo de embargos de declaração contra decisões interlocutórias e sentenças.",                   valor="R$ 1.200,00"),
            AtoProcessualRow(ato="Recurso Especial / Extraordinário",   descricao="Elaboração e protocolo de recursos excepcionais ao STJ e STF, inclusive agravos correlatos.",                     valor="R$ 6.500,00"),
            AtoProcessualRow(ato="Memoriais",                           descricao="Elaboração de memoriais para juízes e desembargadores em casos de maior complexidade ou em véspera de julgamento.", valor="R$ 2.800,00"),
            AtoProcessualRow(ato="Audiência",                           descricao="Comparecimento, acompanhamento e atuação em audiência.",                                                          valor="R$ 1.500,00"),
            AtoProcessualRow(ato="Sustentação Oral",                    descricao="Sustentação oral em sessão de julgamento em tribunal de 2ª instância ou superior.",                                valor="R$ 4.500,00"),
            AtoProcessualRow(ato="Diligência Externa",                  descricao="Realização de diligência presencial em cartório, órgão público ou unidade do Contratante.",                       valor="R$ 850,00"),
        ],
    )


def _hon_cont_preco_mensal() -> HonorariosContenciosa:
    return HonorariosContenciosa(
        modalidades=HonorariosContenciosaModalidades(preco_mensal_massa=True),
        preco_mensal_valor="R$ 28.500,00",
        preco_mensal_maximo_acoes="40",
        preco_mensal_maximo_acoes_extenso="quarenta",
        preco_mensal_criterio_excedentes=(
            "Processos excedentes ao número máximo coberto serão cobrados à parte, "
            "no valor de R$ 750,00 por processo/mês, com cobrança proporcional a "
            "partir da data de distribuição. Em caso de redução do volume abaixo "
            "do mínimo de 25 processos ativos, o valor mensal será revisto entre "
            "as Partes no início do trimestre subsequente."
        ),
    )


def _hon_cont_valor_projeto() -> HonorariosContenciosa:
    return HonorariosContenciosa(
        modalidades=HonorariosContenciosaModalidades(valor_projeto=True),
        valor_projeto_total="R$ 95.000,00",
        valor_projeto_fases_cobertas=(
            "Conhecimento e Execução em primeira e segunda instâncias (TRT/TRF), "
            "incluindo embargos de declaração, agravos internos e demais incidentes "
            "processuais, com sustentação oral em sessão de julgamento."
        ),
        valor_projeto_forma_pagamento=(
            "40% no ato da assinatura da proposta; 30% após sentença de primeiro grau; "
            "30% após trânsito em julgado. Pagamento via TED até o 5º dia útil após "
            "emissão da NF. Em caso de êxito antecipado, antecipa-se a última parcela."
        ),
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
                Contato(telefone="(11) 91234-5678", email="contratos@empresademo.com.br"),
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
                        "Consultoria contratual recorrente: revisão, elaboração e negociação de contratos "
                        "comerciais (prestação de serviços, fornecimento, distribuição, franquia, "
                        "licenciamento), termos de uso, políticas de privacidade e adequação à LGPD, "
                        "com SLA de resposta jurídica para a operação."
                    ),
                    honorarios=_hon_cons_fixo_mensal(),
                ),
                EscopoConsultivoItem(
                    letra="C",
                    descricao=(
                        "Projeto de reestruturação societária e adequação à LGPD: condução integral do "
                        "redesenho societário do grupo econômico, incluindo elaboração de novos atos, "
                        "aprovações regulatórias, mapeamento de dados pessoais, programa de governança "
                        "e treinamentos para áreas-chave."
                    ),
                    honorarios=_hon_cons_valor_projeto(),
                ),
            ],
            escopos_contenciosos=[
                EscopoContenciosoItem(
                    letra="A",
                    descricao=(
                        "Contencioso cível estratégico por ato processual: defesa em ações cíveis de alta "
                        "complexidade — cobrança, indenizatórias, ações coletivas — perante juízos cíveis "
                        "estaduais e federais, com cobrança individualizada por ato processual praticado."
                    ),
                    honorarios=_hon_cont_valor_ato(),
                ),
                EscopoContenciosoItem(
                    letra="B",
                    descricao=(
                        "Contencioso trabalhista de massa: defesa em reclamações trabalhistas em primeira "
                        "e segunda instâncias, fase de conhecimento e execução, em todos os TRTs do "
                        "território nacional, com modelo de honorários por massa processual coberta."
                    ),
                    honorarios=_hon_cont_preco_mensal(),
                ),
                EscopoContenciosoItem(
                    letra="C",
                    descricao=(
                        "Litígio tributário projeto-único: condução integral de mandado de segurança e "
                        "subsequente ação ordinária visando recuperação de créditos de PIS/COFINS sobre "
                        "ICMS, com acompanhamento em todas as instâncias até o STF."
                    ),
                    honorarios=_hon_cont_valor_projeto(),
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
                DespesaItem(
                    categoria="Despesas Cartorárias",
                    descricao="Certidões, autenticações, reconhecimentos de firma, apostilamentos e demais atos notariais necessários à condução dos serviços.",
                ),
                DespesaItem(
                    categoria="Despesas de Tradução",
                    descricao="Tradução juramentada de documentos em língua estrangeira para uso processual ou consultivo, conforme tabela vigente do tradutor habilitado.",
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
                "pelo IPCA-IBGE acumulado nos 12 meses anteriores, aplicado na data-base da assinatura.\n\n"
                "4. Comitê jurídico mensal: realização de reunião mensal de status entre o Contratado e o "
                "Departamento Jurídico do Contratante, com pauta consolidada e ata circulada em até 48 horas."
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
