"""Installazioni a versione fissa (task O18.T3, piano punto 11): le installazioni senza versione o "latest".

Fuori da pacman ogni installazione dichiara la versione: npm, pnpm, yarn, bun e npx; pip, pipx e uv; cargo, go e gem;
immagini di docker e podman; claude install e update; script scaricati ed eseguiti (curl | sh). pacman e gli helper
AUR restano fuori: Arch è rolling e la stabilità la danno deck update e gli snapshot. Una installazione senza
versione è un errore; l'agente la può fare solo con un consenso motivato, scritto nel comando come prefisso innocuo
AGENTDECK_LATEST_OK="<motivo>", che la guardia registra. Come access.py è una guardia, non un sandbox: in dubbio
lascia passare. La usano claude/guard.py sui comandi Bash e components/term.py sui programmi interattivi.
Documentazione: docs/claude-code.md (guardia).
"""
from __future__ import annotations

import json
import re
import shlex
from datetime import datetime
from pathlib import Path
from typing import Optional

CONSENT = re.compile(r"\bAGENTDECK_LATEST_OK=(?:\"([^\"]*)\"|'([^']*)'|(\S*))")
CONSENT_MIN = 10
FLOATING = {"", "latest", "next", "stable", "*", "x", "canary", "nightly", "beta"}
SEPARATORS = re.compile(r"\|\||&&|[;|\n&]")
PIPED_SCRIPT = re.compile(r"\b(?:curl|wget)\b[^|;&\n]*\|\s*(?:sudo\s+(?:-\S+\s+)*)?(?:env\s+\S+=\S+\s+)*"
                          r"(?:ba|z|da|k)?sh\b|\b(?:curl|wget)\b[^|;&\n]*\|\s*(?:sudo\s+)?python[0-9.]*\b|"
                          r"\b(?:ba|z)?sh\s+(?:-c\s+)?[\"']?\$\(\s*(?:curl|wget)\b|<\(\s*(?:curl|wget)\b")
PREFIXES = {"sudo", "env", "time", "nice", "nohup", "command", "exec", "doas"}
VALUE_OPTIONS = {
    # opzioni con un valore, così il valore non si scambia per un pacchetto o un'immagine
    "npm": {"--prefix", "--registry", "-C", "--cwd", "--tag", "--workspace", "-w", "--cache"},
    "pip": {"-r", "--requirement", "-c", "--constraint", "-e", "--editable", "-t", "--target", "-i", "--index-url",
            "--extra-index-url", "-f", "--find-links", "--prefix", "--root", "--python", "-p", "--cache-dir"},
    "container": {"-v", "--volume", "-p", "--publish", "-e", "--env", "--name", "-w", "--workdir", "--network",
                  "--net", "--entrypoint", "-u", "--user", "--env-file", "--mount", "-l", "--label", "--restart",
                  "-m", "--memory", "--cpus", "-h", "--hostname", "--add-host", "--device", "--cap-add",
                  "--cap-drop", "--pull", "--platform", "--log-driver", "--log-opt", "--security-opt", "--tmpfs",
                  "--ulimit", "--shm-size", "--ipc", "--pid", "--dns", "--expose", "--health-cmd", "-a", "--attach"},
}


def _tokens(segment: str) -> list:
    try:
        words = shlex.split(segment, comments=True)
    except ValueError:
        words = segment.split()
    while words and (re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", words[0]) or words[0] in PREFIXES):
        first = words.pop(0)
        if first in ("sudo", "doas"):
            while words and words[0].startswith("-"):
                flag = words.pop(0)
                if flag in ("-u", "-g", "-C", "-D") and words:
                    words.pop(0)
    if words:
        words[0] = words[0].rsplit("/", 1)[-1]
    return words


def _args(words: list, value_options: set) -> list:
    out, skip = [], False
    for w in words:
        if skip:
            skip = False
            continue
        if w.startswith("-"):
            if w in value_options:
                skip = True
            continue
        out.append(w)
    return out


def _local(spec: str) -> bool:
    return spec.startswith((".", "/", "~", "file:", "git+", "git:", "http:", "https:", "github:")) or \
        spec.endswith((".tgz", ".tar.gz", ".whl", ".zip", ".gem", ".crate"))


def _js_unpinned(spec: str) -> bool:
    if _local(spec):
        return False
    if spec.startswith("@"):
        _, _, version = spec[1:].partition("@")
    else:
        if "/" in spec:  # utente/repo di GitHub: il ramo di default
            return "#" not in spec
        _, _, version = spec.partition("@")
    return version.lower() in FLOATING


def _py_unpinned(spec: str) -> bool:
    if _local(spec) or ("@" in spec and "://" in spec):  # riferimento diretto: nome @ url
        return False
    return "==" not in spec


def _image_unpinned(image: str) -> bool:
    if "@sha256:" in image:
        return False
    last = image.rsplit("/", 1)[-1]
    _, _, tag = last.partition(":")
    return tag.lower() in FLOATING


def _segment(words: list) -> Optional[str]:
    if not words:
        return None
    prog, rest = words[0], words[1:]
    if prog in ("python", "python3") and rest[:2] == ["-m", "pip"]:
        prog, rest = "pip", rest[2:]
    if prog in ("npm", "pnpm", "yarn", "bun"):
        if rest and rest[0] in ("dlx", "x") and prog in ("pnpm", "yarn", "bun"):
            args = _args(rest[1:], VALUE_OPTIONS["npm"])
            if args and _js_unpinned(args[0]):
                return f"{prog} {rest[0]} {args[0]} without a version"
            return None
        if rest and rest[0] in ("install", "i", "add", "global"):
            pkgs = _args(rest[1:] if rest[0] != "global" else rest[2:], VALUE_OPTIONS["npm"])
            bad = [p for p in pkgs if _js_unpinned(p)]
            if bad:
                return f"{prog} {rest[0]} {' '.join(bad)} without a version"
        if rest and rest[0] in ("update", "upgrade", "up") and prog in ("npm", "pnpm", "yarn", "bun"):
            return f"{prog} {rest[0]} moves packages to newer versions"
        return None
    if prog in ("npx", "bunx", "pnpx"):
        args = _args(rest, VALUE_OPTIONS["npm"] | {"-p", "--package"})
        packages = [rest[i + 1] for i, w in enumerate(rest[:-1]) if w in ("-p", "--package")]
        targets = packages or args[:1]
        bad = [p for p in targets if _js_unpinned(p)]
        if bad:
            return f"{prog} {' '.join(bad)} without a version"
        return None
    if prog in ("pip", "pip3", "pipx") or (prog == "uv" and rest[:1] in (["pip"], ["add"], ["tool"])):
        if prog == "uv":
            rest = rest[1:] if rest[0] in ("pip", "tool") else rest
            if rest[:1] == ["add"]:
                rest = ["install"] + rest[1:]
        if rest[:1] in (["install"], ["inject"]):
            if "-U" in rest or "--upgrade" in rest:
                pkgs = _args(rest[1:], VALUE_OPTIONS["pip"])
                if pkgs and any(_py_unpinned(p) for p in pkgs):
                    return f"{prog} install --upgrade without fixed versions"
            pkgs = _args(rest[1:], VALUE_OPTIONS["pip"])
            bad = [p for p in pkgs if _py_unpinned(p)]
            if bad:
                return f"{prog} install {' '.join(bad)} without ==version"
        if rest[:1] in (["upgrade"], ["upgrade-all"]) and prog == "pipx":
            return "pipx upgrade moves packages to newer versions"
        return None
    if prog == "cargo" and rest[:1] == ["install"]:
        if any(w in ("--version", "--vers", "--path", "--git") or w.startswith(("--version=", "--vers=", "--path=",
                                                                                     "--git="))
               for w in rest):
            return None
        crates = _args(rest[1:], {"--root", "--registry", "--index", "-j", "--jobs", "--target", "--features",
                                  "-F", "--profile", "--bin", "--example"})
        bad = [c for c in crates if "@" not in c or c.split("@", 1)[1].lower() in FLOATING]
        return f"cargo install {' '.join(bad)} without a version" if bad else None
    if prog == "go" and rest[:1] == ["install"]:
        mods = [m for m in _args(rest[1:], {"-o", "-tags", "-ldflags", "-gcflags"}) if not m.startswith(".")]
        bad = [m for m in mods if "@" not in m or m.split("@", 1)[1].lower() in FLOATING]
        return f"go install {' '.join(bad)} without a version" if bad else None
    if prog == "gem" and rest[:1] in (["install"], ["update"]):
        if rest[0] == "update":
            return "gem update moves gems to newer versions"
        if any(w in ("-v", "--version") or w.startswith("--version=") for w in rest):
            return None
        gems = [g for g in _args(rest[1:], {"-i", "--install-dir", "-n", "--bindir", "-s", "--source"})
                if not _local(g)]
        return f"gem install {' '.join(gems)} without -v" if gems else None
    if prog in ("docker", "podman"):
        if rest[:1] == ["pull"]:
            images = _args(rest[1:], {"--platform"})
        elif rest[:1] in (["run"], ["create"]) or rest[:2] in (["container", "run"], ["container", "create"]):
            start = 2 if rest[0] == "container" else 1
            images = _args(rest[start:], VALUE_OPTIONS["container"])[:1]
        else:
            return None
        bad = [i for i in images if _image_unpinned(i)]
        return f"{prog} image {' '.join(bad)} without a fixed tag" if bad else None
    if prog == "claude" and rest[:1] in (["install"], ["update"], ["upgrade"]):
        target = _args(rest[1:], set())
        if rest[0] in ("update", "upgrade") or not target or target[0].lower() in FLOATING:
            return f"claude {' '.join(rest[:2])} changes the pinned Claude Code; use `deck claude/version switch`"
    return None


HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


def strip_heredocs(command: str) -> str:
    """Toglie il corpo degli heredoc: è testo passato a un programma, non comandi della shell."""
    lines, out, end = command.split("\n"), [], None
    for line in lines:
        if end is not None:
            if line.strip() == end:
                end = None
            continue
        out.append(line)
        m = HEREDOC.search(line)
        if m:
            end = m.group(2)
    return "\n".join(out)


def check(command: str) -> Optional[str]:
    """Il motivo per cui il comando installa senza versione fissa, o None."""
    command = strip_heredocs(command)
    if PIPED_SCRIPT.search(command):
        return "a downloaded script piped into a shell or interpreter installs whatever version is published today"
    for segment in SEPARATORS.split(command):
        reason = _segment(_tokens(segment))
        if reason:
            return reason
    return None


def consent(command: str) -> Optional[str]:
    """Il motivo del consenso dell'agente scritto nel comando, se c'è ed è abbastanza lungo."""
    m = CONSENT.search(command)
    if not m:
        return None
    reason = next((g for g in m.groups() if g is not None), "").strip()
    return reason if len(reason) >= CONSENT_MIN else None


def record(path: Path, command: str, reason: str, why: str, session: Optional[str] = None) -> None:
    """Registra un consenso: chi lo legge dopo vede comando, motivo dichiarato e cosa la regola aveva visto."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(json.dumps({"time": datetime.now().astimezone().isoformat(timespec="seconds"),
                                "session": session, "rule": why, "consent": reason,
                                "command": command[:2000]}, ensure_ascii=False) + "\n")
    except OSError:
        pass
