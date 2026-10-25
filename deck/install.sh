#!/usr/bin/env bash
# Installa o aggiorna deck sulla Deck, dal Mac. Ripetibile: ogni esecuzione porta la Deck allo stato del
# repository. Fasi: test sul Mac, python sulla Deck (snap-pac fa gli snapshot), copia in /opt/agentdeck,
# comando /usr/local/bin/deck, test e prove sulla Deck.
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

step "Test sulla Deck"
ssh "$HOST" "cd $DEST && python -m unittest discover -s tests -q"

step "Prove"
ssh "$HOST" 'deck; echo " (uscita $?)"; deck /indirizzo-inesistente; echo " (uscita $?)"'
