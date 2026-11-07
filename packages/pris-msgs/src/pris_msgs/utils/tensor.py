"""Convert pris.common.Tensor to and from NumPy arrays. Needs pris-msgs[numpy]."""

from __future__ import annotations

from collections.abc import Sequence

try:
    import numpy as np
    import numpy.typing as npt
except ImportError as error:  # pragma: no cover
    raise ImportError("pris_msgs.utils.tensor needs NumPy: install pris-msgs[numpy]") from error

from pris_msgs.common_pb2 import DataType, Tensor


def to_array(
    tensor: Tensor,
) -> npt.NDArray[np.float32 | np.float64 | np.int32 | np.int64]:
    """Convert a tensor to an array.

    Args:
        tensor: values row-major in the order of `shape.dims`; a 2-D tensor whose first dim is
            named "cols" is column-major.

    Returns:
        A new array shaped as the dims, always (rows, cols) for 2-D, with the dtype of `type`:
        float32, float64, int32 or int64.

    Raises:
        ValueError: the tensor has no shape, a negative size, an unknown type, or a value count
            that doesn't match its shape.
    """
    dims = tensor.shape.dims
    if len(dims) == 0:
        raise ValueError("tensor has no shape")
    shape = tuple(dim.size for dim in dims)
    if any(size < 0 for size in shape):
        raise ValueError(f"negative size in shape {shape}")

    array: npt.NDArray[np.float32 | np.float64 | np.int32 | np.int64]
    if tensor.type == DataType.FLOAT_TYPE:
        array = np.array(tensor.floats, dtype=np.float32)
    elif tensor.type == DataType.DOUBLE_TYPE:
        array = np.array(tensor.doubles, dtype=np.float64)
    elif tensor.type == DataType.INT32_TYPE:
        array = np.array(tensor.ints32, dtype=np.int32)
    elif tensor.type == DataType.INT64_TYPE:
        array = np.array(tensor.ints64, dtype=np.int64)
    else:
        raise ValueError(f"unsupported tensor type {DataType.Name(tensor.type)}")

    array = array.reshape(shape)
    if len(dims) == 2 and dims[0].name == "cols":
        array = array.T.copy()
    return array


def to_tensor(
    array: npt.ArrayLike,
    names: Sequence[str] | None = None,
) -> Tensor:
    """Convert an array to a tensor.

    Args:
        array: float32, float64, int32 or int64 values, in any byte order, with at least one dim.
        names: one name per dim; by default "rows" and "cols" for 2-D, unnamed otherwise.

    Returns:
        A row-major tensor.

    Raises:
        ValueError: the array is 0-d, or `names` has the wrong length.
        TypeError: the array has another dtype.
    """
    array = np.asarray(array)
    if array.ndim == 0:
        raise ValueError("a tensor needs at least one dim")
    if names is None:
        names = ("rows", "cols") if array.ndim == 2 else ("",) * array.ndim
    elif len(names) != array.ndim:
        raise ValueError(f"{len(names)} names for {array.ndim} dims")

    tensor = Tensor()
    for size, name in zip(array.shape, names):
        tensor.shape.dims.add(size=size, name=name)
    dtype = array.dtype.newbyteorder("=")
    if dtype == np.float32:
        tensor.type = DataType.FLOAT_TYPE
        tensor.floats.extend(array.ravel().tolist())
    elif dtype == np.float64:
        tensor.type = DataType.DOUBLE_TYPE
        tensor.doubles.extend(array.ravel().tolist())
    elif dtype == np.int32:
        tensor.type = DataType.INT32_TYPE
        tensor.ints32.extend(array.ravel().tolist())
    elif dtype == np.int64:
        tensor.type = DataType.INT64_TYPE
        tensor.ints64.extend(array.ravel().tolist())
    else:
        raise TypeError(f"no Tensor type for dtype '{array.dtype}'")
    return tensor
