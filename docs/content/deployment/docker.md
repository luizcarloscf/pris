# Docker images

Every service ships as a container image, built locally; nothing in the repository pushes images to a registry.

```shell
make image SERVICE=pris-calibration-server     # luizcarloscf/pris-calibration-server:0.1.0
```

The root target runs `make image` in the service's folder, which can also be run there. The image is named `$(DOCKER_USERNAME)/<service>:<version>`: `DOCKER_USERNAME` defaults to `luizcarloscf` (`make image DOCKER_USERNAME=... SERVICE=...` to change it), and the version is the one in the service's `pyproject.toml`.

!!! info "New to Docker?"

    - [Multi-stage builds](https://docs.docker.com/build/building/multi-stage/): a build stage and a smaller final one;
    - [Using uv in Docker](https://docs.astral.sh/uv/guides/integration/docker/): the pattern the Dockerfiles follow.

## How an image is built

Each service has its Dockerfile in `services/<service>/etc/docker/Dockerfile`, and its build context is the service's own folder: an image never sees the rest of the repository. A `.dockerignore` there keeps `.venv`, the caches and the tests out of it.

1. **Build stage** (Ubuntu 24.04, Python 3.12, git and uv): `uv sync --frozen --no-dev` installs exactly the service's `uv.lock`, fetching the libraries from their [git tags](git-dependencies.md), first the dependencies alone (a layer of their own), then the service.
2. **Final stage** (Ubuntu 24.04 and Python 3.12): the virtual environment of the build stage and the service's default options, `etc/conf/options.json`, at `/etc/<service>/options.json`.

Builds run on the host network (`docker build --network host`): Docker's bridge network is unreliable on some hosts. Run containers the same way.

## Running an image

The default options are those of a cluster: the broker at `rabbitmq.pris` and telemetry sent to `otel-collector.pris` (see [Kubernetes](kubernetes.md)). On one host, mount your own options over them; without a `telemetry` field, telemetry is off:

```shell
cat > /tmp/options.json <<END
{"broker_uri": "amqp://guest:guest@localhost:5672", "calibrations_path": "/etc/calibrations"}
END
docker run --rm --network host \
    -v /tmp/options.json:/etc/pris-calibration-server/options.json:ro \
    -v $PWD/calibrations/labvisio:/etc/calibrations:ro \
    luizcarloscf/pris-calibration-server:0.1.0
```
