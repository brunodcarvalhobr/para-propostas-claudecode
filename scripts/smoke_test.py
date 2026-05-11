#!/usr/bin/env python3
"""Smoke test end-to-end: defaults -> contexto -> docxtpl -> .docx valido.

Renderiza 3 cenarios (PF/Consultiva, PJ/Mista completa, PJ/Contenciosa
minimal) e salva os arquivos em out/ para inspecao manual.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pmra.data_mapper import form_to_context
from pmra.defaults import proposal_form_default
from pmra.schema import Contato, Endereco
from pmra.template_engine import render_proposal


def assert_valid_docx(data: bytes, label: str) -> None:
    assert data[:4] == b"PK\x03\x04", f"{label}: nao parece um zip/docx valido"
    with zipfile.ZipFile(__import__("io").BytesIO(data)) as zf:
        names = set(zf.namelist())
        assert "word/document.xml" in names, f"{label}: faltando word/document.xml"
        # Garante que nao sobraram tags Jinja2 nao processadas
        body = zf.read("word/document.xml").decode("utf-8")
        for marker in ("{%p ", "{%tr ", "{% if ", "{% for "):
            if marker in body:
                raise AssertionError(f"{label}: marcador Jinja nao processado: {marker!r}")
    print(f"  ok: {label} ({len(data):,} bytes)")


def cenario_pf_consultiva():
    form = proposal_form_default()
    form.contratante.tipo_pessoa = "fisica"
    form.contratante.nome = "Joao da Silva"
    form.contratante.cpf = "123.456.789-00"
    form.contratante.endereco = Endereco(
        logradouro="Rua das Flores", numero="100", bairro="Centro",
        cep="30000-000", cidade="Belo Horizonte", uf="MG",
    )
    form.contratante.contato_nome = "Joao da Silva"
    form.contratante.contatos = [Contato(telefone="(31) 99999-0000", email="joao@example.com")]
    form.escopo.modalidade = "consultiva"
    form.escopo.atuacao_consultiva = "Consultoria em direito societario.\nRevisao de contratos."
    form.honorarios_consultiva.modalidades.hora_senioridade = True
    form.honorarios_consultiva.modalidades.hora_fixa = True
    form.honorarios_consultiva.hora_fixa_valor = "R$ 700,00"
    return form


def cenario_pj_mista_completa():
    form = proposal_form_default()
    form.contratante.tipo_pessoa = "juridica"
    form.contratante.razao_social = "Acme Industria S.A."
    form.contratante.cnpj = "12.345.678/0001-99"
    form.contratante.endereco = Endereco(
        logradouro="Av. Paulista", numero="1000", bairro="Bela Vista",
        cep="01310-100", cidade="Sao Paulo", uf="SP",
    )
    form.contratante.contato_nome = "Maria Souza"
    form.contratante.contatos = [
        Contato(telefone="(11) 3000-1000", email="maria@acme.com"),
        Contato(telefone="(11) 3000-1001", email="juridico@acme.com"),
    ]
    form.escopo.modalidade = "mista"
    form.escopo.atuacao_consultiva = "Consultoria empresarial completa."
    form.escopo.atuacao_contenciosa = "Defesa em processos civeis e trabalhistas."
    form.escopo.sla_ativo = True
    form.escopo.sla_descricao = "Baixa: 5 dias\nMedia: 2 dias\nAlta: 24 horas"
    form.honorarios_consultiva.modalidades.hora_senioridade = True
    form.honorarios_consultiva.modalidades.fixo_mensal = True
    form.honorarios_consultiva.fixo_mensal_valor = "R$ 15.000,00"
    form.honorarios_consultiva.fixo_mensal_cap = "30 horas"
    form.honorarios_consultiva.fixo_mensal_excedente = "R$ 600,00"
    form.honorarios_contenciosa.modalidades.valor_acao = True
    form.honorarios_contenciosa.modalidades.valor_ato_processual = True
    form.honorarios_contenciosa.tabela_acoes = [
        type(form.honorarios_contenciosa.tabela_acoes[0])(
            natureza="Trabalhista", fase="Conhecimento", valor="R$ 5.000,00"
        )
    ]
    form.honorarios_contenciosa.exito_ativo = True
    form.honorarios_contenciosa.exito_percentual = "10"
    form.disposicoes.ativo = True
    form.disposicoes.descricao = "Foro eleito: comarca de Sao Paulo/SP."
    form.despesas.taxa_manutencao_processual = "R$ 50,00 por processo/mes"
    return form


def cenario_pj_contenciosa_minimal():
    form = proposal_form_default()
    form.contratante.tipo_pessoa = "juridica"
    form.contratante.razao_social = "Beta Ltda"
    form.contratante.cnpj = "98.765.432/0001-11"
    form.escopo.modalidade = "contenciosa"
    form.escopo.atuacao_contenciosa = "Trabalhista — defesa."
    form.honorarios_contenciosa.modalidades.preco_mensal_massa = True
    form.honorarios_contenciosa.preco_mensal_valor = "R$ 8.000,00"
    form.honorarios_contenciosa.preco_mensal_maximo_acoes = "20"
    form.honorarios_contenciosa.preco_mensal_maximo_acoes_extenso = "vinte"
    form.honorarios_contenciosa.horas_extra_escopo_modo = "horaFixa"
    form.honorarios_contenciosa.horas_extra_valor = "R$ 500,00"
    return form


def main() -> None:
    out_dir = ROOT / "out"
    out_dir.mkdir(exist_ok=True)

    cenarios = [
        ("pf_consultiva.docx", cenario_pf_consultiva()),
        ("pj_mista_completa.docx", cenario_pj_mista_completa()),
        ("pj_contenciosa_minimal.docx", cenario_pj_contenciosa_minimal()),
    ]

    for nome, form in cenarios:
        ctx = form_to_context(form)
        data = render_proposal(ctx)
        path = out_dir / nome
        path.write_bytes(data)
        assert_valid_docx(data, nome)
        print(f"  -> {path}")

    print("\nSmoke test passou.")


if __name__ == "__main__":
    main()
