import numpy as np
import pytest

from pris_msgs.common_pb2 import DataType, Tensor
from pris_msgs.utils.tensor import to_array, to_tensor


def tensor(type, values, *dims):
    """Tensor with the given (size, name) dims."""
    field = {DataType.FLOAT_TYPE: "floats", DataType.DOUBLE_TYPE: "doubles",
             DataType.INT32_TYPE: "ints32", DataType.INT64_TYPE: "ints64"}[type]
    result = Tensor(type=type, **{field: values})
    for size, name in dims:
        result.shape.dims.add(size=size, name=name)
    return result


@pytest.mark.parametrize("dtype, type", [
    (np.float32, DataType.FLOAT_TYPE),
    (np.float64, DataType.DOUBLE_TYPE),
    (np.int32, DataType.INT32_TYPE),
    (np.int64, DataType.INT64_TYPE),
])
@pytest.mark.parametrize("shape", [(5,), (2, 3), (2, 3, 4), (0, 3)])
def test_round_trip(dtype, type, shape):
    array = np.arange(int(np.prod(shape)), dtype=dtype).reshape(shape) - 3
    result = to_tensor(array)
    assert result.type == type
    assert [dim.size for dim in result.shape.dims] == list(shape)
    back = to_array(result)
    assert back.dtype == dtype
    np.testing.assert_array_equal(back, array)


def test_dim_names():
    assert [dim.name for dim in to_tensor(np.eye(3)).shape.dims] == ["rows", "cols"]
    assert [dim.name for dim in to_tensor(np.zeros(4)).shape.dims] == [""]
    named = to_tensor(np.zeros((1, 2, 3)), names=["batch", "rows", "cols"])
    assert [dim.name for dim in named.shape.dims] == ["batch", "rows", "cols"]
    with pytest.raises(ValueError, match="2 names for 3 dims"):
        to_tensor(np.zeros((1, 2, 3)), names=["rows", "cols"])


def test_transposed_array_is_written_row_major():
    result = to_tensor(np.array([[1.0, 4.0], [2.0, 5.0], [3.0, 6.0]]).T)
    assert list(result.doubles) == [1, 2, 3, 4, 5, 6]


def test_column_major_tensor_is_transposed():
    column_major = tensor(DataType.DOUBLE_TYPE, [1, 4, 2, 5, 3, 6], (3, "cols"), (2, "rows"))
    np.testing.assert_array_equal(to_array(column_major), [[1, 2, 3], [4, 5, 6]])


def test_to_array_returns_a_new_array():
    source = tensor(DataType.DOUBLE_TYPE, [1, 2], (1, "rows"), (2, "cols"))
    to_array(source)[0, 0] = 99
    assert list(source.doubles) == [1, 2]


def test_lists_are_accepted():
    result = to_tensor([[1.5, 2.5]])
    assert result.type == DataType.DOUBLE_TYPE
    np.testing.assert_array_equal(to_array(result), [[1.5, 2.5]])


@pytest.mark.parametrize("value, error", [
    (np.array([1], dtype=np.uint8), TypeError),
    (np.array([True, False]), TypeError),
    (np.array(["a"]), TypeError),
    (np.zeros(()), ValueError),
])
def test_to_tensor_errors(value, error):
    with pytest.raises(error):
        to_tensor(value)


@pytest.mark.parametrize("value, message", [
    (Tensor(), "no shape"),
    (Tensor(type=DataType.UNKNOWN_TYPE, shape={"dims": [{"size": 1}]}), "UNKNOWN_TYPE"),
    (tensor(DataType.DOUBLE_TYPE, [1, 2, 3], (2, "rows"), (2, "cols")), "cannot reshape"),
    (tensor(DataType.DOUBLE_TYPE, [], (-1, "rows")), "negative"),
])
def test_to_array_errors(value, message):
    with pytest.raises(ValueError, match=message):
        to_array(value)
