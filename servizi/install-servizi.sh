#!/usr/bin/env bash
# Prepara sulla Deck l'area dei servizi ospitati. Ripetibile: ogni esecuzione porta la Deck allo stato voluto.
# Fasi: subvolume Btrfs @servizi, montaggio su /srv/servizi in fstab (nofail: se manca, l'avvio prosegue),
# unità modello agentdeck-servizio@.service, comando agentdeck-nuovo-servizio.
# Va eseguito come root sulla Deck, dopo uno snapshot (INV-3): deck snapshot create description=...
#
# Uso:  sudo bash servizi/install-servizi.sh
#
# Documentazione: docs/servizi.md

set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
MNT=/srv/servizi
SUBVOL=@servizi
UNIT=agentdeck-servizio@.service

step() { printf '\n== %s\n' "$*"; }

[ "$(id -u)" = 0 ] || { echo "ERRORE: serve root (sudo)" >&2; exit 1; }

DEV=$(findmnt -no SOURCE / | sed 's/\[.*//')
UUID=$(blkid -s UUID -o value "$DEV")
OPTS=$(findmnt -no OPTIONS / | tr ',' '\n' | grep -Ev '^(subvol|subvolid)=' | paste -sd, -)

step "Subvolume $SUBVOL su $DEV"
top=$(mktemp -d)
mount -o subvolid=5 "$DEV" "$top"
if [ -d "$top/$SUBVOL" ]; then
  echo "$SUBVOL esiste già"
else
  btrfs subvolume create "$top/$SUBVOL"
fi
umount "$top" && rmdir "$top"

step "Montaggio su $MNT"
install -d -m 0755 "$MNT"
line="UUID=$UUID	$MNT	btrfs     	$OPTS,subvol=/$SUBVOL,nofail	0 0"
if grep -qE "^[^#]*[[:space:]]$MNT[[:space:]]" /etc/fstab; then
  echo "$MNT è già in /etc/fstab"
else
  cp -a /etc/fstab "/etc/fstab.prima-servizi"
  printf '\n# AgentDeck: area dei servizi ospitati (docs/servizi.md)\n%s\n' "$line" >> /etc/fstab
  if ! findmnt --verify --tab-file /etc/fstab >/dev/null 2>&1; then
    cp -a /etc/fstab.prima-servizi /etc/fstab
    echo "ERRORE: fstab non valido, ripristinato" >&2
    findmnt --verify --tab-file /etc/fstab.prima-servizi || true
    exit 1
  fi
fi
systemctl daemon-reload
mountpoint -q "$MNT" || mount "$MNT"
findmnt "$MNT"
chown root:root "$MNT" && chmod 0755 "$MNT"

step "Unità modello $UNIT"
install -m 0644 "$HERE/$UNIT" "/etc/systemd/system/$UNIT"
systemctl daemon-reload
echo "installata /etc/systemd/system/$UNIT"

step "Comando agentdeck-nuovo-servizio"
install -m 0755 "$HERE/nuovo-servizio.sh" /usr/local/sbin/agentdeck-nuovo-servizio
command -v agentdeck-nuovo-servizio
