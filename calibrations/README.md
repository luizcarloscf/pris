# Camera calibrations

Camera calibrations of each site, served by `pris-calibration-server`. One `pris.vision.CameraCalibration` in protobuf JSON per camera, in `<site>/<id>.json`, where `id` (inside the file) must equal the file name.

| Path | Site | Cameras |
|---|---|---|
| `labvisio/` | LabVISIO | 0–3, FLIR Blackfly BFLY-PGE-09S2C-CS at 1288×728 |

**Documentation:**
* [pris-calibration-server](../docs/content/services/pris-calibration-server.md#calibration-files)
* [Kubernetes](../docs/content/deployment/kubernetes.md#calibrations)