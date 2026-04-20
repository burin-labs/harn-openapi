# harn-openapi

Pure-Harn library for parsing OpenAPI 3.1 documents and generating typed Harn
SDK source code from them. Acts as the reference example of a non-trivial
external Harn library and powers downstream typed SDKs such as
[notion-sdk-harn](https://github.com/burin-labs/notion-sdk-harn).

> **Status: pre-alpha** — actively developed in tandem with
> [burin-labs/harn](https://github.com/burin-labs/harn). See the
> [Pure-Harn Connectors Pivot epic #350](https://github.com/burin-labs/harn/issues/350).

## Install

Once Harn package management v0
([harn#345](https://github.com/burin-labs/harn/issues/345)) lands:

```sh
harn add github.com/burin-labs/harn-openapi@v0.1.0
```

Until then, depend on this repo via a path import in your `harn.toml`:

```toml
[dependencies]
harn-openapi = { path = "../harn-openapi" }
```

## Usage

```harn
import openapi from "harn-openapi"

let raw = read_file("./notion.openapi.json")
let doc = openapi.parse(raw)

// Walk operations
for op in openapi.operations(doc) {
  println("${op.method} ${op.path} -> ${op.operation_id}")
}

// Generate Harn SDK source from the parsed document
let src = openapi.codegen_module(doc, {
  module_name: "notion",
  client_name: "Client",
})
write_file("./src/lib.harn", src)
```

## Development

This repo is being built out by Claude Code sessions following a structured
prompt. **Read [SESSION_PROMPT.md](./SESSION_PROMPT.md) before making changes.**

The upstream Harn language and runtime live at
[burin-labs/harn](https://github.com/burin-labs/harn). For local development,
clone it next to this repo at `../harn`.

## License

Dual-licensed under MIT and Apache-2.0. Choose whichever you prefer.

- [LICENSE-MIT](./LICENSE-MIT)
- [LICENSE-APACHE](./LICENSE-APACHE)
