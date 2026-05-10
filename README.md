# PMRA — Gerador de Propostas (Streamlit)

App web para geração de propostas comerciais de prestação de serviços jurídicos
da PMRA (Porto, Miranda, Rocha Advogados) a partir de um formulário adaptativo.
O usuário preenche dados do contratante e da contratação; o app produz um
`.docx` final pronto para envio.

Esta é a versão Python/Streamlit. Existe também uma versão desktop (Electron)
no repositório irmão.

## Stack

- **Streamlit** — UI e estado de formulário
- **Pydantic v2** — validação dos dados
- **docxtpl** — template Word com Jinja2 (`{%p if %}`, `{%tr for %}`, `{{var}}`)
- **pandas** — back-end para `st.data_editor` (tabelas dinâmicas)

## Estrutura

```
.
├── app.py                          # Entry point Streamlit
├── pmra/                           # Lógica de domínio
│   ├── auth.py                     # Gate de senha via st.secrets
│   ├── data_mapper.py              # form -> contexto do template
│   ├── defaults.py                 # Valores pré-preenchidos (tabela senioridade etc.)
│   ├── schema.py                   # Modelos Pydantic
│   └── template_engine.py          # Renderização docxtpl + pós-processamento de \n
├── scripts/
│   └── build_template.py           # Gera PMRA_Template_Jinja.docx do original
├── resources/
│   └── templates/
│       ├── PMRA_Escopo_Misto.docx       # Template canônico — NUNCA editar
│       └── PMRA_Template_Jinja.docx     # Runtime, gerado pelo script
├── requirements.txt
├── runtime.txt                     # Python 3.11 (Streamlit Cloud)
└── .streamlit/
    ├── config.toml                 # Tema
    └── secrets.toml.example        # Template para senha (NÃO commitar o real)
```

## Setup local

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 1. Gerar o template Jinja2 (uma vez, ou sempre que o original mudar)
python scripts/build_template.py

# 2. (Opcional) Configurar senha
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edite .streamlit/secrets.toml e defina APP_PASSWORD

# 3. Rodar o app
streamlit run app.py
```

Sem `APP_PASSWORD` configurado, o app abre sem gate de senha.

## Deploy no Streamlit Community Cloud

1. Suba este repositório para o GitHub (público ou privado).
2. Acesse [share.streamlit.io](https://share.streamlit.io) e conecte sua conta GitHub.
3. **New app** → escolha o repositório, branch `main`, arquivo `app.py`.
4. Em **Advanced settings** → **Secrets**, cole:
   ```toml
   APP_PASSWORD = "troque-esta-senha"
   ```
5. Deploy. O Streamlit instala `requirements.txt` e roda `app.py`.

O template `PMRA_Template_Jinja.docx` precisa estar **commitado** no repositório,
porque o build no Cloud não roda `scripts/build_template.py` automaticamente.
Sempre que alterar `PMRA_Escopo_Misto.docx` (com aprovação dos sócios), regere
localmente e faça commit do `PMRA_Template_Jinja.docx` atualizado.

## Mapa de regras do template

| Decisão | Comportamento no .docx |
|---|---|
| Pessoa Física | Mostra "Nome" + "CPF"; oculta "Razão Social" + "CNPJ" |
| Pessoa Jurídica | Mostra "Razão Social" + "CNPJ"; oculta "Nome" + "CPF" |
| Modalidade = Consultiva | Remove integralmente a Seção 4 (Contenciosa) |
| Modalidade = Contenciosa | Remove integralmente a Seção 3 (Consultiva) |
| Modalidade = Mista | Mantém ambas |
| SLA = NÃO | Remove subseção SLA |
| Honorários Êxito = NÃO | Remove subseção Êxito |
| Disposições Específicas = NÃO | Remove integralmente a Seção 6 |
| Modalidade de honorários (multi-select) | Mostra apenas blocos selecionados |
| Horas Extra Escopo = "Tabela Senioridade" / "Hora Fixa" | Mostra apenas a opção escolhida |
| Tabelas dinâmicas (Ações, Atos, Senioridade) | Linhas via `{%tr for it in items %}` |
| Múltiplos contatos | Concatenados em "Telefone: X; E-mail: Y" |
| Endereço | Concatenado em "Logradouro N°, Bairro, CEP, Cidade/UF" |

## O que NÃO mudar

- `resources/templates/PMRA_Escopo_Misto.docx` é a referência canônica do
  escritório. **Nunca editar** este arquivo. Para ajustar o conteúdo do .docx
  final, modifique `scripts/build_template.py` ou `pmra/data_mapper.py`.
- Cláusulas dos Termos e Condições são texto jurídico revisado pelos sócios.
  **Nunca alterar** sem solicitação explícita.
- Valores pré-preenchidos da tabela de senioridade refletem a política
  comercial vigente. Estão em `pmra/defaults.py`.

## Como adicionar um novo campo

1. Estender o schema em `pmra/schema.py`.
2. Adicionar default em `pmra/defaults.py` se aplicável.
3. Renderizar o campo na seção apropriada de `app.py`.
4. Mapear o valor → contexto em `pmra/data_mapper.py`.
5. Adicionar a tag `{{...}}` no `PMRA_Template_Jinja.docx` (via edição
   manual do .docx OU acrescentando lógica em `scripts/build_template.py` e
   regerando).
6. Testar geração com cenário cobrindo o novo campo preenchido e vazio.
