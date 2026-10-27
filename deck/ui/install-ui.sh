#!/usr/bin/env bash
# Installa sulla Deck lo schermo grafico con le interfacce effimere (O15.T3, ADR-0003). Gira come root, lanciato
# da deck/install.sh dopo la copia in /opt/agentdeck. Ripetibile: cambia solo ciò che è diverso.
# - pacchetti cage, chromium, wlr-randr e grim: prima uno snapshot nostro (INV-3), poi snap-pac fa i suoi;
# - utente deckui senza privilegi per il browser, e la sessione PAM agentdeck-ui che gli dà seat, schermo e comandi;
# - servizi agentdeck-ui-server (deck ui, utente agent, 127.0.0.1:8790) e agentdeck-ui (cage + Chromium su tty1);
# - il terminale dell'agente (agentdeck-screen) resta installato ma spento: torna da solo se lo schermo grafico
#   non riesce a partire (OnFailure).
# SSH, rete e registrazione dei comandi non cambiano (INV-1).
# Documentazione: docs/interfacce.md
set -euo pipefail

SRC=$(cd "$(dirname "$0")" && pwd)
PKGS=(cage chromium wlr-randr grim)
UNITS=(agentdeck-ui-server.service agentdeck-ui.service)
PAM=/etc/pam.d/agentdeck-ui

changed=0
pacman -Q "${PKGS[@]}" >/dev/null 2>&1 || changed=1
cmp -s "$SRC/pam-agentdeck-ui" "$PAM" || changed=1
for unit in "${UNITS[@]}"; do cmp -s "$SRC/$unit" "/etc/systemd/system/$unit" || changed=1; done
if [ "$changed" = 1 ]; then
  snapper -c root create -d "deck/ui: prima dello schermo grafico"
fi

pacman -S --needed --noconfirm "${PKGS[@]}" >/dev/null
id deckui >/dev/null 2>&1 || useradd --system --create-home --home-dir /var/lib/agentdeck-ui \
  --shell /usr/bin/nologin --comment "AgentDeck, browser dello schermo" deckui
install -m 644 "$SRC/pam-agentdeck-ui" "$PAM"
chmod 755 "$SRC/kiosk.sh"
for unit in "${UNITS[@]}"; do install -m 644 "$SRC/$unit" "/etc/systemd/system/$unit"; done
systemctl daemon-reload

systemctl mask getty@tty1.service >/dev/null 2>&1
systemctl disable agentdeck-screen.service >/dev/null 2>&1 || true
systemctl enable agentdeck-ui-server.service agentdeck-ui.service >/dev/null 2>&1
systemctl restart agentdeck-ui-server.service
systemctl restart agentdeck-ui.service  # ferma il terminale, che è in conflitto su tty1
for _ in $(seq 1 20); do
  systemctl is-active --quiet agentdeck-ui.service && break
  sleep 1
done
systemctl is-active agentdeck-ui-server.service agentdeck-ui.service
