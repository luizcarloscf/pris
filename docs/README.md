# Documentation

The documentation site of PRIS, built with [Zensical](https://zensical.org). Pages are in
[`content/`](content/), the navigation in [`zensical.toml`](zensical.toml).

From the repository root:

```shell
make docs-serve   # live reload on http://localhost:8001
make docs-build   # build into docs/site (strict: fails on broken links)
make docs-image   # nginx image with the site, tagged with VERSION
```
