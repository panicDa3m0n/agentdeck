#!/usr/bin/env python3
"""Cambio di rete Wi-Fi con ritorno automatico (task O4.T2).

Gira come root in un'unità transitoria di systemd (agentdeck-wifi-switch), staccata dalla sessione SSH che la
lancia: il cambio di rete interrompe quella sessione. Passi:
  1. crea il profilo iwd della rete di destinazione copiando solo la Passphrase dal profilo della rete di
     riserva (le chiavi SAE-PT dipendono dal nome della rete e non si copiano); la password non viene mai stampata;
  2. fa scansionare iwd finché la destinazione compare nel suo elenco (iwctl si collega solo a reti viste da
     una scansione di iwd, non a quelle di `iw scan`), si collega e aspetta un indirizzo e il gateway
     raggiungibile (IP_WAIT_S);
  3. aspetta che l'agente confermi di raggiungere ancora la Deck (deck network keep_5ghz crea KEEP_FLAG);
  4. confermato: preferenza per i 5 GHz in /etc/iwd/main.conf. Altrimenti torna alla rete di riserva e toglie
     il profilo appena creato.
Lo stato di ogni passo è in STATE_FILE, letto da deck network.

Uso: wifi_switch.py <ssid di destinazione> <ssid di riserva>
Documentazione: docs/deck.md
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

STATE_FILE = Path("/var/lib/agentdeck/wifi-switch.json")
KEEP_FLAG = Path("/run/agentdeck/wifi-keep")
IWD_DIR = Path("/var/lib/iwd")
IWD_MAIN = Path("/etc/iwd/main.conf")
IP_WAIT_S = 60
SCAN_WAIT_S = 20
CONFIRM_WAIT_S = 180
BAND_PREFERENCE = "[Rank]\nBandModifier5GHz=1.5\n"


def profile_name(ssid: str) -> str:
    """Nome del file di profilo iwd: l'SSID così com'è se usa solo lettere, cifre, spazi, - e _, altrimenti
    = seguito dall'SSID in esadecimale."""
    if re.fullmatch(r"[A-Za-z0-9 _-]+", ssid):
        return f"{ssid}.psk"
    return "=" + ssid.encode().hex() + ".psk"


def extract_passphrase(profile_text: str):
    """La sola Passphrase della sezione [Security] di un profilo iwd, o None."""
    section = None
    for line in profile_text.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line
        elif section == "[Security]" and line.startswith("Passphrase="):
            return line[len("Passphrase="):]
    return None


def build_profile(passphrase: str) -> str:
    return f"[Security]\nPassphrase={passphrase}\n"


_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_NETWORK_ROW = re.compile(r"^\s*>?\s*(\S.*?)\s{2,}(psk|open|8021x|wep)\s")


def parse_get_networks(text: str) -> list:
    """I nomi delle reti di `iwctl station <dev> get-networks`, esatti (mai per prefisso, P11)."""
    return [m.group(1) for m in map(_NETWORK_ROW.match, _ANSI.sub("", text).splitlines()) if m]


def sh(cmd: list, timeout: float = 30) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def iwctl(*args: str) -> int:
    """Un comando iwctl, con esito e messaggio nel journal dell'unità (iwctl non stampa mai la password)."""
    try:
        r = subprocess.run(["iwctl", *args], capture_output=True, text=True, timeout=30)
        code, out = r.returncode, _ANSI.sub("", r.stdout + r.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        code, out = -1, type(e).__name__
    print(f"wifi-switch: iwctl {' '.join(args[:3])} -> {code} {out[:200]}", flush=True)
    return code


def iwd_sees(dev: str, ssid: str) -> bool:
    return ssid in parse_get_networks(sh(["iwctl", "station", dev, "get-networks"]))


def write_state(state: str, target: str, fallback: str, **extra) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {"state": state, "target": target, "fallback": fallback,
            "time": datetime.now().astimezone().isoformat(timespec="seconds"), **extra}
    STATE_FILE.write_text(json.dumps(data))
    STATE_FILE.chmod(0o644)
    print(f"wifi-switch: {state} {extra}", flush=True)


def wifi_device() -> str:
    for d in sorted(Path("/sys/class/net").glob("*")):
        if (d / "wireless").exists():
            return d.name
    raise RuntimeError("no Wi-Fi interface")


def link_ok(dev: str, ssid: str):
    """L'IPv4 se la Deck è collegata a ssid, ha un indirizzo e raggiunge il gateway; altrimenti None."""
    link = sh(["iw", "dev", dev, "link"])
    current = re.search(r"^\s*SSID:\s*(.*)$", link, re.MULTILINE)
    if not current or current.group(1).strip() != ssid:
        return None
    addrs = json.loads(sh(["ip", "-j", "-4", "addr", "show", "dev", dev]) or "[]")
    ip = next((i["local"] for a in addrs for i in a.get("addr_info", []) if i.get("family") == "inet"), None)
    routes = json.loads(sh(["ip", "-j", "route", "show", "default"]) or "[]")
    gateway = routes[0].get("gateway") if routes else None
    if not ip or not gateway:
        return None
    return ip if subprocess.run(["ping", "-c", "1", "-W", "2", gateway], capture_output=True).returncode == 0 else None


def wait_for(check, seconds: float, step: float = 2):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = check()
        if result:
            return result
        time.sleep(step)
    return None


def main(target: str, fallback: str) -> int:
    dev = wifi_device()
    KEEP_FLAG.unlink(missing_ok=True)
    write_state("switching", target, fallback)

    target_profile, fallback_profile = IWD_DIR / profile_name(target), IWD_DIR / profile_name(fallback)
    created = False
    if not target_profile.exists():
        passphrase = extract_passphrase(fallback_profile.read_text()) if fallback_profile.exists() else None
        if passphrase is None:
            write_state("failed", target, fallback, reason="no_passphrase")
            return 1
        target_profile.write_text(build_profile(passphrase))
        target_profile.chmod(0o600)
        created = True
        time.sleep(2)  # iwd legge i profili nuovi dalla cartella

    def revert(reason: str) -> int:
        if created:
            target_profile.unlink(missing_ok=True)
        iwctl("station", dev, "connect", fallback)
        back = wait_for(lambda: link_ok(dev, fallback), IP_WAIT_S)
        if back is None:  # ultima risorsa: iwd riparte e si ricollega da solo a una rete nota
            sh(["systemctl", "restart", "iwd"])
            back = wait_for(lambda: link_ok(dev, fallback), IP_WAIT_S)
        write_state("reverted", target, fallback, reason=reason, ipv4=back)
        return 1

    try:
        iwctl("station", dev, "scan")
        if not wait_for(lambda: iwd_sees(dev, target), SCAN_WAIT_S):
            return revert("not_seen_by_iwd")
        iwctl("station", dev, "connect", target)
        ip = wait_for(lambda: link_ok(dev, target), IP_WAIT_S)
        if ip is None:
            return revert("no_connection")

        write_state("awaiting_confirmation", target, fallback, ipv4=ip, confirm_within_s=CONFIRM_WAIT_S)
        if not wait_for(lambda: KEEP_FLAG.exists(), CONFIRM_WAIT_S, step=1):
            return revert("not_confirmed")

        IWD_MAIN.parent.mkdir(parents=True, exist_ok=True)
        IWD_MAIN.write_text(BAND_PREFERENCE)
    except Exception as e:  # qualunque imprevisto dopo il cambio: si torna alla rete di riserva
        return revert("error: " + type(e).__name__)
    KEEP_FLAG.unlink(missing_ok=True)
    write_state("kept", target, fallback, ipv4=ip)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
