"""The transformation topics someone listens to, and when to publish them."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from pris_frame_transformation.graph import FrameGraph, Pair, Transformation

Path = tuple[int, ...]


def parse_topic(topic: str, prefix: str = "FrameTransformation") -> Path | None:
    """Return the frames of a `<prefix>.<source>[.<hint>...].<target>` topic.

    Args:
        topic: the topic.
        prefix: the first word of a transformation topic.

    Returns:
        The frames, or None for any other topic.
    """
    match = re.fullmatch(re.escape(prefix) + r"((?:\.-?\d+){2,})", topic)
    if match is None:
        return None
    return tuple(int(id) for id in match.group(1)[1:].split("."))


def topic_for(path: Path, prefix: str = "FrameTransformation") -> str:
    """Return the topic of a path of frames.

    Args:
        path: the source, any hints, and the target.
        prefix: the first word of a transformation topic.
    """
    return ".".join([prefix] + [str(id) for id in path])


class Watches(object):
    """The paths someone listens to, and the route each was last published with."""

    def __init__(self, prefix: str = "FrameTransformation") -> None:
        """Watch nothing.

        Args:
            prefix: the first word of a transformation topic.
        """
        self.prefix = prefix
        self.consumers: dict[Path, set[str]] = {}
        self.published: dict[Path, tuple[tuple[Pair, int], ...]] = {}

    def set_consumers(self, consumers: Mapping[str, Iterable[str]]) -> tuple[set[Path], set[Path]]:
        """Watch exactly the transformation topics among `consumers`.

        A path with a new consumer is published again at the next `due`, so the newcomer gets it.

        Args:
            consumers: the queues of each topic, as in a ConsumerList.

        Returns:
            The paths added and removed.
        """
        current: dict[Path, set[str]] = {}
        for topic, queues in consumers.items():
            path = parse_topic(topic, self.prefix)
            if path is not None:
                current[path] = set(queues)
        added = set(current) - set(self.consumers)
        removed = set(self.consumers) - set(current)
        for path in removed:
            self.published.pop(path, None)
        for path in set(current) & set(self.consumers):
            if current[path] - self.consumers[path]:
                self.published.pop(path, None)
        self.consumers = current
        return added, removed

    def due(self, graph: FrameGraph) -> list[tuple[Path, Transformation]]:
        """Return the watched paths whose route or edges changed since last published.

        They are marked published. A path that stops resolving is forgotten, so it is published
        again as soon as it resolves.

        Args:
            graph: the current graph.

        Returns:
            The paths and their new transformations, in a stable order.
        """
        result = []
        for path in sorted(self.consumers):
            route = graph.route(path)
            if route is None:
                self.published.pop(path, None)
                continue
            signature = graph.signature(route)
            if self.published.get(path) == signature:
                continue
            self.published[path] = signature
            result.append((path, graph.compose(route)))
        return result
