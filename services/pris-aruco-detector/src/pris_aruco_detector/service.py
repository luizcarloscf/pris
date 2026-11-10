"""The service: detect the markers on the newest frame of each camera and publish them."""

from __future__ import annotations

import re
from collections.abc import Iterable

import cv2
from opentelemetry import trace
from opentelemetry.instrumentation.pris_wire import extract
from opentelemetry.trace import SpanKind, StatusCode
from pris_msgs.image_pb2 import Image, ObjectAnnotations
from pris_wire.core import Channel, Logger, Message, Subscription

from pris_aruco_detector.detector import MarkerDetector


class ArucoDetectorService(object):
    """Publishes the markers of each camera's frames on its detection topic."""

    log = Logger("ArucoDetector")

    def __init__(
        self,
        channel: Channel,
        detector: MarkerDetector,
        camera_ids: Iterable[int] = (),
        queue_name: str = "ArUco.Detector",
        frame_topic: str = "CameraGateway.{}.Frame",
        detection_topic: str = "ArUco.{}.Detection",
        exchange: str = "pris",
    ) -> None:
        """Subscribe to the frames on a shared queue: replicas with the same name split them.

        Args:
            channel: the channel that consumes the frames and publishes the detections.
            detector: the marker detector.
            camera_ids: the cameras whose frames are processed; empty means every camera.
            queue_name: the shared queue.
            frame_topic: the frames' topic, with `{}` for the camera id.
            detection_topic: the detections' topic, with `{}` for the camera id.
            exchange: the exchange of the frames, for the spans.
        """
        self.channel = channel
        self.detector = detector
        self.frame_topic = frame_topic
        self.detection_topic = detection_topic
        self.exchange = exchange
        self.subscription = Subscription(channel, name=queue_name)
        topics = [frame_topic.format(id) for id in camera_ids] or [frame_topic.format("*")]
        for topic in topics:
            self.subscription.subscribe(topic)
        self.log.info("Subscribed to {} on queue '{}'", topics, self.subscription.name)

    def run(self) -> None:
        """Run `step` until the process stops."""
        while True:
            self.step()

    def step(self, timeout: float | None = None) -> list[Message]:
        """Wait for frames, then process only the newest one of each camera.

        Args:
            timeout: the most seconds to wait for a frame; by default, forever.

        Returns:
            The detections published.

        Raises:
            socket.timeout: no frame arrived within `timeout`.
        """
        messages = [self.channel.consume(timeout)] + self.channel.consume_ready()
        published = []
        for id, (frame, dropped) in self.latest_per_camera(messages, self.frame_topic).items():
            detection = self.handle(id, frame, dropped)
            if detection is not None:
                published.append(detection)
        return published

    def handle(self, camera_id: int, frame: Message, dropped: int = 0) -> Message | None:
        """Detect the markers of a frame and publish them on the camera's detection topic.

        The detection keeps the frame's created_at, the instant of the capture.

        Args:
            camera_id: the frame's camera.
            frame: the frame, an Image.
            dropped: how many older frames of the camera it replaced.

        Returns:
            The detection published, or None if the frame has no image that can be decoded.
        """
        with trace.get_tracer(__name__).start_as_current_span(
            "process {}".format(frame.topic),
            context=extract(frame),
            kind=SpanKind.CONSUMER,
            attributes={
                "messaging.system": "rabbitmq",
                "messaging.operation.type": "process",
                "messaging.operation.name": "process",
                "messaging.destination.name": "{}:{}".format(self.exchange, frame.topic),
                "pris.aruco_detector.camera_id": camera_id,
                "pris.aruco_detector.dropped": dropped,
            },
        ) as span:
            if dropped:
                self.log.debug("camera={} dropped={} older frames", camera_id, dropped)
            try:
                annotations = self.detector.detect(frame.unpack(Image))
            except (ValueError, cv2.error) as error:
                self.log.warn("camera={} frame skipped: {}", camera_id, error)
                span.set_status(StatusCode.ERROR, str(error))
                return None
            span.set_attribute("pris.aruco_detector.markers", len(annotations.objects))
            return self.publish(camera_id, frame, annotations)

    def publish(self, camera_id: int, frame: Message,
                annotations: ObjectAnnotations) -> Message:
        """Publish the annotations of a frame, with the frame's capture instant.

        Returns:
            The message published.
        """
        annotations.frame_id = camera_id
        detection = Message(content=annotations)
        detection.created_at = frame.created_at
        self.channel.publish(detection, topic=self.detection_topic.format(camera_id))
        return detection

    @staticmethod
    def camera_id(topic: str, frame_topic: str = "CameraGateway.{}.Frame") -> int | None:
        """Return the camera id of a frame topic.

        Args:
            topic: a topic.
            frame_topic: the frames' topic, with `{}` for the camera id.

        Returns:
            The id, or None for any other topic.
        """
        pattern = re.escape(frame_topic).replace(re.escape("{}"), r"(\d+)")
        match = re.fullmatch(pattern, topic)
        return int(match.group(1)) if match else None

    @staticmethod
    def latest_per_camera(messages: Iterable[Message],
                          frame_topic: str = "CameraGateway.{}.Frame",
                          ) -> dict[int, tuple[Message, int]]:
        """Keep the newest frame of each camera.

        Args:
            messages: oldest first, as `consume_ready` returns them; other topics are ignored.
            frame_topic: the frames' topic, with `{}` for the camera id.

        Returns:
            By camera id, its newest frame and how many older ones it replaces.
        """
        latest: dict[int, tuple[Message, int]] = {}
        for message in messages:
            id = ArucoDetectorService.camera_id(message.topic or "", frame_topic)
            if id is None:
                continue
            dropped = latest[id][1] + 1 if id in latest else 0
            latest[id] = (message, dropped)
        return latest
