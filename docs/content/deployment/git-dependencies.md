# Libraries from git tags

The libraries ([pris-msgs](../libraries/pris-msgs.md), [pris-wire](../libraries/pris-wire.md), the [OpenTelemetry instrumentation](../libraries/opentelemetry-instrumentation-pris-wire.md) and [pris-common](../libraries/pris-common.md)) are released as git tags of this repository, `<library>-v<version>`, and installed from there: no package index is involved.

```shell
pip install "pris-wire @ git+https://github.com/luizcarloscf/pris@pris-wire-v1.0.0#subdirectory=packages/pris-wire"
```

!!! info "How uv handles git dependencies"

    - [Git dependencies](https://docs.astral.sh/uv/concepts/projects/dependencies/#git): `tag`, `subdirectory` and how they are locked;
    - [Workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/): why the libraries share one environment at the repository root.

## In the repository

At the root, the libraries form a uv workspace: they use each other from their folders, so a change to one is seen by the others at once. Every service is an independent project instead, with its own `uv.lock`; its `pyproject.toml` takes each library from a tag:

```toml
[tool.uv.sources]
pris-wire = { git = "https://github.com/luizcarloscf/pris", tag = "pris-wire-v1.0.0", subdirectory = "packages/pris-wire" }
```

`uv.lock` pins the commit of each tag, so a service, and its image, gets the same code until its sources are changed.

## Releasing a library

1. Change the library, its version in `pyproject.toml` (or `version.py` for the instrumentation) and its docs; `make test` and `make lint`.
2. Commit, tag `<library>-v<version>` and push the commit and the tag.
3. In each service that should use it, change `tag` in its `[tool.uv.sources]`, run `uv lock` in its folder, and test it.

A tag that is already published is not moved: the services that locked it would no longer find its commit.
