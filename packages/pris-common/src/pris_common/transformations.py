"""Frame transformations fetched from pris-frame-transformation."""

from __future__ import annotations

from collections.abc import Iterable

from pris_msgs.camera_pb2 import (
    FrameTransformation,
    GetTransformationReply,
    GetTransformationRequest,
    IdPair,
)
from pris_wire.core import Channel

from pris_common.rpc import call


def fetch_transformations(
    channel: Channel,
    pairs: Iterable[tuple[int, int]],
    timeout: float = 5.0,
    topic: str = "FrameTransformation.GetTransformation",
) -> dict[tuple[int, int], FrameTransformation]:
    """Request the transformations between pairs of frames and wait for the reply.

    The reply holds each transformation as it is now, so it suits fixed ones, such as from a
    camera to the world; one that changes, such as a marker's, is watched on its topic instead.
    Call it at startup, before subscribing to anything else on `channel`: it consumes the channel
    until the reply arrives, and drops any other message.

    Args:
        channel: the channel that publishes the request and consumes the reply.
        pairs: (source, target) frame ids; each transformation maps source coordinates to target
            coordinates.
        timeout: the most seconds to wait for the reply.
        topic: where pris-frame-transformation listens.

    Returns:
        The transformations, by (source, target).

    Raises:
        socket.timeout: no reply within `timeout`.
        RuntimeError: the server answered with an error, such as NOT_FOUND for a pair without a
            route, or the reply misses a pair.
    """
    pairs = list(dict.fromkeys(pairs))
    request = GetTransformationRequest(ids=[IdPair(source=s, target=t) for s, t in pairs])
    reply = call(channel, request, topic, timeout)
    found = {(tf.source, tf.target): tf
             for tf in reply.unpack(GetTransformationReply).transformations}
    missing = [pair for pair in pairs if pair not in found]
    if missing:
        raise RuntimeError("no transformation for {}".format(missing))
    return {pair: found[pair] for pair in pairs}
