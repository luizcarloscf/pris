# Services

The programs that run on the space. Each one is an independent project with its own image and Kubernetes manifests, and talks to the others only through the broker. In the order the data flows:

<div class="grid cards" markdown>

- **[pris-camera-gateway](pris-camera-gateway.md)**

    Connects to one camera, publishes its frames stamped with the capture instant, and serves its settings.

- **[pris-aruco-detector](pris-aruco-detector.md)**

    Finds the ArUco markers on every camera's frames and publishes their ids and corners, in pixels.

- **[pris-aruco-localization](pris-aruco-localization.md)**

    Combines the cameras that see a marker at the same instant and publishes its pose in the world.

- **[pris-frame-transformation](pris-frame-transformation.md)**

    Keeps the graph of the space's coordinate frames and gives the transformation between any two of them.

- **[pris-calibration-server](pris-calibration-server.md)**

    Serves the calibration of each camera: how it forms an image and where it is in the world.

- **[pris-broker-events](pris-broker-events.md)**

    Publishes who consumes every topic, and again whenever that changes: which cameras are online, who listens.

</div>
