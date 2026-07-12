# AGENTS.md - harn-openapi

Use this with [README.md](./README.md). This file is the current source of
truth for coding-agent instructions in this repo.

## Repo rules

- This is a pure Harn package. Do not add a Cargo workspace, `package.json`, or
  generated build system.
- The package default export is `src/lib.harn`.
- Use `.harn` files with `snake_case` names. Keep directories `kebab-case`.
- Tests live in `tests/*.harn`. Fixtures live in `tests/fixtures/`.
- Keep the Notion OpenAPI fixture pinned. Refresh it only when the task asks
  for a fixture refresh.

## Harn references

- For repo-wide Harn conventions, use the
  [Harn agent guide](https://github.com/burin-labs/harn/blob/main/AGENTS.md).
- For syntax, use the
  [Harn quick reference](https://github.com/burin-labs/harn/blob/main/docs/llm/harn-quickref.md).
- Before editing Harn code, run `harn skill list --json` and fetch the
  narrowest matching skill with `harn skill get <name> --full`.

## Local gate

Install the pinned CLI, then run the same checks CI cares about:

```sh
cargo install harn-cli --version "$(cat .harn-version)" --locked
harn check src scripts
harn lint src scripts
harn fmt --check src scripts tests
harn package check
HARN_BIN="$(command -v harn)" harn test tests --parallel --timing
harn run scripts/regen_demo.harn
HARN_BIN="$(command -v harn)" harn run --no-sandbox scripts/package_install_smoke.harn
harn run scripts/check_fixture_staleness.harn
```

`HARN_BIN` lets generated-code tests shell out to the same CLI version that is
running the suite.

## Fixture refresh

Refresh the Notion fixture only for deliberate snapshot updates:

```sh
cp tests/fixtures/notion.openapi.json /tmp/notion.openapi.old.json
harn run scripts/refresh_fixtures.harn
harn run scripts/fixture_diff.harn -- \
  /tmp/notion.openapi.old.json \
  tests/fixtures/notion.openapi.json
harn run scripts/check_fixture_staleness.harn
```

Commit `tests/fixtures/notion.openapi.json` and
`tests/fixtures/notion.openapi.json.meta.toml` together. The staleness check is
quiet under 90 days, warns from 90 to 180 days, and fails non-`main` branches
after 180 days.

## Do not

- Do not hand-edit `LICENSE-*` or `.gitignore`.
- Do not auto-refresh external fixtures during unrelated work.
- Do not publish docs that require a sibling checkout unless the section is
  explicitly about local multi-repo development.
