import numpy as np
import pytest

from pris_msgs.image_pb2 import Vertex
from pris_msgs.utils.vertex import to_array, to_vertex


def test_round_trip_3d():
    vertex = Vertex(x=1.5, y=-2.0, z=3.25)
    array = to_array(vertex)
    np.testing.assert_array_equal(array, [1.5, -2.0, 3.25])
    assert to_vertex(array) == vertex


def test_round_trip_2d():
    vertex = Vertex(x=320, y=240)
    array = to_array(vertex, dims=2)
    np.testing.assert_array_equal(array, [320, 240])
    assert to_vertex(array) == vertex


@pytest.mark.parametrize("dims, expected", [(2, [1, 2, 1]), (3, [1, 2, 3, 1])])
def test_homogeneous(dims, expected):
    vertex = Vertex(x=1, y=2, z=3 if dims == 3 else 0)
    array = to_array(vertex, dims=dims, homogeneous=True)
    np.testing.assert_array_equal(array, expected)
    assert to_vertex(array, homogeneous=True) == vertex


def test_lists_and_numpy_scalars_are_accepted():
    assert to_vertex([1, 2, 3]) == Vertex(x=1, y=2, z=3)
    assert to_vertex(np.array([1, 2], dtype=np.float32)) == Vertex(x=1, y=2)


def test_to_array_errors():
    with pytest.raises(ValueError, match="2 or 3 dims"):
        to_array(Vertex(), dims=4)


@pytest.mark.parametrize("value, homogeneous", [
    ([1], False),
    ([1, 2, 3, 4], False),
    ([1, 2], True),
    (np.zeros((1, 3)), False),
    (np.zeros(()), False),
])
def test_to_vertex_errors(value, homogeneous):
    with pytest.raises(ValueError, match="1-D array of 2 or 3 values"):
        to_vertex(value, homogeneous=homogeneous)
