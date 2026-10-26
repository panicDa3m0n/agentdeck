---
name: agentdeck-update-system
description: Update Arch Linux on AgentDeck with deck update, which checks, previews, takes snapshots before and after, verifies services and access, and handles the reboot. Use when the owner asks for updates, when an alert says updates are pending or unchecked, or before installing a package on an old system.
---
# Update the system

Never run `pacman -Syu` directly: deck update does the same with the system's safety net.

1. **Check:** `mcp__deck__update_check`. Read the list of packages and the flags:
   - `reboot_required`: the kernel or firmware changes;
   - `grub`: GRUB changes and gets reinstalled;
   - `access_packages`: packages your access depends on, such as openssh.
2. **Apply:** `mcp__deck__update_apply` returns the preview. Check it, then repeat with `confirm=<token>`. The update
   runs in its own unit with snapshots before and after, so a dropped session does not stop it.
3. **Verify:** `mcp__deck__update_verify` checks the access services, the services that failed after the update, the
   kernel modules and the new `.pacnew` files. Read `data.verification.problems` and handle each one; merge each
   `.pacnew` with care, since it may be a configuration your access depends on.
4. **Reboot**, if required: `mcp__deck__update_reboot`, with preview and confirm. After reconnecting, run
   `mcp__deck__update_verify` again, then `mcp__deck__open` with `path=/status`.
5. **Obligations:** an update can install new packages, and then the system opens `PROFILE_NEEDED` obligations
   (skill agentdeck-alerts-and-obligations).
6. **Report to the owner**, in Italian: how many packages, the important ones (kernel, systemd, openssh), the
   snapshot pair, the reboot, and the result of the verification.
