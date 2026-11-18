# Kubernetes

The `k8s/` folder has the manifests, one folder per component, all in the namespace `pris`:

- `k8s/common/`: what any site needs, the namespace, RabbitMQ, Jaeger and the OpenTelemetry Collector;
- `k8s/labvisio/`: the services of the LabVISIO, each with its Deployment and the ConfigMap of its options, and one gateway per camera. Another site copies this folder and edits its options and cameras.

!!! warning "Not yet tested on a cluster"

    The manifests are checked with `kubectl apply --dry-run=client`; the services were run with Docker on one host.

!!! info "New to Kubernetes?"

    - [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/): how a component's pods are kept running;
    - [Services](https://kubernetes.io/docs/concepts/services-networking/service/): the names, such as `rabbitmq.pris`, and the node ports;
    - [ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/): the services' options, the broker and collector configuration, and the calibrations;
    - [Namespaces](https://kubernetes.io/docs/concepts/overview/working-with-objects/namespaces/).

## Components

| Folder | Image | Reached at |
|---|---|---|
| `common/rabbitmq/` | `rabbitmq:4.3.6-management`, configured by `rabbitmq/conf/` | `rabbitmq.pris`: AMQP 5672, management 80. Node ports: 31000 (AMQP), 31080 (management), 31001 (MQTT), 31002 (web MQTT) |
| `common/jaeger/` | `jaegertracing/jaeger:2.22.0` | `jaeger.pris:4317` (OTLP gRPC); the UI on node port 31686 |
| `common/otel-collector/` | `otel/opentelemetry-collector:0.163.2` | `otel-collector.pris`: 4317 (OTLP gRPC), 4318 (OTLP HTTP) |
| `labvisio/pris-aruco-detector/` | `luizcarloscf/pris-aruco-detector:0.1.0` | `ArUco.<id>.Detection` from `CameraGateway.<id>.Frame`; replicas split the frames |
| `labvisio/pris-aruco-localization/` | `luizcarloscf/pris-aruco-localization:0.1.0` | `ArUco.FrameTransformations` from the detections; one instance (`Recreate`) |
| `labvisio/pris-broker-events/` | `luizcarloscf/pris-broker-events:0.1.0` | publishes `BrokerEvents.Consumers`; one instance (`Recreate`), since replicas would split its events |
| `labvisio/pris-calibration-server/` | `luizcarloscf/pris-calibration-server:0.1.0` | serves `CalibrationServer.GetCalibration` |
| `labvisio/pris-camera-gateway/` | `luizcarloscf/pris-camera-gateway:0.1.0` | publishes `CameraGateway.<n>.Frame`, serves `.GetConfig`/`.SetConfig`; one ConfigMap and Deployment per camera (0–3), host network, `Recreate` |
| `labvisio/pris-frame-transformation/` | `luizcarloscf/pris-frame-transformation:0.1.0` | publishes `FrameTransformation.<ids>`, serves `FrameTransformation.GetTransformation`; one instance (`Recreate`) |

The services' default options already use these names: the broker at `amqp://guest:guest@rabbitmq.pris`, and telemetry sent to `http://otel-collector.pris:4318`.

## Deploying

The images of the services are built locally and never pushed: build them with `make image SERVICE=<service>` and load them into the cluster (on minikube, `minikube image load luizcarloscf/<service>:<version>`). Their Deployments use `imagePullPolicy: IfNotPresent`, so the loaded image is used. Then apply the common manifests, then the site's:

```shell
kubectl apply -f k8s/common/namespace.yaml
kubectl -n pris create configmap rabbitmq --from-file=k8s/common/rabbitmq/conf/ \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f k8s/common/rabbitmq/ -f k8s/common/jaeger/ -f k8s/common/otel-collector/
kubectl -n pris create configmap pris-calibration-server-calibrations \
  --from-file=calibrations/labvisio/ --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -R -f k8s/labvisio/
```

## The broker

`k8s/common/rabbitmq/conf/` holds RabbitMQ's plugins (`enabled_plugins`), configuration (`rabbitmq.conf`) and definitions (`definitions.json`), loaded at startup; the ConfigMap `rabbitmq` is created from that folder, as above. The local broker of `make broker-up` mounts the same folder, so local and cluster brokers behave alike:

- **Plugins:** management, MQTT and web MQTT (MQTT messages go to the `pris` exchange), top, and the event exchange.
- **Definitions:** the `guest` user, allowed from other hosts; the `pris` topic exchange; and every broker event (`amq.rabbitmq.event`, from the event exchange plugin) forwarded into `pris`, so that [pris-broker-events](../services/pris-broker-events.md) can follow the `binding.*` events to keep its list of consumers.
- **Policy:** every queue holds at most 64 messages and 10 MiB, so a consumer that stops doesn't fill the broker's memory.

## Telemetry

The services send traces and metrics over OTLP/HTTP to `otel-collector`, which forwards the traces to Jaeger and prints the metrics, as there is no metrics backend yet. Open the traces at Jaeger's node port 31686.

## Options and calibrations

Each service folder of the site has a `configmap.yaml` with the service's `options.json`, mounted over its image's `/etc/<service>/options.json`; it starts as a copy of `services/<service>/etc/conf/options.json`. A service reads its options once, so after editing one, apply it and restart the service: `kubectl apply -f k8s/labvisio/<service>/configmap.yaml` and `kubectl -n pris rollout restart deployment/<service>`. [pris-frame-transformation](../services/pris-frame-transformation.md) and [pris-aruco-localization](../services/pris-aruco-localization.md) should list the same `camera_ids`.

[pris-calibration-server](../services/pris-calibration-server.md) reads the calibrations of one site from the ConfigMap `pris-calibration-server-calibrations`, mounted at `/etc/calibrations`; the command above creates or updates it from `calibrations/<site>/`. The server reads them once, so restart it after a change: `kubectl -n pris rollout restart deployment/pris-calibration-server`.
