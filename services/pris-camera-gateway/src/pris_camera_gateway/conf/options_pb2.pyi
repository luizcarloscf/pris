from pris_msgs import camera_pb2 as _camera_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ColorProcessingAlgorithm(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NONE: _ClassVar[ColorProcessingAlgorithm]
    NEAREST_NEIGHBOR: _ClassVar[ColorProcessingAlgorithm]
    NEAREST_NEIGHBOR_AVG: _ClassVar[ColorProcessingAlgorithm]
    EDGE_SENSING: _ClassVar[ColorProcessingAlgorithm]
    HQ_LINEAR: _ClassVar[ColorProcessingAlgorithm]
    BILINEAR: _ClassVar[ColorProcessingAlgorithm]
    DIRECTIONAL_FILTER: _ClassVar[ColorProcessingAlgorithm]
    WEIGHTED_DIRECTIONAL_FILTER: _ClassVar[ColorProcessingAlgorithm]
    RIGOROUS: _ClassVar[ColorProcessingAlgorithm]
    IPP: _ClassVar[ColorProcessingAlgorithm]

class TriggerMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FREE_RUN: _ClassVar[TriggerMode]
    SOFTWARE_SCHEDULED: _ClassVar[TriggerMode]
NONE: ColorProcessingAlgorithm
NEAREST_NEIGHBOR: ColorProcessingAlgorithm
NEAREST_NEIGHBOR_AVG: ColorProcessingAlgorithm
EDGE_SENSING: ColorProcessingAlgorithm
HQ_LINEAR: ColorProcessingAlgorithm
BILINEAR: ColorProcessingAlgorithm
DIRECTIONAL_FILTER: ColorProcessingAlgorithm
WEIGHTED_DIRECTIONAL_FILTER: ColorProcessingAlgorithm
RIGOROUS: ColorProcessingAlgorithm
IPP: ColorProcessingAlgorithm
FREE_RUN: TriggerMode
SOFTWARE_SCHEDULED: TriggerMode

class CameraOptions(_message.Message):
    __slots__ = ("id", "ip", "trigger_mode", "algorithm", "onboard_color_processing", "use_turbojpeg", "packet_size", "packet_delay", "packet_resend", "packet_resend_timeout", "packet_resend_max_requests", "reverse_x", "initial_config", "settle_time", "clock_sync_period", "latch_samples")
    ID_FIELD_NUMBER: _ClassVar[int]
    IP_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_MODE_FIELD_NUMBER: _ClassVar[int]
    ALGORITHM_FIELD_NUMBER: _ClassVar[int]
    ONBOARD_COLOR_PROCESSING_FIELD_NUMBER: _ClassVar[int]
    USE_TURBOJPEG_FIELD_NUMBER: _ClassVar[int]
    PACKET_SIZE_FIELD_NUMBER: _ClassVar[int]
    PACKET_DELAY_FIELD_NUMBER: _ClassVar[int]
    PACKET_RESEND_FIELD_NUMBER: _ClassVar[int]
    PACKET_RESEND_TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    PACKET_RESEND_MAX_REQUESTS_FIELD_NUMBER: _ClassVar[int]
    REVERSE_X_FIELD_NUMBER: _ClassVar[int]
    INITIAL_CONFIG_FIELD_NUMBER: _ClassVar[int]
    SETTLE_TIME_FIELD_NUMBER: _ClassVar[int]
    CLOCK_SYNC_PERIOD_FIELD_NUMBER: _ClassVar[int]
    LATCH_SAMPLES_FIELD_NUMBER: _ClassVar[int]
    id: int
    ip: str
    trigger_mode: TriggerMode
    algorithm: ColorProcessingAlgorithm
    onboard_color_processing: bool
    use_turbojpeg: bool
    packet_size: int
    packet_delay: int
    packet_resend: bool
    packet_resend_timeout: int
    packet_resend_max_requests: int
    reverse_x: bool
    initial_config: _camera_pb2.CameraConfig
    settle_time: float
    clock_sync_period: float
    latch_samples: int
    def __init__(self, id: _Optional[int] = ..., ip: _Optional[str] = ..., trigger_mode: _Optional[_Union[TriggerMode, str]] = ..., algorithm: _Optional[_Union[ColorProcessingAlgorithm, str]] = ..., onboard_color_processing: _Optional[bool] = ..., use_turbojpeg: _Optional[bool] = ..., packet_size: _Optional[int] = ..., packet_delay: _Optional[int] = ..., packet_resend: _Optional[bool] = ..., packet_resend_timeout: _Optional[int] = ..., packet_resend_max_requests: _Optional[int] = ..., reverse_x: _Optional[bool] = ..., initial_config: _Optional[_Union[_camera_pb2.CameraConfig, _Mapping]] = ..., settle_time: _Optional[float] = ..., clock_sync_period: _Optional[float] = ..., latch_samples: _Optional[int] = ...) -> None: ...

class TelemetryOptions(_message.Message):
    __slots__ = ("otlp_endpoint", "service_name")
    OTLP_ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    SERVICE_NAME_FIELD_NUMBER: _ClassVar[int]
    otlp_endpoint: str
    service_name: str
    def __init__(self, otlp_endpoint: _Optional[str] = ..., service_name: _Optional[str] = ...) -> None: ...

class CameraGatewayOptions(_message.Message):
    __slots__ = ("broker_uri", "telemetry", "camera")
    BROKER_URI_FIELD_NUMBER: _ClassVar[int]
    TELEMETRY_FIELD_NUMBER: _ClassVar[int]
    CAMERA_FIELD_NUMBER: _ClassVar[int]
    broker_uri: str
    telemetry: TelemetryOptions
    camera: CameraOptions
    def __init__(self, broker_uri: _Optional[str] = ..., telemetry: _Optional[_Union[TelemetryOptions, _Mapping]] = ..., camera: _Optional[_Union[CameraOptions, _Mapping]] = ...) -> None: ...
