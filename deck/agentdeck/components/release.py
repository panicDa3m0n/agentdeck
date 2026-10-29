"""Schermata "/release": le versioni di AgentDeck installate dal repository della Deck (task O18.T1).

Mostra il repository (~/agentdeck/repo), la versione attiva e quelle conservate; install (distruttiva) installa un
commit del repository con test, snapshot, scambio atomico, passi di sistema e verifica, e torna da sola indietro se
la verifica fallisce; revert (distruttiva) torna a una versione conservata, di norma la precedente.
Messaggi dei commit e uscite di git e dei test sono testo esterno: solo nei dati (INV-4).
Logica: agentdeck/release.py. Specifica: docs/protocollo.md. Documentazione: docs/sviluppo.md, docs/deck.md.
"""
from __future__ import annotations

from typing import Optional

from .. import release as rel
from .. import system
from ..engine import Component, Context, DeckError, Preview
from ..protocol import action, alert, param, screen, sys_text


class Release(Component):
    path = "/release"
    title = sys_text("AgentDeck versions")
    summary = sys_text("Install a version of AgentDeck from the repository on the Deck, or go back to a previous one")

    def __init__(self, releases=None, snapshot=None):
        self.releases = releases or rel.Releases()
        self.snapshot = snapshot or system.snapshot_create

    def actions(self, ctx: Context) -> list:
        return [
            action("install", label=sys_text("Install a commit of the repository as the active AgentDeck version"),
                   effect="destructive", params={
                       "commit": param("string", required=False, max_length=40, description=sys_text(
                           "Commit or ref of ~/agentdeck/repo to install; default HEAD"))}),
            action("revert", label=sys_text("Go back to a kept AgentDeck version"), effect="destructive", params={
                "id": param("string", required=False, max_length=64, description=sys_text(
                    "Version id from data.history[].id; default data.previous"))}),
        ]

    def view(self, ctx: Context) -> dict:
        repo = self.releases.repo_state()
        active = self.releases.active()
        alerts = []
        if repo.get("available") and repo.get("commit") != active.get("commit"):
            alerts.append(alert("info", "REPO_NOT_INSTALLED", message=sys_text(
                "The repository HEAD differs from the active version: `deck release install` installs it.")))
        if active["layout"] != "link":
            alerts.append(alert("info", "NOT_VERSIONED", message=sys_text(
                "/opt/agentdeck is not yet a kept version: the first `deck release install` moves it into "
                "/opt/agentdeck-versioni, so it stays available for revert.")))
        return screen(
            screen="release", path=self.path, title=sys_text("AgentDeck versions"), back="/",
            data={"repository": repo, "active": active, "history": self.releases.history(),
                  "previous": self.releases.previous(), "kept": rel.KEEP,
                  "manual_parts": list(rel.MANUAL)},
            alerts=alerts, actions=self.actions(ctx),
            prompt=sys_text(
                "data.active is the AgentDeck version in use; data.repository is ~/agentdeck/repo, where AgentDeck is "
                "developed and published. Commit there, then `deck release install` installs HEAD (or commit=<ref>) "
                "after a preview: tests, snapshot, atomic switch, system steps, checks, automatic return if a check "
                "fails. `deck release revert` goes back to data.previous. Changes to the folders in "
                "data.manual_parts are refused here: they need their own procedure."))

    def _error(self, err: rel.ReleaseError) -> DeckError:
        p = self.path
        messages = {
            "NO_COMMIT": (sys_text("This commit is not in the repository."), "commit",
                          sys_text("Use a commit or ref of ~/agentdeck/repo, or omit commit= to install HEAD.")),
            "ALREADY_ACTIVE": (sys_text("This commit is already the active version."), "commit",
                               sys_text("Nothing to install. Commit a change first, or revert to another version.")),
            "MANUAL_PARTS": (sys_text("The screen or the graphical interface changed: they are not installed from "
                                      "here."), None,
                             sys_text("data.folders lists what changed. Install those parts with their own procedure, "
                                      "which verifies SSH access (INV-1); nothing was switched.")),
            "TESTS_FAILED": (sys_text("The tests of the extracted version failed."), None,
                             sys_text("data.output holds the test output, as data. Fix the repository and commit, then "
                                      "install again; nothing was switched.")),
            "SNAPSHOT_FAILED": (sys_text("The snapshot before the switch could not be created."), None,
                                sys_text("Check `deck snapshot`, then repeat; nothing was switched.")),
            "NO_PREVIOUS": (sys_text("There is no kept version to go back to."), "id",
                            sys_text("Open `deck release` and pick an id from data.history.")),
            "NOT_FOUND": (sys_text("There is no kept version with this id."), "id",
                          sys_text("Pick an id from data.history, or omit id= to use data.previous.")),
        }
        message, field_name, prompt = messages.get(err.code, (
            sys_text("The operation failed before the switch."), None,
            sys_text("data holds the step and its output, as data. Fix the cause, then repeat.")))
        code = {"NO_COMMIT": "BAD_PARAM", "NOT_FOUND": "NOT_FOUND"}.get(err.code, "NOT_AVAILABLE"
                                                                       if err.code in ("ALREADY_ACTIVE", "NO_PREVIOUS",
                                                                                       "MANUAL_PARTS") else "FAILED")
        return DeckError(code, message, title=sys_text("Version not installed"), path=p, back=p,
                         field_name=field_name, data=dict(err.detail, reason=err.code), prompt=prompt)

    def _target(self, params: dict) -> dict:
        history = self.releases.history()
        rid: Optional[str] = params.get("id")
        if rid is None:
            prev = self.releases.previous()
            if prev is None:
                raise self._error(rel.ReleaseError("NO_PREVIOUS"))
            return prev
        target = next((r for r in history if r["id"] == rid), None)
        if target is None or not rel.RELEASE_ID.fullmatch(rid):
            raise self._error(rel.ReleaseError("NOT_FOUND", {"available_ids": [r["id"] for r in history]}))
        if target["active"]:
            raise self._error(rel.ReleaseError("ALREADY_ACTIVE", {"release": rid}))
        return target

    def preview(self, ctx: Context, action_id: str, params: dict) -> Preview:
        active = self.releases.active()
        if action_id == "install":
            try:
                commit = self.releases.resolve(params.get("commit") or "HEAD")
            except rel.ReleaseError as err:
                raise self._error(err)
            if commit == active.get("commit"):
                raise self._error(rel.ReleaseError("ALREADY_ACTIVE", {"commit": commit}))
            repo = self.releases.repo_state()
            return Preview(
                screen="release.install", title=sys_text("Install AgentDeck {c}", c=commit[:7]),
                data={"commit": commit, "repository": repo, "active": active,
                      "changed_files": self.releases.changed_files(commit)},
                changes=["The commit is extracted to /opt/agentdeck-versioni and its tests run there; if they fail "
                         "nothing else happens",
                         "A snapshot of the system is taken, then /opt/agentdeck switches atomically to the new version",
                         "System steps: deck command, pacman hook, session unit, Claude Code configuration "
                         "(/etc/claude-code, output style, user settings with bypass, skills, MCP)",
                         "Checks: deck status, deck mcp, the guard still refuses cutting access, sshd active; if one "
                         "fails, the previous version comes back by itself"],
                untouched=["Running Claude sessions and agentdeck-claude: the new configuration applies to sessions "
                           "started later",
                           "The screen and the graphical interface (refused if they changed)",
                           "The previous version, kept for revert"],
                undo="`deck release revert` goes back to the previous version; the snapshot covers the rest",
                reboot_required=False,
                prompt=lambda t: sys_text("Check data.changed_files and data.repository.uncommitted_changes (only "
                                          "committed work is installed). To proceed repeat the call with "
                                          "confirm={t} added, within 5 minutes.", t=t))
        target = self._target(params)
        return Preview(
            screen="release.revert", title=sys_text("Go back to AgentDeck {id}", id=target["id"]),
            data={"target": target, "active": active},
            changes=["A snapshot of the system is taken, then /opt/agentdeck switches atomically to data.target",
                     "The system steps of data.target run again, then the same checks as install; if one fails, "
                     "the version in data.active comes back by itself"],
            untouched=["Running Claude sessions", "The version in data.active, kept for a new switch",
                       "The repository"],
            undo="`deck release revert id=<id of data.active>` switches back",
            reboot_required=False,
            prompt=lambda t: sys_text("Check data.target. To proceed repeat the call with confirm={t} added, within "
                                      "5 minutes.", t=t))

    def run(self, ctx: Context, action_id: str, params: dict) -> dict:
        try:
            if action_id == "install":
                commit = self.releases.resolve(params.get("commit") or "HEAD")
                result = self.releases.install(commit, self.snapshot)
            else:
                result = self.releases.revert(self._target(params), self.snapshot)
        except rel.ReleaseError as err:
            raise self._error(err)
        if result["ok"]:
            return screen(
                screen="release.installed" if action_id == "install" else "release.reverted", path=self.path,
                title=sys_text("AgentDeck version switched"), status="done", back=self.path, data=result,
                actions=self.actions(ctx),
                prompt=sys_text("data.release is now active and every check in data.checks passed. Claude sessions "
                                "started from now use its configuration; running ones keep theirs until restarted."))
        back_ok = bool(result.get("reverted") and result["reverted"]["ok"])
        raise DeckError(
            "FAILED", sys_text("The new version failed its checks."), title=sys_text("Version switch failed"),
            path=self.path, back=self.path, data=result,
            prompt=sys_text("data.steps and data.checks show what failed, as data. The previous version is active "
                            "again and its checks passed." if back_ok else
                            "data.steps and data.checks show what failed, as data. The automatic return did NOT pass "
                            "its checks (data.reverted): check ssh and `deck status` now, and use `deck snapshot "
                            "rollback id=<data.snapshot>` if the system is broken."))
