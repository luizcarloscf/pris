# Programmable Intelligent Space (PRIS)

An environment instrumented with sensors, mainly calibrated cameras, whose data feeds independent services that locate people and robots, understand what happens in the space, and act on it. Computer vision is the main source of information, but the same infrastructure serves any sensor or actuator.

Every component talks to the others through a message broker ([RabbitMQ](https://www.rabbitmq.com)), exchanging [Protocol Buffers](https://protobuf.dev) messages over AMQP:

- **gateways** publish what the sensors capture (for example, camera frames) and accept configuration requests;
- **services** subscribe to that data, process it, and publish their results or answer requests;
- **robots** join through a ROS 2 bridge.

Components only share topic names and message types, so each one can be added, replaced, or scaled without changing the others. Every component is a container image, with Kubernetes manifests to run them together.

## Where to start

<div class="grid cards" markdown>

- **[Status](project/status.md)**

    What is done, what is still to check, and what is planned.

</div>
