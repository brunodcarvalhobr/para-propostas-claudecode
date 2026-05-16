# DocGen by PMRA Legal Tech (Streamlit)

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
│   └── smoke_test.py               # End-to-end: 3 cenários -> out/*.docx
├── tests/                          # Suíte pytest (data_mapper, schema)
├── resources/
│   ├── static/styles.css           # CSS extraído do app.py
│   └── templates/
│       └── PMRA_Template_Jinja.docx     # Template Word com tags Jinja — editar direto
├── .github/workflows/ci.yml        # CI: pytest + smoke test em PR
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

# 1. (Opcional) Configurar senha
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edite .streamlit/secrets.toml e defina APP_PASSWORD

# 2. Rodar o app
streamlit run app.py
```

Sem `APP_PASSWORD` configurado, o app abre sem gate de senha.

## Testes

```bash
pip install pytest
pytest tests/                 # unitários (data_mapper, schema)
python scripts/smoke_test.py  # end-to-end: gera 3 .docx em out/
```

CI roda os dois em todo PR (`.github/workflows/ci.yml`).

## Deploy no Streamlit Community Cloud

1. Suba este repositório para o GitHub (público ou privado).
2. Acesse [share.streamlit.io](https://share.streamlit.io) e conecte sua conta GitHub.
3. **New app** → escolha o repositório, branch `main`, arquivo `app.py`.
4. Em **Advanced settings** → **Secrets**, cole:
   ```toml
   APP_PASSWORD = "troque-esta-senha"
   ```
5. Deploy. O Streamlit instala `requirements.txt` e roda `app.py`.

O template `PMRA_Template_Jinja.docx` precisa estar **commitado** no repositório.
Sempre que alterar o template (com aprovação dos sócios), rode o smoke test
localmente antes de commitar.

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

## Como editar o template (PMRA_Template_Jinja.docx)

O `.docx` é mantido **direto** com as tags Jinja2 dentro do arquivo Word.
Não há mais build step.

**O que NÃO mexer dentro do .docx:**

- `{{ var.path }}` — interpolação simples
- `{%p if cond %}…{%p endif %}` — bloco condicional ao nível de parágrafo (remove o parágrafo inteiro)
- `{%tr for it in items %}…{%tr endfor %}` — loop ao nível de linha de tabela (remove a linha inteira)

**Armadilhas do Word a evitar:**

- Não clique no meio de `{{…}}` ou `{%…%}` para editar — Word pode fragmentar
  a tag em múltiplos runs e quebrar a renderização silenciosamente.
- Não use Localizar/Substituir cruzando fronteira de tag.
- Não cole texto formatado de fora do Word; use colar-sem-formatação
  (`Ctrl+Shift+V`).
- Não selecione texto que cruze a tag para reformatar (cor, fonte, etc.).

**Workflow:**

```bash
# 1. edite resources/templates/PMRA_Template_Jinja.docx no Word
# 2. valide:
python scripts/smoke_test.py
# 3. abra os 3 .docx em out/ e confira visualmente
# 4. commit + push
```

O smoke test detecta tags Jinja não processadas (fragmentação por Word),
mas **não** detecta layout quebrado — sempre faça a conferência visual.

## O que NÃO mudar (sem aprovação dos sócios)

- Cláusulas dos Termos e Condições são texto jurídico revisado.
- Valores pré-preenchidos da tabela de senioridade refletem a política
  comercial vigente. Estão em `pmra/defaults.py`.

## Como adicionar um novo campo

1. Estender o schema em `pmra/schema.py`.
2. Adicionar default em `pmra/defaults.py` se aplicável.
3. Renderizar o campo na seção apropriada de `app.py`.
4. Mapear o valor → contexto em `pmra/data_mapper.py`.
5. Adicionar a tag `{{...}}` em `PMRA_Template_Jinja.docx` (edição manual no Word).
6. Adicionar caso ao smoke test (`scripts/smoke_test.py`) com o campo preenchido e vazio.
