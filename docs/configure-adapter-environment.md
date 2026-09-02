# Configure an adapter environment

Set the generated base URL and credential variables in the process that starts
the adapter. Generated source contains variable names, never secret values.

The prefix comes from `environment_prefix`. For `WIDGETS`, the base URL is:

```sh
export WIDGETS_BASE_URL=https://api.example.com
```

Each referenced OpenAPI security scheme gets its own variables:

| OpenAPI scheme | Generated variable shape |
|---|---|
| bearer, OAuth 2.0, OpenID Connect | `WIDGETS_<SCHEME>_TOKEN` |
| HTTP Basic | `WIDGETS_<SCHEME>_USERNAME` and `WIDGETS_<SCHEME>_PASSWORD` |
| API key | `WIDGETS_<SCHEME>_API_KEY` |
| mutual TLS | no secret variable; configure the client certificate in the host |

The scheme stem is uppercase and non-alphanumeric characters become `_`. If
two names produce the same stem, the generator appends a stable hash suffix.
Inspect `adapter_security_plan(doc, "WIDGETS")` when deployment automation
needs the exact names.

For a scheme named `bearerAuth`:

```sh
export WIDGETS_BEARERAUTH_TOKEN=replace-with-a-secret-store-reference
```

Prefer the platform's secret injection mechanism over shell history or a
checked-in environment file. The host owns OAuth authorization, refresh,
rotation, secure storage, tenant selection, and mutual-TLS certificate setup.
For programmatic clients, a scheme credential may use a request-time
`token_provider`, `value_provider`, or `basic_provider` closure instead of a
static value.

Configuration is validated before tools are published. An operation requiring
`[{bearerAuth: [], headerKey: []}, {basicAuth: []}]` is available only when the
bearer and header key are both configured, or when both Basic fields are
configured. Diagnostics name missing schemes but never print their values.

Next, [run the adapter as a CLI](run-adapter-cli.md) or
[serve it over MCP](serve-adapter-mcp.md).
