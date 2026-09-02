# Contributing

`harn-openapi` parses OpenAPI 3.1 documents and generates typed Harn SDK source
and tool registries from them. Downstream packages such as
[notion-sdk-harn](https://github.com/burin-labs/notion-sdk-harn) install it and
regenerate their client from it, so a change to the generator changes their
generated code. Contributions are welcome. Read this page first, because a few
of the rules here are not obvious from the source.

## What belongs here

This package owns OpenAPI parsing, schema walking, security metadata, and typed
Harn codegen for a focused API backed by one OpenAPI document.

These do not belong here:

- broad cloud SDK families and provider discovery formats;
- Smithy and other non-OpenAPI description languages;
- provider-specific authentication flows.

Put those in a package above this layer. If you are unsure which side of the
line your idea falls on, open an issue before you write code.

## Repository rules

- This is a pure Harn package. Do not add a Cargo workspace, a `package.json`,
  or a generated build system. The repository has no non-Harn runtime
  dependency and keeping it that way is the point.
- The default export is `src/lib.harn`.
- Name `.harn` files in `snake_case` and directories in `kebab-case`.
- Tests live in `tests/*.harn` and fixtures in `tests/fixtures/`.
- Do not hand-edit `LICENSE-APACHE`, `LICENSE-MIT`, or `.gitignore`.

## Set up and run the gate

Install the Harn CLI version pinned in `.harn-version`, then run the same checks
CI runs:

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

`HARN_BIN` points generated-code tests at the same CLI version running the
suite. The two smoke scripts need `--no-sandbox` only because they spawn child
Harn processes. The CI job sandbox is still the authority boundary.

A change to documentation alone does not need the full gate.

## Leave the pinned fixture alone

`tests/fixtures/notion.openapi.json` is a pinned snapshot of a real Notion
OpenAPI document. It is what keeps coverage deterministic, so an unrelated
change that refreshes it makes every diff unreadable.

Refresh it only when refreshing it is the task:

```sh
cp tests/fixtures/notion.openapi.json /tmp/notion.openapi.old.json
harn run scripts/refresh_fixtures.harn
harn run scripts/fixture_diff.harn -- \
  /tmp/notion.openapi.old.json \
  tests/fixtures/notion.openapi.json
harn run scripts/check_fixture_staleness.harn
```

Commit the fixture and its `.meta.toml` together. The staleness check is quiet
under 90 days, warns from 90 to 180 days, and fails a non-`main` branch after
180 days.

## Open the pull request

Title it `[Area] Sentence case description`. `AGENTS.md` lists the ten areas and
how to pick one. Keep the description to 3-5 sentences: what changed, why, the
one risk, and how you verified it. `.github/pull_request_template.md` has a
worked example.

If your change alters generated output, say so in the description and name what
a downstream consumer has to do. That is the part a reviewer cannot see from the
diff.

## Write documentation to house style

Any Markdown page you add or change follows the Burin Labs
[house-style skill](https://github.com/burin-labs/.github/blob/main/skills/house-style/SKILL.md):
one Diataxis mode per page, second person, sentence-case headings, no em dashes,
and a named verification for every claim.

## Labels

`.github/labels.yml` is this repository's label taxonomy. The priority, status,
and effort categories are copied from
[`burin-labs/.github`](https://github.com/burin-labs/.github/blob/main/.github/labels.yml)
and are not edited here. The `area/*` labels use the same words as the pull
request title areas.

## License

The repository is dual-licensed under Apache 2.0 and MIT. By contributing, you
agree that your contribution is licensed the same way.
