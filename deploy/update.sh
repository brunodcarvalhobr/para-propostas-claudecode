#!/usr/bin/env bash
# Atualiza o app self-hosted e reinicia o servico.
# O servidor segue a branch producao-legaltech — promova o main para ela
# antes (ver deploy/README.md) e entao rode este script.
#
# Uso: sudo bash /var/www/legaltech.pmra.com.br/deploy/update.sh
set -euo pipefail

APP_DIR=/var/www/legaltech.pmra.com.br
BRANCH=producao-legaltech
SERVICE=pmra-propostas
RUN_USER=www-data

echo "==> git pull (${BRANCH})"
git -C "${APP_DIR}" fetch origin "${BRANCH}"
git -C "${APP_DIR}" reset --hard "origin/${BRANCH}"

echo "==> dependencias"
"${APP_DIR}/.venv/bin/pip" install --quiet -r "${APP_DIR}/requirements.txt"

echo "==> permissoes + restart"
chown -R "${RUN_USER}:${RUN_USER}" "${APP_DIR}"
systemctl restart "${SERVICE}"

sleep 3
if curl -fsS http://127.0.0.1:8501/_stcore/health >/dev/null; then
    VERSION=$(grep -oP 'APP_VERSION = "\K[^"]+' "${APP_DIR}/app.py" || true)
    echo "OK — app no ar (v${VERSION:-?})."
else
    echo "FALHOU — app nao respondeu ao health check. Veja: journalctl -u ${SERVICE} -n 50" >&2
    exit 1
fi
