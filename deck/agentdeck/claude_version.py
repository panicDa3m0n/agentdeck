"""Claude Code a versione fissa sulla Deck (task O18.T2, piano punto 11).

Due blocchi, entrambi impostazioni gestite di Claude Code (INV-10, nessuna modifica al programma):
- DISABLE_AUTOUPDATER=1 in env di deck/claude/managed-settings.json: niente aggiornamenti in background;
- requiredMaximumVersion nel file /etc/claude-code/managed-settings.d/50-agentdeck-versione.json, scritto da qui:
  Claude Code rifiuta di aggiornarsi oltre e di partire in una versione più nuova.
Cambiare versione: si alza il limite, `claude install <versione>` scarica e collega il binario, poi la prova degli
agganci (agentdeck/claude_probe.py) sul binario nuovo; se fallisce si torna al binario e al limite di prima. Le
sessioni già aperte tengono il loro binario fino al riavvio. Versioni disponibili lette da downloads.claude.ai.
Uscite di claude e della rete sono testo esterno: solo nei dati (INV-4).
Schermata: agentdeck/components/claude_version.py. Documentazione: docs/claude-code.md.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Optional

from . import claude_probe

HOME = Path(os.environ.get("HOME", "/home/agent"))
LINK = HOME / ".local" / "bin" / "claude"
VERSIONS = HOME / ".local" / "share" / "claude" / "versions"
MANAGED = Path("/etc/claude-code/managed-settings.json")
PIN = Path("/etc/claude-code/managed-settings.d/50-agentdeck-versione.json")
RELEASES = "https://downloads.claude.ai/claude-code-releases"
SEMVER = re.compile(r"[0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,6}")
TAIL = 3000


class VersionError(Exception):
    def __init__(self, code: str, detail: Optional[dict] = None):
        super().__init__(code)
        self.code, self.detail = code, detail or {}


def _key(version: str) -> tuple:
    return tuple(int(x) for x in version.split("."))


class System:
    """Le operazioni reali. I test usano un finto con gli stessi metodi."""

    def run(self, argv: list, timeout: float = 300) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired) as e:
            return subprocess.CompletedProcess(argv, 124, "", str(e))

    def fetch(self, channel: str) -> Optional[str]:
        try:
            with urllib.request.urlopen(f"{RELEASES}/{channel}", timeout=10) as r:
                text = r.read(64).decode().strip()
            return text if SEMVER.fullmatch(text) else None
        except (OSError, ValueError):
            return None

    def probe(self, binary: Path) -> dict:
        return claude_probe.probe(binary)


class ClaudeVersions:
    def __init__(self, system: Optional[System] = None, link: Path = LINK, versions: Path = VERSIONS,
                 managed: Path = MANAGED, pin: Path = PIN):
        self.sys = system or System()
        self.link, self.versions, self.managed, self.pin_file = link, versions, managed, pin

    # ---- Lettura

    def active(self) -> Optional[str]:
        try:
            name = Path(os.readlink(self.link)).name
        except OSError:
            return None
        return name if SEMVER.fullmatch(name) else None

    def on_disk(self) -> list:
        if not self.versions.is_dir():
            return []
        return sorted((p.name for p in self.versions.iterdir() if SEMVER.fullmatch(p.name)), key=_key, reverse=True)

    def pinned(self) -> Optional[str]:
        try:
            value = json.loads(self.pin_file.read_text()).get("requiredMaximumVersion")
        except (OSError, ValueError, AttributeError):
            return None
        return value if isinstance(value, str) and SEMVER.fullmatch(value) else None

    def autoupdater_disabled(self) -> bool:
        try:
            env = json.loads(self.managed.read_text()).get("env") or {}
        except (OSError, ValueError, AttributeError):
            return False
        return str(env.get("DISABLE_AUTOUPDATER", "")) in ("1", "true")

    def state(self, remote: bool = True) -> dict:
        active, pinned = self.active(), self.pinned()
        available = {"latest": self.sys.fetch("latest"), "stable": self.sys.fetch("stable")} if remote else {}
        return {"active": active, "pinned": pinned, "on_disk": self.on_disk(),
                "autoupdater_disabled": self.autoupdater_disabled(), "pin_matches": active is not None
                and active == pinned, "available": available, "pin_file": str(self.pin_file)}

    def previous(self) -> Optional[str]:
        active = self.active()
        older = [v for v in self.on_disk() if v != active]
        return older[0] if older else None

    # ---- Scrittura

    def write_pin(self, version: str) -> None:
        content = json.dumps({"requiredMaximumVersion": version}, indent=2) + "\n"
        out = self.sys.run(["sudo", "-n", "sh", "-c", 'install -d -m 0755 "$(dirname "$1")" && printf "%s" "$2" > '
                            '"$1.tmp" && chmod 0644 "$1.tmp" && mv -f "$1.tmp" "$1"', "sh", str(self.pin_file),
                            content])
        if out.returncode != 0:
            raise VersionError("PIN_FAILED", {"output": (out.stderr or out.stdout)[-TAIL:]})

    def _relink(self, version: str) -> bool:
        target = self.versions / version
        out = self.sys.run(["sh", "-c", 'ln -sfn "$1" "$2.tmp" && mv -T "$2.tmp" "$2"', "sh", str(target),
                            str(self.link)])
        return out.returncode == 0

    def pin_active(self) -> dict:
        """Fissa la versione attiva: il passo di deck release e l'azione pin."""
        active = self.active()
        if active is None:
            raise VersionError("NO_ACTIVE", {"link": str(self.link)})
        self.write_pin(active)
        return {"pinned": active}

    def switch(self, version: str, snapshot) -> dict:
        """Passa a version (scaricandola se manca), prova gli agganci, torna indietro se la prova fallisce."""
        if not SEMVER.fullmatch(version):
            raise VersionError("BAD_VERSION", {"version": version})
        before, before_pin = self.active(), self.pinned()
        if version == before:
            raise VersionError("ALREADY_ACTIVE", {"version": version})
        snap = snapshot(f"prima di passare Claude Code da {before} a {version}")
        if snap is None:
            raise VersionError("SNAPSHOT_FAILED", {"version": version})
        self.write_pin(version)
        if version in self.on_disk():
            installed = {"ok": self._relink(version), "output": "relinked a version already on disk"}
        else:
            out = self.sys.run([str(self.versions / before) if before else str(self.link), "install", version],
                               timeout=600)
            installed = {"ok": out.returncode == 0 and self.active() == version,
                         "output": (out.stdout + out.stderr)[-TAIL:]}
        probe = self.sys.probe(self.versions / version) if installed["ok"] else None
        ok = bool(probe and probe["ok"])
        result = {"from": before, "to": version, "snapshot": snap, "install": installed, "probe": probe, "ok": ok,
                  "restored": None}
        if not ok and before:
            relinked = self._relink(before)
            self.write_pin(before_pin or before)
            result["restored"] = {"version": before, "ok": relinked and self.active() == before}
        return result
