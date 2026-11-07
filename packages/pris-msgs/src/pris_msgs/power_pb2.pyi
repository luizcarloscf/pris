import datetime

from google.protobuf import duration_pb2 as _duration_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class PowerInfo(_message.Message):
    __slots__ = ("voltage", "terminal_voltage", "cell_voltage", "charge", "capacity", "type", "status", "uptime", "autonomy")
    class BatteryType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        PB: _ClassVar[PowerInfo.BatteryType]
        NICD: _ClassVar[PowerInfo.BatteryType]
        NIMH: _ClassVar[PowerInfo.BatteryType]
        LIPO: _ClassVar[PowerInfo.BatteryType]
    PB: PowerInfo.BatteryType
    NICD: PowerInfo.BatteryType
    NIMH: PowerInfo.BatteryType
    LIPO: PowerInfo.BatteryType
    class BatteryStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        UNKNOWN: _ClassVar[PowerInfo.BatteryStatus]
        CHARGING: _ClassVar[PowerInfo.BatteryStatus]
        DISCHARGING: _ClassVar[PowerInfo.BatteryStatus]
        CHARGED: _ClassVar[PowerInfo.BatteryStatus]
        NOT_CONNECTED: _ClassVar[PowerInfo.BatteryStatus]
    UNKNOWN: PowerInfo.BatteryStatus
    CHARGING: PowerInfo.BatteryStatus
    DISCHARGING: PowerInfo.BatteryStatus
    CHARGED: PowerInfo.BatteryStatus
    NOT_CONNECTED: PowerInfo.BatteryStatus
    VOLTAGE_FIELD_NUMBER: _ClassVar[int]
    TERMINAL_VOLTAGE_FIELD_NUMBER: _ClassVar[int]
    CELL_VOLTAGE_FIELD_NUMBER: _ClassVar[int]
    CHARGE_FIELD_NUMBER: _ClassVar[int]
    CAPACITY_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    UPTIME_FIELD_NUMBER: _ClassVar[int]
    AUTONOMY_FIELD_NUMBER: _ClassVar[int]
    voltage: float
    terminal_voltage: float
    cell_voltage: _containers.RepeatedScalarFieldContainer[float]
    charge: float
    capacity: float
    type: PowerInfo.BatteryType
    status: PowerInfo.BatteryStatus
    uptime: _duration_pb2.Duration
    autonomy: _duration_pb2.Duration
    def __init__(self, voltage: _Optional[float] = ..., terminal_voltage: _Optional[float] = ..., cell_voltage: _Optional[_Iterable[float]] = ..., charge: _Optional[float] = ..., capacity: _Optional[float] = ..., type: _Optional[_Union[PowerInfo.BatteryType, str]] = ..., status: _Optional[_Union[PowerInfo.BatteryStatus, str]] = ..., uptime: _Optional[_Union[datetime.timedelta, _duration_pb2.Duration, _Mapping]] = ..., autonomy: _Optional[_Union[datetime.timedelta, _duration_pb2.Duration, _Mapping]] = ...) -> None: ...
