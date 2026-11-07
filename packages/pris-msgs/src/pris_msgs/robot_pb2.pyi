import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from pris_msgs import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class RangeScan(_message.Message):
    __slots__ = ("angles", "ranges")
    ANGLES_FIELD_NUMBER: _ClassVar[int]
    RANGES_FIELD_NUMBER: _ClassVar[int]
    angles: _containers.RepeatedScalarFieldContainer[float]
    ranges: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, angles: _Optional[_Iterable[float]] = ..., ranges: _Optional[_Iterable[float]] = ...) -> None: ...

class RobotConfig(_message.Message):
    __slots__ = ("speed",)
    SPEED_FIELD_NUMBER: _ClassVar[int]
    speed: _common_pb2.Speed
    def __init__(self, speed: _Optional[_Union[_common_pb2.Speed, _Mapping]] = ...) -> None: ...

class BasicMoveTask(_message.Message):
    __slots__ = ("positions", "speeds", "final_orientation", "allowed_error", "rate")
    POSITIONS_FIELD_NUMBER: _ClassVar[int]
    SPEEDS_FIELD_NUMBER: _ClassVar[int]
    FINAL_ORIENTATION_FIELD_NUMBER: _ClassVar[int]
    ALLOWED_ERROR_FIELD_NUMBER: _ClassVar[int]
    RATE_FIELD_NUMBER: _ClassVar[int]
    positions: _containers.RepeatedCompositeFieldContainer[_common_pb2.Position]
    speeds: _containers.RepeatedCompositeFieldContainer[_common_pb2.Speed]
    final_orientation: _common_pb2.Orientation
    allowed_error: float
    rate: float
    def __init__(self, positions: _Optional[_Iterable[_Union[_common_pb2.Position, _Mapping]]] = ..., speeds: _Optional[_Iterable[_Union[_common_pb2.Speed, _Mapping]]] = ..., final_orientation: _Optional[_Union[_common_pb2.Orientation, _Mapping]] = ..., allowed_error: _Optional[float] = ..., rate: _Optional[float] = ...) -> None: ...

class RobotTaskRequest(_message.Message):
    __slots__ = ("id", "basic_move_task")
    ID_FIELD_NUMBER: _ClassVar[int]
    BASIC_MOVE_TASK_FIELD_NUMBER: _ClassVar[int]
    id: int
    basic_move_task: BasicMoveTask
    def __init__(self, id: _Optional[int] = ..., basic_move_task: _Optional[_Union[BasicMoveTask, _Mapping]] = ...) -> None: ...

class RobotTaskReply(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: int
    def __init__(self, id: _Optional[int] = ...) -> None: ...

class RobotControllerProgress(_message.Message):
    __slots__ = ("id", "current_speed", "current_pose", "desired_pose", "error", "completion", "sources", "begin", "end")
    ID_FIELD_NUMBER: _ClassVar[int]
    CURRENT_SPEED_FIELD_NUMBER: _ClassVar[int]
    CURRENT_POSE_FIELD_NUMBER: _ClassVar[int]
    DESIRED_POSE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    COMPLETION_FIELD_NUMBER: _ClassVar[int]
    SOURCES_FIELD_NUMBER: _ClassVar[int]
    BEGIN_FIELD_NUMBER: _ClassVar[int]
    END_FIELD_NUMBER: _ClassVar[int]
    id: int
    current_speed: _common_pb2.Speed
    current_pose: _common_pb2.Pose
    desired_pose: _common_pb2.Pose
    error: float
    completion: float
    sources: _containers.RepeatedScalarFieldContainer[str]
    begin: _timestamp_pb2.Timestamp
    end: _timestamp_pb2.Timestamp
    def __init__(self, id: _Optional[int] = ..., current_speed: _Optional[_Union[_common_pb2.Speed, _Mapping]] = ..., current_pose: _Optional[_Union[_common_pb2.Pose, _Mapping]] = ..., desired_pose: _Optional[_Union[_common_pb2.Pose, _Mapping]] = ..., error: _Optional[float] = ..., completion: _Optional[float] = ..., sources: _Optional[_Iterable[str]] = ..., begin: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., end: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class PathRequest(_message.Message):
    __slots__ = ("id", "destination_pose", "robot_gateway_id", "rate", "allowed_error")
    ID_FIELD_NUMBER: _ClassVar[int]
    DESTINATION_POSE_FIELD_NUMBER: _ClassVar[int]
    ROBOT_GATEWAY_ID_FIELD_NUMBER: _ClassVar[int]
    RATE_FIELD_NUMBER: _ClassVar[int]
    ALLOWED_ERROR_FIELD_NUMBER: _ClassVar[int]
    id: int
    destination_pose: _common_pb2.Pose
    robot_gateway_id: int
    rate: float
    allowed_error: float
    def __init__(self, id: _Optional[int] = ..., destination_pose: _Optional[_Union[_common_pb2.Pose, _Mapping]] = ..., robot_gateway_id: _Optional[int] = ..., rate: _Optional[float] = ..., allowed_error: _Optional[float] = ...) -> None: ...
