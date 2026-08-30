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
        cli:
          command: [widgets, get]
          hidden: false
        annotations:
          readOnlyHint: true
          destructiveHint: false
          idempotentHint: true
          openWorldHint: true
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
| `cli.command` | string or list of strings | Portable command path. Segments use ASCII letters, digits, `_`, and `-`, and cannot start with `-`. |
| `cli.hidden` | boolean | Hide the command from help while retaining explicit invocation. |
| `annotations` | object | Overrides for the four standard MCP boolean hints. |
| `meta` | object | Protocol extension metadata projected as MCP `_meta`. |

Unknown fields and invalid values fail during code generation. Duplicate
exposed tool names or CLI command paths also fail before source is rendered.

Generated policy is separate from MCP hints. `GET`, `HEAD`, and `OPTIONS` map
to `{kind: "fetch", side_effect_level: "network"}`; other methods map to
`{kind: "execute", side_effect_level: "network"}`. Generated source metadata
uses `{kind: "openapi", id: operationId, binding: {method, path}}`.
