# Registra nel journal il comando SSH dell'agente e la sua risposta, per lo schermo della Deck.
# Bash lo legge prima di eseguire `bash -c "<comando>"` perché sshd imposta BASH_ENV per l'utente agent
# (/etc/ssh/sshd_config.d/20-agentdeck-screen.conf).
#
# - Il comando va nel journal con l'identificatore agentdeck-cmd.
# - Stdout e stderr passano da tee: una copia arriva invariata a chi ha lanciato il comando, l'altra va nel
#   journal (agentdeck-out, agentdeck-err). Codice di uscita e dati restano identici.
# - Esclusi: trasferimenti di file (scp, sftp, rsync) e sessioni con terminale, dove tee cambierebbe il
#   comportamento dei programmi.
# - Se qui qualcosa fallisse, il comando parte comunque: niente "set -e", ogni passo ignora i propri errori.
#
# Installato in /usr/local/lib/agentdeck/ssh-log.sh da screen/install-screen.sh.
# Documentazione: docs/schermo.md

if [ -n "${BASH_EXECUTION_STRING-}" ] && [ -z "${AGENTDECK_LOGGED-}" ]; then
  export AGENTDECK_LOGGED=1
  logger --size 65536 -t agentdeck-cmd -- "$BASH_EXECUTION_STRING" 2>/dev/null || true
  case "$BASH_EXECUTION_STRING" in
    /usr/lib/ssh/sftp-server*|scp\ *|rsync\ --server*|internal-sftp*) ;;
    *)
      if [ ! -t 1 ] && [ ! -t 2 ] && command -v tee >/dev/null 2>&1 && command -v logger >/dev/null 2>&1; then
        exec > >(tee >(logger --size 65536 -t agentdeck-out 2>/dev/null)) \
             2> >(tee >(logger --size 65536 -t agentdeck-err 2>/dev/null) >&2)
      fi
      ;;
  esac
fi
unset BASH_ENV
