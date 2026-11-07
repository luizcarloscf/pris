# Camera calibrations

Camera calibrations of each site, served by `pris-calibration-server`. One `pris.vision.CameraCalibration` in protobuf JSON per camera, in `<site>/<id>.json`, where `id` (inside the file) must equal the file name.

| Path | Site | Cameras |
|---|---|---|
| `labvisio/` | LabVISIO | 0–3, FLIR Blackfly BFLY-PGE-09S2C-CS at 1288×728 |

## Kubernetes

pris-calibration-server reads the calibrations of one site from the ConfigMap
`pris-calibration-server-calibrations`. Create or update it from the repository root:

```bash
kubectl -n pris create configmap pris-calibration-server-calibrations \
  --from-file=calibrations/labvisio/ --dry-run=client -o yaml | kubectl apply -f -
```
