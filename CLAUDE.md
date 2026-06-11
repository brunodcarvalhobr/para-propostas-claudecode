# CLAUDE.md — Regras e diretrizes do projeto

> Lido automaticamente pelo Claude Code a cada sessão.  
> Para outros agentes: OpenAI Codex lê `AGENTS.md` (mantido em sincronia com este arquivo).

---

## 1. Regra obrigatória: versionamento

**A cada commit em `main`, incremente `APP_VERSION` em `app.py` (linha ~27).**

- Formato: `MAJOR.MINOR.PATCH` — ex.: `2.0.29`
- A versão aparece no rodapé: `PMRA · v{APP_VERSION}`

### Qual dígito incrementar?

| Dígito | Regra |
|---|---|
| **PATCH** `2.0.X` | Todo commit do dia a dia — correções, textos, estilos, ajustes |
| **MINOR** `2.X.0` | Decisão do dono do projeto. Exemplos: nova seção no documento, nova modalidade de escopo, nova forma de honorários |
| **MAJOR** `X.0.0` | Decisão do dono do projeto. Reservar para viradas grandes: reformulação do formulário, troca de stack, mudança incompatível |

MINOR e MAJOR não têm critério automático — são chamadas deliberadas do dono do projeto, não do agente. Ao subir MINOR ou MAJOR, resetar os dígitos à direita para zero (ex: `2.0.99` → `2.1.0`).

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

A regra é definida pelo arquivo tocado — sem julgamento subjetivo:

| Arquivos alterados | Fluxo |
|---|---|
| `pmra/schema.py`, `pmra/data_mapper.py`, `pmra/template_engine.py`, `resources/templates/*.docx` | Branch → PR → squash merge em `main` |
| Qualquer outro arquivo | Commit direto em `main` |

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

Além disso, `_ensure_do_not_expand_shift_return` injeta a flag de compatibilidade
`doNotExpandShiftReturn` em `word/settings.xml`: todo texto livre do formulário sai
**justificado** (inclusive multilinha/Enter) sem o Word esticar a linha que termina
em quebra manual. Não reintroduzir o antigo `_left_align_multiline` (removia a
justificação de parágrafos com `<w:br/>` — substituído pela flag).

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

---

## 11. Regras de ouro para operações git — lição aprendida em produção

> Estas regras existem porque um agente causou regressão em produção ao executar operações git desnecessariamente destrutivas. Nunca repita.

### Nunca use `git filter-repo` sem autorização explícita do dono do projeto

`git filter-repo` reescreve **todo o histórico** do repositório, muda todos os hashes e força um `push --force` que quebra deploys ativos (Streamlit Cloud, CI, branches abertos). Para remover dados sensíveis de um arquivo de exemplo, basta um **commit normal** corrigindo o conteúdo — não é necessário reescrever história.

### Nunca faça `git push --force` em `main` sem autorização explícita

Force push em `main` substitui o histórico remoto. O Streamlit Cloud redetecta a branch como modificada e pode redeployar do commit errado ou falhar silenciosamente, causando regressão em produção.

### Antes de aplicar código de um branch em outro, confirme que são o mesmo codebase

Este repositório já teve dois codebases distintos no mesmo remote (histórias sem ancestral comum). Aplicar `auth.py` de um codebase em outro sem verificar compatibilidade quebra o app. Sempre confirme com `git merge-base` e inspecione os arquivos críticos antes de qualquer operação cross-branch.

### Para remover dado sensível de arquivo rastreado

O procedimento correto é, **nesta ordem**:
1. Corrigir o arquivo (trocar valor real por placeholder)
2. Commitar normalmente
3. Trocar a credencial exposta no serviço (Streamlit Cloud Secrets, etc.)

Reescrever histórico só se justifica se o dado estiver em um repositório **privado** e o dono autorizar explicitamente — e mesmo assim, depois de confirmar que nenhum deploy ativo será afetado.

---

## 12. Persistência de estado entre etapas — regra de ouro do Streamlit

> Lição recorrente (já aconteceu mais de uma vez): campos preenchidos sumiam ao avançar e voltar entre as etapas do formulário. Esta seção existe para não repetir.

**Sintoma:** o usuário digita um campo, clica "Próximo" (ou pula pelo stepper) e, ao voltar, o campo está vazio.

**Causa:** o Streamlit descarta o estado de widgets que **não são renderizados** no rerun atual. Ao clicar num botão de navegação, o callback troca de etapa e o corpo da etapa anterior não re-renderiza — então o último valor digitado nem é copiado para `st.session_state.form`, e a chave do widget é coletada (GC).

**Duas defesas em `app.py` — NÃO remover:**

1. **Reatribuir as chaves a si mesmas a cada rerun**, logo após `_init_state()` e ANTES de qualquer widget ser instanciado:
   ```python
   for _k in list(st.session_state.keys()):
       if _is_acao_key(_k):   # botões NÃO podem ser reatribuídos
           continue
       st.session_state[_k] = st.session_state[_k]
   ```
   Isso "promove" as chaves de widget a estado do usuário e impede o descarte.

2. **`_apply_formats` lê a CHAVE do widget, não o `form`** (que está defasado ao sair da etapa no mesmo rerun do clique). Vale para qualquer sincronização feita em callback de navegação.

**REGRA ao criar um BOTÃO novo:** a `key=` precisa casar com um padrão de `_is_acao_key` (`step_btn_`, `nav_`, `reset_`, `fix_step_`, contém `__del__`, termina em `__add`, ou `escopo_cons_`/`escopo_cont_` que não seja `_desc_`). O Streamlit **proíbe** escrever o estado de `st.button`/`download_button` via `session_state` (`StreamlitValueAssignmentNotAllowedError`); se o novo botão não casar com um padrão, adicione-o em `_is_acao_key`, senão a reatribuição quebra o app.

**Regressão:** travada em `tests/test_app_persistence.py` (AppTest, roda no CI). Ao mexer em navegação ou estado de widgets, rode `pytest tests/test_app_persistence.py`.
