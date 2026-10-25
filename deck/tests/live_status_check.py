#!/usr/bin/env python3
"""Controllo dal vivo di deck status sulla Deck: ogni valore confrontato con una lettura indipendente
fatta con gli strumenti classici di Linux (free, df, ip, ss, systemctl, snapper, timedatectl, ...).

Uso sulla Deck: python /opt/agentdeck/tests/live_status_check.py   (uscita 1 se qualcosa non coincide)
Documentazione: docs/deck.md.
"""
import json
import re
import subprocess
import sys


def sh(cmd: str) -> str:
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


def main() -> int:
    s = json.loads(sh("deck status"))
    d = s["data"]
    free = sh("free -b | awk '/Mem:/{print $2, $7}'").split()
    df = sh("df -B1 --output=size,used,avail / | tail -1").split()
    iw = sh("iw dev wlan0 link")
    freq = re.search(r"freq:\s*([0-9.]+)", iw)
    signal = re.search(r"signal:\s*(-?[0-9]+)", iw)
    ss_ports = sorted({int(line.split()[4].rpartition(":")[2]) for line in sh("sudo ss -Hltun").splitlines()})
    snapper_count = len([ln for ln in sh("sudo snapper -c root list --columns number").splitlines()[2:]
                         if ln.strip() and ln.strip() != "0"])
    wifi = d["network"]["wifi"] or {}

    checks = [
        ("hostname", d["system"]["hostname"], sh("hostname"), None),
        ("kernel", d["system"]["kernel"], sh("uname -r"), None),
        ("uptime_s (±5)", d["system"]["uptime_s"], int(float(sh("cut -d' ' -f1 /proc/uptime"))), 5),
        ("product", d["hardware"]["product"], sh("cat /sys/class/dmi/id/product_name"), None),
        ("bios", d["hardware"]["bios_version"], sh("cat /sys/class/dmi/id/bios_version"), None),
        ("cpu_threads", d["hardware"]["cpu_threads"], int(sh("nproc --all")), None),
        ("battery %", d["battery"]["percent"], int(sh("cat /sys/class/power_supply/BAT1/capacity")), None),
        ("ac_online", d["battery"]["ac_online"], sh("cat /sys/class/power_supply/ACAD/online") == "1", None),
        ("apu °C (±2)", d["sensors"]["temps_c"]["apu"],
         round(int(sh("cat $(grep -l k10temp /sys/class/hwmon/hwmon*/name | sed 's/name$/temp1_input/')")) / 1000), 2),
        ("memory total", d["memory_bytes"]["total"], int(free[0]), None),
        ("memory available (±1%)", d["memory_bytes"]["available"], int(free[1]), int(free[0]) // 100),
        ("disk total", d["disk_bytes"]["total"], int(df[0]), None),
        ("disk used (±1 MB)", d["disk_bytes"]["used"], int(df[1]), 1 << 20),
        ("disk available (±1 MB)", d["disk_bytes"]["available"], int(df[2]), 1 << 20),
        ("ipv4 wlan0", next(i["ipv4"] for i in d["network"]["interfaces"] if i["name"] == "wlan0"),
         sh("ip -4 -o addr show wlan0 | awk '{print $4}' | cut -d/ -f1"), None),
        ("gateway", d["network"]["default_gateway"], sh("ip route show default | awk '{print $3}'"), None),
        ("wifi MHz", wifi.get("frequency_mhz"), int(float(freq.group(1))) if freq else None, None),
        ("wifi dBm (±6)", wifi.get("signal_dbm"), int(signal.group(1)) if signal else None, 6),
        ("porte in ascolto", sorted({p["port"] for p in d["listening"]}), ss_ports, None),
        ("system state", d["services"]["system_state"], sh("systemctl is-system-running"), None),
        ("servizi falliti", len(d["services"]["failed"]), int(sh("systemctl --failed --no-legend | wc -l")), None),
        ("snapshot", d["snapshots"]["count"], snapper_count, None),
        ("ntp", d["time"]["ntp_synchronized"], sh("timedatectl show -p NTPSynchronized --value") == "yes", None),
    ]
    bad = 0
    for name, ours, theirs, tolerance in checks:
        ok = ours == theirs if tolerance is None else (
            ours is not None and theirs is not None and abs(ours - theirs) <= tolerance)
        bad += not ok
        print(f"{'ok ' if ok else 'NO '} {name:<26} deck={ours!r:<28} sistema={theirs!r}")
    print(f"\n{len(checks) - bad}/{len(checks)} valori coincidono; avvisi: {[a['code'] for a in s['alerts']]}; "
          f"read_errors: {d['read_errors']}; took_ms: {s['meta']['took_ms']}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
