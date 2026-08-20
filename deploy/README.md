# Hospedagem própria — legaltech.pmra.com.br

Guia de deploy do gerador de propostas em servidor próprio (**Debian + Apache 2.4**),
com o app instalado em **`/var/www/legaltech.pmra.com.br/`**.

## INSTRUÇÕES DE CLONE (para o dev) — leia primeiro

O repositório tem **dois canais**. Clonar a branch errada publica a versão errada.
Para o domínio próprio, use **sempre** `producao-legaltech`:

```bash
# 1. Diretório destino (exatamente este caminho)
sudo mkdir -p /var/www/legaltech.pmra.com.br

# 2. Clone da branch do domínio próprio (NÃO use main aqui)
sudo git clone --branch producao-legaltech \
  https://github.com/brunodcarvalhobr/para-propostas-claudecode.git \
  /var/www/legaltech.pmra.com.br

# 3. Confirme que veio a branch certa (deve imprimir: producao-legaltech)
git -C /var/www/legaltech.pmra.com.br rev-parse --abbrev-ref HEAD

# 4. Rode o instalador (venv, deps, systemd, módulos do Apache)
sudo bash /var/www/legaltech.pmra.com.br/deploy/install.sh
```

Se o diretório já existir com um clone antigo, **não** apague: rode só o passo 4
(o `install.sh` é idempotente e faz o `fetch`/`checkout` da branch correta).

Regras:

- **Não clonar `main`** em `/var/www/legaltech.pmra.com.br` — `main` é o canal do
  Streamlit Cloud e pode estar à frente do que foi homologado para o domínio.
- **Não editar arquivos direto no servidor.** Toda mudança entra por git; o
  servidor só recebe via `update.sh`. Exceção única: `.streamlit/secrets.toml`
  (senha), que é local e não versionado.
- **O clone é público** (repo acessível por HTTPS), não precisa de chave de deploy.
  Se o repositório for fechado depois, gere uma *deploy key* de leitura e troque a
  URL para SSH (`git@github.com:...`).

## Dois canais de deploy — qual branch clonar onde

| Ambiente | Branch | Como recebe código | Clone |
|---|---|---|---|
| **Streamlit Cloud** (link atual) | `main` | Automático a cada push em `main` | Nenhum — o próprio Streamlit Cloud puxa o repo |
| **Domínio próprio** (`https://legaltech.pmra.com.br`) | `producao-legaltech` | Espelhada automaticamente de `main` quando o CI passa; o servidor puxa com `update.sh` | `git clone --branch producao-legaltech https://github.com/brunodcarvalhobr/para-propostas-claudecode.git /var/www/legaltech.pmra.com.br` |

**Sincronização automática das branches.** O workflow
`.github/workflows/sync-producao.yml` espelha `main` → `producao-legaltech` a cada
push em `main`, mas **só depois que o CI passa** — assim o canal do domínio próprio
nunca fica apontando para um commit que quebrou testes ou smoke test. O push é feito
com o `GITHUB_TOKEN`, que não dispara novos workflows (sem risco de loop).

Também dá para sincronizar manualmente: aba **Actions → Sync producao-legaltech →
Run workflow**.

**O servidor não se atualiza sozinho.** A branch fica pronta, mas o código só chega
ao ar quando alguém roda, no servidor:

```bash
sudo bash /var/www/legaltech.pmra.com.br/deploy/update.sh
```

Esse é o ponto de controle: o Streamlit Cloud redeploya na hora, enquanto o domínio
próprio só muda quando você mandar.

> **Se o sync falhar**, é porque alguém commitou direto na `producao-legaltech` e as
> branches divergiram. O workflow falha de propósito, em vez de descartar o commit
> em silêncio. Para resolver, decida o que fazer com o commit exclusivo do canal e
> depois force o alinhamento:
> `git push origin origin/main:producao-legaltech --force-with-lease`

(Alternativa pela interface do GitHub: abrir PR `main` → `producao-legaltech` e mergear.)

## Arquitetura no servidor

```
Internet ──► Apache 2.4 (443, TLS já existente no domínio)
                 │  ProxyPass + upgrade=websocket (obrigatório p/ Streamlit)
                 ▼
         127.0.0.1:8501  ── streamlit run app.py (systemd: pmra-propostas)
                 │
         /var/www/legaltech.pmra.com.br/   (branch producao-legaltech + .venv + secrets)
```

| Arquivo | Papel |
|---|---|
| `install.sh` | Instalação inicial completa (idempotente) |
| `update.sh` | Atualização: pull da `producao-legaltech` + deps + restart + health check |
| `pmra-propostas.service` | Unit systemd (roda como `www-data`, escuta só em loopback) |
| `legaltech.pmra.com.br.apache.conf` | VirtualHost Apache com proxy + WebSocket |

## Passo a passo

1. **Instalação** (como root — o clone é feito pelo próprio script):
   ```bash
   curl -fsSL https://raw.githubusercontent.com/brunodcarvalhobr/para-propostas-claudecode/producao-legaltech/deploy/install.sh -o /tmp/install-pmra.sh
   sudo bash /tmp/install-pmra.sh
   ```
   (Ou clone manualmente com o comando da tabela acima e rode `sudo bash deploy/install.sh`.)

2. **Vhost/TLS — o domínio já responde 403 na 443.** Existe um VirtualHost ativo
   servindo o docroot vazio. Resolva assim:
   ```bash
   sudo apache2ctl -S           # localiza o vhost atual de legaltech.pmra.com.br
   ```
   - Copie as linhas `SSLCertificateFile`/`SSLCertificateKeyFile` do vhost atual para
     `/etc/apache2/sites-available/legaltech.pmra.com.br.conf` (o novo, com proxy);
   - Desative o antigo: `sudo a2dissite <nome-do-vhost-antigo>`;
   - `sudo apache2ctl configtest && sudo systemctl reload apache2`.

   Se preferir, em vez de trocar o vhost, cole o bloco `PROXY` do arquivo novo dentro
   do vhost 443 existente (mantendo os certificados como estão).

3. **Senha do app** — edite `/var/www/legaltech.pmra.com.br/.streamlit/secrets.toml`
   (mesmo formato do Secrets do Streamlit Cloud) e reinicie:
   ```toml
   APP_PASSWORD = "senha-forte-aqui"
   ```
   ```bash
   sudo systemctl restart pmra-propostas
   ```

4. **Conferência**:
   ```bash
   curl -fsS http://127.0.0.1:8501/_stcore/health   # -> ok
   systemctl status pmra-propostas                  # -> active (running)
   ```
   Abra `https://legaltech.pmra.com.br` — deve exibir a tela de senha e o rodapé
   `PMRA · v<APP_VERSION>`.

## Operação

| Ação | Comando |
|---|---|
| Publicar no domínio próprio a versão já sincronizada | `sudo bash /var/www/legaltech.pmra.com.br/deploy/update.sh` |
| Forçar o sync das branches fora do CI | Actions → **Sync producao-legaltech** → Run workflow |
| Logs ao vivo | `journalctl -u pmra-propostas -f` |
| Reiniciar | `sudo systemctl restart pmra-propostas` |
| Health check (monitoramento) | `GET https://legaltech.pmra.com.br/_stcore/health` → `ok` |

## Notas

- **WebSocket é obrigatório**: sem `upgrade=websocket` no `ProxyPass` (módulo
  `proxy_wstunnel`), o app carrega e congela em "Please wait…". Já está no vhost
  fornecido; o `install.sh` habilita os módulos.
- **`enableXsrfProtection = true`** (`.streamlit/config.toml`) permanece ligado e
  funciona atrás do proxy — não desligar (regra do projeto).
- O Streamlit escuta só em `127.0.0.1:8501`; a exposição pública é exclusiva do
  Apache. Não abra a porta 8501 no firewall.
- `runtime.txt` (python-3.11) é lido só pelo Streamlit Cloud; no servidor o Python
  3.11 é garantido pelo `install.sh` (venv em `.venv/`).
- Backup: o único estado local do servidor é `.streamlit/secrets.toml` — todo o
  resto vem do git (branch `producao-legaltech`).
