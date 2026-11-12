# pris-camera-gateway

Every other service starts from the cameras' frames. `pris-camera-gateway` connects to one [Blackfly GigE](https://www.flir.com/products/blackfly-gige/) or Blackfly S GigE camera through Teledyne FLIR's Spinnaker SDK, publishes its frames on `CameraGateway.<id>.Frame`, each stamped with its capture instant, and serves requests to read and change the camera's settings. One gateway runs per camera, on a host next to it. It can trigger the camera itself, at instants of the host clock, so that several cameras capture the same instant, which is what the localizations need to combine them.

!!! info "New to GigE cameras?"

    - [Spinnaker SDK](https://www.flir.com/products/spinnaker-sdk/): Teledyne FLIR's SDK, and the download the image needs;
    - [Understanding color interpolation](https://www.flir.eu/support-center/iis/machine-vision/application-note/understanding-color-interpolation/): the Bayer image and how it becomes color;
    - [Troubleshooting image consistency errors](https://www.flir.com/support-center/iis/machine-vision/application-note/troubleshooting-image-consistency-errors/): lost and incomplete images, and the network settings behind them.

## Reading a camera

The image needs the SDK, downloaded by hand (see the README). With it built, start the gateway next to the camera, on the host network, with options for the local broker:

```shell
docker run --rm --network host -v $PWD/options.json:/etc/pris-camera-gateway/options.json \
  luizcarloscf/pris-camera-gateway:0.1.0
```

In another terminal, read its settings and its frames:

```python
from pris_msgs.camera_pb2 import CameraConfig, CameraConfigFields
from pris_msgs.common_pb2 import FieldSelector
from pris_msgs.image_pb2 import Image
from pris_wire.core import Channel, Message, Subscription

channel = Channel("amqp://guest:guest@localhost:5672")
replies = Subscription(channel)
selector = FieldSelector(fields=[CameraConfigFields.SAMPLING_SETTINGS])
channel.publish(Message(content=selector, reply_to=replies), topic="CameraGateway.0.GetConfig")
print(channel.consume(timeout=3.0).unpack(CameraConfig).sampling)  # frequency { value: 10 }

Subscription(channel).subscribe("CameraGateway.0.Frame")
frame = channel.consume(timeout=3.0)
print(frame.created_at, len(frame.unpack(Image).data))  # the capture instant, the JPEG's size
channel.close()
```

On `FREE_RUN` the camera triggers itself at its frame rate; on `SOFTWARE_SCHEDULED` the gateway triggers it at `k × period + delay` of the host clock, so cameras on hosts with synced clocks capture together, and a `SetConfig` of `sampling.delay` shifts one of them inside the period.

## Reference

The settings, the trigger modes, the capture instants, the options, the image with the SDK, Kubernetes and the hardware still to check are in the service's [README](https://github.com/luizcarloscf/pris/tree/main/services/pris-camera-gateway#readme).
