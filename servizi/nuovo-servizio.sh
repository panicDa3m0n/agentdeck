#!/usr/bin/env bash
# Crea la cartella di un nuovo servizio in /srv/servizi/<nome> e il suo utente di sistema srv-<nome>.
# Ripetibile: completa quello che manca e non tocca codice, dati o configurazione già presenti.
# Non avvia né abilita il servizio: lo si fa con deck service start|enable name=agentdeck-servizio@<nome>
#
# Uso:  sudo agentdeck-nuovo-servizio <nome>      (nome: minuscole, cifre e trattini, max 28 caratteri)
#
# Installato da servizi/install-servizi.sh. Documentazione: docs/servizi.md

set -euo pipefail

ROOT=/srv/servizi
OWNER=agent   # l'agente distribuisce codice e configurazione; il servizio li legge soltanto

[ "$(id -u)" = 0 ] || { echo "ERRORE: serve root (sudo)" >&2; exit 1; }
nome=${1:-}
[[ "$nome" =~ ^[a-z][a-z0-9-]{0,27}$ ]] || { echo "ERRORE: nome non valido: minuscole, cifre e trattini, max 28" >&2; exit 2; }
mountpoint -q "$ROOT" || { echo "ERRORE: $ROOT non è montato" >&2; exit 1; }

user=srv-$nome
dir=$ROOT/$nome

if ! id "$user" >/dev/null 2>&1; then
  useradd --system --user-group --no-create-home --home-dir "$dir" --shell /usr/bin/nologin \
          --comment "AgentDeck servizio $nome" "$user"
fi

install -d -o "$OWNER" -g "$user" -m 0750 "$dir"
install -d -o "$OWNER" -g "$user" -m 0750 "$dir/app" "$dir/config"
install -d -o "$user"  -g "$user" -m 0750 "$dir/dati"

if [ ! -e "$dir/config/env" ]; then
  install -o "$OWNER" -g "$user" -m 0640 /dev/null "$dir/config/env"
  cat > "$dir/config/env" <<'EOF'
# Variabili d'ambiente del servizio (KEY=valore, una per riga). Qui vanno anche i segreti: non sono in git (INV-6).
# Già impostate dall'unità: SERVIZIO_NOME, SERVIZIO_DIR, SERVIZIO_DATI, HOST=127.0.0.1
# PORT=8001
EOF
fi

if [ ! -e "$dir/avvia" ]; then
  install -o "$OWNER" -g "$user" -m 0640 /dev/null "$dir/avvia"
  cat > "$dir/avvia" <<'EOF'
#!/bin/sh
# Comando che avvia il servizio, in primo piano (systemd lo segue e lo riavvia se cade).
# Cartella di lavoro: app/. Scrivere solo in "$SERVIZIO_DATI". Ascoltare su "$HOST" (127.0.0.1 salvo decisione).
# Quando è pronto: chmod 0750 avvia  (finché non è eseguibile l'unità non parte).
echo "avvia non ancora configurato" >&2
exit 1
EOF
fi

if [ ! -e "$dir/LEGGIMI.md" ]; then
  install -o "$OWNER" -g "$user" -m 0640 /dev/null "$dir/LEGGIMI.md"
  cat > "$dir/LEGGIMI.md" <<EOF
# Servizio $nome

Cosa fa, da quale repository viene (URL e commit), come si aggiorna, su quale porta ascolta.

- Unità: agentdeck-servizio@$nome.service, utente $user
- app/: codice (dell'agente, in sola lettura per il servizio)
- dati/: dati persistenti (unica cartella scrivibile dal servizio)
- config/env: variabili e segreti; avvia: comando di avvio

Struttura dell'area: docs/servizi.md nel repository AgentDeck.
EOF
fi

echo "servizio $nome pronto in $dir (utente $user)"
echo "prossimi passi: codice in app/, comando in avvia (chmod 0750), poi deck service start name=agentdeck-servizio@$nome"
