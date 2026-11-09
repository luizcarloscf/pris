import numpy as np
import pytest

from pris_frame_transformation.graph import Edge, FrameGraph
from pris_frame_transformation.watch import Watches, parse_topic, topic_for


@pytest.mark.parametrize("topic, path", [
    ("FrameTransformation.100.1000", (100, 1000)),
    ("FrameTransformation.100.0.1000", (100, 0, 1000)),
    ("FrameTransformation.-1.5", (-1, 5)),
    ("FrameTransformation.100", None),
    ("FrameTransformation.GetTransformation", None),
    ("FrameTransformation.1.x", None),
    ("ArUco.FrameTransformations", None),
    ("Other.FrameTransformation.1.2", None),
])
def test_parse_topic(topic, path):
    assert parse_topic(topic) == path


def test_topic_for():
    assert topic_for((100, 0, 1000)) == "FrameTransformation.100.0.1000"
    assert parse_topic(topic_for((7, 8))) == (7, 8)


def graph():
    result = FrameGraph()
    result.set(Edge(1000, 0, np.eye(4), static=True))
    result.set(Edge(100, 1000, np.eye(4), stamp=1.0, expiration=2.0))
    return result


def due(watches, frames):
    return [path for path, _ in watches.due(frames)]


def test_consumers_select_transformation_topics():
    watches = Watches()
    added, removed = watches.set_consumers(
        ["FrameTransformation.100.0", "ArUco.0.Detection", "FrameTransformation.0.1000"])
    assert added == {(100, 0), (0, 1000)} and removed == set()
    added, removed = watches.set_consumers(["FrameTransformation.0.1000"])
    assert added == set() and removed == {(100, 0)}


def test_a_watched_path_is_due_once_until_it_changes():
    frames = graph()
    watches = Watches()
    watches.set_consumers(["FrameTransformation.100.0", "FrameTransformation.1000.0"])
    assert due(watches, frames) == [(100, 0), (1000, 0)]
    assert due(watches, frames) == []
    frames.set(Edge(100, 1000, np.eye(4), stamp=1.1, expiration=2.1))
    assert due(watches, frames) == [(100, 0)]
    assert due(watches, frames) == []


def test_unresolved_paths_are_due_when_they_resolve():
    frames = graph()
    watches = Watches()
    watches.set_consumers(["FrameTransformation.101.0"])
    assert due(watches, frames) == []
    frames.set(Edge(101, 1000, np.eye(4), stamp=1.0))
    assert due(watches, frames) == [(101, 0)]


def test_a_path_that_expires_and_comes_back_is_due_again():
    frames = graph()
    watches = Watches()
    watches.set_consumers(["FrameTransformation.100.0"])
    assert due(watches, frames) == [(100, 0)]
    frames.expire(now=2.0)
    assert due(watches, frames) == []
    frames.set(Edge(100, 1000, np.eye(4), stamp=3.0, expiration=4.0))
    assert due(watches, frames) == [(100, 0)]


def test_a_path_watched_again_is_due_again():
    frames = graph()
    watches = Watches()
    watches.set_consumers(["FrameTransformation.1000.0"])
    assert due(watches, frames) == [(1000, 0)]
    watches.set_consumers([])
    watches.set_consumers(["FrameTransformation.1000.0"])
    assert due(watches, frames) == [(1000, 0)]


def test_due_returns_the_transformation():
    frames = graph()
    watches = Watches()
    watches.set_consumers(["FrameTransformation.100.1000.0"])
    (path, transformation), = watches.due(frames)
    assert path == (100, 1000, 0)
    assert transformation.route == (100, 1000, 0)
    assert transformation.expiration == 2.0


def test_another_prefix():
    watches = Watches(prefix="Tf")

    added, _ = watches.set_consumers(["Tf.1.2", "FrameTransformation.3.4"])

    assert added == {(1, 2)}
    assert topic_for((1, 2), prefix="Tf") == "Tf.1.2"
    assert parse_topic("Tf.1.2") is None
