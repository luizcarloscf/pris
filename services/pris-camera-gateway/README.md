# pris-camera-gateway

Publishes the frames of one [Blackfly GigE](https://www.flir.com/products/blackfly-gige/) or Blackfly S GigE camera, through Teledyne FLIR's [Spinnaker SDK](https://www.flir.com/products/spinnaker-sdk/), and serves requests to read and change its settings. One gateway runs per camera. It can trigger the camera itself at instants of the host clock, so that several cameras capture together, and it stamps each frame with its capture instant. A high-level introduction is in the [documentation](../../docs/content/services/pris-camera-gateway.md).

Ported from pris-spinnaker-gateway (is-spinnaker-gateway 0.7.0): Spinnaker only (no simulated driver), and everything on one thread.

## Interface

| | Topic | Message |
|---|---|---|
| Publishes | `CameraGateway.<id>.Frame` | `pris.vision.Image` |
| Publishes | `CameraGateway.<id>.Timestamp` | `google.protobuf.Timestamp` |
| Serves | `CameraGateway.<id>.GetConfig` | `pris.common.FieldSelector` → `pris.vision.CameraConfig` |
| Serves | `CameraGateway.<id>.SetConfig` | `pris.vision.CameraConfig` → `google.protobuf.Empty` |

Each frame is an encoded `Image` (JPEG by default). Its `created_at` is the capture instant in the host clock, which `.Timestamp` also carries, in nanoseconds; an incomplete image, or one that can't be encoded, is not published.

`GetConfig` takes the `CameraConfigFields` to read (`ALL` for every group); a setting the camera can't read is left out. `SetConfig` changes the settings present in the request and leaves the others as they are:

| Setting | Notes |
|---|---|
| `sampling.frequency` | on `FREE_RUN`, the camera's frame rate; on `SOFTWARE_SCHEDULED`, the trigger period |
| `sampling.delay` | `SOFTWARE_SCHEDULED` only, in `[0, period]`; kept inside the period when the rate changes |
| `image.format` | JPEG, PNG or WebP, with a compression in (0, 1) |
| `image.color_space`, `image.region` | RGB or GRAY; a region of 2 vertices; only while not streaming, so in `initial_config` |
| `camera.brightness`, `.gain`, `.shutter` | gain and shutter can be automatic |
| `camera.white_balance_rv`, `.white_balance_bu` | RGB only; making one automatic makes both automatic |

Any other setting is refused with `UNIMPLEMENTED` before anything is applied. Out-of-range values come back as `INVALID_ARGUMENT` (the message says the valid interval), and settings that aren't possible in the current mode as `FAILED_PRECONDITION`.

## How it works

At startup the gateway finds the camera by its IP and connects; if it can't, it exits, and Docker or Kubernetes restarts it. It loads the camera's `Default` user set (every start begins from the same state; nothing is saved to the camera), sets the trigger, the stream (`NewestOnly` buffers) and the network options, maps the camera clock to the host's, applies `initial_config`, waits `settle_time` and starts streaming. On `SIGTERM` it releases the camera.

Everything runs on one thread, as in is-spinnaker-gateway 0.3.0, so settings never change while an image is grabbed:

- **`FREE_RUN`**: the camera triggers itself at its frame rate. Each turn waits for the next image, encodes and publishes it, then serves the requests that arrived meanwhile. With `NewestOnly` buffers, a slow encode skips frames instead of falling behind.
- **`SOFTWARE_SCHEDULED`**: the gateway triggers the camera at the instants `k × period + delay` of the host clock. It serves requests until 2 ms before the next instant, busy-waits to it, triggers, and waits at most a period for the image. Cameras on hosts whose clocks are synced (with [chrony](https://chrony-project.org/), for example) capture together; `measure_sync.py` measures how well.
- **Capture instants.** The camera stamps each image with its own counter. Every `clock_sync_period` seconds, between images, the gateway latches the counter `latch_samples` times, each between two readings of the host clock, keeps the latch with the shortest round trip, and fits a line over the last 10 pairs to follow the drift of the camera clock (`clock.py`). A camera without the latch nodes is stamped when the image reaches the host, with a warning at startup; that instant includes the exposure, readout and transfer.

| Module | Does |
|---|---|
| `camera.py` | `SpinnakerCamera`: connection, trigger, grab, clock mapping, color processing and encoding, the settings' getters and setters |
| `nodes.py` | typed access to the GenICam nodes; `StatusException` |
| `clock.py` | `ClockMapper`, `LatchSample` |
| `schedule.py` | `next_tick`, `normalize_delay`, `rebase_delay`, `sleep_until` |
| `service.py` | `CameraGateway`: the loop, the publishing, `GetConfig` and `SetConfig` |
| `main.py` | the startup: options, telemetry, the camera, then `run` |

## Options

`pris-camera-gateway [options.json]`, by default `/etc/pris-camera-gateway/options.json`. The fields are described in [`conf/options.proto`](src/pris_camera_gateway/conf/options.proto) and their defaults are in [`etc/conf/options.json`](etc/conf/options.json); `camera` holds:

- `id` and `ip`: the topics' id and the camera's persistent IP. A camera accepts one connection: a second gateway, or SpinView, fails with "already in use".
- `trigger_mode`: `FREE_RUN` or `SOFTWARE_SCHEDULED`.
- **Color.** The sensor gives a Bayer image (BayerRG8). Without `onboard_color_processing`, the gateway interpolates it with `algorithm`; with it, the camera does, sending three times the data. `use_turbojpeg` encodes JPEG with libjpeg-turbo, about three times faster than OpenCV.
- **Network.** `packet_size` as large as the network carries without fragmenting; `packet_delay` (8 ns ticks) leaves room for resends but lowers the maximum frame rate; `packet_resend`, `packet_resend_timeout` (ms) and `packet_resend_max_requests` (1 to 5). Teledyne FLIR's [Troubleshooting Image Consistency Errors](https://www.flir.com/support-center/iis/machine-vision/application-note/troubleshooting-image-consistency-errors/) covers lost and incomplete images.
- `reverse_x`: flips the image on the camera, before the region of interest.
- `initial_config`: a `CameraConfig` applied at startup as a `SetConfig` would; it must set `sampling.frequency`.
- `settle_time`, `clock_sync_period`, `latch_samples`: seconds before streaming, seconds between clock estimates, latches per estimate.

`LOG_LEVEL` sets the log level.

## Telemetry

From [opentelemetry-instrumentation-pris-wire](../../packages/opentelemetry-instrumentation-pris-wire/README.md): a PRODUCER span `publish CameraGateway.<id>.Frame` (and `.Timestamp`) per frame, a SERVER span per `GetConfig` and `SetConfig`, child of the caller's, and the RPC and messaging metrics.

## Running

The SDK must be downloaded by hand from Teledyne FLIR (a login is required), for Ubuntu 24.04: the SDK (`.tar.gz` with `.deb` files) and the Python wheel (`spinnaker_python-4.4.0.246-cp312-cp312-linux_x86_64.whl`). Put every `.deb` and the `.whl` in [`etc/spinnaker/`](etc/spinnaker/), which git ignores. The wheel is the project's `spinnaker-python` dependency (a path source in `pyproject.toml`), so `uv lock` and `uv sync` need it there too; it is built for CPython 3.12 only, hence `requires-python = "==3.12.*"`. Then `make image` in this folder, or `make image SERVICE=pris-camera-gateway` at the repository root. The image installs every SDK package but SpinView, accepting the EULA and declining analytics, and the build fails at the end if PySpin can't load its libraries. The `.deb` files stay in the layer that copies them (about 64 MB of the 1.1 GB image).

On a host next to the camera, with your options over the default ones:

```shell
docker run --rm --network host -v $PWD/options.json:/etc/pris-camera-gateway/options.json \
  luizcarloscf/pris-camera-gateway:0.1.0
```

GigE Vision discovery and streaming need the host network. On Kubernetes, [`k8s/pris-camera-gateway/`](../../k8s/pris-camera-gateway/) has a ConfigMap and a Deployment per camera (0 to 3, at `10.20.6.<n>`), on the host network, with the `Recreate` strategy, since a camera accepts one connection.

[`etc/examples/`](etc/examples/): `get_config.py`, `set_config.py`, `measure_sync.py` (the spread between cameras on `SOFTWARE_SCHEDULED`, from their `.Timestamp`) and `view_opencv.py` (a camera's frames through `SpinnakerCamera`, without a broker).

## Development

An independent project: its `pyproject.toml` takes the PRIS libraries from their git tags, and `uv.lock` pins them. PySpin needs the SDK's libraries, which only the image has: the tests replace it with [`tests/fake_pyspin.py`](tests/fake_pyspin.py), whose node maps record every write, and use a real broker at `WIRE_RABBITMQ_URI` (default `amqp://guest:guest@localhost:5672`). In this folder, `uv run pytest` and `uv run mypy src`; `make proto` regenerates `conf/options_pb2.py/.pyi`. The fake doesn't replace checks with a real camera.

## Hardware status

Not checked on a camera yet. To check with the Blackfly GigE `BFLY-PGE-09S2C` at `10.20.6.0`, with Docker:

- [ ] `FREE_RUN` and `SOFTWARE_SCHEDULED` at 10 Hz, every frame delivered;
- [ ] `GetConfig` and `SetConfig` (the delay) while streaming;
- [ ] the clock mapping: the latch nodes, and whether `GetTimeStamp()` marks the start of the exposure;
- [ ] `.Timestamp` matching `.Frame`'s `created_at`;
- [ ] a clean stop on `docker stop`;
- [ ] a stream of several hours (the old gateway restarted its stream every hour; this one releases every image after grabbing it);
- [ ] a Blackfly S, in both trigger modes.

Known from the old gateway: `SOFTWARE_SCHEDULED` with a manual shutter delivered almost no frames; keep the shutter automatic there until it is checked. On `SOFTWARE_SCHEDULED`, each frame must be exposed, read out and transferred before the next trigger, so it delivers every frame only up to about 18 Hz with 1400-byte packets and a `packet_delay` of 2500.
