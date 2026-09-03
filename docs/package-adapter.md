# Package an adapter

Package the generated SDK and executable entrypoint as one Harn package.

The generated manifest should export both files:

```toml
[package]
name = "widgets-adapter"
version = "0.1.0"

[exports]
default = "src/lib.harn"
entrypoint = "src/main.harn"
```

Check the package boundary:

```sh
harn package check
harn check src/lib.harn src/main.harn
harn fmt --check src/lib.harn src/main.harn
```

Run each projection from the package checkout before publishing:

```sh
harn tool schema src/main.harn --pretty
harn tool run src/main.harn --help
harn serve mcp src/main.harn
```

Keep the OpenAPI input and generation command in source control so a reviewer
can reproduce `src/lib.harn`, `src/main.harn`, and `harn.toml`. Keep deployment
credentials outside the package.

Next, [distribute the verified package](distribute-adapter.md).
