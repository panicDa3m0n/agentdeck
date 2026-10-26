#!/usr/bin/env bash
# Prova dell'accesso alla Deck da una rete esterna (task O10.T10). Porta il Mac sull'hotspot del telefono, verifica che
# ssh agentdeck passi da internet (scarlethome.ddns.net:49222) e che funzionino deck status e deck/install.sh, poi
# riporta il Mac sul Wi-Fi di casa, anche se una prova fallisce.
#
# Uso, dal Mac, in un terminale, dalla radice del repository:   bash install/remote-check.sh
# Chiede nome e password dell'hotspot: la password non viene mostrata, né scritta nel registro o salvata dallo script.
# Il Wi-Fi di casa si ritrova con la password che macOS ha già salvato; se macOS non la usa, lo script la chiede.
# Registro della prova: ${TMPDIR}/agentdeck-remote-check.log. Documentazione: docs/accesso.md
set -uo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
IF=$(networksetup -listallhardwareports | awk '/Wi-Fi/{getline; print $2; exit}')
LOG="${TMPDIR:-/tmp}/agentdeck-remote-check.log"
DOMAIN=scarlethome.ddns.net
results=()

current_ssid() { ipconfig getsummary "$IF" 2>/dev/null | awk -F ' SSID : ' '/ SSID : /{print $2; exit}'; }
step() { printf '\n== %s\n' "$*"; }
check() {  # check "<descrizione>" <condizione vera o falsa>
  if [ "$2" = 0 ]; then results+=("PASS $1"); echo "PASS $1"; else results+=("FAIL $1"); echo "FAIL $1"; fi
}
join() {  # join "<rete>" ["<password>"]: aspetta fino a 25 secondi che macOS sia davvero sulla rete
  local out
  if [ -n "${2-}" ]; then out=$(networksetup -setairportnetwork "$IF" "$1" "$2" 2>&1); else
    out=$(networksetup -setairportnetwork "$IF" "$1" 2>&1); fi
  [ -z "$out" ] || echo "networksetup: $out"
  for _ in $(seq 1 25); do [ "$(current_ssid)" = "$1" ] && return 0; sleep 1; done
  return 1
}
online() { for _ in $(seq 1 30); do curl -s -m 3 -o /dev/null https://www.apple.com && return 0; sleep 1; done; return 1; }

home_ssid=$(current_ssid)
home_ip=$(dig +short "$DOMAIN" A | tail -1)
[ -n "$IF" ] && [ -n "$home_ssid" ] || { echo "ERRORE: non trovo il Wi-Fi del Mac o la rete attuale"; exit 1; }
echo "Wi-Fi: $IF, rete di casa: $home_ssid, IP pubblico di casa: $home_ip"
read -r -p "Nome dell'hotspot [Davide]: " hotspot
hotspot=${hotspot:-Davide}
read -r -s -p "Password dell'hotspot (non viene mostrata): " hotspot_pass
echo

back_home() {
  step "Ritorno sul Wi-Fi di casa ($home_ssid)"
  if [ "$(current_ssid)" != "$home_ssid" ] && ! join "$home_ssid"; then
    read -r -s -p "macOS non ha usato la password salvata: password del Wi-Fi di casa: " home_pass
    echo
    join "$home_ssid" "$home_pass" || echo "ATTENZIONE: scegli $home_ssid dal menu del Wi-Fi"
    unset home_pass
  fi
  online && ping -c 1 -t 2 -q 192.168.1.49 >/dev/null 2>&1 && \
    ssh -o BatchMode=yes -o ConnectTimeout=10 agentdeck 'echo "di nuovo in casa: ssh agentdeck via $(echo $SSH_CLIENT | cut -d" " -f1)"'
  step "Esito"
  printf '%s\n' ${results[@]+"${results[@]}"}
  if printf '%s\n' ${results[@]+"${results[@]}"} | grep -q '^FAIL'; then echo "RISULTATO: qualcosa non va"; else
    echo "RISULTATO: accesso da fuori casa verificato"; fi
  echo "Registro: $LOG"
}

exec > >(tee "$LOG") 2>&1
trap back_home EXIT

step "Collegamento all'hotspot $hotspot"
join "$hotspot" "$hotspot_pass"; check "Mac sull'hotspot $hotspot" $?
unset hotspot_pass
[ "$(current_ssid)" = "$hotspot" ] || exit 1
online; check "internet raggiungibile dall'hotspot" $?

step "Il Mac è davvero fuori casa"
mac_ip=$(curl -s -m 5 https://api.ipify.org)
echo "IP pubblico del Mac: $mac_ip (casa: $home_ip)"
[ -n "$mac_ip" ] && [ "$mac_ip" != "$home_ip" ]; check "IP pubblico diverso da quello di casa" $?

step "ssh agentdeck sceglie internet"
route=$(ssh -G agentdeck 2>/dev/null | awk '/^hostname /{h=$2} /^port /{p=$2} END{print h":"p}')
echo "ssh agentdeck va verso $route"
[ "$route" = "$DOMAIN:49222" ]; check "ssh agentdeck usa $DOMAIN:49222" $?

step "ssh agentdeck e deck status"
client=$(ssh -o BatchMode=yes -o ConnectTimeout=20 agentdeck 'echo $SSH_CLIENT' | cut -d' ' -f1)
echo "la Deck vede la connessione da: $client"
[ -n "$client" ]; check "ssh agentdeck entra da fuori casa" $?
[ "$client" = "$mac_ip" ]; check "la Deck vede l'indirizzo esterno vero (sshguard lo può bloccare)" $?
ssh -o BatchMode=yes agentdeck 'deck status' | python3 -c '
import json, sys
s = json.load(sys.stdin)
print("deck status:", s["status"], "| avvisi:", [a["code"] for a in s["alerts"]], "| versione:", s["meta"]["version"])
sys.exit(0 if s["status"] == "ok" else 1)'
check "deck status risponde" $?

step "deck/install.sh da fuori casa"
(cd "$ROOT" && bash deck/install.sh) > "$LOG.install" 2>&1
code=$?
grep -E "^==|^Ran|^OK|FAIL|ERROR" "$LOG.install"
check "deck/install.sh completo (registro: $LOG.install)" $code

step "Sulla Deck"
ssh -o BatchMode=yes agentdeck "journalctl -t sshd-session --since -15min -o cat | grep -c 'Accepted publickey for agent from $mac_ip'" \
  | sed 's/^/accessi registrati da questo indirizzo: /'
ssh -o BatchMode=yes agentdeck 'sudo nft list set ip sshguard attackers | grep -q elements && echo "sshguard blocca qualcuno" || echo "sshguard: nessun indirizzo bloccato"'
