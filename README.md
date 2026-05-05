# harn-openapi

Pure-Harn library for parsing OpenAPI 3.1 documents and generating typed Harn
SDK source code from them. Acts as the reference example of a non-trivial
external Harn library and powers downstream typed SDKs such as
[notion-sdk-harn](https://github.com/burin-labs/notion-sdk-harn).

> **Status: v0.1.0 release candidate** - the parser, walker, codegen, package
> metadata, and CI surfaces are intended to be the first production-ready
> external Harn package contract.

## Intent

`harn-openapi` is the OpenAPI layer for Harn's external connector ecosystem.
Provider-specific SDKs and connectors should not each learn OpenAPI parsing,
schema walking, security handling, or typed SDK generation independently. This
repo keeps that shared logic in one pure-Harn package:

- parse OpenAPI 3.1 JSON into normalized Harn records;
- walk paths, webhooks, components, schemas, enums, security metadata,
  pagination patterns, and rate-limit response conventions;
- generate typed Harn SDK source for downstream provider repos;
- keep a pinned real-world Notion OpenAPI fixture for deterministic coverage.

The repo intentionally has no Cargo workspace, `package.json`, generated build
system, or non-Harn runtime dependency. CI and local development install the
pinned Harn CLI from crates.io using `.harn-version`.

## Repository Layout

| Path | Purpose |
|---|---|
| `harn.toml` | Package metadata and exported entry points. `src/lib.harn` is the default export and `src/types.harn` exports shared types. |
| `src/lib.harn` | Public parser, walker, schema-resolution, and SDK codegen implementation. |
| `src/types.harn` | Type aliases used by the public surface and tests. |
| `tests/*.harn` | Smoke and behavior tests for parsing, walking, codegen, security, response typing, polymorphic request bodies, fixture tooling, and helper scripts. |
| `tests/fixtures/notion.openapi.json` | Pinned Notion OpenAPI 3.1 snapshot used as the main real-world fixture. |
| `tests/fixtures/notion.openapi.json.meta.toml` | Capture metadata for the pinned fixture: upstream URL, timestamp, byte size, and SHA-256. |
| `tests/fixtures/connector_helpers.openapi.json` | Small synthetic OpenAPI fixture covering auth alternatives, pagination, and rate-limit metadata. |
| `scripts/regen_demo.harn` | End-to-end parse to codegen demo that writes generated SDK source to `/tmp`. |
| `scripts/refresh_fixtures.harn` | Refreshes the pinned Notion fixture and metadata intentionally. |
| `scripts/fixture_diff.harn` | Prints a structured operation/schema diff between two fixture captures. |
| `scripts/check_fixture_staleness.harn` | CI guard for fixture age. |
| `scripts/package_install_smoke.harn` | Clean temp-project install/import smoke for package-manager consumption. |
| `.harn-version` | Pinned crates.io `harn-cli` version used by CI and local gates. |
| `scripts/bump_harn_cli_version.harn` | Updates the pinned crates.io `harn-cli` version and runs the local gate. |
| `.github/workflows/ci.yml` | Main Harn check/lint/fmt/test/demo workflow. |
| `.github/workflows/fixture-staleness.yml` | Lightweight fixture freshness workflow. |
| `docs/migration-v0.1.0.md` | Migration note for connector repos moving from sibling path imports to package-managed imports. |
| `SESSION_PROMPT.md` | Historical project bootstrap and v0 milestone context. |
| `AGENTS.md` | Repo-specific instructions for coding agents. |

## Install

```sh
harn add github.com/burin-labs/harn-openapi@v0.1.0
```

For local multi-repo development, a path dependency is still useful:

```toml
[dependencies]
harn-openapi = { path = "../harn-openapi" }
```

The CI package smoke uses the same package-manager path against the current
checkout (`<repo>@HEAD`) so pull requests are verified before a release tag
exists. To test a published ref locally:

```sh
HARN_PACKAGE_REF=github.com/burin-labs/harn-openapi@v0.1.0 \
  harn run scripts/package_install_smoke.harn
```

## Usage

With either package install path, import the named functions you use:

```harn
import {
  parse,
  operations,
  webhook_operations,
  component_path_items,
  auth_helpers,
  pagination_plans,
  rate_limit_metadata,
  codegen_module,
  codegen_harn_toml,
} from "harn-openapi/default"

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

// Connector-facing helper metadata
let auth = auth_helpers(doc)
let pages = pagination_plans(doc)
let limits = rate_limit_metadata(doc)

// Generate Harn SDK source from the parsed document
let src = codegen_module(doc, {
  module_name: "notion",
  client_name: "Client",
})
write_file("./src/lib.harn", src)
write_file(
  "./harn.toml",
  codegen_harn_toml({
    package_name: "notion-sdk-harn",
    dependencies: {["harn-openapi"]: {path: "../harn-openapi"}},
  }),
)
```

When running examples or tests directly from this repository checkout, use the
source path instead:

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
- `auth_helpers(doc: OpenApiDoc) -> list<AuthHelper>` — classify each declared
  security scheme into reusable helper metadata, including generated client
  fields and OAuth scopes where present.
- `pagination_plans(doc: OpenApiDoc) -> list<PaginationPlan>` — detect simple
  cursor, page-number, and next-link list patterns from operation query
  parameters and success-response schemas.
- `rate_limit_metadata(doc: OpenApiDoc) -> list<RateLimitMetadata>` — surface
  per-operation 429, `Retry-After`, and `X-RateLimit-*` response header
  conventions for downstream retry/backoff code.
- `codegen_module(doc: OpenApiDoc, options: dict) -> string` — emit a typed Harn SDK
  module source string with per-scheme security dispatch, credential-provider
  hooks, pagination metadata, and rate-limit metadata (see below).
- `codegen_harn_toml(options: dict) -> string` — emit a package manifest for a
  generated SDK repo with `[package]`, `[exports]`, and `[dependencies]`.

### Compatibility policy

The v0.1.0 public API is the set of `harn.toml` exports plus the named
functions and types listed above. Patch releases in the `0.1.x` line should not
remove exports, rename fields in normalized parser output, or change generated
client function names for equivalent OpenAPI inputs. New helpers, extra
normalized fields, and stricter diagnostics are acceptable patch changes when
existing callers continue to check and run.

Breaking API changes before a stable 1.0 release require a new minor version,
a migration note under `docs/`, and fixture-backed smoke coverage showing the
new behavior. The supported Harn CLI floor is the version pinned in
`.harn-version`; CI installs that exact `harn-cli` release from crates.io.

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
| `http` + `bearer`, `oauth2`, `openIdConnect` | `token: string = ""`, `token_provider = nil` |
| `http` + `basic` | `basic_user: string = ""`, `basic_password: string = ""`, `basic_provider = nil` |
| `apiKey` (header / query / cookie) | `api_keys: dict = {}`, `api_key_provider = nil` (keyed by scheme name) |
| `mutualTLS` | (v0: no-op — op falls through to `_no_auth_headers`) |

So a Notion-shaped spec with `bearerAuth` + `basicAuth` yields:

```harn
new_client(
  base_url: string = "https://api.notion.com",
  token: string = "",
  token_provider = nil,
  basic_user: string = "",
  basic_password: string = "",
  basic_provider = nil,
  extra_headers: dict = {"Notion-Version": "..."},
) -> dict
```

For connector packages, prefer provider hooks over static token strings. The
generated module includes `token_from_secret(secret_id)` and
`api_key_from_secret(secret_ids)` helpers that call Harn's active
`secret_get(...)` connector primitive at request time. Callers can also pass
custom closures for token refresh, OAuth storage, or multi-tenant key lookup.

When an operation declares multiple security requirement alternatives
(`security: [{a: []}, {b: []}]`), v0 picks the first and leaves a
`NOTE` comment above the generated function listing the alternatives so
a human can retarget manually.

Out of scope for v0: full OAuth2 flows (authorization-code, device,
PKCE) and `mutualTLS` client-certificate plumbing.

### Pagination and rate-limit helpers

`pagination_plans(doc)` and generated SDKs expose the same lightweight metadata
for list operations. The detector intentionally recognizes only common
provider-neutral shapes: cursor params such as `start_cursor` with response
fields such as `next_cursor`, page params such as `page` / `per_page`, and
response next-link fields such as `next_url`.

Generated SDKs include `pagination_plans()`, `pagination_plan(operation_id)`,
`pagination_items(response, plan)`, and `pagination_next(response, plan)`.
`rate_limit_metadata(doc)` and generated SDKs surface declared `429`,
`Retry-After`, and `X-RateLimit-*` headers. Generated SDKs also include
`rate_limit_from_response(resp)` and `is_rate_limited_response(resp)` so
connectors can implement retries/backoff consistently without hardcoding every
endpoint class.

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
HARN_ROOT="$PWD" HARN_BIN="$(command -v harn)" harn run scripts/package_install_smoke.harn
```

When using the sibling upstream checkout instead:

```sh
cd ../harn
cargo run --quiet --bin harn -- check ../harn-openapi/src ../harn-openapi/scripts
cargo run --quiet --bin harn -- lint ../harn-openapi/src ../harn-openapi/scripts
cargo run --quiet --bin harn -- fmt --check ../harn-openapi/src ../harn-openapi/scripts ../harn-openapi/tests
for test in ../harn-openapi/tests/*.harn; do cargo run --quiet --bin harn -- run "$test" || exit 1; done
cargo run --quiet --bin harn -- run ../harn-openapi/scripts/regen_demo.harn
HARN_BIN="$PWD/target/debug/harn" cargo run --quiet --bin harn -- run ../harn-openapi/scripts/package_install_smoke.harn
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

GitHub Actions pins `harn-cli` from crates.io via `.harn-version`. When a new
Harn release is published, update that pin and run the local gate with:

```sh
harn run scripts/bump_harn_cli_version.harn -- 0.7.57
```

The script accepts a leading `v` (`v0.7.57` is normalized to `0.7.57`),
installs that `harn-cli` release into a temp directory, then runs check, lint,
formatting, all smoke tests, `scripts/regen_demo.harn`, and
`scripts/package_install_smoke.harn`. Use `--no-verify` only when you
intentionally want to edit the version pin without running the gate.

## License

Dual-licensed under MIT and Apache-2.0. Choose whichever you prefer.

- [LICENSE-MIT](./LICENSE-MIT)
- [LICENSE-APACHE](./LICENSE-APACHE)
