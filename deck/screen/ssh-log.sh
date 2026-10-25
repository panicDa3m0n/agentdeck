# Registra nel journal il comando SSH dell'agente, per lo schermo della Deck (agentdeck-screen).
# Bash lo legge prima di eseguire `bash -c "<comando>"` perché sshd imposta BASH_ENV per l'utente agent
# (/etc/ssh/sshd_config.d/20-agentdeck-screen.conf). Se qui qualcosa fallisse, il comando parte comunque:
# per questo non c'è "set -e" e ogni passo ignora i propri errori.
# Installato in /usr/local/lib/agentdeck/ssh-log.sh da screen/install-screen.sh.
# Documentazione: docs/schermo.md

if [ -n "${BASH_EXECUTION_STRING-}" ] && [ -z "${AGENTDECK_LOGGED-}" ]; then
  export AGENTDECK_LOGGED=1
  logger -t agentdeck-cmd -- "$BASH_EXECUTION_STRING" 2>/dev/null || true
fi
unset BASH_ENV
