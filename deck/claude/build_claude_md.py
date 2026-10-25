#!/usr/bin/env python3
"""Genera il CLAUDE.md gestito di AgentDeck (/etc/claude-code/CLAUDE.md) dal modello e dalle invarianti del progetto.

Fonte unica (INV-9): le invarianti si leggono da .claude/workflow/invariants.json, scritto dalla governance;
il resto da deck/claude/CLAUDE.template.md. Uso: build_claude_md.py <radice del repository> > CLAUDE.md
Documentazione: docs/claude-code.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def invariants(repo: Path) -> list:
    data = json.loads((repo / ".claude" / "workflow" / "invariants.json").read_text())
    return [(i["id"], i["testo"]) for i in data["items"]]


def build(repo: Path) -> str:
    template = (HERE / "CLAUDE.template.md").read_text()
    lines = "\n".join(f"- **{iid}** {text}" for iid, text in invariants(repo))
    if "{{INVARIANTS}}" not in template:
        raise SystemExit("template without {{INVARIANTS}}")
    return template.replace("{{INVARIANTS}}", lines)


if __name__ == "__main__":
    sys.stdout.write(build(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent.parent))
