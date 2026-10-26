#!/bin/bash
# Lanciato da pacman (95-agentdeck-obligations.hook) dopo un'installazione, come root, con i nomi dei pacchetti su
# stdin: chiede a deck, come utente agent, gli obblighi per i programmi nuovi (deck obligations installed).
# Non fa mai fallire la transazione: ogni errore viene ignorato e l'uscita è sempre 0.
# Installato in /usr/local/lib/agentdeck/ (di root) da deck/install.sh.
# Documentazione: docs/obblighi.md
pkgs=$(tr '\n' ' ')
[ -n "${pkgs// /}" ] || exit 0
out=$(env -i HOME=/home/agent PATH=/usr/local/bin:/usr/bin LANG=C.UTF-8 \
      /usr/bin/runuser -u agent -- /usr/local/bin/deck obligations installed "packages=$pkgs" 2>/dev/null)
n=$(printf '%s' "$out" | /usr/bin/python3 -c 'import json, sys; print(len(json.load(sys.stdin)["data"]["created"]))' \
    2>/dev/null)
if [ -n "$n" ] && [ "$n" != 0 ]; then
  echo "AgentDeck: $n new obligations for the agent, see deck obligations"
fi
exit 0
