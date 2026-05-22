# harn-openapi v0.1.0 migration note

`harn-openapi` v0.1.0 is the first package-manager-ready release shape for
connector and SDK repos. Once the `v0.1.0` tag exists, it replaces
sibling-checkout assumptions with a versioned Harn package dependency while
keeping path overrides for local multi-repo development.

## Consumer dependency

Use a versioned package ref in normal connector and SDK repos after the release
tag is published:

```sh
harn add github.com/burin-labs/harn-openapi@v0.1.0
```

Then import through the package export path:

```harn
import { codegen_module, operations, parse } from "harn-openapi/default"
```

Type aliases are available from the default export:

```harn
import "harn-openapi/default"
```

After the release tag exists, do not require a sibling `../harn-openapi`
checkout in CI or in fresh-clone bootstrap docs. CI should use the pinned Harn
CLI and let Harn resolve package dependencies from `harn.toml`.

## Generated SDK names

Generated operation functions use `snake_case` identifiers. OpenAPI ids such
as `getPage`, `get-page`, and `get page` all map to `get_page` with numeric
suffixes added only when two operations collide after normalization.

If a pre-release generated SDK committed lowercased camelCase names such as
`getpage`, regenerate it with the v0.1.0 codegen output and update callers to
the `snake_case` names.

## Local override

For active cross-repo development, keep the override local and explicit:

```toml
[dependencies]
harn-openapi = { path = "../harn-openapi" }
```

Before opening a PR in a consuming repo, switch back to the versioned package
dependency if the tag exists. Otherwise, document that the PR is intentionally
stacked on unpublished `harn-openapi` work.

## Verification

Run the consumer repo's normal Harn gate with the pinned Harn CLI. In this
repo, the equivalent package-manager smoke is:

```sh
HARN_PACKAGE_REF=github.com/burin-labs/harn-openapi@v0.1.0 \
  harn run scripts/package_install_smoke.harn
```

During unreleased PR work, omit `HARN_PACKAGE_REF`; the smoke installs the
current checkout with `@HEAD` so package install behavior is still covered
before the release tag exists.
