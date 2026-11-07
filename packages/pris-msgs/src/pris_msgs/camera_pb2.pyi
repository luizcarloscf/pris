import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import wrappers_pb2 as _wrappers_pb2
from pris_msgs import common_pb2 as _common_pb2
from pris_msgs import image_pb2 as _image_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CameraConfigFields(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ALL: _ClassVar[CameraConfigFields]
    SAMPLING_SETTINGS: _ClassVar[CameraConfigFields]
    IMAGE_SETTINGS: _ClassVar[CameraConfigFields]
    CAMERA_SETTINGS: _ClassVar[CameraConfigFields]
    STREAM_CHANNEL_ID: _ClassVar[CameraConfigFields]
    CHANNEL_ID: _ClassVar[CameraConfigFields]
    PTZCONTROL_SETTINGS: _ClassVar[CameraConfigFields]
ALL: CameraConfigFields
SAMPLING_SETTINGS: CameraConfigFields
IMAGE_SETTINGS: CameraConfigFields
CAMERA_SETTINGS: CameraConfigFields
STREAM_CHANNEL_ID: CameraConfigFields
CHANNEL_ID: CameraConfigFields
PTZCONTROL_SETTINGS: CameraConfigFields

class CameraSetting(_message.Message):
    __slots__ = ("automatic", "ratio", "option")
    AUTOMATIC_FIELD_NUMBER: _ClassVar[int]
    RATIO_FIELD_NUMBER: _ClassVar[int]
    OPTION_FIELD_NUMBER: _ClassVar[int]
    automatic: bool
    ratio: float
    option: str
    def __init__(self, automatic: _Optional[bool] = ..., ratio: _Optional[float] = ..., option: _Optional[str] = ...) -> None: ...

class CameraSettings(_message.Message):
    __slots__ = ("brightness", "exposure", "focus", "gain", "gamma", "hue", "iris", "saturation", "sharpness", "shutter", "white_balance_bu", "white_balance_rv", "zoom", "contrast")
    BRIGHTNESS_FIELD_NUMBER: _ClassVar[int]
    EXPOSURE_FIELD_NUMBER: _ClassVar[int]
    FOCUS_FIELD_NUMBER: _ClassVar[int]
    GAIN_FIELD_NUMBER: _ClassVar[int]
    GAMMA_FIELD_NUMBER: _ClassVar[int]
    HUE_FIELD_NUMBER: _ClassVar[int]
    IRIS_FIELD_NUMBER: _ClassVar[int]
    SATURATION_FIELD_NUMBER: _ClassVar[int]
    SHARPNESS_FIELD_NUMBER: _ClassVar[int]
    SHUTTER_FIELD_NUMBER: _ClassVar[int]
    WHITE_BALANCE_BU_FIELD_NUMBER: _ClassVar[int]
    WHITE_BALANCE_RV_FIELD_NUMBER: _ClassVar[int]
    ZOOM_FIELD_NUMBER: _ClassVar[int]
    CONTRAST_FIELD_NUMBER: _ClassVar[int]
    brightness: CameraSetting
    exposure: CameraSetting
    focus: CameraSetting
    gain: CameraSetting
    gamma: CameraSetting
    hue: CameraSetting
    iris: CameraSetting
    saturation: CameraSetting
    sharpness: CameraSetting
    shutter: CameraSetting
    white_balance_bu: CameraSetting
    white_balance_rv: CameraSetting
    zoom: CameraSetting
    contrast: CameraSetting
    def __init__(self, brightness: _Optional[_Union[CameraSetting, _Mapping]] = ..., exposure: _Optional[_Union[CameraSetting, _Mapping]] = ..., focus: _Optional[_Union[CameraSetting, _Mapping]] = ..., gain: _Optional[_Union[CameraSetting, _Mapping]] = ..., gamma: _Optional[_Union[CameraSetting, _Mapping]] = ..., hue: _Optional[_Union[CameraSetting, _Mapping]] = ..., iris: _Optional[_Union[CameraSetting, _Mapping]] = ..., saturation: _Optional[_Union[CameraSetting, _Mapping]] = ..., sharpness: _Optional[_Union[CameraSetting, _Mapping]] = ..., shutter: _Optional[_Union[CameraSetting, _Mapping]] = ..., white_balance_bu: _Optional[_Union[CameraSetting, _Mapping]] = ..., white_balance_rv: _Optional[_Union[CameraSetting, _Mapping]] = ..., zoom: _Optional[_Union[CameraSetting, _Mapping]] = ..., contrast: _Optional[_Union[CameraSetting, _Mapping]] = ...) -> None: ...

class PTZControl(_message.Message):
    __slots__ = ("absolute", "step")
    ABSOLUTE_FIELD_NUMBER: _ClassVar[int]
    STEP_FIELD_NUMBER: _ClassVar[int]
    absolute: _common_pb2.Position
    step: _common_pb2.Position
    def __init__(self, absolute: _Optional[_Union[_common_pb2.Position, _Mapping]] = ..., step: _Optional[_Union[_common_pb2.Position, _Mapping]] = ...) -> None: ...

class CameraConfig(_message.Message):
    __slots__ = ("sampling", "image", "camera", "stream_channel_id", "channel_id", "ptzcontrol")
    SAMPLING_FIELD_NUMBER: _ClassVar[int]
    IMAGE_FIELD_NUMBER: _ClassVar[int]
    CAMERA_FIELD_NUMBER: _ClassVar[int]
    STREAM_CHANNEL_ID_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_ID_FIELD_NUMBER: _ClassVar[int]
    PTZCONTROL_FIELD_NUMBER: _ClassVar[int]
    sampling: _common_pb2.SamplingSettings
    image: _image_pb2.ImageSettings
    camera: CameraSettings
    stream_channel_id: _wrappers_pb2.Int32Value
    channel_id: _wrappers_pb2.Int32Value
    ptzcontrol: PTZControl
    def __init__(self, sampling: _Optional[_Union[_common_pb2.SamplingSettings, _Mapping]] = ..., image: _Optional[_Union[_image_pb2.ImageSettings, _Mapping]] = ..., camera: _Optional[_Union[CameraSettings, _Mapping]] = ..., stream_channel_id: _Optional[_Union[_wrappers_pb2.Int32Value, _Mapping]] = ..., channel_id: _Optional[_Union[_wrappers_pb2.Int32Value, _Mapping]] = ..., ptzcontrol: _Optional[_Union[PTZControl, _Mapping]] = ...) -> None: ...

class CameraCalibration(_message.Message):
    __slots__ = ("id", "calibrated_at", "error", "resolution", "intrinsic", "distortion", "extrinsic")
    ID_FIELD_NUMBER: _ClassVar[int]
    CALIBRATED_AT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    RESOLUTION_FIELD_NUMBER: _ClassVar[int]
    INTRINSIC_FIELD_NUMBER: _ClassVar[int]
    DISTORTION_FIELD_NUMBER: _ClassVar[int]
    EXTRINSIC_FIELD_NUMBER: _ClassVar[int]
    id: int
    calibrated_at: _timestamp_pb2.Timestamp
    error: float
    resolution: _image_pb2.Resolution
    intrinsic: _common_pb2.Tensor
    distortion: _common_pb2.Tensor
    extrinsic: _containers.RepeatedCompositeFieldContainer[FrameTransformation]
    def __init__(self, id: _Optional[int] = ..., calibrated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., error: _Optional[float] = ..., resolution: _Optional[_Union[_image_pb2.Resolution, _Mapping]] = ..., intrinsic: _Optional[_Union[_common_pb2.Tensor, _Mapping]] = ..., distortion: _Optional[_Union[_common_pb2.Tensor, _Mapping]] = ..., extrinsic: _Optional[_Iterable[_Union[FrameTransformation, _Mapping]]] = ...) -> None: ...

class FrameTransformation(_message.Message):
    __slots__ = ("to", "tf", "expiration")
    FROM_FIELD_NUMBER: _ClassVar[int]
    TO_FIELD_NUMBER: _ClassVar[int]
    TF_FIELD_NUMBER: _ClassVar[int]
    EXPIRATION_FIELD_NUMBER: _ClassVar[int]
    to: int
    tf: _common_pb2.Tensor
    expiration: _timestamp_pb2.Timestamp
    def __init__(self, to: _Optional[int] = ..., tf: _Optional[_Union[_common_pb2.Tensor, _Mapping]] = ..., expiration: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., **kwargs) -> None: ...

class FrameTransformations(_message.Message):
    __slots__ = ("tfs",)
    TFS_FIELD_NUMBER: _ClassVar[int]
    tfs: _containers.RepeatedCompositeFieldContainer[FrameTransformation]
    def __init__(self, tfs: _Optional[_Iterable[_Union[FrameTransformation, _Mapping]]] = ...) -> None: ...

class IdPair(_message.Message):
    __slots__ = ("to",)
    FROM_FIELD_NUMBER: _ClassVar[int]
    TO_FIELD_NUMBER: _ClassVar[int]
    to: int
    def __init__(self, to: _Optional[int] = ..., **kwargs) -> None: ...

class GetTransformationRequest(_message.Message):
    __slots__ = ("ids",)
    IDS_FIELD_NUMBER: _ClassVar[int]
    ids: _containers.RepeatedCompositeFieldContainer[IdPair]
    def __init__(self, ids: _Optional[_Iterable[_Union[IdPair, _Mapping]]] = ...) -> None: ...

class GetTransformationReply(_message.Message):
    __slots__ = ("transformations",)
    TRANSFORMATIONS_FIELD_NUMBER: _ClassVar[int]
    transformations: _containers.RepeatedCompositeFieldContainer[FrameTransformation]
    def __init__(self, transformations: _Optional[_Iterable[_Union[FrameTransformation, _Mapping]]] = ...) -> None: ...

class AddTransformationRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class AddTransformationReply(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetCalibrationRequest(_message.Message):
    __slots__ = ("ids",)
    IDS_FIELD_NUMBER: _ClassVar[int]
    ids: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, ids: _Optional[_Iterable[int]] = ...) -> None: ...

class GetCalibrationReply(_message.Message):
    __slots__ = ("calibrations",)
    CALIBRATIONS_FIELD_NUMBER: _ClassVar[int]
    calibrations: _containers.RepeatedCompositeFieldContainer[CameraCalibration]
    def __init__(self, calibrations: _Optional[_Iterable[_Union[CameraCalibration, _Mapping]]] = ...) -> None: ...
