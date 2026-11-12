# pris-calibration-server

Every camera of a site has a calibration: how it forms an image (intrinsics and distortion) and where it is in the world (extrinsics). `pris-calibration-server` loads them from one file per camera at startup and serves them on `CalibrationServer.GetCalibration`, so services that turn pixels into positions ask it for their cameras instead of reading files.

!!! info "New to camera calibration?"

    OpenCV's documentation explains what a calibration holds:

    - [Camera calibration tutorial](https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html): the camera matrix, distortion coefficients, and how they are estimated;
    - [Camera calibration and 3D reconstruction](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html): the pinhole model the intrinsics and extrinsics follow.

## Where it fits

```mermaid
flowchart LR
  files[("calibrations/#lt;site#gt;/#lt;id#gt;.json")] -->|"at startup"| server("pris-calibration-server")
  localization("pris-aruco-localization") -.->|"CalibrationServer.GetCalibration"| server
  frames("pris-frame-transformation") -.->|"CalibrationServer.GetCalibration"| server
```

## Serving the calibrations

The calibrations of each site are kept in the repository, in `calibrations/<site>/`, one `<id>.json` per camera. With a broker on `localhost` (`make broker-up` in this repository), serve those of the LabVISIO from the repository root:

```shell
cat > /tmp/options.json <<END
{"broker_uri": "amqp://guest:guest@localhost:5672", "calibrations_path": "calibrations/labvisio"}
END
uv run --project services/pris-calibration-server pris-calibration-server /tmp/options.json
```

In another terminal, a service fetches the calibrations of its cameras with [pris-common](../libraries/pris-common.md):

```python
from pris_wire.core import Channel
from pris_common.calibrations import fetch_calibrations

channel = Channel("amqp://guest:guest@localhost:5672")
calibrations = fetch_calibrations(channel, [0, 1, 2, 3])
for id, calibration in calibrations.items():
    print(id, calibration.resolution.width, calibration.resolution.height)   # 0 1288 728 ...
channel.close()
```

An unknown camera gets a `NOT_FOUND` reply. The server refuses to start on a bad calibration file, so a mistake stops the deployment instead of being served, and it reads the files once: a new calibration needs a restart.

## Reference

The request, the calibration files and their checks, the options, telemetry and development are in the service's [README](https://github.com/luizcarloscf/pris/tree/main/services/pris-calibration-server#readme).
