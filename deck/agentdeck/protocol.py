"""Protocollo dell'interfaccia agentica, versione 1: costruzione e validazione delle schermate.

Specifica: docs/protocollo.md. Documentazione del motore: docs/deck.md.

Il canale istruzioni (vedi INSTRUCTION_FIELDS) accetta solo SysText: testo nato da modelli scritti nel
codice, con dentro soli valori validati (INV-4). Tutto il resto, testo esterno compreso, va in data.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Optional

PROTOCOL_VERSION = 1
STATUSES = ("ok", "confirm", "done", "error")
EFFECTS = ("read", "safe", "destructive")
LEVELS = ("info", "warning", "critical")
ERROR_CODES = ("NOT_FOUND", "BAD_PARAM", "MISSING_PARAM", "NOT_AVAILABLE", "CONFIRM_INVALID", "FAILED")
PARAM_TYPES = ("string", "int", "bool", "enum")
INSTRUCTION_FIELDS = (
    "title", "prompt", "actions[].label", "actions[].reason", "actions[].params.*.description",
    "alerts[].message", "error.message", "nav.children[].title", "nav.children[].summary",
)
TOP_LEVEL = ("deck", "screen", "path", "title", "status", "data", "alerts", "actions", "nav", "prompt",
             "confirm", "error", "meta")

# Oltre ai numeri, nel canale istruzioni entrano solo identificatori senza spazi.
_SAFE_VALUE = re.compile(r"[A-Za-z0-9_./:=@+-]{1,64}")
_PATH = re.compile(r"/[a-z0-9_/-]*")
_CODE = re.compile(r"[A-Z][A-Z0-9_]*")


class UnsafeText(ValueError):
    """Un valore non validato stava per entrare nel canale istruzioni."""


class SysText(str):
    """Testo del canale istruzioni: si costruisce solo con sys_text()."""

    __slots__ = ()


def sys_text(template: str, **values: Any) -> SysText:
    """Riempie un modello scritto nel codice con valori validati: numeri o identificatori senza spazi."""
    for name, value in values.items():
        if isinstance(value, (bool, int, float, SysText)):
            continue
        if isinstance(value, str) and _SAFE_VALUE.fullmatch(value):
            continue
        raise UnsafeText(f"value {name!r} is not allowed in the instruction channel")
    return SysText(template.format(**values))


def is_path(value: str) -> bool:
    return bool(_PATH.fullmatch(value))


def _text(value: Any, where: str) -> SysText:
    if not isinstance(value, SysText):
        raise UnsafeText(f"{where} must be built with sys_text()")
    return value


def param(type_: str, *, description: SysText, required: bool = True,
          values: Optional[Iterable[str]] = None, max_length: Optional[int] = None) -> dict:
    """Specifica di un parametro di azione (protocollo, sezione 5)."""
    if type_ not in PARAM_TYPES:
        raise ValueError(f"unknown parameter type {type_!r}")
    if type_ == "enum" and not values:
        raise ValueError("enum parameters need values")
    spec: dict = {"type": type_, "required": required, "description": _text(description, "param description")}
    if values is not None:
        spec["values"] = list(values)
    if max_length is not None:
        spec["max_length"] = max_length
    return spec


def action(id_: str, *, label: SysText, effect: str, params: Optional[dict] = None,
           available: bool = True, reason: Optional[SysText] = None) -> dict:
    """Un'azione della schermata, come un pulsante (sezione 5). Le distruttive richiedono conferma."""
    if effect not in EFFECTS:
        raise ValueError(f"unknown effect {effect!r}")
    spec = {"id": id_, "label": _text(label, "action label"), "effect": effect,
            "confirm": effect == "destructive", "available": available, "params": dict(params or {})}
    if not available:
        spec["reason"] = _text(reason, "action reason")
    return spec


def alert(level: str, code: str, *, message: SysText, path: Optional[str] = None,
          action_id: Optional[str] = None) -> dict:
    """Un'anomalia rilevata dal sistema, con codice stabile (sezione 6)."""
    if level not in LEVELS:
        raise ValueError(f"unknown alert level {level!r}")
    if not _CODE.fullmatch(code):
        raise ValueError(f"alert code {code!r} is not UPPER_SNAKE_CASE")
    target = None if path is None else {"path": path, "action": action_id}
    return {"level": level, "code": code, "message": _text(message, "alert message"), "action": target}


def child(path: str, *, title: SysText, summary: SysText) -> dict:
    """Una schermata raggiungibile da quella corrente (sezione 4)."""
    return {"path": path, "title": _text(title, "child title"), "summary": _text(summary, "child summary")}


def error_info(code: str, message: SysText, field: Optional[str] = None) -> dict:
    """L'oggetto error di una schermata di errore (sezione 8)."""
    if code not in ERROR_CODES:
        raise ValueError(f"unknown error code {code!r}")
    info = {"code": code, "message": _text(message, "error message")}
    if field is not None:
        info["field"] = field
    return info


def screen(*, screen: str, path: str, title: SysText, prompt: SysText, status: str = "ok",
           data: Optional[dict] = None, alerts: Iterable[dict] = (), actions: Iterable[dict] = (),
           back: Optional[str] = None, children: Iterable[dict] = (), confirm: Optional[dict] = None,
           error: Optional[dict] = None) -> dict:
    """Costruisce una schermata (sezione 3). Il campo meta lo aggiunge il motore."""
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r}")
    result = {"deck": PROTOCOL_VERSION, "screen": screen, "path": path, "title": _text(title, "title"),
              "status": status, "data": dict(data or {}), "alerts": list(alerts), "actions": list(actions),
              "nav": {"back": back, "children": list(children)}, "prompt": _text(prompt, "prompt")}
    if confirm is not None:
        result["confirm"] = confirm
    if error is not None:
        result["error"] = error
    return result


def instruction_texts(s: dict) -> list:
    """Tutti i testi del canale istruzioni di una schermata in forma JSON (per i controlli INV-4)."""
    texts = [s.get("title"), s.get("prompt")]
    for a in s.get("actions", []):
        texts += [a.get("label"), a.get("reason")]
        texts += [p.get("description") for p in a.get("params", {}).values() if isinstance(p, dict)]
    texts += [al.get("message") for al in s.get("alerts", [])]
    texts.append((s.get("error") or {}).get("message"))
    for c in (s.get("nav") or {}).get("children", []):
        texts += [c.get("title"), c.get("summary")]
    return [t for t in texts if t is not None]


def validate(s: Any) -> list:
    """Controlla che una schermata, già in forma JSON, rispetti il protocollo. Restituisce i problemi."""
    if not isinstance(s, dict):
        return ["screen is not an object"]
    problems = []
    types = {"deck": int, "screen": str, "path": str, "title": str, "status": str, "data": dict,
             "alerts": list, "actions": list, "nav": dict, "prompt": str, "meta": dict}
    for key, kind in types.items():
        if key not in s:
            problems.append(f"missing {key}")
        elif not isinstance(s[key], kind) or (kind is int and isinstance(s[key], bool)):
            problems.append(f"{key} has the wrong type")
    problems += [f"unknown field {k}" for k in s if k not in TOP_LEVEL]
    if problems:
        return problems

    if s["deck"] != PROTOCOL_VERSION:
        problems.append("unsupported protocol version")
    if not is_path(s["path"]):
        problems.append("path is not an address")
    if s["status"] not in STATUSES:
        problems.append("unknown status")
    if (s["status"] == "error") != ("error" in s):
        problems.append("error must be present exactly when status is error")
    if (s["status"] == "confirm") != ("confirm" in s):
        problems.append("confirm must be present exactly when status is confirm")

    if "error" in s:
        e = s["error"]
        if not isinstance(e, dict) or e.get("code") not in ERROR_CODES or not isinstance(e.get("message"), str):
            problems.append("error needs a known code and a message")
    if "confirm" in s:
        c = s["confirm"]
        if not (isinstance(c, dict) and isinstance(c.get("token"), str) and isinstance(c.get("expires"), str)
                and isinstance(c.get("preview"), dict)):
            problems.append("confirm needs token, expires and preview")

    nav = s["nav"]
    back = nav.get("back")
    if back is not None and not (isinstance(back, str) and is_path(back)):
        problems.append("nav.back is not an address")
    children = nav.get("children")
    if not isinstance(children, list):
        problems.append("nav.children is not a list")
    else:
        for c in children:
            if not (isinstance(c, dict) and isinstance(c.get("path"), str) and is_path(c["path"])
                    and isinstance(c.get("title"), str) and isinstance(c.get("summary"), str)):
                problems.append("nav child needs path, title and summary")

    for a in s["actions"]:
        if not isinstance(a, dict):
            problems.append("action is not an object")
            continue
        aid = a.get("id")
        if not isinstance(aid, str) or not isinstance(a.get("label"), str):
            problems.append("action needs id and label")
        if a.get("effect") not in EFFECTS:
            problems.append(f"action {aid}: unknown effect")
        if a.get("confirm") is not (a.get("effect") == "destructive"):
            problems.append(f"action {aid}: confirm must be true exactly for destructive actions")
        if not isinstance(a.get("available"), bool):
            problems.append(f"action {aid}: available must be a boolean")
        elif not a["available"] and not isinstance(a.get("reason"), str):
            problems.append(f"action {aid}: unavailable actions need a reason")
        params = a.get("params")
        if not isinstance(params, dict):
            problems.append(f"action {aid}: params must be an object")
            continue
        for name, p in params.items():
            if not (isinstance(p, dict) and p.get("type") in PARAM_TYPES and isinstance(p.get("required"), bool)
                    and isinstance(p.get("description"), str)):
                problems.append(f"action {aid}: parameter {name} needs type, required and description")

    for al in s["alerts"]:
        if not (isinstance(al, dict) and al.get("level") in LEVELS and isinstance(al.get("code"), str)
                and _CODE.fullmatch(al["code"]) and isinstance(al.get("message"), str) and "action" in al):
            problems.append("alert needs level, code, message and action")

    meta = s["meta"]
    if not (isinstance(meta.get("time"), str) and isinstance(meta.get("took_ms"), int)
            and isinstance(meta.get("host"), str) and isinstance(meta.get("version"), str)):
        problems.append("meta needs time, took_ms, host and version")
    return problems
