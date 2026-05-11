# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
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
