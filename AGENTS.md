# AGENTS.md — Regras e diretrizes do projeto

> Lido automaticamente pelo OpenAI Codex a cada sessão.  
> Para outros agentes: Claude Code lê `CLAUDE.md` (mantido em sincronia com este arquivo).

---

## 1. Regra obrigatória: versionamento

**A cada PR mergeado, incremente `APP_VERSION` em `app.py` (linha ~27).**

- Formato: `MAJOR.MINOR.PATCH` — ex.: `2.0.26`
- Incremente o PATCH em +1 por PR de correção ou ajuste
- A versão aparece no rodapé: `PMRA · v{APP_VERSION}`
- Inclua o bump no mesmo PR das alterações — nunca mergear sem atualizar

---

## 2. Visão geral do projeto

Gerador de propostas jurídicas da **PMRA Legal Tech**, construído em Streamlit + Python.  
Formulário em etapas → valida com Pydantic → renderiza `.docx` via docxtpl (Jinja2) + docxcompose.

### Stack

| Camada | Tecnologia |
|---|---|
| UI | Streamlit 1.40.1 |
| Validação | Pydantic v2 |
| Template Word | docxtpl 0.19.0 (Jinja2) + docxcompose 1.4.0 |
| Tabelas dinâmicas | pandas (back-end do `st.data_editor`) |
| Python | 3.11 (runtime.txt) |
| CSS | Antigravity Design System (`resources/static/styles.css`) |

### Estrutura de arquivos

```
app.py                          # UI Streamlit — formulário em etapas, navegação
pmra/
  schema.py                     # Modelos Pydantic (validação)
  defaults.py                   # Valores padrão do formulário
  data_mapper.py                # ProposalForm → contexto Jinja2
  template_engine.py            # Renderiza .docx + pós-processamento XML
  auth.py                       # Password gate via st.secrets
resources/
  static/styles.css             # CSS (Antigravity) — não editar inline em app.py
  templates/PMRA_Template_Jinja.docx   # Template Word com tags Jinja2
tests/
  test_schema.py                # Validação cross-field, SLA, PF/PJ
  test_data_mapper.py           # Formatação monetária, endereço, contexto
scripts/
  smoke_test.py                 # Teste end-to-end com 3 cenários
  generate_demo.py              # Gera demo multi-escopo
  generate_demo_simples.py      # Gera demo legado (1 escopo)
  pre-commit                    # Hook: auto-incrementa versão (local)
.github/workflows/ci.yml        # CI: pytest + smoke_test em todo PR
.streamlit/config.toml          # Tema, toolbar minimal, XSRF, light mode
```

---

## 3. Regras de negócio — NÃO alterar sem aprovação explícita

### Tabela de senioridade (`pmra/defaults.py`)

```python
SENIORIDADE_DEFAULT = [
    ("Sócio",                  "R$ 1.050,00"),
    ("Associado Sênior",       "R$ 850,00"),
    ("Associado Pleno",        "R$ 650,00"),
    ("Associado Júnior",       "R$ 450,00"),
    ("Estagiário/Paralegal",   "R$ 250,00"),
]
```

**Refletem a política comercial vigente da PMRA. Alterar apenas com solicitação explícita da Diretoria.**

### Template Word (`resources/templates/PMRA_Template_Jinja.docx`)

- Contém texto jurídico e cláusulas dos Termos Gerais — **não alterar condições sem aprovação da Diretoria**
- Tags Jinja2 inseridas diretamente no Word; não há build step
- Nunca fragmentar uma tag no meio com Find/Replace ou formatação parcial
- Nunca cruzar fronteiras de tag em edições manuais

### Defaults de SLA (`pmra/defaults.py — SLA_DESCRICAO_DEFAULT`)

Prazos padrão pré-aprovados pela área. Alterar somente com alinhamento da equipe.

---

## 4. Modalidades de escopo

| Modalidade | Campos exibidos |
|---|---|
| `consultiva` | Apenas campos consultivos |
| `contenciosa` | Apenas campos contenciosos |
| `mista` | Ambos os blocos |

- **Padrão ao abrir o gerador:** `"consultiva"` (definido em `pmra/defaults.py`)
- SLA só aparece em `consultiva` e `mista` — validator no schema zera campos SLA se `contenciosa`
- Êxito só aparece em `contenciosa`
- Lógica de visibilidade: `if modal in ("consultiva", "mista"):` / `if modal in ("contenciosa", "mista"):`

---

## 5. Convenções de código

- **Sem comentários** salvo quando o *porquê* é não-óbvio (workaround, invariante oculta, constraint de negócio)
- snake_case em todo o Python (espelha camelCase do app Electron irmão)
- CSS sempre em `resources/static/styles.css` — nunca inline em `app.py`
- Widgets Streamlit com `key=` explícito; sincronização via `_init_state()` antes do render
- Nunca usar `st.set_page_config` fora do topo de `app.py` (Streamlit exige como primeiro comando)
- `_fmt_money` formata valores monetários: `"500"` → `"R$ 500,00"`; texto livre não é modificado

---

## 6. Testes — obrigatório passar antes de mergear

```bash
pytest tests/ -v
python scripts/smoke_test.py
```

O CI (`.github/workflows/ci.yml`) roda ambos em todo PR. Não mergear com CI vermelho.

### Cobertura mínima esperada

- `test_schema.py`: cross-field PF/PJ, SLA contenciosa zerando
- `test_data_mapper.py`: formatação monetária, endereço, contatos, flags de contexto
- `smoke_test.py`: 3 cenários end-to-end (PF consultiva, PJ mista completa, PJ contenciosa mínima)

---

## 7. Fluxo de deploy

- **Ajustes simples** (textos, estilos, correções pontuais): commit direto em `main`
- **Mudanças maiores** (nova funcionalidade, refactor, alteração de schema): branch → PR → squash merge em `main`
- Streamlit Cloud detecta push em `main` e faz redeploy automático

### Autenticação em produção

`APP_PASSWORD` configurado em **Streamlit Cloud → Settings → Secrets**:

```toml
APP_PASSWORD = "..."
```

Localmente: criar `.streamlit/secrets.toml` com o mesmo conteúdo (gitignored).

---

## 8. Design system — Antigravity

Nome interno do sistema de design visual do app. **Não é um editor de AI.**

- Glassmorphism: painéis com `backdrop-filter`, opacidade 55%
- Paleta: `--color-ember-*` (laranja), `--color-paper` (off-white), `--color-ink` (preto)
- Tipografia: Fraunces (display) + Inter (sans) via Google Fonts
- Ícones: Material Symbols Outlined
- Light mode forçado via JS em `app.py` + `config.toml` base=light + toolbar hidden

---

## 9. Pós-processamento do .docx

O `template_engine.py` aplica 5 transformações no XML após renderizar:

1. `_split_linebreaks` — converte `\n` em quebras de linha Word (`<w:br/>`)
2. `_collapse_empty_paragraphs` — normaliza parágrafos em branco consecutivos
3. `_remove_table_outer_bottom_borders` — remove borda inferior externa de tabelas
4. `_force_font_size_10` — normaliza todas as fontes para 10pt
5. `_dedupe_para_ids` — garante `w14:paraId` únicos (duplicatas corrompem o arquivo no Word)

---

## 10. O que NÃO fazer

- Não alterar valores de `SENIORIDADE_DEFAULT` sem aprovação da Diretoria
- Não editar cláusulas do template Word sem aprovação da Diretoria
- Não adicionar CSS inline em `app.py` (usar `styles.css`)
- Não commitar arquivos `.docx` gerados (gitignored)
- Não usar `git push --force` em `main`
- Não mergear sem bump de versão em `APP_VERSION`
- Não mergear com CI falhando
- Não remover `enableXsrfProtection = true` do `config.toml`
