"""Schemas Pydantic do formulario.

Espelha src/shared/schema.ts do app Electron — mesmos campos, mesmos defaults,
naming convertido de camelCase (TS/Zod) para snake_case (Python/Pydantic).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

UFS = (
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
)
UF_OPTIONS = ("",) + UFS

TipoPessoa = Literal["fisica", "juridica"]
ModalidadeEscopo = Literal["consultiva", "contenciosa", "mista"]
HorasExtraEscopoModo = Literal["senioridade", "horaFixa"]


class Contato(BaseModel):
    model_config = ConfigDict(extra="ignore")
    telefone: str = ""
    email: str = ""


class Endereco(BaseModel):
    model_config = ConfigDict(extra="ignore")
    logradouro: str = ""
    numero: str = ""
    bairro: str = ""
    cep: str = ""
    cidade: str = ""
    uf: str = ""


class Contratante(BaseModel):
    model_config = ConfigDict(extra="ignore")
    tipo_pessoa: TipoPessoa = "juridica"
    nome: str = ""
    razao_social: str = ""
    cpf: str = ""
    cnpj: str = ""
    endereco: Endereco = Field(default_factory=Endereco)
    contato_nome: str = ""
    contatos: list[Contato] = Field(default_factory=lambda: [Contato()])


class Escopo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    modalidade: ModalidadeEscopo = "mista"
    atuacao_consultiva: str = ""
    atuacao_contenciosa: str = ""
    sla_ativo: bool = False
    sla_descricao: str = ""


class SenioridadeRow(BaseModel):
    model_config = ConfigDict(extra="ignore")
    categoria: str = ""
    valor: str = ""


class AcaoRow(BaseModel):
    model_config = ConfigDict(extra="ignore")
    natureza: str = ""
    fase: str = ""
    valor: str = ""


class AtoProcessualRow(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ato: str = ""
    descricao: str = ""
    valor: str = ""


class HonorariosConsultivaModalidades(BaseModel):
    model_config = ConfigDict(extra="ignore")
    hora_senioridade: bool = False
    hora_fixa: bool = False
    fixo_mensal: bool = False
    valor_projeto: bool = False


class HonorariosConsultiva(BaseModel):
    model_config = ConfigDict(extra="ignore")
    modalidades: HonorariosConsultivaModalidades = Field(default_factory=HonorariosConsultivaModalidades)
    tabela_senioridade: list[SenioridadeRow] = Field(default_factory=list)
    hora_fixa_valor: str = ""
    fixo_mensal_valor: str = ""
    fixo_mensal_cap: str = ""
    fixo_mensal_excedente: str = ""
    valor_projeto_total: str = ""
    valor_projeto_forma_pagamento: str = ""


class HonorariosContenciosaModalidades(BaseModel):
    model_config = ConfigDict(extra="ignore")
    valor_acao: bool = False
    valor_ato_processual: bool = False
    preco_mensal_massa: bool = False
    valor_projeto: bool = False


class HonorariosContenciosa(BaseModel):
    model_config = ConfigDict(extra="ignore")
    modalidades: HonorariosContenciosaModalidades = Field(default_factory=HonorariosContenciosaModalidades)
    tabela_acoes: list[AcaoRow] = Field(default_factory=list)
    tabela_atos: list[AtoProcessualRow] = Field(default_factory=list)
    preco_mensal_valor: str = ""
    preco_mensal_maximo_acoes: str = ""
    preco_mensal_maximo_acoes_extenso: str = ""
    preco_mensal_criterio_excedentes: str = ""
    valor_projeto_total: str = ""
    valor_projeto_fases_cobertas: str = ""
    valor_projeto_forma_pagamento: str = ""
    exito_ativo: bool = False
    exito_percentual: str = ""
    horas_extra_escopo_modo: HorasExtraEscopoModo = "senioridade"
    horas_extra_senioridade: list[SenioridadeRow] = Field(default_factory=list)
    horas_extra_valor: str = ""


class Despesas(BaseModel):
    model_config = ConfigDict(extra="ignore")
    gerais_descricao: str = ""
    especificas_descricao: str = ""
    taxa_manutencao_processual: str = ""


class Disposicoes(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ativo: bool = False
    descricao: str = ""


class ProposalForm(BaseModel):
    model_config = ConfigDict(extra="ignore")
    contratante: Contratante = Field(default_factory=Contratante)
    escopo: Escopo = Field(default_factory=Escopo)
    honorarios_consultiva: HonorariosConsultiva = Field(default_factory=HonorariosConsultiva)
    honorarios_contenciosa: HonorariosContenciosa = Field(default_factory=HonorariosContenciosa)
    despesas: Despesas = Field(default_factory=Despesas)
    disposicoes: Disposicoes = Field(default_factory=Disposicoes)
