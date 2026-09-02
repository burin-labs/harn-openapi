# Run an adapter as a CLI

Use Harn's CLI projection against the generated executable entrypoint.

Inspect the command tree first:

```sh
harn tool run ./src/main.harn --help
```

Inspect one nested command:

```sh
harn tool run ./src/main.harn widgets get --help
```

Invoke it with JSON-Schema-derived flags:

```sh
harn tool run ./src/main.harn widgets get --widget-id w_123
```

The command path comes from `x-harn.cli.command`, or from the generated
namespace and tool name when the extension omits it. Hidden commands remain
invocable by their exact path. Input and output use the same schemas and
handler closure as MCP.

To inspect the machine-readable contract without invoking a handler:

```sh
harn tool schema ./src/main.harn --pretty
```

If startup reports a missing base URL or credential, fix the
[environment configuration](configure-adapter-environment.md). Harn validates
all exposed operations before publishing the command tree.
