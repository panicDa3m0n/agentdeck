"""Versioni di AgentDeck installate dal repository della Deck stessa (task O18.T1, piano punto 10).

Ogni versione si estrae da un commit di ~/agentdeck/repo in una cartella sua, /opt/agentdeck-versioni/<versione>-<commit>,
e /opt/agentdeck diventa un collegamento simbolico a quella attiva: installare e tornare indietro sono lo scambio
atomico del collegamento (mv --exchange), così guardia e hook delle sessioni, che girano da /opt/agentdeck, non
vedono mai una cartella a metà. Installare: estrazione, test nella copia, snapshot, scambio, passi di sistema
(comando deck, hook di pacman, unità delle sessioni, configurazione di Claude Code), eseguiti dal codice della
versione nuova, verifica; se la verifica
fallisce si torna da soli alla versione di prima. agentdeck-claude non si riavvia: la configurazione nuova vale per
le sessioni aperte dopo. Schermo (screen/) e interfaccia grafica (ui/) non si installano da qui: install-screen.sh
tocca la configurazione SSH e serve una procedura con verifica dell'accesso (INV-1); se cambiano, l'installazione
si rifiuta. Uscite di git e dei test sono testo esterno: solo nei dati (INV-4).
Schermata: agentdeck/components/release.py. Documentazione: docs/sviluppo.md, docs/deck.md.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

HOME = Path(os.environ.get("HOME", "/home/agent"))
REPO = HOME / "agentdeck" / "repo"
BASE = Path("/opt/agentdeck-versioni")
CURRENT = Path("/opt/agentdeck")
NEXT = Path("/opt/agentdeck.next")
CLAUDE_BIN = HOME / ".local" / "bin" / "claude"
INSTALLED_CLAUDE_MD = Path("/etc/claude-code/CLAUDE.md")
PIN = Path("/etc/claude-code/managed-settings.d/50-agentdeck-versione.json")  # agentdeck/claude_version.py
KEEP = 5
COMMIT = re.compile(r"[0-9a-f]{7,40}")
RELEASE_ID = re.compile(r"[0-9A-Za-z._-]{1,64}")
INFO = "RELEASE.json"
MANUAL = ("screen", "ui")  # cartelle che richiedono una procedura propria
TAIL = 3000


class ReleaseError(Exception):
    def __init__(self, code: str, detail: Optional[dict] = None):
        super().__init__(code)
        self.code, self.detail = code, detail or {}


def _tail(text: str) -> str:
    return (text or "")[-TAIL:]


class System:
    """Le operazioni reali. I test usano un finto con gli stessi metodi."""

    def run(self, argv: list, timeout: float = 120, cwd: Optional[Path] = None,
            stdin: Optional[str] = None) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, cwd=cwd, input=stdin)
        except (OSError, subprocess.TimeoutExpired) as e:
            return subprocess.CompletedProcess(argv, 124, "", str(e))

    def now(self) -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")


class Releases:
    def __init__(self, system: Optional[System] = None, repo: Path = REPO, base: Path = BASE,
                 current: Path = CURRENT, next_link: Path = NEXT, installed_claude_md: Path = INSTALLED_CLAUDE_MD):
        self.sys = system or System()
        self.repo, self.base, self.current, self.next = repo, base, current, next_link
        self.installed_claude_md = installed_claude_md

    # ---- Lettura

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return self.sys.run(["git", "-C", str(self.repo), *args], timeout=60)

    def repo_state(self) -> dict:
        head = self._git("rev-parse", "HEAD")
        if head.returncode != 0:
            return {"path": str(self.repo), "available": False, "output": _tail(head.stderr)}
        commit = head.stdout.strip()
        version = self._git("show", f"{commit}:VERSION")
        dirty = self._git("status", "--porcelain", "--untracked-files=no")
        subject = self._git("log", "-1", "--format=%s", commit)
        return {"path": str(self.repo), "available": True, "commit": commit, "short": commit[:7],
                "version": version.stdout.strip() if version.returncode == 0 else None,
                "subject": subject.stdout.strip(), "uncommitted_changes": bool(dirty.stdout.strip())}

    @staticmethod
    def _info(folder: Path) -> dict:
        try:
            return json.loads((folder / INFO).read_text())
        except (OSError, ValueError):
            pass
        version = None
        try:
            version = (folder / "VERSION").read_text().strip()
        except OSError:
            pass
        return {"version": version, "commit": None, "installed_at": None, "source": "legacy"}

    def active(self) -> dict:
        """La versione attiva: il collegamento /opt/agentdeck, o la cartella di prima di O18.T1."""
        if self.current.is_symlink():
            target = Path(os.readlink(self.current))
            info = self._info(target)
            return {"id": target.name, "path": str(target), "layout": "link", **info}
        if self.current.is_dir():
            return {"id": None, "path": str(self.current), "layout": "folder", **self._info(self.current)}
        return {"id": None, "path": str(self.current), "layout": "missing", "version": None, "commit": None,
                "installed_at": None, "source": None}

    def history(self) -> list:
        """Le versioni conservate, dalla più recente installata; active segna quella in uso."""
        if not self.base.is_dir():
            return []
        active = self.active()
        items = []
        for folder in self.base.iterdir():
            if not folder.is_dir() or folder.name.startswith("."):
                continue
            info = self._info(folder)
            items.append({"id": folder.name, "path": str(folder), "version": info.get("version"),
                          "commit": info.get("commit"), "installed_at": info.get("installed_at"),
                          "source": info.get("source"), "active": str(folder) == active["path"]})
        items.sort(key=lambda r: r["installed_at"] or "", reverse=True)
        return items

    def previous(self) -> Optional[dict]:
        """La versione installata prima di quella attiva: il bersaglio predefinito di revert."""
        return next((r for r in self.history() if not r["active"] and r["installed_at"]), None)

    @staticmethod
    def _digest(folder: Path, sub: str) -> Optional[str]:
        root = folder / sub
        if not root.is_dir():
            return None
        h = hashlib.sha256()
        for path in sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
            h.update(str(path.relative_to(root)).encode())
            h.update(path.read_bytes())
        return h.hexdigest()

    def manual_changes(self, new: Path) -> list:
        """Le cartelle che cambiano rispetto alla versione attiva e che da qui non si installano."""
        old = Path(self.active()["path"])
        return [sub for sub in MANUAL if self._digest(old, sub) != self._digest(new, sub)]

    def changed_files(self, commit: str) -> list:
        """I file di deck/ cambiati fra il commit attivo e quello da installare (se il primo è noto)."""
        old = self.active().get("commit")
        if not old:
            return []
        out = self._git("diff", "--name-only", old, commit, "--", "deck", "VERSION")
        return out.stdout.split() if out.returncode == 0 else []

    # ---- Estrazione e prove

    def resolve(self, ref: str) -> str:
        out = self._git("rev-parse", "--verify", f"{ref}^{{commit}}")
        if out.returncode != 0:
            raise ReleaseError("NO_COMMIT", {"ref": ref, "output": _tail(out.stderr)})
        return out.stdout.strip()

    def extract(self, commit: str) -> Path:
        """Estrae deck/ e VERSION del commit in una cartella nuova; genera CLAUDE.md con le invarianti del commit."""
        version = self._git("show", f"{commit}:VERSION").stdout.strip() or "dev"
        folder = self.base / f"{version}-{commit[:7]}"
        if str(folder) == self.active()["path"]:
            raise ReleaseError("ALREADY_ACTIVE", {"release": folder.name})  # mai riscrivere la cartella in uso
        staging = self.base / f".staging-{commit[:7]}"
        steps = [
            ["sudo", "-n", "install", "-d", "-o", "agent", "-g", "agent", str(self.base)],
            ["rm", "-rf", str(staging)],
            ["mkdir", "-p", str(staging)],
        ]
        for argv in steps:
            out = self.sys.run(argv)
            if out.returncode != 0:
                raise ReleaseError("EXTRACT_FAILED", {"step": argv, "output": _tail(out.stderr)})
        archive = self.sys.run(["sh", "-c", 'git -C "$1" archive "$2" deck VERSION .claude/workflow/invariants.json '
                                            '| tar -x -C "$3"', "sh", str(self.repo), commit, str(staging)])
        if archive.returncode != 0:
            raise ReleaseError("EXTRACT_FAILED", {"step": "git archive", "output": _tail(archive.stderr)})
        claude_md = self.sys.run(["python3", str(staging / "deck" / "claude" / "build_claude_md.py"), str(staging)])
        if claude_md.returncode != 0:
            raise ReleaseError("EXTRACT_FAILED", {"step": "build_claude_md.py", "output": _tail(claude_md.stderr)})
        info = {"version": version, "commit": commit, "installed_at": None, "source": str(self.repo)}
        script = ('set -e; cd "$1"; cp VERSION deck/VERSION; printf "%s" "$3" > deck/claude/CLAUDE.md; '
                  'printf "%s\\n" "$4" > deck/RELEASE.json; rm -rf "$2"; mv deck "$2"; cd /; rm -rf "$1"')
        out = self.sys.run(["sh", "-c", script, "sh", str(staging), str(folder), claude_md.stdout, json.dumps(info)])
        if out.returncode != 0:
            raise ReleaseError("EXTRACT_FAILED", {"step": "move", "output": _tail(out.stderr)})
        return folder

    def test(self, folder: Path) -> dict:
        out = self.sys.run(["python3", "-m", "unittest", "discover", "-s", "tests", "-q"], timeout=600, cwd=folder)
        return {"ok": out.returncode == 0, "output": _tail(out.stderr + out.stdout)}

    # ---- Scambio, passi di sistema, verifica

    def switch(self, folder: Path) -> dict:
        """Rende attiva la cartella con uno scambio atomico; la cartella di prima di O18.T1 entra fra le versioni."""
        legacy = self.current.is_dir() and not self.current.is_symlink()
        # la cartella di prima non ha il CLAUDE.md generato: si conserva quello installato, per poterci tornare
        script = ('set -e; rm -f "$2"; ln -s "$1" "$2"; mv -T --exchange "$2" "$3"; '
                  'if [ -L "$2" ]; then rm -f "$2"; else mv -T "$2" "$4"; '
                  'if [ -f "$5" ] && [ ! -f "$4/claude/CLAUDE.md" ]; then cp "$5" "$4/claude/CLAUDE.md"; fi; fi')
        legacy_dest = self.base / f"{self._info(self.current).get('version') or 'dev'}-prima"
        out = self.sys.run(["sudo", "-n", "sh", "-c", script, "sh", str(folder), str(self.next), str(self.current),
                            str(legacy_dest), str(self.installed_claude_md)])
        if out.returncode != 0:
            raise ReleaseError("SWITCH_FAILED", {"output": _tail(out.stderr)})
        if legacy:
            self._mark(legacy_dest, source="legacy", installed_at="0000-legacy")
        return {"active": str(folder), "legacy_kept": str(legacy_dest) if legacy else None}

    def _mark(self, folder: Path, source: Optional[str] = None, installed_at: Optional[str] = None) -> None:
        info = self._info(folder)
        info["installed_at"] = installed_at or self.sys.now()
        if source:
            info["source"] = source
        self.sys.run(["sudo", "-n", "sh", "-c", 'printf "%s\\n" "$2" > "$1/RELEASE.json"; chown -R agent:agent "$1"',
                      "sh", str(folder), json.dumps(info)])

    def apply(self) -> list:
        """I passi di sistema della versione attiva, letti da /opt/agentdeck. Ognuno con esito e uscita."""
        cur = str(self.current)
        settings = ('import json, pathlib\n'
                    'p = pathlib.Path.home() / ".claude" / "settings.json"\n'
                    's = json.loads(p.read_text()) if p.exists() else {}\n'
                    's["outputStyle"] = "AgentDeck"\n'
                    's["skipDangerousModePermissionPrompt"] = True\n'
                    's.setdefault("permissions", {})["defaultMode"] = "bypassPermissions"\n'
                    'p.parent.mkdir(parents=True, exist_ok=True)\n'
                    'p.write_text(json.dumps(s, indent=2) + "\\n")\n')
        skills = ('set -e; src="$1/claude/skills"; dst="$HOME/.claude/skills"; mkdir -p "$dst"; '
                  'for d in "$dst"/agentdeck-*/; do [ -d "$d" ] || continue; '
                  '[ -d "$src/$(basename "$d")" ] || rm -rf "$d"; done; '
                  'for d in "$src"/*/; do n=$(basename "$d"); rm -rf "$dst/$n"; cp -r "$d" "$dst/$n"; done')
        steps = [
            ("deck command", ["sudo", "-n", "sh", "-c",
                              f'chmod +x {cur}/deck && ln -sfn {cur}/deck /usr/local/bin/deck']),
            ("pacman hook", ["sudo", "-n", "sh", "-c",
                             f'install -D -m 0755 -o root -g root {cur}/system/obligations-hook.sh '
                             f'/usr/local/lib/agentdeck/obligations-hook.sh && install -D -m 0644 '
                             f'{cur}/system/95-agentdeck-obligations.hook /etc/pacman.d/hooks/95-agentdeck-obligations.hook']),
            ("session unit", ["sudo", "-n", "sh", "-c",
                              f'install -m 0644 {cur}/claude/agentdeck-sessione@.service /etc/systemd/system/ '
                              f'&& systemctl daemon-reload']),
            # l'intermediario dell'agente interno (O20.T1): riavviato perché usi il codice della versione attiva
            ("agent proxy", ["sudo", "-n", "sh", "-c",
                             f'test ! -f {cur}/claude/agentdeck-agente-proxy.service || '
                             f'(install -d -o agent -g agent /home/agent/.local/state/agentdeck && '
                             f'install -m 0644 {cur}/claude/agentdeck-agente-proxy.service /etc/systemd/system/ && '
                             f'systemctl daemon-reload && systemctl enable agentdeck-agente-proxy.service && '
                             f'systemctl restart agentdeck-agente-proxy.service)']),
            ("claude managed", ["sudo", "-n", "sh", "-c",
                                f'python3 -m json.tool {cur}/claude/managed-settings.json >/dev/null && '
                                f'install -d -m 0755 /etc/claude-code && '
                                f'install -m 0644 {cur}/claude/CLAUDE.md /etc/claude-code/CLAUDE.md && '
                                f'install -m 0644 {cur}/claude/managed-settings.json /etc/claude-code/managed-settings.json']),
            ("claude output style", ["sh", "-c", f'install -D -m 0644 {cur}/claude/output-styles/agentdeck.md '
                                                 f'"$HOME/.claude/output-styles/agentdeck.md"']),
            ("claude user settings", ["python3", "-c", settings]),
            ("claude skills", ["sh", "-c", skills, "sh", cur]),
            ("claude version pin", ["sh", "-c", f'test -f {PIN} || {cur}/deck claude/version pin >/dev/null']),
            ("claude mcp", ["sh", "-c", f'"$1" mcp get deck >/dev/null 2>&1 || '
                                        f'"$1" mcp add --transport stdio --scope user deck -- /usr/local/bin/deck mcp',
                            "sh", str(CLAUDE_BIN)]),
        ]
        results = []
        for name, argv in steps:
            out = self.sys.run(argv, timeout=120)
            results.append({"step": name, "ok": out.returncode == 0, "output": _tail(out.stderr + out.stdout)})
            if out.returncode != 0:
                break
        return results

    def apply_active(self) -> list:
        """I passi di sistema eseguiti dal codice della versione attiva, così valgono subito anche i passi nuovi;
        una versione senza release.py (la cartella di prima di O18.T1) usa quelli di chi chiama."""
        if not (self.current / "agentdeck" / "release.py").is_file():
            return self.apply()
        code = ("import json, sys; sys.path.insert(0, sys.argv[1]); from agentdeck import release; "
                "print(json.dumps(release.Releases().apply()))")
        out = self.sys.run(["python3", "-c", code, str(self.current)], timeout=900)
        try:
            steps = json.loads(out.stdout.strip().splitlines()[-1])
            if isinstance(steps, list):
                return steps
        except (ValueError, IndexError):
            pass
        return [{"step": "apply from the active version", "ok": False, "output": _tail(out.stderr + out.stdout)}]

    def verify(self) -> list:
        """Dopo lo scambio: deck risponde, il server MCP parte, la guardia rifiuta, sshd è attivo (INV-1)."""
        checks = []
        status = self.sys.run(["/usr/local/bin/deck", "status"], timeout=60)
        try:
            ok = json.loads(status.stdout).get("status") == "ok"
        except ValueError:
            ok = False
        checks.append({"check": "deck status", "ok": ok, "output": "" if ok else _tail(status.stdout + status.stderr)})
        mcp = self.sys.run(["/usr/local/bin/deck", "mcp"], timeout=30, stdin="")
        checks.append({"check": "deck mcp", "ok": mcp.returncode == 0, "output": _tail(mcp.stderr)})
        event = json.dumps({"tool_name": "Bash", "tool_input": {"command": "sudo systemctl " + "stop sshd"}})
        guard = self.sys.run(["python3", str(self.current / "claude" / "guard.py")], timeout=30, stdin=event)
        checks.append({"check": "guard refuses cutting access", "ok": guard.returncode == 2,
                       "output": "" if guard.returncode == 2 else _tail(guard.stderr + guard.stdout)})
        sshd = self.sys.run(["systemctl", "is-active", "sshd"], timeout=30)
        checks.append({"check": "sshd active", "ok": sshd.stdout.strip() == "active", "output": sshd.stdout.strip()})
        if (self.current / "claude" / "agentdeck-agente-proxy.service").is_file():
            # l'intermediario dell'agente interno risponde (O20.T1); ritenta per qualche secondo dopo il riavvio
            proxy = self.sys.run(["sh", "-c", 'for i in 1 2 3 4 5 6 7 8 9 10; do '
                                              'curl -fsS -m 2 http://127.0.0.1:8791/health && exit 0; sleep 1; done; '
                                              'exit 1'], timeout=30)
            checks.append({"check": "agent proxy answers", "ok": proxy.returncode == 0,
                           "output": "" if proxy.returncode == 0 else _tail(proxy.stderr + proxy.stdout)})
        return checks

    def prune(self) -> list:
        """Tiene le KEEP versioni più recenti, sempre l'attiva e la precedente; le altre si tolgono."""
        history = self.history()
        prev = self.previous()
        keep = {r["id"] for r in history[:KEEP]} | {r["id"] for r in history if r["active"]}
        if prev:
            keep.add(prev["id"])
        removed = []
        for r in history:
            if r["id"] not in keep:
                if self.sys.run(["sudo", "-n", "rm", "-rf", r["path"]]).returncode == 0:
                    removed.append(r["id"])
        return removed

    # ---- Le due operazioni

    def _switch_apply_verify(self, folder: Path, back_to: Optional[Path]) -> dict:
        switched = self.switch(folder)
        steps = self.apply_active()
        checks = self.verify() if all(s["ok"] for s in steps) else []
        ok = bool(checks) and all(c["ok"] for c in checks)
        result = {"switch": switched, "steps": steps, "checks": checks, "ok": ok, "reverted": None}
        if not ok and back_to is not None:
            self.switch(back_to)
            back_steps = self.apply_active()
            back_checks = self.verify()
            result["reverted"] = {"to": str(back_to), "steps": back_steps, "checks": back_checks,
                                  "ok": all(s["ok"] for s in back_steps) and all(c["ok"] for c in back_checks)}
        return result

    def install(self, commit: str, snapshot) -> dict:
        """snapshot(descrizione) -> id o None: lo fornisce il chiamante (deck snapshot)."""
        previous = Path(self.active()["path"])
        folder = self.extract(commit)
        manual = self.manual_changes(folder)
        if manual:
            raise ReleaseError("MANUAL_PARTS", {"folders": manual, "release": str(folder)})
        tests = self.test(folder)
        if not tests["ok"]:
            raise ReleaseError("TESTS_FAILED", {"release": str(folder), "output": tests["output"]})
        snap = snapshot(f"prima di deck release install {folder.name}")
        if snap is None:
            raise ReleaseError("SNAPSHOT_FAILED", {"release": str(folder)})
        result = self._switch_apply_verify(folder, previous)
        if result["ok"]:
            self._mark(folder)
            result["pruned"] = self.prune()
        result.update({"release": folder.name, "snapshot": snap, "tests": tests})
        return result

    def revert(self, target: dict, snapshot) -> dict:
        previous = Path(self.active()["path"])
        snap = snapshot(f"prima di deck release revert a {target['id']}")
        if snap is None:
            raise ReleaseError("SNAPSHOT_FAILED", {"release": target["id"]})
        result = self._switch_apply_verify(Path(target["path"]), previous)
        if result["ok"]:
            self._mark(Path(target["path"]))
        result.update({"release": target["id"], "snapshot": snap})
        return result
