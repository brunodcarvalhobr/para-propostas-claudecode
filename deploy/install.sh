#!/usr/bin/env bash
# Instalacao inicial do gerador de propostas PMRA em hospedagem propria.
# Alvo fixo: /var/www/legaltech.pmra.com.br
#
# Uso (como root ou com sudo):
#   sudo bash deploy/install.sh
#
# O script e idempotente: pode ser re-executado com seguranca.
# NAO mexe no deploy do Streamlit Cloud — os dois ambientes convivem:
#   Streamlit Cloud  -> branch main (redeploy automatico)
#   Dominio proprio  -> branch producao-legaltech (este script/update.sh)
set -euo pipefail

APP_DIR=/var/www/legaltech.pmra.com.br
REPO_URL=https://github.com/brunodcarvalhobr/para-propostas-claudecode.git
BRANCH=producao-legaltech   # canal do dominio proprio (Streamlit Cloud usa main)
SERVICE=pmra-propostas
RUN_USER=www-data

echo "==> 1/6 Dependencias do sistema (python3.11, git, apache2)"
if ! command -v python3.11 >/dev/null 2>&1; then
    apt-get update -qq
    # Ubuntu 22.04 ja traz python3.11 nos repositorios padrao (23.10+ = python3.11/3.12).
    apt-get install -y -qq python3.11 python3.11-venv || {
        echo "python3.11 indisponivel nos repositorios. Instale-o (ex.: PPA deadsnakes) e re-execute." >&2
        exit 1
    }
fi
apt-get install -y -qq git apache2

echo "==> 2/6 Codigo em ${APP_DIR} (branch ${BRANCH})"
if [ -d "${APP_DIR}/.git" ]; then
    git -C "${APP_DIR}" fetch origin "${BRANCH}"
    git -C "${APP_DIR}" checkout -B "${BRANCH}" "origin/${BRANCH}"
else
    mkdir -p "${APP_DIR}"
    git clone --branch "${BRANCH}" "${REPO_URL}" "${APP_DIR}"
fi

echo "==> 3/6 Virtualenv + dependencias Python"
if [ ! -x "${APP_DIR}/.venv/bin/python" ]; then
    python3.11 -m venv "${APP_DIR}/.venv"
fi
"${APP_DIR}/.venv/bin/pip" install --quiet --upgrade pip
"${APP_DIR}/.venv/bin/pip" install --quiet -r "${APP_DIR}/requirements.txt"

echo "==> 4/6 Senha do app (.streamlit/secrets.toml)"
SECRETS="${APP_DIR}/.streamlit/secrets.toml"
if [ ! -f "${SECRETS}" ]; then
    cat > "${SECRETS}" <<'EOF'
# Senha de acesso ao gerador (mesma logica do Streamlit Cloud -> Secrets).
# TROQUE o valor abaixo antes de liberar o site.
APP_PASSWORD = "TROCAR-ESTA-SENHA"
EOF
    chmod 600 "${SECRETS}"
    echo "    Criado ${SECRETS} — EDITE e defina APP_PASSWORD."
else
    echo "    ${SECRETS} ja existe — mantido."
fi

echo "==> 5/6 Permissoes + servico systemd"
chown -R "${RUN_USER}:${RUN_USER}" "${APP_DIR}"
cp "${APP_DIR}/deploy/${SERVICE}.service" "/etc/systemd/system/${SERVICE}.service"
systemctl daemon-reload
systemctl enable --now "${SERVICE}"

echo "==> 6/6 apache (modulos de proxy/websocket)"
a2enmod -q proxy proxy_http proxy_wstunnel headers ssl rewrite
cp "${APP_DIR}/deploy/legaltech.pmra.com.br.apache.conf" /etc/apache2/sites-available/legaltech.pmra.com.br.conf

# O vhost NAO e ativado automaticamente: o dominio ja tem um VirtualHost 443 em
# uso (o que hoje devolve 403) e este servidor pode hospedar outros sites. Ativar
# um vhost com certificado inexistente quebraria o proximo reload do Apache
# INTEIRO. A ativacao e manual e guiada — ver deploy/README.md, passo 2.
cat <<EOF

    VHOST NAO ATIVADO (proposital). Para concluir:
      1. sudo apache2ctl -S                  # ache o vhost atual do dominio
      2. copie as linhas SSLCertificateFile/SSLCertificateKeyFile dele para
         /etc/apache2/sites-available/legaltech.pmra.com.br.conf
      3. sudo a2dissite <vhost-antigo> && sudo a2ensite legaltech.pmra.com.br
      4. sudo apache2ctl configtest && sudo systemctl reload apache2
    Detalhes: ${APP_DIR}/deploy/README.md
EOF

echo
echo "Instalacao concluida."
echo "  - Saude do app:   curl -fsS http://127.0.0.1:8501/_stcore/health   (esperado: ok)"
echo "  - Logs:           journalctl -u ${SERVICE} -f"
echo "  - Senha:          edite ${SECRETS} e rode: sudo systemctl restart ${SERVICE}"
echo "  - Vhost:          confira certificados/vhost antigo — deploy/README.md, secao Apache"
