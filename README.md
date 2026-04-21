# harn-openapi

Pure-Harn library for parsing OpenAPI 3.1 documents and generating typed Harn
SDK source code from them. Acts as the reference example of a non-trivial
external Harn library and powers downstream typed SDKs such as
[notion-sdk-harn](https://github.com/burin-labs/notion-sdk-harn).

> **Status: pre-alpha** — actively developed in tandem with
> [burin-labs/harn](https://github.com/burin-labs/harn). See the
> [Pure-Harn Connectors Pivot epic #350](https://github.com/burin-labs/harn/issues/350).

## Intent

`harn-openapi` is the OpenAPI layer for Harn's external connector ecosystem.
Provider-specific SDKs and connectors should not each learn OpenAPI parsing,
schema walking, security handling, or typed SDK generation independently. This
repo keeps that shared logic in one pure-Harn package:

- parse OpenAPI 3.1 JSON into normalized Harn records;
- walk paths, webhooks, components, schemas, enums, and security metadata;
- generate typed Harn SDK source for downstream provider repos;
- keep a pinned real-world Notion OpenAPI fixture for deterministic coverage.

The repo intentionally has no Cargo workspace, `package.json`, generated build
system, or non-Harn runtime dependency. Harn package management is not available
yet, so consumers currently use a local `harn.toml` path dependency.

## Repository Layout

| Path | Purpose |
|---|---|
| `harn.toml` | Package metadata and exported entry points. `src/lib.harn` is the default export and `src/types.harn` exports shared types. |
| `src/lib.harn` | Public parser, walker, schema-resolution, and SDK codegen implementation. |
| `src/types.harn` | Type aliases used by the public surface and tests. |
| `tests/*.harn` | Smoke and behavior tests for parsing, walking, codegen, security, response typing, polymorphic request bodies, fixture tooling, and helper scripts. |
| `tests/fixtures/notion.openapi.json` | Pinned Notion OpenAPI 3.1 snapshot used as the main real-world fixture. |
| `tests/fixtures/notion.openapi.json.meta.toml` | Capture metadata for the pinned fixture: upstream URL, timestamp, byte size, and SHA-256. |
| `scripts/regen_demo.harn` | End-to-end parse to codegen demo that writes generated SDK source to `/tmp`. |
| `scripts/refresh_fixtures.harn` | Refreshes the pinned Notion fixture and metadata intentionally. |
| `scripts/fixture_diff.harn` | Prints a structured operation/schema diff between two fixture captures. |
| `scripts/check_fixture_staleness.harn` | CI guard for fixture age. |
| `scripts/bump_harn_cli_version.harn` | Updates the pinned crates.io `harn-cli` version in GitHub Actions and runs the local gate. |
| `.github/workflows/ci.yml` | Main Harn check/lint/fmt/test/demo workflow. |
| `.github/workflows/fixture-staleness.yml` | Lightweight fixture freshness workflow. |
| `SESSION_PROMPT.md` | Historical project bootstrap and v0 milestone context. |
| `AGENTS.md` | Repo-specific instructions for coding agents. |

## Install

Once Harn package management v0
([harn#345](https://github.com/burin-labs/harn/issues/345)) lands:

```sh
harn add github.com/burin-labs/harn-openapi@v0.1.0
```

Until then, depend on a local checkout of this repo through `harn.toml`:

```toml
[dependencies]
harn-openapi = { path = "../harn-openapi" }
```

## Usage

With either the future package install or the current `harn.toml` path
dependency, import the named functions you use:

```harn
import {
  parse,
  operations,
  webhook_operations,
  component_path_items,
  codegen_module,
} from "harn-openapi"

let raw = read_file("./notion.openapi.json")
let doc = parse(raw)

// Walk operations
let ops = operations(doc)
for op in ops {
  println("${op.method} ${op.path} -> ${op.operation_id}")
}

// Walk OAS 3.1 webhooks (inbound payloads)
for wop in webhook_operations(doc) {
  println("webhook ${wop.name} (${wop.method}) -> ${wop.operation_id}")
}

// Passthrough accessor for the 3.1-new components.pathItems map
let shared_path_items = component_path_items(doc)

// Generate Harn SDK source from the parsed document
let src = codegen_module(doc, {
  module_name: "notion",
  client_name: "Client",
})
write_file("./src/lib.harn", src)
```

When running examples or tests directly from this repository before package
management ships, use the source path instead:

```harn
import { parse } from "../src/lib"
```

### Exported surface

- `parse(json_string) -> OpenApiDoc` — normalize a 3.1.x doc to
  `{ openapi, info, servers, paths, webhooks, components,
  security_schemes, security, tags }`. `paths` may be empty (3.1 allows
  webhooks-only docs). `components.pathItems` is always present as a
  dict, even when the source doc omits it.
- `operations(doc: OpenApiDoc) -> list<Operation>` — flatten `doc.paths` into operation
  records `{ method, path, operation_id, summary, parameters,
  request_body, responses, security, tags, ... }`. Each operation's
  `security` is resolved as `op.security ?? doc.security ?? []`.
- `webhook_operations(doc: OpenApiDoc) -> list<WebhookOperation>` — flatten `doc.webhooks` into
  records `{ name, method, path_item, operation, operation_id,
  summary, parameters, request_body, responses, security, tags }`.
  `name` is the webhook key (e.g. `commentCreated`); downstream
  connectors use these to know which inbound payloads to handle.
- `component_path_items(doc: OpenApiDoc) -> dict<string, RefOr<PathItem>>` —
  passthrough accessor for `doc.components.pathItems` (new in
  OAS 3.1). Returns `{}` when absent.
- `schema(doc: OpenApiDoc, ref_or_inline: RefOr<Schema>) -> Schema` — resolve a local `$ref`, or
  return inline schemas unchanged. Merges one level of `allOf` and preserves
  `$ref` siblings as valid JSON Schema 2020-12 data.
- `enum_values(schema: Schema) -> list<string> | nil` — extract the enum variant list,
  or `nil` when the schema is not an enum.
- `is_openapi_doc(value)`, `is_reference(value)`, `is_schema(value)` — small schema guards
  for common dynamic boundaries.
- `codegen_module(doc: OpenApiDoc, options: dict) -> string` — emit a typed Harn SDK
  module source string with per-scheme security dispatch (see below).

### Security handling in generated clients

`codegen_module` inspects `components.securitySchemes` and emits a
dedicated `_headers_<scheme>(client)` helper per scheme that is actually
referenced by at least one operation. Each operation dispatches through
the helper matching its *effective* security (`op.security ?? doc.security
?? []`) — explicit `security: []` at either level routes through
`_no_auth_headers(client)` so the call goes out without an `Authorization`
header.

`new_client` takes only the client fields implied by the schemes in use,
all defaulted so callers only supply what their spec actually needs:

| Scheme kind | Client field added |
|---|---|
| `http` + `bearer`, `oauth2`, `openIdConnect` | `token: string = ""` |
| `http` + `basic` | `basic_user: string = ""`, `basic_password: string = ""` |
| `apiKey` (header / query / cookie) | `api_keys: dict = {}` (keyed by scheme name) |
| `mutualTLS` | (v0: no-op — op falls through to `_no_auth_headers`) |

So a Notion-shaped spec with `bearerAuth` + `basicAuth` yields:

```harn
new_client(
  base_url: string = "https://api.notion.com",
  token: string = "",
  basic_user: string = "",
  basic_password: string = "",
  extra_headers: dict = {"Notion-Version": "..."},
) -> dict
```

When an operation declares multiple security requirement alternatives
(`security: [{a: []}, {b: []}]`), v0 picks the first and leaves a
`NOTE` comment above the generated function listing the alternatives so
a human can retarget manually.

Out of scope for v0: full OAuth2 flows (authorization-code, device,
PKCE) and `mutualTLS` client-certificate plumbing.

### Polymorphic request bodies

For `application/json` request bodies whose top-level schema is `oneOf` or
`anyOf`, `codegen_module` emits the normal umbrella operation plus one
constructor per variant. Callers can build the body dynamically and pass it to
the umbrella, while static callers can use the variant constructor directly:

```harn
let body = update_page_markdown_insert_content({
  content: "## New section",
})
let page = update_page_markdown(client, page_id, body)
```

The constructor adds an internal `_variant` tag so the umbrella can validate
which variant was selected, then strips `_variant` before serializing the HTTP
body. When an OpenAPI discriminator mapping is present, the mapping key is used
as the `_variant` tag.

Downstream SDK wrappers can expose the same two styles as methods, e.g.
`client.update_page_markdown(body)` for dynamic dispatch and
`client.update_page_markdown_insert_content({...})` for a static variant call.

## Development

This repo is being built out by Claude Code sessions following a structured
prompt. **Read [SESSION_PROMPT.md](./SESSION_PROMPT.md) before making changes.**

The upstream Harn language and runtime live at
[burin-labs/harn](https://github.com/burin-labs/harn). For local development,
clone it next to this repo at `../harn`.

### Local checks

The GitHub workflows install `harn-cli` from crates.io, but local development
can use either a released `harn` binary or the upstream checkout. With a
released binary:

```sh
HARN_ROOT="$PWD" harn check src scripts
HARN_ROOT="$PWD" harn lint src scripts
HARN_ROOT="$PWD" harn fmt --check src scripts tests
for test in tests/*.harn; do HARN_ROOT="$PWD" harn run "$test" || exit 1; done
HARN_ROOT="$PWD" harn run scripts/regen_demo.harn
```

When using the sibling upstream checkout instead:

```sh
cd ../harn
cargo run --quiet --bin harn -- check ../harn-openapi/src ../harn-openapi/scripts
cargo run --quiet --bin harn -- lint ../harn-openapi/src ../harn-openapi/scripts
cargo run --quiet --bin harn -- fmt --check ../harn-openapi/src ../harn-openapi/scripts ../harn-openapi/tests
for test in ../harn-openapi/tests/*.harn; do cargo run --quiet --bin harn -- run "$test" || exit 1; done
cargo run --quiet --bin harn -- run ../harn-openapi/scripts/regen_demo.harn
```

### CI and merge queue

Both workflows run on pull requests, `main` pushes, merge queue
`merge_group` events, and manual dispatch. They install a pinned crates.io
`harn-cli` version with `cargo install --locked`, cache the install and cargo
registry data, and then run repo-local Harn commands.

`main` is protected by GitHub's merge queue. Changes should be pushed on a
branch, opened as a PR, and queued after checks pass. The merge queue runs the
same workflows again on GitHub's synthetic queue branch before landing the PR
on `main`.

### Fixture refresh workflow

The Notion OpenAPI fixture is intentionally pinned. To refresh it manually,
save the current fixture, run the refresh script, then review the diff report:

```sh
cp tests/fixtures/notion.openapi.json /tmp/notion.openapi.old.json
cd ../harn
cargo run --quiet --bin harn -- run ../harn-openapi/scripts/refresh_fixtures.harn
cargo run --quiet --bin harn -- run ../harn-openapi/scripts/fixture_diff.harn -- \
  /tmp/notion.openapi.old.json \
  ../harn-openapi/tests/fixtures/notion.openapi.json
```

`scripts/refresh_fixtures.harn` writes both
`tests/fixtures/notion.openapi.json` and
`tests/fixtures/notion.openapi.json.meta.toml`, including the upstream URL,
capture timestamp, byte size, and SHA-256. CI runs
`scripts/check_fixture_staleness.harn`; it is quiet under 90 days old, warns
between 90 and 180 days, and fails non-`main` branches once the fixture is over
180 days old.

### Harn CLI version bumps

GitHub Actions pins `harn-cli` from crates.io in
`.github/workflows/ci.yml` and `.github/workflows/fixture-staleness.yml`.
When a new Harn release is published, update both pins and run the local gate
with:

```sh
harn run scripts/bump_harn_cli_version.harn -- 0.7.30
```

The script accepts a leading `v` (`v0.7.30` is normalized to `0.7.30`),
installs that `harn-cli` release into a temp directory, then runs check, lint,
formatting, all smoke tests, and `scripts/regen_demo.harn`. Use
`--no-verify` only when you intentionally want to edit the workflow pins
without running the gate.

## License

Dual-licensed under MIT and Apache-2.0. Choose whichever you prefer.

- [LICENSE-MIT](./LICENSE-MIT)
- [LICENSE-APACHE](./LICENSE-APACHE)
