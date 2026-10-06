# Code conventions

Match the surrounding code rather than importing outside style: its naming, its
comment density, its idioms.

- Type hints on anything public. Comments are full sentences and explain
  reasoning, not mechanics. Private helpers are `_prefixed`, or whatever the
  repository already does.
- Limit comments by default. Add one when it captures a non-obvious *why*: a
  constraint, an invariant, a workaround. Never add a comment restating what
  the identifier and structure already say.
- Prefer clear, boring code over clever code. Optimise for the next reader.
- Configuration comes from the environment with a default that matches what the
  deployment config sets.
- **No new runtime dependency without asking.** Manifests and lockfiles are
  edited through the package manager, never by hand, and with the version CI
  pins. An older local tool can silently rewrite the lockfile format and turn a
  one-line change into a whole-file diff.
- Avoid backwards-compatibility shims, unused `_var` renames, re-exported dead
  types, or "removed" comments unless compatibility is an actual requirement.
  Delete dead code outright when it is clearly unused.
- Do not reformat unrelated code.

## Prefer the general rule to the special case

A component should expose what varies as parameters with sensible defaults, so
the next use retunes it by overriding a value rather than by copying the rule
and editing the copy. Name it for what it is, not for where it first appeared.

**One number, one job.** If a value is doing two jobs at once, give the second
job its own name before you change either.

## Version bumps

**Never bump the version without first asking which bump is meant and
confirming the exact resulting number.** "Bump minor" is not enough on its own.
Say the specific transition back ("0.3.1 to 0.4.0") and get a yes before
touching any file.

A wrong guess is not a one-line fix: it means re-editing every manifest,
regenerating the lockfile, and throwing all of it away. This applies every
time, not just the first time in a session.
