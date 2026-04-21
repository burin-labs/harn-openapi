# AGENTS.md — harn-openapi

**Read [SESSION_PROMPT.md](./SESSION_PROMPT.md) first.** It contains the
pivot context, what's blocked, what's unblocked, and the v0 milestones.

## Quick repo conventions

- File extension: `.harn`. Use `snake_case` for filenames (e.g. `parse_paths.harn`).
- Repo directories use `kebab-case` (already applied to this repo).
- Entry point: `src/lib.harn`.
- Tests live under `tests/` and `conformance/` (paired `.harn` + `.expected`
  fixtures, mirroring upstream harn conventions).
- Pinned external fixtures live under `tests/fixtures/` (e.g. the Notion
  OpenAPI spec snapshot).

## How to test

Until `harn add` ships
([harn#345](https://github.com/burin-labs/harn/issues/345)), drive everything
through the upstream binary:

```sh
cd /Users/ksinder/projects/harn
cargo run --quiet --bin harn -- run /Users/ksinder/projects/harn-openapi/tests/smoke.harn
cargo run --quiet --bin harn -- check /Users/ksinder/projects/harn-openapi/src/lib.harn
cargo run --quiet --bin harn -- lint /Users/ksinder/projects/harn-openapi/src/lib.harn
cargo run --quiet --bin harn -- fmt --check /Users/ksinder/projects/harn-openapi/src/lib.harn
```

## Upstream conventions

For general Harn coding conventions and the broader project layout, defer to
[`/Users/ksinder/projects/harn/AGENTS.md`](/Users/ksinder/projects/harn/AGENTS.md).
The Harn quickref autoload lives in `.Codex/skills/harn-scripting/SKILL.md`
inside that repo and is the fastest way to get oriented on syntax.

## Don't

- Don't add a Cargo workspace, package.json, or any non-Harn build tooling
  to this repo. It's pure Harn.
- Don't hand-edit `LICENSE-*` or `.gitignore`.
