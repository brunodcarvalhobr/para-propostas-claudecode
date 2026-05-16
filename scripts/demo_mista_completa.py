#!/usr/bin/env python3
"""Gera uma proposta mista completa com todas as secoes preenchidas.

Util para conferencia visual do template apos alteracoes — gera um unico
.docx em out/PMRA_Proposta_Mista_Completa_Demo.docx.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pmra.data_mapper import form_to_context
from pmra.defaults import proposal_form_default
from pmra.schema import (
    AcaoRow, AtoProcessualRow, Contato, DespesaItem, Endereco, SenioridadeRow,
)
from pmra.template_engine import render_proposal


def cenario_mista_completa():
    f = proposal_form_default()

    # ── Contratante PJ
    f.contratante.tipo_pessoa = "juridica"
    f.contratante.razao_social = "Industrias Verdejar Ltda."
    f.contratante.cnpj = "11.222.333/0001-81"
    f.contratante.endereco = Endereco(
        logradouro="Avenida Afonso Pena",
        numero="1500, Sala 1201",
        bairro="Funcionarios",
        cep="30130-005",
        cidade="Belo Horizonte",
        uf="MG",
    )
    f.contratante.contato_nome = "Carolina Mendes (Diretora Juridica)"
    f.contratante.contatos = [
        Contato(telefone="(31) 3333-4444", email="juridico@verdejar.com.br"),
        Contato(telefone="(31) 99999-8888", email="carolina.mendes@verdejar.com.br"),
    ]

    # ── Escopo mista, com SLA
    f.escopo.modalidade = "mista"
    f.escopo.atuacao_consultiva = (
        "Assessoria juridica preventiva nas areas societaria, contratual, "
        "trabalhista, tributaria e ambiental.\n"
        "Elaboracao e revisao de contratos, pareceres juridicos e atos societarios.\n"
        "Acompanhamento de operacoes de M&A e reestruturacao societaria."
    )
    f.escopo.atuacao_contenciosa = (
        "Defesa em processos civeis, trabalhistas e tributarios em todas as instancias.\n"
        "Atuacao perante o TJMG, TRT-3, TRF-6 e Tribunais Superiores."
    )
    f.escopo.sla_ativo = True
    f.escopo.sla_descricao = (
        "Baixa complexidade: ate 5 dias uteis.\n"
        "Media complexidade: ate 2 dias uteis.\n"
        "Alta complexidade / urgente: ate 24 horas."
    )

    # ── Honorarios Consultiva — todas as 4 modalidades ativas
    cm = f.honorarios_consultiva.modalidades
    cm.hora_senioridade = True
    cm.hora_fixa = True
    cm.fixo_mensal = True
    cm.valor_projeto = True

    f.honorarios_consultiva.tabela_senioridade = [
        SenioridadeRow(categoria="Socio", valor="1.050,00"),
        SenioridadeRow(categoria="Associado Senior", valor="850,00"),
        SenioridadeRow(categoria="Associado Pleno", valor="650,00"),
        SenioridadeRow(categoria="Associado Junior", valor="450,00"),
        SenioridadeRow(categoria="Estagiario/Paralegal", valor="250,00"),
    ]
    f.honorarios_consultiva.hora_fixa_valor = "700,00"
    f.honorarios_consultiva.fixo_mensal_valor = "15.000,00"
    f.honorarios_consultiva.fixo_mensal_cap = "30 horas"
    f.honorarios_consultiva.fixo_mensal_excedente = "600,00"
    f.honorarios_consultiva.valor_projeto_total = "85.000,00"
    f.honorarios_consultiva.valor_projeto_forma_pagamento = (
        "30% na assinatura, 30% na entrega do diagnostico e 40% na conclusao do projeto."
    )

    # ── Honorarios Contenciosa — todas as 4 modalidades ativas + exito
    cm = f.honorarios_contenciosa.modalidades
    cm.valor_acao = True
    cm.valor_ato_processual = True
    cm.preco_mensal_massa = True
    cm.valor_projeto = True

    f.honorarios_contenciosa.tabela_acoes = [
        AcaoRow(natureza="Trabalhista", fase="Conhecimento (1a instancia)", valor="5.000,00"),
        AcaoRow(natureza="Trabalhista", fase="Recurso ordinario (2a instancia)", valor="3.500,00"),
        AcaoRow(natureza="Civel", fase="Conhecimento (1a instancia)", valor="6.500,00"),
        AcaoRow(natureza="Tributaria", fase="Defesa administrativa", valor="8.000,00"),
        AcaoRow(natureza="Tributaria", fase="Execucao fiscal", valor="12.000,00"),
    ]
    f.honorarios_contenciosa.tabela_atos = [
        AtoProcessualRow(ato="Audiencia inicial", descricao="Comparecimento e sustentacao oral", valor="1.500,00"),
        AtoProcessualRow(ato="Audiencia de instrucao", descricao="Inquiricao de testemunhas", valor="2.500,00"),
        AtoProcessualRow(ato="Memoriais", descricao="Razoes finais escritas", valor="1.800,00"),
        AtoProcessualRow(ato="Recurso", descricao="Apelacao ou agravo", valor="3.000,00"),
    ]
    f.honorarios_contenciosa.preco_mensal_valor = "8.000,00"
    f.honorarios_contenciosa.preco_mensal_maximo_acoes = "20"
    f.honorarios_contenciosa.preco_mensal_maximo_acoes_extenso = "vinte"
    f.honorarios_contenciosa.preco_mensal_criterio_excedentes = (
        "Acima de 20 acoes simultaneas, cada nova acao sera cobrada conforme tabela "
        "de Valor Mensal Por Processo, proporcionalmente ao mes de distribuicao."
    )
    f.honorarios_contenciosa.valor_projeto_total = "120.000,00"
    f.honorarios_contenciosa.valor_projeto_fases_cobertas = (
        "Inclui defesa em primeira e segunda instancia para a acao trabalhista coletiva "
        "do sindicato (Processo n. 0001234-56.2024.5.03.0001), abrangendo audiencias, "
        "memoriais, recurso ordinario e contrarrazoes."
    )
    f.honorarios_contenciosa.valor_projeto_forma_pagamento = (
        "40% na assinatura, 30% apos audiencia de instrucao e 30% apos transito em julgado."
    )
    f.honorarios_contenciosa.exito_ativo = True
    f.honorarios_contenciosa.exito_percentual = "15"
    f.honorarios_contenciosa.horas_extra_escopo_modo = "senioridade"
    f.honorarios_contenciosa.horas_extra_senioridade = [
        SenioridadeRow(categoria="Socio", valor="1.200,00"),
        SenioridadeRow(categoria="Associado Senior", valor="950,00"),
        SenioridadeRow(categoria="Associado Pleno", valor="750,00"),
    ]

    # ── Despesas
    f.despesas.tabela_despesas = [
        DespesaItem(
            categoria="Despesas Logisticas",
            descricao=(
                "Deslocamento em veiculo proprio: R$ 2,50 por km; estacionamento, "
                "taxi, transporte por aplicativo, hospedagem e alimentacao apurados "
                "conforme comprovantes."
            ),
        ),
        DespesaItem(
            categoria="Despesas Gerais",
            descricao=(
                "Custas e emolumentos judiciais e administrativos, depositos recursais, "
                "diligencias externas simples (R$ 150,00 por diligencia), servicos de "
                "correspondentes e demais despesas correlatas."
            ),
        ),
    ]
    f.despesas.taxa_manutencao_processual = "50,00 por processo/mes"

    # ── Disposicoes especificas
    f.disposicoes.ativo = True
    f.disposicoes.descricao = (
        "Foro eleito: comarca de Belo Horizonte/MG.\n"
        "Sigilo: as partes obrigam-se a manter sigilo sobre todas as informacoes "
        "trocadas durante a vigencia deste contrato, pelo prazo de 5 (cinco) anos "
        "apos seu termino.\n"
        "Conflito de interesses: a contratada compromete-se a comunicar imediatamente "
        "qualquer conflito de interesses identificado durante a execucao dos servicos."
    )

    return f


def main() -> None:
    out_dir = ROOT / "out"
    out_dir.mkdir(exist_ok=True)

    form = cenario_mista_completa()
    context = form_to_context(form)
    data = render_proposal(context)

    path = out_dir / "PMRA_Proposta_Mista_Completa_Demo.docx"
    path.write_bytes(data)
    print(f"  ok ({len(data):,} bytes)")
    print(f"  -> {path}")


if __name__ == "__main__":
    main()
