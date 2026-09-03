# Generated tool adapter reference

`codegen_module` emits one executable Harn `ToolRegistry`. Harn projects that
registry as MCP tools, a command-line help tree, or a versioned static catalog.
The generated SDK function remains the only execution path for an operation.

## Generated exports

Each generated module exports:

```text
pub fn adapter_tools(
  harness: {clock: HarnessClock, net: HarnessNet},
  client: dict,
) -> ToolRegistry

pub fn adapter_catalog(
  harness: {clock: HarnessClock, net: HarnessNet},
  client: dict,
) -> ToolCatalog
```

With `transport: "raw"`, both functions accept `net: HarnessNet` instead of
the `{clock, net}` record.

`adapter_tools` returns the executable registry. `adapter_catalog` returns the
same registry through Harn's `harn-tools/1.0` static projection. The projection
omits handler closures and retains registry identity, input and output JSON
Schemas, CLI paths, MCP annotations, Harn policy, source bindings, and `_meta`.

Operations with `x-harn.expose: false` remain in the typed SDK and are omitted
from the tool registry.

## Server script

```harn
import { adapter_tools, new_client } from "example-sdk/default"

fn main(harness: Harness) {
  const client = new_client("https://api.example.com")
  harness.tools.mcp_tools(
    adapter_tools({clock: harness.clock, net: harness.net}, client),
  )
}
```

Given `server.harn`, the supported projections are:

```sh
harn tool schema server.harn --pretty
harn tool run server.harn --help
harn tool run server.harn widgets get --widget-id w_123
harn serve mcp server.harn
```

The CLI and MCP server load and execute the same handler closure. Both validate
input against the registry's JSON Schema. The CLI also validates handler output
before printing it.

## Portable schema graph

The package facade exports two typed normalization boundaries for catalog
schemas:

```harn
import {
  normalize_adapter_schema,
  normalize_adapter_schema_graph,
  parse,
} from "harn-openapi/default"

fn main(harness: Harness) {
  const doc = parse(harness.fs.read_text("./openapi.json"))
  const graph = normalize_adapter_schema_graph(
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
instead of coercing boolean schemas into objects. `AdapterSchemaGraph` contains
one `schemas` map. Shared and recursive references stay as references, including
escaped component names and nested JSON Pointer targets.

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
and application-error values. The current `harn-tools/1.0` generated registry
still emits resolved per-operation schemas; the direct graph projection lands
with the `harn-tools/2.0` cutover.

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
