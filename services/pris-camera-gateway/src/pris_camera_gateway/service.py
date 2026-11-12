"""The gateway: one loop that triggers, grabs and publishes the frames and serves the requests."""

from __future__ import annotations

import time

from google.protobuf.empty_pb2 import Empty
from google.protobuf.timestamp_pb2 import Timestamp
from pris_msgs.camera_pb2 import CameraConfig, CameraConfigFields
from pris_msgs.common_pb2 import FieldSelector
from pris_wire.core import Channel, Logger, Message, Status, StatusCode
from pris_wire.rpc import LogInterceptor, ServiceProvider
from pris_wire.rpc.context import Context

from pris_camera_gateway.camera import Capture, SpinnakerCamera
from pris_camera_gateway.conf.options_pb2 import CameraOptions
from pris_camera_gateway.nodes import StatusException
from pris_camera_gateway.schedule import next_tick, sleep_until


class CameraGateway(object):
    """Publishes the frames of one camera and serves requests to read and change its settings.

    Everything runs on one thread. On FREE_RUN each turn waits for the camera's next image,
    publishes it, then serves the requests that arrived meanwhile. On SOFTWARE_SCHEDULED it
    serves requests until just before the next instant `k * period + delay`, triggers the
    camera, then grabs and publishes the image.
    """

    log = Logger("CameraGateway")

    # * CameraConfig group -> setting -> the camera's get_<method> / set_<method>, in the order
    # * they're set; settings not listed are UNIMPLEMENTED
    settings = {
        "image": {"color_space": "color_space", "format": "format", "region": "region"},
        "sampling": {"frequency": "sampling_rate", "delay": "delay"},
        "camera": {name: name for name in (
            "brightness", "gain", "shutter", "white_balance_rv", "white_balance_bu")},
    }
    groups = {
        CameraConfigFields.IMAGE_SETTINGS: "image",
        CameraConfigFields.SAMPLING_SETTINGS: "sampling",
        CameraConfigFields.CAMERA_SETTINGS: "camera",
    }

    def __init__(
        self,
        channel: Channel,
        camera: SpinnakerCamera,
        options: CameraOptions,
        prefix: str = "CameraGateway",
        grab_timeout_ms: int = 3000,
        wake_ns: int = 2_000_000,
    ) -> None:
        """Serve `<prefix>.<id>.GetConfig` and `.SetConfig` on `channel`.

        Args:
            channel: the channel that publishes the frames and serves the requests.
            camera: the connected camera.
            options: the camera's options.
            prefix: the topics' prefix.
            grab_timeout_ms: the most milliseconds to wait for an image on FREE_RUN.
            wake_ns: how long before a trigger instant the loop stops serving requests.
        """
        self.channel = channel
        self.camera = camera
        self.options = options
        self.grab_timeout_ms = grab_timeout_ms
        self.wake_ns = wake_ns
        self.frame_topic = f"{prefix}.{options.id}.Frame"
        self.timestamp_topic = f"{prefix}.{options.id}.Timestamp"
        self.provider = ServiceProvider(channel)
        self.provider.add_interceptor(LogInterceptor())
        self.provider.delegate(f"{prefix}.{options.id}.GetConfig", self.get_config,
                               FieldSelector, CameraConfig)
        self.provider.delegate(f"{prefix}.{options.id}.SetConfig", self.set_config,
                               CameraConfig, Empty)
        self.next_sync = time.time() + options.clock_sync_period

    def run(self) -> None:
        """Apply `initial_config`, start streaming, and loop until the process stops; the
        camera is released on the way out."""
        try:
            status = self.set_config(self.options.initial_config)
            if isinstance(status, Status):
                self.log.critical("Initial config: {}", status.why)
            time.sleep(self.options.settle_time)
            self.camera.start()
            self.log.info("Publishing {}", self.frame_topic)
            while True:
                self.step()
        finally:
            self.camera.disconnect()

    def step(self) -> Capture | None:
        """Grab one image, publish it, and serve the requests that arrived.

        Returns:
            The capture published, or None when no image could be published.
        """
        if time.time() >= self.next_sync:
            self.camera.sync_clock()
            self.next_sync = time.time() + self.options.clock_sync_period
        if self.camera.scheduled:
            sleep_until(self.serve_until_tick())
            self.camera.trigger()
            # * the image must arrive before the next tick
            capture = self.camera.grab(max(1, self.camera.period_ns // 1_000_000))
        else:
            capture = self.camera.grab(self.grab_timeout_ms)
        if capture is not None:
            self.publish(capture)
        for message in self.channel.consume_ready():
            self.serve(message)
        return capture

    def serve_until_tick(self) -> int:
        """Serve requests until `wake_ns` before the next trigger instant, which a request may
        move, and return that instant."""
        while True:
            tick = next_tick(time.time_ns(), self.camera.period_ns, self.camera.delay_ns)
            message = self.channel.consume_until((tick - self.wake_ns) / 1e9)
            if message is None:
                return tick
            self.serve(message)

    def serve(self, message: Message) -> None:
        if self.provider.should_serve(message):
            self.provider.serve(message)

    def publish(self, capture: Capture) -> None:
        """Publish the frame and its capture instant, both with that instant as created_at."""
        frame = Message(content=capture.image)
        frame.created_at = capture.timestamp_ns / 1e9
        self.channel.publish(frame, topic=self.frame_topic)
        stamp = Timestamp()
        stamp.FromNanoseconds(capture.timestamp_ns)
        timestamp = Message(content=stamp)
        timestamp.created_at = frame.created_at
        self.channel.publish(timestamp, topic=self.timestamp_topic)

    def get_config(self, selector: FieldSelector, context: Context | None = None) -> CameraConfig:
        """Return the settings of the groups `selector` asks for (`ALL` for every group); a
        setting the camera can't read is left out."""
        fields = set(selector.fields)
        if CameraConfigFields.ALL in fields:
            fields.update(self.groups)
        config = CameraConfig()
        for field, group in self.groups.items():
            if field not in fields:
                continue
            for name, method in self.settings[group].items():
                try:
                    value = getattr(self.camera, "get_" + method)()
                except StatusException:
                    continue
                getattr(getattr(config, group), name).CopyFrom(value)
        return config

    def set_config(self, config: CameraConfig, context: Context | None = None) -> Empty | Status:
        """Apply every setting present in `config`; the others stay as they are.

        Returns:
            Empty, or the Status of the first setting refused; UNIMPLEMENTED, before anything is
            applied, for a setting this camera doesn't support.
        """
        for group, settings in self.settings.items():
            for field, _ in getattr(config, group).ListFields():
                if field.name not in settings:
                    return Status(StatusCode.UNIMPLEMENTED, f"'{field.name}' is not supported")
        try:
            for group, settings in self.settings.items():
                message = getattr(config, group)
                for name, method in settings.items():
                    if message.HasField(name):
                        getattr(self.camera, "set_" + method)(getattr(message, name))
        except StatusException as ex:
            return ex.status
        return Empty()
