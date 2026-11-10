"""The service: localize the markers seen by the cameras at each capture instant."""

from __future__ import annotations

import re
import time
from collections.abc import Mapping

import numpy as np
from google.protobuf.timestamp_pb2 import Timestamp
from opentelemetry import trace
from opentelemetry.instrumentation.pris_wire import extract
from opentelemetry.trace import Link
from pris_msgs.camera_pb2 import FrameTransformation, FrameTransformations
from pris_msgs.image_pb2 import ObjectAnnotations
from pris_msgs.utils.tensor import to_tensor
from pris_wire.core import Channel, Logger, Message, Subscription

from pris_aruco_localization.conf.options_pb2 import ArucoLocalizationOptions
from pris_aruco_localization.geometry import Camera, Estimate, Observation, localize


class ArucoLocalization(object):
    """Publishes, for each capture instant, the poses of the markers the cameras saw.

    A capture instant is the oldest created_at among the detections waiting, with the detections
    within `sync.tolerance` of it, one per camera.
    """

    log = Logger("ArucoLocalization")

    def __init__(
        self,
        channel: Channel,
        cameras: Mapping[int, Camera],
        options: ArucoLocalizationOptions,
        detection_topic: str = "ArUco.{}.Detection",
        transformations_topic: str = "ArUco.FrameTransformations",
    ) -> None:
        """Subscribe to the detections of the cameras of `options.camera_ids`.

        Args:
            channel: the channel that consumes the detections and publishes the poses.
            cameras: the calibrated cameras, by id.
            options: the service's options.
            detection_topic: the detections' topic, with `{}` for the camera id.
            transformations_topic: where the poses are published.
        """
        self.channel = channel
        self.cameras = cameras
        self.options = options
        self.detection_topic = detection_topic
        self.transformations_topic = transformations_topic
        self.topics = {detection_topic.format(id) for id in options.camera_ids}
        self.subscription = Subscription(channel)
        for topic in self.topics:
            self.subscription.subscribe(topic)
        self.pending: list[Message] = []
        self.deadline = 0.0
        self.last = float("-inf")
        self.log.info("Subscribed to {}; markers {}", sorted(self.topics), sorted(options.markers))

    def run(self) -> None:
        """Run `step` until the process stops."""
        while True:
            self.step()

    def step(self, timeout: float | None = None) -> Message:
        """Wait for the detections of one capture instant, then localize and publish them.

        The instant is solved once every camera has sent, or `sync.max_delay` after its first
        detection arrived, with the cameras that have. A detection older than the last instant
        solved is dropped.

        Args:
            timeout: the most seconds to wait for a first detection; by default, forever.

        Returns:
            The message published.

        Raises:
            socket.timeout: no detection arrived within `timeout`.
        """
        tolerance, max_delay = self.options.sync.tolerance, self.options.sync.max_delay
        while True:
            message = (
                self.channel.consume_until(self.deadline)
                if self.pending
                else self.channel.consume(timeout)
            )
            if message is not None and message.created_at > self.last + tolerance:
                if not self.pending:
                    self.deadline = time.time() + max_delay
                self.pending.append(message)
            if not self.pending:
                continue
            first = min(m.created_at for m in self.pending)
            instant = {
                m.topic: m for m in reversed(self.pending) if m.created_at - first <= tolerance
            }
            if instant.keys() == self.topics or time.time() >= self.deadline:
                self.pending = [m for m in self.pending if m.created_at - first > tolerance]
                self.deadline = time.time() + max_delay
                self.last = first
                return self.solve(instant)

    def solve(self, messages: Mapping[str, Message]) -> Message:
        """Localize the markers of one capture instant and publish them, even when none is found.

        Args:
            messages: the detections of the instant, by topic.

        Returns:
            The message published, at the mean capture instant of the detections.
        """
        instant = sum(message.created_at for message in messages.values()) / len(messages)
        detections = {}
        links = []
        for topic, message in messages.items():
            camera_id = self.camera_id(topic, self.detection_topic)
            if camera_id is not None:
                detections[camera_id] = message.unpack(ObjectAnnotations)
            context = trace.get_current_span(extract(message)).get_span_context()
            if context.is_valid:
                links.append(Link(context))

        with trace.get_tracer(__name__).start_as_current_span("localize", links=links) as span:
            result = FrameTransformations()
            by_marker = self.observations(detections, self.cameras, self.options.markers)
            localized, discarded = [], []
            for marker_id, marker_observations in sorted(by_marker.items()):
                length = self.options.markers[marker_id]
                estimate = localize(marker_observations, length, self.options.max_camera_error)
                if estimate is None or not self.accepted(estimate, self.options):
                    discarded.append(marker_id)
                    continue
                localized.append(marker_id)
                result.tfs.append(self.transformation(marker_id, estimate, self.options, instant))
                span.add_event(
                    "marker",
                    {
                        "pris.aruco_localization.marker_id": marker_id,
                        "pris.aruco_localization.cameras": list(estimate.camera_ids),
                        "pris.aruco_localization.rejected": list(estimate.rejected),
                        "pris.aruco_localization.error": estimate.error,
                    },
                )
                if estimate.rejected:
                    self.log.debug(
                        "marker={} cameras {} rejected as outliers",
                        marker_id,
                        list(estimate.rejected),
                    )
            span.set_attributes(
                {
                    "pris.aruco_localization.cameras": sorted(detections),
                    "pris.aruco_localization.markers": localized,
                    "pris.aruco_localization.discarded": discarded,
                    "pris.aruco_localization.delay": time.time() - instant,
                }
            )
            message = Message(content=result)
            message.topic = self.transformations_topic
            message.created_at = instant
            self.channel.publish(message)
            return message

    @staticmethod
    def camera_id(topic: str, detection_topic: str = "ArUco.{}.Detection") -> int | None:
        """Return the camera id of a detection topic, or None for any other topic.

        Args:
            topic: a topic.
            detection_topic: the detections' topic, with `{}` for the camera id.
        """
        pattern = re.escape(detection_topic).replace(re.escape("{}"), r"(\d+)")
        match = re.fullmatch(pattern, topic)
        return int(match.group(1)) if match else None

    @staticmethod
    def observations(
        detections: Mapping[int, ObjectAnnotations],
        cameras: Mapping[int, Camera],
        markers: Mapping[int, float],
    ) -> dict[int, list[Observation]]:
        """Return the corners of each configured marker, per calibrated camera.

        Each camera's intrinsics are scaled to the resolution of its detection.

        Args:
            detections: the annotations, by camera id.
            cameras: the calibrated cameras, by id; other cameras are ignored.
            markers: the side length of each marker to localize; other markers are ignored.
        """
        by_marker: dict[int, list[Observation]] = {}
        for camera_id, detection in sorted(detections.items()):
            camera = cameras.get(camera_id)
            if camera is None:
                continue
            resolution = detection.resolution
            if resolution.width and resolution.height:
                camera = camera.scaled(resolution.width, resolution.height)
            for marker in detection.objects:
                vertices = marker.region.vertices
                if marker.id not in markers or len(vertices) != 4:
                    continue
                corners = np.array([[vertex.x, vertex.y] for vertex in vertices], dtype=np.float64)
                by_marker.setdefault(marker.id, []).append(Observation(camera, corners))
        return by_marker

    @staticmethod
    def transformation(
        marker_id: int, estimate: Estimate, options: ArucoLocalizationOptions, instant: float
    ) -> FrameTransformation:
        """Return the marker's pose, from its frame to the reference frame, valid for
        `options.validity` seconds after `instant`."""
        result = FrameTransformation(
            source=options.frame_id_offset + marker_id,
            target=options.reference_frame,
            tf=to_tensor(estimate.pose),
        )
        expiration = Timestamp()
        expiration.FromNanoseconds(int(round((instant + options.validity) * 1e9)))
        result.expiration.CopyFrom(expiration)
        return result

    @staticmethod
    def accepted(estimate: Estimate, options: ArucoLocalizationOptions) -> bool:
        """Tell whether an estimate has enough cameras and, with `max_error` set, a small error."""
        if len(estimate.camera_ids) < options.min_cameras:
            return False
        return options.max_error == 0 or estimate.error <= options.max_error
