# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- **Suíte de testes pytest** em `tests/` (validators, data_mapper, schema) — 50 testes.
- **Smoke test com asserções de conteúdo** (`scripts/smoke_test.py`) verificando que dados específicos aparecem no `.docx` renderizado.
- **CI** em `.github/workflows/ci.yml` rodando pytest + smoke test em PR.
- **`pmra/validators.py`**: validação de CPF/CNPJ por dígito verificador.
- **`resources/static/styles.css`**: CSS extraído de `app.py` (340 linhas inline → arquivo dedicado).

### Changed
- Schema `Contratante` agora valida CPF/CNPJ (dígito verificador) e zera campos cruzados PF/PJ.
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
