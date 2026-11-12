<p align="center"><img src="docs/content/assets/logo.svg" alt="PRIS" width="120"></p>

# Programmable Intelligent Space (PRIS)

[![License](https://img.shields.io/github/license/luizcarloscf/pris?color=6366f1)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-14b8a6?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://docs.astral.sh/uv/)
[![RabbitMQ](https://img.shields.io/badge/broker-RabbitMQ-FF6600?logo=rabbitmq&logoColor=white)](https://www.rabbitmq.com)
[![OpenTelemetry](https://img.shields.io/badge/telemetry-OpenTelemetry-425CC7?logo=opentelemetry&logoColor=white)](https://opentelemetry.io)
[![Last commit](https://img.shields.io/github/last-commit/luizcarloscf/pris?color=14b8a6)](https://github.com/luizcarloscf/pris/commits/main)

Python libraries, the services, and the ROS 2 packages that connect robots to it.

## Packages

The libraries the services are built on. They form one uv workspace at the repository root, so they are developed and tested together; each is released on its own git tag, which the services depend on.

| Package | Version | Contents |
|---|---|---|
| [`pris-msgs`](packages/pris-msgs/) | [![pris-msgs version](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Fluizcarloscf%2Fpris%2Fmain%2Fpackages%2Fpris-msgs%2Fpyproject.toml&query=%24.project.version&label=version&color=6366f1)](packages/pris-msgs/pyproject.toml) | message schemas (`.proto`), their generated code, JSON load/save, NumPy helpers |
| [`pris-wire`](packages/pris-wire/) | [![pris-wire version](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Fluizcarloscf%2Fpris%2Fmain%2Fpackages%2Fpris-wire%2Fpyproject.toml&query=%24.project.version&label=version&color=6366f1)](packages/pris-wire/pyproject.toml) | publish/subscribe and request/reply over RabbitMQ |
| [`opentelemetry-instrumentation-pris-wire`](packages/opentelemetry-instrumentation-pris-wire/) | [![opentelemetry-instrumentation-pris-wire version](https://img.shields.io/badge/dynamic/regex?url=https%3A%2F%2Fraw.githubusercontent.com%2Fluizcarloscf%2Fpris%2Fmain%2Fpackages%2Fopentelemetry-instrumentation-pris-wire%2Fsrc%2Fopentelemetry%2Finstrumentation%2Fpris_wire%2Fversion.py&search=__version__%20%3D%20%22%28%5B%5E%22%5D%2B%29%22&replace=%241&label=version&color=6366f1)](packages/opentelemetry-instrumentation-pris-wire/src/opentelemetry/instrumentation/pris_wire/version.py) | OpenTelemetry tracing and metrics for pris-wire |
| [`pris-common`](packages/pris-common/) | [![pris-common version](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Fluizcarloscf%2Fpris%2Fmain%2Fpackages%2Fpris-common%2Fpyproject.toml&query=%24.project.version&label=version&color=6366f1)](packages/pris-common/pyproject.toml) | code shared by the services: camera calibrations and frame transformations fetched at startup |

## Services

The programs that run on the space, each an independent project in `services/` with its own `uv.lock`, image and Kubernetes manifests in `k8s/`. Each README has the interface, options and how to run it.

| Service | Version | Does |
|---|---|---|
| [`pris-camera-gateway`](services/pris-camera-gateway/) | [![pris-camera-gateway version](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Fluizcarloscf%2Fpris%2Fmain%2Fservices%2Fpris-camera-gateway%2Fpyproject.toml&query=%24.project.version&label=version&color=6366f1)](services/pris-camera-gateway/pyproject.toml) | publishes the frames of a Blackfly GigE camera and serves its settings |
| [`pris-calibration-server`](services/pris-calibration-server/) | [![pris-calibration-server version](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Fluizcarloscf%2Fpris%2Fmain%2Fservices%2Fpris-calibration-server%2Fpyproject.toml&query=%24.project.version&label=version&color=6366f1)](services/pris-calibration-server/pyproject.toml) | serves the camera calibrations of a site |
| [`pris-frame-transformation`](services/pris-frame-transformation/) | [![pris-frame-transformation version](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Fluizcarloscf%2Fpris%2Fmain%2Fservices%2Fpris-frame-transformation%2Fpyproject.toml&query=%24.project.version&label=version&color=6366f1)](services/pris-frame-transformation/pyproject.toml) | the graph of coordinate frames and the transformation between any two |
| [`pris-aruco-detector`](services/pris-aruco-detector/) | [![pris-aruco-detector version](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Fluizcarloscf%2Fpris%2Fmain%2Fservices%2Fpris-aruco-detector%2Fpyproject.toml&query=%24.project.version&label=version&color=6366f1)](services/pris-aruco-detector/pyproject.toml) | detects ArUco markers in the cameras' frames |
| [`pris-aruco-localization`](services/pris-aruco-localization/) | [![pris-aruco-localization version](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Fluizcarloscf%2Fpris%2Fmain%2Fservices%2Fpris-aruco-localization%2Fpyproject.toml&query=%24.project.version&label=version&color=6366f1)](services/pris-aruco-localization/pyproject.toml) | localizes ArUco markers in the world from several cameras |
| [`pris-broker-events`](services/pris-broker-events/) | [![pris-broker-events version](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Fluizcarloscf%2Fpris%2Fmain%2Fservices%2Fpris-broker-events%2Fpyproject.toml&query=%24.project.version&label=version&color=6366f1)](services/pris-broker-events/pyproject.toml) | publishes the consumers of each topic |

## Other folders

| Folder | Contents |
|---|---|
| [`calibrations/`](calibrations/) | camera calibrations of each site |
| [`k8s/`](k8s/) | Kubernetes manifests: the namespace `pris`, RabbitMQ, Jaeger, the OpenTelemetry Collector and the services |
| [`docs/`](docs/) | the documentation site (Zensical) |

## Quick start

> **_NOTE:_** Install [Python 3.12](https://www.python.org/downloads/), [uv](https://docs.astral.sh/uv/getting-started/installation/) and [Docker](https://docs.docker.com/engine/install/) before you start.

```shell
make sync         # .venv on Python 3.12, every package editable
make broker-up    # RabbitMQ on localhost:5672, required by make test
make test         # the test suite
make help         # everything else
```
