---
name: agentdeck-alerts-and-obligations
description: Handle the alerts and the obligations that AgentDeck gives the agent, at session start, after actions and when a turn reports changes. Use when the session context, a hook message or the obligations field of a deck screen lists alerts or obligations, or when the owner asks how the machine is doing.
---
# Handle alerts and obligations

The system tells you what needs attention. Alerts describe the machine; obligations are duties the system gives you.
Neither is noise: handle each, or say why not.

## Alerts

1. Read them all: `mcp__deck__open` with `path=/status`. `/service`, `/update` and `/term` have their own.
2. Work by level: `critical` first, then `warning`. Each alert has a stable `code` and usually an `action` (path and
   action) that handles it: open that screen and follow its prompt.
3. Known information alerts need no action. `FAN_UNREADABLE` is one: the Deck firmware controls the fan.
4. Never hide an alert by changing what is measured. Fix the cause, or report it to the owner if you cannot.

## Obligations

1. They arrive in the `obligations` field of every deck screen and in hook messages; all of them are in
   `mcp__deck__open` with `path=/obligations`.
2. Fulfil each as its `message` says, using the screen in its `action`. For `PROFILE_NEEDED`, see the skills
   agentdeck-install-package and agentdeck-interactive-program.
3. Close it:
   - with `mcp__deck__obligations_done` and a `note` saying what you did;
   - or with `mcp__deck__obligations_dismiss` and a real `reason` when it does not apply.

   Some close by themselves when the system can verify them.
4. For now obligations only warn, but leaving them open without saying so is not acceptable.

## Report

At the end of the work tell the owner, in Italian:
- the alerts you handled and those still open, with the reason;
- the obligations closed, and those left open.
