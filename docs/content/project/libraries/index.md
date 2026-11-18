# Libraries

The Python libraries every component of PRIS is built on. Each one is an independent package, released by git tag, with its own README for the reference.

<div class="grid cards" markdown>

- **[pris-msgs](pris-msgs.md)**

    The Protocol Buffers schemas every component may exchange, and their generated Python code.

- **[pris-wire](pris-wire.md)**

    The RabbitMQ client: publish to topics, subscribe to them, and make requests that another component answers.

- **[OpenTelemetry instrumentation](opentelemetry-instrumentation-pris-wire.md)**

    Traces and metrics for every component, with no change to its code, carried inside each message.

- **[pris-common](pris-common.md)**

    What several services need beyond messaging: the camera calibrations and frame transformations they fetch at startup.

</div>
