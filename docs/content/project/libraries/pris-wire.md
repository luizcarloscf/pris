# pris-wire

Components of PRIS talk to each other through a [RabbitMQ](https://www.rabbitmq.com) broker. `pris_wire` is the Python client: components publish messages to topics, subscribe to the topics they need, and make requests that another component answers. It is built on [py-amqp](https://github.com/celery/py-amqp), and the message bodies are usually [pris-msgs](pris-msgs.md) messages.

!!! info "New to RabbitMQ?"

    These pages from the official documentation explain the model `pris_wire` uses:

    - [AMQP 0-9-1 concepts](https://www.rabbitmq.com/tutorials/amqp-concepts): exchanges, queues, bindings and routing keys;
    - [Topics tutorial](https://www.rabbitmq.com/tutorials/tutorial-five-python): routing by topic, with the `*` and `#` wildcards;
    - [RPC tutorial](https://www.rabbitmq.com/tutorials/tutorial-six-python): requests and replies with `reply_to` and `correlation_id`;
    - [Work queues tutorial](https://www.rabbitmq.com/tutorials/tutorial-two-python): several consumers sharing one queue;
    - [Consumer prefetch](https://www.rabbitmq.com/docs/consumer-prefetch), [acknowledgements](https://www.rabbitmq.com/docs/confirms) and [queue length limits](https://www.rabbitmq.com/docs/maxlength).

## How it maps to the broker

| `pris_wire` | On the broker |
|---|---|
| `Channel` | a connection, and the topic exchange `pris` it declares |
| `Subscription` | a queue; `subscribe(topic)` adds a binding from the exchange |
| `Message` | an AMQP message: a body and its properties (`reply_to`, `correlation_id`, expiration, headers) |
| a topic | the routing key, words separated by dots such as `CameraGateway.0.Frame` |
| `ServiceProvider` | a named queue per served topic, and the replies it publishes |

A message that matches no binding is dropped: the broker keeps nothing for topics nobody listens to.

## Publish and subscribe

Every example below runs as is, with a broker on `localhost` (`make broker-up` in this repository) and pris-wire and pris-msgs installed (see the [README](https://github.com/luizcarloscf/pris/tree/main/packages/pris-wire#readme)). Each part runs in a terminal of its own; start the one that listens first.

A subscriber receives the positions of every robot:

```python
from pris_msgs.common_pb2 import Position
from pris_wire.core import Channel, Subscription

channel = Channel("amqp://guest:guest@localhost:5672")
subscription = Subscription(channel)
subscription.subscribe("Robot.*.Position")             # * matches one word

while True:
    message = channel.consume()
    print(message.topic, message.unpack(Position).x)   # Robot.0.Position 1.5
```

A publisher sends the position of robot 0:

```python
from pris_msgs.common_pb2 import Position
from pris_wire.core import Channel, Message

channel = Channel("amqp://guest:guest@localhost:5672")
channel.publish(Message(content=Position(x=1.5)), topic="Robot.0.Position")
channel.close()
```

`consume` waits for the next message of any subscription of the channel; `consume_for`, `consume_until` and `consume_ready` wait less, or not at all, and return `None` or an empty list when nothing arrived.

## Requests and replies

A `ServiceProvider` calls a function for every request published to a topic and publishes its return value as the reply:

```python
from google.protobuf.wrappers_pb2 import FloatValue
from pris_msgs.common_pb2 import Position
from pris_wire.core import Channel
from pris_wire.rpc import ServiceProvider


def norm(position, context):
    return FloatValue(value=(position.x ** 2 + position.y ** 2) ** 0.5)


channel = Channel("amqp://guest:guest@localhost:5672")
provider = ServiceProvider(channel)
provider.delegate("Geometry.Norm", norm, request_type=Position, reply_type=FloatValue)
provider.run()                                          # serves until interrupted
```

The caller sets `reply_to` to its own subscription, where the reply arrives with the request's `correlation_id`:

```python
from google.protobuf.wrappers_pb2 import FloatValue
from pris_msgs.common_pb2 import Position
from pris_wire.core import Channel, Message, Subscription

channel = Channel("amqp://guest:guest@localhost:5672")
replies = Subscription(channel)
channel.publish(Message(content=Position(x=3, y=4), reply_to=replies), topic="Geometry.Norm")

reply = channel.consume(timeout=1.0)
print(reply.status.code, reply.unpack(FloatValue).value)   # StatusCode.OK 5.0
channel.close()
```

The reply's `status` says how the request went: `OK` with the function's result, a `Status` the function returned instead of a result (such as `Status(StatusCode.INVALID_ARGUMENT, "only 2D positions")`), `FAILED_PRECONDITION` for a request of the wrong type, `INTERNAL_ERROR` if the function raised, or `DEADLINE_EXCEEDED` for a request whose `timeout` passed.

## Sharing work between replicas

Consumers of one named queue split its messages, so replicas of a service share the load. With `manual_ack`, each message is settled with `ack` or `reject`, and `prefetch=1` gives the next message to whichever replica is free. Start this worker in two terminals:

```python
import time

from pris_wire.core import Channel, Subscription

channel = Channel("amqp://guest:guest@localhost:5672")
Subscription(channel, name="Jobs", prefetch=1, manual_ack=True)

while True:
    job = channel.consume()
    print(job.body)                                     # b'job 0', then b'job 2'
    time.sleep(1.0)                                     # the work
    channel.ack(job)                                    # done: the broker forgets it
```

Then send four jobs:

```python
from pris_wire.core import Channel, Message

channel = Channel("amqp://guest:guest@localhost:5672")
for n in range(4):
    channel.publish(Message(content="job {}".format(n).encode()), topic="Jobs")
channel.close()
```

Each worker gets two jobs: one prints `b'job 0'` and `b'job 2'`, the other `b'job 1'` and `b'job 3'`, since a worker gets the next job only after acknowledging the previous one.

`Subscription(arguments=...)` passes queue arguments to the broker, for example `{"x-max-length": 1, "x-overflow": "drop-head"}` to keep only the newest message.

## Logging

`Logger` prints colored lines, formatted with `str.format`. The `LOG_LEVEL` environment variable (`DEBUG`, `INFO`, ...) sets the level of every logger of the process:

```python
from pris_wire.core import Logger

log = Logger("MyService", Logger.INFO)
log.info("serving on '{}'", "Geometry.Norm")
```

## Reference

Installation, the modules, and development are in the package's [README](https://github.com/luizcarloscf/pris/tree/main/packages/pris-wire#readme).