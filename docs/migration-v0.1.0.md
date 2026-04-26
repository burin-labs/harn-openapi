# harn-openapi v0.1.0 migration note

`harn-openapi` v0.1.0 is the first package-manager-ready release shape for
connector and SDK repos. It replaces sibling-checkout assumptions with a
versioned Harn package dependency while keeping path overrides for local
multi-repo development.

## Consumer dependency

Use a versioned package ref in normal connector and SDK repos:

```sh
harn add github.com/burin-labs/harn-openapi@v0.1.0
```

Then import through the package export path:

```harn
import { codegen_module, operations, parse } from "harn-openapi/default"
```

Do not require a sibling `../harn-openapi` checkout in CI or in fresh-clone
bootstrap docs. CI should install the pinned `harn-cli` from crates.io and let
Harn resolve package dependencies from `harn.toml`.

## Local override

For active cross-repo development, keep the override local and explicit:

```toml
[dependencies]
harn-openapi = { path = "../harn-openapi" }
```

Before opening a PR in a consuming repo, switch back to the versioned package
dependency or document why the PR is intentionally stacked on unpublished
`harn-openapi` work.

## Verification

Run the consumer repo's normal Harn gate with the crates.io-installed CLI. In
this repo, the equivalent package-manager smoke is:

```sh
HARN_PACKAGE_REF=github.com/burin-labs/harn-openapi@v0.1.0 \
  harn run scripts/package_install_smoke.harn
```

During unreleased PR work, omit `HARN_PACKAGE_REF`; the smoke installs the
current checkout with `@HEAD` so package install behavior is still covered
before the release tag exists.
