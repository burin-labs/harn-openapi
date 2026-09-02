# Migrate to scheme-keyed credentials

Generated clients no longer accept shared bearer, Basic, or API-key fields.
Pass one `AdapterCredential` per original OpenAPI security-scheme name.

Replace shared positional credential fields with:

```harn
new_client(
  "https://api.example.com",
  {
    bearerAuth: {token: "bearer-token"},
    basicAuth: {username: "basic-user", password: "basic-password"},
    headerKey: {value: "api-key"},
  },
  {},
)
```

Provider callbacks move into the relevant scheme record:

```harn
new_client(
  "https://api.example.com",
  {bearerAuth: {token_provider: token_from_secret(harness.secrets, "provider/token")}},
  {},
)
```

Regenerate the SDK and its entrypoint together. Remove hand-written MCP and CLI
dispatch code, then use `adapter_registry` or the generated `src/main.harn` as
the one executable path. Required credentials now fail before registry
publication, and multiple OpenAPI security alternatives are selected at
runtime instead of hard-coding the first alternative.
