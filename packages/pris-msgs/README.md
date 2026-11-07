# pris-msgs

The [Protocol Buffers](https://protobuf.dev/) schemas shared by every component of PRIS, the Python code generated from them, and helpers to load and save messages as JSON and to convert tensors, images and annotations to NumPy arrays. A high-level introduction is in the [documentation](../../docs/content/libraries/pris-msgs.md).

```shell
pip install "pris-msgs @ git+https://github.com/luizcarloscf/pris@pris-msgs-v1.0.0#subdirectory=packages/pris-msgs"
```

| Extra | Needed by |
|---|---|
| `numpy` | `pris_msgs.utils.tensor`, `pris_msgs.utils.annotation` |
| `opencv` | `pris_msgs.utils.image` |
| `turbojpeg` | `pris_msgs.utils.image` with `turbojpeg=True`; also needs the system `libturbojpeg` |

## Schemas

| File | Package | Contents |
|---|---|---|
| `common.proto` | `pris.common` | positions, poses, speeds, tensors, sampling settings, consumer lists |
| `image.proto` | `pris.vision` | images, image settings, object and keypoint annotations |
| `camera.proto` | `pris.vision` | camera configuration, calibrations, frame transformations |
| `robot.proto` | `pris.robot` | robot configuration and tasks, range scans |
| `power.proto` | `pris.common` | battery state (voltage, charge, autonomy) |

Each `.proto` file in `src/pris_msgs/` becomes a module, `pris_msgs.<name>_pb2`. The `.proto` sources ship in the wheel next to the generated code and import each other as `pris_msgs/<name>.proto`.

## Helpers

| Module | Does |
|---|---|
| `pris_msgs.utils.io` | `load` and `save` any message as a JSON file |
| `pris_msgs.utils.tensor` | `to_array` and `to_tensor`: `pris.common.Tensor` ↔ NumPy array |
| `pris_msgs.utils.image` | `to_array` and `to_image`: `pris.vision.Image` ↔ NumPy array of BGR or gray pixels |
| `pris_msgs.utils.annotation` | `to_array` and `to_annotation`: `ObjectAnnotation` keypoints ↔ NumPy arrays, in the order of a list of `HumanKeypoints` ids |
| `pris_msgs.utils.build` | compiles your own `.proto` files that import the shared ones |

* `HumanKeypoints` 0–20 are the original values and never change. 21–27 (pelvis and feet), 100–167 (`FACE_0`…`FACE_67`, iBUG 300-W), 200–220 and 300–320 (left and right hand: `ROOT`, then `THUMB`, `INDEX`, `MIDDLE`, `RING`, `PINKY`, `_1` at the base to `_4` at the tip) were added for the Halpe-26 and COCO-WholeBody-133 models.

To compile a `.proto` that imports `pris_msgs/common.proto`:

```shell
PROTOC="python -m grpc_tools.protoc" python -m pris_msgs.utils.build --proto_path src --out src src/my_service/my.proto
```

## Development

From the repository root:

```shell
make proto # regenerate src/pris_msgs/*_pb2.py/.pyi after editing a .proto
make test  # run unit testing
make lint  # run linter
```

`make proto` runs `make -C packages/pris-msgs proto`, which compiles the schemas with the protoc bundled in `grpcio-tools`, a dev dependency of the workspace. Commit the regenerated code with the `.proto` change. To test another Python version: `uv run --isolated --python 3.10 pytest packages/pris-msgs`. `grpcio-tools==1.85.1` (dev) bundles protoc 35.1, the runtime's lower bound. Before moving it, check `python -m grpc_tools.protoc --version`.
