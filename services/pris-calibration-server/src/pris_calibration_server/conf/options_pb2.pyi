from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TelemetryOptions(_message.Message):
    __slots__ = ("otlp_endpoint", "service_name")
    OTLP_ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    SERVICE_NAME_FIELD_NUMBER: _ClassVar[int]
    otlp_endpoint: str
    service_name: str
    def __init__(self, otlp_endpoint: _Optional[str] = ..., service_name: _Optional[str] = ...) -> None: ...

class CalibrationServerOptions(_message.Message):
    __slots__ = ("broker_uri", "calibrations_path", "telemetry")
    BROKER_URI_FIELD_NUMBER: _ClassVar[int]
    CALIBRATIONS_PATH_FIELD_NUMBER: _ClassVar[int]
    TELEMETRY_FIELD_NUMBER: _ClassVar[int]
    broker_uri: str
    calibrations_path: str
    telemetry: TelemetryOptions
    def __init__(self, broker_uri: _Optional[str] = ..., calibrations_path: _Optional[str] = ..., telemetry: _Optional[_Union[TelemetryOptions, _Mapping]] = ...) -> None: ...
