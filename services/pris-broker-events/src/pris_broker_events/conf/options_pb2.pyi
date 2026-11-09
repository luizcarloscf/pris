from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class BrokerManagementApiOptions(_message.Message):
    __slots__ = ("uri", "timeout")
    URI_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    uri: str
    timeout: float
    def __init__(self, uri: _Optional[str] = ..., timeout: _Optional[float] = ...) -> None: ...

class TelemetryOptions(_message.Message):
    __slots__ = ("otlp_endpoint", "service_name")
    OTLP_ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    SERVICE_NAME_FIELD_NUMBER: _ClassVar[int]
    otlp_endpoint: str
    service_name: str
    def __init__(self, otlp_endpoint: _Optional[str] = ..., service_name: _Optional[str] = ...) -> None: ...

class BrokerEventsOptions(_message.Message):
    __slots__ = ("broker_uri", "broker_management_api", "telemetry")
    BROKER_URI_FIELD_NUMBER: _ClassVar[int]
    BROKER_MANAGEMENT_API_FIELD_NUMBER: _ClassVar[int]
    TELEMETRY_FIELD_NUMBER: _ClassVar[int]
    broker_uri: str
    broker_management_api: BrokerManagementApiOptions
    telemetry: TelemetryOptions
    def __init__(self, broker_uri: _Optional[str] = ..., broker_management_api: _Optional[_Union[BrokerManagementApiOptions, _Mapping]] = ..., telemetry: _Optional[_Union[TelemetryOptions, _Mapping]] = ...) -> None: ...
