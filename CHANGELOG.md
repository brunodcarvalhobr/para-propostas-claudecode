# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- **Múltiplos escopos por modalidade** (consultivo A/B/C…, contencioso A/B/C…) com forma de pagamento opcionalmente independente por escopo. Cada bloco de honorários é construído via Subdoc com todas as tabelas estilizadas do template original. Schema retrocompatível: lista de escopos vazia → caminho legado (1 escopo único por modalidade).
- **Títulos sublinhados** "Honorários Propostos para os Escopos Consultivos/Contenciosos" nos blocos multi.
- **Título SLA dinâmico** (`{{escopo.sla_titulo}}`) com versão singular/plural conforme número de escopos.
- **`scripts/generate_demo.py`** (multi) e **`scripts/generate_demo_simples.py`** (legado): geram demos completos para conferência visual. Saídas em `Proposta_*.docx` (gitignored).

### Changed
- `requirements.txt`: `setuptools<81` adicionado para preservar `pkg_resources` no Python 3.14 (Streamlit Cloud) — `docxcompose==1.4.0` ainda depende do módulo em runtime.
- Parágrafo em branco inserido entre título e conteúdo em "SLA/Prazos de Entrega" e "Condições Específicas".
- Nota azul do SLA estendida para orientar uso em múltiplos escopos com prazos distintos.

### Removed
- `Proposta_Teste_Simples.docx`, `Proposta_Demo_*.docx` (geráveis via scripts; agora gitignored).
- `scripts/demo_mista_completa.py` (substituído por `generate_demo.py` + `generate_demo_simples.py`).

### Fixed
- **Texto do formulário sai justificado no `.docx` — apenas quando é texto corrido.** Vários parágrafos de texto livre (Escopo Consultivo, Escopo Contencioso, SLA, Disposições, critério de excedentes, fases cobertas, forma de pagamento, endereço e contatos) não tinham `<w:jc>` no template e herdavam alinhamento à esquerda. `template_engine._justify_form_paragraphs` força `w:jc=both` nesses parágrafos antes do render. Como justificar texto com quebra manual (Enter → `<w:br/>`) faz o Word esticar a linha antes da quebra, `_left_align_multiline` remove a justificação de parágrafos que contenham `<w:br/>` — assim texto corrido fica justificado e texto com Enter (SLA em lista, contatos, itens) volta a alinhar à esquerda. Coberto por `tests/test_template_engine.py`.
- **Atos Processuais pré-preenchidos voltam a aparecer.** `_init_state` semeava `tbl_acoes`/`tbl_atos`, mas o render do modo único lê `tbl_acoes_cont`/`tbl_atos_cont` (prefixo `cont`) — chaves órfãs faziam os 8 atos padrão sumirem (1 linha vazia). Chaves do seed alinhadas ao prefixo.
- **Última edição preservada ao criar o 2º escopo.** `_to_multi_cons_cb`/`_to_multi_cont_cb` liam o dict (defasado 1 ciclo no `on_click`); passam a ler a chave do widget (`atuacao_*_ta`), evitando perder o texto recém-digitado.
- **`exito_percentual` robusto a valores com `%`.** O `int()` agora opera sobre o valor já sem `%`/espaços, evitando `ValueError` com dados legados/importados.
- **`scripts/generate_minuta_completa.py`** (QA): gera duas minutas de cobertura máxima (escopo único PJ e multi-escopo PF, todas as modalidades) e valida integridade do `.docx` (zip, sem tags Jinja residuais, abre no python-docx, paraIds únicos).

---

## [Histórico]

### Added
- **Suíte de testes pytest** em `tests/` (data_mapper, schema).
- **Smoke test com asserções de conteúdo** (`scripts/smoke_test.py`) verificando que dados específicos aparecem no `.docx` renderizado.
- **CI** em `.github/workflows/ci.yml` rodando pytest + smoke test em PR.
- **`resources/static/styles.css`**: CSS extraído de `app.py` (340 linhas inline → arquivo dedicado).

### Changed
- Schema `Contratante` agora zera campos cruzados PF/PJ (CPF/CNPJ aceitam qualquer string para permitir números temporários ou de teste).
- `requirements.txt` com pinning estrito (`pydantic==2.13.4`, `pandas==2.3.3`).
- `.streamlit/config.toml`: `enableXsrfProtection = true` (estava desativado).
- `.devcontainer/devcontainer.json`: removidos flags `--enableCORS false --enableXsrfProtection false`.
- `app.py`: traceback exposto trocado por `logger.exception` + mensagem amigável; interpolações HTML no review card escapadas com `html.escape`.

### Removed
- Injeção do MS Teams SDK no parent document (era código órfão — restaurar de forma controlada se for embedar em Teams).
- **`resources/templates/PMRA_Escopo_Misto.docx`** e **`scripts/build_template.py`** (872 linhas). Template é mantido direto em `PMRA_Template_Jinja.docx` com tags Jinja inline.

### Security
- Auto-XSS via campos do form no review card (`app.py:1232`) corrigido por escape.
- Proteção XSRF reativada em produção.

### Added (Design System Antigravity)
- **Design System Antigravity**: Implementação do design spec no front-end Streamlit.
- Configuração de tipografia (Fraunces e Inter) vindas do Google Fonts.
- Efeito *Glassmorphism* em painéis principais e formulários via `backdrop-filter`.
- Barra de progresso (stepper) estilizada com formato de pílula (`border-radius: 999px`).
- Background *Ambient* animado usando gradientes no corpo principal da aplicação.
- Componente novo de Footer elegante, assinado pela PMRA Legal Tech.

### Changed
- Configurações globais em `.streamlit/config.toml` atualizadas para usar as cores `ember` e `paper` do Spec.
- Cabeçalho (`pmra-header`) reconstruído e posicionado como `sticky` no topo da tela com efeito de vidro opaco.
- Botões primários (`button[kind="primary"]`) atualizados com sombra e efeitos gradientes nativos da Antigravity.
