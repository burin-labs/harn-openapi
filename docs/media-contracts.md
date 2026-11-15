# Generated HTTP media contracts

`OperationMediaPlan` determines request serialization, response decoding, headers
and registry schemas. The CLI and MCP invoke the same generated handler.

## Request representations

| Declared media type | Generated body value | HTTP representation |
| --- | --- | --- |
| `application/json` and types ending in `+json` | A value matching the declared schema | Compact JSON |
| `application/x-www-form-urlencoded` | An object matching the field schema | Form encoding, with spaces as `+` |
| `multipart/form-data` | An object of part records | Native HTTP multipart encoding |
| `text/*` | A string | UTF-8 text |
| `application/octet-stream`, `application/pdf`, `image/*`, `audio/*`, `video/*` | Harn `bytes` | Unencoded bytes |

Each content key must name an exact media type. Media ranges don't select a
serializer. A JSON Schema `format: binary` annotation doesn't select a byte
serializer; the surrounding Media Type Object determines serialization.

The generated headers use the selected `Content-Type`. `Accept` lists the
declared success and default response representations, or `*/*` when none are
declared. Conflicting caller headers fail before HTTP.

### JSON

For an operation with one JSON representation, its `body` is the JSON value:

```json
{"body":{"value":"sentinel"}}
```

An omitted optional body sends no body. An explicit JSON `null` sends the four
bytes `null` when the schema permits it:

```json
{"body":null}
```

An empty JSON schema preserves arrays, objects, strings, numbers, booleans and
null. A false schema forbids the value.

### Forms

Form fields follow their declared Encoding Objects. Repeated fields retain
their names and order; non-exploded arrays use their declared delimiter.

```json
{"body":{"title":"a + b","tags":["one","two"]}}
```

With ordinary exploded form fields, this produces
`tags=one&tags=two&title=a+%2B+b`. Object fields use their declared content
encoding. Unsupported combinations fail during generation.

### Multipart uploads

Each property is a part record. Its `value` contains the payload; `filename`,
`content_type` and `headers` provide metadata allowed by the declaration.
Array properties use a list of part records with the same field name.

```json
{
  "body": {
    "file": {
      "value": {"$bytes_b64":"AAEC/w=="},
      "filename": "proof.bin",
      "headers": {"X-Part":"present"}
    },
    "title": {"value":"title"},
    "tags": [{"value":"a"},{"value":"b"}]
  }
}
```

This example requires an operation declaring the `file`, `title` and `tags`
parts, binary file content and the `X-Part` header. Save input in a file and
pass its path to the generated command:

```sh
harn tool run src/main.harn send_multipart --harn-input @upload.json --json
```

The native HTTP encoder creates the boundary. File contents don't enter
generated source, catalog metadata or command arguments.

Part headers retain their Header Object constraints, including local Header
references and each header schema's definitions and component references.
Declared scalar values use simple serialization; for example, an integer header
value `7` sends the text `7`. Header content objects, non-scalar schemas and
other header styles require a value adapter and fail during generation.

Required properties, dependent required properties, property names,
property counts and array length bounds retain their meaning through part
wrappers. Value-dependent object or array assertions that cannot be preserved
through those wrappers fail during generation with the unsupported keyword.

### Text and bytes

A text body is a string:

```json
{"body":"plain text"}
```

The CLI and MCP use Harn's canonical bytes representation for byte bodies:

```json
{"body":{"$bytes_b64":"AAEC/w=="}}
```

The handler receives native bytes before the HTTP call. The HTTP encoder sends
those bytes directly, without JSON encoding the envelope.

A false binary schema forbids the value. String length, pattern and other
value assertions on opaque binary data require an explicit value adapter and
fail during generation.

### Multiple request representations

An operation declaring several alternatives requires explicit selection:

```json
{"body":{"content_type":"text/plain","value":"selected text"}}
```

The catalog validates the discriminator and the selected value. Undeclared
content types fail before handler entry. Declaration order doesn't choose a
representation.

## Responses and limits

The decoder selects the exact status, then its status range, then `default`.
The declared response media determines whether the result is JSON, a string,
bytes or an empty result. Multiple declared media use the response
`Content-Type`; an absent header is accepted only for a single alternative.
An undeclared representation or a forbidden body fails.

Responses are buffered with a 16 MiB limit. A larger response fails; it isn't
published as a partial result. Non-UTF-8 bytes can't become a text result.
Connector errors retain the shared connector's header redaction and bounded
error-body policy. See [application errors](tool-adapters.md#http-application-errors)
for the separate typed error contract.

`itemSchema`, `itemEncoding`, `prefixEncoding`, event streams, JSON sequences
and JSON-lines media require a streaming adapter and fail during generation.
Referenced Media Type Objects also fail during generation. No streamed item
is advertised as a complete buffered response.

The executable media fixture covers these representations through the same
recording server for the real CLI and stdio MCP:

```sh
HARN_BIN="$(command -v harn)" harn test tests/media_transport_smoke.harn
```
