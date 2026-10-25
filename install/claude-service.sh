#!/usr/bin/env bash
# Installa il servizio agentdeck-claude (Claude Code con Remote Control in tmux) sulla Deck (task O10.T2).
#
# Uso sulla Deck, come agent (usa sudo per l'unità):  bash install/claude-service.sh [start|enable]
#   start   installa l'unità e la avvia, senza abilitarla all'accensione (prima prova)
#   enable  la abilita anche all'accensione
# Prerequisiti: Claude Code installato (install/claude-code.sh), login fatto, tmux, cartella ~/agentdeck.
# Al primo avvio Remote Control chiede due conferme nella sessione tmux "claude": vanno date da chi ne ha il
# diritto (tmux attach -t claude). Documentazione: docs/claude-code.md
set -euo pipefail

MODE="${1:-start}"
here="$(cd "$(dirname "$0")" && pwd)"
fail() { echo "ERRORE: $*" >&2; exit 1; }

[ "$(id -un)" = agent ] || fail "lanciare come utente agent"
[ -x "$HOME/.local/bin/claude" ] || fail "Claude Code non installato: install/claude-code.sh"
command -v tmux >/dev/null || fail "tmux non installato"
"$HOME/.local/bin/claude" auth status 2>/dev/null | grep -q '"loggedIn": true' || fail "login non fatto: claude auth login"
mkdir -p "$HOME/agentdeck"

sudo install -m 0644 "$here/agentdeck-claude.service" /etc/systemd/system/agentdeck-claude.service
sudo systemctl daemon-reload
sudo systemctl restart agentdeck-claude.service
[ "$MODE" = enable ] && sudo systemctl enable agentdeck-claude.service
sleep 3
systemctl --no-pager --lines=0 status agentdeck-claude.service | head -5
echo "sessione tmux:"; tmux list-sessions 2>&1 | grep '^claude:' || echo "nessuna sessione claude"
