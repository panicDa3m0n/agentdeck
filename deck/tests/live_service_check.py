#!/usr/bin/env python3
"""Controllo dal vivo di deck service sulla Deck.

1. L'elenco di deck service contro `systemctl list-units --all` e `systemctl list-unit-files`.
2. Il giro completo su un servizio di prova creato per l'occasione (agentdeck-test, un `sleep`): start, stop e
   restart con conferma, enable e disable con snapshot; ogni passo controllato con systemctl is-active/is-enabled.
3. stop e disable rifiutati per i servizi da cui dipende l'accesso, che restano attivi.
Alla fine il servizio di prova viene tolto.

Uso sulla Deck: python /opt/agentdeck/tests/live_service_check.py   (uscita 1 se qualcosa non coincide)
Documentazione: docs/deck.md.
"""
import json
import subprocess
import sys

TEST_UNIT = "agentdeck-test.service"
TEST_FILE = f"/etc/systemd/system/{TEST_UNIT}"
TEST_BODY = ("[Unit]\nDescription=AgentDeck: servizio di prova di deck service\n\n"
             "[Service]\nExecStart=/usr/bin/sleep infinity\n\n[Install]\nWantedBy=multi-user.target\n")
ACCESS = ("sshd", "systemd-networkd", "iwd", "systemd-resolved", "dbus-broker")


def sh(cmd: list) -> str:
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def deck(*args: str) -> dict:
    return json.loads(sh(["deck", "service", *args]))


def confirmed(verb: str, name: str) -> dict:
    first = deck(verb, f"name={name}")
    if first["status"] != "confirm":
        return first
    return deck(verb, f"name={name}", f"confirm={first['confirm']['token']}")


def main() -> int:
    checks = []

    # 1. Elenco
    s = deck()
    ours = {x["unit"]: x for x in s["data"]["services"]}
    theirs = {}
    for line in sh(["systemctl", "list-units", "--type=service", "--all", "--plain", "--no-legend"]).splitlines():
        parts = line.split(None, 4)
        if len(parts) >= 4:
            theirs[parts[0]] = parts[1:4]
    files = dict(line.split()[:2] for line in sh(["systemctl", "list-unit-files", "--type=service", "--no-legend",
                                                  "--plain"]).splitlines() if len(line.split()) >= 2)
    checks.append(("servizi caricati", sorted(ours), sorted(theirs)))
    checks.append(("load/active/sub", {u: [x["load"], x["active"], x["sub"]] for u, x in ours.items()}, theirs))
    checks.append(("abilitazione", {u: x["enabled"] for u, x in ours.items() if u in files},
                   {u: files[u] for u in ours if u in files}))
    failed = sh(["systemctl", "list-units", "--type=service", "--failed", "--plain", "--no-legend"])
    checks.append(("falliti", sorted(s["data"]["failed"]), sorted(l.split()[0] for l in failed.splitlines() if l)))

    # 2. Servizio di prova
    subprocess.run(["sudo", "-n", "tee", TEST_FILE], input=TEST_BODY, text=True, capture_output=True)
    subprocess.run(["sudo", "-n", "systemctl", "daemon-reload"])
    steps = [("start", lambda: deck("start", "name=agentdeck-test"), "is-active", "active"),
             ("restart", lambda: confirmed("restart", "agentdeck-test"), "is-active", "active"),
             ("stop", lambda: confirmed("stop", "agentdeck-test"), "is-active", "inactive"),
             ("enable", lambda: deck("enable", "name=agentdeck-test"), "is-enabled", "enabled"),
             ("disable", lambda: confirmed("disable", "agentdeck-test"), "is-enabled", "disabled")]
    for verb, call, query, expected in steps:
        r = call()
        checks.append((f"prova {verb}", [r["status"], sh(["systemctl", query, TEST_UNIT])], ["done", expected]))
        if verb in ("enable", "disable"):
            checks.append((f"prova {verb}: snapshot", isinstance(r["data"].get("snapshot_id"), int), True))
    first = deck("stop", "name=agentdeck-test")
    checks.append(("anteprima di stop", [first["status"], "changes" in first.get("confirm", {}).get("preview", {})],
                   ["confirm", True]))

    # 3. Rifiuti
    for unit in ACCESS:
        for verb in ("stop", "disable"):
            r = deck(verb, f"name={unit}")
            checks.append((f"rifiuto {verb} {unit}", (r.get("error") or {}).get("code"), "NOT_AVAILABLE"))
        checks.append((f"{unit} ancora attivo", sh(["systemctl", "is-active", unit]), "active"))

    subprocess.run(["sudo", "-n", "rm", "-f", TEST_FILE])
    subprocess.run(["sudo", "-n", "systemctl", "daemon-reload"])
    checks.append(("prova tolta", sh(["systemctl", "show", "-p", "LoadState", "--value", TEST_UNIT]), "not-found"))

    bad = 0
    for name, ours_v, theirs_v in checks:
        ok = ours_v == theirs_v
        bad += not ok
        shown = (f"{len(ours_v)} voci" if ok and isinstance(ours_v, list) and len(ours_v) > 5 else
                 f"deck={ours_v!r:<28} sistema={theirs_v!r}" if not isinstance(ours_v, dict)
                 else f"{len(ours_v)} voci" + ("" if ok else f", diverse: "
                      f"{ {k: (ours_v.get(k), theirs_v.get(k)) for k in set(ours_v) | set(theirs_v) if ours_v.get(k) != theirs_v.get(k)} }"))
        print(f"{'ok ' if ok else 'NO '} {name:<34} {shown}")
    print(f"\n{len(checks) - bad}/{len(checks)} controlli passati; servizi: {s['data']['counts']}; "
          f"took_ms: {s['meta']['took_ms']}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
