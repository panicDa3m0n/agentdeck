#!/usr/bin/env bash
# Installa o aggiorna deck sulla Deck, dal Mac. Ripetibile: ogni esecuzione porta la Deck allo stato del
# repository. Fasi: test sul Mac, python sulla Deck (snap-pac fa gli snapshot), copia in /opt/agentdeck,
# comando /usr/local/bin/deck, schermo della Deck (docs/schermo.md), test e prove sulla Deck.
#
# Uso:  deck/install.sh            (host SSH predefinito: agentdeck)
#       DECK_HOST=altro deck/install.sh
#
# Documentazione: docs/deck.md

set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
HOST=${DECK_HOST:-agentdeck}
DEST=/opt/agentdeck

step() { printf '\n== %s\n' "$*"; }

step "Test sul Mac"
(cd "$ROOT/deck" && python3 -m unittest discover -s tests -q)

step "Python sulla Deck"
ssh "$HOST" 'pacman -Q python >/dev/null 2>&1 && pacman -Q python || sudo pacman -S --noconfirm --needed python'

step "Copia in $DEST"
ssh "$HOST" "sudo install -d -o agent -g agent $DEST"
rsync -a --delete --exclude '__pycache__' --exclude 'VERSION' "$ROOT/deck/" "$HOST:$DEST/"
scp -q "$ROOT/VERSION" "$HOST:$DEST/VERSION"

step "Comando deck"
ssh "$HOST" "chmod +x $DEST/deck && sudo ln -sfn $DEST/deck /usr/local/bin/deck && command -v deck"

step "Schermo della Deck"
screen_out=$(ssh "$HOST" "sudo bash $DEST/screen/install-screen.sh")
echo "$screen_out"
if grep -q SSH_CHANGED <<<"$screen_out"; then
  step "Verifica di ssh, scp, rsync, uscite e dati (la modifica SSH si annulla da sola entro 3 minuti)"
  probe=$(mktemp)
  head -c 65536 /dev/urandom > "$probe"
  sum=$(shasum -a 256 < "$probe" | cut -d' ' -f1)
  set +e
  out=$(ssh -o ConnectTimeout=10 "$HOST" 'echo uscita; echo errore >&2; exit 7' 2>"$probe.err"); code=$?
  set -e
  if [ "$out" = uscita ] && [ "$(cat "$probe.err")" = errore ] && [ "$code" = 7 ] \
     && scp -q "$probe" "$HOST:/tmp/agentdeck-scp-probe" \
     && rsync -q "$probe" "$HOST:/tmp/agentdeck-rsync-probe" \
     && [ "$(ssh "$HOST" 'cat /tmp/agentdeck-scp-probe' | shasum -a 256 | cut -d' ' -f1)" = "$sum" ] \
     && [ "$(ssh "$HOST" 'sha256sum < /tmp/agentdeck-rsync-probe' | cut -d' ' -f1)" = "$sum" ] \
     && ssh "$HOST" 'rm -f /tmp/agentdeck-scp-probe /tmp/agentdeck-rsync-probe && sudo systemctl stop agentdeck-ssh-revert.timer'; then
    echo "ssh, scp, rsync, stdout, stderr, codice di uscita e dati binari invariati: modifica SSH confermata"
  else
    echo "ERRORE: verifica SSH fallita; la modifica si annulla da sola entro 3 minuti" >&2
    exit 1
  fi
  rm -f "$probe" "$probe.err"
fi

step "Test sulla Deck"
ssh "$HOST" "cd $DEST && python -m unittest discover -s tests -q"

step "Prove"
ssh "$HOST" 'deck; echo " (uscita $?)"; deck /indirizzo-inesistente; echo " (uscita $?)"'
