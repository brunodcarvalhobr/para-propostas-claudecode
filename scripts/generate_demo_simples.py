"""Gera proposta demo no modo Escopo Simples (legacy: 1 escopo por modalidade).

Mesmo cliente e SLA da demo multi, porém:
- 1 escopo consultivo único (atuacao_consultiva como texto livre)
- 1 escopo contencioso único (atuacao_contenciosa como texto livre)
- 1 conjunto único de honorários consultivos cobrindo várias modalidades
- 1 conjunto único de honorários contenciosos cobrindo várias modalidades
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


def build_demo_form() -> ProposalForm:
    return ProposalForm(
        contratante=Contratante(
            tipo_pessoa="juridica",
            razao_social="Empresa Demo Simples Ltda.",
            cnpj="98.765.432/0001-10",
            endereco=Endereco(
                logradouro="Rua Joaquim Floriano",
                numero="820",
                bairro="Itaim Bibi",
                cep="04534-003",
                cidade="São Paulo",
                uf="SP",
            ),
            contato_nome="Dr. Ricardo Mendes Almeida",
            contatos=[
                Contato(telefone="(11) 99888-7766", email="ricardo.almeida@empresademosimples.com.br"),
                Contato(telefone="(11) 3232-4545",  email="juridico@empresademosimples.com.br"),
            ],
        ),
        escopo=Escopo(
            modalidade="mista",
            atuacao_consultiva=(
                "Consultoria jurídica integral nas áreas societária, contratual, trabalhista e "
                "regulatória, abrangendo: (i) revisão e elaboração de atos societários e contratos "
                "comerciais; (ii) pareceres em operações de M&A e due diligence jurídica; "
                "(iii) orientações em rotinas de RH e adequação à LGPD; (iv) acompanhamento "
                "regulatório (ANATEL, ANEEL, CVM) e suporte a obrigações acessórias; (v) "
                "elaboração de políticas internas, programas de integridade e treinamentos in company."
            ),
            atuacao_contenciosa=(
                "Patrocínio integral do contencioso do Contratante perante todas as instâncias "
                "do Poder Judiciário brasileiro, abrangendo: (i) contencioso trabalhista de massa "
                "(reclamações em 1ª e 2ª instâncias, audiências e recursos); (ii) contencioso "
                "cível estratégico (ações de cobrança, indenizatórias, coletivas); e (iii) "
                "contencioso tributário (mandados de segurança e ações ordinárias para recuperação "
                "de créditos), com atuação até o STF e o STJ quando cabível."
            ),
            sla_ativo=True,
            sla_descricao=(
                "Demandas de baixa complexidade: até 3 dias úteis;\n"
                "Demandas de média complexidade: até 5 dias úteis;\n"
                "Demandas de alta complexidade (ou em língua estrangeira): entre 5 e 10 dias úteis.\n"
                "Projetos de altíssima complexidade ou alto volume: prazo a definir em conjunto com o Contratante.\n"
                "Solicitações de urgência fora do SLA acima poderão ser atendidas mediante alinhamento entre as Partes e disponibilidade."
            ),
        ),
        honorarios_consultiva=HonorariosConsultiva(
            modalidades=HonorariosConsultivaModalidades(
                hora_senioridade=True,
                fixo_mensal=True,
            ),
            tabela_senioridade=[s.model_copy() for s in SENIORIDADE_DEMO],
            fixo_mensal_valor="R$ 18.500,00",
            fixo_mensal_cap="35 horas",
            fixo_mensal_excedente="R$ 650,00",
        ),
        honorarios_contenciosa=HonorariosContenciosa(
            modalidades=HonorariosContenciosaModalidades(
                valor_acao=True,
                valor_ato_processual=True,
            ),
            tabela_acoes=[
                AcaoRow(natureza="Trabalhista", fase="Conhecimento", valor="R$ 5.500,00"),
                AcaoRow(natureza="Trabalhista", fase="Execução",     valor="R$ 3.800,00"),
                AcaoRow(natureza="Cível",       fase="Conhecimento", valor="R$ 7.200,00"),
                AcaoRow(natureza="Tributária",  fase="Conhecimento", valor="R$ 9.500,00"),
            ],
            tabela_atos=[
                AtoProcessualRow(ato="Petição Inicial",   descricao="Elaboração e protocolo da peça inaugural.",                                                     valor="R$ 2.500,00"),
                AtoProcessualRow(ato="Contestação",       descricao="Elaboração e protocolo de defesa em processo judicial.",                                        valor="R$ 2.200,00"),
                AtoProcessualRow(ato="Recurso Ordinário", descricao="Elaboração e protocolo de recurso ordinário na Justiça do Trabalho.",                           valor="R$ 3.000,00"),
                AtoProcessualRow(ato="Apelação",          descricao="Elaboração e protocolo de apelação cível em 1º grau de jurisdição.",                            valor="R$ 3.500,00"),
                AtoProcessualRow(ato="Audiência",         descricao="Comparecimento, acompanhamento e atuação em audiência.",                                        valor="R$ 1.500,00"),
            ],
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
    out = Path("Proposta_Demo_Simples.docx")
    out.write_bytes(bytes_)
    print(f"Proposta gerada: {out.resolve()} ({len(bytes_):,} bytes)")


if __name__ == "__main__":
    main()
