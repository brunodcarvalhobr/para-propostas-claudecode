# CLAUDE.md — Instruções para o agente neste repositório

## Regra obrigatória: versionamento

**A cada PR mergeado, incremente `APP_VERSION` em `app.py` (linha ~27).**

- O formato é `MAJOR.MINOR.PATCH` (ex.: `2.0.26`).
- Incremente o PATCH em +1 por PR de correção ou ajuste.
- A versão aparece no rodapé do app: `PMRA · v{APP_VERSION}`.
- Nunca mergear sem atualizar a versão. Inclua o bump no mesmo PR das alterações ou em PR imediato a seguir.

---

## Visão geral do projeto

Gerador de propostas jurídicas da PMRA Legal Tech, construído em **Streamlit + Python**.  
Formulário em etapas → gera `.docx` via `python-docx` + `docxcompose`.

### Estrutura principal

| Caminho | Responsabilidade |
|---|---|
| `app.py` | UI Streamlit (formulário em etapas, navegação, renderização) |
| `pmra/schema.py` | Modelos Pydantic (validação do formulário) |
| `pmra/defaults.py` | Valores padrão do formulário ao abrir o gerador |
| `pmra/data_mapper.py` | Converte `ProposalForm` → contexto de template |
| `pmra/template_engine.py` | Renderiza o `.docx` a partir do contexto |
| `resources/static/styles.css` | Estilos do app (não inline em `app.py`) |
| `tests/` | Suíte pytest (data_mapper, schema) |

### Modalidades de escopo

- `consultiva` — exibe apenas campos consultivos
- `contenciosa` — exibe apenas campos contenciosos
- `mista` — exibe ambos os blocos

O padrão ao abrir o gerador é `"consultiva"` (definido em `pmra/defaults.py`).

### Fluxo de deploy

Branch de feature → PR → squash merge em `main` → Streamlit Cloud detecta push e faz redeploy automático.
