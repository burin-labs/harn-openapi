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

## Pull requests

Title every pull request `[Area] Sentence case description`. Capitalize the
first word of the description and proper nouns only, and leave the trailing
period off.

`Area` is one of these, taken from the repository layout table in
[README.md](./README.md):

| Area | Covers |
| --- | --- |
| `Parser` | Parsing OpenAPI 3.1 documents into normalized Harn records |
| `Types` | The typed public surface and its aliases |
| `Codegen` | Generating typed Harn SDK source |
| `Adapters` | Tool registry generation and the `x-harn` extension |
| `Connector` | Helpers for auth, pagination, and rate limits |
| `Fixtures` | `tests/fixtures/`, refresh, diff, and staleness |
| `Packaging` | `harn.toml`, the `.harn-version` pin, and releases |
| `CI` | This repository's workflows and required checks |
| `Docs` | `README.md`, `AGENTS.md`, `CONTRIBUTING.md`, and `docs/` |
| `Tests` | `tests/` coverage outside the fixtures themselves |

Pick the area that owns the behavior you changed, not the file you touched most.
`src/lib.harn` holds the parser, the walker, and the generator, so a change
inside it can be `[Parser]`, `[Codegen]`, or `[Adapters]`. If two areas fit, the
pull request is probably two pull requests.

Keep the description to 3-5 sentences: what changed, why, the one risk, and how
you verified it. Do not list the gate commands. `.github/pull_request_template.md`
carries a worked example.

The same words are the `area/*` labels in `.github/labels.yml`, so a title and a
label agree.

<!-- BEGIN HARN SHARED AGENT CONTRACT: managed by harn-bump-fleet -->

## Ecosystem working agreement

- Pursue the ambitious product outcome; make the seams boring with small typed
  interfaces, explicit invariants, and deterministic projections.
- Give each behavior one semantic owner. Generate or parity-test other surfaces
  instead of maintaining competing implementations.
- Work autonomously inside approved scope. Pause for destructive, production,
  high-spend, ambiguous, or authority-expanding actions—not routine reversible work.
- Treat stop, wait, stand down, and pivot as control events for long-lived work.
- Match evidence to the claim: exercise the canonical user path, state the
  falsifier, verify liveness and recovery, and record residual blind spots.
- "Ship" means landed on main with required deploy and post-merge checks complete.

<!-- END HARN SHARED AGENT CONTRACT -->
