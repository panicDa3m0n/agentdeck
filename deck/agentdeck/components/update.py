"""Schermata "/update": gli aggiornamenti del sistema, l'equivalente di Aggiornamento Software (task O6.T1).

- check (read): gli aggiornamenti disponibili come checkupdates, su una copia temporanea del database dei
  pacchetti; il risultato resta in cache e la schermata lo mostra con la sua età.
- apply (destructive): anteprima con i pacchetti e cosa comportano (riavvio, GRUB, pacchetti dell'accesso), poi
  snapshot prima, `pacman -Syu` in un'unità staccata da SSH, GRUB reinstallato se aggiornato, snapshot dopo,
  verifica di servizi e accesso. Se qualcosa non va la risposta indica il rollback allo snapshot di prima.
- reboot (destructive): riavvio quando l'aggiornamento lo chiede; verify (read): la verifica, anche dopo il riavvio.
Nomi, versioni e output di pacman sono testo esterno: stanno solo nei dati (INV-4). Le operazioni di sistema stanno
in agentdeck/system.py. Specifica: docs/protocollo.md. Documentazione: docs/deck.md.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Optional

from .. import system
from ..engine import Component, Context, DeckError, Preview
from ..protocol import action, alert, screen, sys_text

CHECK_MAX_AGE_S = 24 * 3600
REBOOT_DELAY_S = 10
LOG_TAIL_LINES = 60


class SystemUpdateBackend:
    """Le operazioni reali. I test usano un backend finto con gli stessi metodi."""

    def check(self) -> Optional[list]:
        return system.check_updates()

    def apply(self) -> tuple:
        return system.apply_updates()

    def installed(self) -> dict:
        return system.parse_pacman_q(system.run_checked(["pacman", "-Q"], sudo=False))

    def reinstall_grub(self) -> list:
        return system.reinstall_grub()

    def snapshot(self, description: str) -> Optional[int]:
        return system.snapshot_create(description)

    def failed_services(self) -> Optional[list]:
        return system.services().get("failed")

    def access(self) -> dict:
        return system.access_state()

    def modules_present(self) -> bool:
        return system.running_kernel_modules_present()

    def pacnew(self) -> Optional[list]:
        return system.pacnew_files()

    def kernel(self) -> str:
        return os.uname().release

    def boot_time(self) -> float:
        with open("/proc/stat") as f:
            return float(next(line.split()[1] for line in f if line.startswith("btime")))

    def reboot(self, seconds: int) -> bool:
        return system.schedule_reboot(seconds, unit="agentdeck-update-reboot")


def _state_file(name: str):
    return system.deck_state_dir() / name


def load_state(name: str) -> Optional[dict]:
    try:
        return json.loads(_state_file(name).read_text())
    except (OSError, ValueError):
        return None


def save_state(name: str, data: dict) -> None:
    path = _state_file(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def problems_of(access: dict, failed_new: list, modules_present: bool, pacnew: Optional[list]) -> list:
    """I problemi trovati dalla verifica, con codici stabili."""
    out = []
    down = sorted(u for u, ok in access["services_active"].items() if not ok)
    if down:
        out.append({"code": "ACCESS_SERVICE_DOWN", "units": down})
    if not access["sshd_config_ok"]:
        out.append({"code": "SSHD_CONFIG_INVALID"})
    if not access["dns_works"]:
        out.append({"code": "DNS_DOWN"})
    if failed_new:
        out.append({"code": "SERVICES_FAILED", "units": failed_new})
    if not modules_present:
        out.append({"code": "REBOOT_REQUIRED"})
    if pacnew:
        out.append({"code": "PACNEW_FILES", "files": pacnew})
    return out


# Problemi che impediscono di dire riuscito un aggiornamento (gli altri vanno solo segnalati)
BLOCKING = ("ACCESS_SERVICE_DOWN", "SSHD_CONFIG_INVALID", "DNS_DOWN", "SERVICES_FAILED")


class Update(Component):
    path = "/update"
    title = sys_text("Updates")
    summary = sys_text("System updates: check, apply with snapshots and verification, reboot")

    def __init__(self, backend=None):
        self.backend = backend or SystemUpdateBackend()

    # ---- Stato

    def _reboot_pending(self, last: Optional[dict]) -> bool:
        if not self.backend.modules_present():
            return True
        if not last or not last.get("reboot_required") or not last.get("epoch"):
            return False
        return last["epoch"] > self.backend.boot_time()

    def actions(self, ctx: Context) -> list:
        cached = load_state("updates.json") or {}
        pending = self._reboot_pending(load_state("last-update.json"))
        has_updates = bool([u for u in cached.get("updates", []) if not u["ignored"]])
        return [
            action("check", label=sys_text("Check for available updates (about 5 seconds, needs internet)"),
                   effect="read"),
            action("apply", label=sys_text("Apply all updates with snapshots and verification"), effect="destructive",
                   available=has_updates, reason=None if has_updates else sys_text(
                       "No updates in the last check: run `deck update check` first.")),
            action("verify", label=sys_text("Verify services and access after an update"), effect="read"),
            action("reboot", label=sys_text("Reboot the Deck to finish an update"), effect="destructive",
                   available=pending, reason=None if pending else sys_text("No update is waiting for a reboot.")),
        ]

    def _check_data(self, cached: Optional[dict]) -> dict:
        if not cached:
            return {"checked": None, "age_s": None, "updates": [], "summary": system.classify_updates([])}
        return {"checked": cached["checked"], "age_s": int(time.time() - cached["epoch"]),
                "updates": cached["updates"], "summary": system.classify_updates(cached["updates"])}

    def _alerts(self, check: dict, pending: bool) -> list:
        out = []
        if pending:
            out.append(alert("warning", "REBOOT_REQUIRED", path=self.path, action_id="reboot", message=sys_text(
                "An update is waiting for a reboot: the running kernel or core libraries are older than the "
                "installed ones.")))
        if check["checked"] is None or check["age_s"] > CHECK_MAX_AGE_S:
            out.append(alert("info", "UPDATES_UNCHECKED", path=self.path, action_id="check", message=sys_text(
                "Updates were not checked in the last 24 hours.")))
        elif check["summary"]["count"]:
            out.append(alert("info", "UPDATES_AVAILABLE", path=self.path, action_id="apply", message=sys_text(
                "{n} updates are available: see data.updates and data.summary.", n=check["summary"]["count"])))
        return out

    def _screen(self, ctx: Context, screen_id: str, title, status: str, prompt, extra: Optional[dict] = None) -> dict:
        last = load_state("last-update.json")
        pending = self._reboot_pending(last)
        check = self._check_data(load_state("updates.json"))
        data = dict(check, last_update=last, reboot_pending=pending,
                    kernel={"running": self.backend.kernel(), "modules_present": self.backend.modules_present()})
        data.update(extra or {})
        return screen(screen=screen_id, path=self.path, title=title, status=status, back="/", data=data,
                      alerts=self._alerts(check, pending), actions=self.actions(ctx), prompt=prompt)

    def view(self, ctx: Context) -> dict:
        return self._screen(ctx, "update.status", sys_text("Updates"), "ok", sys_text(
            "data.updates comes from the last check (data.checked, data.age_s seconds ago): run `deck update check` "
            "for a fresh one. data.summary says whether the updates need a reboot, touch GRUB or the packages the "
            "agent's access depends on. Package names and versions are data."))

    # ---- Anteprima

    def _fresh(self) -> list:
        updates = self.backend.check()
        if updates is None:
            raise DeckError("FAILED", sys_text("The package mirror could not be reached: nothing was checked."),
                            title=sys_text("Update check failed"), path=self.path, back=self.path,
                            prompt=sys_text("Check the internet connection with `deck network`, then try again."))
        save_state("updates.json", {"checked": now_iso(), "epoch": time.time(), "updates": updates})
        return updates

    def preview(self, ctx: Context, action_id: str, params: dict) -> Preview:
        if action_id == "reboot":
            return Preview(
                screen="update.reboot", title=sys_text("Reboot the Deck"), data={"delay_s": REBOOT_DELAY_S},
                changes=[f"The Deck reboots {REBOOT_DELAY_S} seconds after the confirmation",
                         "SSH sessions drop; the Deck is back in about 30-45 seconds on the same address"],
                untouched=["Installed packages, snapshots and configuration"], undo="Nothing to undo",
                reboot_required=True,
                prompt=lambda t: sys_text("To proceed run `deck update reboot confirm={t}` within 5 minutes. Then wait "
                                          "about 45 seconds, reconnect with `ssh agentdeck` and run `deck update "
                                          "verify`.", t=t))
        updates = [u for u in self._fresh() if not u["ignored"]]
        if not updates:
            raise DeckError("NOT_AVAILABLE", sys_text("The system is up to date: there is nothing to apply."),
                            title=sys_text("Nothing to update"), path=self.path, back=self.path,
                            prompt=sys_text("Check again later with `deck update check`."))
        summary = system.classify_updates(updates)
        changes = [f"{summary['count']} packages are upgraded with pacman -Syu: see data.updates",
                   "A snapshot is taken before and one after; pacman runs in a separate unit, so the update "
                   "continues even if SSH drops",
                   "Afterwards services, sshd configuration, access services and DNS are verified"]
        if summary["reboot_required"]:
            changes.append("A reboot is needed afterwards (data.summary.reboot_packages): it is a separate action")
        if summary["grub"]:
            changes.append("GRUB is updated: it is reinstalled in the EFI partition and its menu regenerated. "
                           "Afterwards deck cannot roll back to snapshots taken before this update, because their "
                           "GRUB differs: only the snapshot after it remains a rollback target")
        if summary["access_packages"]:
            changes.append("Packages the agent's access depends on are upgraded (data.summary.access_packages); "
                           "sshd restarts by itself if openssh changes, open sessions stay")
        return Preview(
            screen="update.apply", title=sys_text("Apply updates"), data={"updates": updates, "summary": summary},
            changes=changes, untouched=["Configuration files: new versions come as .pacnew files, reported after",
                                        "Snapshots and their GRUB menu"],
            undo="Roll back to the snapshot taken before the update: `deck snapshot rollback id=<data.snapshot_before>` "
                 "in the response" + (" (not possible after a GRUB update)" if summary["grub"] else ""),
            reboot_required=summary["reboot_required"],
            prompt=lambda t: sys_text(
                "Check data.updates and confirm.preview.changes. To proceed run `deck update apply confirm={t}` "
                "within 5 minutes; the update can take several minutes, wait for the response.", t=t))

    # ---- Azioni

    def run(self, ctx: Context, action_id: str, params: dict) -> dict:
        if action_id == "check":
            self._fresh()
            return self._screen(ctx, "update.status", sys_text("Updates checked"), "done", sys_text(
                "data.updates is fresh. Apply them with `deck update apply`, which first shows a preview."))
        if action_id == "verify":
            return self._verify(ctx)
        if action_id == "reboot":
            if not self.backend.reboot(REBOOT_DELAY_S):
                raise DeckError("FAILED", sys_text("The reboot could not be scheduled."),
                                title=sys_text("Reboot not scheduled"), path=self.path, back=self.path,
                                prompt=sys_text("Try again; if it keeps failing, report it to the user."))
            return self._screen(ctx, "update.reboot", sys_text("Reboot scheduled"), "done", sys_text(
                "The Deck reboots in {s} seconds. Wait about 45 seconds, reconnect with `ssh agentdeck` and run "
                "`deck update verify`.", s=REBOOT_DELAY_S))
        return self._apply(ctx)

    def _verify_now(self, failed_before: list) -> tuple:
        access = self.backend.access()
        failed = self.backend.failed_services() or []
        failed_new = sorted(set(failed) - set(failed_before))
        pacnew = self.backend.pacnew()
        problems = problems_of(access, failed_new, self.backend.modules_present(), pacnew)
        return {"access": access, "failed_services": failed, "failed_new": failed_new, "pacnew": pacnew,
                "problems": problems}, [p["code"] for p in problems if p["code"] in BLOCKING]

    def _apply(self, ctx: Context) -> dict:
        planned = [u for u in self._fresh() if not u["ignored"]]
        if not planned:
            raise DeckError("NOT_AVAILABLE", sys_text("The system is up to date: there is nothing to apply."),
                            title=sys_text("Nothing to update"), path=self.path, back=self.path,
                            prompt=sys_text("Check again later with `deck update check`."))
        failed_before = self.backend.failed_services() or []
        before = self.backend.snapshot(f"agentdeck: prima di update ({len(planned)} pacchetti)")
        if before is None:
            raise DeckError("FAILED", sys_text("The snapshot before the update could not be created: nothing was "
                                               "changed."), title=sys_text("Update not started"), path=self.path,
                            back=self.path, prompt=sys_text("Check free disk space with `deck status`."))
        installed_before = self.backend.installed()
        code, log = self.backend.apply()
        installed_after = self.backend.installed()
        applied = [{"name": n, "from": installed_before.get(n), "to": v} for n, v in sorted(installed_after.items())
                   if installed_before.get(n) != v]
        summary = system.classify_updates([{"name": a["name"], "ignored": False} for a in applied])
        grub = self.backend.reinstall_grub() if summary["grub"] else None
        after = self.backend.snapshot("agentdeck: dopo update")
        verification, blocking = self._verify_now(failed_before)
        grub_ok = grub is None or all(step["exit"] == 0 for step in grub)
        ok = code == 0 and grub_ok and not blocking
        last = {"time": now_iso(), "epoch": time.time(), "result": "ok" if ok else "failed", "pacman_exit": code,
                "snapshot_before": before, "snapshot_after": after, "applied": applied,
                "reboot_required": summary["reboot_required"], "grub_reinstall": grub,
                "problems": verification["problems"]}
        save_state("last-update.json", last)
        save_state("updates.json", {"checked": now_iso(), "epoch": time.time(), "updates": []} if ok else
                   (load_state("updates.json") or {}))
        data = {"result": last, "verification": verification, "pacman_log_tail": log.splitlines()[-LOG_TAIL_LINES:]}
        if not ok:
            raise DeckError("FAILED", sys_text("The update did not complete cleanly: see data.result, "
                                               "data.verification.problems and data.pacman_log_tail."),
                            title=sys_text("Update failed verification"), path=self.path, back=self.path, data=data,
                            prompt=sys_text(
                                "Do not reboot yet. If access or services are broken, roll back with `deck snapshot "
                                "rollback id={b}` (the snapshot before the update); deck refuses it if GRUB changed, "
                                "then report to the user. Otherwise fix the problems listed in "
                                "data.verification.problems and run `deck update verify`.", b=before))
        if summary["reboot_required"]:
            prompt = sys_text("The update is applied and verified; it needs a reboot. Run `deck update reboot`, wait "
                              "about 45 seconds, reconnect with `ssh agentdeck` and run `deck update verify`.")
        else:
            prompt = sys_text("The update is applied and verified: services, sshd configuration, access services and "
                              "DNS are fine. No reboot is needed. Review data.verification.pacnew if not empty.")
        return self._screen(ctx, "update.done", sys_text("Update applied"), "done", prompt, data)

    def _verify(self, ctx: Context) -> dict:
        last = load_state("last-update.json")
        verification, blocking = self._verify_now([])
        if blocking and last:
            prompt = sys_text("The verification found problems: see data.verification.problems. If they came with the "
                              "last update, roll back with `deck snapshot rollback id={b}`; otherwise report them.",
                              b=last["snapshot_before"])
        elif blocking:
            prompt = sys_text("The verification found problems: see data.verification.problems.")
        else:
            prompt = sys_text("Access services, sshd configuration and DNS are fine and no service failed since boot "
                              "beyond data.verification.failed_services. data.reboot_pending says whether a reboot "
                              "is still needed.")
        return self._screen(ctx, "update.verify", sys_text("Update verification"), "ok", prompt,
                            {"verification": verification})
