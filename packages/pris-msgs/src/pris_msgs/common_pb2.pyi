from google.protobuf import wrappers_pb2 as _wrappers_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class DataType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNKNOWN_TYPE: _ClassVar[DataType]
    FLOAT_TYPE: _ClassVar[DataType]
    DOUBLE_TYPE: _ClassVar[DataType]
    INT32_TYPE: _ClassVar[DataType]
    INT64_TYPE: _ClassVar[DataType]
UNKNOWN_TYPE: DataType
FLOAT_TYPE: DataType
DOUBLE_TYPE: DataType
INT32_TYPE: DataType
INT64_TYPE: DataType

class SamplingSettings(_message.Message):
    __slots__ = ("frequency", "delay")
    FREQUENCY_FIELD_NUMBER: _ClassVar[int]
    DELAY_FIELD_NUMBER: _ClassVar[int]
    frequency: _wrappers_pb2.FloatValue
    delay: _wrappers_pb2.FloatValue
    def __init__(self, frequency: _Optional[_Union[_wrappers_pb2.FloatValue, _Mapping]] = ..., delay: _Optional[_Union[_wrappers_pb2.FloatValue, _Mapping]] = ...) -> None: ...

class SyncRequest(_message.Message):
    __slots__ = ("entities", "sampling")
    ENTITIES_FIELD_NUMBER: _ClassVar[int]
    SAMPLING_FIELD_NUMBER: _ClassVar[int]
    entities: _containers.RepeatedScalarFieldContainer[str]
    sampling: SamplingSettings
    def __init__(self, entities: _Optional[_Iterable[str]] = ..., sampling: _Optional[_Union[SamplingSettings, _Mapping]] = ...) -> None: ...

class FieldSelector(_message.Message):
    __slots__ = ("fields",)
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    fields: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, fields: _Optional[_Iterable[int]] = ...) -> None: ...

class Shape(_message.Message):
    __slots__ = ("dims",)
    class Dimension(_message.Message):
        __slots__ = ("size", "name")
        SIZE_FIELD_NUMBER: _ClassVar[int]
        NAME_FIELD_NUMBER: _ClassVar[int]
        size: int
        name: str
        def __init__(self, size: _Optional[int] = ..., name: _Optional[str] = ...) -> None: ...
    DIMS_FIELD_NUMBER: _ClassVar[int]
    dims: _containers.RepeatedCompositeFieldContainer[Shape.Dimension]
    def __init__(self, dims: _Optional[_Iterable[_Union[Shape.Dimension, _Mapping]]] = ...) -> None: ...

class Tensor(_message.Message):
    __slots__ = ("shape", "type", "floats", "doubles", "ints32", "ints64")
    SHAPE_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    FLOATS_FIELD_NUMBER: _ClassVar[int]
    DOUBLES_FIELD_NUMBER: _ClassVar[int]
    INTS32_FIELD_NUMBER: _ClassVar[int]
    INTS64_FIELD_NUMBER: _ClassVar[int]
    shape: Shape
    type: DataType
    floats: _containers.RepeatedScalarFieldContainer[float]
    doubles: _containers.RepeatedScalarFieldContainer[float]
    ints32: _containers.RepeatedScalarFieldContainer[int]
    ints64: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, shape: _Optional[_Union[Shape, _Mapping]] = ..., type: _Optional[_Union[DataType, str]] = ..., floats: _Optional[_Iterable[float]] = ..., doubles: _Optional[_Iterable[float]] = ..., ints32: _Optional[_Iterable[int]] = ..., ints64: _Optional[_Iterable[int]] = ...) -> None: ...

class Position(_message.Message):
    __slots__ = ("x", "y", "z")
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    x: float
    y: float
    z: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ...) -> None: ...

class Orientation(_message.Message):
    __slots__ = ("yaw", "pitch", "roll")
    YAW_FIELD_NUMBER: _ClassVar[int]
    PITCH_FIELD_NUMBER: _ClassVar[int]
    ROLL_FIELD_NUMBER: _ClassVar[int]
    yaw: float
    pitch: float
    roll: float
    def __init__(self, yaw: _Optional[float] = ..., pitch: _Optional[float] = ..., roll: _Optional[float] = ...) -> None: ...

class Pose(_message.Message):
    __slots__ = ("position", "orientation")
    POSITION_FIELD_NUMBER: _ClassVar[int]
    ORIENTATION_FIELD_NUMBER: _ClassVar[int]
    position: Position
    orientation: Orientation
    def __init__(self, position: _Optional[_Union[Position, _Mapping]] = ..., orientation: _Optional[_Union[Orientation, _Mapping]] = ...) -> None: ...

class Speed(_message.Message):
    __slots__ = ("linear", "angular")
    LINEAR_FIELD_NUMBER: _ClassVar[int]
    ANGULAR_FIELD_NUMBER: _ClassVar[int]
    linear: float
    angular: float
    def __init__(self, linear: _Optional[float] = ..., angular: _Optional[float] = ...) -> None: ...

class ConsumerInfo(_message.Message):
    __slots__ = ("consumers",)
    CONSUMERS_FIELD_NUMBER: _ClassVar[int]
    consumers: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, consumers: _Optional[_Iterable[str]] = ...) -> None: ...

class ConsumerList(_message.Message):
    __slots__ = ("info",)
    class InfoEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: ConsumerInfo
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[ConsumerInfo, _Mapping]] = ...) -> None: ...
    INFO_FIELD_NUMBER: _ClassVar[int]
    info: _containers.MessageMap[str, ConsumerInfo]
    def __init__(self, info: _Optional[_Mapping[str, ConsumerInfo]] = ...) -> None: ...

class Phrase(_message.Message):
    __slots__ = ("content", "confidence", "language")
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    content: _containers.RepeatedScalarFieldContainer[str]
    confidence: float
    language: str
    def __init__(self, content: _Optional[_Iterable[str]] = ..., confidence: _Optional[float] = ..., language: _Optional[str] = ...) -> None: ...
