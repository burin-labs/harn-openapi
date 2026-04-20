# SESSION_PROMPT.md — harn-openapi v0

You are picking up the v0 build of `harn-openapi`, a pure-Harn library that
parses OpenAPI 3.1 documents and generates typed Harn SDK source code from
them. This file is your self-contained bootstrap. Read it end-to-end before
touching any code.

## Pivot context (60 seconds)

Harn is moving per-provider connectors **out** of its Rust monorepo and into
external pure-Harn libraries under `burin-labs/`. This repo is the first
"vertical" library in that pivot — not a connector itself, but the codegen
backbone for typed SDKs like `notion-sdk-harn` (which then feeds
`harn-notion-connector`).

Tracking ticket: [Pure-Harn Connectors Pivot epic
#350](https://github.com/burin-labs/harn/issues/350).

## What this repo specifically delivers

Pure-Harn modules that:

1. Parse an OpenAPI 3.1 JSON document into ergonomic typed Harn dicts.
2. Walk the parsed document via small, composable helpers (operations,
   schemas, components, enumerations, security schemes).
3. Emit a complete typed SDK module — Harn source code as a string —
   from a parsed document, suitable for writing to disk and committing
   to a sibling repo (e.g. `notion-sdk-harn/src/lib.harn`).

## What's unblocked

**Everything.** This repo has no upstream blockers:

- JSON parsing (`json_parse` / `parse_json`) is in stdlib.
- File reads (`read_file`) and writes (`write_file`) are in stdlib.
- Template rendering (`render_prompt` / `render`) is in stdlib and is the
  recommended engine for codegen output. See the prompt-templating section
  of the quickref and `docs/src/prompt-templating.md` upstream.
- Dicts, lists, strings, regex — all standard.

## What's blocked / not your problem yet

- **Distribution**: until [harn#345 (Package management
  v0)](https://github.com/burin-labs/harn/issues/345) lands, this library
  cannot be `harn add`'d. Downstream repos consume it via `path =
  "../harn-openapi"` until then. Don't attempt to invent registry plumbing.
- **Connector interface**: not relevant here. This repo doesn't implement
  a connector. If you find yourself wiring up `provider_id()` /
  `normalize_inbound()`, you're in the wrong repo.

## v0 milestones (build in order)

### M1 — Parse end-to-end without crashing

- Add `tests/fixtures/notion.openapi.json` by downloading
  `https://developers.notion.com/openapi.json` and committing it (~995KB,
  ~150+ schemas). Document the fetch command in a comment in `tests/`.
- Implement `parse(json_string) -> dict` in `src/lib.harn`. Returns a
  normalized doc structure: `{ openapi, info, servers, paths, components,
  security_schemes, tags }`. Deliberately fail fast on `openapi != "3.1.x"`.
- Acceptance: `tests/parse_smoke.harn` reads the Notion fixture, parses it,
  asserts there are >100 operations and the title contains "Notion", and
  exits 0.

### M2 — Walking helpers

- `operations(doc) -> list<{method, path, operation_id, summary, parameters,
  request_body, responses, security}>` — flattens path-itemed operations.
- `schema(doc, ref_or_inline) -> dict` — resolves `$ref` strings of the form
  `"#/components/schemas/Foo"` against `doc.components.schemas`. Handles
  one level of `allOf` merging; leaves `oneOf` / `anyOf` un-merged
  (callers decide). Returns the inline schema unchanged when not a `$ref`.
- `enum_values(schema) -> option<list<string>>` — returns the enum array
  if present, none otherwise.
- Acceptance: `tests/walk_smoke.harn` enumerates the Notion spec's
  operations, resolves the request body schema on `databases.query`, and
  prints the field names of the request schema. No panics.

### M3 — Codegen MVP

- `codegen_module(doc, options) -> string` — emits one Harn module that
  exposes a `Client` factory and one function per operation. Use
  `render_prompt` with templates stored as triple-quoted strings inside
  the module (no external `.harn.prompt` files for v0 — keeps everything
  one-file-loadable).
- Options shape: `{ module_name: string, client_name: string,
  default_base_url: string?, header_overrides: dict<string, string>? }`.
- Each generated function:
  - Takes the path/query/body params of its operation.
  - Constructs the URL with path interpolation.
  - Calls `http_get` / `http_post` / `http_patch` / etc. with the auth
    headers from the Client.
  - Returns the parsed JSON response (or an error result).
- Acceptance: `tests/codegen_smoke.harn` reads the Notion fixture, runs
  `codegen_module`, writes the result to a temp path, then `harn check`s
  the output and asserts no parse errors. (Use `subprocess` builtins or
  shell out to `harn check` from a small shell helper if needed.)

### M4 — Polish & docs

- Add a top-of-file doc comment block to `src/lib.harn` describing the
  exported surface.
- Add `scripts/regen_demo.harn` that demonstrates the
  parse → codegen → write loop end-to-end against the bundled fixture.
- Update README usage example if the actual surface drifted from the
  aspirational example written there.

## Recommended workflow

1. **Use a worktree.** Don't develop on the main checkout of
   `/Users/ksinder/projects/harn-openapi` directly:
   ```sh
   cd /Users/ksinder/projects/harn-openapi
   git worktree add ../harn-openapi-wt-m1 -b m1-parser
   ```
   Iterate inside `../harn-openapi-wt-m1`. Merge back to `main` when M1
   is green.
2. Scaffold `src/lib.harn` with stub function signatures and a
   `module_doc` constant before filling them in. Run `harn check` early
   and often — it's faster than waiting for runtime errors.
3. Write the smoke test for a milestone first; let it fail. Then build
   the implementation. Don't pre-implement; the spec is rich enough that
   you'll over-engineer if you do.
4. Keep `harn fmt --check` green at every commit. The pre-commit hooks
   in upstream harn won't fire here, but the same conventions apply.

## Reference materials

- Harn quickref (autoload-friendly):
  `/Users/ksinder/projects/harn/docs/llm/harn-quickref.md` — read this
  first if you're new to Harn syntax.
- Harn language spec:
  `/Users/ksinder/projects/harn/spec/HARN_SPEC.md` — canonical reference.
- Prompt template engine:
  `/Users/ksinder/projects/harn/docs/src/prompt-templating.md`. Single
  authoritative implementation lives at
  `/Users/ksinder/projects/harn/crates/harn-vm/src/stdlib/template.rs`.
- OpenAPI 3.1 spec: <https://spec.openapis.org/oas/v3.1.0>.
- Notion's OpenAPI: <https://developers.notion.com/openapi.json>.

## Testing expectations

- Every public function in `src/lib.harn` should be exercised by at
  least one test under `tests/`.
- Keep `tests/fixtures/notion.openapi.json` pinned (don't auto-refresh
  it) so tests stay deterministic.
- Run before committing:
  ```sh
  cd /Users/ksinder/projects/harn
  cargo run --quiet --bin harn -- check /Users/ksinder/projects/harn-openapi/src/lib.harn
  cargo run --quiet --bin harn -- lint  /Users/ksinder/projects/harn-openapi/src/lib.harn
  cargo run --quiet --bin harn -- fmt --check /Users/ksinder/projects/harn-openapi/src/lib.harn
  for t in /Users/ksinder/projects/harn-openapi/tests/*.harn; do
    cargo run --quiet --bin harn -- run "$t" || exit 1
  done
  ```

## Definition of done for v0

- [ ] `parse()` round-trips the Notion OpenAPI fixture without errors.
- [ ] `operations()`, `schema()`, `enum_values()` all have green smoke tests.
- [ ] `codegen_module()` emits Harn source that passes `harn check`.
- [ ] `src/lib.harn`, `harn.toml`, README usage example all consistent.
- [ ] `scripts/regen_demo.harn` runs cleanly against the fixture.
- [ ] No TODO comments in `src/lib.harn` for surfaces claimed in README.
- [ ] When [#345](https://github.com/burin-labs/harn/issues/345) lands,
      `harn add github.com/burin-labs/harn-openapi` resolves this repo
      and downstream `notion-sdk-harn` codegen works against it via the
      registry path (not just `path = "../harn-openapi"`).
