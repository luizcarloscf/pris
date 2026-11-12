"""The graph of coordinate frames, in NumPy: each edge, traversed both ways, maps one frame to
another."""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

Array = npt.NDArray[np.float64]
Pair = tuple[int, int]


def pair(a: int, b: int) -> Pair:
    """Return the key of the edge between two frames, whatever its direction."""
    return (a, b) if a <= b else (b, a)


def invert(matrix: Array) -> Array:
    """Return the inverse of a 4x4 rigid transformation."""
    inverse = np.eye(4)
    inverse[:3, :3] = matrix[:3, :3].T
    inverse[:3, 3] = -matrix[:3, :3].T @ matrix[:3, 3]
    return inverse


@dataclass(frozen=True)
class Edge:
    """A transformation between two frames.

    Attributes:
        source: the frame whose coordinates `matrix` maps.
        target: the frame it maps them to.
        matrix: 4x4, source to target.
        static: from a calibration: never expires and isn't replaced by a dynamic edge.
        stamp: the instant it refers to, such as a capture instant, in seconds.
        expiration: when it stops being valid, in seconds; None, valid forever.
    """

    source: int
    target: int
    matrix: Array
    static: bool = False
    stamp: float | None = None
    expiration: float | None = None

    def towards(self, frame: int) -> Array:
        """Return the transformation that maps the other frame of the edge to `frame`."""
        return self.matrix if frame == self.target else invert(self.matrix)


@dataclass(frozen=True)
class Transformation:
    """The composition of the edges of a route.

    Attributes:
        source: the first frame of the route.
        target: the last frame of the route.
        matrix: 4x4, source to target.
        route: the frames from source to target.
        expiration: the earliest expiration of its edges; None if none expires.
        stamp: the latest stamp of its edges; None if none has one, all static.
    """

    source: int
    target: int
    matrix: Array
    route: tuple[int, ...]
    expiration: float | None
    stamp: float | None


class FrameGraph(object):
    """The edges between frames, and the routes and transformations they compose."""

    def __init__(self) -> None:
        """Create an empty graph."""
        self.edges: dict[Pair, Edge] = {}
        self.neighbors: dict[int, set[int]] = {}
        self.versions: dict[Pair, int] = {}
        self._counter = 0

    def set(self, edge: Edge) -> bool:
        """Add or replace the edge between its two frames, bumping its version.

        A dynamic edge goes from child (source) to parent (target), and a frame has one dynamic
        parent at a time.

        Args:
            edge: the edge.

        Returns:
            False, changing nothing, for a self edge, or for a dynamic edge that would replace a
            static or a later one, or give its source a second dynamic parent.
        """
        if edge.source == edge.target:
            return False
        key = pair(edge.source, edge.target)
        current = self.edges.get(key)
        if current is not None and not edge.static:
            if current.static:
                return False
            if current.stamp is not None and edge.stamp is not None and edge.stamp < current.stamp:
                return False
        if not edge.static and self.parent(edge.source) not in (None, edge.target):
            return False
        self.edges[key] = edge
        self.neighbors.setdefault(edge.source, set()).add(edge.target)
        self.neighbors.setdefault(edge.target, set()).add(edge.source)
        self._counter += 1
        self.versions[key] = self._counter
        return True

    def remove(self, a: int, b: int) -> bool:
        """Remove the edge between two frames.

        Returns:
            False if there was none.
        """
        key = pair(a, b)
        if self.edges.pop(key, None) is None:
            return False
        for frame, other in ((a, b), (b, a)):
            self.neighbors[frame].discard(other)
            if not self.neighbors[frame]:
                del self.neighbors[frame]
        self._counter += 1
        self.versions[key] = self._counter
        return True

    def parent(self, frame: int) -> int | None:
        """Return the dynamic parent of a frame, or None."""
        for other in self.neighbors.get(frame, ()):
            edge = self.edges[pair(frame, other)]
            if not edge.static and edge.source == frame:
                return other
        return None

    def expire(self, now: float) -> list[Pair]:
        """Remove the edges whose expiration has passed.

        Args:
            now: the current time.time().

        Returns:
            The pairs of the removed edges.
        """
        expired = [key for key, edge in self.edges.items()
                   if edge.expiration is not None and edge.expiration <= now]
        for key in expired:
            self.remove(*key)
        return expired

    def route(self, frames: Sequence[int]) -> tuple[int, ...] | None:
        """Find the frames from the first of `frames` to the last, through the others in order.

        Each segment is a fewest-hops search; between routes of the same length, static edges and
        then lower frame ids are preferred, so the same graph always gives the same route.

        Args:
            frames: the source, any hints, and the target.

        Returns:
            The route, or None if a segment is unreachable.

        Raises:
            ValueError: fewer than two frames.
        """
        if len(frames) < 2:
            raise ValueError("a route needs at least two frames")
        result: list[int] = [frames[0]]
        for start, goal in zip(frames, frames[1:]):
            segment = self._segment(start, goal)
            if segment is None:
                return None
            result.extend(segment[1:])
        return tuple(result)

    def _segment(self, start: int, goal: int) -> list[int] | None:
        if start == goal:
            return [start]
        if start not in self.neighbors or goal not in self.neighbors:
            return None
        previous: dict[int, int] = {start: start}
        queue = deque([start])
        while queue:
            frame = queue.popleft()
            for other in sorted(self.neighbors[frame], key=lambda o: self._order(frame, o)):
                if other in previous:
                    continue
                previous[other] = frame
                if other == goal:
                    path = [goal]
                    while path[-1] != start:
                        path.append(previous[path[-1]])
                    return path[::-1]
                queue.append(other)
        return None

    def _order(self, frame: int, other: int) -> tuple[bool, int]:
        return (not self.edges[pair(frame, other)].static, other)

    def compose(self, route: Sequence[int]) -> Transformation:
        """Compose the edges of a route.

        Args:
            route: frames, each joined to the next by an edge.

        Returns:
            The transformation from the first frame to the last.
        """
        matrix = np.eye(4)
        expirations, stamps = [], []
        for a, b in zip(route, route[1:]):
            edge = self.edges[pair(a, b)]
            matrix = edge.towards(b) @ matrix
            if edge.expiration is not None:
                expirations.append(edge.expiration)
            if edge.stamp is not None:
                stamps.append(edge.stamp)
        return Transformation(
            source=route[0],
            target=route[-1],
            matrix=matrix,
            route=tuple(route),
            expiration=min(expirations, default=None),
            stamp=max(stamps, default=None),
        )

    def transformation(self, frames: Sequence[int]) -> Transformation | None:
        """Return `compose(route(frames))`, or None if there is no route."""
        route = self.route(frames)
        return None if route is None else self.compose(route)

    def signature(self, route: Sequence[int]) -> tuple[tuple[Pair, int], ...]:
        """Return the edges of a route with their versions: equal signatures, equal result."""
        keys = [pair(a, b) for a, b in zip(route, route[1:])]
        return tuple((key, self.versions[key]) for key in keys)
