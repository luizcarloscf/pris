"""The service: the frame graph, kept from calibrations and transformations, published and
served."""

from __future__ import annotations

import time
from collections.abc import Iterable

import numpy as np
import numpy.typing as npt
from google.protobuf.timestamp_pb2 import Timestamp
from opentelemetry import trace
from opentelemetry.instrumentation.pris_wire import extract
from opentelemetry.trace import Link, SpanKind
from pris_msgs.camera_pb2 import (
    CameraCalibration,
    FrameTransformation,
    FrameTransformations,
    GetTransformationReply,
    GetTransformationRequest,
)
from pris_msgs.common_pb2 import ConsumerList
from pris_msgs.utils.tensor import to_array, to_tensor
from pris_wire.core import Channel, Logger, Message, Status, StatusCode, Subscription
from pris_wire.rpc import LogInterceptor, ServiceProvider
from pris_wire.rpc.context import Context

from pris_frame_transformation.graph import Edge, FrameGraph, Pair, Transformation, pair
from pris_frame_transformation.watch import Watches, topic_for


class FrameTransformationService(object):
    """Composes the transformation between any two frames, published and on request."""

    log = Logger("FrameTransformation")

    def __init__(
        self,
        channel: Channel,
        calibrations: Iterable[CameraCalibration],
        consumers_topic: str = "BrokerEvents.Consumers",
        transformations_topic: str = "#.FrameTransformations",
        get_transformation_topic: str = "FrameTransformation.GetTransformation",
    ) -> None:
        """Add the calibrations' static edges, then subscribe and register the request.

        `consumers_topic` is subscribed first: pris-broker-events publishes the consumers only
        when they change, and the subscriptions that follow are such changes.

        Args:
            channel: the channel that consumes and publishes everything.
            calibrations: the cameras' calibrations; every extrinsic becomes a static edge.
            consumers_topic: where pris-broker-events publishes the consumers of each topic.
            transformations_topic: where dynamic edges arrive, as FrameTransformations.
            get_transformation_topic: where the request is served.

        Raises:
            ValueError: an extrinsic isn't a 4x4 matrix.
        """
        self.channel = channel
        self.graph = FrameGraph()
        self.watches = Watches()
        self.refused: set[Pair] = set()
        for calibration in calibrations:
            edges = self.static_edges(calibration)
            for edge in edges:
                self.graph.set(edge)
            self.log.info("Camera {}: static edges {}", calibration.id,
                          [(edge.source, edge.target) for edge in edges])
        self.consumers = Subscription(channel)
        self.consumers.subscribe(consumers_topic)
        self.transformations = Subscription(channel)
        self.transformations.subscribe(transformations_topic)
        self.provider = ServiceProvider(channel)
        self.provider.add_interceptor(LogInterceptor())
        self.provider.delegate(get_transformation_topic, self.get_transformation,
                               GetTransformationRequest, GetTransformationReply)

    def run(self) -> None:
        """Run `step` until the process stops."""
        while True:
            self.step()

    def step(self, timeout: float | None = None) -> list[Message]:
        """Handle every message ready, then publish each watched transformation that changed.

        Args:
            timeout: the most seconds to wait for a message; by default, until the next edge
                expires, or forever if none expires.

        Returns:
            The messages published.
        """
        deadlines = [d for d in (self.next_expiration(),) if d is not None]
        if timeout is not None:
            deadlines.append(time.time() + timeout)
        message = (self.channel.consume_until(min(deadlines)) if deadlines
                   else self.channel.consume())
        messages = [message] + self.channel.consume_ready() if message is not None else []

        self.graph.expire(time.time())
        links = []
        updated = 0
        for message in messages:
            if message.subscription_id == self.consumers.id:
                self.set_consumers(message)
            elif message.subscription_id == self.transformations.id:
                updated += self.update(message)
                context = trace.get_current_span(extract(message)).get_span_context()
                if context.is_valid:
                    links.append(Link(context))
            elif self.provider.should_serve(message):
                self.provider.serve(message)
        return self.publish_due(links, updated)

    def next_expiration(self) -> float | None:
        """Return when the next edge expires, or None if none does."""
        return min((edge.expiration for edge in self.graph.edges.values()
                    if edge.expiration is not None), default=None)

    def set_consumers(self, message: Message) -> None:
        """Watch the transformation topics of a ConsumerList."""
        info = message.unpack(ConsumerList).info
        added, removed = self.watches.set_consumers(
            {topic: info[topic].consumers for topic in info})
        for path in sorted(added):
            self.log.info("Watching {}", topic_for(path, self.watches.prefix))
        for path in sorted(removed):
            self.log.info("No longer watching {}", topic_for(path, self.watches.prefix))

    def update(self, message: Message) -> int:
        """Add the dynamic edges of a FrameTransformations message.

        Returns:
            How many edges were set; an unusable message, or an edge the graph refuses, is logged
            and ignored.
        """
        try:
            edges = self.dynamic_edges(message.unpack(FrameTransformations), message.created_at)
        except ValueError as error:
            self.log.warn("'{}': unusable transformations: {}", message.topic, error)
            return 0
        count = 0
        for edge in edges:
            if self.graph.set(edge):
                count += 1
                continue
            key = pair(edge.source, edge.target)
            if key not in self.refused:
                self.refused.add(key)
                self.log.warn("'{}': edge {} -> {} ignored (static, older, a second parent or "
                              "a self edge)", message.topic, edge.source, edge.target)
        return count

    def publish_due(self, links: list[Link], updated: int) -> list[Message]:
        """Publish the watched transformations that changed, in an `update` span.

        Args:
            links: the trace contexts of the messages that brought the changes.
            updated: how many edges they set.

        Returns:
            The messages published.
        """
        due = self.watches.due(self.graph)
        if not due and not links:
            return []
        published = []
        with trace.get_tracer(__name__).start_as_current_span(
                "update", kind=SpanKind.INTERNAL, links=links) as span:
            for path, transformation in due:
                message = Message(content=self.to_message(transformation))
                message.topic = topic_for(path, self.watches.prefix)
                if transformation.stamp is not None:
                    message.created_at = transformation.stamp
                self.channel.publish(message)
                published.append(message)
            span.set_attributes({
                "pris.frame_transformation.edges": updated,
                "pris.frame_transformation.published": [message.topic for message in published],
            })
        return published

    def get_transformation(self, request: GetTransformationRequest,
                           context: Context) -> GetTransformationReply | Status:
        """Return the transformations of the requested pairs, in their order.

        Args:
            request: (source, target) pairs, without hints.
            context: the request's context.

        Returns:
            The transformations, or NOT_FOUND for the first pair without a route.
        """
        self.graph.expire(time.time())
        reply = GetTransformationReply()
        for ids in request.ids:
            transformation = self.graph.transformation([ids.source, ids.target])
            if transformation is None:
                return Status(StatusCode.NOT_FOUND, "no transformation from {} to {}".format(
                    ids.source, ids.target))
            reply.transformations.append(self.to_message(transformation))
        return reply

    @staticmethod
    def static_edges(calibration: CameraCalibration) -> list[Edge]:
        """Return one static edge per extrinsic of a calibration, from its source to the camera.

        Raises:
            ValueError: an extrinsic isn't a 4x4 matrix.
        """
        edges = []
        for extrinsic in calibration.extrinsic:
            matrix = FrameTransformationService._matrix(extrinsic)
            edges.append(Edge(extrinsic.source, extrinsic.target, matrix, static=True))
        return edges

    @staticmethod
    def dynamic_edges(transformations: FrameTransformations, stamp: float) -> list[Edge]:
        """Return one edge per transformation of a message.

        Args:
            transformations: the message.
            stamp: its created_at, the instant the transformations refer to.

        Raises:
            ValueError: a transformation isn't a 4x4 matrix.
        """
        edges = []
        for transformation in transformations.tfs:
            expiration = (transformation.expiration.ToNanoseconds() / 1e9
                          if transformation.HasField("expiration") else None)
            matrix = FrameTransformationService._matrix(transformation)
            edges.append(Edge(transformation.source, transformation.target, matrix, stamp=stamp,
                              expiration=expiration))
        return edges

    @staticmethod
    def _matrix(transformation: FrameTransformation) -> npt.NDArray[np.float64]:
        matrix = to_array(transformation.tf).astype(np.float64)
        if matrix.shape != (4, 4):
            raise ValueError("{} -> {}: a {} matrix, expected 4x4".format(
                transformation.source, transformation.target, matrix.shape))
        return matrix

    @staticmethod
    def to_message(transformation: Transformation) -> FrameTransformation:
        """Return a transformation as a FrameTransformation, with its expiration if any."""
        result = FrameTransformation(source=transformation.source, target=transformation.target,
                                     tf=to_tensor(transformation.matrix))
        if transformation.expiration is not None:
            expiration = Timestamp()
            expiration.FromNanoseconds(int(round(transformation.expiration * 1e9)))
            result.expiration.CopyFrom(expiration)
        return result
