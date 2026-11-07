# pris

Monorepo of PRIS, a Programmable Intelligent Space: the Python libraries, the services of the space, and the ROS 2 packages that connect robots to it. Every component talks to the others through RabbitMQ, with Protocol Buffers messages.

**Documentation:** [`docs/content/`](docs/content/index.md), or browse it with `make docs-serve` (http://localhost:8001). What is done and planned is in [Status](docs/content/project/status.md).

| Path | Contents |
|---|---|
| `calibrations/` | camera calibrations of each site |
| `docs/` | the documentation site (Zensical) |

## Quick start

Needs [uv](https://docs.astral.sh/uv/) and Docker:

```shell
make sync         # .venv on Python 3.12, every package editable
make broker-up    # RabbitMQ on localhost:5672, required by make test
make test         # the test suite
make help         # everything else
```
