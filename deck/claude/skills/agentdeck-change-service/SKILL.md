---
name: agentdeck-change-service
description: Change a systemd service or its configuration on AgentDeck safely, with a snapshot, a drop-in instead of vendor files, a confirmed restart and a verification of state and logs. Use when the owner asks to configure, start, stop, restart, enable or disable a service.
---
# Change a service on AgentDeck

1. **Read the service:** `mcp__deck__service_show` with `name=<unit>`.
   - If `data.protected` is true, the service keeps your access to the Deck (SSH, network, Wi-Fi, name resolution,
     system bus): stop and disable are refused. Change its configuration only through the deck actions that
     protect access, or with a safety net that reverts by itself.
   - Units `agentdeck-servizio@<name>` are the owner's services: starting, stopping, enabling or changing them asks
     the owner for permission (ADR-0001). Every other service is yours to change.
2. **Snapshot:** `mcp__deck__snapshot_create` with a description of what you are about to change.
3. **Change the configuration with a drop-in**, never the vendor file in `/usr/lib/systemd`:
   `/etc/systemd/system/<unit>.d/override.conf` for the unit, or the program's own `.d` directory in `/etc` when
   it has one. Write only what changes, with a comment on why. Then run `sudo systemctl daemon-reload`.
4. **Apply:** `mcp__deck__service_restart` with `name=<unit>`. It answers with a preview of what stops and what
   depends on it: check it, then repeat the call with `confirm=<token>`. Use `mcp__deck__service_start`,
   `mcp__deck__service_stop`, `mcp__deck__service_enable` and `mcp__deck__service_disable` the same way; enable and
   disable take a snapshot by themselves.
5. **Verify:**
   - `mcp__deck__service_show`: `ActiveState` must be `active` (or what you intended) and `Result` `success`;
   - `mcp__deck__logs_query` with `unit=<unit>`, `since=5m` and `priority=warning`: no new errors.
6. **If it broke:** remove or fix the drop-in, `daemon-reload`, restart again. If the system is still wrong, go
   back to the snapshot (skill agentdeck-rollback).
7. **Report to the owner**, in Italian: what changed and why, the file, the snapshot id, and the verification.
