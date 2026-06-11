"""Schemas Pydantic do formulario.

Espelha src/shared/schema.ts do app Electron — mesmos campos, mesmos defaults,
naming convertido de camelCase (TS/Zod) para snake_case (Python/Pydantic).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

UFS = (
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
)
UF_OPTIONS = ("",) + UFS

TipoPessoa = Literal["fisica", "juridica"]
ModalidadeEscopo = Literal["consultiva", "contenciosa", "mista"]
HorasExtraEscopoModo = Literal["senioridade", "horaFixa", "nenhuma"]


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

    @model_validator(mode="after")
    def _clear_pf_pj_crossfields(self) -> "Contratante":
        # Garante que campos da outra pessoa nao vazem para o documento final:
        # PF nao deve carregar razao_social/cnpj; PJ nao deve carregar nome/cpf.
        if self.tipo_pessoa == "fisica":
            self.razao_social = ""
            self.cnpj = ""
        else:
            self.nome = ""
            self.cpf = ""
        return self


class EscopoConsultivoItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    letra: str = "A"
    descricao: str = ""
    honorarios: "HonorariosConsultiva" = Field(default_factory=lambda: HonorariosConsultiva())


class EscopoContenciosoItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    letra: str = "A"
    descricao: str = ""
    honorarios: "HonorariosContenciosa" = Field(default_factory=lambda: HonorariosContenciosa())


class Escopo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    modalidade: ModalidadeEscopo = "mista"
    atuacao_consultiva: str = ""
    atuacao_contenciosa: str = ""
    sla_ativo: bool = False
    sla_descricao: str = ""
    escopos_consultivos: list[EscopoConsultivoItem] = Field(default_factory=list)
    escopos_contenciosos: list[EscopoContenciosoItem] = Field(default_factory=list)
    forma_pagamento_por_escopo_consultiva: bool = False
    forma_pagamento_por_escopo_contenciosa: bool = False

    @model_validator(mode="after")
    def _sla_so_para_consultiva_ou_mista(self) -> "Escopo":
        # SLA nao se aplica a escopo puramente contencioso — zera para garantir
        # que nem o template nem o resumo renderizem essa secao.
        if self.modalidade == "contenciosa":
            self.sla_ativo = False
            self.sla_descricao = ""
        return self


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
    valor_projeto_cap_ativo: bool = False
    valor_projeto_cap: str = ""
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

    @model_validator(mode="after")
    def _zera_horas_extra_se_nenhuma(self) -> "HonorariosContenciosa":
        # Usuario optou por nao definir hora extra-escopo — zera para garantir
        # que nem o template nem o resumo renderizem a secao.
        if self.horas_extra_escopo_modo == "nenhuma":
            self.horas_extra_senioridade = []
            self.horas_extra_valor = ""
        return self


class DespesaItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    categoria: str = ""
    descricao: str = ""


class Despesas(BaseModel):
    model_config = ConfigDict(extra="ignore")
    tabela_despesas: list[DespesaItem] = Field(default_factory=list)
    taxa_manutencao_ativa: bool = False
    taxa_manutencao_processual: str = ""

    @model_validator(mode="after")
    def _zera_taxa_se_inativa(self) -> "Despesas":
        # Se a taxa nao esta ativa, garante que o valor nao vaze para o documento.
        if not self.taxa_manutencao_ativa:
            self.taxa_manutencao_processual = ""
        return self


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
