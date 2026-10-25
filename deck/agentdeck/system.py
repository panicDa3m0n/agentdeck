"""Letture dello stato della Deck da /proc, /sys e comandi di sistema, per deck status.

Ogni lettura restituisce None (o un dizionario con valori None) se non riesce: una lettura fallita non
rompe la schermata, finisce in read_errors. I parser sono funzioni pure, testate con output reali.
Documentazione: docs/deck.md. Specifica: docs/protocollo.md.
"""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

SYS = Path("/sys")
PROC = Path("/proc")


def run(cmd: list, sudo: bool = False, timeout: float = 5) -> Optional[str]:
    """Esegue un comando e ne restituisce lo stdout, o None se fallisce."""
    if sudo:
        cmd = ["sudo", "-n"] + cmd
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def read(path: Path) -> Optional[str]:
    try:
        return path.read_text().strip()
    except OSError:
        return None


def read_int(path: Path) -> Optional[int]:
    text = read(path)
    try:
        return int(text) if text is not None else None
    except ValueError:
        return None


# ---- Parser (puri)

def parse_meminfo(text: str) -> dict:
    """Valori di /proc/meminfo in byte."""
    values = {}
    for line in text.splitlines():
        m = re.match(r"(\w+):\s+(\d+)\s*kB", line)
        if m:
            values[m.group(1)] = int(m.group(2)) * 1024
    return values


def band_ghz(frequency_mhz: Optional[int]) -> Optional[float]:
    if frequency_mhz is None:
        return None
    if frequency_mhz < 3000:
        return 2.4
    return 5.0 if frequency_mhz < 5925 else 6.0


def parse_iw_link(text: str) -> dict:
    """Stato del collegamento Wi-Fi da `iw dev <if> link`."""
    if not text or text.startswith("Not connected"):
        return {"connected": False, "ssid": None, "frequency_mhz": None, "band_ghz": None, "signal_dbm": None,
                "rx_bitrate_mbps": None, "tx_bitrate_mbps": None}

    def find(pattern: str) -> Optional[str]:
        m = re.search(pattern, text, re.MULTILINE)
        return m.group(1) if m else None

    freq = find(r"^\s*freq:\s*([0-9.]+)")
    signal = find(r"^\s*signal:\s*(-?[0-9]+)")
    rx = find(r"^\s*rx bitrate:\s*([0-9.]+)")
    tx = find(r"^\s*tx bitrate:\s*([0-9.]+)")
    frequency = int(float(freq)) if freq else None
    return {"connected": True, "bssid": find(r"^Connected to ([0-9a-f:]{17})"), "ssid": find(r"^\s*SSID:\s*(.*)$"),
            "frequency_mhz": frequency,
            "band_ghz": band_ghz(frequency), "signal_dbm": int(signal) if signal else None,
            "rx_bitrate_mbps": float(rx) if rx else None, "tx_bitrate_mbps": float(tx) if tx else None}


def parse_ss(text: str) -> list:
    """Porte in ascolto da `ss -Hltunp`: protocollo, indirizzo, porta, processo."""
    sockets = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        address, _, port = parts[4].rpartition(":")
        process = re.search(r'users:\(\("([^"]+)"', line)
        try:
            port_number = int(port)
        except ValueError:
            continue
        sockets.append({"proto": parts[0], "address": address.strip("[]"), "port": port_number,
                        "process": process.group(1) if process else None})
    sockets.sort(key=lambda s: (s["port"], s["proto"], s["address"]))
    return sockets


def parse_snapper_list(text: str) -> list:
    """Gli snapshot da `snapper --jsonout list`, escluso lo 0 (il sistema in uso), dal più vecchio."""
    snapshots = []
    for e in json.loads(text).get("root", []):
        if e.get("number", 0) == 0:
            continue
        snapshots.append({"id": e["number"], "type": e.get("type"), "pre_id": e.get("pre-number"),
                          "date": iso_date(e.get("date")), "description": e.get("description"),
                          "cleanup": e.get("cleanup") or None, "userdata": e.get("userdata") or None})
    return snapshots


def parse_snapper(text: str) -> dict:
    """Riepilogo degli snapshot da `snapper --jsonout list`, per deck status."""
    entries = parse_snapper_list(text)
    keys = ("id", "type", "date", "description", "cleanup")

    def brief(e: Optional[dict]) -> Optional[dict]:
        return None if e is None else {k: e[k] for k in keys}

    manual = [e for e in entries if e["type"] == "single" and not e["cleanup"]]
    return {"count": len(entries), "latest": brief(entries[-1] if entries else None),
            "latest_manual": brief(manual[-1] if manual else None)}


def grub_snapshot_ids(text: str) -> set:
    """Gli snapshot avviabili dal menu di GRUB, dal file generato da grub-btrfs."""
    return {int(n) for n in re.findall(r"@?snapshots/([0-9]+)/snapshot", text)}


def iso_date(value: Optional[str]) -> Optional[str]:
    """Una data "AAAA-MM-GG HH:MM:SS" locale in ISO 8601 con fuso."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").astimezone().isoformat(timespec="seconds")
    except ValueError:
        return None


# ---- Letture

def system_info() -> dict:
    os_release = read(Path("/etc/os-release")) or ""
    pretty = re.search(r'^PRETTY_NAME="?([^"\n]*)"?', os_release, re.MULTILINE)
    uptime = read(PROC / "uptime")
    return {"hostname": socket.gethostname(), "os": pretty.group(1) if pretty else None,
            "kernel": os.uname().release, "uptime_s": int(float(uptime.split()[0])) if uptime else None}


def hardware() -> dict:
    cpuinfo = read(PROC / "cpuinfo") or ""
    model = re.search(r"^model name\s*:\s*(.*)$", cpuinfo, re.MULTILINE)
    dmi = SYS / "class" / "dmi" / "id"
    return {"vendor": read(dmi / "sys_vendor"), "product": read(dmi / "product_name"),
            "bios_version": read(dmi / "bios_version"), "cpu_model": model.group(1) if model else None,
            "cpu_threads": os.cpu_count()}


def load() -> dict:
    text = read(PROC / "loadavg")
    values = text.split()[:3] if text else [None] * 3
    return {k: float(v) if v is not None else None for k, v in zip(("load_1m", "load_5m", "load_15m"), values)}


def battery() -> dict:
    supply = SYS / "class" / "power_supply"
    status = read(supply / "BAT1" / "status")
    ac = read_int(supply / "ACAD" / "online")
    return {"percent": read_int(supply / "BAT1" / "capacity"),
            "state": status.lower().replace(" ", "_") if status else None,
            "ac_online": bool(ac) if ac is not None else None}


def hwmon() -> dict:
    """Temperature (°C) per sensore e giri della ventola, se leggibili."""
    names = {"k10temp": "apu", "amdgpu": "gpu", "nvme": "nvme", "acpitz": "acpi"}
    temps: dict = {v: None for v in names.values()}
    fan = None
    for h in sorted((SYS / "class" / "hwmon").glob("hwmon*")):
        name = read(h / "name")
        temp = read_int(h / "temp1_input")
        if name in names and temp is not None and temps[names[name]] is None:
            temps[names[name]] = round(temp / 1000)
        for f in sorted(h.glob("fan*_input")):
            fan = read_int(f) if fan is None else fan
    return {"temps_c": temps, "fan_rpm": fan}


def memory() -> dict:
    info = parse_meminfo(read(PROC / "meminfo") or "")
    total, available = info.get("MemTotal"), info.get("MemAvailable")
    swap_total, swap_free = info.get("SwapTotal"), info.get("SwapFree")
    return {"total": total, "available": available,
            "used": total - available if total is not None and available is not None else None,
            "swap_total": swap_total,
            "swap_used": swap_total - swap_free if swap_total is not None and swap_free is not None else None}


def disk(path: str = "/") -> dict:
    try:
        st = os.statvfs(path)
    except OSError:
        return {"total": None, "used": None, "available": None}
    total, free, available = st.f_blocks * st.f_frsize, st.f_bfree * st.f_frsize, st.f_bavail * st.f_frsize
    return {"total": total, "used": total - free, "available": available}


def parse_iw_scan(text: str) -> list:
    """Access point da `iw dev <if> scan [dump]`: BSSID, frequenza, banda, segnale, SSID, ultima volta visto."""
    points, current = [], None
    for line in text.splitlines():
        head = re.match(r"^BSS ([0-9a-f:]{17})", line)
        if head:
            current = {"bssid": head.group(1), "ssid": None, "frequency_mhz": None, "band_ghz": None,
                       "signal_dbm": None, "last_seen_ms": None, "associated": "-- associated" in line}
            points.append(current)
            continue
        if current is None:
            continue
        value = line.strip()
        if value.startswith("freq:"):
            current["frequency_mhz"] = int(float(value.split()[1]))
            current["band_ghz"] = band_ghz(current["frequency_mhz"])
        elif value.startswith("signal:"):
            current["signal_dbm"] = round(float(value.split()[1]))
        elif value.startswith("last seen:"):
            current["last_seen_ms"] = int(value.split()[2])
        elif line.startswith("\tSSID:"):
            current["ssid"] = line.split("SSID:", 1)[1].strip() or None
    return points


def group_networks(points: list) -> list:
    """Le reti visibili per nome, con le bande su cui trasmettono e il segnale migliore per banda."""
    networks: dict = {}
    for p in points:
        n = networks.setdefault(p["ssid"], {"ssid": p["ssid"], "bands_ghz": [], "best_signal_dbm": {},
                                            "access_points": []})
        n["access_points"].append(p)
        band = p["band_ghz"]
        if band is not None:
            if band not in n["bands_ghz"]:
                n["bands_ghz"].append(band)
            key = str(band)
            if p["signal_dbm"] is not None and (key not in n["best_signal_dbm"] or p["signal_dbm"] > n["best_signal_dbm"][key]):
                n["best_signal_dbm"][key] = p["signal_dbm"]
    for n in networks.values():
        n["bands_ghz"].sort()
    return sorted(networks.values(), key=lambda n: -max(n["best_signal_dbm"].values(), default=-999))


def same_router(a: Optional[str], b: Optional[str]) -> bool:
    """Due BSSID dello stesso apparecchio: i router danno a ogni rete un indirizzo che differisce solo nel
    primo o nell'ultimo byte (per esempio 58:4b:bc:20:65:d6 e 58:4b:bc:20:65:d7)."""
    if not a or not b or a == b:
        return False
    x, y = a.lower().split(":"), b.lower().split(":")
    return len(x) == len(y) == 6 and (x[:5] == y[:5] or x[1:] == y[1:])


def wifi_interface() -> Optional[str]:
    for d in sorted((SYS / "class" / "net").glob("*")):
        if (d / "wireless").exists():
            return d.name
    return None


def wifi_scan(fresh: bool = False) -> Optional[list]:
    """Access point visibili. Senza fresh legge la cache del kernel (immediata, ma tiene solo quelli visti di
    recente); con fresh fa una scansione attiva, che dura circa 5 secondi."""
    iface = wifi_interface()
    if iface is None:
        return None
    if fresh:
        run(["iw", "dev", iface, "scan"], sudo=True, timeout=20)
    text = run(["iw", "dev", iface, "scan", "dump"], sudo=True)
    return parse_iw_scan(text) if text is not None else None


def parse_resolvectl(text: str) -> dict:
    """Risoluzione dei nomi da `resolvectl status --json=short`: impostazioni globali e per interfaccia."""
    scopes = json.loads(text)

    def flag(value) -> Optional[bool]:
        return None if value is None else value != "no"

    def server(s) -> Optional[str]:
        return (s or {}).get("addressString")

    glob = next((s for s in scopes if "ifname" not in s), {})
    links = [{"interface": s["ifname"], "llmnr": flag(s.get("llmnr")), "mdns": flag(s.get("mDNS")),
              "dns_servers": [server(x) for x in s.get("servers", [])], "current_server": server(s.get("currentServer")),
              "default_route": s.get("defaultRoute")}
             for s in scopes if "ifname" in s]
    return {"global": {"llmnr": flag(glob.get("llmnr")), "mdns": flag(glob.get("mDNS")),
                       "current_server": server(glob.get("currentServer")),
                       "fallback_servers": [server(x) for x in glob.get("fallbackServers", [])]},
            "links": links}


def name_resolution() -> Optional[dict]:
    text = run(["resolvectl", "status", "--json=short"])
    return parse_resolvectl(text) if text else None


LLMNR_DROPIN = "/etc/systemd/resolved.conf.d/20-agentdeck-llmnr.conf"
WIFI_SWITCH_STATE = Path("/var/lib/agentdeck/wifi-switch.json")
WIFI_KEEP_FLAG = "/run/agentdeck/wifi-keep"
WIFI_SWITCH_SCRIPT = Path(__file__).resolve().parent / "wifi_switch.py"
WIFI_SWITCH_UNIT = "agentdeck-wifi-switch"


def llmnr_set(enabled: bool) -> None:
    """Accende o spegne LLMNR con un drop-in di systemd-resolved, poi lo riavvia. mDNS non cambia."""
    if enabled:
        run_checked(["rm", "-f", LLMNR_DROPIN])
    else:
        run_checked(["install", "-d", "/etc/systemd/resolved.conf.d"])
        run_checked(["sh", "-c", f"printf '[Resolve]\\nLLMNR=no\\n' > {LLMNR_DROPIN}"])
    run_checked(["systemctl", "restart", "systemd-resolved"])


def dns_works(name: str = "archlinux.org") -> bool:
    return run(["resolvectl", "query", "--legend=no", name], timeout=10) is not None


def iwd_profile_has_passphrase(ssid: str) -> bool:
    """Vero se il profilo iwd della rete contiene una Passphrase; la password non viene letta qui."""
    from .wifi_switch import profile_name
    out = run(["grep", "-c", "^Passphrase=", f"/var/lib/iwd/{profile_name(ssid)}"], sudo=True)
    return bool(out) and out.strip() != "0"


def wifi_switch_state() -> Optional[dict]:
    """Lo stato dell'ultimo cambio Wi-Fi. Un cambio "in corso" la cui unità non è più attiva (riavvio, errore)
    vale "interrupted"."""
    try:
        state = json.loads(WIFI_SWITCH_STATE.read_text())
    except (OSError, ValueError):
        return None
    if state.get("state") in ("switching", "awaiting_confirmation") and \
            run(["systemctl", "is-active", "--quiet", WIFI_SWITCH_UNIT]) is None:
        state = dict(state, state="interrupted")
    return state


def wifi_switch_start(target: str, fallback: str) -> bool:
    """Lancia il cambio Wi-Fi in un'unità transitoria, staccata dalla sessione SSH (vedi wifi_switch.py)."""
    run(["systemctl", "reset-failed", WIFI_SWITCH_UNIT], sudo=True)
    return run(["systemd-run", "--quiet", "--collect", f"--unit={WIFI_SWITCH_UNIT}", "/usr/bin/python3",
                str(WIFI_SWITCH_SCRIPT), target, fallback], sudo=True) is not None


def wifi_switch_keep() -> None:
    run_checked(["install", "-d", "/run/agentdeck"])
    run_checked(["touch", WIFI_KEEP_FLAG])


def network() -> dict:
    addrs = json.loads(run(["ip", "-j", "-4", "addr"]) or "[]")
    interfaces = [{"name": a.get("ifname"), "state": (a.get("operstate") or "").lower() or None,
                   "ipv4": next((i.get("local") for i in a.get("addr_info", []) if i.get("family") == "inet"), None)}
                  for a in addrs if a.get("ifname") != "lo"]
    route = json.loads(run(["ip", "-j", "route", "show", "default"]) or "[]")
    wifi_if = wifi_interface()
    wifi = parse_iw_link(run(["iw", "dev", wifi_if, "link"]) or "") if wifi_if else None
    if wifi is not None:
        wifi["interface"] = wifi_if
    return {"interfaces": interfaces, "default_gateway": route[0].get("gateway") if route else None,
            "default_interface": route[0].get("dev") if route else None, "wifi": wifi}


def listening() -> Optional[list]:
    text = run(["ss", "-Hltunp"], sudo=True)
    return parse_ss(text) if text is not None else None


def services() -> dict:
    state = run(["systemctl", "is-system-running"])  # esce con 1 quando lo stato è "degraded"
    if state is None:
        state = subprocess.run(["systemctl", "is-system-running"], capture_output=True, text=True).stdout
    failed = json.loads(run(["systemctl", "list-units", "--failed", "--output=json"]) or "null")
    return {"system_state": state.strip() or None if state else None,
            "failed": [u.get("unit") for u in failed] if isinstance(failed, list) else None}


def snapshots() -> Optional[dict]:
    text = run(["snapper", "--jsonout", "list"], sudo=True)
    return parse_snapper(text) if text else None


GRUB_BTRFS_CFG = Path("/boot/grub/grub-btrfs.cfg")


def snapshot_list() -> Optional[list]:
    """Tutti gli snapshot, ognuno con in_grub: vero se è avviabile dal menu snapshot di GRUB.

    in_grub vale None se il menu non è leggibile: grub-btrfsd lo cancella e lo riscrive a ogni modifica,
    quindi per un attimo il file non esiste.
    """
    text = run(["snapper", "--jsonout", "list"], sudo=True)
    if not text:
        return None
    menu = read(GRUB_BTRFS_CFG)
    in_grub = grub_snapshot_ids(menu) if menu is not None else None
    return [dict(s, in_grub=None if in_grub is None else s["id"] in in_grub) for s in parse_snapper_list(text)]


SNAPSHOTS_DIR = "/.snapshots"
TOP_MOUNT = "/run/agentdeck/btrfs-top"
UNTOUCHED_BY_ROLLBACK = ["/home", "/var/log", "/var/cache/pacman/pkg", "/.snapshots", "/efi"]

# File dello snapshot di destinazione da cui dipende l'accesso dell'agente (INV-1)
ACCESS_FILES = {
    "sshd_enabled": "etc/systemd/system/multi-user.target.wants/sshd.service",
    "networkd_enabled": "etc/systemd/system/multi-user.target.wants/systemd-networkd.service",
    "iwd_enabled": "etc/systemd/system/multi-user.target.wants/iwd.service",
    "wifi_network_file": "etc/systemd/network/25-wireless.network",
    "agent_sudoers": "etc/sudoers.d/10-agent",
}


def run_checked(cmd: list, sudo: bool = True, timeout: float = 120) -> str:
    """Come run(), ma un fallimento solleva RuntimeError con lo stderr del comando."""
    full = ["sudo", "-n"] + cmd if sudo else cmd
    result = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:3])}: {result.stderr.strip() or 'exit ' + str(result.returncode)}")
    return result.stdout


def parse_pacman_q(text: str) -> dict:
    """Pacchetti installati da `pacman -Q`: nome -> versione."""
    return dict(line.split(" ", 1) for line in text.splitlines() if " " in line)


def parse_pacman_local(names: list) -> dict:
    """Pacchetti di uno snapshot dai nomi delle cartelle di var/lib/pacman/local (nome-versione-rilascio)."""
    packages = {}
    for entry in names:
        parts = entry.strip().rsplit("-", 2)
        if len(parts) == 3:
            packages[parts[0]] = parts[1] + "-" + parts[2]
    return packages


def package_diff(current: dict, target: dict) -> dict:
    """Cosa cambia nei pacchetti tornando allo snapshot."""
    return {"removed": sorted(n for n in current if n not in target),
            "restored": sorted(n for n in target if n not in current),
            "changed": [{"name": n, "from": current[n], "to": target[n]}
                        for n in sorted(current) if n in target and current[n] != target[n]]}


def snapshot_packages(snapshot_id: int) -> tuple:
    """(pacchetti attuali, pacchetti dello snapshot)."""
    current = parse_pacman_q(run_checked(["pacman", "-Q"], sudo=False))
    listing = run_checked(["ls", f"{SNAPSHOTS_DIR}/{int(snapshot_id)}/snapshot/var/lib/pacman/local"])
    return current, parse_pacman_local([n for n in listing.split() if n != "ALPM_DB_VERSION"])


def snapshot_access_check(snapshot_id: int) -> dict:
    """Controlla nello snapshot che dopo il rollback la Deck resti raggiungibile come agent (INV-1)."""
    base = f"{SNAPSHOTS_DIR}/{int(snapshot_id)}/snapshot"
    script = "; ".join(
        [f'[ -e "{base}/{rel}" ] && echo {key}=1 || echo {key}=0' for key, rel in ACCESS_FILES.items()]
        + [f'grep -q "^agent:" "{base}/etc/passwd" && echo agent_user=1 || echo agent_user=0',
           f'ls "{base}"/var/lib/iwd/*.psk >/dev/null 2>&1 && echo wifi_profile=1 || echo wifi_profile=0',
           f'grep -h "^AllowUsers" "{base}"/etc/ssh/sshd_config "{base}"/etc/ssh/sshd_config.d/*.conf 2>/dev/null '
           f'| sed "s/^/allow=/" || true'])
    out = run_checked(["sh", "-c", script])
    checks: dict = {}
    allow_lines = []
    for line in out.splitlines():
        key, _, value = line.partition("=")
        if key == "allow":
            allow_lines.append(value)
        elif key:
            checks[key] = value == "1"
    checks["ssh_allows_agent"] = all("agent" in line.split()[1:] for line in allow_lines)
    checks["ok"] = all(checks.values())
    return checks


def root_device() -> str:
    """Il dispositivo Btrfs della radice, per esempio /dev/nvme0n1p2."""
    return run_checked(["findmnt", "-no", "SOURCE", "/"], sudo=False).strip().split("[")[0]


def rollback_root(snapshot_id: int, stamp: str) -> str:
    """Rimpiazza il subvolume @ con una copia scrivibile dello snapshot. Restituisce il nome del vecchio @.

    Lavora sul livello superiore del filesystem (subvolid=5) montato in TOP_MOUNT. Se lo scambio fallisce
    a metà, rimette subito il vecchio @ al suo posto: in ogni caso, all'uscita, @ esiste.
    """
    top = TOP_MOUNT
    source = f"{top}/@snapshots/{int(snapshot_id)}/snapshot"
    new, old = f"{top}/@new-{stamp}", f"{top}/@old-{stamp}"
    run_checked(["mkdir", "-p", top])
    run_checked(["mount", "-o", "subvolid=5", root_device(), top])
    try:
        run_checked(["test", "-d", source])
        run_checked(["btrfs", "subvolume", "snapshot", source, new])
        try:
            run_checked(["mv", f"{top}/@", old])
        except Exception:
            run_checked(["btrfs", "subvolume", "delete", new])
            raise
        try:
            run_checked(["mv", new, f"{top}/@"])
        except Exception:
            run_checked(["mv", old, f"{top}/@"])  # il sistema torna com'era
            raise
    finally:
        run(["umount", top], sudo=True)
    return f"@old-{stamp}"


def schedule_reboot(seconds: int) -> bool:
    """Riavvia la Deck fra qualche secondo, così la risposta di deck arriva prima."""
    return run(["systemd-run", "--quiet", f"--on-active={int(seconds)}", "--unit=agentdeck-rollback-reboot",
                "systemctl", "reboot"], sudo=True) is not None


def snapshot_create(description: str) -> Optional[int]:
    """Crea uno snapshot singolo con questa descrizione; restituisce il numero, o None se fallisce."""
    out = run(["snapper", "-c", "root", "create", "--print-number", "--userdata", "source=deck",
               "--description", description], sudo=True)
    try:
        return int(out.strip()) if out else None
    except ValueError:
        return None


def time_sync() -> dict:
    text = run(["timedatectl", "show", "-p", "NTPSynchronized", "-p", "Timezone"]) or ""
    values = dict(line.split("=", 1) for line in text.splitlines() if "=" in line)
    synced = values.get("NTPSynchronized")
    return {"ntp_synchronized": synced == "yes" if synced else None, "timezone": values.get("Timezone")}


READERS: dict = {
    "system": system_info, "hardware": hardware, "load": load, "battery": battery, "sensors": hwmon,
    "memory_bytes": memory, "disk_bytes": disk, "network": network, "listening": listening,
    "services": services, "snapshots": snapshots, "time": time_sync,
}


def collect(readers: Optional[dict] = None) -> dict:
    """Esegue tutte le letture; quelle che falliscono valgono None e compaiono in read_errors."""
    data: dict = {}
    errors = []
    for key, reader in (readers or READERS).items():
        try:
            data[key] = reader()
        except Exception as e:  # una lettura rotta non deve rompere la schermata
            data[key] = None
            errors.append({"section": key, "exception": type(e).__name__, "detail": str(e)})
        if data[key] is None and not any(e["section"] == key for e in errors):
            errors.append({"section": key, "exception": None, "detail": "no data"})
    data["read_errors"] = errors
    return data
