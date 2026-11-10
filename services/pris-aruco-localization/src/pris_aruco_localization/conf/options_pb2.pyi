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

class SyncOptions(_message.Message):
    __slots__ = ("tolerance", "max_delay")
    TOLERANCE_FIELD_NUMBER: _ClassVar[int]
    MAX_DELAY_FIELD_NUMBER: _ClassVar[int]
    tolerance: float
    max_delay: float
    def __init__(self, tolerance: _Optional[float] = ..., max_delay: _Optional[float] = ...) -> None: ...

class ArucoLocalizationOptions(_message.Message):
    __slots__ = ("broker_uri", "telemetry", "reference_frame", "frame_id_offset", "markers", "camera_ids", "sync", "max_camera_error", "max_error", "min_cameras", "validity")
    class MarkersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: int
        value: float
        def __init__(self, key: _Optional[int] = ..., value: _Optional[float] = ...) -> None: ...
    BROKER_URI_FIELD_NUMBER: _ClassVar[int]
    TELEMETRY_FIELD_NUMBER: _ClassVar[int]
    REFERENCE_FRAME_FIELD_NUMBER: _ClassVar[int]
    FRAME_ID_OFFSET_FIELD_NUMBER: _ClassVar[int]
    MARKERS_FIELD_NUMBER: _ClassVar[int]
    CAMERA_IDS_FIELD_NUMBER: _ClassVar[int]
    SYNC_FIELD_NUMBER: _ClassVar[int]
    MAX_CAMERA_ERROR_FIELD_NUMBER: _ClassVar[int]
    MAX_ERROR_FIELD_NUMBER: _ClassVar[int]
    MIN_CAMERAS_FIELD_NUMBER: _ClassVar[int]
    VALIDITY_FIELD_NUMBER: _ClassVar[int]
    broker_uri: str
    telemetry: TelemetryOptions
    reference_frame: int
    frame_id_offset: int
    markers: _containers.ScalarMap[int, float]
    camera_ids: _containers.RepeatedScalarFieldContainer[int]
    sync: SyncOptions
    max_camera_error: float
    max_error: float
    min_cameras: int
    validity: float
    def __init__(self, broker_uri: _Optional[str] = ..., telemetry: _Optional[_Union[TelemetryOptions, _Mapping]] = ..., reference_frame: _Optional[int] = ..., frame_id_offset: _Optional[int] = ..., markers: _Optional[_Mapping[int, float]] = ..., camera_ids: _Optional[_Iterable[int]] = ..., sync: _Optional[_Union[SyncOptions, _Mapping]] = ..., max_camera_error: _Optional[float] = ..., max_error: _Optional[float] = ..., min_cameras: _Optional[int] = ..., validity: _Optional[float] = ...) -> None: ...
