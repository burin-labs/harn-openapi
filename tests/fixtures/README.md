# Pinned test fixtures

These files are checked in verbatim so tests stay deterministic. Do **not**
auto-refresh them in CI or in tests.

## `notion.openapi.json`

Notion's public OpenAPI 3.1 document, fetched with:

```sh
curl -fsSL https://developers.notion.com/openapi.json \
  -o tests/fixtures/notion.openapi.json
```

Refresh manually when intentionally re-pinning to a newer spec snapshot.
