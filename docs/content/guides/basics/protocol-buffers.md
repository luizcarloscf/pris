# Protocol Buffers

To save data in a file or send it to another program, it must become a sequence of **bytes**, and the other side must turn the bytes back into the same data. That is **serializing** and **deserializing**, and both sides must agree on the format, or the bytes mean nothing. [Protocol Buffers](https://protobuf.dev/overview/), often "protobuf", write that agreement down as a **schema**, a `.proto` file describing each kind of message and its fields. From the schema, a compiler writes the code that builds, serializes and reads the messages, in Python, C++ or a dozen other languages, so programs in different languages understand each other. The bytes are compact, and the schema can grow without breaking programs that use an older version. This guide uses it from Python on a fresh Ubuntu install, after [Python](python.md); [Messaging](messaging.md) shows how to send the bytes between programs.

!!! info "To learn more"

    - [Language guide (proto3)](https://protobuf.dev/programming-guides/proto3/): every type and rule of a `.proto` file;
    - [Python tutorial](https://protobuf.dev/getting-started/pythontutorial/) and [generated code](https://protobuf.dev/reference/python/python-generated/): the classes the compiler writes;
    - [Dos and don'ts](https://protobuf.dev/programming-guides/dos-donts/): how to change a schema safely;
    - [Encoding](https://protobuf.dev/programming-guides/encoding/) and [JSON mapping](https://protobuf.dev/programming-guides/json/);
    - [Well-known types](https://protobuf.dev/reference/protobuf/google.protobuf/), such as `Timestamp`.

## Setting up

```shell
mkdir messages && cd messages
uv init --bare --python 3.12
uv add protobuf                    # the library the generated code uses
uv add --dev grpcio-tools          # the compiler, protoc, as a Python package
```

The compiler is called **protoc**. [`grpcio-tools`](https://pypi.org/project/grpcio-tools/) ships one as a Python package, whose version matches the `protobuf` library. Ubuntu's `protobuf-compiler` package works too, but it is much older than the library uv installs, and the code one compiler writes is only guaranteed to work with a library at least as new.

## A schema

Save as `sensor.proto`, a temperature reading from a sensor:

```protobuf
syntax = "proto3";

package demo;

import "google/protobuf/timestamp.proto";

enum Unit {
  UNIT_UNSPECIFIED = 0;
  CELSIUS = 1;
  FAHRENHEIT = 2;
}

message Reading {
  string sensor = 1;
  double value = 2;
  Unit unit = 3;
  google.protobuf.Timestamp time = 4;
  repeated string tags = 5;
}

message Readings {
  repeated Reading readings = 1;
}
```

- `syntax = "proto3"` says which version of the language this is.
- A **message** is a kind of data with named, typed **fields**, like a dataclass (see [Python](python.md#a-module)): `string` for text, `double` for a decimal number, `int64` for a whole number, `bool`, `bytes`, an enum, or another message.
- Each field has a **number**, `= 1`, `= 2`. The bytes carry these numbers, not the names: that is part of why they are small. A number identifies its field forever; the name is only for people and code.
- `repeated` makes a field a list. `Readings` holds a list of `Reading`, so many readings travel in one message.
- An **enum** gives names to a few whole numbers, so a field can only take those values. Its first value must be 0, which is also the default, so it is usually an "unspecified" value.
- `google.protobuf.Timestamp` is a **well-known type**, a message that comes with protobuf: an instant, as seconds and nanoseconds since 1970 UTC. `import` makes it available.
- `package demo` groups these names, so they don't clash with another schema's `Reading`.

## Generating the code

```shell
uv run python -m grpc_tools.protoc -I . --python_out=. --pyi_out=. sensor.proto
```

This runs the compiler on `sensor.proto`. `-I .` says to look for `.proto` files, and their imports, in the current folder. `--python_out=.` writes `sensor_pb2.py`, with a Python class for each message; `--pyi_out=.` writes `sensor_pb2.pyi`, the classes' type hints, which editors and mypy read. Never edit these files: change the `.proto` and run the command again.

## Writing and reading

Save as `write.py`:

```python
import json

from sensor_pb2 import CELSIUS, Reading

reading = Reading(sensor="lab", value=22.5, unit=CELSIUS, tags=["indoor"])
reading.time.GetCurrentTime()
reading.tags.append("floor-1")

data = reading.SerializeToString()
print(len(data), "bytes")
as_json = {"sensor": "lab", "value": 22.5, "unit": "CELSIUS", "tags": ["indoor", "floor-1"],
           "time": reading.time.ToJsonString()}
print(len(json.dumps(as_json)), "bytes as JSON")

with open("reading.bin", "wb") as file:
    file.write(data)
```

and as `read.py`:

```python
from google.protobuf.json_format import MessageToJson

from sensor_pb2 import Reading, Unit

with open("reading.bin", "rb") as file:
    reading = Reading.FromString(file.read())

print(reading.sensor, reading.value, Unit.Name(reading.unit), list(reading.tags))
print(reading.time.ToDatetime())
print(MessageToJson(reading))
```

```shell
uv run write.py                    # about 46 bytes, then 121 bytes as JSON
uv run read.py                     # lab 22.5 CELSIUS ['indoor', 'floor-1'], the time, the JSON
```

- `Reading(...)` builds a message, like any Python class. Fields can also be set later, as `reading.tags.append(...)` does, and a message field such as `time` is filled through its own methods: `GetCurrentTime()` sets it to now.
- `SerializeToString()` turns the message into bytes (despite its name, it gives `bytes`, not text). `Reading.FromString(...)` builds a message back from bytes. The bytes are what you write to a file, as here, or send through a network.
- `open("reading.bin", "wb")` opens a file to **w**rite **b**ytes; `"rb"` to read them; `with` closes the file at the end.
- The same reading takes about 46 bytes against 121 as JSON (a byte more or less, with the timestamp). The difference grows with numbers and lists.
- `MessageToJson`, from `google.protobuf.json_format`, shows a message as JSON, and `Parse` reads one from JSON: handy to look at messages or to write them by hand.
- `Unit.Name(...)` turns an enum's number into its name. `ToDatetime()` turns a `Timestamp` into a Python date and time, in UTC; `ToDatetime(tzinfo=datetime.timezone.utc)` also attaches the time zone.

## Defaults

A field that was never set reads as its **default**: `0`, `""`, `False`, an empty list, the enum's 0. Defaults aren't written to the bytes, so an empty message takes no bytes at all:

```python
from sensor_pb2 import Reading

empty = Reading()
print(repr(empty.sensor), empty.value, empty.unit, len(empty.tags))   # '' 0.0 0 0
print(empty.HasField("time"))                                       # False
print(len(empty.SerializeToString()))                               # 0
```

The catch: a `value` of 0.0 can't be told apart from no value at all. A message field, such as `time`, can: `HasField("time")` says whether it was set. For a number where "missing" matters, declare it `optional double value = 2;` and `HasField("value")` works for it too.

Fields are typed: `Reading(value="hot")` stops with a `TypeError` instead of sending the wrong kind of data.

## Changing a schema

Programs are rarely all updated at once: for a while, some will use the old schema and some the new one. A schema must change in ways both understand. Adding a field is safe. Add `double humidity = 6;` to `Reading` in a new version of `sensor.proto`, and:

- new code reading old bytes sees `humidity` as 0, its default;
- old code reading new bytes reads the fields it knows, and keeps the `humidity` it doesn't understand: if it writes the message on, the field is still there for newer code.

The rules that keep it so:

| Change | Safe? |
|---|---|
| add a field, with a new number | yes |
| rename a field or a message | yes, for the bytes; the code that uses the name changes |
| remove a field | yes, if you `reserve` its number and name, so nobody reuses them: `reserved 6; reserved "humidity";` |
| change a field's number | no: it is another field to every program |
| reuse a removed field's number | no: old programs read the new data as the old field |
| change a field's type | no, except between a few compatible types: see the language guide |

## Common mistakes

| Symptom | Likely cause |
|---|---|
| `ModuleNotFoundError: No module named 'sensor_pb2'` | the code wasn't generated, or was generated in another folder |
| `VersionError: Detected incompatible Protobuf Gencode/Runtime versions` | the code was generated by a compiler newer than the `protobuf` library: generate it with the `grpcio-tools` of the same project |
| a field always reads 0 or empty | the sender and the receiver use different schemas, or different numbers for that field |
| `DecodeError` | the bytes aren't that message: another type, or cut short on the way |
| a removed field comes back with nonsense | its number was reused for another field |

## What you learned

- Serializing turns data into bytes and back; a `.proto` schema is the agreement on how.
- Messages have typed, numbered fields; the numbers, not the names, go in the bytes.
- protoc generates the code; never edit it.
- Unset fields read as defaults and take no space; `optional` and `HasField` tell "unset" apart.
- Add fields freely; never change or reuse a field's number.
