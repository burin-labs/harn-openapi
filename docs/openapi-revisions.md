# Supported OpenAPI revisions

The parser and schema graph share `classify_openapi_revision`. Generation
supports the following revision matrix:

| Revision | Schema dialect | Additional supported contracts |
| --- | --- | --- |
| `3.1.<patch>` | Draft 2020-12 or the OpenAPI 3.1 base dialect | Buffered media, local schema references |
| `3.2.0` | Draft 2020-12 or the OpenAPI 3.1 base dialect | Document `$self`, whole-query content, named servers |

The parser requires a full revision string. Other major or minor revisions,
including `3.2.1`, fail. The standalone schema-graph API retains its existing
explicit `3.1` abbreviation. The [OpenAPI 3.2.0 specification](https://spec.openapis.org/oas/v3.2.0.html)
still uses the OpenAPI 3.1 schema dialect URI.

## Document identity and references

`parse(json_string, {retrieval_uri: absolute_uri})` records the retrieval
location separately from the document's `$self`. A relative `$self` resolves
against the retrieval location. Without `$self`, the retrieval location is
the document reference base.

References to that same resource, including relative URI references, resolve
to its local JSON Pointers. A reference must use `$self` when it is present;
the retrieval URI doesn't become a second identity. Fragment-only local
references also work without a retrieval location.

Parsing doesn't fetch other resources. External references fail with a
diagnostic requiring an explicit host resource loader. This package doesn't
provide that loader. Document self identities containing fragments, JSON
Schema `$id`, anchors and dynamic reference scopes are unsupported.

Server URLs use the retrieval location as their relative base. They ignore
`$self`. A relative server URL therefore requires a retrieval location.
Resolved server URLs must use HTTP or HTTPS and have no query or fragment.

## Whole-query content

An `in: querystring` parameter treats the complete query as one value. Its
required OpenAPI name identifies the generated input property; that name
isn't included in the HTTP query.

The parameter must declare exactly one `content` Media Type Object. Supported
types are JSON, structured-syntax `+json`, and form-urlencoded. Serialization
uses the same [media plan](media-contracts.md) as request bodies.

JSON is compacted and percent-encoded once. Form content uses its existing
encoding, with spaces as `+` and literal plus signs as `%2B`. An omitted
optional querystring input contributes no query.

Each path or operation scope may declare at most one querystring parameter.
It can't coexist with ordinary query parameters or query authentication.
Schema-style serialization fields, unsupported media and ambiguous content
maps fail before generation.

## Named servers

OpenAPI 3.2 server names must be unique and nonempty. Names retain their URL
identity when the declaration order changes. Unnamed default selection still
uses the first server and expands its variables with declared defaults.

Generated clients accept an optional fourth `server_name` argument. Generated
runtime configuration also accepts `server_name`; the environment projection
reads `<PREFIX>_SERVER_NAME`. An unknown name fails before tools are published.
An explicit base URL override can't be combined with a server name.

Operation servers override path servers, which override document servers.
The selected name resolves in each operation's effective server list. A name
missing from a published operation fails registry configuration. An explicit
client base URL overrides these declared defaults. Variable defaults must
belong to their declared enum; undeclared variables fail.

## Unsupported operations and streams

`QUERY` and `additionalOperations` fail before generation. Sequential media
contracts using `itemSchema`, `itemEncoding` or `prefixEncoding` require a
streaming adapter. See [media limits](media-contracts.md#responses-and-limits).

The executable dialect fixture exercises parsing, same-document references,
generated clients, the registry, the real CLI and stdio MCP:

```sh
HARN_BIN="$(command -v harn)" harn test tests/openapi_dialect_smoke.harn
```
