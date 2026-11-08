# Programmable Intelligent Space (PRIS)

Python libraries, the services, and the ROS 2 packages that connect robots to it.

| Path | Contents |
|---|---|
| [`packages/pris-msgs/`](packages/pris-msgs/) | message schemas (`.proto`), their generated code, JSON load/save, NumPy helpers |
| [`packages/pris-wire/`](packages/pris-wire/) | publish/subscribe and request/reply over RabbitMQ |
| [`packages/opentelemetry-instrumentation-pris-wire/`](packages/opentelemetry-instrumentation-pris-wire/) | OpenTelemetry tracing and metrics for pris-wire |
| [`calibrations/`](calibrations/) | camera calibrations of each site |
| [`docs/`](docs/) | the documentation site (Zensical) |

## Quick start

> **_NOTE:_** Install [Python 3.12](https://www.python.org/downloads/), [uv](https://docs.astral.sh/uv/getting-started/installation/) and [Docker](https://docs.docker.com/engine/install/) before you start.

```shell
make sync         # .venv on Python 3.12, every package editable
make broker-up    # RabbitMQ on localhost:5672, required by make test
make test         # the test suite
make help         # everything else
```
