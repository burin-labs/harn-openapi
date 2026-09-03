# harn-openapi

Pure-Harn library for parsing OpenAPI 3.1 documents and generating typed Harn
SDK source code from them. Acts as the reference example of a non-trivial
external Harn library and powers downstream typed SDKs such as
[notion-sdk-harn](https://github.com/burin-labs/notion-sdk-harn).

> Status: `v0.2.0-rc.1` is the current prerelease and supports Harn 0.10. Use
> its tagged package ref for released consumption; use a path dependency or
> explicit `@HEAD` for unreleased work.

## Intent

`harn-openapi` is the OpenAPI layer for Harn's external connector ecosystem.
Provider-specific SDKs and connectors should not each learn OpenAPI parsing,
schema walking, security handling, or typed SDK generation independently. This
repo keeps that shared logic in one pure-Harn package:

- parse OpenAPI 3.1 JSON into normalized Harn records;
- walk paths, webhooks, components, schemas, enums, security metadata,
  pagination patterns, and rate-limit response conventions;
- generate typed Harn SDK source for downstream provider repos;
- generate one typed tool registry that Harn projects as an MCP server, a
  command tree, or a versioned static catalog;
- keep a pinned real-world Notion OpenAPI fixture for deterministic coverage.

The generator is intentionally scoped to focused API packages backed by an
OpenAPI document. Broad cloud SDK families, provider discovery formats, Smithy,
and provider-specific auth flows belong in dedicated packages above this layer,
not in `harn-openapi`.

The repo intentionally has no Cargo workspace, `package.json`, generated build
system, or non-Harn runtime dependency. CI and local development use the Harn
CLI pinned by `.harn-version`.

## Repository layout

| Path | Purpose |
|---|---|
| `harn.toml` | Package metadata and exported entry points. `src/lib.harn` is the default export and carries the typed public surface. |
| `src/lib.harn` | Public parser, walker, schema-resolution, and SDK codegen implementation. |
| `src/adapter_governance.harn` | Canonical `x-harn.governance` validation against Harn's closed adapter-audience types. |
| `src/adapter_schema_graph.harn` | Portable Draft 2020-12 component graph and reference validation shared by future catalog projections. |
| `src/adapter_security.harn` | Typed OpenAPI security plan shared by generated clients, environment configuration, CLI, MCP, and static catalogs. |
| `tests/*.harn` | Smoke and behavior tests for parsing, walking, codegen, security, response typing, polymorphic request bodies, fixture tooling, and helper scripts. |
| `tests/fixtures/notion.openapi.json` | Pinned Notion OpenAPI 3.1 snapshot used as the main real-world fixture. |
| `tests/fixtures/notion.openapi.json.meta.toml` | Capture metadata for the pinned fixture: upstream URL, timestamp, byte size, and SHA-256. |
| `tests/fixtures/connector_helpers.openapi.json` | Small synthetic OpenAPI fixture covering auth alternatives, pagination, and rate-limit metadata. |
| `tests/fixtures/adapter_catalog.openapi.json` | Synthetic adapter fixture covering `x-harn`, registry, CLI, static catalog, and MCP parity. |
| `scripts/regen_demo.harn` | End-to-end parse to codegen demo that writes generated SDK source to `/tmp`. |
| `scripts/refresh_fixtures.harn` | Refreshes the pinned Notion fixture and metadata intentionally. |
| `scripts/fixture_diff.harn` | Prints a structured operation/schema diff between two fixture captures. |
| `scripts/check_fixture_staleness.harn` | CI guard for fixture age. |
| `scripts/package_install_smoke.harn` | Clean temp-project install/import smoke for package-manager consumption. |
| `.harn-version` | Pinned Harn CLI version used by CI and local gates. |
| `scripts/bump_harn_cli_version.harn` | Local/manual path: updates the pinned Harn CLI version and runs the full gate against that release. Routine bumps are automated by `.github/workflows/bump-harn.yml`. |
| `.github/workflows/ci.yml` | Harn check/lint/fmt/package/test/demo/fixture workflow with an aggregate `CI status` job for branch rules and merge queue. |
| `docs/migration-v0.1.0.md` | Migration note for connector repos moving from sibling path imports to package-managed imports. |
| `docs/migration-codegen-fs.md` | How to update `codegen_module` callers to pass `HarnessFs`. |
| `docs/tool-adapters.md` | Reference for generated tool registries and the `x-harn` extension. |
| `docs/generate-adapter-package.md` | Generate a typed SDK and its executable registry entrypoint. |
| `docs/configure-adapter-environment.md` | Configure base URLs and credentials without writing secrets into generated source. |
| `docs/run-adapter-cli.md` | Inspect and invoke the generated registry as a command tree. |
| `docs/serve-adapter-mcp.md` | Serve the same registry over MCP stdio. |
| `docs/package-adapter.md` | Assemble and verify a distributable Harn package. |
| `docs/distribute-adapter.md` | Publish and consume an adapter through a pinned package reference. |
| `docs/migration-scheme-credentials.md` | Breaking migration from shared credential fields to scheme-keyed credentials. |
| `AGENTS.md` | Repo-specific instructions for coding agents. |

## Install

For unreleased local or stacked work, use a path dependency:

```toml
[dependencies]
harn-openapi = { path = "../harn-openapi" }
```

The published `v0.2.0-rc.1` prerelease can be installed by tag:

```sh
harn add github.com/burin-labs/harn-openapi@v0.2.0-rc.1
```

The CI package smoke uses the same package-manager path against the current
checkout (`<repo>@HEAD`) so pull requests are checked before a release tag
exists. To test a published ref locally after tagging:

```sh
HARN_PACKAGE_REF=github.com/burin-labs/harn-openapi@v0.2.0-rc.1 \
  harn run scripts/package_install_smoke.harn
```

## Quick start

This example reads an OpenAPI document, inspects it, and writes a generated SDK.
File access stays explicit through the filesystem capability.

```harn
import { codegen_module, operations, parse } from "harn-openapi/default"

fn main(harness: Harness) {
  const raw = harness.fs.read_text("./notion.openapi.json")
  const doc = parse(raw)

  for op in operations(doc) {
    harness.stdio.println("${op.method} ${op.path} -> ${op.operation_id}")
  }

  const source = codegen_module(harness.fs, doc, {
    module_name: "notion",
    client_name: "Client",
    transport: "connector_policy",
  })
  harness.fs.write_text("./src/lib.harn", source)
}
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
- `prepare_adapter_schema_graph(openapi_version, schemas, json_schema_dialect?) -> PreparedAdapterSchemaGraph` —
  validate reusable OpenAPI 3.1 component schemas once, then retain their
  dependency closures and work counters for every generated projection.
- `normalize_adapter_schema(openapi_version, schema, graph, json_schema_dialect?) -> AdapterJsonSchema` —
  normalize one inline tool schema and validate its references against the same
  component graph.
- `is_openapi_doc(value)`, `is_reference(value)`, `is_schema(value)` — small schema guards
  for common dynamic boundaries.
- `auth_helpers(doc: OpenApiDoc) -> list<AuthHelper>` — classify each declared
  security scheme into reusable helper metadata, including generated client
  credential fields and OAuth scopes where present.
- `adapter_security_plan(doc: OpenApiDoc, environment_prefix: string) -> AdapterSecurityPlan` —
  normalize every effective operation requirement into ordered OR alternatives
  whose members are AND requirements, plus stable environment-variable names.
- `pagination_plans(doc: OpenApiDoc) -> list<PaginationPlan>` — detect simple
  cursor, page-number, and next-link list patterns from operation query
  parameters and success-response schemas.
- `rate_limit_metadata(doc: OpenApiDoc) -> list<RateLimitMetadata>` — surface
  per-operation 429, `Retry-After`, and `X-RateLimit-*` response header
  conventions for downstream retry/backoff code.
- `codegen_module(fs: HarnessFs, doc: OpenApiDoc, options: dict) -> string` — emit a typed Harn SDK
  module source string with per-scheme security dispatch, credential-provider
  hooks, optional connector-policy transport, pagination metadata, rate-limit
  metadata, and `adapter_tools` / `adapter_catalog` projections (see below).
- `codegen_entrypoint(fs: HarnessFs, doc: OpenApiDoc, options: AdapterEntrypointOptions) -> string` —
  emit the executable that reads the generated environment contract and
  registers the SDK's one tool registry for CLI and MCP hosts.
- `codegen_harn_toml(options: dict) -> string` — emit a package manifest for a
  generated SDK repo with `[package]`, `[exports]`, and `[dependencies]`,
  including an optional named entrypoint export.

### Pre-1.0 change policy

The package may make breaking changes before 1.0. Each change must update this
reference, include a migration note when callers need to change, and have a
fixture-backed test. CI uses the exact Harn CLI version in `.harn-version`.

### Security handling in generated clients

`codegen_module` inspects `components.securitySchemes` and emits a
dedicated `_headers_<scheme>(client)` helper per scheme that is actually
referenced by at least one operation. Each operation dispatches through
the helper matching its *effective* security (`op.security ?? doc.security
?? []`) — explicit `security: []` at either level routes through
`_no_auth_headers(client)` so the call goes out without an `Authorization`
header. A single OpenAPI security requirement object is treated as an AND:
`security: [{bearerAuth: [], apiKeyAuth: []}]` sends both schemes, while
separate objects remain alternatives.

Generated clients keep credentials in one map keyed by the original OpenAPI
security-scheme name. This prevents two schemes of the same kind from sharing
credential state accidentally:

```harn
new_client(
  base_url: string = "https://api.notion.com",
  credentials: dict<string, AdapterCredential> = {
    bearerAuth: {token: "..."},
    basicAuth: {username: "...", password: "..."},
  },
  extra_headers: dict = {"Notion-Version": "..."},
) -> AdapterClient
```

Each credential accepts a typed request-time `token_provider`,
`value_provider`, or `basic_provider` closure. Generated modules
also include `token_from_secret(secrets, secret_id)` and
`api_key_from_secret(secrets, secret_id)` helpers. The host remains responsible
for OAuth login, token refresh and rotation, tenant selection, secure storage,
and client-certificate configuration. Mutual TLS requires
`{host_configured: true}` and never degrades to an unauthenticated request.

When an operation declares multiple security requirement alternatives
(`security: [{a: [], b: []}, {c: []}]`), the generated client chooses the first
fully configured alternative. It sends both `a` and `b`, or falls back to `c`.
An empty requirement object is the explicit anonymous alternative. Missing
required configuration rejects registry publication and direct operation calls
without echoing credential values.

Every generated operation function takes only its transport's capabilities
first: connector-policy operations accept
`harness: {clock: HarnessClock, net: HarnessNet}`, while raw-transport
operations accept `net: HarnessNet`. After it come the OpenAPI `path`, `query`,
`header`, and `cookie` parameters. Path values are URL-encoded during
interpolation, query values are encoded in the query string, header parameters
are merged into the request headers, and cookie parameters are appended to the
`Cookie` header.

The generated environment projection creates stable names such as
`WIDGETS_BASE_URL`, `WIDGETS_BEARERAUTH_TOKEN`, and
`WIDGETS_HEADERKEY_API_KEY`. See
[Configure an adapter environment](docs/configure-adapter-environment.md).

### Transport policy

Generated SDKs default to the connector policy transport. It avoids deprecated
ambient HTTP builtins in generated code and routes requests through the shared
retry, idempotency, JSON parse, and rate-limit policy layer:

```harn
let src = codegen_module(harness.fs, doc, {
  module_name: "example_sdk",
  client_name: "ExampleClient",
  transport: "connector_policy",
})
```

Connector-policy output imports `connector_http_request` and
`connector_http_json` from `std/connectors/shared`. JSON response operations
call `connector_http_json`; opaque or empty-response operations call
`connector_http_request`. On helper errors, generated functions throw the
helper envelope directly, so callers can branch on `category`, `status`,
`retryable`, `retry_after_ms`, `error`, and `rate_limit` without parsing a
string.

Safe or idempotent methods (`GET`, `HEAD`, `PUT`, `DELETE`, `OPTIONS`, `TRACE`) emit a
bounded retry policy. `POST` and `PATCH` emit that retry policy only when the
OpenAPI operation declares an explicit `Idempotency-Key` header parameter; the
generated function also threads that parameter into `options.idempotency_key`
for the shared helper. Unsafe writes without an idempotency key emit
`max_attempts: 1`, leaving retries disabled by default.

Generated packages that still need the historical direct-HTTP shape can opt in
explicitly:

```harn
let src = codegen_module(harness.fs, doc, {
  module_name: "example_sdk",
  client_name: "ExampleClient",
  transport: "raw",
})
```

Raw transport emits direct `http_get`, `http_post`, and sibling calls with
structured throws for non-2xx responses. Prefer connector policy for new SDKs.

### Tool adapters

Every generated module exports `adapter_tools(authority, client) ->
ToolRegistry`. That registry owns operation names, JSON Schemas, handlers,
policy, source bindings, and presentation metadata. Use Harn's adapters instead
of generating parallel dispatch code:

```sh
harn tool schema ./src/main.harn --pretty
harn tool run ./src/main.harn --help
harn serve mcp ./src/main.harn
```

Generated modules also export `adapter_catalog(authority, client) ->
ToolCatalog`, a typed convenience wrapper over Harn's versioned tool-contract
projection. See
[Generated tool adapters](docs/tool-adapters.md) for the exact `x-harn`
contract and portable schema graph. Start with
[Generate an adapter package](docs/generate-adapter-package.md) for the runnable
path.

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
let page = update_page_markdown(
  {clock: harness.clock, net: harness.net},
  client,
  page_id,
  body,
)
```

The constructor adds an internal `_variant` tag so the umbrella can validate
which variant was selected, then strips `_variant` before serializing the HTTP
body. When an OpenAPI discriminator mapping is present, the mapping key is used
as the `_variant` tag.

Downstream SDK wrappers can expose the same two styles as methods, e.g.
`client.update_page_markdown(body)` for dynamic dispatch and
`client.update_page_markdown_insert_content({...})` for a static variant call.

## Development

Read [AGENTS.md](./AGENTS.md) before making changes. It has the current agent
rules, local gate, and fixture guidance.

The upstream Harn language and runtime live at
[burin-labs/harn](https://github.com/burin-labs/harn). For local development,
clone it next to this repo at `../harn`.

### Local checks

The GitHub workflows install the Harn version pinned by `.harn-version`, using
the published release archive when available and falling back to crates.io.
Local development can use either a released `harn` binary or the upstream
checkout. With a released binary:

```sh
harn check src scripts
harn lint src scripts
harn fmt --check src scripts tests
harn package check
HARN_BIN="$(command -v harn)" harn test tests --parallel --timing
harn run scripts/regen_demo.harn
HARN_BIN="$(command -v harn)" harn run scripts/package_install_smoke.harn
harn run scripts/check_fixture_staleness.harn
```

When using the sibling upstream checkout instead:

```sh
OPENAPI_ROOT="$(pwd)"
cd ../harn
cargo run --quiet --bin harn -- check "$OPENAPI_ROOT/src" "$OPENAPI_ROOT/scripts"
cargo run --quiet --bin harn -- lint "$OPENAPI_ROOT/src" "$OPENAPI_ROOT/scripts"
cargo run --quiet --bin harn -- fmt --check "$OPENAPI_ROOT/src" "$OPENAPI_ROOT/scripts" "$OPENAPI_ROOT/tests"
cargo run --quiet --bin harn -- package check "$OPENAPI_ROOT"
HARN_BIN="$PWD/target/debug/harn" cargo run --quiet --bin harn -- test "$OPENAPI_ROOT/tests" --parallel --timing
HARN_BIN="$PWD/target/debug/harn" cargo run --quiet --bin harn -- run "$OPENAPI_ROOT/scripts/regen_demo.harn"
HARN_BIN="$PWD/target/debug/harn" cargo run --quiet --bin harn -- run "$OPENAPI_ROOT/scripts/package_install_smoke.harn"
cargo run --quiet --bin harn -- run "$OPENAPI_ROOT/scripts/check_fixture_staleness.harn"
```

### CI and merge queue

The CI workflow runs on pull requests, `main` pushes, merge queue
`merge_group` events, and manual dispatch. It installs the Harn version pinned
by `.harn-version`: first from the published Linux release archive, then from
crates.io with `cargo install --locked` if the archive is unavailable.

Branch rules require the aggregate `CI status` job. Keep every required check
as a dependency of that job so repository rulesets and merge queue
configuration do not drift when individual job names change.

`main` is protected by GitHub's merge queue. Changes should be pushed on a
branch, opened as a PR, and queued after checks pass. The merge queue runs the
same workflows again on GitHub's synthetic queue branch before landing the PR
on `main`.

### Fixture refresh workflow

The Notion OpenAPI fixture is intentionally pinned. To refresh it manually,
save the current fixture, run the refresh script, then review the diff report:

```sh
cp tests/fixtures/notion.openapi.json /tmp/notion.openapi.old.json
harn run scripts/refresh_fixtures.harn
harn run scripts/fixture_diff.harn -- \
  /tmp/notion.openapi.old.json \
  tests/fixtures/notion.openapi.json
```

`scripts/refresh_fixtures.harn` writes both
`tests/fixtures/notion.openapi.json` and
`tests/fixtures/notion.openapi.json.meta.toml`, including the upstream URL,
capture timestamp, byte size, and SHA-256. CI runs
`scripts/check_fixture_staleness.harn`; it verifies the committed byte size and
SHA-256 before checking age, is quiet under 90 days old, warns
between 90 and 180 days, and fails non-`main` branches once the fixture is over
180 days old.

### Harn CLI version bumps

GitHub Actions reads the Harn version from `.harn-version`, stored as bare
semver (`0.10.39`, no leading `v`).

Routine bumps are automated. `.github/workflows/bump-harn.yml` is a thin caller
of Harn's reusable `workflow_call` workflow; it runs daily, rewrites the pin,
refreshes the lockfile, runs this repo's validation command, and opens a signed
auto-merging PR. Nothing needs to be done by hand.

To bump by hand — trying a candidate release locally, or reproducing an
automated failure without pushing — use:

```sh
harn run scripts/bump_harn_cli_version.harn -- 0.9.22
```

The script accepts a leading `v` (`v0.9.22` is normalized to `0.9.22`),
installs that `harn-cli` release into a temp directory, then runs check, lint,
formatting, the smoke test suite, `scripts/regen_demo.harn`, and
`scripts/package_install_smoke.harn`. Unlike the workflow it pins a specific
version you name and verifies against a from-crates.io install, so it stays the
local-development path. Use `--no-verify` only when you intentionally want to
edit the version pin without running the gate.

## Contributing

Read [CONTRIBUTING.md](./CONTRIBUTING.md) before you open a pull request. It
covers what belongs in this package, the pinned-CLI gate, why the Notion fixture
stays pinned, and the `[Area] Sentence case description` title convention.

## License

Dual-licensed under MIT and Apache-2.0. Choose whichever you prefer.

- [LICENSE-MIT](./LICENSE-MIT)
- [LICENSE-APACHE](./LICENSE-APACHE)
