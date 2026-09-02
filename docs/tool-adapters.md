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
omits handler closures and retains registry identity, input and output JSON
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

The OpenAPI graph retains boolean schemas exactly. Harn and MCP tool contracts
require schema objects, so their projection uses the Draft 2020-12 equivalents:
`true` becomes `{}`, and `false` becomes `{"not": {}}`. Generated SDK return
types independently lower `true` to `any` and `false` to `never`, preserving the
same validation semantics on every surface.

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
and application-error values. Generated registries currently emit resolved
per-operation schemas. The direct graph projection lands with the next
versioned Harn tool-contract cutover.

## `x-harn`

OpenAPI extension fields are optional. OpenAPI operation data supplies the
default tool name, title, description, JSON Schemas, method-derived MCP hints,
policy, and source binding.

```yaml
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
          hidden: false
        annotations:
          readOnlyHint: true
          destructiveHint: false
          idempotentHint: true
          openWorldHint: true
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
| `cli.hidden` | boolean | Hide the command from help while retaining explicit invocation. |
| `annotations` | object | Overrides for the four standard MCP boolean hints. |
| `icons` | list of icon objects | Portable tool icons. Each icon requires `src` and accepts `mimeType`, `sizes`, and `theme` (`light` or `dark`). |
| `execution.taskSupport` | `forbidden`, `optional`, or `required` | Whether MCP clients may or must invoke the tool as a task. |
| `meta` | object | Protocol extension metadata projected as MCP `_meta`. |

Unknown fields and invalid values fail during code generation. Duplicate
exposed tool names and exact or parent/leaf CLI command collisions also fail
before source is rendered.

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

Generated policy is separate from MCP hints. `GET`, `HEAD`, and `OPTIONS` map
to `{kind: "fetch", side_effect_level: "network"}`; other methods map to
`{kind: "execute", side_effect_level: "network"}`. Generated source metadata
uses `{kind: "openapi", id: operationId, binding: {method, path}}`.
