from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ArucoDictionary(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DICT_4X4_50: _ClassVar[ArucoDictionary]
    DICT_4X4_100: _ClassVar[ArucoDictionary]
    DICT_4X4_250: _ClassVar[ArucoDictionary]
    DICT_4X4_1000: _ClassVar[ArucoDictionary]
    DICT_5X5_50: _ClassVar[ArucoDictionary]
    DICT_5X5_100: _ClassVar[ArucoDictionary]
    DICT_5X5_250: _ClassVar[ArucoDictionary]
    DICT_5X5_1000: _ClassVar[ArucoDictionary]
    DICT_6X6_50: _ClassVar[ArucoDictionary]
    DICT_6X6_100: _ClassVar[ArucoDictionary]
    DICT_6X6_250: _ClassVar[ArucoDictionary]
    DICT_6X6_1000: _ClassVar[ArucoDictionary]
    DICT_7X7_50: _ClassVar[ArucoDictionary]
    DICT_7X7_100: _ClassVar[ArucoDictionary]
    DICT_7X7_250: _ClassVar[ArucoDictionary]
    DICT_7X7_1000: _ClassVar[ArucoDictionary]
    DICT_ARUCO_ORIGINAL: _ClassVar[ArucoDictionary]
    DICT_APRILTAG_16h5: _ClassVar[ArucoDictionary]
    DICT_APRILTAG_25h9: _ClassVar[ArucoDictionary]
    DICT_APRILTAG_36h10: _ClassVar[ArucoDictionary]
    DICT_APRILTAG_36h11: _ClassVar[ArucoDictionary]
    DICT_ARUCO_MIP_36h12: _ClassVar[ArucoDictionary]

class CornerRefinement(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CORNER_REFINE_SUBPIX: _ClassVar[CornerRefinement]
    CORNER_REFINE_NONE: _ClassVar[CornerRefinement]
    CORNER_REFINE_CONTOUR: _ClassVar[CornerRefinement]
    CORNER_REFINE_APRILTAG: _ClassVar[CornerRefinement]
DICT_4X4_50: ArucoDictionary
DICT_4X4_100: ArucoDictionary
DICT_4X4_250: ArucoDictionary
DICT_4X4_1000: ArucoDictionary
DICT_5X5_50: ArucoDictionary
DICT_5X5_100: ArucoDictionary
DICT_5X5_250: ArucoDictionary
DICT_5X5_1000: ArucoDictionary
DICT_6X6_50: ArucoDictionary
DICT_6X6_100: ArucoDictionary
DICT_6X6_250: ArucoDictionary
DICT_6X6_1000: ArucoDictionary
DICT_7X7_50: ArucoDictionary
DICT_7X7_100: ArucoDictionary
DICT_7X7_250: ArucoDictionary
DICT_7X7_1000: ArucoDictionary
DICT_ARUCO_ORIGINAL: ArucoDictionary
DICT_APRILTAG_16h5: ArucoDictionary
DICT_APRILTAG_25h9: ArucoDictionary
DICT_APRILTAG_36h10: ArucoDictionary
DICT_APRILTAG_36h11: ArucoDictionary
DICT_ARUCO_MIP_36h12: ArucoDictionary
CORNER_REFINE_SUBPIX: CornerRefinement
CORNER_REFINE_NONE: CornerRefinement
CORNER_REFINE_CONTOUR: CornerRefinement
CORNER_REFINE_APRILTAG: CornerRefinement

class TelemetryOptions(_message.Message):
    __slots__ = ("otlp_endpoint", "service_name")
    OTLP_ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    SERVICE_NAME_FIELD_NUMBER: _ClassVar[int]
    otlp_endpoint: str
    service_name: str
    def __init__(self, otlp_endpoint: _Optional[str] = ..., service_name: _Optional[str] = ...) -> None: ...

class DetectorOptions(_message.Message):
    __slots__ = ("dictionary", "corner_refinement", "cpu_threads")
    DICTIONARY_FIELD_NUMBER: _ClassVar[int]
    CORNER_REFINEMENT_FIELD_NUMBER: _ClassVar[int]
    CPU_THREADS_FIELD_NUMBER: _ClassVar[int]
    dictionary: ArucoDictionary
    corner_refinement: CornerRefinement
    cpu_threads: int
    def __init__(self, dictionary: _Optional[_Union[ArucoDictionary, str]] = ..., corner_refinement: _Optional[_Union[CornerRefinement, str]] = ..., cpu_threads: _Optional[int] = ...) -> None: ...

class ArucoDetectorOptions(_message.Message):
    __slots__ = ("broker_uri", "telemetry", "camera_ids", "queue_name", "detector")
    BROKER_URI_FIELD_NUMBER: _ClassVar[int]
    TELEMETRY_FIELD_NUMBER: _ClassVar[int]
    CAMERA_IDS_FIELD_NUMBER: _ClassVar[int]
    QUEUE_NAME_FIELD_NUMBER: _ClassVar[int]
    DETECTOR_FIELD_NUMBER: _ClassVar[int]
    broker_uri: str
    telemetry: TelemetryOptions
    camera_ids: _containers.RepeatedScalarFieldContainer[int]
    queue_name: str
    detector: DetectorOptions
    def __init__(self, broker_uri: _Optional[str] = ..., telemetry: _Optional[_Union[TelemetryOptions, _Mapping]] = ..., camera_ids: _Optional[_Iterable[int]] = ..., queue_name: _Optional[str] = ..., detector: _Optional[_Union[DetectorOptions, _Mapping]] = ...) -> None: ...
