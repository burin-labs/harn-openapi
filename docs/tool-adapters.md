# Generated tool adapter reference

`codegen_module` emits one executable Harn `ToolRegistry`. Harn projects that
registry as MCP tools, a command-line help tree, or a versioned static catalog.
The generated SDK function remains the only execution path for an operation.

## Generated exports

Each generated module exports:

```text
pub fn adapter_tools(
  harness: {clock: HarnessClock, net: HarnessNet},
  client: AdapterClient,
) -> ToolRegistry

pub fn adapter_catalog(
  harness: {clock: HarnessClock, net: HarnessNet},
  client: AdapterClient,
) -> ToolCatalog

pub fn adapter_registry(
  harness: {clock: HarnessClock, net: HarnessNet},
  config: AdapterRuntimeConfig,
) -> ToolRegistry
```

With `transport: "raw"`, both functions accept `net: HarnessNet` instead of
the `{clock, net}` record.

`adapter_tools` returns the executable registry. `adapter_catalog` returns the
same registry through Harn's versioned static projection. The projection
omits handler closures and retains registry identity, input, output and error JSON
Schemas, CLI paths, MCP annotations, Harn policy, source bindings, and `_meta`.

Operations with `x-harn.expose: false` remain in the typed SDK and are omitted
from the tool registry.

## Executable entrypoint

`codegen_entrypoint` emits a private `pipeline main` that reads
`adapter_environment_config(harness.env)`, constructs `adapter_registry`, and
passes it to `harness.tools.mcp_tools`. Keeping configuration helpers in the SDK
module prevents Harn's automatic MCP projection from publishing them as tools.

Given `src/main.harn`, the supported projections are:

```sh
harn tool schema src/main.harn --pretty
harn tool run src/main.harn --help
harn tool run src/main.harn widgets get --widget-id w_123
harn serve mcp src/main.harn
```

The CLI and MCP server load and execute the same handler closure. Both validate
input against the registry's JSON Schema. The CLI also validates handler output
before printing it.

See [Generate an adapter package](generate-adapter-package.md),
[Run an adapter as a CLI](run-adapter-cli.md), and
[Serve an adapter over MCP](serve-adapter-mcp.md) for runnable procedures.

## Security plan and runtime configuration

`adapter_security_plan(doc, prefix)` returns one `AdapterSecurityPlan`. Its
scheme map retains original OpenAPI names and contains only portable metadata:
the normalized scheme kind, wire parameter name, host-managed flag, and stable
environment-variable names. It never contains credential values.

Each operation contains ordered `alternatives`. Each alternative is one OpenAPI
Security Requirement Object, so every scheme inside it is required. The list of
objects is an OR. `{}` is the anonymous alternative. Generated clients select
the first fully configured branch and never merge credentials across branches.

`AdapterRuntimeConfig` contains:

```text
base_url: string
credentials: dict<string, AdapterCredential>
extra_headers: dict
```

Bearer, OAuth 2.0, and OpenID Connect credentials use `token`; Basic uses
`username` plus `password`; API keys use `value`; mutual TLS uses
`host_configured: true`. A credential can instead carry a typed request-time
`token_provider`, `value_provider`, or `basic_provider` callback. The host owns OAuth authorization and refresh, secure
storage, tenant selection, token rotation, and client-certificate plumbing.

`adapter_registry` validates the base URL and every exposed operation before it
publishes a tool. Missing configuration reports the operation and acceptable
scheme combinations without printing secret values. See
[Configure an adapter environment](configure-adapter-environment.md) for exact
environment shapes.

## Portable schema graph

The package facade exports two typed normalization boundaries for catalog
schemas:

```harn
import {
  normalize_adapter_schema,
  prepare_adapter_schema_graph,
  parse,
} from "harn-openapi/default"

fn main(harness: Harness) {
  const doc = parse(harness.fs.read_text("./openapi.json"))
  const graph = prepare_adapter_schema_graph(
    doc.openapi,
    doc.components?.schemas ?? {},
    doc.jsonSchemaDialect,
  )
  const input_schema = normalize_adapter_schema(
    doc.openapi,
    {
      type: "object",
      properties: {widget: {"$ref": "#/components/schemas/Widget"}},
      required: ["widget"],
      additionalProperties: false,
    },
    graph,
    doc.jsonSchemaDialect,
  )
  harness.stdio.println(json_stringify({graph: graph, input_schema: input_schema}))
}
```

`AdapterJsonSchema` is `bool | dict<string, unknown>`, matching Draft 2020-12
instead of coercing boolean schemas into objects. `PreparedAdapterSchemaGraph`
contains normalized schemas, direct dependencies, transitive closures, and work
counters. Shared and recursive references stay as references, including escaped
component names and nested JSON Pointer targets.

Generated registries publish reusable schemas once in `components.schemas`.
Tools retain local `#/components/schemas/...` references in their complete
`inputSchema`, `outputSchema` and `errorSchema`. Input schemas preserve required
properties and reject additional properties. Boolean schemas remain booleans;
generated SDK types lower `true` to `any` and `false` to `never`.

The normalizer traverses only JSON Schema keyword positions. A `$ref`-shaped
object inside `const` or `enum` is instance data and remains unchanged. It
rejects the following before source generation:

- dangling component or nested JSON Pointer references;
- external resources and non-schema OpenAPI component targets;
- OpenAPI 3.0 `nullable` and boolean exclusive-bound spellings;
- custom schema dialects outside Draft 2020-12 and the OpenAPI 3.1 base
  dialect; per-schema OpenAPI base declarations canonicalize to Draft 2020-12;
- `$id`, anchors, and dynamic references that would change resource scope when
  the graph is bundled into an MCP tool schema.

This boundary validates schema structure and reference portability. Harn's
prepared tool catalog remains the owner of validating runtime input, output,
and application-error values. MCP discovery projects the same registry, bundling
references where its protocol requires self-contained schemas.

### HTTP application errors

An exact non-success status with a declared `application/json` schema contributes
one `errorSchema.oneOf` branch. The branch requires the original OpenAPI
operation ID, exact status, response headers and decoded body:

```json
{
  "operation": "getWidget",
  "status": 404,
  "headers": {"x-request-id": "request_123"},
  "body": {"message": "Widget not found"}
}
```

The generated handler decodes exact declared JSON failures into Harn's explicit
error outcome. Harn's prepared catalog validates the value once before any
adapter exposes application data. MCP places typed error data in
`_meta["com.harnlang/toolContract"].applicationError.data`; CLI JSON output uses
`error.data`. Neither projection treats the error as successful output.

Transport faults, undeclared statuses, malformed JSON and schema-invalid bodies
remain runtime errors. Range responses, `default`, non-JSON media and responses
without schemas don't create application-error branches. The connector-policy
transport retains its shared header redaction and bounded error-body handling;
raw transport retains its direct response behavior.

Schema dialects and references follow the
[OpenAPI 3.1 Schema Object](https://spec.openapis.org/oas/v3.1.0.html#schema-object)
and [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12/json-schema-core).
The [MCP tools contract](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
defines discovery and invocation; Harn's tool-contract metadata carries the
application-error schema and data.

## `x-harn`

OpenAPI extension fields are optional. OpenAPI operation data supplies the
default tool name, title, description, JSON Schemas, method-derived MCP hints,
policy, and source binding.

```yaml
x-harn:
  annotationDefaults:
    openWorldHint: false
  cli:
    commands:
      - command: [widgets]
        title: Widget commands
        aliases: [w]
paths:
  /widgets/{widget-id}:
    get:
      operationId: get-widget
      tags: [widgets]
      x-harn:
        name: lookup_widget
        title: Look up widget
        namespace: widgets
        expose: true
        defer_loading: true
        governance:
          audiences: [agent, catalog, mcp, cli]
        cli:
          command: [widgets, get]
          aliases: [show]
          hidden: false
          arguments:
            widget-id:
              position: 0
              value_name: ID
        annotations:
          readOnlyHint: true
          destructiveHint: false
          idempotentHint: true
        icons:
          - src: https://api.example.com/assets/widget.svg
            mimeType: image/svg+xml
            sizes: [any]
            theme: light
        execution:
          taskSupport: optional
        meta:
          com.example/audience: developer
```

| Field | Type | Meaning |
|---|---|---|
| `name` | non-empty string | Stable tool and MCP name. |
| `title` | non-empty string | Human-readable display title. |
| `namespace` | non-empty string | Default CLI command prefix when `cli.command` is absent. |
| `expose` | boolean | Include the operation in adapter projections. Defaults to `true`. |
| `defer_loading` | boolean | Mark the tool for deferred discovery. Defaults to `false`. |
| `governance.audiences` | non-empty list of `cli`, `mcp`, `catalog`, `dashboard`, or `agent` | Adapters allowed to discover and invoke the tool. Defaults to all five. |
| `cli.command` | string or non-empty list of strings | Portable command path. Segments use ASCII letters, digits, `_`, and `-`, and cannot start with `-`. |
| `cli.aliases` | list of portable strings | Alternative names for the leaf command. |
| `cli.hidden` | boolean | Hide the command from help while retaining explicit invocation. |
| `cli.arguments` | map of OpenAPI wire names to argument records | Override CLI presentation and token mapping for an input property. Use `body` for the request body. |
| `annotations` | object | Advisory MCP hints. Values that contradict standard HTTP method facts are rejected. |
| `icons` | list of icon objects | Portable tool icons. Each icon requires `src` and accepts `mimeType`, `sizes`, and `theme` (`light` or `dark`). |
| `execution.taskSupport` | `forbidden`, `optional`, or `required` | Whether MCP clients may or must invoke the tool as a task. |
| `meta` | object | Protocol extension metadata projected as MCP `_meta`. |

Unknown fields and invalid values fail during code generation. Duplicate
exposed tool names and exact or parent/leaf CLI command collisions also fail
before source is rendered.

### CLI metadata

Without overrides, the first operation tag supplies the parent command and the
generated tool name supplies its leaf. An exact sanitized tag token at the
start or end of the leaf is removed: `widgets_list` becomes `widgets list`,
while `list_widget` stays `widgets list_widget`. There is no singularization.
An explicit `namespace` supplies the prefix instead; `cli.command` replaces the
whole path. Declared OpenAPI tags contribute titles, descriptions, and source
order only when they own a generated CLI parent.

Root `x-harn.cli.commands` contains non-runnable parent records. Each requires a
`command` path and accepts `title`, `description`, `aliases`, `hidden`, and
non-negative `display_order`. An explicit record overlays the matching derived
parent; omitted fields retain their OpenAPI defaults.

Argument keys use the original parameter spelling, such as `widget-id`, rather
than the generated `widget_id` property. Parameters that collide after
normalization are rejected. A parameter named `body` receives a separate safe
property name when the operation also accepts a request body. An explicit
`cli.arguments.body` override is rejected in that case because its target is
ambiguous. Headers supplied through `header_overrides` are not exposed as
arguments. Presentation overrides leave input validation and governance unchanged.

| Argument field | Type | Meaning |
|---|---|---|
| `long`, `short`, `aliases` | string, one ASCII letter or digit, list of strings | Option tokens without leading dashes. |
| `position` | non-negative integer | Positional argument index. |
| `value_name`, `help`, `help_group` | non-empty string | Value label, help text, and help section. |
| `value_hint` | `file`, `directory`, `path`, `url`, `email`, `username`, `hostname`, `command`, `other` | Portable completion hint. |
| `boolean_style` | `value`, `set_true`, `set_false` | Whether a boolean takes a value or changes when present. |
| `repeatable`, `hidden` | boolean | Repeated-value mapping and help visibility. |
| `completions` | list of non-empty strings | Explicit completion candidates. |
| `display_order` | non-negative integer | Ordering within help. |

Parameter descriptions supply argument help. Closed string enums supply
completion candidates; URI, email, and hostname formats supply value hints.
Explicit fields replace these defaults, including an empty completion list.
Short names, positions, and boolean presence semantics require explicit
overrides. Harn owns command-tree and argument compatibility validation; the
generator does not maintain a second parser or usage schema.

The optional top-level `x-harn.annotationDefaults.openWorldHint` is a boolean
default for every generated tool. An operation-level `openWorldHint` overrides
it. When neither value is present, Harn leaves `openWorldHint` unspecified
instead of claiming that the operation can or cannot reach an open world.

HTTP method facts have one typed owner shared by generated annotations and
connector retry planning:

| Methods | `readOnlyHint` | `idempotentHint` | `destructiveHint` | Retry default |
|---|---:|---:|---:|---:|
| `GET`, `HEAD`, `OPTIONS`, `TRACE` | `true` | `true` | `false` | 3 attempts |
| `PUT` | `false` | `true` | unspecified | 3 attempts |
| `DELETE` | `false` | `true` | `true` | 3 attempts |
| `POST`, `PATCH` | `false` | `false` | unspecified | 1 attempt |

An `Idempotency-Key` parameter raises the generated retry limit for `POST` or
`PATCH` to three attempts. It does not change `idempotentHint`: the key makes a
particular invocation safe to repeat, not every invocation of the operation.
`destructiveHint` remains unspecified for methods where HTTP alone cannot
answer the question. Operation annotations may fill that gap, but cannot
mark a safe method as mutating or destructive, or an idempotent method as
non-idempotent. An operation may refine an otherwise unknown fact, such as a
read-only POST or an additive DELETE.

Teams that do not own the source OpenAPI document can add the same metadata
with an OpenAPI Overlay 1.1 document, apply it with their overlay tool, and pass
the resulting OpenAPI document to Harn:

```yaml
overlay: 1.1.0
info:
  title: Harn adapter semantics
  version: 1.0.0
extends: ./openapi.yaml
actions:
  - target: $
    update:
      x-harn:
        annotationDefaults:
          openWorldHint: false
  - target: $.paths['/search'].post
    update:
      x-harn:
        annotations:
          readOnlyHint: true
          idempotentHint: true
          openWorldHint: true
```

Governance is a closed exposure policy, not a transport configuration. Input
order is normalized to `cli`, `mcp`, `catalog`, `dashboard`, `agent`, and the
generated `tool_define` always contains the complete normalized record. Harn
uses that one record to filter CLI, MCP, catalog, dashboard, and agent
projections. The generator does not infer audiences from tags, security,
deprecation, HTTP methods, or MCP annotations because those fields describe
different concerns.

`expose: false` is stronger and separate: it omits the operation from the
registry and every projection. Selective governance retains the executable
tool and its catalog identity while excluding only the unnamed adapters. CLI
command conflicts are therefore checked only between tools that include the
`cli` audience; an MCP-only tool may share a dormant CLI path with a CLI tool.

The static catalog retains all three `execution.taskSupport` values. MCP omits
`execution` for `forbidden`, which is the protocol default, and emits the field
for `optional` and `required`. Icons pass through unchanged; clients decide
which declared size and theme they can display.

Generated policy is separate from MCP hints. Safe HTTP methods map to
`{kind: "fetch", side_effect_level: "network"}`; other methods map to
`{kind: "execute", side_effect_level: "network"}`. Generated source metadata
uses `{kind: "openapi", id: operationId, binding: {method, path}}`.
Changing advisory annotations never grants an audience, changes execution
policy, or weakens Harn's capability checks.
