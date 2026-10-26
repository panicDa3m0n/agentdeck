"""Obblighi del sistema verso l'agente (O10.T8): i doveri che AgentDeck impone, per ora solo come avvisi.

È il paradigma deciso il 25/10 (architettura 7.4 bis): l'agente è uno strumento, e il sistema lo usa per il proprio
funzionamento corretto. Un obbligo nasce da un evento del sistema e resta aperto finché è soddisfatto (il sistema
lo chiude da sé quando può verificarlo), finché l'agente lo dichiara fatto, o finché lo scarta dicendo perché.
Oggi l'evento è l'installazione di un pacchetto, segnalata dall'hook di pacman (system/95-agentdeck-obligations.hook):
ogni programma nuovo deve avere il suo profilo dell'adattatore (PROFILE_NEEDED).

Ogni schermata di deck porta gli obblighi aperti nel campo obligations (protocollo, sezione 6 bis). I messaggi nascono
dai modelli scritti qui (INV-4): nomi di pacchetti e programmi stanno nei dati dell'obbligo.
Stato: $XDG_STATE_HOME/agentdeck/obligations.json. Documentazione: docs/obblighi.md.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import term
from .protocol import SysText, sys_text

PACKAGE = re.compile(r"[a-z0-9@_+][a-z0-9@._+-]{0,127}")
OID = re.compile(r"[0-9a-f]{6}")
STATUSES = ("open", "done", "dismissed")
SCREEN_LIMIT = 5
KEEP_CLOSED = 50

CODES = {
    "PROFILE_NEEDED": {
        "level": "warning",
        "action": {"path": "/term", "action": "profile_save"},
        "template": ("Package {package} installed programs without an adapter profile (obligation {id}). For each "
                     "program in its subject.programs that asks questions, write a profile with `deck term "
                     "profile_save`; then close it with `deck obligations done id={id}` and a note on the programs "
                     "that ask nothing."),
        "template_unnamed": ("A package installed programs without an adapter profile (obligation {id}): see "
                             "`deck obligations show id={id}`."),
    },
}


def _store() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "agentdeck" / "obligations.json"


def pacman_local() -> Path:
    return Path(os.environ.get("AGENTDECK_PACMAN_LOCAL", "/var/lib/pacman/local"))


def load() -> list:
    try:
        items = json.loads(_store().read_text()).get("items", [])
    except (OSError, ValueError, AttributeError):
        return []
    return [i for i in items if isinstance(i, dict) and i.get("code") in CODES and i.get("status") in STATUSES
            and isinstance(i.get("id"), str) and OID.fullmatch(i["id"])]


def save(items: list) -> None:
    opened = [i for i in items if i["status"] == "open"]
    closed = sorted((i for i in items if i["status"] != "open"), key=lambda i: i.get("updated", 0))[-KEEP_CLOSED:]
    store = _store()
    store.parent.mkdir(parents=True, exist_ok=True)
    tmp = store.with_suffix(".tmp")
    tmp.write_text(json.dumps({"version": 1, "items": opened + closed}, ensure_ascii=False, indent=1))
    tmp.replace(store)


def _id(code: str, key: str) -> str:
    return hashlib.sha256(f"{code}:{key}".encode()).hexdigest()[:6]


def message(item: dict) -> SysText:
    spec = CODES[item["code"]]
    package = (item.get("subject") or {}).get("package")
    if isinstance(package, str) and PACKAGE.fullmatch(package) and len(package) <= 64:
        return sys_text(spec["template"], package=package, id=item["id"])
    return sys_text(spec["template_unnamed"], id=item["id"])


def iso(ts) -> Optional[str]:
    return None if ts is None else datetime.fromtimestamp(ts).astimezone().isoformat(timespec="seconds")


# pacchetti e programmi

def _package_dir(package: str) -> Optional[Path]:
    local = pacman_local()
    for d in sorted(local.glob(f"{package}-*")):
        try:
            desc = (d / "desc").read_text()
        except OSError:
            continue
        if re.search(rf"^%NAME%\n{re.escape(package)}$", desc, re.MULTILINE):
            return d
    return None


def package_programs(package: str) -> Optional[list]:
    """I programmi che il pacchetto installa in /usr/bin, dal database locale di pacman; None se non è installato."""
    d = _package_dir(package)
    if d is None:
        return None
    try:
        files = (d / "files").read_text().split("%FILES%\n", 1)[-1].split("\n\n", 1)[0].splitlines()
    except OSError:
        return []
    names = {Path(f).name for f in files if f.startswith("usr/bin/") and not f.endswith("/")}
    return sorted(n for n in names if term.PROGRAM.fullmatch(n.lower()))


def _missing_profiles(programs: list) -> list:
    return [p for p in programs if term.load_profile(p.lower())[0] is None]


# ciclo di vita

def resolve(items: list, now: Optional[float] = None) -> bool:
    """Chiude da sé gli obblighi che il sistema può verificare come soddisfatti. True se qualcosa è cambiato."""
    now = now or time.time()
    changed = False
    for item in items:
        if item["status"] != "open" or item["code"] != "PROFILE_NEEDED":
            continue
        subject = item.get("subject") or {}
        programs = package_programs(subject.get("package", ""))
        if programs is None:
            item.update(status="done", updated=now, resolved_by="package_removed")
            changed = True
        elif not _missing_profiles(subject.get("programs", [])):
            item.update(status="done", updated=now, resolved_by="profiles_written")
            changed = True
    return changed


def open_items() -> list:
    items = load()
    if resolve(items):
        save(items)
    return [i for i in items if i["status"] == "open"]


def for_screen() -> list:
    """Gli obblighi aperti come compaiono in ogni schermata: al più SCREEN_LIMIT, i più recenti, più un riepilogo."""
    try:
        opened = sorted(open_items(), key=lambda i: i.get("created", 0), reverse=True)
    except Exception:  # un archivio guasto non deve togliere la schermata
        return []
    shown = [{"id": i["id"], "code": i["code"], "level": CODES[i["code"]]["level"], "message": message(i),
              "action": dict(CODES[i["code"]]["action"])} for i in opened[:SCREEN_LIMIT]]
    if len(opened) > SCREEN_LIMIT:
        shown.append({"id": "more", "code": "OBLIGATIONS_MORE", "level": "info",
                      "message": sys_text("{n} more open obligations: open `deck obligations`.",
                                          n=len(opened) - SCREEN_LIMIT),
                      "action": {"path": "/obligations", "action": None}})
    return shown


def add_installed(packages: list, now: Optional[float] = None) -> list:
    """Dopo un'installazione: un obbligo PROFILE_NEEDED per ogni pacchetto con programmi senza profilo."""
    now = now or time.time()
    items = load()
    by_id = {i["id"]: i for i in items}
    created = []
    for package in packages:
        if not PACKAGE.fullmatch(package):
            continue
        programs = package_programs(package)
        if not programs:
            continue
        missing = _missing_profiles(programs)
        if not missing:
            continue
        oid = _id("PROFILE_NEEDED", package)
        existing = by_id.get(oid)
        if existing is not None:
            if existing["status"] == "open":
                existing["subject"]["programs"] = missing
                existing["updated"] = now
            continue  # già fatto o scartato: reinstallare non lo riapre
        item = {"id": oid, "code": "PROFILE_NEEDED", "status": "open", "created": now, "updated": now,
                "source": "pacman", "subject": {"package": package, "programs": missing}, "note": None,
                "resolved_by": None}
        items.append(item)
        by_id[oid] = item
        created.append(item)
    save(items)
    return created


def close(oid: str, status: str, note: Optional[str], now: Optional[float] = None) -> Optional[dict]:
    items = load()
    for item in items:
        if item["id"] == oid:
            item.update(status=status, note=note, updated=now or time.time(),
                        resolved_by="agent" if status == "done" else "agent_dismissed")
            save(items)
            return item
    return None


def public(item: dict) -> dict:
    """Un obbligo per i dati di una schermata: le date in ISO 8601."""
    out = {k: v for k, v in item.items() if k not in ("created", "updated")}
    out.update(created=iso(item.get("created")), updated=iso(item.get("updated")),
               level=CODES[item["code"]]["level"], action=dict(CODES[item["code"]]["action"]))
    return out
