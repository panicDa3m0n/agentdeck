"""Memoria del Brain: pacchetti piccoli in SQLite con ricerca testuale FTS5, revisioni e collegamenti (O22.T1).

Componente isolato: usa solo la libreria standard e non conosce il protocollo delle schermate, così un suo guasto
resta suo. La schermata che lo espone è agentdeck/brain/components/memory.py. Documentazione: docs/brain.md.

Un pacchetto di memoria: id, tipo, testo (al massimo MAX_TEXT caratteri), etichette, stato, origine (sessione e
messaggio in cui è nato), numero di revisione, date. Ogni cambiamento scrive una revisione, così nulla si perde;
solo forget cancella davvero. I testi sono dati scritti da agenti e possono venire da testo esterno (INV-4): qui
non diventano mai istruzioni, ed entrano nelle schermate solo dentro data.

Il database sta in $AGENTDECK_BRAIN_DB, di norma ~/.local/share/agentdeck/brain/brain.db (cartella 700, file 600).
"""
from __future__ import annotations

import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

SCHEMA_VERSION = 1
TYPES = ("fact", "decision", "preference", "procedure", "lesson", "reference")
STATUSES = ("active", "deprecated", "superseded", "merged")
MAX_TEXT = 1000
MAX_REASON = 300
MAX_TAGS = 8
MAX_MERGE = 10
SEARCH_LIMIT = 50

TAG = re.compile(r"[a-z0-9][a-z0-9._-]{0,31}")
ORIGIN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_WORD = re.compile(r"\w+")

# Testi che sembrano segreti: in memoria non entrano mai (INV-6); si scrive dove sta il segreto, non il segreto.
SECRETS = {
    "private-key": re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    "github-token": re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})"),
    "anthropic-key": re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"),
    "api-key": re.compile(r"\bsk-[A-Za-z0-9_-]{32,}"),
    "slack-token": re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}"),
    "aws-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "telegram-token": re.compile(r"\b[0-9]{8,10}:[A-Za-z0-9_-]{35}\b"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    # un valore dopo password=, token: e simili; non un percorso, una variabile o un segnaposto (~/, /, $, <)
    "password-assignment": re.compile(
        r"(?i)\b(password|passwd|passphrase|api[_-]?key|secret[_-]?key|token)\s*[:=]\s*(?![~/$<])\S{8,}"),
}

# IF NOT EXISTS ovunque: due sessioni che creano il database insieme non si scontrano (BEGIN IMMEDIATE in _connect).
_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories(
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL,
    text TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    origin_session TEXT,
    origin_message TEXT,
    revision INTEGER NOT NULL DEFAULT 1,
    created TEXT NOT NULL,
    updated TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS revisions(
    memory_id INTEGER NOT NULL,
    revision INTEGER NOT NULL,
    type TEXT NOT NULL,
    text TEXT NOT NULL,
    tags TEXT NOT NULL,
    status TEXT NOT NULL,
    time TEXT NOT NULL,
    change TEXT NOT NULL,
    reason TEXT,
    session TEXT,
    PRIMARY KEY(memory_id, revision)
);
CREATE TABLE IF NOT EXISTS links(
    from_id INTEGER NOT NULL,
    to_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    time TEXT NOT NULL,
    PRIMARY KEY(from_id, to_id, kind)
);
CREATE INDEX IF NOT EXISTS links_to ON links(to_id);
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    text, tags, content='memories', content_rowid='id', tokenize='unicode61 remove_diacritics 2'
);
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, text, tags) VALUES (new.id, new.text, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, text, tags) VALUES ('delete', old.id, old.text, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE OF text, tags ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, text, tags) VALUES ('delete', old.id, old.text, old.tags);
    INSERT INTO memories_fts(rowid, text, tags) VALUES (new.id, new.text, new.tags);
END;
"""


class Invalid(ValueError):
    """Un valore non accettabile: field è il parametro, reason un codice stabile (per esempio too_long)."""

    def __init__(self, field: str, reason: str, detail: Optional[str] = None):
        super().__init__(f"{field}: {reason}")
        self.field, self.reason, self.detail = field, reason, detail


class NotFound(LookupError):
    def __init__(self, memory_id: int):
        super().__init__(f"memory {memory_id} not found")
        self.memory_id = memory_id


class Conflict(ValueError):
    """L'operazione non vale per lo stato attuale della memoria: reason è un codice stabile."""

    def __init__(self, memory_id: int, reason: str, status: Optional[str] = None):
        super().__init__(f"memory {memory_id}: {reason}")
        self.memory_id, self.reason, self.status = memory_id, reason, status


def default_path() -> Path:
    explicit = os.environ.get("AGENTDECK_BRAIN_DB")
    if explicit:
        return Path(explicit)
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "agentdeck" / "brain" / "brain.db"


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


# ---- Validazione

def clean_text(value: str, field: str = "text", limit: int = MAX_TEXT) -> str:
    text = _CONTROL.sub("", value.replace("\r\n", "\n")).strip()
    if not text:
        raise Invalid(field, "empty")
    if len(text) > limit:
        raise Invalid(field, "too_long")
    if field == "text":
        for name, pattern in SECRETS.items():
            if pattern.search(text):
                raise Invalid(field, "secret", name)
    return text


def parse_tags(value: Optional[str]) -> list:
    """Etichette separate da virgole o spazi, in minuscolo, senza doppioni: al massimo MAX_TAGS."""
    if not value:
        return []
    tags: list = []
    for raw in re.split(r"[,\s]+", value.strip().lower()):
        if not raw:
            continue
        if not TAG.fullmatch(raw):
            raise Invalid("tags", "bad_tag")
        if raw not in tags:
            tags.append(raw)
    if len(tags) > MAX_TAGS:
        raise Invalid("tags", "too_many")
    return tags


def parse_ids(value: str) -> list:
    ids: list = []
    for raw in re.split(r"[,\s]+", value.strip()):
        if not raw:
            continue
        if not raw.isdigit() or int(raw) < 1:
            raise Invalid("ids", "bad_id")
        if int(raw) not in ids:
            ids.append(int(raw))
    if len(ids) < 2:
        raise Invalid("ids", "too_few")
    if len(ids) > MAX_MERGE:
        raise Invalid("ids", "too_many")
    return ids


def check_origin(value: Optional[str], field: str) -> Optional[str]:
    if value is None or value == "":
        return None
    if not ORIGIN_ID.fullmatch(value):
        raise Invalid(field, "bad_id")
    return value


def fts_query(text: str) -> Optional[str]:
    """Una domanda libera diventa una ricerca FTS5 sicura: parole tra virgolette in OR, le lunghe anche come
    prefisso senza l'ultima lettera, così memoria trova memorie. None se non resta nessuna parola."""
    words: list = []
    for w in _WORD.findall(text.lower()):
        if w not in words:
            words.append(w)
    long_words = [w for w in words if len(w) >= 3] or words
    terms = []
    for w in long_words[:24]:
        terms.append(f'"{w[:-1]}"*' if len(w) >= 5 else f'"{w}"*' if len(w) >= 3 else f'"{w}"')
    return " OR ".join(terms) or None


# ---- Archivio

class Store:
    """Il database delle memorie. Ogni metodo apre e chiude la sua connessione: più sessioni lo usano insieme."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else default_path()

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self.path.parent, 0o700)
        fresh = not self.path.exists()
        conn = sqlite3.connect(self.path, timeout=10)
        if fresh:
            os.chmod(self.path, 0o600)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout = 10000")
            conn.execute("PRAGMA secure_delete = ON")  # le pagine liberate si azzerano: forget non lascia tracce
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version == 0:
                conn.execute("PRAGMA journal_mode = WAL")
                conn.executescript(f"BEGIN IMMEDIATE; {_SCHEMA} PRAGMA user_version = {SCHEMA_VERSION}; COMMIT;")
            elif version > SCHEMA_VERSION:
                raise RuntimeError(f"brain database schema {version} is newer than this code ({SCHEMA_VERSION})")
        except BaseException:
            conn.close()
            raise
        return conn

    # lettura

    def info(self) -> dict:
        with closing(self._connect()) as conn:
            by_status = {s: 0 for s in STATUSES}
            by_type = {t: 0 for t in TYPES}
            for row in conn.execute("SELECT status, type, COUNT(*) AS n FROM memories GROUP BY status, type"):
                by_status[row["status"]] = by_status.get(row["status"], 0) + row["n"]
                if row["status"] == "active":
                    by_type[row["type"]] = by_type.get(row["type"], 0) + row["n"]
            recent = [self._public(conn, r, links=False) for r in conn.execute(
                "SELECT * FROM memories WHERE status = 'active' ORDER BY updated DESC, id DESC LIMIT 5")]
        size = sum(p.stat().st_size for p in self.path.parent.glob(self.path.name + "*") if p.is_file())
        return {"database": {"path": str(self.path), "bytes": size, "schema": SCHEMA_VERSION},
                "counts": {"total": sum(by_status.values()), "by_status": by_status, "active_by_type": by_type},
                "recent": recent}

    def get(self, memory_id: int) -> dict:
        with closing(self._connect()) as conn:
            return self._public(conn, self._row(conn, memory_id))

    def revisions(self, memory_id: int) -> list:
        with closing(self._connect()) as conn:
            self._row(conn, memory_id)
            return [{"revision": r["revision"], "time": r["time"], "change": r["change"], "reason": r["reason"],
                     "session": r["session"], "type": r["type"], "status": r["status"], "text": r["text"],
                     "tags": _split(r["tags"])}
                    for r in conn.execute("SELECT * FROM revisions WHERE memory_id = ? ORDER BY revision DESC",
                                          (memory_id,))]

    def search(self, query: Optional[str] = None, *, type_: Optional[str] = None, tag: Optional[str] = None,
               status: str = "active", limit: int = 10, exclude: Iterable[int] = ()) -> dict:
        """Ricerca testuale (bm25 su testo ed etichette), oppure le più recenti se query manca."""
        limit = max(1, min(limit, SEARCH_LIMIT))
        where, args = [], []
        if status != "all":
            where.append("m.status = ?")
            args.append(status)
        if type_:
            where.append("m.type = ?")
            args.append(type_)
        if tag:
            where.append("instr(' ' || m.tags || ' ', ?) > 0")
            args.append(f" {tag} ")
        excluded = list(exclude)
        if excluded:
            where.append(f"m.id NOT IN ({','.join('?' * len(excluded))})")
            args += excluded
        match = fts_query(query) if query else None
        with closing(self._connect()) as conn:
            if match:
                sql = ("SELECT m.*, bm25(memories_fts, 1.0, 2.0) AS rank FROM memories_fts "
                       "JOIN memories m ON m.id = memories_fts.rowid WHERE memories_fts MATCH ?"
                       + "".join(f" AND {w}" for w in where) + " ORDER BY rank, m.updated DESC LIMIT ?")
                rows = conn.execute(sql, [match] + args + [limit + 1]).fetchall()
            else:
                sql = ("SELECT m.*, NULL AS rank FROM memories m"
                       + (" WHERE " + " AND ".join(where) if where else "")
                       + " ORDER BY m.updated DESC, m.id DESC LIMIT ?")
                rows = conn.execute(sql, args + [limit + 1]).fetchall()
            found = []
            for r in rows[:limit]:
                item = self._public(conn, r, links=False)
                if r["rank"] is not None:
                    item["score"] = float(f"{-r['rank']:.3g}")  # bm25: più alto è meglio, 3 cifre significative
                found.append(item)
        return {"mode": "text" if match else "recent", "memories": found, "more": len(rows) > limit}

    # scrittura

    def save(self, text: str, type_: str, tags: Optional[list] = None, *, session: Optional[str] = None,
             message: Optional[str] = None, reason: str = "created") -> dict:
        _check_type(type_)
        text = clean_text(text)
        now = _now()
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                "INSERT INTO memories(type, text, tags, status, origin_session, origin_message, revision, created, "
                "updated) VALUES (?, ?, ?, 'active', ?, ?, 1, ?, ?)",
                (type_, text, " ".join(tags or []), session, message, now, now))
            memory_id = cur.lastrowid
            self._revision(conn, memory_id, reason, None, session, now)
            return self._public(conn, self._row(conn, memory_id))

    def edit(self, memory_id: int, *, text: Optional[str] = None, type_: Optional[str] = None,
             tags: Optional[list] = None, reason: Optional[str] = None, session: Optional[str] = None) -> dict:
        changes: dict = {}
        if text is not None:
            changes["text"] = clean_text(text)
        if type_ is not None:
            _check_type(type_)
            changes["type"] = type_
        if tags is not None:
            changes["tags"] = " ".join(tags)
        if not changes:
            raise Invalid("text", "nothing_to_change")
        with closing(self._connect()) as conn, conn:
            row = self._row(conn, memory_id)
            if row["status"] != "active":
                raise Conflict(memory_id, "not_active", row["status"])
            if all(row[k] == v for k, v in changes.items()):
                raise Invalid("text", "nothing_to_change")
            self._update(conn, memory_id, changes, "edited", reason, session)
            return self._public(conn, self._row(conn, memory_id))

    def deprecate(self, memory_id: int, reason: str, session: Optional[str] = None) -> dict:
        with closing(self._connect()) as conn, conn:
            row = self._row(conn, memory_id)
            if row["status"] != "active":
                raise Conflict(memory_id, "not_active", row["status"])
            self._update(conn, memory_id, {"status": "deprecated"}, "deprecated", reason, session)
            return self._public(conn, self._row(conn, memory_id))

    def restore(self, memory_id: int, reason: Optional[str] = None, session: Optional[str] = None) -> dict:
        """Torna attiva una memoria deprecata, sostituita o accorpata; il collegamento che la chiudeva sparisce,
        resta nelle revisioni."""
        with closing(self._connect()) as conn, conn:
            row = self._row(conn, memory_id)
            if row["status"] == "active":
                raise Conflict(memory_id, "already_active", "active")
            conn.execute("DELETE FROM links WHERE to_id = ?", (memory_id,))
            self._update(conn, memory_id, {"status": "active"}, "restored", reason, session)
            return self._public(conn, self._row(conn, memory_id))

    def supersede(self, memory_id: int, by: int, reason: Optional[str] = None, session: Optional[str] = None) -> dict:
        """memory_id è superata da by: la vecchia si chiude, il collegamento by -> memory_id resta."""
        if by == memory_id:
            raise Invalid("by", "same_id")
        with closing(self._connect()) as conn, conn:
            old, new = self._row(conn, memory_id), self._row(conn, by)
            if old["status"] != "active":
                raise Conflict(memory_id, "not_active", old["status"])
            if new["status"] != "active":
                raise Conflict(by, "not_active", new["status"])
            conn.execute("INSERT OR REPLACE INTO links(from_id, to_id, kind, time) VALUES (?, ?, 'supersedes', ?)",
                         (by, memory_id, _now()))
            self._update(conn, memory_id, {"status": "superseded"}, "superseded", reason, session)
            return {"old": self._public(conn, self._row(conn, memory_id)),
                    "new": self._public(conn, self._row(conn, by))}

    def merge(self, ids: list, text: str, type_: Optional[str] = None, tags: Optional[list] = None,
              reason: Optional[str] = None, *, session: Optional[str] = None, message: Optional[str] = None) -> dict:
        """Accorpa memorie affini in una nuova, scritta dall'agente: le vecchie si chiudono come merged."""
        text = clean_text(text)
        with closing(self._connect()) as conn, conn:
            rows = [self._row(conn, i) for i in ids]
            for r in rows:
                if r["status"] != "active":
                    raise Conflict(r["id"], "not_active", r["status"])
            if type_ is None:
                kinds = {r["type"] for r in rows}
                if len(kinds) != 1:
                    raise Invalid("type", "needed_for_mixed_types")
                type_ = kinds.pop()
            _check_type(type_)
            if tags is None:
                tags = []
                for r in rows:
                    tags += [t for t in _split(r["tags"]) if t not in tags]
                tags = tags[:MAX_TAGS]
            now = _now()
            cur = conn.execute(
                "INSERT INTO memories(type, text, tags, status, origin_session, origin_message, revision, created, "
                "updated) VALUES (?, ?, ?, 'active', ?, ?, 1, ?, ?)",
                (type_, text, " ".join(tags), session, message, now, now))
            new_id = cur.lastrowid
            self._revision(conn, new_id, "merged-from", reason, session, now)
            for r in rows:
                conn.execute("INSERT INTO links(from_id, to_id, kind, time) VALUES (?, ?, 'merges', ?)",
                             (new_id, r["id"], now))
                self._update(conn, r["id"], {"status": "merged"}, "merged", reason, session)
            return {"new": self._public(conn, self._row(conn, new_id)),
                    "old": [self._public(conn, self._row(conn, r["id"]), links=False) for r in rows]}

    def forget(self, memory_id: int) -> dict:
        """Cancella davvero: memoria, revisioni e collegamenti. Per segreti o dati personali salvati per errore."""
        with closing(self._connect()) as conn, conn:
            gone = self._public(conn, self._row(conn, memory_id))
            revisions = conn.execute("SELECT COUNT(*) FROM revisions WHERE memory_id = ?", (memory_id,)).fetchone()[0]
            conn.execute("DELETE FROM links WHERE from_id = ? OR to_id = ?", (memory_id, memory_id))
            conn.execute("DELETE FROM revisions WHERE memory_id = ?", (memory_id,))
            conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        with closing(self._connect()) as conn:  # anche le pagine liberate e l'indice non devono tenere il testo
            conn.execute("INSERT INTO memories_fts(memories_fts) VALUES ('optimize')")
            conn.commit()
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.execute("VACUUM")
        return {"memory": gone, "revisions_removed": revisions}

    def counts_for(self, memory_id: int) -> dict:
        with closing(self._connect()) as conn:
            self._row(conn, memory_id)
            revisions = conn.execute("SELECT COUNT(*) FROM revisions WHERE memory_id = ?", (memory_id,)).fetchone()[0]
            links = conn.execute("SELECT COUNT(*) FROM links WHERE from_id = ? OR to_id = ?",
                                 (memory_id, memory_id)).fetchone()[0]
        return {"revisions": revisions, "links": links}

    # interni

    def _row(self, conn: sqlite3.Connection, memory_id: int) -> sqlite3.Row:
        row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        if row is None:
            raise NotFound(memory_id)
        return row

    def _update(self, conn: sqlite3.Connection, memory_id: int, changes: dict, change: str,
                reason: Optional[str], session: Optional[str]) -> None:
        now = _now()
        sets = ", ".join(f"{k} = ?" for k in changes)
        conn.execute(f"UPDATE memories SET {sets}, revision = revision + 1, updated = ? WHERE id = ?",
                     list(changes.values()) + [now, memory_id])
        self._revision(conn, memory_id, change, reason, session, now)

    def _revision(self, conn: sqlite3.Connection, memory_id: int, change: str, reason: Optional[str],
                  session: Optional[str], now: str) -> None:
        r = self._row(conn, memory_id)
        conn.execute("INSERT INTO revisions(memory_id, revision, type, text, tags, status, time, change, reason, "
                     "session) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (memory_id, r["revision"], r["type"], r["text"], r["tags"], r["status"], now, change, reason,
                      session))

    def _public(self, conn: sqlite3.Connection, row: sqlite3.Row, links: bool = True) -> dict:
        item = {"id": row["id"], "type": row["type"], "status": row["status"], "text": row["text"],
                "tags": _split(row["tags"]), "origin": {"session": row["origin_session"],
                                                        "message": row["origin_message"]},
                "revision": row["revision"], "created": row["created"], "updated": row["updated"]}
        if links:
            item["links"] = self._links(conn, row["id"])
        return item

    def _links(self, conn: sqlite3.Connection, memory_id: int) -> dict:
        out = {"supersedes": [], "superseded_by": None, "merged_from": [], "merged_into": None}
        for r in conn.execute("SELECT * FROM links WHERE from_id = ? OR to_id = ? ORDER BY time, from_id, to_id",
                              (memory_id, memory_id)):
            if r["kind"] == "supersedes":
                if r["from_id"] == memory_id:
                    out["supersedes"].append(r["to_id"])
                else:
                    out["superseded_by"] = r["from_id"]
            elif r["kind"] == "merges":
                if r["from_id"] == memory_id:
                    out["merged_from"].append(r["to_id"])
                else:
                    out["merged_into"] = r["from_id"]
        return out


def _split(tags: str) -> list:
    return [t for t in (tags or "").split() if t]


def _check_type(type_: str) -> None:
    if type_ not in TYPES:
        raise Invalid("type", "unknown_type")
