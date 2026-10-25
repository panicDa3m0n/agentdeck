#!/usr/bin/env python3
"""Controllo dal vivo di deck network sulla Deck: ogni valore confrontato con ip, iw, resolvectl e ss.

Uso sulla Deck: python /opt/agentdeck/tests/live_network_check.py   (uscita 1 se qualcosa non coincide)
Documentazione: docs/deck.md.
"""
import json
import re
import subprocess
import sys


def sh(cmd: str) -> str:
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


def main() -> int:
    fresh = json.loads(sh("deck network scan"))
    d = fresh["data"]
    link = sh("iw dev wlan0 link")
    freq = re.search(r"freq:\s*([0-9.]+)", link)
    ssid = re.search(r"SSID:\s*(.*)", link)
    dump = sh("sudo iw dev wlan0 scan dump")
    # Lettura indipendente dal parser di deck: blocco per blocco, nome esatto (riga "\tSSID: ...")
    blocks = []
    for chunk in re.split(r"\n(?=BSS )", dump):
        bssid = re.match(r"BSS ([0-9a-f:]{17})", chunk)
        f = re.search(r"^\tfreq:\s*([0-9.]+)", chunk, re.MULTILINE)
        s = re.search(r"^\tSSID: ?(.*)$", chunk, re.MULTILINE)
        if bssid and f:
            blocks.append((bssid.group(1), int(float(f.group(1))), s.group(1).strip() if s else ""))
    home = ssid.group(1).strip() if ssid else None
    band = lambda f: 2.4 if f < 3000 else (5.0 if f < 5925 else 6.0)  # noqa: E731
    home_bands = sorted({band(f) for _, f, s in blocks if s == home})
    mine = re.search(r"Connected to ([0-9a-f:]{17})", link).group(1)
    sibling = lambda b: b != mine and (b.split(":")[:5] == mine.split(":")[:5] or b.split(":")[1:] == mine.split(":")[1:])  # noqa: E731
    companions = sorted({s for b, _, s in blocks if s and s != home and (sibling(b) or s.startswith(home))})
    wlan = next(l for l in d["name_resolution"]["links"] if l["interface"] == "wlan0")
    checks = [
        ("ipv4 wlan0", next(i["ipv4"] for i in d["interfaces"] if i["name"] == "wlan0"),
         sh("ip -4 -o addr show wlan0 | awk '{print $4}' | cut -d/ -f1")),
        ("gateway", d["default_gateway"], sh("ip route show default | awk '{print $3}'")),
        ("wifi MHz", d["wifi"]["frequency_mhz"], int(float(freq.group(1))) if freq else None),
        ("SSID collegato", d["wifi"]["ssid"], ssid.group(1).strip() if ssid else None),
        ("access point in cache", d["scan"]["access_points"], dump.count("\nBSS ") + dump.startswith("BSS ")),
        ("bande della rete di casa", d["connected_network"]["bands_seen_ghz"], home_bands),
        ("reti sorelle", sorted(c["ssid"] for c in d["connected_network"]["companions"]), companions),
        ("DNS wlan0", wlan["dns_servers"], sh("resolvectl dns wlan0").split(":", 1)[1].split()),
        ("LLMNR wlan0", wlan["llmnr"], sh("resolvectl llmnr wlan0").endswith("yes")),
        ("mDNS wlan0", wlan["mdns"], sh("resolvectl mdns wlan0").endswith("yes")),
        ("porte in ascolto", sorted({p["port"] for p in d["listening"]}),
         sorted({int(l.split()[4].rpartition(":")[2]) for l in sh("sudo ss -Hltun").splitlines()})),
    ]
    bad = 0
    for name, ours, theirs in checks:
        ok = ours == theirs
        bad += not ok
        print(f"{'ok ' if ok else 'NO '} {name:<26} deck={ours!r:<32} sistema={theirs!r}")
    print(f"\n{len(checks) - bad}/{len(checks)} valori coincidono; avvisi: "
          f"{[(a['code'], a['action']) for a in fresh['alerts']]}; took_ms: {fresh['meta']['took_ms']}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
