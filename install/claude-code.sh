#!/usr/bin/env bash
# Installa Claude Code sulla Deck per l'utente agent e ne verifica l'integrità (task O10.T1).
#
# 1. Lancia l'installatore ufficiale di Anthropic (https://claude.ai/install.sh), come utente normale, mai con
#    sudo: installa in ~/.local/share/claude/versions/ e crea il comando ~/.local/bin/claude.
# 2. Verifica oltre a quanto fa l'installatore, che controlla solo la checksum: firma GPG del manifest della
#    versione con la chiave di rilascio di Anthropic (impronta fissata qui sotto), poi la SHA256 del binario
#    installato contro il manifest firmato.
# 3. Stampa versione e diagnostica (claude doctor).
#
# Uso sulla Deck, come agent:  bash install/claude-code.sh [latest|stable|<versione>]
# Esce con un codice diverso da 0 se una verifica non passa. Documentazione: docs/claude-code.md
set -euo pipefail

CHANNEL="${1:-latest}"
BASE="https://downloads.claude.ai/claude-code-releases"
KEY_URL="https://downloads.claude.ai/keys/claude-code.asc"
# Impronta della chiave "Anthropic Claude Code Release Signing <security@anthropic.com>",
# pubblicata in https://code.claude.com/docs/en/setup (Binary integrity and code signing)
FINGERPRINT="31DDDE24DDFAB679F42D7BD2BAA929FF1A7ECACE"
PLATFORM="linux-x64"

fail() { echo "ERRORE: $*" >&2; exit 1; }
[ "$(id -u)" -ne 0 ] || fail "non lanciare come root: Claude Code si installa per l'utente agent"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

echo "== installatore ufficiale ($CHANNEL)"
curl -fsSL https://claude.ai/install.sh -o "$work/install.sh"
bash "$work/install.sh" "$CHANNEL"

claude="$HOME/.local/bin/claude"
[ -x "$claude" ] || fail "$claude non c'è dopo l'installazione"
version="$("$claude" --version | awk '{print $1}')"
binary="$HOME/.local/share/claude/versions/$version"
[ -f "$binary" ] || fail "binario della versione $version non trovato in $binary"
echo "installata la versione $version"

echo "== firma del manifest"
export GNUPGHOME="$work/gnupg"
mkdir -m 700 "$GNUPGHOME"
curl -fsSL "$KEY_URL" -o "$work/key.asc"
gpg --batch --quiet --import "$work/key.asc"
gpg --batch --with-colons --fingerprint | grep -q "^fpr:::::::::${FINGERPRINT}:" \
  || fail "la chiave scaricata non ha l'impronta attesa $FINGERPRINT"
curl -fsSL "$BASE/$version/manifest.json" -o "$work/manifest.json"
curl -fsSL "$BASE/$version/manifest.json.sig" -o "$work/manifest.json.sig"
gpg --batch --verify "$work/manifest.json.sig" "$work/manifest.json" 2>"$work/verify.txt" \
  || { cat "$work/verify.txt" >&2; fail "firma del manifest non valida"; }
grep -q "Good signature" "$work/verify.txt" || fail "firma del manifest non confermata"
echo "firma valida (impronta $FINGERPRINT)"

echo "== checksum del binario"
expected="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["platforms"][sys.argv[2]]["checksum"])' \
  "$work/manifest.json" "$PLATFORM")"
actual="$(sha256sum "$binary" | cut -d' ' -f1)"
[ "$expected" = "$actual" ] || fail "checksum diversa dal manifest firmato: atteso $expected, trovato $actual"
echo "checksum uguale al manifest firmato: $actual"

echo "== PATH per le sessioni interattive e di login"
# Le sessioni SSH non interattive non leggono questi file: lì si usa ~/.local/bin/claude (docs/claude-code.md)
line='export PATH="$HOME/.local/bin:$PATH"  # Claude Code (install/claude-code.sh)'
for rc in "$HOME/.bashrc" "$HOME/.bash_profile"; do
  grep -qF '.local/bin:$PATH"  # Claude Code' "$rc" 2>/dev/null || printf '\n%s\n' "$line" >> "$rc"
done

echo "== diagnostica"
"$claude" --version
"$claude" doctor || true
