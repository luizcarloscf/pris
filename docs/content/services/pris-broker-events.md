# pris-broker-events

Which cameras are online? Does anyone serve a topic, or listen to it? `pris-broker-events` answers by publishing, on `BrokerEvents.Consumers`, the queues that consume every topic, and again whenever that changes. It builds the list from the broker itself: its bindings at startup, then its binding events.

!!! info "New to RabbitMQ's events?"

    - [Event exchange plugin](https://www.rabbitmq.com/docs/event-exchange): the broker publishes its own events, such as `binding.created`, as messages;
    - [Management plugin](https://www.rabbitmq.com/docs/management): the HTTP API that lists the bindings at startup.

## Finding the cameras online

The examples run as is, with the local broker of `make broker-up`, which has the plugins the service needs. Start the service from the repository root:

```shell
cat > /tmp/options.json <<END
{"broker_uri": "amqp://guest:guest@localhost:5672",
 "broker_management_api": {"uri": "http://guest:guest@localhost:15672", "timeout": 5.0}}
END
uv run --project services/pris-broker-events pris-broker-events /tmp/options.json
```

In another terminal, stand in for the gateways of cameras 0 and 2, which serve `CameraGateway.<id>.GetConfig`:

```python
from pris_wire.core import Channel, Subscription

channel = Channel("amqp://guest:guest@localhost:5672")
Subscription(channel, name="CameraGateway.0.GetConfig")  # as camera 0's gateway does
Subscription(channel, name="CameraGateway.2.GetConfig")
channel.consume()                                       # stays until interrupted
```

In a third, find the cameras from the topics their gateways serve:

```python
import re

from pris_msgs.common_pb2 import ConsumerList
from pris_wire.core import Channel, Subscription

channel = Channel("amqp://guest:guest@localhost:5672")
Subscription(channel).subscribe("BrokerEvents.Consumers")

consumers = channel.consume(timeout=5.0).unpack(ConsumerList)
cameras = sorted(
    int(match.group(1))
    for topic in consumers.info
    if (match := re.fullmatch(r"CameraGateway\.(\d+)\.GetConfig", topic))
)
print(cameras)                                          # [0, 2]
channel.close()
```

A new subscriber gets the list right after subscribing, since its own subscription changes it. The keys are bindings as subscribed, so they may be patterns such as `CameraGateway.*.Frame`.

## Reference

How the list is built, the broker it needs, the options, telemetry and development are in the service's [README](https://github.com/luizcarloscf/pris/tree/main/services/pris-broker-events#readme).
