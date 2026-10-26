---
name: agentdeck-install-package
description: Install an Arch Linux package on AgentDeck the system's way, through the adapter, with snapshots, the obligations it creates and a verification. Use whenever the owner asks to install software or a task needs a program that is missing.
---
# Install a package on AgentDeck

Packages change the system: pacman runs through the adapter so you read its questions as data, snap-pac takes a
snapshot before and after the transaction, and the system then gives you an obligation for the new programs.

1. **Check the state first.** `mcp__deck__open` with `path=/status`: handle critical alerts before installing.
   Never run `pacman -Sy <package>` alone: on Arch a database refresh without the upgrade is a partial upgrade.
   If the package database is old, update the system first (skill agentdeck-update-system).
2. **Look the package up**, read-only: `pacman -Si <name>` (or `pacman -Ss <words>` to search).
3. **Install through the adapter:** `mcp__deck__term_start` with `command=sudo pacman -S <name>` and `wait_s=20`.
   The pacman profile fills `data.parsed` (packages, download and installed size) and recognizes the question.
   - Read `data.parsed.packages`: only what you expected, plus dependencies.
   - If pacman asks to replace or remove packages, or reports conflicts, decide yourself: the system is yours, and
     snap-pac takes a snapshot. Stop and interrupt only if the change would remove what one of the owner's services
     in `/srv/servizi` needs: that service is the owner's, so ask before going on.
   - Otherwise answer with `mcp__deck__term_choose`, `option=y`.
4. **Wait for the end** with `mcp__deck__term_wait`: the session must be `exited` with `exit_status` 0 and no
   `data.parsed.errors`. Close it with `mcp__deck__term_close` (preview, then `confirm=<token>`).
5. **Fulfil the obligation.** A `PROFILE_NEEDED` obligation appears in the `obligations` field of the next screens
   for the programs the package installed without an adapter profile.
   - For each program in its `subject.programs`, find out whether it asks questions: its `--help`, its man page
     (`man -f <program>`), or run it in `mcp__deck__term_start` and see whether the session ends up
     `waiting_input`.
   - Write a profile for each program that asks questions (skill agentdeck-interactive-program, profiles.md).
   - Close the obligation with `mcp__deck__obligations_done`, with a note naming the programs that ask nothing.
6. **Verify**: `mcp__deck__open` with `path=/status`, no new alerts. If the package brought a service, read it with
   `mcp__deck__service_show`; enable it if the task needs it.
7. **Report to the owner**, in Italian: package and version, the snapshot pair (`mcp__deck__open` with
   `path=/snapshot`, the last pre and post), the obligation and how you closed it.
