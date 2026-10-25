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
    return {"connected": True, "ssid": find(r"^\s*SSID:\s*(.*)$"), "frequency_mhz": frequency,
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


def parse_snapper(text: str) -> dict:
    """Riepilogo degli snapshot da `snapper --jsonout list`."""
    entries = [e for e in json.loads(text).get("root", []) if e.get("number", 0) != 0]

    def brief(e: Optional[dict]) -> Optional[dict]:
        if e is None:
            return None
        return {"id": e["number"], "type": e["type"], "date": iso_date(e.get("date")),
                "description": e.get("description"), "cleanup": e.get("cleanup") or None}

    manual = [e for e in entries if e.get("type") == "single" and not e.get("cleanup")]
    return {"count": len(entries), "latest": brief(entries[-1] if entries else None),
            "latest_manual": brief(manual[-1] if manual else None)}


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


def network() -> dict:
    addrs = json.loads(run(["ip", "-j", "-4", "addr"]) or "[]")
    interfaces = [{"name": a.get("ifname"), "state": (a.get("operstate") or "").lower() or None,
                   "ipv4": next((i.get("local") for i in a.get("addr_info", []) if i.get("family") == "inet"), None)}
                  for a in addrs if a.get("ifname") != "lo"]
    route = json.loads(run(["ip", "-j", "route", "show", "default"]) or "[]")
    wifi_if = next((i["name"] for i in interfaces if i["name"] and (SYS / "class" / "net" / i["name"] / "wireless").exists()), None)
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
