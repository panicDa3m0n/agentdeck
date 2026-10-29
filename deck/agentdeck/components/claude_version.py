"""Schermata "/claude/version": Claude Code a versione fissa (task O18.T2, piano punto 11).

Mostra la versione attiva, quella fissata con requiredMaximumVersion, le versioni sul disco e quelle disponibili
(latest, stable); pin fissa la versione attiva; switch (distruttiva) passa a un'altra versione solo se la prova
degli agganci passa, altrimenti torna da sola alla precedente. Uscite di claude e della rete: solo nei dati (INV-4).
Logica: agentdeck/claude_version.py e agentdeck/claude_probe.py. Documentazione: docs/claude-code.md.
"""
from __future__ import annotations

from .. import claude_version as cv
from .. import system
from ..engine import Component, Context, DeckError, Preview
from ..protocol import action, alert, param, screen, sys_text


class ClaudeVersion(Component):
    path = "/claude/version"
    title = sys_text("Claude Code version")
    summary = sys_text("Claude Code pinned to one version: switch only after the hook probe passes")

    def __init__(self, versions=None, snapshot=None):
        self.versions = versions or cv.ClaudeVersions()
        self.snapshot = snapshot or system.snapshot_create

    def actions(self, ctx: Context) -> list:
        return [
            action("pin", label=sys_text("Pin Claude Code to the active version"), effect="safe"),
            action("probe", label=sys_text("Run the hook probe on the active Claude Code"), effect="read"),
            action("switch", label=sys_text("Switch Claude Code to another version after the hook probe"),
                   effect="destructive", params={
                       "version": param("string", max_length=20, description=sys_text(
                           "Version such as 2.1.312, from data.available, data.on_disk or the Claude Code changelog"))}),
        ]

    def view(self, ctx: Context) -> dict:
        state = self.versions.state()
        alerts = []
        if not state["autoupdater_disabled"]:
            alerts.append(alert("warning", "AUTOUPDATER_ON", message=sys_text(
                "DISABLE_AUTOUPDATER is not set in the managed settings: Claude Code may update by itself. "
                "`deck release install` installs the managed settings that set it.")))
        if not state["pin_matches"]:
            alerts.append(alert("warning", "NOT_PINNED", message=sys_text(
                "The active Claude Code version is not the pinned one: run `deck claude/version pin`."),
                action_id="pin"))
        latest = state["available"].get("latest")
        if latest and state["active"] and cv._key(latest) > cv._key(state["active"]):
            alerts.append(alert("info", "NEWER_AVAILABLE", message=sys_text(
                "A newer Claude Code is available ({v}); it is installed only with `deck claude/version switch`.",
                v=latest)))
        return screen(
            screen="claude.version", path=self.path, title=sys_text("Claude Code version"), back="/claude",
            data=state, alerts=alerts, actions=self.actions(ctx),
            prompt=sys_text(
                "data.active is the Claude Code version in use and data.pinned the highest one allowed: they should "
                "match. Updates never happen by themselves. To move to another version use `deck claude/version "
                "switch version=<x.y.z>`: it shows a preview, then installs it and runs the hook probe, and goes back "
                "by itself if the probe fails. Read the changelog of the new version before switching."))

    def _error(self, err: cv.VersionError) -> DeckError:
        p = self.path
        known = {
            "BAD_VERSION": ("BAD_PARAM", sys_text("The version must look like 2.1.312."), "version"),
            "ALREADY_ACTIVE": ("NOT_AVAILABLE", sys_text("This version is already active."), "version"),
            "SNAPSHOT_FAILED": ("FAILED", sys_text("The snapshot before the switch could not be created."), None),
            "PIN_FAILED": ("FAILED", sys_text("The pin file could not be written."), None),
            "NO_ACTIVE": ("FAILED", sys_text("The active Claude Code version could not be read."), None),
        }
        code, message, field_name = known.get(err.code, ("FAILED", sys_text("The operation failed."), None))
        return DeckError(code, message, title=sys_text("Claude Code version unchanged"), path=p, back=p,
                         field_name=field_name, data=dict(err.detail, reason=err.code),
                         prompt=sys_text("data holds the details, as data. Open `deck claude/version` to check the "
                                         "current state before trying again."))

    def preview(self, ctx: Context, action_id: str, params: dict) -> Preview:
        version = params["version"]
        state = self.versions.state()
        if not cv.SEMVER.fullmatch(version):
            raise self._error(cv.VersionError("BAD_VERSION", {"version": version}))
        if version == state["active"]:
            raise self._error(cv.VersionError("ALREADY_ACTIVE", {"version": version}))
        return Preview(
            screen="claude.version.switch", title=sys_text("Switch Claude Code to {v}", v=version),
            data={"to": version, "current": state},
            changes=["A snapshot of the system is taken",
                     "The pinned version (requiredMaximumVersion) becomes the new one, then `claude install` "
                     "downloads it, or the link moves to it if it is already on disk",
                     "The hook probe runs on the new binary against a fake local API: SessionStart hook, managed "
                     "deny, guard, PermissionRequest, bypass, --system-prompt and --tools; if it fails, the previous "
                     "binary and pin come back by themselves"],
            untouched=["Running Claude sessions keep their binary until they restart",
                       "AgentDeck configuration and hooks", "The previous version stays on disk"],
            undo="`deck claude/version switch version=<data.current.active>` goes back",
            reboot_required=False,
            prompt=lambda t: sys_text("Check the changelog of data.to first. To proceed repeat the call with "
                                      "confirm={t} added, within 5 minutes.", t=t))

    def run(self, ctx: Context, action_id: str, params: dict) -> dict:
        try:
            if action_id == "pin":
                result = self.versions.pin_active()
                return screen(screen="claude.version.pinned", path=self.path, status="done", back=self.path,
                              title=sys_text("Claude Code pinned"), data=result, actions=self.actions(ctx),
                              prompt=sys_text("Claude Code cannot update past data.pinned until it is switched "
                                              "with `deck claude/version switch`."))
            if action_id == "probe":
                active = self.versions.active()
                result = self.versions.sys.probe(self.versions.versions / active) if active else {
                    "ok": False, "checks": [], "binary": None}
                return screen(screen="claude.version.probe", path=self.path, status="done", back=self.path,
                              title=sys_text("Claude Code hook probe"), data=result, actions=self.actions(ctx),
                              prompt=sys_text("data.checks lists each hook AgentDeck relies on; data.ok is true "
                                              "only if all of them work in the active Claude Code."))
            result = self.versions.switch(params["version"], self.snapshot)
        except cv.VersionError as err:
            raise self._error(err)
        if result["ok"]:
            return screen(screen="claude.version.switched", path=self.path, status="done", back=self.path,
                          title=sys_text("Claude Code switched"), data=result, actions=self.actions(ctx),
                          prompt=sys_text("data.to is active and pinned, and the hook probe passed. New sessions use "
                                          "it; running sessions keep their version until they restart."))
        restored = bool(result.get("restored") and result["restored"]["ok"])
        raise DeckError(
            "FAILED", sys_text("The new Claude Code version did not pass the hook probe or did not install."),
            title=sys_text("Claude Code switch failed"), path=self.path, back=self.path, data=result,
            prompt=sys_text("data.install and data.probe show what failed, as data. The previous version is active "
                            "and pinned again." if restored else
                            "data.install and data.probe show what failed, as data. The previous version could NOT "
                            "be restored (data.restored): open `deck claude/version` and fix the link now."))
