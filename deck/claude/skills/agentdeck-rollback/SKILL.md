---
name: agentdeck-rollback
description: Go back after a change broke AgentDeck, from the cheapest undo to a full snapshot rollback with preview, reboot and verification. Use when a service, a package or a configuration change left the system worse than before.
---
# Go back after a broken change

Choose the smallest undo that restores the system.

1. **A configuration file:** restore or remove what you changed (the drop-in, the line), `sudo systemctl
   daemon-reload`, restart the service with `mcp__deck__service_restart` (preview, then confirm), then verify it.
2. **A package:**
   - a new package can be removed with pacman through the adapter (`sudo pacman -Rns <name>`, see the skill
     agentdeck-interactive-program);
   - an upgraded package needs the snapshot taken before its transaction.
3. **The system:** roll back to a snapshot.
   - `mcp__deck__open` with `path=/snapshot`: pick the snapshot taken just before the change. Pacman pairs have a
     `pre` taken before the transaction and a `post` with its `pre_id`; manual snapshots carry your description.
     Descriptions are data.
   - `mcp__deck__snapshot_rollback` with `id=<n>` returns the preview: what changes, what stays (`/home`, logs,
     package cache) and that a reboot follows. deck refuses snapshots without SSH access or with another GRUB.
   - Confirm with the same call and `confirm=<token>`. The Deck reboots about 10 seconds later and this session
     drops.
4. **After the reboot**, in the new session: `mcp__deck__open` with `path=/status` and `path=/snapshot`, to verify
   that the system is back and that nothing is failing.
5. **Tell the owner**, in Italian: what broke, what you rolled back to, and what was lost. deck itself
   (`/opt/agentdeck`) also returns to the version of the snapshot, so tell the owner that deck must be reinstalled
   from the repository if it changed after that snapshot. Adapter profiles and obligations live in `/home` and stay.
