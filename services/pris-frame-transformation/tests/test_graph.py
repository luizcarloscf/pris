import numpy as np
import pytest

from pris_frame_transformation.graph import Edge, FrameGraph, invert, pair


def rigid(angle, translation, axis=2):
    """4x4 rotation of `angle` about `axis`, then a translation."""
    c, s = np.cos(angle), np.sin(angle)
    i, j = [k for k in range(3) if k != axis]
    matrix = np.eye(4)
    matrix[i, i], matrix[i, j], matrix[j, i], matrix[j, j] = c, -s, s, c
    matrix[:3, 3] = translation
    return matrix


WORLD_TO_CAM0 = rigid(0.3, [1.0, 2.0, 3.0])
WORLD_TO_CAM1 = rigid(-1.2, [-2.0, 0.5, 2.5], axis=0)
MARKER_TO_WORLD = rigid(0.7, [0.2, -0.1, 0.0])


def room():
    """World 1000, cameras 0 and 1 (static), marker 100 (dynamic)."""
    graph = FrameGraph()
    graph.set(Edge(1000, 0, WORLD_TO_CAM0, static=True))
    graph.set(Edge(1000, 1, WORLD_TO_CAM1, static=True))
    graph.set(Edge(100, 1000, MARKER_TO_WORLD, stamp=5.0, expiration=6.0))
    return graph


def test_direct_and_inverse_edges():
    graph = room()
    np.testing.assert_allclose(graph.transformation([1000, 0]).matrix, WORLD_TO_CAM0)
    np.testing.assert_allclose(graph.transformation([0, 1000]).matrix, invert(WORLD_TO_CAM0))


def test_multi_hop_composition():
    graph = room()
    result = graph.transformation([100, 1])
    assert result.route == (100, 1000, 1)
    np.testing.assert_allclose(result.matrix, WORLD_TO_CAM1 @ MARKER_TO_WORLD, atol=1e-12)
    point = np.array([0.3, -0.4, 2.0, 1.0])
    to_cam1 = graph.transformation([0, 1]).matrix
    np.testing.assert_allclose(
        to_cam1 @ point, WORLD_TO_CAM1 @ invert(WORLD_TO_CAM0) @ point, atol=1e-12)


def test_hints_force_the_path():
    graph = room()
    graph.set(Edge(0, 1, rigid(0.1, [3.0, 0.0, 0.0]), static=True))
    assert graph.route([0, 1]) == (0, 1)
    assert graph.route([0, 1000, 1]) == (0, 1000, 1)
    np.testing.assert_allclose(graph.transformation([0, 1000, 1]).matrix,
                               WORLD_TO_CAM1 @ invert(WORLD_TO_CAM0), atol=1e-12)


def test_unreachable_and_unknown_frames():
    graph = room()
    graph.set(Edge(7, 8, np.eye(4)))
    assert graph.route([0, 7]) is None
    assert graph.route([0, 12345]) is None
    assert graph.transformation([12345, 0]) is None
    with pytest.raises(ValueError):
        graph.route([0])


def test_a_frame_to_itself():
    graph = room()
    result = graph.transformation([0, 0])
    assert result.route == (0,)
    np.testing.assert_allclose(result.matrix, np.eye(4))


def test_ties_prefer_static_edges_then_lower_ids():
    graph = FrameGraph()
    for middle, static in ((5, False), (3, True), (4, True)):
        graph.set(Edge(1, middle, np.eye(4), static=static))
        graph.set(Edge(middle, 9, np.eye(4), static=static))
    assert graph.route([1, 9]) == (1, 3, 9)
    graph.remove(1, 3)
    assert graph.route([1, 9]) == (1, 4, 9)
    graph.remove(1, 4)
    assert graph.route([1, 9]) == (1, 5, 9)


def test_expiration_and_stamp_of_a_composition():
    graph = room()
    graph.set(Edge(101, 1000, np.eye(4), stamp=5.5, expiration=7.0))
    result = graph.transformation([100, 1000, 101])
    assert result.expiration == 6.0
    assert result.stamp == 5.5
    static = graph.transformation([0, 1])
    assert static.expiration is None and static.stamp is None


def test_expired_edges_are_removed():
    graph = room()
    assert graph.expire(now=5.9) == []
    assert graph.expire(now=6.0) == [(100, 1000)]
    assert graph.route([100, 0]) is None
    assert 100 not in graph.neighbors
    assert graph.expire(now=1e12) == []


def test_dynamic_updates_never_replace_static_edges():
    graph = room()
    assert not graph.set(Edge(0, 1000, np.eye(4)))
    np.testing.assert_allclose(graph.transformation([1000, 0]).matrix, WORLD_TO_CAM0)
    assert graph.set(Edge(1000, 0, np.eye(4), static=True))
    np.testing.assert_allclose(graph.transformation([1000, 0]).matrix, np.eye(4))


def test_a_newer_edge_replaces_the_older_in_either_direction():
    graph = room()
    graph.set(Edge(1000, 100, invert(MARKER_TO_WORLD) @ rigid(0, [1, 0, 0]), stamp=5.1))
    np.testing.assert_allclose(graph.transformation([100, 1000]).matrix,
                               invert(invert(MARKER_TO_WORLD) @ rigid(0, [1, 0, 0])), atol=1e-12)
    assert len(graph.edges) == 3


def test_self_edges_are_refused():
    assert not FrameGraph().set(Edge(3, 3, np.eye(4)))


def test_versions_change_with_every_update():
    graph = room()
    route = graph.route([100, 0])
    before = graph.signature(route)
    graph.set(Edge(100, 1000, MARKER_TO_WORLD, stamp=5.1, expiration=6.1))
    assert graph.signature(route) != before
    unrelated = graph.signature(graph.route([0, 1]))
    graph.set(Edge(100, 1000, MARKER_TO_WORLD, stamp=5.2, expiration=6.2))
    assert graph.signature(graph.route([0, 1])) == unrelated


def test_remove():
    graph = room()
    assert graph.remove(1000, 100)
    assert not graph.remove(1000, 100)
    assert pair(100, 1000) not in graph.edges
