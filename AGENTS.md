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

Install the pinned Harn CLI from crates.io, then run the local gate:

```sh
cargo install harn-cli --version "$(cat .harn-version)" --locked
harn check src scripts
harn lint src scripts
harn fmt --check src scripts tests
for test in tests/*.harn; do
  harn run "$test" || exit 1
done
harn run scripts/regen_demo.harn
```

## Fixture refresh workflow

The Notion OpenAPI fixture is pinned for deterministic tests. Refresh it only
when intentionally updating the snapshot:

```sh
cp tests/fixtures/notion.openapi.json /tmp/notion.openapi.old.json
cd /Users/ksinder/projects/harn
cargo run --quiet --bin harn -- run /Users/ksinder/projects/harn-openapi/scripts/refresh_fixtures.harn
cargo run --quiet --bin harn -- run /Users/ksinder/projects/harn-openapi/scripts/fixture_diff.harn -- \
  /tmp/notion.openapi.old.json \
  /Users/ksinder/projects/harn-openapi/tests/fixtures/notion.openapi.json
```

Commit the updated JSON and `tests/fixtures/notion.openapi.json.meta.toml`
together. CI runs `scripts/check_fixture_staleness.harn`: under 90 days is OK,
90–180 days prints a warning, and over 180 days fails non-`main` branches while
warning on `main`.

## Upstream conventions

For general Harn coding conventions and the broader project layout, defer to
[`/Users/ksinder/projects/harn/AGENTS.md`](/Users/ksinder/projects/harn/AGENTS.md).
The Harn quickref autoload lives in `.Codex/skills/harn-scripting/SKILL.md`
inside that repo and is the fastest way to get oriented on syntax.

## Don't

- Don't add a Cargo workspace, package.json, or any non-Harn build tooling
  to this repo. It's pure Harn.
- Don't hand-edit `LICENSE-*` or `.gitignore`.
