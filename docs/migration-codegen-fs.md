# Pass filesystem authority to code generation

`codegen_module` now accepts `HarnessFs` instead of the root `Harness`. Update
callers when moving to a release that contains this change.

## Change the call

Before:

```harn
const source = codegen_module(harness, doc, options)
```

After:

```harn
const source = codegen_module(harness.fs, doc, options)
```

No option or generated-source behavior changed. The narrower argument states
the function's only host dependency: rendering a template through the
filesystem capability.

## Verify the consumer

Run the consumer package's normal checks and regenerate its committed SDK:

```sh
harn check src scripts tests
harn test tests
```

Review the generated diff before committing it. See the
[quick start](../README.md#quick-start) for a complete example and the
[Harn repository guide](https://github.com/burin-labs/harn/blob/main/AGENTS.md)
for current capability conventions.
