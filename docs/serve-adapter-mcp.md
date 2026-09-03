# Serve an adapter over MCP

Start the generated registry as an MCP stdio server:

```sh
harn serve mcp ./src/main.harn
```

Configure the MCP client to launch that command and pass the variables from
[Configure an adapter environment](configure-adapter-environment.md). Do not
put credential values in command arguments.

The MCP server and CLI do not have separate operation implementations. Both
load the registry from `adapter_registry`, apply the same governance audience,
validate the same JSON Schemas, and invoke the same generated SDK function.
Tool names, descriptions, annotations, icons, and task support come from the
same OpenAPI operation and optional `x-harn` metadata.

Check what the server will publish before adding it to a client:

```sh
harn tool schema ./src/main.harn --pretty
```

An invalid base URL or unavailable required security alternative stops startup
before `tools/list` can publish a partial server. Diagnostics identify the
operation and scheme names without exposing configured values.
