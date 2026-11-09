"""Convert pris.vision.Vertex to and from NumPy arrays. Needs pris-msgs[numpy]."""

from __future__ import annotations

from typing import Literal

try:
    import numpy as np
    import numpy.typing as npt
except ImportError as error:  # pragma: no cover
    raise ImportError("pris_msgs.utils.vertex needs NumPy: install pris-msgs[numpy]") from error

from pris_msgs.image_pb2 import Vertex


def to_array(
    vertex: Vertex,
    dims: Literal[2, 3] = 3,
    homogeneous: bool = False,
) -> npt.NDArray[np.float64]:
    """Convert a vertex to an array.

    Args:
        vertex: the vertex to read.
        dims: 2 for an image point [x, y], 3 for a point in space [x, y, z].
        homogeneous: append a 1 to get homogeneous coordinates.

    Returns:
        A new array of `dims` values, plus the 1 when `homogeneous`.

    Raises:
        ValueError: `dims` isn't 2 or 3.
    """
    if dims == 3:
        values = [vertex.x, vertex.y, vertex.z]
    elif dims == 2:
        values = [vertex.x, vertex.y]
    else:
        raise ValueError(f"a vertex has 2 or 3 dims, got {dims}")
    if homogeneous:
        values.append(1.0)
    return np.array(values)


def to_vertex(array: npt.ArrayLike, homogeneous: bool = False) -> Vertex:
    """Convert an array to a vertex.

    Args:
        array: 1-D [x, y] or [x, y, z]; z is 0 for a 2-D point.
        homogeneous: the array has a trailing scale value, which is dropped without dividing.

    Returns:
        A vertex with the array's values.

    Raises:
        ValueError: the array isn't 1-D or doesn't have 2 or 3 values, homogeneous one excluded.
    """
    array = np.asarray(array)
    if homogeneous and array.ndim == 1:
        array = array[:-1]
    if array.ndim != 1 or array.size not in (2, 3):
        raise ValueError(f"a vertex needs a 1-D array of 2 or 3 values, got shape {array.shape}")
    z = float(array[2]) if array.size == 3 else 0.0
    return Vertex(x=float(array[0]), y=float(array[1]), z=z)
