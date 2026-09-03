# Distribute an adapter

Publish an immutable Git ref after the generated package passes its checks.

Consumers install an exact release tag:

```sh
harn add github.com/example/widgets-adapter@v0.1.0
harn install --locked
```

Applications import the typed SDK from the default export:

```harn
import { AdapterClient, get_widget } from "widgets-adapter/default"
```

Hosts launch the package's named executable export according to their package
resolution policy. During local development, invoke `src/main.harn` directly:

```sh
harn tool run src/main.harn --help
harn serve mcp src/main.harn
```

Ship the OpenAPI input, generator version, and generated files in the same tag.
Pin downstream consumers to that tag and lock their dependency graph. Rotate
credentials in the deployment host without regenerating or republishing the
package.

Before announcing a release, install the tag into a clean temporary project,
run `harn install --locked --offline`, import the typed SDK, and check the
entrypoint. This detects missing exports and undeclared dependencies that an
in-repository test can hide.
