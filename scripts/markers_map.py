"""Mapa unico marker <-> tag Jinja.

Usado por:
  - scripts/to_markers.py: gera PMRA_Template_Markers.docx a partir do Jinja
  - scripts/build_from_markers.py: faz o caminho inverso (markers editados -> Jinja)

Convencoes:
  [NOME_VARIAVEL]    interpolacao simples (vira {{ caminho.var }})
  [SE_X] ... [FIM_SE]    condicional paragraph-level (remove paragrafo inteiro se falso)
  [SE_X_INLINE] ... [FIM_SE_INLINE]  condicional inline (so o texto, mantem paragrafo)
  [PARA_CADA_X] ... [FIM_PARA_CADA]  loop table-row-level (remove linha inteira em iteracao)
"""
from __future__ import annotations

# Variaveis simples — {{...}}
VARIAVEIS: dict[str, str] = {
    "{{contratante.cpf}}": "[CPF]",
    "{{contratante.cnpj}}": "[CNPJ]",
    "{{contratante.endereco_completo}}": "[ENDERECO]",
    "{{contratante.contato_nome}}": "[CONTATO_NOME]",
    "{{contratante.contatos_texto}}": "[CONTATOS]",
    # Renderizado via RichText (negrito + caixa alta) — prefixo `r` necessario
    "{{r meta.nome_ou_razao_social}}": "[NOME_OU_RAZAO]",

    "{{escopo.atuacao_consultiva}}": "[ATUACAO_CONSULTIVA]",
    "{{escopo.atuacao_contenciosa}}": "[ATUACAO_CONTENCIOSA]",
    "{{escopo.sla_descricao}}": "[SLA]",

    "{{consultiva.hora_fixa_valor}}": "[CONS_HORA_MEDIA_VALOR]",
    "{{consultiva.fixo_mensal_valor}}": "[CONS_FIXO_MENSAL_VALOR]",
    "{{consultiva.fixo_mensal_cap}}": "[CONS_FIXO_MENSAL_CAP]",
    "{{consultiva.fixo_mensal_excedente}}": "[CONS_FIXO_MENSAL_EXCEDENTE]",
    "{{consultiva.valor_projeto_total}}": "[CONS_PRECO_GLOBAL]",
    "{{consultiva.valor_projeto_cap}}": "[CONS_PRECO_GLOBAL_CAP]",
    "{{consultiva.valor_projeto_forma_pagamento}}": "[CONS_PRECO_GLOBAL_PAGAMENTO]",

    "{{contenciosa.preco_mensal_valor}}": "[CONT_PRECO_MENSAL_VALOR]",
    "{{contenciosa.preco_mensal_maximo_acoes}}": "[CONT_PRECO_MENSAL_MAX]",
    "{{contenciosa.preco_mensal_maximo_acoes_extenso}}": "[CONT_PRECO_MENSAL_MAX_EXTENSO]",
    "{{contenciosa.preco_mensal_criterio_excedentes}}": "[CONT_PRECO_MENSAL_EXCEDENTES]",
    "{{contenciosa.valor_projeto_total}}": "[CONT_PRECO_GLOBAL]",
    "{{contenciosa.valor_projeto_fases_cobertas}}": "[CONT_PRECO_GLOBAL_FASES]",
    "{{contenciosa.valor_projeto_forma_pagamento}}": "[CONT_PRECO_GLOBAL_PAGAMENTO]",
    "{{contenciosa.exito_percentual}}": "[CONT_EXITO_PERCENTUAL]",
    "{{contenciosa.horas_extra_valor}}": "[CONT_HORAS_EXTRA_VALOR]",

    "{{despesas.taxa_manutencao_processual}}": "[DESPESAS_TAXA]",
    "{{disposicoes.descricao}}": "[DISPOSICOES_DESCRICAO]",

    # Variaveis de loop (validas apenas dentro do bloco PARA_CADA_X correspondente)
    "{{s.categoria}}": "[SENIORIDADE_CATEGORIA]",
    "{{s.valor}}": "[SENIORIDADE_VALOR]",
    "{{it.natureza}}": "[ACAO_NATUREZA]",
    "{{it.fase}}": "[ACAO_FASE]",
    "{{it.valor}}": "[VALOR_LINHA]",
    "{{it.ato}}": "[ATO_NOME]",
    "{{it.descricao}}": "[ATO_DESCRICAO]",
    "{{d.categoria}}": "[DESPESA_CATEGORIA]",
    "{{d.descricao}}": "[DESPESA_DESCRICAO]",
}

# Condicionais paragraph-level — {%p if %}...{%p endif %}
SE_BLOCO: dict[str, str] = {
    "{%p if contratante.pf %}": "[SE_PF]",
    "{%p if contratante.pj %}": "[SE_PJ]",
    "{%p if escopo.show_consultiva %}": "[SE_CONSULTIVA]",
    "{%p if escopo.show_contenciosa %}": "[SE_CONTENCIOSA]",
    "{%p if escopo.show_sla %}": "[SE_SLA]",
    "{%p if consultiva.show_hora_senioridade %}": "[SE_CONS_HORA_SENIORIDADE]",
    "{%p if consultiva.show_hora_fixa %}": "[SE_CONS_HORA_MEDIA]",
    "{%p if consultiva.show_fixo_mensal %}": "[SE_CONS_FIXO_MENSAL]",
    "{%p if consultiva.show_valor_projeto %}": "[SE_CONS_PRECO_GLOBAL]",
    "{%p if contenciosa.show_valor_acao %}": "[SE_CONT_VALOR_MENSAL_PROCESSO]",
    "{%p if contenciosa.show_valor_ato %}": "[SE_CONT_VALOR_ATO]",
    "{%p if contenciosa.show_preco_mensal %}": "[SE_CONT_PRECO_MENSAL]",
    "{%p if contenciosa.show_valor_projeto %}": "[SE_CONT_PRECO_GLOBAL]",
    "{%p if contenciosa.show_exito %}": "[SE_CONT_EXITO]",
    "{%p if contenciosa.show_extra_senioridade %}": "[SE_CONT_EXTRA_SENIORIDADE]",
    "{%p if contenciosa.show_extra_hora_fixa %}": "[SE_CONT_EXTRA_HORA_MEDIA]",
    "{%p if disposicoes.show %}": "[SE_DISPOSICOES]",
}
FIM_SE_BLOCO_TAG = "{%p endif %}"
FIM_SE_BLOCO_MARKER = "[FIM_SE]"

# Condicionais inline — {% if %}...{% endif %}  (raros, apenas tabela)
SE_INLINE: dict[str, str] = {
    "{% if contratante.pf %}": "[SE_PF_INLINE]",
    "{% if contratante.pj %}": "[SE_PJ_INLINE]",
}
FIM_SE_INLINE_TAG = "{% endif %}"
FIM_SE_INLINE_MARKER = "[FIM_SE_INLINE]"

# Condicionais row-level — {%tr if %}...{%tr endif %}  (remove linha inteira de tabela se falso)
SE_LINHA: dict[str, str] = {
    "{%tr if contratante.contatos_texto %}": "[SE_LINHA_CONTATOS]",
    "{%tr if despesas.show_taxa_manutencao %}": "[SE_LINHA_TAXA_MANUTENCAO]",
    "{%tr if consultiva.show_valor_projeto_cap %}": "[SE_LINHA_CONS_PRECO_GLOBAL_CAP]",
}
FIM_SE_LINHA_TAG = "{%tr endif %}"
FIM_SE_LINHA_MARKER = "[FIM_SE_LINHA]"

# Loops table-row-level — {%tr for %}...{%tr endfor %}
PARA_CADA: dict[str, str] = {
    "{%tr for s in consultiva.tabela_senioridade %}": "[PARA_CADA_SENIORIDADE]",
    "{%tr for s in contenciosa.horas_extra_senioridade %}": "[PARA_CADA_SENIORIDADE_CONT]",
    "{%tr for it in contenciosa.tabela_acoes %}": "[PARA_CADA_ACAO]",
    "{%tr for it in contenciosa.tabela_atos %}": "[PARA_CADA_ATO]",
    "{%tr for d in despesas.tabela_despesas %}": "[PARA_CADA_DESPESA]",
}
FIM_PARA_CADA_TAG = "{%tr endfor %}"
FIM_PARA_CADA_MARKER = "[FIM_PARA_CADA]"


def build_full_map() -> dict[str, str]:
    """Retorna mapa completo Jinja -> marker, ordenado por comprimento decrescente
    para evitar substring match (substitui as tags mais longas primeiro)."""
    full: dict[str, str] = {}
    full.update(SE_BLOCO)
    full.update(SE_INLINE)
    full.update(SE_LINHA)
    full.update(PARA_CADA)
    full.update(VARIAVEIS)
    full[FIM_SE_BLOCO_TAG] = FIM_SE_BLOCO_MARKER
    full[FIM_SE_INLINE_TAG] = FIM_SE_INLINE_MARKER
    full[FIM_SE_LINHA_TAG] = FIM_SE_LINHA_MARKER
    full[FIM_PARA_CADA_TAG] = FIM_PARA_CADA_MARKER
    return dict(sorted(full.items(), key=lambda kv: -len(kv[0])))
