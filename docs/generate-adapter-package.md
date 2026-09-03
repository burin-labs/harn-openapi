# Generate an adapter package

Generate a typed SDK and the executable registry that Harn can project as a
CLI, MCP server, or static catalog.

Create `generate.harn` beside an OpenAPI 3.1 JSON document:

```harn
import {
  codegen_entrypoint,
  codegen_harn_toml,
  codegen_module,
  parse,
} from "harn-openapi/default"

pipeline main(harness: Harness) {
  const doc = parse(harness.fs.read_text("./openapi.json"))
  harness.fs.mkdir("./src")
  harness.fs.write_text(
    "./src/lib.harn",
    codegen_module(harness.fs, doc, {
      module_name: "widgets",
      client_name: "WidgetClient",
      environment_prefix: "WIDGETS",
    }),
  )
  harness.fs.write_text(
    "./src/main.harn",
    codegen_entrypoint(harness.fs, doc, {
      module_import: "./lib",
      environment_prefix: "WIDGETS",
    }),
  )
  harness.fs.write_text(
    "./harn.toml",
    codegen_harn_toml({
      package_name: "widgets-adapter",
      default_export: "src/lib.harn",
      entrypoint_export: "src/main.harn",
    }),
  )
}
```

Run the generator and verify both generated files:

```sh
harn run generate.harn
harn check src/lib.harn src/main.harn
harn fmt --check src/lib.harn src/main.harn
```

Regenerate the files whenever the OpenAPI document or generator version
changes. Do not add a second CLI or MCP dispatcher. `src/main.harn` registers
the same typed registry that the SDK exports.

Next, [configure the adapter environment](configure-adapter-environment.md).
