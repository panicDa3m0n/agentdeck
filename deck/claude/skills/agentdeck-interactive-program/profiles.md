# Writing an adapter profile

A profile teaches the adapter the questions of one program and the data to extract from its output. The format,
with an example, is in `data.profile_format` of `mcp__deck__open` with `path=/term`.

## Rules

- `program`: the lowercase name of the executable, as the adapter derives it from the command (`sudo`, `env`,
  `nice`, `timeout` and variable assignments are skipped).
- `questions`: Python regular expressions, searched in the last 8 non-empty lines up to the cursor.
  - A rule counts only when its match **ends on the cursor line**, the question being asked now. A question already
    answered, still visible above, does not win. Anchor with `\s*$` when the prompt ends the line.
  - The first rule that counts wins: put specific rules before general ones.
  - `type`: `confirm`, `choice`, `text`, `secret`, `menu`, `pager` or `unknown`. Mark every password or passphrase
    prompt as `secret`.
  - Named groups go to `question.fields`; a group named `default` gives the default answer.
  - `options`: fixed options as objects with `key` and `label`. `options_pattern` extracts them, with the named group
    `key` and optionally `label`.
- `parse`: rules searched in the whole output; named groups go to `data.parsed.<name>`, and `all: true` keeps every
  match. Extract what you will check after the program ends: sizes, paths, counts, errors.
- `description`: what the program is and which questions it asks, in plain words. `author`: `agent`.

## Workflow

1. Start the program in a session and bring it to the question you want to recognize.
2. Draft the profile and test it on the current screen: `mcp__deck__term_profile_test` with `id=<session>` and
   `profile=<the JSON>`. Repeat until `data.matched_by_profile` is true and `data.question` has the right type,
   options and fields.
3. Move the program to its next question and test again: every question the profile knows should match.
4. Save it: `mcp__deck__term_profile_save` with `profile=<the JSON>`. The answer shows what it recognizes now in
   the open sessions of that program.
5. Check it with `mcp__deck__term_profile_show`. If a `PROFILE_NEEDED` obligation listed the program, the obligation
   closes by itself once every program of the package has a profile.
