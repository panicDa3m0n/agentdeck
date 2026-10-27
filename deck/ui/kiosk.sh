#!/bin/sh
# AgentDeck: dentro cage, come utente deckui. Orienta lo schermo e apre la pagina dello schermo in Chromium a tutto
# schermo. Il pannello della Deck è 800x1280 montato in verticale: se cage lo lascia così, lo si ruota (la console
# del kernel fa lo stesso, fbcon rotate=1). Il codice per l'API arriva nell'ancora dell'indirizzo, che il browser
# non manda al server. Documentazione: docs/interfacce.md
set -u
TRANSFORM=${AGENTDECK_UI_TRANSFORM:-270}
if wlr-randr 2>/dev/null | grep -q "Transform: normal"; then
  wlr-randr --output eDP-1 --transform "$TRANSFORM" || true
fi
token=$(cat /run/agentdeck-ui.token 2>/dev/null || true)
exec /usr/bin/chromium --kiosk --ozone-platform=wayland --no-first-run --noerrdialogs --disable-infobars \
  --disable-session-crashed-bubble --disable-features=Translate,TranslateUI,MediaRouter --lang=it --password-store=basic \
  --disable-pinch --overscroll-history-navigation=0 --incognito --user-data-dir="$HOME/chromium" \
  "http://127.0.0.1:8790/#t=$token"
