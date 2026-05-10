"""Mapeia ProposalForm -> contexto para o template Jinja2.

Espelha src/main/services/data-mapper.ts. As decisoes de visibilidade (PF/PJ,
modalidade consultiva/contenciosa/mista, SLA, Exito, etc.) sao calculadas aqui
e expostas como flags `show_*` que o template consume diretamente.
"""
from __future__ import annotations

import re
from typing import Any

from .schema import Contato, Endereco, ProposalForm


def _non_empty(*parts: str) -> str:
    return ", ".join(p.strip() for p in parts if p and p.strip())


def _fmt_money(v: str) -> str:
    """Formata valor monetário brasileiro.

    '500'        → 'R$ 500,00'
    '1050'       → 'R$ 1.050,00'
    '1.050,50'   → 'R$ 1.050,50'
    'R$ 1.050,00'→ 'R$ 1.050,00'  (sem alteração)
    'texto livre'→ 'texto livre'   (sem alteração)
    ''           → ''
    """
    v = str(v).strip()
    if not v or v in ("nan", "None"):
        return ""
    if "R$" in v:
        return v  # já formatado

    # Só formata se o valor for puramente numérico (dígitos + separadores BR)
    # Qualquer outro caractere (letras, %, etc.) indica texto descritivo
    if not re.match(r"^\s*[\d.,]+\s*$", v):
        return v

    cleaned = re.sub(r"[^\d.,]", "", v)
    if not cleaned:
        return v

    try:
        if "," in cleaned:
            # Formato BR: ponto = milhar, vírgula = decimal
            amount = float(cleaned.replace(".", "").replace(",", "."))
        else:
            # Sem vírgula: trata ponto como milhar (ex.: "1.050" → 1050)
            amount = float(cleaned.replace(".", ""))
        formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted}"
    except (ValueError, OverflowError):
        return v


def _fmt_rows(rows: list[dict], money_cols: tuple[str, ...] = ("valor",)) -> list[dict]:
    """Aplica _fmt_money às colunas monetárias de cada linha de tabela."""
    return [
        {k: (_fmt_money(v) if k in money_cols else v) for k, v in row.items()}
        for row in rows
    ]


def montar_endereco(end: Endereco) -> str:
    linha1 = _non_empty(
        ", ".join(p for p in [end.logradouro, end.numero] if p),
        end.bairro,
    )
    cidade_uf = "/".join(p for p in [end.cidade, end.uf] if p)
    return ", ".join(p for p in [linha1, end.cep, cidade_uf] if p)


def montar_contatos(contatos: list[Contato]) -> str:
    linhas: list[str] = []
    for c in contatos:
        if not (c.telefone.strip() or c.email.strip()):
            continue
        partes: list[str] = []
        if c.telefone.strip():
            partes.append(f"Telefone: {c.telefone.strip()}")
        if c.email.strip():
            partes.append(f"E-mail: {c.email.strip()}")
        linhas.append("; ".join(partes))
    return "\n".join(linhas)


def form_to_context(form: ProposalForm) -> dict[str, Any]:
    pf = form.contratante.tipo_pessoa == "fisica"
    pj = not pf

    show_consultiva = form.escopo.modalidade in ("consultiva", "mista")
    show_contenciosa = form.escopo.modalidade in ("contenciosa", "mista")

    consultiva_mod = form.honorarios_consultiva.modalidades
    contenciosa_mod = form.honorarios_contenciosa.modalidades

    return {
        "contratante": {
            "pf": pf,
            "pj": pj,
            "nome": form.contratante.nome,
            "razao_social": form.contratante.razao_social,
            "cpf": form.contratante.cpf,
            "cnpj": form.contratante.cnpj,
            "endereco_completo": montar_endereco(form.contratante.endereco),
            "contato_nome": form.contratante.contato_nome,
            "contatos_texto": montar_contatos(form.contratante.contatos),
        },
        "escopo": {
            "show_consultiva": show_consultiva,
            "show_contenciosa": show_contenciosa,
            "atuacao_consultiva": form.escopo.atuacao_consultiva,
            "atuacao_contenciosa": form.escopo.atuacao_contenciosa,
            "show_sla": form.escopo.sla_ativo,
            "sla_descricao": form.escopo.sla_descricao,
        },
        "consultiva": {
            "show_hora_senioridade": show_consultiva and consultiva_mod.hora_senioridade,
            "show_hora_fixa": show_consultiva and consultiva_mod.hora_fixa,
            "show_fixo_mensal": show_consultiva and consultiva_mod.fixo_mensal,
            "show_valor_projeto": show_consultiva and consultiva_mod.valor_projeto,
            "tabela_senioridade": _fmt_rows([s.model_dump() for s in form.honorarios_consultiva.tabela_senioridade]),
            "hora_fixa_valor": _fmt_money(form.honorarios_consultiva.hora_fixa_valor),
            "fixo_mensal_valor": _fmt_money(form.honorarios_consultiva.fixo_mensal_valor),
            "fixo_mensal_cap": form.honorarios_consultiva.fixo_mensal_cap,
            "fixo_mensal_excedente": _fmt_money(form.honorarios_consultiva.fixo_mensal_excedente),
            "valor_projeto_total": _fmt_money(form.honorarios_consultiva.valor_projeto_total),
            "valor_projeto_forma_pagamento": form.honorarios_consultiva.valor_projeto_forma_pagamento,
        },
        "contenciosa": {
            "show_valor_acao": show_contenciosa and contenciosa_mod.valor_acao,
            "show_valor_ato": show_contenciosa and contenciosa_mod.valor_ato_processual,
            "show_preco_mensal": show_contenciosa and contenciosa_mod.preco_mensal_massa,
            "show_valor_projeto": show_contenciosa and contenciosa_mod.valor_projeto,
            "tabela_acoes": _fmt_rows([a.model_dump() for a in form.honorarios_contenciosa.tabela_acoes]),
            "tabela_atos": _fmt_rows([a.model_dump() for a in form.honorarios_contenciosa.tabela_atos]),
            "preco_mensal_valor": _fmt_money(form.honorarios_contenciosa.preco_mensal_valor),
            "preco_mensal_maximo_acoes": form.honorarios_contenciosa.preco_mensal_maximo_acoes,
            "preco_mensal_maximo_acoes_extenso": form.honorarios_contenciosa.preco_mensal_maximo_acoes_extenso,
            "preco_mensal_criterio_excedentes": form.honorarios_contenciosa.preco_mensal_criterio_excedentes,
            "valor_projeto_total": _fmt_money(form.honorarios_contenciosa.valor_projeto_total),
            "valor_projeto_fases_cobertas": form.honorarios_contenciosa.valor_projeto_fases_cobertas,
            "valor_projeto_forma_pagamento": form.honorarios_contenciosa.valor_projeto_forma_pagamento,
            "show_exito": show_contenciosa and form.honorarios_contenciosa.exito_ativo,
            "exito_percentual": form.honorarios_contenciosa.exito_percentual,
            "show_extra_senioridade": (
                show_contenciosa and form.honorarios_contenciosa.horas_extra_escopo_modo == "senioridade"
            ),
            "show_extra_hora_fixa": (
                show_contenciosa and form.honorarios_contenciosa.horas_extra_escopo_modo == "horaFixa"
            ),
            "horas_extra_senioridade": _fmt_rows([
                s.model_dump() for s in form.honorarios_contenciosa.horas_extra_senioridade
            ]),
            "horas_extra_valor": _fmt_money(form.honorarios_contenciosa.horas_extra_valor),
        },
        "despesas": {
            "gerais_descricao": form.despesas.gerais_descricao,
            "especificas_descricao": form.despesas.especificas_descricao,
            "taxa_manutencao_processual": _fmt_money(form.despesas.taxa_manutencao_processual),
            "show_taxa_manutencao": bool(form.despesas.taxa_manutencao_processual.strip()),
        },
        "disposicoes": {
            "show": form.disposicoes.ativo,
            "descricao": form.disposicoes.descricao,
        },
        "meta": {
            "nome_ou_razao_social": form.contratante.nome if pf else form.contratante.razao_social,
        },
    }
