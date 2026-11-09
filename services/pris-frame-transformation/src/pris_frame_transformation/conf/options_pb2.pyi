from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TelemetryOptions(_message.Message):
    __slots__ = ("otlp_endpoint", "service_name")
    OTLP_ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    SERVICE_NAME_FIELD_NUMBER: _ClassVar[int]
    otlp_endpoint: str
    service_name: str
    def __init__(self, otlp_endpoint: _Optional[str] = ..., service_name: _Optional[str] = ...) -> None: ...

class FrameTransformationOptions(_message.Message):
    __slots__ = ("broker_uri", "telemetry", "camera_ids")
    BROKER_URI_FIELD_NUMBER: _ClassVar[int]
    TELEMETRY_FIELD_NUMBER: _ClassVar[int]
    CAMERA_IDS_FIELD_NUMBER: _ClassVar[int]
    broker_uri: str
    telemetry: TelemetryOptions
    camera_ids: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, broker_uri: _Optional[str] = ..., telemetry: _Optional[_Union[TelemetryOptions, _Mapping]] = ..., camera_ids: _Optional[_Iterable[int]] = ...) -> None: ...
