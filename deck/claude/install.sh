#!/usr/bin/env bash
# Installa sulla Deck la configurazione di Claude Code per AgentDeck (task O10.T3). Si lancia dal Mac, dalla radice
# del repository, dopo deck/install.sh (che copia guard.py e session_start.py in /opt/agentdeck/claude):
#
#   bash deck/claude/install.sh
#
# Strati:
#   1. stile di output "AgentDeck"      -> ~/.claude/output-styles/agentdeck.md e outputStyle nelle impostazioni utente
#   2. regole stabili (CLAUDE.md)       -> /etc/claude-code/CLAUDE.md, generato da modello e invarianti
#   3. vincoli duri e hook              -> /etc/claude-code/managed-settings.json (deny, bypass predefinito, hook)
#   4. strumenti: il server MCP deck    -> `deck mcp` registrato per l'utente agent (~/.claude.json), i suoi
#                                          strumenti permessi nelle impostazioni gestite (O10.T6)
#   5. procedure: le skill di AgentDeck -> ~/.claude/skills/agentdeck-*, da deck/claude/skills (O10.T9); le altre
#                                          skill dell'utente non vengono toccate
# Poi riavvia il servizio agentdeck-claude, perché le sessioni nuove leggano la configurazione.
# Documentazione: docs/claude-code.md
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../.." && pwd)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

python3 "$here/build_claude_md.py" "$repo" > "$work/CLAUDE.md"
python3 -m json.tool "$here/managed-settings.json" > /dev/null
cp "$here/managed-settings.json" "$here/output-styles/agentdeck.md" "$work/"

ssh agentdeck 'deck snapshot create "description=prima della configurazione di Claude Code (deck/claude/install.sh)" >/dev/null && echo snapshot ok'
scp -q "$work/CLAUDE.md" "$work/managed-settings.json" "$work/agentdeck.md" agentdeck:/tmp/
ssh agentdeck 'rm -rf /tmp/agentdeck-skills' && scp -q -r "$here/skills" agentdeck:/tmp/agentdeck-skills
ssh agentdeck 'set -e
  test -x /opt/agentdeck/claude/guard.py -o -f /opt/agentdeck/claude/guard.py || { echo "manca /opt/agentdeck/claude: lancia prima deck/install.sh"; exit 1; }
  sudo install -d -m 0755 /etc/claude-code
  sudo install -m 0644 /tmp/CLAUDE.md /etc/claude-code/CLAUDE.md
  sudo install -m 0644 /tmp/managed-settings.json /etc/claude-code/managed-settings.json
  install -d ~/.claude/output-styles
  install -m 0644 /tmp/agentdeck.md ~/.claude/output-styles/agentdeck.md
  python3 - <<EOF
import json, pathlib
p = pathlib.Path.home() / ".claude" / "settings.json"
s = json.loads(p.read_text()) if p.exists() else {}
s["outputStyle"] = "AgentDeck"
p.write_text(json.dumps(s, indent=2) + "\n")
EOF
  rm -f /tmp/CLAUDE.md /tmp/managed-settings.json /tmp/agentdeck.md
  install -d ~/.claude/skills
  for d in ~/.claude/skills/agentdeck-*/; do
    if [ -d "$d" ] && [ ! -d "/tmp/agentdeck-skills/$(basename "$d")" ]; then rm -rf "$d"; fi
  done
  for d in /tmp/agentdeck-skills/*/; do n=$(basename "$d"); rm -rf ~/.claude/skills/"$n"; cp -r "$d" ~/.claude/skills/"$n"; done
  rm -rf /tmp/agentdeck-skills
  /usr/local/bin/deck mcp </dev/null || { echo "deck mcp non parte: lancia prima deck/install.sh"; exit 1; }
  ~/.local/bin/claude mcp remove --scope user deck >/dev/null 2>&1 || true
  ~/.local/bin/claude mcp add --transport stdio --scope user deck -- /usr/local/bin/deck mcp >/dev/null
  sudo systemctl restart agentdeck-claude
  echo "installato: /etc/claude-code/{CLAUDE.md,managed-settings.json}, ~/.claude/output-styles/agentdeck.md, server MCP deck, skill: $(ls -d ~/.claude/skills/agentdeck-* | wc -l)"'
